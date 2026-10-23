"""只读索引 C# 方法与显式参数初值，不执行设备源码或构建脚本。"""

import hashlib
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property

import tree_sitter_c_sharp
from tree_sitter import Language, Parser

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_numbers import (
    NUMERIC_TYPES,
    binary_value,
    coerce,
    literal,
    literal_type,
    promoted,
)


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

    @cached_property
    def namespaces(self):
        result, pending = set(), [self.tree.root_node]
        while pending:
            node = pending.pop()
            if node.type != "using_directive":
                if node.type in {
                    "compilation_unit",
                    "namespace_declaration",
                    "file_scoped_namespace_declaration",
                    "declaration_list",
                }:
                    pending.extend(children(node))
                continue
            found = re.fullmatch(
                r"(?:global\s+)?using\s+((?:global::)?[\w.]+)\s*;", text(node).strip()
            )
            if found is None:
                continue
            imported = found[1].removeprefix("global::")
            result.add(imported)
            if found[1].startswith("global::") or text(node).lstrip().startswith("global "):
                continue
            scopes, parent = [], node.parent
            while parent:
                if parent.type in {"namespace_declaration", "file_scoped_namespace_declaration"}:
                    scopes.append(text(parent.child_by_field_name("name")))
                parent = parent.parent
            if not scopes:
                scopes = [
                    text(part.child_by_field_name("name"))
                    for part in children(self.tree.root_node, "file_scoped_namespace_declaration")
                    if part.start_byte < node.start_byte
                ]
            # namespace AKRS.ZX2200 内的 using Galaxy2... 可以指向
            # AKRS.Galaxy2...；位于该namespace之前的全局using不能这样补前缀。
            parts = ".".join(reversed(scopes)).split(".") if scopes else []
            result.update(
                f"{'.'.join(parts[:length])}.{imported}" for length in range(1, len(parts) + 1)
            )
        return result

    def evidence(self, node):
        key = (node.start_byte, node.end_byte)
        if key not in self.evidence_texts:
            self.evidence_texts[key] = text(node).strip()[:650]
        return {
            "path": self.path,
            "line": node.start_point[0] + 1,
            "version": self.version,
            "code": self.evidence_texts[key],
        }

    @cached_property
    def evidence_texts(self):
        return {}


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
    body_node: object = None
    callable_kind: str = "method"
    is_static: bool = False
    is_virtual: bool = False
    type_scope: tuple = ()
    variadic: bool = False

    @property
    def key(self):
        identity = (
            f"{self.owner}.{self.name}@{self.unit.path}:"
            f"{self.node.start_point[0] + 1}:{self.node.start_byte}"
        )
        return identity + (f":cycle:{self.body_override.start_byte}" if self.body_override else "")

    @property
    def body(self):
        return self.body_override or self.body_node or self.node.child_by_field_name("body")


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
    initializers: list = field(default_factory=list)
    static_members: set = field(default_factory=set)
    member_units: dict = field(default_factory=dict)


