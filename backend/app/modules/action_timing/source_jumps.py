"""块内标签控制流；跳转携带对应状态，不能顺序执行其后的不可达语句。"""

from collections import deque

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import ZERO, Cost, Flow, add, choice
from app.modules.action_timing.source_index import children, text
from app.modules.action_timing.source_tasks import CLOCK

MAX_JUMPS = 32
MAX_GRAPH_STEPS = 512


def observable(bindings):
    """比较会影响后续源码的状态，忽略时钟及单次表达式求值缓存。"""
    prefixes = (
        state.PREFIX,
        state.LOCAL_PREFIX,
        state.COLLECTION_PREFIX,
        "<task",
        "<delegate",
    )
    return {
        key: value
        for key, value in bindings.items()
        if not key.startswith("<") or key.startswith(prefixes)
    }


def labels(node, method):
    result = {}
    for position, statement in enumerate(children(node)):
        current = statement
        while current is not None and current.type == "labeled_statement":
            name = next(iter(children(current, "identifier")), None)
            if name is not None:
                result[f"goto:{method.key}:{current.start_byte}"] = (position, text(name), current)
            current = next((n for n in children(current) if n.type.endswith("_statement")), None)
    return result


def target(node, method):
    if any(n.type in {"case", "default"} for n in node.children):
        return None
    name = next(iter(children(node, "identifier")), None)
    parent = node.parent
    while parent is not None:
        if parent.type in {"block", "switch_section"}:
            for key, (_, candidate, _) in labels(parent, method).items():
                if candidate == text(name):
                    return key
        if parent == method.body or parent == method.node:
            break
        parent = parent.parent
    return None


def transfer(estimator, node, method, bindings, conditions, background):
    destination = target(node, method)
    if destination is None:
        estimator.truncated = True
        estimator.record(
            "unresolved", "跳转目标不在已解析标签作用域内", node, method, conditions, background
        )
        destination = f"unbound-goto:{method.key}:{node.start_byte}"
    return Flow(None, None, jumps={destination: ZERO}).with_state(destination, bindings)


def labeled_body(node):
    return next((n for n in children(node) if n.type.endswith("_statement")), None)


def exits(node, method):
    """保守控制图：仅在所有可能路径均困于本地标签时证明没有正常出口。"""
    if node is None:
        return {"<next>"}
    if node.type == "labeled_statement":
        return exits(labeled_body(node), method)
    if node.type in {"block", "switch_section"}:
        result = {"<next>"}
        for child in children(node):
            if "<next>" not in result:
                break
            result = (result - {"<next>"}) | exits(child, method)
        return result
    if node.type == "if_statement":
        return exits(node.child_by_field_name("consequence"), method) | exits(
            node.child_by_field_name("alternative"), method
        )
    if node.type == "goto_statement":
        return {target(node, method) or "<exit>"}
    if node.type == "throw_statement":
        return set()
    if node.type in {"return_statement", "break_statement", "continue_statement"}:
        return {"<exit>"}
    if node.type in {"expression_statement", "local_declaration_statement", "empty_statement"}:
        return {"<next>"}
    # 循环、异常恢复和未支持的语法可能带有出口；不能据此证明无限重试。
    return {"<next>", "<exit>"}


def can_leave(statements, position, table, method):
    pending, visited = [position], set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        if current == len(statements):
            return True
        visited.add(current)
        for outgoing in exits(statements[current], method):
            if outgoing == "<next>":
                pending.append(current + 1)
            elif outgoing in table:
                pending.append(table[outgoing][0])
            else:
                return True
    return False


def limited_exit(estimator, statements, position, table, method, scope, elapsed, result, completed):
    estimator.truncated = True
    if not can_leave(statements, position, table, method):
        estimator.failure_reasons.append("标签循环没有正常出口")
        return
    for key in list(scope):
        if not key.startswith("<") or key.startswith(
            (state.PREFIX, state.LOCAL_PREFIX, state.COLLECTION_PREFIX)
        ):
            scope[key] = None
    result.live = choice(result.live, Cost(elapsed.lower, None))
    completed.append(scope)


