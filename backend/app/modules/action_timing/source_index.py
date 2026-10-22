"""只读索引 C# 方法与显式参数初值，不执行设备源码或构建脚本。"""

import hashlib
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field

import tree_sitter_c_sharp
from tree_sitter import Language, Parser


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def children(node, kind=None):
    if node is None:
        return []
    return [child for child in node.children if child.is_named and (not kind or child.type == kind)]


def text(node):
    return node.text.decode("utf-8") if node else ""


def initializer(node):
    if node is None:
        return None
    value = node.child_by_field_name("value") or node.child_by_field_name("default")
    if value is not None:
        return value
    after_equal = False
    for child in node.children:
        if child.type == "=":
            after_equal = True
        elif after_equal and child.is_named:
            return child
    return None


def simple_type(value):
    return value.split("<", 1)[0].split(".")[-1].rstrip("?[]")


def description(raw, node):
    prefix = raw[: node.start_byte].decode("utf-8")[-1500:]
    summaries = re.findall(r"<summary>(.*?)</summary>", prefix, re.S)
    return re.sub(r"\s*///\s*|<[^>]+>", "", summaries[-1]).strip() if summaries else ""


@dataclass
class Unit:
    path: str
    raw: bytes
    version: str
    tree: object

    def evidence(self, node):
        return {
            "path": self.path,
            "line": node.start_point[0] + 1,
            "version": self.version,
            "code": text(node).strip()[:650],
        }


@dataclass
class Method:
    owner: str
    name: str
    node: object
    unit: Unit
    parameters: list
    types: dict

    @property
    def key(self):
        return f"{self.owner}.{self.name}@{self.unit.path}:{self.node.start_point[0] + 1}"

    @property
    def body(self):
        return self.node.child_by_field_name("body")


@dataclass
class ClassInfo:
    name: str
    bases: list = field(default_factory=list)
    methods: list = field(default_factory=list)
    types: dict = field(default_factory=dict)
    defaults: dict = field(default_factory=dict)
    declarations: list = field(default_factory=list)


