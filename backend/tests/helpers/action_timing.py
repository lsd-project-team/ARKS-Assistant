"""协议测试数据，与设备实际采样严格区分。"""

import copy
import io
import json
import zipfile

from app.modules.action_timing.catalog import CATALOG


def timing_package():
    events = []
    for index, definition in enumerate(CATALOG):
        events.append(
            {
                "event_id": f"event-{index}",
                "action_code": definition["code"],
                "parent_id": None,
                "logical_id": f"logical-{index}",
                "attempt": 1,
                "kind": "action",
                "stage": "",
                "category": "work",
                "branch": "drycycle.collector_test",
                "station": definition["station"],
                "start_ms": index * 20,
                "end_ms": index * 20 + 10,
                "status": "success",
                "raw_result": "Success",
                "reason": "",
                "thread_id": index + 1,
                "context": {"bond_position": "测试焊点", "process_step": "协议验证"},
            }
        )
    stage = copy.deepcopy(events[0])
    stage.update(
        event_id="stage-0", parent_id="event-0", kind="stage", stage="移动", start_ms=1, end_ms=8
    )
    events.append(stage)
    return {
        "manifest": {
            "protocol_version": 1,
            "run_id": "test-run-1",
            "mode": "DryCycle",
            "source_kind": "collector_test",
            "source_revision": "test-revision",
            "recipe_name": "协议验证配方",
            "recipe_fingerprint": "test-config",
            "entry_point": "test_fixture",
            "started_at": "2026-10-21T00:00:00Z",
            "finished_at": "2026-10-21T00:01:00Z",
            "state": "completed",
            "clock": "stopwatch",
            "clock_frequency": 1000,
            "event_count": len(events),
            "dropped_events": 0,
            "boundary": "synchronous_call_including_waits",
        },
        "events": events,
    }


def raw_package(package=None):
    return json.dumps(package or timing_package(), ensure_ascii=False).encode()


def zip_package(package=None):
    package = package or timing_package()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(package["manifest"]))
        archive.writestr(
            "events.jsonl", "\n".join(json.dumps(event) for event in package["events"])
        )
    return output.getvalue()
