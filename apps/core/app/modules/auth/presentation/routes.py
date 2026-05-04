from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.config import Settings, get_settings

from ..application.dto import LoginInput
from ..application.use_cases.get_current_user import GetCurrentUser
from ..application.use_cases.login import Login
from ..application.use_cases.logout import Logout
from ..application.use_cases.refresh_access_token import RefreshAccessToken
from ..domain.exceptions import (
    InactiveUser,
    InvalidCredentials,
    TokenExpired,
    TokenInvalid,
    TokenRevoked,
    UserNotFound,
)
from .cookies import clear_auth_cookies, set_auth_cookies
from .deps import (
    assert_csrf,
    current_user,
    get_get_current_user,
    get_login,
    get_logout,
    get_refresh_access_token,
)
from .schemas import CurrentUserResponse, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate with email and password",
    description=(
        "Validates credentials, sets httpOnly access/refresh cookies and a "
        "non-httpOnly CSRF cookie. Response body carries the user profile "
        "and the list of memberships so the frontend can decide where to "
        "redirect (single → /portal/<slug>, multiple → /select-org)."
    ),
)
async def login(
    request: LoginRequest,
    raw_request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    use_case: Annotated[Login, Depends(get_login)],
    current_user_use_case: Annotated[GetCurrentUser, Depends(get_get_current_user)],
) -> LoginResponse:
    try:
        tokens = await use_case.execute(
            LoginInput(
                email=request.email,
                password=request.password,
                user_agent=raw_request.headers.get("user-agent"),
                ip_address=raw_request.client.host if raw_request.client else None,
            )
        )
    except InvalidCredentials as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
        ) from exc
    except InactiveUser as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="user is inactive") from exc

    set_auth_cookies(
        response=response,
        settings=settings,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_expires_at=tokens.access_expires_at,
        refresh_expires_at=tokens.refresh_expires_at,
    )

    profile = await current_user_use_case.execute(tokens.user_id)
    return LoginResponse.model_validate(profile, from_attributes=True)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log the current session out",
    dependencies=[Depends(assert_csrf)],
)
async def logout(
    raw_request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    use_case: Annotated[Logout, Depends(get_logout)],
) -> Response:
    access_token = raw_request.cookies.get(settings.access_cookie_name)
    refresh_token = raw_request.cookies.get(settings.refresh_cookie_name)
    await use_case.execute(access_token=access_token, refresh_token=refresh_token)
    clear_auth_cookies(response, settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/refresh",
    summary="Rotate refresh and access tokens",
    description=(
        "Reads the refresh cookie, validates it, issues a new access + "
        "refresh pair (rotation), invalidates the old refresh, and "
        "rewrites cookies. CSRF check applies."
    ),
    dependencies=[Depends(assert_csrf)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def refresh(
    raw_request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    use_case: Annotated[RefreshAccessToken, Depends(get_refresh_access_token)],
) -> Response:
    refresh_token = raw_request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="no refresh cookie")
    try:
        tokens = await use_case.execute(
            refresh_token,
            user_agent=raw_request.headers.get("user-agent"),
            ip_address=raw_request.client.host if raw_request.client else None,
        )
    except TokenExpired as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="refresh token expired") from exc
    except TokenRevoked as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="refresh token revoked") from exc
    except (TokenInvalid, UserNotFound) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc
    except InactiveUser as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="user is inactive") from exc

    set_auth_cookies(
        response=response,
        settings=settings,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_expires_at=tokens.access_expires_at,
        refresh_expires_at=tokens.refresh_expires_at,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Return current user profile and memberships",
)
async def get_me(
    user_id: Annotated[UUID, Depends(current_user)],
    use_case: Annotated[GetCurrentUser, Depends(get_get_current_user)],
) -> CurrentUserResponse:
    profile = await use_case.execute(user_id)
    return CurrentUserResponse.model_validate(profile, from_attributes=True)
