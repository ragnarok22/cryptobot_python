from dataclasses import is_dataclass
from enum import Enum
from inspect import signature
from typing import Any, Type, TypeVar, Union, get_args, get_origin, get_type_hints

T = TypeVar("T")


def _convert_union_value(value: Any, union_args: tuple) -> Any:
    for arg_type in (arg for arg in union_args if arg is not type(None)):
        try:
            return _convert_typed_value(value, arg_type)
        except (ValueError, TypeError, KeyError):
            continue
    return value


def _convert_list_value(value: Any, list_args: tuple) -> Any:
    item_type = list_args[0] if list_args else Any
    if not isinstance(value, list):
        return value
    return [_convert_typed_value(item, item_type) for item in value]


def _convert_class_value(value: Any, expected_type: type) -> Any:
    if issubclass(expected_type, Enum):
        if isinstance(value, expected_type):
            return value
        try:
            return expected_type(value)
        except ValueError:
            return value

    if is_dataclass(expected_type) and isinstance(value, dict):
        return parse_json(expected_type, **value)

    return value


def _convert_typed_value(value: Any, expected_type: Any) -> Any:
    if value is None or expected_type is Any:
        return value

    origin = get_origin(expected_type)
    args = get_args(expected_type)

    if origin is Union:
        return _convert_union_value(value, args)

    if origin in (list,):
        return _convert_list_value(value, args)

    if isinstance(expected_type, type):
        return _convert_class_value(value, expected_type)

    return value


def parse_json(cls: Type[T], **json: Any) -> T:
    cls_fields = {field for field in signature(cls).parameters}
    type_hints = get_type_hints(cls)
    native_args, new_args = {}, {}
    for name, val in json.items():
        if name in cls_fields:
            expected_type = type_hints.get(name)
            native_args[name] = _convert_typed_value(val, expected_type) if expected_type else val
        else:
            new_args[name] = val
    ret = cls(**native_args)
    for new_name, new_val in new_args.items():
        setattr(ret, new_name, new_val)
    return ret
