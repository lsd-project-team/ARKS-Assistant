"""只读索引 C# 方法与显式参数初值，不执行设备源码或构建脚本。"""

import hashlib
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field

import tree_sitter_c_sharp
from tree_sitter import Language, Parser


def walk(node):
    pending = [node] if node is not None else []
    while pending:
        current = pending.pop()
        yield current
        pending.extend(reversed(current.children))


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
    comment = re.search(r"((?:[ \t]*///[^\n]*\n)+)[ \t]*$", prefix)
    summaries = re.findall(r"<summary>(.*?)</summary>", comment[1], re.S) if comment else []
    return re.sub(r"\s*///\s*|<[^>]+>", "", summaries[-1]).strip() if summaries else ""


@dataclass
class Unit:
    path: str
    raw: bytes
    version: str
    tree: object
    project: str = ""
    role: str = "business"

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
    initializers: dict = field(default_factory=dict)
    body_override: object = None

    @property
    def key(self):
        identity = (
            f"{self.owner}.{self.name}@{self.unit.path}:"
            f"{self.node.start_point[0] + 1}:{self.node.start_byte}"
        )
        return identity + (f":cycle:{self.body_override.start_byte}" if self.body_override else "")

    @property
    def body(self):
        return self.body_override or self.node.child_by_field_name("body")


@dataclass
class ClassInfo:
    name: str
    bases: list = field(default_factory=list)
    methods: list = field(default_factory=list)
    types: dict = field(default_factory=dict)
    defaults: dict = field(default_factory=dict)
    declarations: list = field(default_factory=list)
    namespace: str = ""
    project: str = ""
    short_name: str = ""
    constructor_writes: set = field(default_factory=set)


