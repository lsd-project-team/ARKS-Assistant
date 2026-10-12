from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage

from app.answer_completion import AnswerCompletion, merge_continuation, termination
from tests.test_compaction import DeterministicModel


def reply(text, reason=None, used=10):
    return AIMessage(
        content=text,
        response_metadata={"stop_reason": reason} if reason else {},
        usage_metadata={"input_tokens": 10, "output_tokens": used, "total_tokens": used + 10},
    )


async def test_length_stop_is_continued_merged_and_replaces_stream():
    events, requests = [], []
    replies = [
        reply("已核对源码。以下是完整结论的第一段", "max_tokens", 4096),
        reply("以下是完整结论的第一段，后续也已说明。", "end_turn"),
    ]
    middleware = AnswerCompletion(lambda *event: events.append(event), 4096)

    async def handler(request):
        requests.append(request)
        return ModelResponse(result=[replies.pop(0)])

    result = await middleware.awrap_model_call(
        ModelRequest(model=DeterministicModel(), messages=[]), handler
    )
    assert result.result[0].text == "已核对源码。以下是完整结论的第一段，后续也已说明。"
    assert len(requests) == 2 and requests[1].tool_choice == "none"
    assert result.result[0].additional_kwargs["answer_completion"]["output"] == "complete"
    assert events[-1][0] == "answer_replace"


async def test_missing_finish_reason_is_suspected_without_blind_continuation():
    middleware = AnswerCompletion(lambda *_: None, 4096)
    called = 0

    async def handler(_request):
        nonlocal called
        called += 1
        return ModelResponse(result=[reply("结尾还没有", used=4096)])

    result = await middleware.awrap_model_call(
        ModelRequest(model=DeterministicModel(), messages=[]), handler
    )
    assert called == 1
    assert (
        result.result[0].additional_kwargs["answer_completion"]["output"] == "suspected_truncated"
    )


async def test_repeated_cutoff_has_two_continuations_total_and_remains_incomplete():
    middleware = AnswerCompletion(lambda *_: None, 256)
    called = 0

    async def handler(_request):
        nonlocal called
        called += 1
        return ModelResponse(result=[reply(str(called), "max_tokens", 256)])

    request = ModelRequest(model=DeterministicModel(), messages=[])
    result = await middleware.awrap_model_call(request, handler)
    assert called == 3
    assert result.result[0].additional_kwargs["answer_completion"]["output"] == "incomplete"
    await middleware.awrap_model_call(request, handler)
    assert called == 4


def test_tool_calls_are_not_continued_and_normal_stop_at_limit_is_complete():
    assert termination(reply("完整。", "end_turn", 4096), 4096)["output"] == "complete"
    assert merge_continuation("此前正文", "此前正文及补充") == "此前正文及补充"
