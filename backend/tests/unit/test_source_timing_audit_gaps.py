"""真实复核缺口的反例：SDK、保存的向导、可算组成与具体缺项。"""

import hashlib

import pytest

from app.modules.action_timing.source_service import SourceTiming
from app.modules.source_analysis.workspace import Workspace


def report(tmp_path, code):
    (tmp_path / "Demo.cs").write_text(code, encoding="utf-8")
    return SourceTiming(Workspace(tmp_path)).report()


def test_direct_sdk_stop_has_entry_and_unknown_completion(tmp_path):
    result = report(
        tmp_path,
        "class Panel {void Click(){for(int n=0;n<24;n++)"
        "GTN.mc.GTN_Stop(1,1,0);GTN.mc.GTN_StopCommandList(1,1,0);}}",
    )
    row = next(r for r in result["rows"] if r["method"] == "Click")
    assert row["total_ms"] is None
    assert sum(x["label"] == "直接设备SDK调用" for x in row["stages"]) == 25
    assert any("停止完成" in s for x in row["missing_requirements"] for s in x["required"])


def test_etel_download_is_discovered_but_same_named_source_type_is_not_sdk(tmp_path):
    result = report(
        tmp_path,
        "using ch.etel.edi.dsa.v40; class Demo {"
        "void Download(){DsaDrive drive;drive.scaleMappingDownload(path,0);}}",
    )
    row = result["rows"][0]
    assert row["method"] == "Download" and row["total_ms"] is None
    assert any("补偿文件" in s for x in row["missing_requirements"] for s in x["required"])
    (tmp_path / "Fake.cs").write_text(
        "class DsaDrive{public void scaleMappingDownload(string p,int n){}}", encoding="utf-8"
    )
    assert not any(
        s["label"] == "直接设备SDK调用"
        for r in SourceTiming(Workspace(tmp_path)).report()["rows"]
        for s in r["stages"]
    )


def test_saved_wizard_is_separate_and_initialization_does_not_run_it(tmp_path):
    result = report(
        tmp_path,
        "class AssistantConfig{public AssistantConfig(Action doneAction){}}"
        "class Teach{void InitControl(){new AssistantConfig(doneAction:()=>{"
        "for(int i=0;i<10;i++)Thread.Sleep(100);});}}",
    )
    step = next(r for r in result["rows"] if r["analysis_unit"] == "wizard_step")
    init = next(r for r in result["rows"] if r["method"] == "InitControl")
    assert step["total_ms"] == 1000 and not step["primary"]
    assert init["known_delay_min_ms"] == 0 and not any(s["kind"] == "delay" for s in init["stages"])
    assert step["source_components"][0]["milliseconds"] == 1000


def test_unknown_delay_names_the_actual_input(tmp_path):
    row = report(tmp_path, "class Demo{public void Start(int delay){Thread.Sleep(delay);}} ")[
        "rows"
    ][0]
    assert row["total_ms"] is None
    assert any(
        x["category"] == "input" and any("delay" in y for y in x["required"])
        for x in row["missing_requirements"]
    )


@pytest.mark.parametrize(
    "body",
    [
        "while(false){Thread.Sleep(999);}",
        "return;Thread.Sleep(999);",
        "for(int i=120;i<=0;i--){Thread.Sleep(999);}",
        "for(double i=120;i<=0;i-=40){Thread.Sleep(999);}",
    ],
)
def test_unreachable_literal_is_not_a_computable_component(tmp_path, body):
    row = report(tmp_path, "class Demo{public void Start(){" + body + "}} ")["rows"][0]
    assert not row["source_components"]


def test_unknown_loop_keeps_each_iteration_composition(tmp_path):
    row = report(
        tmp_path,
        "class Demo{public void Start(int count){for(int i=0;i<count;i++){"
        "Thread.Sleep(30);Thread.Sleep(30);Thread.Sleep(30);}}}",
    )["rows"][0]
    component = row["source_components"][0]
    assert component["milliseconds"] == 90 and any("i<count" in x for x in component["factors"])
    assert row["total_ms"] is None


