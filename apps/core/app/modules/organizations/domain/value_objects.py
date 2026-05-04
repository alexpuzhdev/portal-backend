import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Slug:
    """URL-friendly идентификатор организации в дереве холдинга."""

    value: str

    _PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?$")

    def __post_init__(self) -> None:
        if not self._PATTERN.fullmatch(self.value):
            raise InvalidSlug(self.value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class INN:
    """ИНН — идентификационный номер налогоплательщика. 10 цифр (юрлицо)
    или 12 цифр (физлицо/ИП)."""

    value: str

    _DIGITS_ONLY = re.compile(r"^\d+$")

    def __post_init__(self) -> None:
        if not self._DIGITS_ONLY.fullmatch(self.value):
            raise InvalidINN(self.value)
        if len(self.value) not in (10, 12):
            raise InvalidINN(self.value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class KPP:
    """КПП — код причины постановки на учёт. 9 символов."""

    value: str

    _PATTERN = re.compile(r"^\d{4}[A-Z\d]{2}\d{3}$")

    def __post_init__(self) -> None:
        if not self._PATTERN.fullmatch(self.value):
            raise InvalidKPP(self.value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class HSLColor:
    """Цвет в формате `H S% L%` для подстановки в shadcn CSS-переменные.
    Например: `222 47% 11%`."""

    value: str

    _PATTERN = re.compile(r"^\d{1,3}\s+\d{1,3}%\s+\d{1,3}%$")

    def __post_init__(self) -> None:
        if not self._PATTERN.fullmatch(self.value):
            raise InvalidHSLColor(self.value)

    def __str__(self) -> str:
        return self.value


class InvalidSlug(ValueError):
    def __init__(self, value: str) -> None:
        super().__init__(
            f"invalid slug '{value}': allowed [a-z0-9-], must start and end with "
            "alphanumeric, length 1..63"
        )


class InvalidINN(ValueError):
    def __init__(self, value: str) -> None:
        super().__init__(f"invalid INN '{value}': must be 10 or 12 digits")


class InvalidKPP(ValueError):
    def __init__(self, value: str) -> None:
        super().__init__(f"invalid KPP '{value}': expected 9 chars (NNNNXXNNN)")


class InvalidHSLColor(ValueError):
    def __init__(self, value: str) -> None:
        super().__init__(f"invalid HSL color '{value}': expected format like '222 47% 11%'")
