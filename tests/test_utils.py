#!/usr/bin/env python

"""Tests for utility functions in `cryptobot` package."""

from dataclasses import dataclass
from typing import Optional

import pytest

from cryptobot._utils import parse_json


@dataclass
class SampleClass:
    """Sample dataclass for parse_json testing."""

    required_field: str
    optional_field: Optional[int] = None


@dataclass
class SimpleClass:
    """Simple test dataclass."""

    name: str
    value: int


class TestParseJson:
    """Tests for parse_json utility function."""

    def test_parse_json_basic(self):
        """Test basic parse_json functionality."""
        json_data = {"required_field": "test_value", "optional_field": 42}

        result = parse_json(SampleClass, **json_data)

        assert isinstance(result, SampleClass)
        assert result.required_field == "test_value"
        assert result.optional_field == 42

    def test_parse_json_extra_fields(self):
        """Test parse_json with extra fields not in class signature."""
        json_data = {
            "required_field": "test_value",
            "optional_field": 42,
            "extra_field": "extra_value",
            "another_extra": 123,
        }

        result = parse_json(SampleClass, **json_data)

        assert result.required_field == "test_value"
        assert result.optional_field == 42

        # Extra fields should be set as attributes
        assert hasattr(result, "extra_field")
        assert hasattr(result, "another_extra")
        assert result.extra_field == "extra_value"
        assert result.another_extra == 123

    def test_parse_json_missing_optional_fields(self):
        """Test parse_json with missing optional fields."""
        json_data = {
            "required_field": "test_value"
            # optional_field is missing, should use default
        }

        result = parse_json(SampleClass, **json_data)

        assert result.required_field == "test_value"
        assert result.optional_field is None  # Default value

    def test_parse_json_missing_required_fields(self):
        """Test parse_json with missing required fields."""
        json_data = {
            "optional_field": 42
            # required_field is missing
        }

        with pytest.raises(TypeError):
            parse_json(SampleClass, **json_data)

    def test_parse_json_empty_data(self):
        """Test parse_json with empty data."""
        with pytest.raises(TypeError):
            parse_json(SampleClass)

    def test_parse_json_simple_class(self):
        """Test parse_json with simple class."""
        json_data = {"name": "test_name", "value": 100}

        result = parse_json(SimpleClass, **json_data)

        assert isinstance(result, SimpleClass)
        assert result.name == "test_name"
        assert result.value == 100

    def test_parse_json_type_conversion(self):
        """Test parse_json handles type conversion correctly."""
        json_data = {"name": "test", "value": "123"}  # String that should work as int

        result = parse_json(SimpleClass, **json_data)

        assert result.name == "test"
        assert result.value == "123"  # No automatic type conversion

    def test_parse_json_none_values(self):
        """Test parse_json with None values."""
        json_data = {"required_field": None, "optional_field": None}

        result = parse_json(SampleClass, **json_data)

        assert result.required_field is None
        assert result.optional_field is None

    def test_parse_json_complex_extra_fields(self):
        """Test parse_json with complex extra field values."""
        json_data = {
            "required_field": "test",
            "list_field": [1, 2, 3],
            "dict_field": {"nested": "value"},
            "bool_field": True,
            "float_field": 3.14,
        }

        result = parse_json(SampleClass, **json_data)

        assert result.required_field == "test"
        assert result.list_field == [1, 2, 3]
        assert result.dict_field == {"nested": "value"}
        assert result.bool_field is True
        assert result.float_field == 3.14

    def test_parse_json_overwrites_extra_fields(self):
        """Test that extra fields can be overwritten."""
        json_data = {"required_field": "test", "dynamic_field": "initial_value"}

        result = parse_json(SampleClass, **json_data)
        assert result.dynamic_field == "initial_value"

        # Manually overwrite the dynamic field
        result.dynamic_field = "updated_value"
        assert result.dynamic_field == "updated_value"

    def test_parse_json_field_name_collision(self):
        """Test parse_json behavior when extra field name collides with method."""
        json_data = {
            "required_field": "test",
            "custom_attr": "custom_value",  # Safe attribute name
        }

        result = parse_json(SampleClass, **json_data)

        # The original __class__ should not be overwritten
        assert result.__class__ == SampleClass
        # Custom attribute should be set
        assert result.custom_attr == "custom_value"

    def test_parse_json_empty_string_fields(self):
        """Test parse_json with empty string fields."""
        json_data = {"required_field": "", "optional_field": 0, "empty_extra": ""}

        result = parse_json(SampleClass, **json_data)

        assert result.required_field == ""
        assert result.optional_field == 0
        assert result.empty_extra == ""

    def test_parse_json_maintains_dataclass_methods(self):
        """Test that dataclass methods are preserved."""
        json_data = {"required_field": "test1", "optional_field": 42}

        result1 = parse_json(SampleClass, **json_data)
        result2 = parse_json(SampleClass, **json_data)

        # Test equality (dataclass feature)
        assert result1 == result2

        # Test repr (dataclass feature)
        repr_str = repr(result1)
        assert "SampleClass" in repr_str
        assert "test1" in repr_str

    def test_parse_json_with_class_without_defaults(self):
        """Test parse_json with class that has no default values."""
        json_data = {"name": "test_name", "value": 42, "extra_field": "extra"}

        result = parse_json(SimpleClass, **json_data)

        assert result.name == "test_name"
        assert result.value == 42
        assert result.extra_field == "extra"