def test_verified_ui_wrapper_keeps_conditional_background_wait(tmp_path, monkeypatch):
    from app.modules.action_timing import source_ui_actions

    code = (
        "namespace AKRS.ZX2200.Infrastructure.Service {class ControlService {"
        "public static void UIActionAsync(object o,Action action){Task.Run(action);}}}"
        "namespace Demo {using AKRS.ZX2200.Infrastructure.Service;class Panel {"
        "public void Start(object sender){sender.UIActionAsync(()=>Thread.Sleep(1000));}}}"
    )
    monkeypatch.setattr(
        source_ui_actions, "SOURCE_SHA256", hashlib.sha256(code.encode()).hexdigest()
    )
    result = report(tmp_path, code)
    row = next(r for r in result["rows"] if r["class_name"] == "Panel")
    assert row["total_ms"] is None and row["known_delay_min_ms"] == 0
    assert any(
        x["scope"] == "background" and x["milliseconds"] == 1000 for x in row["known_components"]
    )
    assert any("互斥" in y for x in row["missing_requirements"] for y in x["required"])


def test_sdk_out_parameter_does_not_keep_old_delay(tmp_path):
    row = report(
        tmp_path,
        "class Demo{public void Start(){int delay=999;"
        "GTN.mc.GTN_GetAdcValue(out delay);Thread.Sleep(delay);}} ",
    )["rows"][0]
    assert row["known_delay_min_ms"] == 0 and row["total_ms"] is None
    assert next(x for x in row["stages"] if x["kind"] == "delay")["milliseconds"] is None


@pytest.mark.parametrize(
    "args", ["(int n)=>Thread.Sleep(n),param:7", "param:7,action:(int n)=>Thread.Sleep(n)"]
)
def test_ui_named_callback_parameters_are_forwarded(tmp_path, monkeypatch, args):
    from app.modules.action_timing import source_ui_actions

    code = (
        "namespace AKRS.ZX2200.Infrastructure.Service {class ControlService {"
        "public static void UIActionAsync<T>(object o,Action<T> action,"
        "List<Control> controls=null,T param=default){}}}"
        "namespace Demo {using AKRS.ZX2200.Infrastructure.Service;class Panel {"
        "public void Start(object sender){sender.UIActionAsync(" + args + ");}}}"
    )
    monkeypatch.setattr(
        source_ui_actions, "SOURCE_SHA256", hashlib.sha256(code.encode()).hexdigest()
    )
    row = next(r for r in report(tmp_path, code)["rows"] if r["class_name"] == "Panel")
    assert any(
        s["kind"] == "delay" and s["milliseconds"] == 7 and s["background"] for s in row["stages"]
    )


def test_motion_known_request_values_are_not_listed_as_missing():
    from app.modules.action_timing.source_requirements import stage_requirements

    stage = {
        "kind": "motion",
        "code": "axis.AbsoluteMove(movePara)",
        "motion_model": {
            "target": 5,
            "velocity": 1,
            "acceleration": 10,
            "deceleration": 10,
            "jerk": 0.02,
            "start_position": None,
            "time_unit": "unproven",
        },
    }
    category, missing = stage_requirements(stage)
    assert category == "motion"
    assert any("起点" in x for x in missing) and any("单位" in x for x in missing)
    assert not any(
        "目标或位移" in x or "加速度" in x or "减速度" in x or "有效速度" in x for x in missing
    )


def test_conditional_component_explains_prior_guard(tmp_path):
    row = report(
        tmp_path,
        "class Demo{public void Start(bool configured){"
        "if(!configured)throw new Exception();Thread.Sleep(50);}} ",
    )["rows"][0]
    assert row["source_components"][0]["milliseconds"] == 50
    assert "!(!configured)" in row["source_components"][0]["conditions"]


def test_both_return_branches_do_not_expose_unreachable_wait(tmp_path):
    row = report(
        tmp_path,
        "class Demo{public void Start(bool ready){"
        "if(ready)return;else return;Thread.Sleep(999);}} ",
    )["rows"][0]
    assert not row["source_components"]


def test_goto_label_can_reach_literal_after_earlier_exit(tmp_path):
    row = report(
        tmp_path, "class Demo{public void Start(){goto Next;return;Next:Thread.Sleep(5);}} "
    )["rows"][0]
    assert any(x["milliseconds"] == 5 for x in row["source_components"])


def test_single_cycle_component_does_not_multiply_outer_service_loop(tmp_path):
    folder = tmp_path / "TransportSystem/Tasks"
    folder.mkdir(parents=True)
    (folder / "TransportTask.cs").write_text(
        "class TransportTask{public void StartDryRun(){Task.Run(()=>{"
        "while(Signal.WaitStart()){Thread.Sleep(500);}});}}",
        encoding="utf-8",
    )
    row = next(
        r
        for r in SourceTiming(Workspace(tmp_path)).report()["rows"]
        if r["analysis_unit"] == "single_cycle"
    )
    assert row["source_components"][0]["milliseconds"] == 500
    assert row["source_components"][0]["factors"] == []


