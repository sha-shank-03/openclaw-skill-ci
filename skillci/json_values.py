"""JSON value equality without Python's boolean/number coercion."""

import math


def json_equal(left, right):
    """Compare recursively; finite int/float numbers share a category, bool does not.

    Numbers use exact Python numeric equality with no tolerance. Decimal JSON
    tokens are parsed as binary floats, so decimal precision is not guaranteed.
    Objects ignore key order; arrays preserve order and length.
    """
    left_type, right_type = type(left), type(right)
    if left_type in (int, float) and right_type in (int, float):
        if ((left_type is float and not math.isfinite(left))
                or (right_type is float and not math.isfinite(right))):
            return False
        return left == right
    if left_type is not right_type:
        return False
    if left_type is dict:
        return (left.keys() == right.keys()
                and all(json_equal(left[key], right[key]) for key in left))
    if left_type is list:
        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
    return left_type in (str, bool, type(None)) and left == right
