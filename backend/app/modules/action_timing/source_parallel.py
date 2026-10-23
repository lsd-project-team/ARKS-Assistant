"""Parallel.ForEach的完成边界；并行上限不作为实际同时启动的线程数。"""

from copy import copy

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Cost
from app.modules.action_timing.source_index import children, simple_type, text, walk
from app.modules.action_timing.source_tasks import task_ids

MAX_PARALLEL_ITEMS = 128
MAX_SHARED_ROUNDS = 16


def operation(index, node, method):
    function = node.child_by_field_name("function")
    if text(function).removeprefix("System.Threading.Tasks.") != "Parallel.ForEach":
        return False
    receiver = text(function.child_by_field_name("expression"))
    if receiver == "Parallel" and (
        receiver in method.types or index.member_type(method.owner, receiver)
    ):
        return False
    kind = index.lookup_type(receiver, method)
    return kind not in index.classes and kind in {"Parallel", "System.Threading.Tasks.Parallel"}


def callback(index, node, method, bindings):
    unwrapped = delegates.unwrap(index, node, method, bindings)
    if isinstance(unwrapped, delegates.BoundDelegate):
        return unwrapped
    if unwrapped is None:
        return None
    if unwrapped.type in {"lambda_expression", "anonymous_method_expression"}:
        return delegates.capture(
            index, node, method, bindings, returns_task=False, discards_result=True
        )
    candidates = [
        delegates.capture(
            index, node, method, bindings, arity=arity, returns_task=False, discards_result=True
        )
        for arity in (1, 2, 3)
    ]
    candidates = [bound for bound in candidates if isinstance(bound, delegates.BoundDelegate)]
    return candidates[0] if len(candidates) == 1 else None


def options(index, node, value, method, bindings):
    if node is None:
        return None, False
    if (
        not isinstance(value, dict)
        or simple_type(value.get("<type>", "")) != "ParallelOptions"
        or index.lookup_type(value.get("<type>", ""), method) in index.classes
    ):
        return None, True
    value = state.materialize(value, bindings)
    degree = value.get("MaxDegreeOfParallelism", -1)
    invalid = not isinstance(degree, int) or isinstance(degree, bool) or degree == 0 or degree < -1
    configured = (
        set(value) - {name for name in value if name.startswith("<")} - {"MaxDegreeOfParallelism"}
    )
    # 取消令牌/自定义调度器没有源码可证明的完成时间。
    uncertain = invalid or bool(configured)
    return (degree if not invalid and degree > 0 else None), uncertain


def probe_estimator(estimator):
    result = copy(estimator)
    result.stages, result.parameters = [], {}
    result.skip_conditions, result.failure_reasons = [], []
    return result


def private_sites(index, bound):
    method = bound.closure.method
    node = bound.node
    if node.type not in {"lambda_expression", "anonymous_method_expression"}:
        method = delegates.method_group(index, node, method, bound.arity)
        node = method.body if method else None
    return (
        {
            f":{method.unit.path}:{part.start_byte}:"
            for part in walk(node)
            if part.type == "object_creation_expression" or part.type in collections.ARRAYS
        }
        if method
        else set()
    )


def reference_values(value, depth=0):
    if depth > 16:
        return set()
    if isinstance(value, dict):
        found = {value["<ref>"]} if value.get("<ref>") is not None else set()
        for part in value.values():
            found.update(reference_values(part, depth + 1))
        return found
    if isinstance(value, (tuple, list)):
        return set().union(*(reference_values(part, depth + 1) for part in value))
    return set()


def private_receiver(key, private, allocation_floor):
    prefix = state.PREFIX if key.startswith(state.PREFIX) else state.COLLECTION_PREFIX
    receiver = key.removeprefix(prefix).split("|", 1)[0]
    return (
        receiver.startswith(("new:", "collection:")) and any(site in receiver for site in private)
    ) or (
        receiver.startswith("array-copy:")
        and receiver.removeprefix("array-copy:").isdigit()
        and int(receiver.removeprefix("array-copy:")) > allocation_floor
    )


