from deepagents.backends import FilesystemBackend
from langchain_core.messages import HumanMessage

from app.agents.context.budget import BudgetedSummarization
from app.agents.context.summary_quality import SECTIONS, summary_report
from tests.helpers.models import DeterministicModel


async def test_long_history_is_folded_from_beginning_without_dropping_constraints(
    monkeypatch, tmp_path
):
    prompts, events = [], []
    original = DeterministicModel._generate

    def capture(model, messages, *args, **kwargs):
        prompts.append(str(messages[0].content))
        return original(model, messages, *args, **kwargs)

    monkeypatch.setattr(DeterministicModel, "_generate", capture)
    middleware = BudgetedSummarization(
        DeterministicModel(),
        backend=FilesystemBackend(tmp_path),
        limit=8192,
        output=1024,
        emit=lambda *event: events.append(event),
        trigger=("tokens", 6000),
        keep=("tokens", 1000),
        trim_tokens_to_summarize=3000,
    )
    await middleware._acreate_summary(
        [
            HumanMessage(content="EARLY_READ_ONLY_CONSTRAINT"),
            HumanMessage(content="背景资料" * 4000),
            HumanMessage(content="TAIL_UNKNOWN_DEPENDENCY"),
        ]
    )
    combined = "\n".join(prompts)
    assert "EARLY_READ_ONLY_CONSTRAINT" in combined and "TAIL_UNKNOWN_DEPENDENCY" in combined
    assert len(prompts) > 2
    assert events[-1][1]["coverage"] == "all supplied history"
    assert summary_report("\n".join("## " + title + "\n无" for title in SECTIONS))["structured"]
