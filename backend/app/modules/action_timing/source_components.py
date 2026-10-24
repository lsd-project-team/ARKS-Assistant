"""源码可算的条件/每轮等待组成；独立于执行总时长，绝不重复相加。"""

import math
import re

from app.modules.action_timing.source_index import children, text, value_children, walk
from app.modules.action_timing.source_local_functions import lexical_walk


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def terminates(node):
    if node is None:
        return False
    if node.type in {
        "return_statement",
        "throw_statement",
        "break_statement",
        "continue_statement",
        "goto_statement",
    }:
        return True
    if node.type == "block":
        return any(terminates(part) for part in children(node))
    if node.type == "if_statement":
        return terminates(node.child_by_field_name("consequence")) and terminates(
            node.child_by_field_name("alternative")
        )
    return False


def fixed_loop(node):
    header = text(node).split("{", 1)[0]
    match = re.match(
        r"for\s*\(\s*(?:int|short|double)\s+(\w+)\s*=\s*(-?\d+)\s*;"
        r"\s*\1\s*(<=|<|>=|>)\s*(-?\d+)\s*;\s*\1\s*(\+\+|--|\+=\s*-?\d+|-=\s*-?\d+)\s*\)",
        header,
    )
    if not match:
        return None
    name, start, operator, end, update = match.groups()
    body = node.child_by_field_name("body")
    # 正文改变计数器、提前出口或ref/out会破坏简单次数公式，保留条件表达式。
    for part in walk(body):
        if part.type in {
            "break_statement",
            "continue_statement",
            "return_statement",
            "goto_statement",
        }:
            return None
        if part.type in {
            "assignment_expression",
            "postfix_unary_expression",
            "prefix_unary_expression",
        }:
            if re.search(rf"\b{re.escape(name)}\b", text(part)):
                return None
        if part.type == "argument" and re.match(rf"\s*(ref|out)\s+{name}\b", text(part)):
            return None
    step = (
        1
        if update == "++"
        else -1
        if update == "--"
        else int(update[2:]) * (1 if update.startswith("+=") else -1)
    )
    value, end = int(start), int(end)
    compare = {
        "<": lambda x: x < end,
        "<=": lambda x: x <= end,
        ">": lambda x: x > end,
        ">=": lambda x: x >= end,
    }[operator]
    count = 0
    if step == 0 and compare(value):
        return None
    while compare(value) and count <= 100000:
        count += 1
        value += step
    return count if count <= 100000 else None


def call_context(call, method):
    """同时用于直接等待和任务启动点；不把不可达回调当作条件组成。"""
    conditions, factors, loops, parent, possible = [], [], [], call.parent, True
    boundary = method.body_override.parent if method.body_override else method.node
    multiplier = 1
    while parent is not None and parent != boundary:
        if parent.type in {"block", "switch_section"}:
            statements = children(parent)
            blocked = False
            for statement in statements:
                if statement.start_byte > call.start_byte:
                    break
                if statement.type == "labeled_statement":
                    blocked = False
                if statement.end_byte <= call.start_byte:
                    if statement.type == "if_statement":
                        yes = terminates(statement.child_by_field_name("consequence"))
                        no = terminates(statement.child_by_field_name("alternative"))
                        guard = text(statement.child_by_field_name("condition"))
                        if yes and not no:
                            conditions.append(f"!({guard})")
                        elif no and not yes:
                            conditions.append(guard)
                    blocked |= terminates(statement)
            possible &= not blocked
        if parent.type == "switch_section":
            conditions.append(text(parent).split("{", 1)[0].splitlines()[0])
        elif parent.type == "catch_clause":
            conditions.append("异常恢复分支")
        if parent.type == "if_statement":
            branch = parent.child_by_field_name("consequence")
            yes = branch is not None and branch.start_byte <= call.start_byte < branch.end_byte
            condition = text(parent.child_by_field_name("condition"))
            if condition in {"true", "false"} and yes != (condition == "true"):
                possible = False
            conditions.append(condition if yes else f"!({condition})")
        elif parent.type == "for_statement":
            count = fixed_loop(parent)
            if count == 0:
                possible = False
            if count is not None:
                multiplier *= count
            else:
                factors.append(f"循环次数（{text(parent.child_by_field_name('condition'))}）")
            loops.append(parent.start_byte)
        elif parent.type in {"foreach_statement", "for_each_statement"}:
            factors.append(f"{text(parent.child_by_field_name('right'))}的项数")
            loops.append(parent.start_byte)
        elif parent.type in {"while_statement", "do_statement"}:
            condition = text(parent.child_by_field_name("condition"))
            if parent.type == "while_statement" and condition == "false":
                possible = False
            else:
                factors.append(f"满足({condition})的轮数")
            loops.append(parent.start_byte)
        parent = parent.parent
    return conditions, factors, loops, multiplier, possible


