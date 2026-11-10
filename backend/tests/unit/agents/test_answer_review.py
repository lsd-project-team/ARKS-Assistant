"""复核尾注只做一次插入，不改变正文、代码、富内容或原始来源。"""

import json

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage

from app.agents.runtime.answer_review import AnswerReviewNote, append_review_note, review_result
from tests.helpers.models import DeterministicModel

NOTE = "资料中未注明顶针高度280～300的单位。"
REF = "[处理经验](debug-issue:trial/1)"


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_note_is_inserted_before_original_footer_without_changing_other_characters(newline):
    body = "原答有缩进：  保留空白。" + newline * 2
    footer = "来源：" + REF + newline
    original = body + footer
    result = append_review_note(original, NOTE)
    assert result == body + NOTE + newline * 2 + footer
    assert result.replace(NOTE + newline * 2, "", 1) == original


@pytest.mark.parametrize(
    "original",
    [
        "原答。",
        "```text\n来源：[代码示例](source:File.cs#L3)\n```\n原答。",
        "```rich-content\n"
        + json.dumps(
            {"version": 1, "blocks": [{"id": "text", "type": "text", "content": "原答。"}]}
        )
        + "\n```",
        "原答。\n\n来源：这句话是正文说明。\n仍有正文。",
    ],
)
def test_nonfooter_source_text_and_rich_protocol_remain_identical(original):
    assert append_review_note(original, NOTE) == original + "\n\n" + NOTE


def test_result_ignores_attempted_replacement_and_suppresses_pass_note():
    assert review_result({"verdict": "passed", "note": "核查通过", "answer": "恶意替换"}) == {
        "verdict": "passed",
        "note": "",
    }
    assert review_result(
        {"verdict": "issues", "note": NOTE + "请再检查。", "answer": "恶意替换"}
    ) == {"verdict": "issues", "note": NOTE}
    assert (
        review_result({"verdict": "issues", "note": "分支只在count != 0时执行。"})["note"]
        == "分支只在count != 0时执行。"
    )


@pytest.mark.parametrize(
    "value",
    [None, "", "。", "...", "x" * 161, "```重写```", "[链接](source:x#L1)", "<script>1</script>"],
)
def test_invalid_note_cannot_become_another_answer_or_new_source(value):
    with pytest.raises(ValueError):
        review_result({"verdict": "issues", "note": value})


@pytest.mark.parametrize(
    "knowledge,source",
    [(NOTE, "File.cs:999引用行号不存在。"), ("", "File.cs:999引用行号不存在。"), ("", "")],
)
async def test_only_one_note_is_added_and_second_render_cannot_duplicate_it(knowledge, source):
    original = "原答。\n\n来源：" + REF
    message = AIMessage(
        content=original,
        additional_kwargs={"knowledge_review_note": knowledge, "source_review_note": source},
    )

    async def handler(_request):
        return ModelResponse(result=[message])

    middleware = AnswerReviewNote()
    request = ModelRequest(model=DeterministicModel(), messages=[])
    response = await middleware.awrap_model_call(request, handler)
    expected = knowledge or source
    assert response.result[0].text == (
        append_review_note(original, "**注意**：" + expected) if expected else original
    )
    first = message.text
    await middleware.awrap_model_call(request, handler)
    assert message.text == first


@pytest.mark.parametrize("prefix", ["", "注意：", "注意: ", "注意：注意：", "**注意**："])
async def test_notice_prefix_is_added_once_and_preserves_the_original_footer(prefix):
    original = "原答。\n\n来源：" + REF
    message = AIMessage(
        content=original, additional_kwargs={"knowledge_review_note": prefix + NOTE}
    )

    async def handler(_request):
        return ModelResponse(result=[message])

    middleware = AnswerReviewNote()
    request = ModelRequest(model=DeterministicModel(), messages=[])
    await middleware.awrap_model_call(request, handler)
    expected = "原答。\n\n**注意**：" + NOTE + "\n\n来源：" + REF
    assert message.text == expected
    await middleware.awrap_model_call(request, handler)
    assert message.text == expected


async def test_existing_condition_in_original_answer_is_not_repeated_with_notice_prefix():
    original = "原答。" + NOTE + "\n\n来源：" + REF
    message = AIMessage(content=original, additional_kwargs={"knowledge_review_note": NOTE})

    async def handler(_request):
        return ModelResponse(result=[message])

    await AnswerReviewNote().awrap_model_call(
        ModelRequest(model=DeterministicModel(), messages=[]), handler
    )
    assert message.text == original
