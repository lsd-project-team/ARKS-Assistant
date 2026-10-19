"""原始人类请求只由服务端入口传入；模型编写的约定不能覆盖这个依据。"""

from dataclasses import asdict, dataclass

from app.core.identifiers import now_iso


@dataclass(frozen=True)
class RequestOrigin:
    channel: str
    text: str
    actor_id: str = ""
    message_id: str = ""
    run_id: str = ""


def initial_binding(origin, contract):
    return {
        "original": {"origin": asdict(origin), "contract": contract, "at": now_iso()}
        if origin is not None
        else None,
        "revisions": [],
    }


def revised_binding(current, origin, previous_version, delta):
    # 老副本没有原始请求时保留未知；后补约定不能伪装成最初已经获得授权。
    binding = current or initial_binding(None, {})
    return {
        "original": binding["original"],
        "revisions": [
            *binding["revisions"],
            {
                "origin": asdict(origin) if origin is not None else None,
                "previous_requirements_version": previous_version,
                "changes": delta,
                "at": now_iso(),
            },
        ],
    }
