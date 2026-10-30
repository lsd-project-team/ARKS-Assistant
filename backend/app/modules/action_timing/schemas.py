"""版本一协议：时间来自采集端单调时钟，归属来自服务端项目上下文。"""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from app.modules.action_timing.catalog import BY_CODE

Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[\w.:-]+$")]


def numeric_time(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("耗时必须为数值")
    return value


Milliseconds = Annotated[
    float, BeforeValidator(numeric_time), Field(ge=0, le=1e12, allow_inf_nan=False)
]
Status = Literal["success", "failed", "aborted", "retry", "skipped", "noop", "incomplete"]


class ProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Manifest(ProtocolModel):
    protocol_version: Literal[1]
    run_id: Identifier
    mode: Literal["DryCycle"]
    source_kind: Literal["zx2200", "collector_test"]
    source_revision: str = Field(min_length=1, max_length=128)
    recipe_name: str = Field(max_length=200)
    recipe_fingerprint: str = Field(default="", max_length=128)
    entry_point: str = Field(min_length=1, max_length=200)
    started_at: AwareDatetime
    finished_at: AwareDatetime
    state: Literal["completed", "stopped", "incomplete"]
    clock: Literal["stopwatch"]
    clock_frequency: int = Field(gt=0, strict=True)
    event_count: int = Field(ge=0, le=20000, strict=True)
    dropped_events: int = Field(ge=0, strict=True)
    boundary: Literal["synchronous_call_including_waits"]

    @model_validator(mode="after")
    def ordered_time(self):
        if self.finished_at < self.started_at:
            raise ValueError("运行结束早于开始")
        return self


class TimingEvent(ProtocolModel):
    event_id: Identifier
    action_code: str
    parent_id: Identifier | None = None
    logical_id: Identifier
    attempt: int = Field(ge=1, strict=True)
    kind: Literal["action", "stage"]
    stage: str = Field(default="", max_length=100)
    category: Literal["work", "wait", "delay"]
    branch: str = Field(min_length=1, max_length=100)
    station: Literal["S1", "S2"]
    start_ms: Milliseconds
    end_ms: Milliseconds | None = None
    status: Status
    raw_result: str = Field(default="", max_length=100)
    reason: str = Field(default="", max_length=1000)
    thread_id: int = Field(ge=0, strict=True)
    context: dict[str, str] = Field(default_factory=dict, max_length=16)

    @model_validator(mode="after")
    def valid_event(self):
        definition = BY_CODE.get(self.action_code)
        if not definition or self.station != definition["station"]:
            raise ValueError("动作代码或工位不属于首批五项")
        if self.kind == "action" and (self.parent_id or self.stage):
            raise ValueError("动作记录不能指定父动作或阶段名")
        if self.kind == "stage" and (not self.parent_id or not self.stage):
            raise ValueError("阶段必须指定父动作和阶段名")
        if self.end_ms is not None and self.end_ms < self.start_ms:
            raise ValueError("动作结束早于开始")
        if (self.end_ms is None) != (self.status == "incomplete"):
            raise ValueError("未结束记录必须标为incomplete，已结束记录必须有结果")
        if any(len(key) > 80 or len(value) > 500 for key, value in self.context.items()):
            raise ValueError("动作上下文字段过长")
        return self


class TimingPackage(ProtocolModel):
    manifest: Manifest
    events: list[TimingEvent] = Field(max_length=20000)

    @model_validator(mode="after")
    def valid_tree(self):
        if len(self.events) != self.manifest.event_count:
            raise ValueError("记录数量与manifest不一致")
        by_id = {event.event_id: event for event in self.events}
        if len(by_id) != len(self.events):
            raise ValueError("数据包内event_id重复")
        attempts = [
            (event.logical_id, event.attempt) for event in self.events if event.kind == "action"
        ]
        if len(set(attempts)) != len(attempts):
            raise ValueError("同一逻辑动作的尝试号重复")
        for event in self.events:
            if event.kind != "stage":
                continue
            parent = by_id.get(event.parent_id)
            # 仅接受一层同步子阶段，防止孤儿、环及跨动作拼接污染统计。
            if (
                not parent
                or parent.kind != "action"
                or parent.action_code != event.action_code
                or parent.logical_id != event.logical_id
                or parent.attempt != event.attempt
                or parent.thread_id != event.thread_id
                or event.start_ms < parent.start_ms
                or (
                    parent.end_ms is not None
                    and (event.end_ms is None or event.end_ms > parent.end_ms)
                )
            ):
                raise ValueError("子阶段与父动作不匹配或超出同步调用区间")
        return self