class SourceIndex:
    def __init__(self, documents, declaration_sources=()):
        self.classes = {}
        self.units = []
        self.declaration_units = []
        self.notes = []
        self.by_method = defaultdict(list)
        self.type_names = defaultdict(list)
        self.enums = set()
        self._inference_cache = {}
        self._local_definition_cache = {}
        self._inferring = set()
        self._resolution_cache = {}
        self._resolving = set()
        self._source_call_sites = set()
        self._overridden_cache = {}
        self._property_cache = {}
        self._valuing = set()
        self._value_cache = {}
        self._value_contexts = {}
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
        self._generated_fields(declaration_sources)
        self.method_kinds = {
            method.key: method.callable_kind
            for info in self.classes.values()
            for method in info.methods
        }
        fingerprint = "\n".join(
            f"{u.path}:{u.version}" for u in [*self.units, *self.declaration_units]
        )
        self.revision = hashlib.sha256(fingerprint.encode()).hexdigest()

    def _generated_fields(self, sources):
        """Designer只补已存在partial类型的字段声明，不执行布局、初始化和事件挂接。"""
        owners = {
            (info.project, info.namespace, info.short_name): info for info in self.classes.values()
        }
        parser = Parser(Language(tree_sitter_c_sharp.language()))
        for source in sources:
            raw = source["content"].encode("utf-8")
            unit = Unit(
                source["path"],
                raw,
                source["version"],
                parser.parse(raw),
                source.get("project", ""),
                source.get("role", "business"),
            )
            self.declaration_units.append(unit)
            if unit.tree.root_node.has_error:
                self.notes.append(f"{unit.path}：生成字段包含语法错误，相关调用保留未解析")
                continue
            for node in walk(unit.tree.root_node):
                if node.type != "class_declaration":
                    continue
                info = owners.get(
                    (
                        unit.project,
                        self.namespace(node, unit),
                        text(node.child_by_field_name("name")),
                    )
                )
                if info is None:
                    continue
                for member in children(node.child_by_field_name("body"), "field_declaration"):
                    declaration = next(iter(children(member, "variable_declaration")), None)
                    if declaration is None:
                        continue
                    kind = text(declaration.child_by_field_name("type"))
                    static = any(
                        text(part) in {"static", "const"} for part in children(member, "modifier")
                    )
                    for variable in children(declaration, "variable_declarator"):
                        name = text(variable.child_by_field_name("name"))
                        if name in info.types:
                            continue
                        info.types[name] = kind
                        info.member_units[name] = unit
                        if static:
                            info.static_members.add(name)

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
        info.declarations.append((unit, node))
        base = next(iter(children(node, "base_list")), None)
        if base:
            info.bases.extend(text(item) for item in children(base))
        body = node.child_by_field_name("body")
        for member in children(body) if body else []:
            if member.type == "property_declaration":
                member_name = text(member.child_by_field_name("name"))
                info.types[member_name] = text(member.child_by_field_name("type"))
                info.member_units[member_name] = unit
                value = member.child_by_field_name("value")
                if value is not None:
                    info.defaults[member_name] = (unit, value)
                    if value.type != "arrow_expression_clause":
                        self._initializer(info, unit, member, member_name, value)
                property_modifiers = {text(part) for part in children(member, "modifier")}
                if "static" in property_modifiers:
                    info.static_members.add(member_name)
                accessors = children(
                    member.child_by_field_name("accessors"), "accessor_declaration"
                )
                if value is not None and value.type == "arrow_expression_clause":
                    accessors = [member]
                for accessor in accessors:
                    mode = (
                        "get" if accessor == member else text(accessor.child_by_field_name("name"))
                    )
                    if mode not in {"get", "set", "init"}:
                        continue
                    name = "set" if mode == "init" else mode
                    method = self._method(
                        info,
                        unit,
                        accessor,
                        f"{name}_{member_name}",
                        f"property_{name}",
                        value if accessor == member else None,
                    )
                    method.is_static = "static" in property_modifiers
                    method.is_virtual = bool(
                        property_modifiers.intersection({"virtual", "abstract", "override"})
                    )
                    if name == "set":
                        method.parameters = [("value", info.types[member_name], None)]
                        method.types["value"] = info.types[member_name]
            elif member.type == "field_declaration":
                declaration = next(iter(children(member, "variable_declaration")), None)
                if not declaration:
                    continue
                kind = text(declaration.child_by_field_name("type"))
                static = any(
                    text(part) in {"static", "const"} for part in children(member, "modifier")
                )
                for variable in children(declaration, "variable_declarator"):
                    member_name = text(variable.child_by_field_name("name"))
                    info.types[member_name] = kind
                    info.member_units[member_name] = unit
                    if static:
                        info.static_members.add(member_name)
                    value = initializer(variable)
                    if value is not None:
                        info.defaults[member_name] = (unit, value)
                        self._initializer(info, unit, member, member_name, value)
            elif member.type in {"method_declaration", "constructor_declaration"}:
                modifiers = {text(part) for part in children(member, "modifier")}
                method_name = text(member.child_by_field_name("name"))
                if member.type == "constructor_declaration":
                    method_name = ".cctor" if "static" in modifiers else ".ctor"
                self._method(
                    info,
                    unit,
                    member,
                    method_name,
                    "constructor" if member.type == "constructor_declaration" else "method",
                )
            if member.type == "constructor_declaration":
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

    def _method(self, info, unit, node, name, callable_kind="method", body_node=None):
        parameters, variadic = call_args.declared_parameters(node)
        types = {name: kind for name, kind, _ in parameters}
        initializers = {}
        for declaration in walk(body_node or node):
            if declaration.type == "variable_declaration":
                kind = text(declaration.child_by_field_name("type"))
                for variable in children(declaration, "variable_declarator"):
                    variable_name = text(variable.child_by_field_name("name"))
                    types[variable_name] = kind
                    initializers[variable_name] = initializer(variable)
        method = Method(
            info.name,
            name,
            node,
            unit,
            parameters,
            types,
            initializers,
            body_node=body_node,
            callable_kind=callable_kind,
            is_static=any(text(part) == "static" for part in children(node, "modifier")),
            variadic=variadic,
        )
        info.methods.append(method)
        self.by_method[(info.name, name)].append(method)
        return method

    def _initializer(self, info, unit, member, name, value):
        if not any(
            part.type in {"invocation_expression", "object_creation_expression"}
            for part in walk(value)
        ):
            return
        method = self._method(info, unit, member, f".initialize_{name}", "initializer", value)
        method.parameters = []
        info.initializers.append(method)

    def constructor(self, owner, arguments, caller):
        return self.overload(self.by_method.get((owner, ".ctor"), []), arguments, caller)

    def overload(self, methods, arguments, caller):
        if not methods:
            return None
        kinds = [self.infer(argument, caller) for argument in arguments]

        candidates = [
            method
            for method in methods
            if (slots := call_args.plan(method.parameters, arguments, variadic=method.variadic))
            is not None
            and not any(
                (kind == "bool" and expected in NUMERIC_TYPES)
                or (expected == "bool" and kind in NUMERIC_TYPES)
                for kind, slot in zip(kinds, slots, strict=True)
                for expected in [self.lookup_type(method.parameters[slot][1], method)]
            )
        ]
        if len(candidates) > 1:
            exact = [
                method
                for method in candidates
                if all(
                    kind and kind == self.lookup_type(parameter[1], method)
                    for kind, slot in zip(
                        kinds,
                        call_args.plan(method.parameters, arguments, variadic=method.variadic),
                        strict=True,
                    )
                    for parameter in [method.parameters[slot]]
                )
            ]
            if arguments and len(exact) > 1:
                fixed = [method for method in exact if not method.variadic]
                # 同等转换时普通参数优于params展开；正常数组形式仍保留原重载判断。
                if len(fixed) == 1 and all(
                    not call_args.params_normal(self, method, arguments, caller)
                    for method in exact
                    if method.variadic
                ):
                    exact = fixed
            candidates = exact if len(exact) == 1 else candidates
            if len(candidates) > 1:
                from app.modules.action_timing.source_dynamic import prefer_typed_callback

                candidates = prefer_typed_callback(self, candidates, arguments, caller)
        return candidates[0] if len(candidates) == 1 else None

    def property_method(self, owner, name, mode, seen=None):
        if seen is None:
            key = (owner, name, mode)
            if key not in self._property_cache:
                self._property_cache[key] = self.property_method(owner, name, mode, set())
            return self._property_cache[key]
        seen = set() if seen is None else seen
        if owner in seen or owner not in self.classes:
            return None
        seen.add(owner)
        local = self.by_method.get((owner, f"{mode}_{name}"), [])
        if local:
            return local[0]
        return next(
            (
                target
                for base in self.base_types(owner)
                if (target := self.property_method(base, name, mode, seen))
            ),
            None,
        )

    def accessor(self, node, caller, mode, owner=None):
        if node is None:
            return None
        if node.type == "member_access_expression":
            name = text(node.child_by_field_name("name"))
            owner = owner or self.infer(node.child_by_field_name("expression"), caller)
        elif node.type == "identifier":
            name = text(node)
            if not owner and name in caller.types:
                return None
            owner = owner or caller.owner
        else:
            return None
        return self.property_method(owner, name, mode)

    def lookup_type(self, source, context, unit=None):
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
            unit = unit or (
                context.unit if isinstance(context, Method) else info.declarations[0][0]
            )
            imported = [key for key in candidates if self.classes[key].namespace in unit.namespaces]
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
            self.lookup_type(info.types[name], owner, info.member_units.get(name))
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
        if name in info.types:
            # 派生类重写/隐藏了成员；不能越过它套用基类的初始化值。
            return None
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
        info = self.classes.get(owner)
        if (
            info is not None
            and info.short_name == "Signal"
            and info.namespace == "AKRS.Galaxy2.Machine.Models"
            and name == "State"
        ):
            # 工作用的交互信号可被其他线程设置；声明时ReSet不是当前工况。
            # 显式状态写入由state.read优先读取，仍参与当前调用的状态传递。
            return None
        found = self.member_default(owner, name)
        if found is None:
            getter = self.property_method(owner, name, "get")
            return self.returned_value(getter, [], bindings, seen) if getter else None
        owner, (unit, value_node) = found
        identity = (owner, name)
        if identity in seen:
            return None
        declaration = Method(owner, "<initializer>", value_node, unit, [], {})
        context = {
            **{key: value for key, value in bindings.items() if "." in key},
            **state.context(bindings),
            state.THIS: bindings.get(state.THIS),
            state.FRAME: f"field:{bindings.get(state.THIS)}:{owner}.{name}",
        }
        value = self.value(value_node, declaration, context, seen | {identity})
        if (
            self.classes[owner].types.get(name) in {"double", "float", "decimal"}
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            return float(value)
        return state.materialize(value, bindings)

    def infer(self, node, method):
        if node is None:
            return ""
        identity = (method.key, node.type, node.start_byte, node.end_byte, method.type_scope)
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
        if node.type == "await_expression":
            from app.modules.action_timing.source_task_returns import result_type

            return result_type(self, children(node)[-1], method)
        if (
            node.type == "member_access_expression"
            and text(node.child_by_field_name("name")) == "Result"
        ):
            from app.modules.action_timing.source_task_returns import result_type

            result = result_type(self, node.child_by_field_name("expression"), method)
            if result:
                return result
        if node.type == "invocation_expression":
            function = node.child_by_field_name("function")
            if text(function.child_by_field_name("name")) == "GetResult":
                from app.modules.action_timing.source_task_returns import result_type

                result = result_type(self, function.child_by_field_name("expression"), method)
                if result:
                    return result
        if node.type == "cast_expression":
            return self.lookup_type(text(node.child_by_field_name("type")), method)
        if node.type == "parenthesized_expression":
            return self.infer(children(node)[-1], method) if children(node) else ""
        if node.type == "binary_expression":
            operator = text(node.child_by_field_name("operator"))
            left = self.infer(node.child_by_field_name("left"), method)
            right = self.infer(node.child_by_field_name("right"), method)
            if operator in {"+", "-", "*", "/", "%", "&", "|", "^"}:
                return promoted(left, right)
            if operator in {"&&", "||"} and left == right == "bool":
                return "bool"
        if node.type in {"prefix_unary_expression", "postfix_unary_expression"}:
            operand = self.infer(children(node)[-1], method) if children(node) else ""
            if operand in NUMERIC_TYPES:
                if source.strip() in {"-2147483648", "-9223372036854775808"}:
                    return "int" if source.strip() == "-2147483648" else "long"
                if source.startswith(("++", "--")) or node.type == "postfix_unary_expression":
                    return operand
                if operand in {"byte", "sbyte", "short", "ushort", "char"}:
                    return "int"
                if source.startswith("-") and operand == "uint":
                    return "long"
                return "" if source.startswith("-") and operand == "ulong" else operand
            if operand == "bool" and source.startswith("!"):
                return "bool"
        if node.type == "element_access_expression":
            from app.modules.action_timing.source_collections import element_type

            return self.lookup_type(
                element_type(self, node.child_by_field_name("expression"), method), method
            )
        if node.type == "this_expression" or source == "this":
            return method.owner
        if node.type == "base_expression" or source == "base":
            bases = self.base_types(method.owner)
            return bases[0] if len(bases) == 1 else ""
        if node.type == "identifier":
            declared, value_node = self.local_definition(node, method)
            if declared == "var":
                return self.infer(value_node, method)
            return (
                (self.lookup_type(declared, method) if declared else "")
                or self.member_type(method.owner, source)
                or self.lookup_type(source, method)
            )
        if node.type == "object_creation_expression":
            return self.lookup_type(text(node.child_by_field_name("type")), method)
        if node.type == "conditional_access_expression":
            owner = self.infer(node.child_by_field_name("condition"), method)
            binding = next(iter(children(node, "member_binding_expression")), None)
            return (
                self.member_type(owner, text(binding.child_by_field_name("name")))
                if binding
                else ""
            )
        if node.type == "member_access_expression":
            from app.modules.action_timing.source_collections import raw_type

            if raw_type(self, node.child_by_field_name("expression"), method).endswith("]"):
                name = text(node.child_by_field_name("name"))
                if name in {"Length", "Rank"}:
                    return "int"
                if name == "LongLength":
                    return "long"
            owner = self.infer(node.child_by_field_name("expression"), method)
            return self.member_type(
                owner, text(node.child_by_field_name("name"))
            ) or self.lookup_type(source, method)
        if node.type == "invocation_expression":
            function = node.child_by_field_name("function")
            if function.type == "member_access_expression":
                from app.modules.action_timing.source_collections import raw_type

                if raw_type(self, function.child_by_field_name("expression"), method).endswith("]"):
                    name = text(function.child_by_field_name("name"))
                    if name in {"GetLength", "GetUpperBound", "GetLowerBound"}:
                        return "int"
                    if name == "GetLongLength":
                        return "long"
            if text(function).endswith(".GetInstance"):
                return self.lookup_type(text(function.child_by_field_name("expression")), method)
            found = self.resolve(node, method)
            return (
                self.lookup_type(text(found.node.child_by_field_name("returns")), found)
                if found
                else ""
            )
        if node.type == "argument":
            parts = children(node)
            return self.infer(parts[-1], method) if parts else ""
        if node.type in {"integer_literal", "real_literal"}:
            return literal_type(source, node.type == "real_literal")
        return {
            "boolean_literal": "bool",
            "string_literal": "string",
        }.get(node.type, "")

    def local_type(self, node, method):
        return self.local_definition(node, method)[0]

    def local_definition(self, node, method):
        identity = (method.key, node.start_byte, node.end_byte, method.type_scope)
        if identity not in self._local_definition_cache:
            self._local_definition_cache[identity] = self._local_definition(node, method)
        return self._local_definition_cache[identity]

    def _local_definition(self, node, method):
        name = text(node)
        parent = node.parent
        while parent is not None and parent != method.node:
            if parent.type in {"block", "switch_section"}:
                for statement in children(parent, "local_declaration_statement"):
                    declaration = next(iter(children(statement, "variable_declaration")), None)
                    for variable in children(declaration, "variable_declarator"):
                        if text(variable.child_by_field_name("name")) == name:
                            return text(declaration.child_by_field_name("type")), initializer(
                                variable
                            )
            if parent.type in {"foreach_statement", "for_each_statement"}:
                body = parent.child_by_field_name("body")
                variable = parent.child_by_field_name("left")
                if (
                    text(variable) == name
                    and body is not None
                    and (
                        body.start_byte <= node.start_byte < body.end_byte
                        or variable.start_byte <= node.start_byte < variable.end_byte
                    )
                ):
                    for position, kind in reversed(method.type_scope):
                        if position == parent.start_byte:
                            return kind, None
                    kind = text(parent.child_by_field_name("type"))
                    if kind == "var":
                        from app.modules.action_timing.source_collections import element_type

                        return element_type(self, parent.child_by_field_name("right"), method), None
                    return kind, None
            if parent.type == "for_statement":
                for declaration in children(parent, "variable_declaration"):
                    for variable in children(declaration, "variable_declarator"):
                        if text(variable.child_by_field_name("name")) == name:
                            return text(declaration.child_by_field_name("type")), initializer(
                                variable
                            )
            parent = parent.parent
        parameter = next(
            (kind for parameter, kind, _ in method.parameters if parameter == name), None
        )
        if parameter is not None:
            return parameter, None
        if method.callable_kind == "delegate":
            return method.types.get(name, ""), method.initializers.get(name)
        return "", None

    def resolve(self, node, caller):
        identity = (caller.key, node.start_byte, node.end_byte, caller.type_scope)
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

    def has_source_call(self, node, caller):
        self.resolve(node, caller)
        return (caller.key, node.start_byte, node.end_byte) in self._source_call_sites

    def _resolve(self, node, caller):
        function = node.child_by_field_name("function")
        if function is None:
            return None
        if function.type == "conditional_access_expression":
            owner = self.infer(function.child_by_field_name("condition"), caller)
            binding = next(iter(children(function, "member_binding_expression")), None)
            name = text(binding.child_by_field_name("name")) if binding else ""
        elif function.type == "identifier":
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
        if methods:
            self._source_call_sites.add((caller.key, node.start_byte, node.end_byte))
        return self.overload(methods, args, caller)

    def polymorphic(self, node, caller, target):
        modifiers = {text(item) for item in children(target.node, "modifier")}
        if not target.is_virtual and not modifiers.intersection(
            {"virtual", "abstract", "override"}
        ):
            return False
        function = node.child_by_field_name("function") or node
        receiver = function.child_by_field_name("expression")
        if text(receiver) == "base" or (receiver and receiver.type == "object_creation_expression"):
            return False
        if receiver and receiver.type == "identifier":
            created = self.local_definition(receiver, caller)[1]
            if (
                created
                and created.type == "object_creation_expression"
                and self.lookup_type(text(created.child_by_field_name("type")), caller)
                == target.owner
            ):
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
        identity = (method.key, node.type, node.start_byte, node.end_byte)
        cached = (*identity, id(bindings))
        if cached in self._value_cache:
            return self._value_cache[cached]
        if identity in self._valuing:
            return None
        # 一次投影中不会执行写入。只复用相同参数上下文的子表达式，避免沿
        # 多层属性接收者反复展开；跨语句清空，且保留上下文以防Python复用id。
        self._value_contexts[id(bindings)] = bindings
        self._valuing.add(identity)
        try:
            value = self._value(node, method, bindings, seen)
            self._value_cache[cached] = value
            return value
        finally:
            self._valuing.remove(identity)
            if not self._valuing:
                self._value_cache.clear()
                self._value_contexts.clear()

    def _value(self, node, method, bindings, seen=None):
        if node is None:
            return None
        seen = set() if seen is None else seen
        kind, source = node.type, text(node)
        if kind in {
            "prefix_unary_expression",
            "postfix_unary_expression",
            "assignment_expression",
            "element_access_expression",
            "binary_expression",
            "conditional_expression",
            "await_expression",
            "is_pattern_expression",
        }:
            result_key = call_args.return_key(node, method, bindings)
            if result_key in bindings:
                return bindings[result_key]
        if kind == "argument":
            parts = children(node)
            return self.value(parts[-1], method, bindings, seen) if parts else None
        if kind in {"identifier", "member_access_expression"}:
            getter = self.accessor(node, method, "get")
            result_key = call_args.return_key(node, method, bindings)
            if result_key in bindings:
                return state.materialize(
                    coerce(self.infer(node, method), bindings[result_key]), bindings
                )
            current = state.read(self, node, method, bindings)
            if current is not state.MISSING:
                return state.materialize(coerce(self.infer(node, method), current), bindings)
        if source in bindings:
            return state.materialize(bindings[source], bindings)
        if kind in {"integer_literal", "real_literal"}:
            return literal(source, kind == "real_literal")
        if kind == "boolean_literal":
            return source == "true"
        if kind in {
            "array_creation_expression",
            "implicit_array_creation_expression",
            "collection_expression",
        }:
            from app.modules.action_timing.source_collections import created

            return created(self, node, method, bindings)
        if kind == "element_access_expression":
            from app.modules.action_timing.source_collections import item, location

            place = location(self, node, method, bindings)
            return item(*place, bindings) if place is not None else None
        if kind == "identifier":
            if self.local_type(node, method):
                return None
            getter = self.accessor(node, method, "get")
            if getter and self.polymorphic(node, method, getter):
                return None
            return self.default_value(method.owner, source, bindings, seen)
        if kind == "object_creation_expression":
            from app.modules.action_timing.source_collections import created
            from app.modules.action_timing.source_tasks import known_task

            task = bindings.get(call_args.return_key(node, method, bindings))
            if known_task(task):
                return task

            collection = created(self, node, method, bindings)
            if collection is not state.MISSING:
                return collection
            # 仅求值显式对象初始化器；不执行构造函数，也不臆测外部构造参数顺序。
            value_node = next(iter(children(node, "initializer_expression")), None)
            result = {
                "<type>": text(node.child_by_field_name("type")),
                "<ref>": bindings.get(
                    f"<allocation:{bindings.get(state.FRAME)}:{method.unit.path}:{node.start_byte}>",
                    f"new:{bindings.get(state.FRAME)}:{method.unit.path}:{node.start_byte}",
                ),
            }
            owner = self.lookup_type(result["<type>"], method)
            for assignment in children(value_node, "assignment_expression"):
                left = assignment.child_by_field_name("left")
                if left.type == "identifier":
                    member_name = text(left)
                    getter = self.property_method(owner, member_name, "get")
                    setter = self.property_method(owner, member_name, "set")
                    custom = (getter and getter.body is not None) or (
                        setter and setter.body is not None
                    )
                    result[member_name] = (
                        None
                        if custom
                        else self.value(
                            assignment.child_by_field_name("right"), method, bindings, seen
                        )
                    )
                    if custom:
                        result[f"<invalidated:{member_name}>"] = True
            return state.materialize(result, bindings)
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
            getter = self.property_method(owner, name, "get")
            if getter and self.polymorphic(node, method, getter):
                return None
            receiver_value = self.value(
                node.child_by_field_name("expression"), method, bindings, seen
            )
            if name in {"Length", "LongLength", "Count", "Rank"}:
                from app.modules.action_timing.source_collections import known, length

                if known(receiver_value):
                    if name == "Rank":
                        shape = receiver_value.get("<shape>")
                        return len(shape) if shape is not None else None
                    return length(receiver_value, bindings)
            if isinstance(receiver_value, dict) and name in receiver_value:
                if receiver_value.get(f"<invalidated:{name}>"):
                    if getter is None or getter.body is None:
                        return None
                else:
                    return receiver_value[name]
            if simple_type(receiver) in self.enums:
                return name
            context = {
                **bindings,
                state.THIS: state.reference(
                    self, node.child_by_field_name("expression"), method, bindings
                ),
            }
            return self.default_value(owner, name, context, seen)
        if kind == "cast_expression":
            value = self.value(children(node)[-1], method, bindings, seen)
            from app.modules.action_timing.source_delegates import NULL_DELEGATE, BoundDelegate
            from app.modules.action_timing.source_tasks import known_task

            if isinstance(value, BoundDelegate) or value is NULL_DELEGATE or known_task(value):
                return value
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
            return binary_value(op, left, right)
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
            result_key = call_args.return_key(node, method, bindings)
            if result_key in bindings:
                return state.materialize(
                    coerce(self.infer(node, method), bindings[result_key]), bindings
                )
            from app.modules.action_timing.source_collections import range_value

            collection = range_value(self, node, method, bindings)
            if collection is not state.MISSING:
                return collection
            function_node = node.child_by_field_name("function")
            function = text(function_node)
            if function_node.type == "conditional_access_expression":
                receiver = self.value(
                    function_node.child_by_field_name("condition"), method, bindings, seen
                )
                if not isinstance(receiver, dict) or "<type>" not in receiver:
                    return None
            values = call_args.values(self, node, method, bindings, seen)
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
            if target and self.polymorphic(node, method, target):
                return None
            saved = call_args.snapshot(node, method, bindings)
            receiver = saved.receiver if saved is not None else state.MISSING
            context = (
                {
                    **bindings,
                    state.THIS: state.receiver_for(self, target, node, method, bindings)
                    if receiver is state.MISSING
                    else receiver,
                }
                if target
                else bindings
            )
            return self.returned_value(target, values, context, seen, call_args.arguments(node))
        return None

    def returned_value(self, target, values, bindings, seen, argument_nodes=None):
        if target is None or target.body is None or target.variadic:
            return None
        identity = (target.key, "<return>")
        if identity in seen:
            return None
        slots = (
            call_args.plan(target.parameters, argument_nodes)
            if argument_nodes is not None
            else tuple(range(len(values)))
        )
        if slots is None:
            return None
        arguments = {
            name: self.value(default, target, {}, seen) for name, _, default in target.parameters
        }
        arguments.update(
            (target.parameters[slot][0], value) for slot, value in zip(slots, values, strict=True)
        )
        arguments.update({key: value for key, value in bindings.items() if "." in key})
        arguments.update(state.context(bindings))
        arguments[state.THIS] = bindings.get(state.THIS)
        arguments[state.FRAME] = bindings.get(state.FRAME)
        if target.body.type == "arrow_expression_clause":
            return self.value(children(target.body)[-1], target, arguments, seen | {identity})
        statements = children(target.body)
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
        if len(statements) == 1 and statements[0].type == "return_statement":
            returned = children(statements[0])
            return (
                self.value(returned[-1], target, arguments, seen | {identity}) if returned else None
            )
        return None
