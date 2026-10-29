"""统一六项不能遗漏旧排查、判断、条件或混入来源元信息。"""

from copy import deepcopy

from app.agents.runtime.knowledge_scope import selected_records, selection_input
from app.modules.handover.domain.debug_knowledge import knowledge_sections
from app.modules.knowledge.corpora.debug_issues import readable_payload


def test_six_sections_project_legacy_facts_without_mutating_original():
    payload = {
        "problem": "取片报警 E901",
        "conditions": "客户现场加热",
        "device": "ZX2200 HS",
        "module": "S1 取片",
        "environment": "配方A",
        "software_version": "2.1.0",
        "investigation": "已检查真空管路",
        "cause": "原记录认为密封圈破损",
        "solution": "更换密封圈",
        "verification": "连续20次正常",
        "notes": "来源编号：EXP-001\n导入标识：hash\n只对应本次工况。",
        "original_text": "原文完整保留",
        "record_type": "problem",
        "resolution_status": "resolved",
        "keywords": ["E901"],
    }
    before = deepcopy(payload)
    sections = knowledge_sections(payload)
    assert list(sections) == ["适用条件", "内容说明", "处理方法", "结果记录", "注意事项"]
    assert (
        sections["内容说明"] == "取片报警 E901\n\n已检查真空管路\n\n原因判断：原记录认为密封圈破损"
    )
    assert all(
        value in sections["适用条件"]
        for value in ("ZX2200 HS", "S1 取片", "配方A", "2.1.0", "加热")
    )
    assert sections["处理方法"] == "更换密封圈"
    assert sections["结果记录"] == "连续20次正常"
    assert sections["注意事项"] == "只对应本次工况。"
    content = readable_payload(payload)
    assert content["内容说明"] == sections["内容说明"]
    assert content["录入原文"] == payload["original_text"]
    assert content["处理状态"] == "记录人反馈已解决"
    assert "来源编号" not in content["注意事项"]
    assert payload == before


def test_absent_facts_stay_empty_and_exact_legacy_repetition_is_not_repeated():
    sections = knowledge_sections(
        {
            "problem": "先检查管路，再检查密封。",
            "investigation": "检查管路",
            "conditions": "设备：ZX2200",
            "device": "ZX2200",
        }
    )
    assert sections["内容说明"] == "先检查管路，再检查密封。"
    assert sections["适用条件"] == "设备：ZX2200"
    assert sections["处理方法"] == sections["结果记录"] == sections["注意事项"] == ""


def test_moved_facts_are_not_duplicated_and_new_fields_can_be_selected_with_fixed_reference():
    payload = {
        "problem": "取片不稳定。",
        "investigation": "已检查真空管路。",
        "solution": "已检查真空管路。\n更换密封圈。",
        "cause": "原记录认为密封圈破损。",
        "notes": "原因判断：原记录认为密封圈破损。",
    }
    content = readable_payload(payload)
    assert content["内容说明"] == payload["problem"]
    rows = [{"reference": "[经验](debug-issue:fixed-id/3)", "content": content}]
    numbered = selection_input(rows)
    assert numbered[0]["content"]["内容说明"][0]["text"] == payload["problem"]
    selected = selected_records(
        {"selections": [{"id": 1, "parts": [{"field": "处理方法", "start": 1, "end": 1}]}]}, rows
    )
    assert selected[0]["reference"] == rows[0]["reference"]
    assert selected[0]["content"] == {"处理方法": "已检查真空管路。"}
