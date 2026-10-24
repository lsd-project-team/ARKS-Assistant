"""保存的向导/线程回调作为独立入口；创建回调时不执行其正文。"""

import re
from dataclasses import replace

from app.modules.action_timing import source_arguments as arguments
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing.source_index import children, description, text, value_children, walk
from app.modules.action_timing.source_local_functions import declared_locals

WIZARD_ACTIONS = {"backAction": "返回", "nextAction": "下一步", "doneAction": "完成"}


def callback_method(node, outer, name):
    types, initializers = declared_locals(node)
    return replace(
        outer,
        name=name,
        node=node,
        parameters=[],
        types={**outer.types, **types},
        initializers=initializers,
        body_override=None,
        body_node=node.child_by_field_name("body"),
        callable_kind="delegate",
        is_virtual=False,
        variadic=False,
    )


def wizard_label(index, args, method):
    for arg in args:
        if arguments.argument_name(arg) not in {"descritpion", "description"}:
            continue
        parts = value_children(arg)
        value = parts[-1] if parts else None
        label = index.value(value, method, {})
        if not isinstance(label, str):
            raw = text(value)
            if '"' not in raw:
                continue
            label = re.sub(r"\{[^{}]*\}", "", raw.split('"', 1)[1].rsplit('"', 1)[0])
        label = re.sub(r"\\[rn]|\s+", " ", label)
        return label.strip(" :：/0123456789")[:80]
    return "向导步骤"


def discover(index, method, qualifies):
    for creation in walk(method.body):
        if creation.type != "object_creation_expression":
            continue
        kind = text(creation.child_by_field_name("type"))
        args = children(creation.child_by_field_name("arguments"), "argument")
        owner = index.lookup_type(kind, method)
        info = index.classes.get(owner)
        wizard = info is not None and info.short_name == "AssistantConfig"
        thread = kind in {"Thread", "System.Threading.Thread"} and owner not in index.classes
        if not wizard and not thread:
            continue
        thread_name = re.search(r'\bName\s*=\s*"([^"]+)"', text(creation)) if thread else None
        label = (
            wizard_label(index, args, method)
            if wizard
            else (
                f"{thread_name[1]}（工作体）"
                if thread_name
                else f"{description(method.unit.raw, method.node) or method.name}（后台工作体）"
            )
        )
        for position, arg in enumerate(args):
            action = arguments.argument_name(arg)
            if (wizard and action not in WIZARD_ACTIONS) or (thread and position != 0):
                continue
            callback = delegates.unwrap(index, arg, method)
            if callback is None or callback.type not in {
                "lambda_expression",
                "anonymous_method_expression",
            }:
                continue
            if not qualifies(callback, method):
                continue
            display = f"{label} · {WIZARD_ACTIONS[action]}" if wizard else label
            target = callback_method(
                callback, method, f"<{action or 'thread'}:{callback.start_byte}>"
            )
            yield target, display, "wizard_step" if wizard else "callback"