def sequence(estimator, node, method, bindings, stack, conditions, background):
    table = labels(node, method)
    statements = children(node)
    started = bindings.get(CLOCK, ZERO)
    queue = deque([(0, ZERO, dict(bindings), 0, {}, frozenset())])
    result = Flow(None, None)
    completed = []
    jumps = 0
    graph_steps = 0
    limited = False
    shared_limit_recorded = False
    resource_limit = None
    while queue:
        position, elapsed, scope, hops, history, widened = queue.popleft()
        while position < len(statements):
            estimator.jump_steps += 1
            graph_steps += 1
            if graph_steps > MAX_GRAPH_STEPS or hops > MAX_JUMPS:
                limited = True
                resource_limit = {
                    "kind": "control_graph",
                    "target": method.key,
                    "used": graph_steps if graph_steps > MAX_GRAPH_STEPS else hops,
                    "limit": MAX_GRAPH_STEPS if graph_steps > MAX_GRAPH_STEPS else MAX_JUMPS,
                }
                limited_exit(
                    estimator,
                    statements,
                    position,
                    table,
                    method,
                    scope,
                    elapsed,
                    result,
                    completed,
                )
                break
            scope[CLOCK] = started.plus(elapsed)
            part = estimator.block(
                statements[position], method, scope, stack, conditions, background
            )
            terminal = Flow(
                None,
                add(elapsed, part.returned),
                add(elapsed, part.broken),
                add(elapsed, part.continued),
                states={key: value for key, value in part.states.items() if key not in part.jumps},
            )
            result = result.merge(terminal)
            for key, cost in part.jumps.items():
                value = add(elapsed, cost)
                context = dict(part.states.get(key, scope))
                if key in table:
                    jumps += 1
                    if key in widened:
                        continue
                    snapshot = observable(context)
                    previous = history.get(key)
                    next_history = {**history, key: (snapshot, value)}
                    next_widened = widened
                    if previous is not None and previous[0] == snapshot:
                        limited = True
                        if not can_leave(statements, table[key][0], table, method):
                            estimator.failure_reasons.append("标签循环没有正常出口")
                            continue
                        # 同一抽象状态再次回到入口，不展开任意32次。再走一轮
                        # 实际出口以保留后续写入，并让重复的时间上界保持未定。
                        earlier = previous[1]
                        if (
                            value.upper is None
                            or earlier.upper is None
                            or value.upper > earlier.upper
                            or value.lower > earlier.lower
                        ):
                            value = Cost(value.lower, None)
                        next_widened = widened | {key}
                    if estimator.jump_budget.exhausted():
                        limited = True
                        resource_limit = {
                            "kind": "jump_budget",
                            "target": method.key,
                            "used": estimator.jump_budget.used,
                            "limit": estimator.jump_budget.limit,
                        }
                        limited_exit(
                            estimator,
                            statements,
                            table[key][0],
                            table,
                            method,
                            context,
                            value,
                            result,
                            completed,
                        )
                        if not shared_limit_recorded:
                            estimator.record(
                                "unresolved",
                                "标签跳转达到共享展开边界",
                                node,
                                method,
                                conditions,
                                background,
                                analysis_limit=resource_limit,
                            )
                            shared_limit_recorded = True
                        continue
                    estimator.jump_budget.consume()
                    queue.append(
                        (table[key][0], value, context, hops + 1, next_history, next_widened)
                    )
                else:
                    outgoing = Flow(None, None, jumps={key: value}).with_state(key, context)
                    result = result.merge(outgoing)
            if part.live is None:
                break
            elapsed = elapsed.plus(part.live)
            position += 1
        else:
            result.live = choice(result.live, elapsed)
            completed.append(dict(scope))
    if completed:
        state.merge(bindings, completed)
    bindings[CLOCK] = started
    if jumps or resource_limit:
        estimator.record(
            "loop",
            "标签重试剩余次数未定" if limited else "标签跳转已按实际路径展开",
            node,
            method,
            conditions,
            background,
            iterations=None,
            bounded=not limited,
            expanded_iterations=jumps,
            **({"analysis_limit": resource_limit} if resource_limit else {}),
            label_names=[info[1] for info in table.values()],
        )
    return result