def test_task_callback_keeps_100ms_per_loop_without_adding_to_launcher(tmp_path):
    row = next(
        r
        for r in report(
            tmp_path,
            "class Demo{void Start(int count){Task.Run(()=>{"
            "for(int i=0;i<count;i++){if(Cancel())return;Thread.Sleep(100);}},token);}}",
        )["rows"]
        if r["method"] == "Start"
    )
    part = next(part for part in row["source_components"] if part.get("deferred"))
    assert part["milliseconds"] == 100
    assert any("count" in factor for factor in part["factors"])
    assert any("Task.Run" in condition for condition in part["conditions"])
    assert row["known_delay_min_ms"] == 0 and row["total_ms"] != 100
    assert any(
        item["background"] and any("count" in value for value in item["required"])
        for item in row["missing_requirements"]
    )


def test_saved_callback_task_keeps_10ms_poll_but_is_not_executed(tmp_path):
    row = next(
        r
        for r in report(
            tmp_path,
            "class Demo{void Start(int count){Action notify=()=>Task.Run(()=>{"
            "while(count>0){Thread.Sleep(10);count--;}});}}",
        )["rows"]
        if r["method"] == "Start"
    )
    part = next(part for part in row["source_components"] if part.get("deferred"))
    assert part["milliseconds"] == 10
    assert any("外层保存的回调" in condition for condition in part["conditions"])
    assert not any(stage["kind"] == "delay" for stage in row["stages"])
    assert row["known_delay_min_ms"] == row["known_delay_max_ms"] == 0


@pytest.mark.parametrize(
    "body",
    [
        "return;Task.Run(()=>Thread.Sleep(999));",
        "if(false)Task.Run(()=>Thread.Sleep(999));",
        "for(int i=120;i<=0;i--)Task.Run(()=>Thread.Sleep(999));",
    ],
)
def test_unreachable_task_creation_does_not_create_wait_component(tmp_path, body):
    row = next(
        r
        for r in report(tmp_path, f"class Demo{{void Start(){{{body}}}}}")["rows"]
        if r["method"] == "Start"
    )
    assert not row["source_components"]


def test_same_named_source_task_is_not_external_task_dispatch(tmp_path):
    row = next(
        r
        for r in report(
            tmp_path,
            "class Task{public static void Run(Action callback){}}"
            "class Demo{void Start(){Task.Run(()=>Thread.Sleep(999));}}",
        )["rows"]
        if r["method"] == "Start"
    )
    assert not row["source_components"]


def test_unreachable_task_body_wait_is_not_a_component(tmp_path):
    row = next(
        r
        for r in report(
            tmp_path, "class Demo{void Start(){Task.Run(()=>{return;Thread.Sleep(999);});}}"
        )["rows"]
        if r["method"] == "Start"
    )
    assert not row["source_components"]


@pytest.mark.parametrize(
    "body",
    [
        "return null;",
        "if(enabled)return null;return (Task)null;",
    ],
)
def test_explicit_null_task_return_has_no_task_completion_wait(tmp_path, body):
    row = next(
        r
        for r in report(
            tmp_path,
            f"class Demo{{Task Start(bool enabled){{if(false)return Task.Delay(99);{body}}}}}",
        )["rows"]
        if r["method"] == "Start"
    )
    assert row["total_ms"] == 0 and row["execution_status"] == "complete"
    assert "未创建任务" in row["status_reason"]
    assert not row["missing_requirements"]


def test_null_task_keeps_waits_before_return(tmp_path):
    row = report(tmp_path, "class Demo{Task Start(){Thread.Sleep(7);return null;}} ")["rows"][0]
    assert row["total_ms"] == row["known_delay_min_ms"] == 7
    assert "未创建任务" in row["status_reason"]


@pytest.mark.parametrize("body", ["return task;", "if(enabled)return Task.Delay(10);return null;"])
def test_unbound_or_mixed_task_return_keeps_specific_analysis_reason(tmp_path, body):
    row = next(
        r
        for r in report(
            tmp_path,
            f"class Demo{{Task Start(Task task,bool enabled){{if(false)return Task.Delay(99);{body}}}}}",
        )["rows"]
        if r["method"] == "Start"
    )
    assert row["total_ms"] is None
    assert "未创建任务" not in row["status_reason"]
    assert any(stage["label"] == "返回任务的完成关系未绑定" for stage in row["stages"])
    assert any(
        "返回分支" in value for item in row["missing_requirements"] for value in item["required"]
    )