class SourceIndex:
    def __init__(self, documents):
        self.classes = {}
        self.units = []
        self.notes = []
        self.by_method = defaultdict(list)
        for source in documents:
            raw = source["content"].encode("utf-8")
            # 文本、语法树与节点共同保存，避免跨文件持有失效的原生节点。
            parser = Parser(Language(tree_sitter_c_sharp.language()))
            unit = Unit(source["path"], raw, source["version"], parser.parse(raw))
            self.units.append(unit)
            if unit.tree.root_node.has_error:
                self.notes.append(f"{unit.path}：包含语法错误，相关结果保留未解析标记")
            self._index(unit)
        fingerprint = "\n".join(f"{u.path}:{u.version}" for u in self.units)
        self.revision = hashlib.sha256(fingerprint.encode()).hexdigest()

    def _index(self, unit):
        for node in walk(unit.tree.root_node):
            if node.type != "class_declaration":
                continue
            name = text(node.child_by_field_name("name"))
            info = self.classes.setdefault(name, ClassInfo(name))
            info.declarations.append((unit, node))
            base = next(iter(children(node, "base_list")), None)
            if base:
                info.bases.extend(simple_type(text(item)) for item in children(base))
            body = node.child_by_field_name("body")
            for member in children(body) if body else []:
                if member.type == "property_declaration":
                    member_name = text(member.child_by_field_name("name"))
                    info.types[member_name] = simple_type(text(member.child_by_field_name("type")))
                    value = member.child_by_field_name("value")
                    if value is not None:
                        info.defaults[member_name] = (unit, value)
                elif member.type == "field_declaration":
                    declaration = next(iter(children(member, "variable_declaration")), None)
                    if not declaration:
                        continue
                    kind = simple_type(text(declaration.child_by_field_name("type")))
                    for variable in children(declaration, "variable_declarator"):
                        member_name = text(variable.child_by_field_name("name"))
                        info.types[member_name] = kind
                        value = initializer(variable)
                        if value is not None:
                            info.defaults[member_name] = (unit, value)
                elif member.type == "method_declaration":
                    parameters = []
                    for parameter in children(
                        member.child_by_field_name("parameters"), "parameter"
                    ):
                        parameters.append(
                            (
                                text(parameter.child_by_field_name("name")),
                                simple_type(text(parameter.child_by_field_name("type"))),
                                initializer(parameter),
                            )
                        )
                    types = {name: kind for name, kind, _ in parameters}
                    for declaration in walk(member):
                        if declaration.type == "variable_declaration":
                            kind = simple_type(text(declaration.child_by_field_name("type")))
                            for variable in children(declaration, "variable_declarator"):
                                types[text(variable.child_by_field_name("name"))] = kind
                    method = Method(
                        name,
                        text(member.child_by_field_name("name")),
                        member,
                        unit,
                        parameters,
                        types,
                    )
                    info.methods.append(method)
                    self.by_method[(name, method.name)].append(method)

    def member_type(self, owner, name, seen=None):
        seen = set() if seen is None else seen
        if owner in seen or owner not in self.classes:
            return ""
        seen.add(owner)
        info = self.classes[owner]
        return info.types.get(name) or next(
            (found for base in info.bases if (found := self.member_type(base, name, seen))), ""
        )

    def infer(self, node, method):
        if node is None:
            return ""
        source = text(node)
        if node.type == "this_expression" or source == "this":
            return method.owner
        if node.type == "identifier":
            return (
                method.types.get(source)
                or self.member_type(method.owner, source)
                or (source if source in self.classes else "")
            )
        if node.type == "object_creation_expression":
            return simple_type(text(node.child_by_field_name("type")))
        if node.type == "member_access_expression":
            owner = self.infer(node.child_by_field_name("expression"), method)
            return self.member_type(owner, text(node.child_by_field_name("name")))
        if node.type == "invocation_expression":
            function = node.child_by_field_name("function")
            if text(function).endswith(".GetInstance"):
                return simple_type(text(function.child_by_field_name("expression")))
            found = self.resolve(node, method)
            return simple_type(text(found.node.child_by_field_name("returns"))) if found else ""
        return ""

    def resolve(self, node, caller):
        function = node.child_by_field_name("function")
        if function is None:
            return None
        if function.type == "identifier":
            owner, name = caller.owner, text(function)
        else:
            owner = self.infer(function.child_by_field_name("expression"), caller)
            name = text(function.child_by_field_name("name"))
        args = children(node.child_by_field_name("arguments"), "argument")
        candidates = [
            method
            for method in self.by_method.get((owner, name), [])
            if sum(default is None for _, _, default in method.parameters)
            <= len(args)
            <= len(method.parameters)
        ]
        return candidates[0] if len(candidates) == 1 else None

    def value(self, node, method, bindings, seen=None):
        """有限表达式求值；未知保持未知，不用 eval，也不把属性编辑器范围当成初值。"""
        if node is None:
            return None
        seen = set() if seen is None else seen
        kind, source = node.type, text(node)
        if source in bindings:
            return bindings[source]
        if kind in {"integer_literal", "real_literal"}:
            try:
                cleaned = re.sub(r"[dDfFmMuUlL]+$", "", source.replace("_", ""))
                value = int(cleaned, 0) if kind == "integer_literal" else float(cleaned)
                return value if math.isfinite(value) else None
            except ValueError:
                return None
        if kind == "boolean_literal":
            return source == "true"
        if kind == "identifier":
            return bindings.get(source)
        if kind == "member_access_expression":
            name = text(node.child_by_field_name("name"))
            if name == "MachineWorkMode":
                return "DryCycle"
            if name == "IsDryCycle":
                return True
            receiver = text(node.child_by_field_name("expression"))
            if receiver.endswith("MachineWorkModeEnum"):
                return name
            owner = self.infer(node.child_by_field_name("expression"), method)
            identity = (owner, name)
            info = self.classes.get(owner)
            if info and name in info.defaults and identity not in seen:
                value = self.value(info.defaults[name][1], method, bindings, seen | {identity})
                if info.types.get(name) in {"double", "float", "decimal"} and isinstance(
                    value, (int, float)
                ):
                    return float(value)
                return value
        if kind == "cast_expression":
            value = self.value(children(node)[-1], method, bindings, seen)
            target = text(node.child_by_field_name("type"))
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if target in {"int", "long", "short", "byte"}:
                    return math.trunc(value) if abs(value) <= 2**31 - 1 else None
                if target in {"double", "float", "decimal"}:
                    return float(value)
            return None
        if kind in {"parenthesized_expression", "argument", "constant_pattern"}:
            parts = children(node)
            return self.value(parts[-1], method, bindings, seen) if parts else None
        if kind == "prefix_unary_expression":
            operand = children(node)[-1]
            value = self.value(operand, method, bindings, seen)
            if value is not None:
                if source.startswith("!") and isinstance(value, bool):
                    return not value
                if source.startswith("-") and isinstance(value, (int, float)):
                    return -value
        if kind == "binary_expression":
            left = self.value(node.child_by_field_name("left"), method, bindings, seen)
            right = self.value(node.child_by_field_name("right"), method, bindings, seen)
            op = text(node.child_by_field_name("operator"))
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
                return (
                    result
                    if not isinstance(result, (int, float)) or math.isfinite(result)
                    else None
                )
            except (TypeError, ZeroDivisionError, OverflowError):
                return None
        if kind == "conditional_expression":
            condition = self.value(node.child_by_field_name("condition"), method, bindings, seen)
            if isinstance(condition, bool):
                return self.value(
                    node.child_by_field_name("consequence" if condition else "alternative"),
                    method,
                    bindings,
                    seen,
                )
        if kind == "invocation_expression":
            function = text(node.child_by_field_name("function"))
            values = [
                self.value(arg, method, bindings, seen)
                for arg in children(node.child_by_field_name("arguments"), "argument")
            ]
            if values and all(
                isinstance(value, (int, float)) and not isinstance(value, bool) for value in values
            ):
                allowed = {
                    "Math.Max": max,
                    "Math.Min": min,
                    "Math.Abs": lambda args: abs(args[0]),
                    "TimeSpan.FromMilliseconds": lambda args: args[0],
                    "TimeSpan.FromSeconds": lambda args: args[0] * 1000,
                }
                if function in allowed:
                    return allowed[function](values)
        return None
