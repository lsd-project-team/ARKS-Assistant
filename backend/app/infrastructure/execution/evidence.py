"""平台执行证明校验；配置中的container标记不能替代真实运行证据。"""

from .cli import IMAGE_ID


def integer(value, minimum=1):
    return not isinstance(value, bool) and isinstance(value, int) and value >= minimum


def sandbox_evidence_valid(evidence, executor):
    if not isinstance(evidence, dict) or not isinstance(executor, dict):
        return False
    if (
        executor.get("kind") != "container"
        or evidence.get("isolated") is not True
        or evidence.get("platform") != executor.get("platform")
    ):
        return False
    actual = evidence.get("image_id")
    if (
        not isinstance(actual, str)
        or not IMAGE_ID.fullmatch(actual)
        or not actual.startswith("sha256:")
    ):
        return False
    configured = executor.get("image", "")
    if not isinstance(configured, str) or not IMAGE_ID.fullmatch(configured):
        return False
    if configured.startswith("sha256:") and actual != configured:
        return False
    # 兼容已有Linux协议2镜像ID证明；manifest digest与image ID不同时必须保留配置身份。
    if evidence.get("configured_image", configured) != configured:
        return False
    if "configured_image" not in evidence and actual != configured.rsplit("@", 1)[-1]:
        return False
    if evidence.get("configured_context", executor.get("context", "default")) != executor.get(
        "context", "default"
    ):
        return False
    if executor.get("platform") == "linux":
        return evidence.get("protocol") == 2
    if (
        executor.get("platform") != "windows"
        or evidence.get("protocol") != 3
        or "configured_image" not in evidence
        or "configured_context" not in evidence
        or evidence.get("proof_kind") != "engine_exec_exit"
        or evidence.get("isolation") != "hyperv"
        or evidence.get("container_stopped") is not True
    ):
        return False
    raw = evidence.get("raw_exit_code")
    if isinstance(raw, bool) or not isinstance(raw, int) or raw != 0:
        return False
    node = evidence.get("node_capacity")
    if not isinstance(node, dict) or node.get("probe_version") != 1:
        return False
    values = [
        node.get("free_bytes"),
        node.get("total_bytes"),
        node.get("measured_at"),
        evidence.get("scratch_reserved_bytes"),
        evidence.get("observed_capacity_bytes"),
        evidence.get("admitted_at"),
        evidence.get("guest_available_bytes"),
    ]
    if not all(integer(value) for value in values):
        return False
    free, total, measured, reserved, observed, admitted, available = values
    node_id = evidence.get("node_id")
    return (
        0 < free <= total
        and 20480 * 1024 * 1024 <= reserved <= 1048576 * 1024 * 1024
        and 0 < available <= observed <= reserved
        and free >= reserved + 1073741824
        and admitted - 120 <= measured <= admitted + 30
        and isinstance(node_id, str)
        and len(node_id) == 64
        and all(character in "0123456789abcdef" for character in node_id)
    )