def shared_changes(before, after, private, allocation_floor):
    result = set()
    for key, value in state.context(after).items():
        if key == state.UNSTABLE or (key in before and value == before[key]):
            continue
        if key.startswith(state.LOCAL_PREFIX) and key not in before:
            continue  # 每次callback新建的局部闭包槽不跨迭代共享。
        receiver = key.split("|", 1)[0]
        if "parallel-state:" in receiver or private_receiver(key, private, allocation_floor):
            continue
        result.add(key)
        result.update(state.object_marker(ref) for ref in reference_values(value))
    return result


def run_item(
    estimator,
    bound,
    method,
    bindings,
    stack,
    conditions,
    background,
    value,
    position,
    kind,
    loop_ref,
):
    values = (
        value,
        {"<type>": "System.Threading.Tasks.ParallelLoopState", "<ref>": loop_ref},
        position,
    )
    types = (kind, "System.Threading.Tasks.ParallelLoopState", "long")
    scope = dict(bindings)
    cost = delegates.execute(
        estimator,
        bound,
        method,
        scope,
        stack,
        conditions,
        background,
        join_result=False,
        argument_values=values[: bound.arity],
        argument_types=types[: bound.arity],
    )
    return cost, scope


def invalidate_unexplored(bindings, depth=0):
    """共享写入分析未收敛时，不让旧成员/集合/任务值继续提供固定毫秒数。"""
    from app.modules.action_timing.source_tasks import known_task

    values = list(bindings.values())
    bindings.update(
        {
            key: None
            for key in state.context(bindings)
            if key not in {state.UNSTABLE, state.UNKNOWN_MEMBERS}
        }
    )
    bindings[state.UNKNOWN_MEMBERS] = True
    for key, value in list(bindings.items()):
        if known_task(value) or key.startswith(delegates.DELEGATE_PREFIX):
            bindings[key] = None

    def clear_collections(value, depth):
        if depth > 16:
            return
        if collections.known(value):
            collections.invalidate(value, bindings)
        parts = (
            value.values()
            if isinstance(value, dict)
            else value
            if isinstance(value, (tuple, list))
            else ()
        )
        for part in parts:
            clear_collections(part, depth + 1)

    for value in values:
        clear_collections(value, depth)


