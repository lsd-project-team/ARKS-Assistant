"""私有操作身份的源码写入摘要；不把未知外部回调当成无副作用。"""

from dataclasses import replace

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_closures as closures
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing import source_dispatch, source_dynamic, source_parallel
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_collections import raw_type
from app.modules.action_timing.source_index import children, simple_type, text


def private_fields(index, owner):
    cache = index.__dict__.setdefault("private_operation_fields", {})
    if owner not in cache:
        result = set()
        info = index.classes.get(owner)
        for _, declaration in info.declarations if info else ():
            for field in children(declaration.child_by_field_name("body")):
                if field.type not in {"field_declaration", "event_field_declaration"}:
                    continue
                modifiers = {text(part) for part in children(field, "modifier")}
                if modifiers & {"public", "protected", "internal", "static"}:
                    continue
                variable = next(iter(children(field, "variable_declaration")), None)
                result.update(
                    text(part.child_by_field_name("name"))
                    for part in children(variable, "variable_declarator")
                )
        cache[owner] = frozenset(result)
    return cache[owner]


def private_controls(index, owner):
    cache = index.__dict__.setdefault("private_control_fields", {})
    if owner not in cache:
        cache[owner] = frozenset(
            name
            for name in private_fields(index, owner)
            if delegates.signature_arity(index.member_type(owner, name)) is not None
            or simple_type(index.member_type(owner, name))
            in {"Delegate", "MulticastDelegate", "IAsyncResult", "Task"}
        )
    return cache[owner]


