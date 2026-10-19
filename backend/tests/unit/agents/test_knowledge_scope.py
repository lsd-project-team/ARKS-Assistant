import json

import pytest

from app.agents.runtime.knowledge_scope import scope_problems, scoped_fallback, selected_records

BEFORE = "7月23日，adv-3精度稳定在3μm 3Σ。"
TARGET = "7月25日14:47至7月26日00:50，adv-3室温23.2℃，精度范围由-4~4μm变为-4~2μm。"
AFTER = "7月27日，adv-3另一个阶段。"
ROWS = [
    {
        "reference": "[跨日试验 · v4](debug-issue:trial/4)",
        "content": {"记录正文": BEFORE + TARGET + AFTER},
    },
    {
        "reference": "[其他设备 · v1](debug-issue:other/1)",
        "content": {"记录正文": "adv-30无关结果900μm"},
    },
]


def choice(text=TARGET, reference=ROWS[0]["reference"]):
    return {
        "selections": [
            {
                "reference": reference,
                "reason": "设备与时间阶段符合",
                "excerpts": [{"field": "记录正文", "text": text}],
            }
        ]
    }


def test_cross_day_record_is_restricted_to_selected_passage_even_on_fallback():
    selected = selected_records(choice(), ROWS)
    assert selected == [{"reference": ROWS[0]["reference"], "content": {"记录正文": TARGET}}]
    fallback = scoped_fallback(selected)
    assert TARGET in fallback
    assert BEFORE not in fallback and AFTER not in fallback and "900" not in fallback
    assert ROWS[0]["content"]["记录正文"] == BEFORE + TARGET + AFTER


@pytest.mark.parametrize(
    "result",
    [
        {},
        {"selections": "all"},
        choice("伪造的精度结果"),
        choice(reference="[旧版本](debug-issue:trial/3)"),
        {"selections": [{"reference": ROWS[0]["reference"], "reason": "符合", "excerpts": []}]},
    ],
)
def test_missing_or_fabricated_evidence_is_rejected(result):
    with pytest.raises((ValueError, KeyError, TypeError)):
        selected_records(result, ROWS)
    assert "adv-3" not in scoped_fallback([])


def test_second_review_cannot_expand_selected_scope():
    selected = selected_records(choice(), ROWS)
    with pytest.raises(ValueError):
        selected_records(choice(BEFORE), selected)
    assert selected_records({"selections": []}, selected) == []


def test_typographic_quote_is_restored_and_reference_title_is_canonical():
    result = choice(TARGET.replace("-4~4μm", "-4 ～ 4 μm"), "debug-issue:trial/4")
    selected = selected_records(result, ROWS)
    assert selected[0]["content"]["记录正文"] == TARGET
    assert selected[0]["reference"] == ROWS[0]["reference"]
    with pytest.raises(ValueError):
        selected_records(choice(TARGET.replace("23.2", "25.2")), ROWS)


def test_foreign_citations_and_missing_requested_images_are_detected():
    selected = selected_records(choice(), ROWS)
    assert "未选定" in scope_problems("试验结果", ROWS[1]["reference"], selected)
    assert "不能遗漏" in scope_problems("展示记录文字和全部原图", TARGET, selected)
    assert not scope_problems("展示全部原图", TARGET + ROWS[0]["reference"], selected)
    assert not scope_problems("示例", "```text\ndebug-issue:other/1\n```", selected)


def test_scoped_fallback_redacts_credentials_without_modifying_source():
    rows = [
        {
            "reference": ROWS[0]["reference"],
            "content": {"记录正文": "api_key='do-not-leak'\n" + TARGET},
        }
    ]
    fallback = scoped_fallback(rows)
    assert "do-not-leak" not in fallback and "敏感值已隐藏" in fallback
    assert "do-not-leak" in json.dumps(rows)