def handle(estimator, node, method, bindings, stack, conditions, background):
    if not operation(estimator.index, node, method):
        return None
    args = call_args.arguments(node)
    names = ["source", "body"] if len(args) == 2 else ["source", "parallelOptions", "body"]
    slots = call_args.plan([(name, "", None) for name in names], args)
    if len(args) not in {2, 3} or slots is None:
        estimator.record("unresolved", "并行枚举重载未绑定", node, method, conditions, background)
        return UNKNOWN
    values = call_args.values(estimator.index, node, method, bindings)
    source_pos, body_pos = slots.index(0), slots.index(len(names) - 1)
    data = values[source_pos]
    bound = callback(estimator.index, args[body_pos], method, bindings)
    if not isinstance(bound, delegates.BoundDelegate) or bound.arity not in {1, 2, 3}:
        estimator.record(
            "unresolved", "并行回调为空或尚未绑定", node, method, conditions, background
        )
        return UNKNOWN
    option_pos = slots.index(1) if len(args) == 3 else None
    degree, uncertain = options(
        estimator.index,
        args[option_pos] if option_pos is not None else None,
        values[option_pos] if option_pos is not None else None,
        method,
        bindings,
    )
    size = collections.length(data, bindings)
    known = size is not None and size <= MAX_PARALLEL_ITEMS
    count = size if known else 1
    kind = data.get("<element_type>", "") if collections.known(data) else ""
    source_node = children(args[source_pos])[-1]
    kind = kind or collections.element_type(estimator.index, source_node, method)
    estimator.allocations += 1
    loop_ref = (
        f"parallel-state:{bindings.get(state.FRAME)}:{method.unit.path}:"
        f"{node.start_byte}:{estimator.allocations}"
    )
    control = state.key((loop_ref, "System.Threading.Tasks.ParallelLoopState", "termination"))
    initial = state.context(bindings)
    private = private_sites(estimator.index, bound)
    masked = set(bindings.get(state.UNSTABLE, ()))
    allocation_floor = estimator.allocations
    fixed = True
    if count > 1 or not known:
        fixed = False
        for _ in range(MAX_SHARED_ROUNDS):
            probe = probe_estimator(estimator)
            probing = {**bindings, state.UNSTABLE: frozenset(masked)}
            discovered = set(masked)
            for position in range(count):
                value = collections.item(data, position, probing) if known else None
                _, after = run_item(
                    probe,
                    bound,
                    method,
                    probing,
                    stack,
                    conditions,
                    background,
                    value,
                    position,
                    kind,
                    loop_ref,
                )
                discovered.update(shared_changes(initial, after, private, allocation_floor))
            if discovered == masked and not probe.truncated:
                fixed = True
                break
            masked = discovered
            if probe.truncated:
                break
    if not fixed:
        estimator.truncated = True
        invalidate_unexplored(bindings)
        known, count = False, 1
    source_mask = {**bindings, state.UNSTABLE: frozenset(masked)}
    changed_source = (
        collections.known(data)
        and data["<collection>"] == "list"
        and (
            collections.length(data, source_mask) is None
            or collections.version(data, source_mask) is None
        )
    )
    if changed_source:
        known, count = False, 1
    costs, scopes = [], []
    for position in range(count):
        scope = dict(bindings)
        scope[state.UNSTABLE] = frozenset(masked)
        value = collections.item(data, position, scope) if known else None
        duration, after = run_item(
            estimator,
            bound,
            method,
            scope,
            stack,
            conditions,
            background,
            value,
            position,
            kind,
            loop_ref,
        )
        costs.append(duration)
        scopes.append(after)
    stopped = any(scope.get(control) for scope in scopes)
    if known:
        # ForEach等待所有已安排的同步回调，但最大并行度不保证实际并发数。
        total = ZERO
        for cost in costs:
            total = total.plus(cost)
        # 等待已有任务的时长会随开工时刻缩短，不能按迭代数/并行度再乘一次。
        external_tasks = bool(task_ids(initial.values()))
        lower = (
            total.lower
            if degree == 1 and not external_tasks
            else max((cost.lower for cost in costs), default=0)
        )
        if degree and degree > 1 and not external_tasks:
            lower = max(lower, total.lower / degree)
        if stopped:
            lower = min((cost.lower for cost in costs), default=0)
        cost = Cost(0 if uncertain else lower, None if uncertain else total.upper)
    else:
        estimator.truncated |= size is not None
        cost = UNKNOWN
    if scopes:
        outgoing = {}
        state.merge(
            outgoing,
            [
                {key: value for key, value in state.context(scope).items() if key != state.UNSTABLE}
                for scope in scopes
            ],
        )
        state.transfer(bindings, outgoing, uncertain=not known)
    estimator.record(
        "loop",
        "并行枚举按完成边界计算" if known else "并行枚举次数未定",
        node,
        method,
        conditions,
        background,
        iterations=None if changed_source else size,
        bounded=known and not stopped,
        parallel=True,
        max_degree=degree,
        note="仅计算源码显式等待；最大并行度不是保证同时执行的数量，未知调度不固定为最快时间",
    )
    return cost


def control(estimator, node, method, bindings, conditions, background):
    function = node.child_by_field_name("function")
    name = text(function.child_by_field_name("name"))
    if name not in {"Stop", "Break"}:
        return None
    receiver = function.child_by_field_name("expression")
    kind = estimator.index.infer(receiver, method)
    if (
        name not in {"Stop", "Break"}
        or simple_type(kind) != "ParallelLoopState"
        or kind in estimator.index.classes
    ):
        return None
    value = estimator.index.value(receiver, method, bindings)
    if not isinstance(value, dict) or "<ref>" not in value:
        return UNKNOWN
    bindings[
        state.key((value["<ref>"], "System.Threading.Tasks.ParallelLoopState", "termination"))
    ] = True
    estimator.record(
        "loop",
        "并行中止条件影响剩余迭代",
        node,
        method,
        conditions,
        background,
        iterations=None,
        bounded=False,
    )
    return ZERO
