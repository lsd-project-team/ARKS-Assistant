"""字段约束是前后端共同的业务边界；AI 也经过相同验证。"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

Text = Annotated[str, Field(max_length=100000)]
Short = Annotated[str, Field(max_length=2000)]
Kind = Literal[
    "source",
    "interview",
    "candidate",
    "task",
    "decision",
    "constraint",
    "baseline",
    "verification",
    "issue",
    "debug_issue",
    "plan",
    "framework",
    "training",
    "receipt",
    "package",
    "job",
]


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_id: str = Field(min_length=1, max_length=36)
    version: int = Field(ge=1)
    locator: Short = ""
    quote: Short = ""


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin: Literal["human", "ai", "import"] = "human"
    evidence: list[Evidence] = Field(default_factory=list, max_length=100)
    notes: Text = ""


class Source(Payload):
    source_project_id: Short = ""
    supersedes: str = ""
    source_workspace_id: Short = ""
    filename: Short = ""
    format: Short = "text"
    provider: Short = ""
    source_version: Short = ""
    device: Short = ""
    sha256: Short = ""
    content: Text = ""
    parse_status: Literal["readable", "partial", "needs_ocr"] = "readable"
    parse_notes: Text = ""
    path: Short = ""
    files: list[dict[str, str]] = Field(default_factory=list, max_length=2000)


class Interview(Payload):
    author: Short = ""
    interviewer: Short = ""
    date: Short = ""
    topic: Short = ""
    questions: Text = ""
    transcript: Text = ""
    correction: Text = ""


class Task(Payload):
    category: Literal["feature", "bug", "untested", "site"] = "feature"
    work_status: Literal["todo", "doing", "blocked", "done", "accepted"] = "todo"
    evidence_status: Literal["unknown", "statement", "source", "tested", "device"] = "unknown"
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    goal: Text = ""
    current: Text = ""
    acceptance: Text = ""
    owner: Short = ""
    due: Short = ""
    location: Short = ""
    result: Text = ""
    dependencies: list[str] = Field(default_factory=list, max_length=100)
    constraints: list[str] = Field(default_factory=list, max_length=100)
    baseline_id: str = ""
    required_layer: Literal[
        "source", "interface", "offline", "simulation", "bench", "device", "release"
    ] = "device"


class Decision(Payload):
    task_id: str = ""
    decision_type: Literal["original", "new"] = "original"
    intent: Text = ""
    alternatives: Text = ""
    rejected: Text = ""
    tradeoffs: Text = ""


class Constraint(Payload):
    task_ids: list[str] = Field(default_factory=list, max_length=100)
    category: Literal["safety", "equipment", "process", "software"] = "equipment"
    condition: Text = ""
    consequence: Text = ""
    stop_condition: Text = ""
    authority: Short = ""


class Baseline(Payload):
    source_id: str = ""
    source_scope: Text = ""
    software_version: Short = ""
    commit: Short = ""
    firmware: Short = ""
    sdk: Short = ""
    device: Short = ""
    recipe: Short = ""
    calibration: Short = ""
    configuration: Text = ""
    build: Text = ""
    environment: Text = ""
    missing: Text = ""


class Verification(Payload):
    task_id: str = ""
    baseline_id: str = ""
    layer: Literal["source", "interface", "offline", "simulation", "bench", "device", "release"] = (
        "source"
    )
    result: Literal["pending", "pass", "fail", "blocked"] = "pending"
    tester: Short = ""
    date: Short = ""
    environment: Text = ""
    method: Text = ""
    observed: Text = ""
    report: Text = ""


class Issue(Payload):
    task_id: str = ""
    category: Literal["question", "blocker", "conflict", "unknown"] = "question"
    risk: Literal["low", "normal", "high", "critical"] = "normal"
    status: Literal["open", "resolved"] = "open"
    question: Text = ""
    owner: Short = ""
    due: Short = ""
    answer: Text = ""
    closure: Text = ""


class DebugIssue(Payload):
    record_type: Literal["problem", "experience", "progress", "archive"] = "problem"
    occurred_on: Short = ""
    recorded_by: Short = ""
    recorded_at: Short = ""
    problem: Text = ""
    conditions: Text = ""
    environment: Text = ""
    device: Short = ""
    software_version: Short = ""
    module: Short = ""
    investigation: Text = ""
    cause: Text = ""
    solution: Text = ""
    verification: Text = ""
    resolution_status: Literal["open", "resolved", "recorded"] = "open"
    keywords: list[Short] = Field(default_factory=list, max_length=20)
    original_text: Text = ""
    reported_by: Short = ""
    source_thread_id: str = Field(default="", max_length=36)
    source_message_id: str = Field(default="", max_length=36)
    source_project_id: Short = ""
    source_change_id: str = Field(default="", max_length=36)
    source_change_version: str = Field(default="", max_length=64)
    source_verification_id: str = Field(default="", max_length=36)


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Short
    prerequisite: Short = ""
    output: Short = ""
    verification: Short = ""
    stop: Short = ""
    rollback: Short = ""
    owner: Short = ""


class Plan(Payload):
    task_id: str = ""
    baseline_id: str = ""
    prerequisites: Text = ""
    steps: list[PlanStep] = Field(default_factory=list, max_length=100)
    unresolved: Text = ""


class Framework(Payload):
    scope: Text = ""
    entrypoints: Text = ""
    layers: Text = ""
    flow: Text = ""
    coverage: Text = ""
    missing: Text = ""


class Training(Payload):
    task_id: str = ""
    audience: Short = ""
    conditions: Text = ""
    operation: Text = ""
    timing: Text = ""
    failure: Text = ""
    recovery: Text = ""
    exercise: Text = ""
    feedback: Text = ""


class Receipt(Payload):
    package_id: str = ""
    package_version: int = Field(default=1, ge=1)
    receiver: Short = ""
    trainer: Short = ""
    date: Short = ""
    understanding: Text = ""
    demonstration: Text = ""
    remaining: Text = ""


class Package(Payload):
    recipient: Short = ""
    scope: Text = ""
    records: list[Evidence] = Field(default_factory=list, max_length=1000)
    gaps: Text = ""


class Candidate(Payload):
    target_kind: Literal["task", "decision", "constraint", "issue", "framework", "training", "plan"]
    proposed: dict = Field(default_factory=dict)
    reason: Text = ""
    promoted_id: str = ""


class Job(Payload):
    action: Literal["extract", "plan", "framework", "training"]
    record_ids: list[str] = Field(min_length=1, max_length=20)
    input_versions: dict[str, int] = Field(default_factory=dict)
    status: Literal["queued", "running", "succeeded", "failed", "cancelled", "interrupted"] = (
        "queued"
    )
    error: Text = ""
    result_ids: list[str] = Field(default_factory=list)


PAYLOADS = {
    "source": Source,
    "interview": Interview,
    "candidate": Candidate,
    "task": Task,
    "decision": Decision,
    "constraint": Constraint,
    "baseline": Baseline,
    "verification": Verification,
    "issue": Issue,
    "debug_issue": DebugIssue,
    "plan": Plan,
    "framework": Framework,
    "training": Training,
    "receipt": Receipt,
    "package": Package,
    "job": Job,
}


def validate_payload(kind, value):
    TypeAdapter(Kind).validate_python(kind)
    return PAYLOADS[kind].model_validate(value).model_dump()