def literal_waits(index, method):
    cache = index.__dict__.setdefault("source_wait_components", {})
    if method.key in cache:
        return cache[method.key]
    groups = {}
    for call in lexical_walk(method.body):
        if call.type != "invocation_expression":
            continue
        function = text(call.child_by_field_name("function")).removeprefix("System.Threading.")
        function = function.removeprefix("Tasks.")
        if function not in {"Thread.Sleep", "Task.Delay", "DelayHelper.Delay"}:
            continue
        if index.resolve(call, method) is not None:
            continue
        raw_function = text(call.child_by_field_name("function"))
        if (
            raw_function in {"Thread.Sleep", "Task.Delay"}
            and index.lookup_type(raw_function.split(".", 1)[0], method) in index.classes
        ):
            continue
        args = children(call.child_by_field_name("arguments"), "argument")
        parts = value_children(args[0]) if len(args) == 1 else []
        value_node = parts[-1] if parts else None
        # 不从可变成员/形参初值猜当前值；这里只处理纯数值表达式。
        if value_node is None or any(
            n.type in {"identifier", "member_access_expression", "invocation_expression"}
            for n in walk(value_node)
        ):
            continue
        duration = index.value(value_node, method, {})
        if not number(duration) or duration <= 0:
            continue
        conditions, factors, loops, multiplier, possible = call_context(call, method)
        if not possible:
            continue
        key = (tuple(conditions), tuple(factors), tuple(loops))
        item = groups.setdefault(
            key,
            {
                "milliseconds": 0,
                "factors": factors,
                "conditions": conditions,
                "sources": [],
                "scope": "conditional",
                "method": f"{method.owner}.{method.name}",
                "note": "进入这些分支并正常执行时的等待组成；可能与汇总重合，不另加到总时长。",
            },
        )
        item["milliseconds"] += duration * multiplier
        item["sources"].append(
            {
                **method.unit.evidence(call),
                "milliseconds": duration,
                "fixed_repetitions": multiplier,
            }
        )
    cache[method.key] = list(groups.values())
    return cache[method.key]


def calculated_stages(stages):
    """后台及重复阶段的正数也需可见，但记录条数不是实际执行次数。"""
    result, seen = [], set()
    for stage in stages:
        duration = stage.get("milliseconds")
        if stage["kind"] != "delay" or not number(duration) or duration <= 0:
            continue
        key = (
            stage["path"],
            stage["line"],
            duration,
            stage["background"],
            stage.get("repeat", False),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "milliseconds": duration,
                "scope": "background" if stage["background"] else "expanded",
                "conditions": stage["conditions"],
                "factors": ["每轮"] if stage.get("repeat") else [],
                "sources": [{k: stage[k] for k in ("path", "line", "code", "version")}],
                "note": "已展开的源码等待站点；同一站点不按展开记录条数推断实际次数。",
            }
        )
    return result


def preview(items):
    """主表只需首个可算组成；完整引用和缺项留在详情，避免发送整个调用图。"""
    return [
        {
            "milliseconds": item["milliseconds"],
            "factors": item["factors"],
            "scope": item["scope"],
            "conditions": [],
            "sources": [],
            "note": "完整条件、其他组成与源码依据见详情",
        }
        for item in items[:1]
    ]
