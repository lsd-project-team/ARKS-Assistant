"""基础表达式投影与整数边界；不以Python无限精度证明C#整数有效。"""

import math
import re

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

NUMERIC_TYPES = {*INTEGER_RANGES, "char", "float", "double", "decimal"}


def coerce(kind, value):
    if (
        kind in {"float", "double", "decimal"}
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        return float(value)
    return value


def literal(source, real=False):
    cleaned = re.sub(r"[fFdDmM]+$" if real else r"[uUlL]+$", "", source.replace("_", ""))
    try:
        value = (
            float(cleaned)
            if real
            else int(cleaned, 0 if cleaned.lower().startswith(("0x", "0b")) else 10)
        )
        return value if math.isfinite(value) else None
    except (ValueError, OverflowError):
        return None


def literal_type(source, real=False):
    if real:
        return (
            "float"
            if source[-1:].lower() == "f"
            else "decimal"
            if source[-1:].lower() == "m"
            else "double"
        )
    value = literal(source)
    if value is None:
        return ""
    suffix = re.search(r"[uUlL]+$", source)
    suffix = suffix[0].lower() if suffix else ""
    candidates = (
        ["ulong"]
        if "u" in suffix and "l" in suffix
        else ["uint", "ulong"]
        if "u" in suffix
        else ["long", "ulong"]
        if "l" in suffix
        else ["int", "uint", "long", "ulong"]
        if source.lower().startswith(("0x", "0b"))
        else ["int", "long", "ulong"]
    )
    return next((kind for kind in candidates if value <= INTEGER_RANGES[kind][1]), "")


def quotient(left, right):
    return (abs(left) // abs(right)) * (-1 if (left < 0) != (right < 0) else 1)


def promoted(left, right):
    if left not in NUMERIC_TYPES or right not in NUMERIC_TYPES:
        return ""
    kinds = {left, right}
    if "decimal" in kinds:
        return "" if kinds & {"float", "double"} else "decimal"
    if "double" in kinds:
        return "double"
    if "float" in kinds:
        return "float"
    if "ulong" in kinds:
        return "" if kinds & {"sbyte", "short", "int", "long"} else "ulong"
    if "long" in kinds:
        return "long"
    if "uint" in kinds:
        return "long" if kinds & {"sbyte", "short", "int"} else "uint"
    return "int"


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
                quotient(left, right)
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