class Effects:
    def __init__(self, index, names, owners):
        self.index, self.names, self.owners = index, names, owners
        self.pending, self.seen = [], set()
        self.writes, self.opaque, self.ends = set(), [], False
        self.callback_environments = {}
        self.constructed = set()

    def callback_key(self, value, depth=0):
        if value is delegates.NULL_DELEGATE:
            return ("null",)
        if not isinstance(value, delegates.BoundDelegate):
            return ("unknown",)
        if depth >= 8:
            self.opaque.append("回调环境摘要达到边界")
            return ("boundary",)
        if value.targets:
            return (
                "multicast",
                tuple(self.callback_key(target, depth + 1) for target in value.targets),
            )
        environment = self.callback_environments.get(id(value), (None, {}))[1]
        return (
            value.method_key,
            value.node.start_byte,
            value.node.end_byte,
            value.signature,
            value.arity,
            id(value.closure.functions)
            if value.node.type in {"local_function_statement", "local_function_declaration"}
            else None,
            tuple(
                sorted(
                    (name, self.callback_key(part, depth + 1)) for name, part in environment.items()
                )
            ),
        )

    def add_method(self, method, environment=None):
        if method.body is not None:
            environment = {
                name: None if source_dispatch.reassigned(method, name) else value
                for name, value in (environment or {}).items()
            }
            self.pending.append((method, environment))
            if method.callable_kind == "constructor":
                self.add_construction(method.owner)
        elif method.callable_kind not in {"property_get", "property_set"}:
            self.opaque.append(method.key)

    def add_construction(self, owner):
        if owner in self.constructed or owner not in self.index.classes:
            return
        self.constructed.add(owner)
        info = self.index.classes[owner]
        for initializer in info.initializers:
            self.add_method(initializer)
        # 写入摘要覆盖全部源码构造候选；不把未知构造链选成无副作用。
        for constructor in self.index.by_method.get((owner, ".ctor"), ()):
            self.add_method(constructor)
        for base in self.index.base_types(owner):
            self.add_construction(base)

    def implementations(self, node, caller, target):
        if not self.index.polymorphic(node, caller, target):
            return [target]
        # 写入分析只求所有可能写入的并集，不替实际执行选择某个override。
        # 同名同参数数的源码实现是保守超集，未知/无正文的出口仍保持未定。
        possible = [
            method
            for (_, name), methods in self.index.by_method.items()
            if name == target.name
            for method in methods
            if len(method.parameters) == len(target.parameters) and method.body is not None
        ]
        if not possible:
            self.opaque.append("动态实现尚未绑定:" + target.key)
        return possible

    def add_callback(self, bound):
        if bound is delegates.NULL_DELEGATE:
            return
        if not isinstance(bound, delegates.BoundDelegate):
            self.opaque.append("回调目标未确定")
            return
        if bound.targets:
            for target in bound.targets:
                self.callback_environments.setdefault(
                    id(target), (target, self.callback_environments.get(id(bound), (None, {}))[1])
                )
                self.add_callback(target)
            return
        node, method = bound.node, bound.closure.method
        if node.type not in {"lambda_expression", "anonymous_method_expression"}:
            target = delegates.method_group(self.index, node, method, bound.arity)
            if target is None:
                self.opaque.append(text(node))
            else:
                for implementation in self.implementations(node, method, target):
                    self.add_method(
                        implementation,
                        self.callback_environments.get(id(bound), (None, {}))[1]
                        if node.type in {"local_function_statement", "local_function_declaration"}
                        else None,
                    )
            return
        shape = source_dynamic.signature(self.index, bound.signature, method)
        parameters = closures.parameters(node)
        types = dict(method.types)
        for number, (name, kind, _) in enumerate(parameters):
            types[name] = shape[0][number] if shape and number < len(shape[0]) else kind
        parameters = [(name, types[name], default) for name, _, default in parameters]
        from app.modules.action_timing.source_local_functions import declared_locals

        local_types, local_values = declared_locals(node)
        types = {**types, **local_types}
        self.add_method(
            replace(
                method,
                node=node,
                body_node=node.child_by_field_name("body"),
                name=f"<private-effect:{node.start_byte}>",
                callable_kind="delegate",
                body_override=None,
                parameters=parameters,
                types=types,
                initializers={**method.initializers, **local_values},
            ),
            self.callback_environments.get(id(bound), (None, {}))[1],
        )

    def callback(self, node, method, environment, kind=""):
        value = source_dynamic.unwrapped(node)
        kind = kind or source_dynamic.explicit_signature(self.index, value, method)
        while value is not None and value.type in {"cast_expression", "object_creation_expression"}:
            if value.type == "cast_expression":
                value = source_dynamic.unwrapped(value.child_by_field_name("value"))
            elif source_dynamic.signature(
                self.index, text(value.child_by_field_name("type")), method
            ):
                parts = call_args.arguments(value)
                value = source_dynamic.unwrapped(parts[0]) if len(parts) == 1 else None
            else:
                break
        if value is not None and value.type == "identifier" and text(value) in environment:
            return environment[text(value)]
        if value is not None and value.type == "identifier":
            if source_dispatch.reassigned(method, text(value)):
                return None
            _, initial = self.index.local_definition(value, method)
            if initial is not None:
                return self.callback(initial, method, environment, kind)
        if value is not None and value.type in {"identifier", "member_access_expression"}:
            if (
                delegates.method_group(
                    self.index, value, method, delegates.signature_arity(kind) or 0
                )
                is None
            ):
                return None
        if value is None or value.type not in {
            "identifier",
            "member_access_expression",
            "lambda_expression",
            "anonymous_method_expression",
            "null_literal",
        }:
            return None
        result = delegates.capture(
            self.index,
            value,
            method,
            environment,
            delegates.signature_arity(kind) or 0,
            signature_kind=kind,
        )
        if (
            isinstance(result, delegates.BoundDelegate)
            and id(result) not in self.callback_environments
            and not any(result is part for part in environment.values())
        ):
            self.callback_environments[id(result)] = (result, dict(environment))
        return result

    def call_method(self, target, node, caller, environment):
        nodes = call_args.arguments(node)
        slots = call_args.plan(target.parameters, nodes, variadic=target.variadic)
        if slots is None:
            self.opaque.append(target.key)
            return
        forwarded = {}
        for position, slot in enumerate(slots):
            name, kind, _ = target.parameters[slot]
            if (
                self.root_object(nodes[position], caller)
                and self.index.lookup_type(kind, target) not in self.owners
            ):
                self.opaque.append("所属对象经擦除类型的源码参数逃逸:" + target.key)
            if delegates.signature_arity(kind) is not None or simple_type(kind) in {
                "Delegate",
                "MulticastDelegate",
            }:
                forwarded[name] = self.callback(nodes[position], caller, environment, kind)
        self.add_method(target, forwarded)

    def write(self, node):
        name = (
            text(node.child_by_field_name("name"))
            if node is not None and node.type == "member_access_expression"
            else text(node)
        )
        if name in self.names:
            self.writes.add(name)

    def root_object(self, node, method, seen=None):
        value = source_dynamic.unwrapped(node)
        if value is None:
            return False
        if self.index.infer(value, method) in self.owners or (
            text(value) in {"this", "base"} and method.owner in self.owners
        ):
            return True
        if value.type == "cast_expression":
            return self.root_object(value.child_by_field_name("value"), method, seen)
        if value.type == "identifier":
            seen = set() if seen is None else seen
            name = text(value)
            if name not in seen:
                seen.add(name)
                _, initial = self.index.local_definition(value, method)
                return initial is not None and self.root_object(initial, method, seen)
        return False

    def invocation(self, node, method, environment):
        receiver, name = source_dispatch.function_parts(node)
        arguments = call_args.arguments(node)
        if name == "EndInvoke":
            self.ends = True
        for _, argument in state.byref_arguments(node):
            self.write(state.argument_target(argument))
        target = self.index.resolve(node, method)
        if target is not None:
            for implementation in self.implementations(node, method, target):
                self.call_method(implementation, node, method, environment)
            return
        dispatch = source_dispatch.callback_position(self.index, node, method)
        if dispatch is not None:
            self.add_callback(self.callback(arguments[dispatch[1]], method, environment))
            return
        if name == "BeginInvoke":
            self.add_callback(
                self.callback(receiver, method, environment, raw_type(self.index, receiver, method))
            )
            # 非null的完成回调也可能写私有字段；未绑定时不能假定无副作用。
            if len(arguments) >= 2 and text(source_dynamic.unwrapped(arguments[-2])) != "null":
                self.add_callback(self.callback(arguments[-2], method, environment))
            return
        function = text(node.child_by_field_name("function")).removeprefix(
            "System.Threading.Tasks."
        )
        if function in {"Task.Run", "Task.Factory.StartNew"} or source_parallel.operation(
            self.index, node, method
        ):
            if arguments:
                self.add_callback(
                    self.callback(
                        arguments[-1] if "ForEach" in function else arguments[0],
                        method,
                        environment,
                    )
                )
            else:
                self.opaque.append(function)
            return
        invoked = delegates.invocation_receiver(
            self.index, node, method
        ) or source_dynamic.receiver(node)
        if invoked is not None and (
            delegates.typed_invocation(self.index, node, method)
            or source_dynamic.operation(self.index, node, method)
        ):
            callback = self.callback(invoked, method, environment)
            if callback is None:
                from app.modules.action_timing.source_delegate_writes import possible_methods

                possible = possible_methods(self.index, invoked, method)
                if possible is not None:
                    for target in possible:
                        self.call_method(target, node, method, environment)
                    return
            self.add_callback(callback)
            return
        if name in {
            "Invoke",
            "DynamicInvoke",
            "InvokeMember",
            "CreateInstance",
            "GetProperties",
            "GetFields",
            "GetValue",
            "SetValue",
            "Compile",
        }:
            self.opaque.append("未绑定派发:" + text(node))
            return
        if self.index.has_source_call(node, method):
            possible = [
                item
                for (_, method_name), methods in self.index.by_method.items()
                if method_name == name
                for item in methods
                if call_args.plan(item.parameters, arguments, variadic=item.variadic) is not None
            ]
            if not possible:
                self.opaque.append(text(node))
            for item in possible:
                self.call_method(item, node, method, environment)
            return
        if node.child_by_field_name("function").type == "identifier":
            self.opaque.append("未绑定本地调用:" + text(node))
        if name == "GetInstance" and not arguments:
            return  # 沿用现有模型的单例身份查找；不执行工厂或重置已有对象。
        if not raw_type(self.index, receiver, method):
            possible = [
                item
                for (_, method_name), methods in self.index.by_method.items()
                if method_name == name
                for item in methods
                if call_args.plan(item.parameters, arguments, variadic=item.variadic) is not None
            ]
            for item in possible:
                self.call_method(item, node, method, environment)
        if any(self.root_object(arg, method) for arg in arguments):
            self.opaque.append("私有状态所属对象传入外部:" + text(node))
        if self.root_object(receiver, method):
            self.opaque.append("所属对象的外部调用:" + text(node))
        for argument in arguments:
            value = source_dynamic.unwrapped(argument)
            kind = raw_type(self.index, value, method)
            if (
                value is not None
                and value.type in {"lambda_expression", "anonymous_method_expression"}
            ) or delegates.signature_arity(kind) is not None:
                self.add_callback(self.callback(argument, method, environment, kind))

    def run(self, bound, environment=None, *, method_target=False):
        if method_target:
            self.add_method(bound, environment)
        else:
            if isinstance(bound, delegates.BoundDelegate):
                self.callback_environments[id(bound)] = (bound, environment or {})
            self.add_callback(bound)
        while self.pending and len(self.seen) < 1500:
            method, environment = self.pending.pop()
            key = (
                method.key,
                tuple(
                    sorted((name, self.callback_key(value)) for name, value in environment.items())
                ),
            )
            if key in self.seen:
                continue
            self.seen.add(key)
            pending = [method.body]
            if method.callable_kind == "constructor":
                pending.extend(children(method.node, "constructor_initializer"))
            while pending:
                node = pending.pop()
                if node is None or node.type in {
                    "lambda_expression",
                    "anonymous_method_expression",
                    "local_function_statement",
                    "local_function_declaration",
                }:
                    continue
                if node.type == "assignment_expression":
                    left = node.child_by_field_name("left")
                    self.write(left)
                    setter = self.index.accessor(left, method, "set")
                    if setter:
                        for implementation in self.implementations(left, method, setter):
                            self.add_method(implementation)
                    if self.root_object(node.child_by_field_name("right"), method):
                        self.opaque.append("私有状态所属对象经赋值逃逸")
                elif node.type in {"prefix_unary_expression", "postfix_unary_expression"}:
                    self.write(node.child_by_field_name("operand"))
                elif node.type == "invocation_expression":
                    self.invocation(node, method, environment)
                elif node.type in {"member_access_expression", "identifier"}:
                    getter = self.index.accessor(node, method, "get")
                    if getter:
                        for implementation in self.implementations(node, method, getter):
                            self.add_method(implementation)
                elif node.type == "object_creation_expression":
                    kind = self.index.lookup_type(text(node.child_by_field_name("type")), method)
                    self.add_construction(kind)
                    target = self.index.constructor(kind, call_args.arguments(node), method)
                    if target:
                        self.call_method(target, node, method, environment)
                    elif any(self.root_object(arg, method) for arg in call_args.arguments(node)):
                        self.opaque.append("所属对象传入外部构造:" + text(node))
                elif node.type == "return_statement":
                    if any(self.root_object(part, method) for part in node.children):
                        self.opaque.append("私有状态所属对象经返回值逃逸")
                if node.type in {
                    "interpolation",
                    "binary_expression",
                    "cast_expression",
                    "prefix_unary_expression",
                    "postfix_unary_expression",
                    "assignment_expression",
                }:
                    for part in node.children:
                        kind = (
                            method.owner
                            if text(part) in {"this", "base"}
                            else self.index.infer(part, method)
                        )
                        info = self.index.classes.get(kind)
                        if info is None:
                            continue
                        formatting = node.type == "interpolation" or (
                            node.type == "binary_expression"
                            and text(node.child_by_field_name("operator")) == "+"
                            and any(
                                self.index.infer(term, method) == "string"
                                for term in children(node)
                            )
                        )
                        operators = any(
                            item.type in {"operator_declaration", "conversion_operator_declaration"}
                            for _, declaration in info.declarations
                            for item in children(declaration.child_by_field_name("body"))
                        )
                        if formatting or operators:
                            self.opaque.append("未绑定的源码格式化/运算符:" + text(node))
                pending.extend(children(node))
        if self.pending:
            self.opaque.append("私有写入摘要达到边界")
        return self


def preserve(index, bindings, is_handle):
    from app.modules.action_timing.source_private_state import may_end, unsafe

    candidates = {}
    for key, value in bindings.items():
        if key.startswith(state.PREFIX) and (
            isinstance(value, delegates.BoundDelegate) or is_handle(value)
        ):
            reference, owner, name = key[len(state.PREFIX) : -1].rsplit("|", 2)
            if name in private_controls(index, owner) and not unsafe(
                index, (reference, owner, name), bindings
            ):
                unstable = bindings.get(state.UNSTABLE, ()) or ()
                if not {key, state.key((None, owner, name)), state.object_marker(reference)} & set(
                    unstable
                ):
                    candidates[key] = (value, owner, name)
    if not candidates:
        return {}
    result = {key: value for key, (value, _, _) in candidates.items()}
    for value, owner, _ in candidates.values():
        if (
            is_handle(value)
            and value.end_marker in bindings
            and not may_end(index, owner, bindings)
        ):
            result[value.end_marker] = bindings[value.end_marker]
    return result
