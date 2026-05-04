import pytest
from app.modules.organizations.domain.value_objects import (
    INN,
    KPP,
    HSLColor,
    InvalidHSLColor,
    InvalidINN,
    InvalidKPP,
    InvalidSlug,
    Slug,
)


class TestSlug:
    @pytest.mark.parametrize(
        "value",
        ["alpha", "alpha-beta", "a", "a-1", "moscow-branch", "0", "abc-def-ghi"],
    )
    def test_accepts_valid(self, value: str) -> None:
        assert str(Slug(value)) == value

    @pytest.mark.parametrize(
        "value",
        ["", "Alpha", "-leading", "trailing-", "with space", "two--dashes" + "x" * 80],
    )
    def test_rejects_invalid(self, value: str) -> None:
        with pytest.raises(InvalidSlug):
            Slug(value)


class TestINN:
    @pytest.mark.parametrize("value", ["1234567890", "123456789012"])
    def test_accepts_10_or_12_digits(self, value: str) -> None:
        assert str(INN(value)) == value

    @pytest.mark.parametrize("value", ["", "12345", "abcd1234567", "12345678901"])
    def test_rejects_invalid(self, value: str) -> None:
        with pytest.raises(InvalidINN):
            INN(value)


class TestKPP:
    def test_accepts_valid_format(self) -> None:
        assert str(KPP("770401001")) == "770401001"

    @pytest.mark.parametrize("value", ["", "12345", "1234abc01", "abcdefghi"])
    def test_rejects_invalid(self, value: str) -> None:
        with pytest.raises(InvalidKPP):
            KPP(value)


class TestHSLColor:
    @pytest.mark.parametrize("value", ["222 47% 11%", "0 0% 100%", "120 100% 50%"])
    def test_accepts_valid(self, value: str) -> None:
        assert str(HSLColor(value)) == value

    @pytest.mark.parametrize("value", ["222,47%,11%", "rgb(1,2,3)", "#ffffff", "222 47 11"])
    def test_rejects_invalid(self, value: str) -> None:
        with pytest.raises(InvalidHSLColor):
            HSLColor(value)
