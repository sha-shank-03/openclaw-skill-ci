"""Strict bounded JSON/JSON5 data parsing, never JavaScript evaluation."""

import json
import math

import json5

from .limits import MAX_DEPTH
from .model import InputError


def check_text_depth(text, location, json5_mode=False):
    depth = 0
    quote = None
    escaped = False
    comment = None
    index = 0
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if comment == "line":
            if char in "\r\n":
                comment = None
        elif comment == "block":
            if char == "*" and following == "/":
                comment = None
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif json5_mode and char == "/" and following in ("/", "*"):
            comment = "line" if following == "/" else "block"
            index += 1
        elif char == '"' or (json5_mode and char == "'"):
            quote = char
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise InputError("INPUT_DEPTH", location, "Container nesting exceeds depth 32.")
        elif char in "]}":
            depth -= 1
        index += 1


def validate_tree(value, location):
    pending = [(value, 0)]
    while pending:
        item, parent_depth = pending.pop()
        if type(item) in (dict, list):
            depth = parent_depth + 1
            if depth > MAX_DEPTH:
                raise InputError("INPUT_DEPTH", location, "Container nesting exceeds depth 32.")
            if type(item) is dict:
                if any(type(key) is not str for key in item):
                    raise InputError("INPUT_JSON_TYPE", location, "Object keys must be strings.")
                try:
                    for key in item:
                        key.encode("utf-8")
                except UnicodeError:
                    raise InputError("INPUT_JSON_TYPE", location, "Object keys must be valid Unicode scalar text.") from None
                pending.extend((child, depth) for child in item.values())
            else:
                pending.extend((child, depth) for child in item)
        elif type(item) is float and not math.isfinite(item):
            raise InputError("INPUT_NONFINITE", location, "Non-finite values are unsupported.")
        elif type(item) is str:
            try:
                item.encode("utf-8")
            except UnicodeError:
                raise InputError("INPUT_JSON_TYPE", location, "Strings must be valid Unicode scalar text.") from None
        elif type(item) not in (str, bool, int, float, type(None)):
            raise InputError("INPUT_JSON_TYPE", location, "Only JSON-compatible data values are supported.")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("non-finite JSON")


def _finite_float(token):
    value = float(token)
    if not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    return value


def parse_json(text, location, json5_mode=False):
    check_text_depth(text, location, json5_mode)
    rule = "INPUT_JSON5" if json5_mode else "INPUT_JSON"
    try:
        if json5_mode:
            value = json5.loads(text, allow_duplicate_keys=False, parse_float=_finite_float,
                                parse_constant=_reject_constant, consume_trailing=True)
        else:
            value = json.loads(text, object_pairs_hook=_unique_pairs,
                               parse_constant=_reject_constant, parse_float=_finite_float)
        validate_tree(value, location)
    except (ValueError, RecursionError, OverflowError):
        raise InputError(rule, location, "Expected valid data with unique keys and finite numbers.") from None
    return value