class SourceIndex:
    def __init__(self, documents):
        self.classes = {}
        self.units = []
        self.notes = []
        self.by_method = defaultdict(list)
        self.type_names = defaultdict(list)
        self.enums = set()
        self._inference_cache = {}
        self._inferring = set()
        self._resolution_cache = {}
        self._resolving = set()
        self._overridden_cache = {}
        for source in documents:
            raw = source["content"].encode("utf-8")
            # 文本、语法树与节点共同保存，避免跨文件持有失效的原生节点。
            parser = Parser(Language(tree_sitter_c_sharp.language()))
            unit = Unit(
                source["path"],
                raw,
                source["version"],
                parser.parse(raw),
                source.get("project", ""),
                source.get("role", "business"),
            )
            self.units.append(unit)
            if unit.tree.root_node.has_error:
                self.notes.append(f"{unit.path}：包含语法错误，相关结果保留未解析标记")
        declarations = defaultdict(list)
        names = defaultdict(set)
        for unit in self.units:
            for node in walk(unit.tree.root_node):
                if node.type == "enum_declaration":
                    self.enums.add(text(node.child_by_field_name("name")))
                if node.type not in {
                    "class_declaration",
                    "struct_declaration",
                    "interface_declaration",
                }:
                    continue
                name = text(node.child_by_field_name("name"))
                namespace = self.namespace(node, unit)
                identity = (unit.project, namespace, name)
                declarations[identity].append((unit, node))
                names[name].add(identity)
        # partial 只在同一工程和命名空间内合并，包与业务代码的同名类不能互相覆盖。
        for (project, namespace, name), nodes in declarations.items():
            key = name if len(names[name]) == 1 else f"{project}::{namespace}.{name}"
            info = ClassInfo(key, namespace=namespace, project=project, short_name=name)
            self.classes[key] = info
            self.type_names[name].append(key)
            for unit, node in nodes:
                self._index(unit, node, info)
        fingerprint = "\n".join(f"{u.path}:{u.version}" for u in self.units)
        self.revision = hashlib.sha256(fingerprint.encode()).hexdigest()

    @staticmethod
    def namespace(node, unit):
        names = []
        current = node.parent
        while current:
            if current.type in {
                "namespace_declaration",
                "file_scoped_namespace_declaration",
                "class_declaration",
            }:
                names.append(text(current.child_by_field_name("name")))
            current = current.parent
        if not names:
            names = [
                text(part.child_by_field_name("name"))
                for part in children(unit.tree.root_node, "file_scoped_namespace_declaration")
            ]
        return ".".join(reversed(names))

    def _index(self, unit, node, info):
        name = info.name
        info.declarations.append((unit, node))
        base = next(iter(children(node, "base_list")), None)
        if base:
            info.bases.extend(text(item) for item in children(base))
        body = node.child_by_field_name("body")
        for member in children(body) if body else []:
            if member.type == "property_declaration":
                member_name = text(member.child_by_field_name("name"))
                info.types[member_name] = text(member.child_by_field_name("type"))
                value = member.child_by_field_name("value")
                if value is not None:
                    info.defaults[member_name] = (unit, value)
            elif member.type == "field_declaration":
                declaration = next(iter(children(member, "variable_declaration")), None)
                if not declaration:
                    continue
                kind = text(declaration.child_by_field_name("type"))
                for variable in children(declaration, "variable_declarator"):
                    member_name = text(variable.child_by_field_name("name"))
                    info.types[member_name] = kind
                    value = initializer(variable)
                    if value is not None:
                        info.defaults[member_name] = (unit, value)
            elif member.type == "method_declaration":
                parameters = []
                for parameter in children(member.child_by_field_name("parameters"), "parameter"):
                    parameters.append(
                        (
                            text(parameter.child_by_field_name("name")),
                            text(parameter.child_by_field_name("type")),
                            initializer(parameter),
                        )
                    )
                types = {name: kind for name, kind, _ in parameters}
                initializers = {}
                for declaration in walk(member):
                    if declaration.type == "variable_declaration":
                        kind = text(declaration.child_by_field_name("type"))
                        for variable in children(declaration, "variable_declarator"):
                            types[text(variable.child_by_field_name("name"))] = kind
                            initializers[text(variable.child_by_field_name("name"))] = initializer(
                                variable
                            )
                method = Method(
                    name,
                    text(member.child_by_field_name("name")),
                    member,
                    unit,
                    parameters,
                    types,
                    initializers,
                )
                info.methods.append(method)
                self.by_method[(name, method.name)].append(method)
            elif member.type == "constructor_declaration":
                for assignment in walk(member.child_by_field_name("body")):
                    if assignment.type != "assignment_expression":
                        continue
                    left = assignment.child_by_field_name("left")
                    if left.type == "identifier":
                        info.constructor_writes.add(text(left))
                    elif left.type == "member_access_expression" and text(
                        left.child_by_field_name("expression")
                    ) in {"this", info.short_name}:
                        info.constructor_writes.add(text(left.child_by_field_name("name")))

    def lookup_type(self, source, context):
        source = source.replace("global::", "").split("<", 1)[0].rstrip("?[]")
        if source in self.classes:
            return source
        info = self.classes.get(context.owner if isinstance(context, Method) else context)
        candidates = self.type_names.get(simple_type(source), [])
        if "." in source:
            candidates = [
                key
                for key in candidates
                if f"{self.classes[key].namespace}.{self.classes[key].short_name}" == source
            ]
        if len(candidates) <= 1:
            return candidates[0] if candidates else source
        if info:
            local = [
                key
                for key in candidates
                if self.classes[key].project == info.project
                and self.classes[key].namespace == info.namespace
            ]
            if len(local) == 1:
                return local[0]
            unit = context.unit if isinstance(context, Method) else info.declarations[0][0]
            usings = {
                text(part).removeprefix("using ").rstrip(";").strip()
                for part in walk(unit.tree.root_node)
                if part.type == "using_directive"
            }
            imported = [key for key in candidates if self.classes[key].namespace in usings]
            if len(imported) == 1:
                return imported[0]
        return ""

    def base_types(self, owner):
        info = self.classes.get(owner)
        return [self.lookup_type(base, owner) for base in info.bases] if info else []

    def member_type(self, owner, name, seen=None):
        seen = set() if seen is None else seen
        if owner in seen or owner not in self.classes:
            return ""
        seen.add(owner)
        info = self.classes[owner]
        return (
            self.lookup_type(info.types[name], owner)
            if name in info.types
            else next(
                (
                    found
                    for base in self.base_types(owner)
                    if (found := self.member_type(base, name, seen))
                ),
                "",
            )
        )

    def member_default(self, owner, name, seen=None):
        seen = set() if seen is None else seen
        if owner in seen or owner not in self.classes:
            return None
        seen.add(owner)
        info = self.classes[owner]
        if name in info.constructor_writes:
            return None
        if name in info.defaults:
            return owner, info.defaults[name]
        return next(
            (
                found
                for base in self.base_types(owner)
                if (found := self.member_default(base, name, seen))
            ),
            None,
        )

    def default_value(self, owner, name, bindings, seen):
        if owner.endswith(("RunTimeProvider", "RuntimeProvider")):
            # 运行中的请求/状态标志不是配方初值，不能用启动时 false 抹掉动作路径。
            return None
        found = self.member_default(owner, name)
        if found is None:
            return None
        owner, (unit, value_node) = found
        identity = (owner, name)
        if identity in seen:
            return None
        declaration = Method(owner, "<initializer>", value_node, unit, [], {})
        context = {key: value for key, value in bindings.items() if "." in key}
        value = self.value(value_node, declaration, context, seen | {identity})
        if (
            self.classes[owner].types.get(name) in {"double", "float", "decimal"}
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            return float(value)
        return value

    def infer(self, node, method):
        if node is None:
            return ""
        identity = (method.key, node.type, node.start_byte, node.end_byte)
        if identity in self._inference_cache:
            return self._inference_cache[identity]
        if identity in self._inferring:
            return ""
        self._inferring.add(identity)
        try:
            value = self._infer(node, method)
            self._inference_cache[identity] = value
            return value
        finally:
            self._inferring.remove(identity)

    def _infer(self, node, method):
        source = text(node)
        if node.type == "this_expression" or source == "this":
            return method.owner
        if node.type == "base_expression" or source == "base":
            bases = self.base_types(method.owner)
            return bases[0] if len(bases) == 1 else ""
        if node.type == "identifier":
            if method.types.get(source) == "var":
                return self.infer(method.initializers.get(source), method)
            return (
                (self.lookup_type(method.types[source], method) if source in method.types else "")
                or self.member_type(method.owner, source)
                or self.lookup_type(source, method)
            )
        if node.type == "object_creation_expression":
            return self.lookup_type(text(node.child_by_field_name("type")), method)
        if node.type == "member_access_expression":
            owner = self.infer(node.child_by_field_name("expression"), method)
            return self.member_type(
                owner, text(node.child_by_field_name("name"))
            ) or self.lookup_type(source, method)
        if node.type == "invocation_expression":
            function = node.child_by_field_name("function")
            if text(function).endswith(".GetInstance"):
                return self.lookup_type(text(function.child_by_field_name("expression")), method)
            found = self.resolve(node, method)
            return (
                self.lookup_type(text(found.node.child_by_field_name("returns")), found)
                if found
                else ""
            )
        if node.type == "argument":
            return self.infer(children(node)[-1], method)
        return {
            "integer_literal": "int",
            "real_literal": "double",
            "boolean_literal": "bool",
            "string_literal": "string",
        }.get(node.type, "")

    def resolve(self, node, caller):
        identity = (caller.owner, caller.unit.path, node.start_byte, node.end_byte)
        if identity in self._resolution_cache:
            return self._resolution_cache[identity]
        if identity in self._resolving:
            return None
        self._resolving.add(identity)
        try:
            result = self._resolve(node, caller)
            self._resolution_cache[identity] = result
            return result
        finally:
            self._resolving.remove(identity)

    def _resolve(self, node, caller):
        function = node.child_by_field_name("function")
        if function is None:
            return None
        if function.type == "identifier":
            owner, name = caller.owner, text(function)
        else:
            owner = self.infer(function.child_by_field_name("expression"), caller)
            name = text(function.child_by_field_name("name"))
        args = children(node.child_by_field_name("arguments"), "argument")
        owners = [owner]
        visited = set()
        methods = []
        signatures = set()
        while owners:
            current = owners.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for method in self.by_method.get((current, name), []):
                signature = tuple(
                    self.lookup_type(kind, method) for _, kind, _ in method.parameters
                )
                if signature not in signatures:
                    methods.append(method)
                    signatures.add(signature)
            owners.extend(self.base_types(current))
        candidates = [
            method
            for method in methods
            if sum(default is None for _, _, default in method.parameters)
            <= len(args)
            <= len(method.parameters)
        ]
        if len(candidates) > 1:
            types = [self.infer(arg, caller) for arg in args]
            exact = [
                candidate
                for candidate in candidates
                if all(
                    kind and kind == self.lookup_type(parameter[1], candidate)
                    for kind, parameter in zip(types, candidate.parameters, strict=False)
                )
            ]
            candidates = exact if len(exact) == 1 else candidates
        return candidates[0] if len(candidates) == 1 else None

    def polymorphic(self, node, caller, target):
        modifiers = {text(item) for item in children(target.node, "modifier")}
        if not modifiers.intersection({"virtual", "abstract", "override"}):
            return False
        receiver = node.child_by_field_name("function").child_by_field_name("expression")
        if text(receiver) == "base" or (receiver and receiver.type == "object_creation_expression"):
            return False
        if receiver and receiver.type == "identifier":
            created = caller.initializers.get(text(receiver))
            if created and created.type == "object_creation_expression":
                return False
        # 无实际实例类型时不能把基类的空实现当成运行时动作。
        identity = (target.owner, target.name)
        if identity not in self._overridden_cache:
            self._overridden_cache[identity] = "abstract" in modifiers or any(
                target.owner in self.base_types(owner) and self.by_method.get((owner, target.name))
                for owner in self.classes
            )
        return self._overridden_cache[identity]

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
            return self.default_value(method.owner, source, bindings, seen)
        if kind == "object_creation_expression":
            # 仅求值显式对象初始化器；不执行构造函数，也不臆测外部构造参数顺序。
            value_node = next(iter(children(node, "initializer_expression")), None)
            if value_node is None:
                return None
            result = {"<type>": text(node.child_by_field_name("type"))}
            for assignment in children(value_node, "assignment_expression"):
                left = assignment.child_by_field_name("left")
                if left.type == "identifier":
                    result[text(left)] = self.value(
                        assignment.child_by_field_name("right"), method, bindings, seen
                    )
            return result
        if kind == "member_access_expression":
            name = text(node.child_by_field_name("name"))
            owner = self.infer(node.child_by_field_name("expression"), method)
            if name == "MachineWorkMode" and simple_type(owner) == "MachineStateModel":
                return "DryCycle"
            if name == "IsDryCycle" and simple_type(owner) == "MachineStateModel":
                return True
            receiver = text(node.child_by_field_name("expression"))
            if receiver.endswith("MachineWorkModeEnum"):
                return name
            identity = f"{simple_type(owner)}.{name}"
            if identity in bindings:
                return bindings[identity]
            receiver_value = self.value(
                node.child_by_field_name("expression"), method, bindings, seen
            )
            if isinstance(receiver_value, dict) and name in receiver_value:
                return receiver_value[name]
            if simple_type(receiver) in self.enums:
                return name
            return self.default_value(owner, name, bindings, seen)
        if kind == "cast_expression":
            value = self.value(children(node)[-1], method, bindings, seen)
            target = text(node.child_by_field_name("type"))
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if target in {"int", "long", "short", "byte"}:
                    return math.trunc(value) if abs(value) <= 2**31 - 1 else None
                if target in {"double", "float", "decimal"}:
                    return float(value)
            return None
        if kind in {
            "parenthesized_expression",
            "argument",
            "constant_pattern",
            "arrow_expression_clause",
        }:
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
            target = self.resolve(node, method)
            identity = (target.key, "<return>") if target else None
            statements = children(target.body) if target and target.body else []
            if (
                len(statements) > 1
                and all(part.type == "expression_statement" for part in statements[:-1])
                and statements[-1].type == "return_statement"
            ):
                returned = children(statements[-1])
                if returned and returned[-1].type in {
                    "integer_literal",
                    "real_literal",
                    "boolean_literal",
                }:
                    statements = statements[-1:]
            if (
                target
                and identity not in seen
                and len(statements) == 1
                and statements[0].type == "return_statement"
            ):
                arguments = {
                    parameter[0]: value
                    for parameter, value in zip(target.parameters, values, strict=False)
                }
                arguments.update({key: value for key, value in bindings.items() if "." in key})
                returned = children(statements[0])
                return (
                    self.value(returned[-1], target, arguments, seen | {identity})
                    if returned
                    else None
                )
        return None
