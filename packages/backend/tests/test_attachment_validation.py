import pytest

from myhome.attachment_validation import (
    ALLOWED_EXTENSIONS,
    sanitise_filename,
    validate_filename,
    validate_id,
)


def test_allowed_extensions():
    assert ALLOWED_EXTENSIONS == {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def test_sanitise_filename_strips_spaces_and_unsafe_chars():
    assert sanitise_filename("my photo (1).JPG") == "my_photo_1.JPG"


def test_sanitise_filename_falls_back_when_result_is_empty():
    assert sanitise_filename("???") == "attachment"


def test_validate_id_accepts_valid_id():
    validate_id("abc-123_XYZ")  # must not raise


def test_validate_id_rejects_path_traversal():
    with pytest.raises(ValueError):
        validate_id("../etc/passwd")


def test_validate_filename_accepts_valid_filename():
    validate_filename("photo.jpg")  # must not raise


def test_validate_filename_rejects_leading_dot():
    with pytest.raises(ValueError):
        validate_filename(".hidden")


def test_validate_filename_rejects_path_separator():
    with pytest.raises(ValueError):
        validate_filename("a/b.jpg")
