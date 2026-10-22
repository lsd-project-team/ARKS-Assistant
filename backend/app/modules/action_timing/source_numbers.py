"""基础表达式投影与整数边界；不以Python无限精度证明C#整数有效。"""

import math

INTEGER_RANGES = {
    "int": (-(2**31), 2**31 - 1),
    "uint": (0, 2**32 - 1),
    "long": (-(2**63), 2**63 - 1),
    "ulong": (0, 2**64 - 1),
    "short": (-(2**15), 2**15 - 1),
    "ushort": (0, 2**16 - 1),
    "byte": (0, 255),
    "sbyte": (-128, 127),
}


def bounded(index, node, method, value):
    limits = INTEGER_RANGES.get(index.infer(node, method))
    invalid = limits and isinstance(value, int) and not limits[0] <= value <= limits[1]
    return (None, True) if invalid else (value, False)


def binary_value(op, left, right):
    if op == "&&":
        return (
            False
            if left is False or right is False
            else True
            if left is True and right is True
            else None
        )
    if op == "||":
        return (
            True
            if left is True or right is True
            else False
            if left is False and right is False
            else None
        )
    if left is None or right is None:
        return None
    try:
        operations = {
            "+": lambda: left + right,
            "-": lambda: left - right,
            "*": lambda: left * right,
            "/": lambda: (
                math.trunc(left / right)
                if isinstance(left, int) and isinstance(right, int)
                else left / right
            ),
            "==": lambda: left == right,
            "!=": lambda: left != right,
            ">": lambda: left > right,
            "<": lambda: left < right,
            ">=": lambda: left >= right,
            "<=": lambda: left <= right,
        }
        result = operations[op]() if op in operations else None
        return result if not isinstance(result, (int, float)) or math.isfinite(result) else None
    except (TypeError, ZeroDivisionError, OverflowError):
        return None
