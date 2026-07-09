import pytest

from myhome.ids import InvalidIdError, validate_safe_id


@pytest.mark.parametrize("value", [
    "abc123", "test-home", "a_b-C9", "f" * 64,
])
def test_validate_safe_id_accepts_safe_values(value):
    assert validate_safe_id(value) == value


@pytest.mark.parametrize("value", [
    "..", "../../etc", "a/b", "a\\b", "", "f" * 65, ".", "home;rm -rf",
])
def test_validate_safe_id_rejects_unsafe_values(value):
    with pytest.raises(InvalidIdError):
        validate_safe_id(value)
