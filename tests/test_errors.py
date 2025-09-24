#!/usr/bin/env python

"""Tests for error handling in `cryptobot` package."""
import pytest

from cryptobot.errors import CryptoBotError


class TestCryptoBotError:
    """Tests for CryptoBotError exception handling."""

    def test_cryptobot_error_creation(self):
        """Test creating CryptoBotError with basic parameters."""
        error = CryptoBotError(code=400, name="BAD_REQUEST")
        assert error.code == 400
        assert error.name == "BAD_REQUEST"

    def test_cryptobot_error_with_description(self):
        """Test creating CryptoBotError with description using parse_json."""
        # Using from_json to add description dynamically
        error = CryptoBotError.from_json(
            {"code": 401, "name": "UNAUTHORIZED", "description": "Invalid API token"}
        )
        assert error.code == 401
        assert error.name == "UNAUTHORIZED"
        assert error.description == "Invalid API token"

    def test_cryptobot_error_str_representation(self):
        """Test string representation of CryptoBotError."""
        error = CryptoBotError(code=404, name="NOT_FOUND")
        assert str(error) == "code=404, name=NOT_FOUND"

    def test_cryptobot_error_from_json(self):
        """Test creating CryptoBotError from JSON data."""
        json_data = {
            "code": 422,
            "name": "UNPROCESSABLE_ENTITY",
            "description": "Validation error",
        }
        error = CryptoBotError.from_json(json_data)
        assert error.code == 422
        assert error.name == "UNPROCESSABLE_ENTITY"
        assert error.description == "Validation error"

    def test_cryptobot_error_from_json_minimal(self):
        """Test creating CryptoBotError from minimal JSON data."""
        json_data = {"code": 500, "name": "INTERNAL_SERVER_ERROR"}
        error = CryptoBotError.from_json(json_data)
        assert error.code == 500
        assert error.name == "INTERNAL_SERVER_ERROR"

    def test_cryptobot_error_equality(self):
        """Test equality comparison of CryptoBotError instances."""
        error1 = CryptoBotError(code=400, name="BAD_REQUEST")
        error2 = CryptoBotError(code=400, name="BAD_REQUEST")
        error3 = CryptoBotError(code=401, name="UNAUTHORIZED")

        assert error1.code == error2.code
        assert error1.name == error2.name
        assert error1.code != error3.code

    def test_cryptobot_error_inheritance(self):
        """Test that CryptoBotError inherits from Exception."""
        error = CryptoBotError(code=400, name="BAD_REQUEST")
        assert isinstance(error, Exception)

    def test_cryptobot_error_common_codes(self):
        """Test creating errors with common HTTP status codes."""
        common_errors = [
            (400, "BAD_REQUEST"),
            (401, "UNAUTHORIZED"),
            (403, "FORBIDDEN"),
            (404, "NOT_FOUND"),
            (422, "UNPROCESSABLE_ENTITY"),
            (500, "INTERNAL_SERVER_ERROR"),
        ]

        for code, name in common_errors:
            error = CryptoBotError(code=code, name=name)
            assert error.code == code
            assert error.name == name

    def test_cryptobot_error_raise_and_catch(self):
        """Test raising and catching CryptoBotError."""
        with pytest.raises(CryptoBotError) as exc_info:
            raise CryptoBotError(code=401, name="UNAUTHORIZED")

        error = exc_info.value
        assert error.code == 401
        assert error.name == "UNAUTHORIZED"

    def test_cryptobot_error_with_none_values(self):
        """Test creating CryptoBotError with None values."""
        error = CryptoBotError(code=None, name=None)
        assert error.code is None
        assert error.name is None
