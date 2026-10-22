"""依赖包内真实的固定等待必须进入模型，不能将 Wait 名字一概当作黑盒。"""

import hashlib

from app.modules.action_timing.source_estimator import Estimator
from app.modules.action_timing.source_index import SourceIndex, description


def analyze(source, dependency=""):
    documents = [("main.cs", source)]
    if dependency:
        documents.append(("package.cs", dependency))
    index = SourceIndex(
        [
            {
                "path": name,
                "content": content,
                "version": hashlib.sha256(content.encode()).hexdigest(),
                "project": name,
            }
            for name, content in documents
        ]
    )
    return Estimator(index).estimate(index.by_method[("Demo", "DoWork")][0])


def test_package_wait_includes_mandatory_do_sleep_and_unbounded_signal_time():
    result = analyze(
        """class Demo { Signal signal; public int DoWork() {
            signal.Wait(); Thread.Sleep(20); return 0; } }""",
        """class Signal { EventWaitHandle handle; public bool Wait() {
            do { Thread.Sleep(5); } while (!handle.WaitOne(100)); return true; } }""",
    )
    assert result["known_delay_min_ms"] == 25
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None
    assert result["wait_count"] == 1
    assert any(
        stage["path"] == "package.cs" and stage["milliseconds"] == 5
        for stage in result["stages"]
        if stage["kind"] == "delay"
    )
    assert any(
        stage["kind"] == "timeout" and stage["milliseconds"] == 100 for stage in result["stages"]
    )


def test_inherited_delay_uses_declaration_context_instead_of_caller_local_name():
    result = analyze(
        """class Base { const int DefaultDelay = 12; protected int Delay = DefaultDelay; }
        class Demo : Base { public int DoWork() {
            int DefaultDelay = 999; Thread.Sleep(Delay); return 0; } }"""
    )
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 12


def test_call_argument_delay_is_evaluated_before_target_method():
    result = analyze(
        """class Demo { public int DoWork() { Wait(GetDelay()); return 0; }
        int GetDelay() { Thread.Sleep(3); return 7; }
        void Wait(int ms) { Thread.Sleep(ms); } }"""
    )
    assert result["known_delay_min_ms"] == 10
    assert result["known_delay_max_ms"] == 10


def test_constructor_overwrite_cannot_reuse_field_initializer_as_effective_delay():
    result = analyze("""class Demo { int delay=5; Demo(int actual) { delay=actual; }
        public int DoWork() { Thread.Sleep(delay); return 0; } }""")
    assert result["known_delay_max_ms"] is None
    assert result["total_ms"] is None


def test_unknown_short_circuit_and_ternary_preserve_alternative_costs():
    short = analyze("""class Demo { public int DoWork() { if(flag && Slow()) {} return 0; }
        bool Slow() { Thread.Sleep(9); return true; } }""")
    assert (short["known_delay_min_ms"], short["known_delay_max_ms"]) == (0, 9)
    ternary = analyze("""class Demo { public int DoWork() {
        var unused = flag ? Slow() : Fast(); return 0; }
        int Slow() { Thread.Sleep(30); return 1; }
        int Fast() { Thread.Sleep(10); return 1; } }""")
    assert (ternary["known_delay_min_ms"], ternary["known_delay_max_ms"]) == (10, 30)


def test_switch_mutation_invalidates_old_local_delay():
    result = analyze("""class Demo { public int DoWork() { int delay=10;
        switch(flag) { case 1: delay=20; break; default: delay=30; break; }
        Thread.Sleep(delay); return 0; } }""")
    assert result["known_delay_max_ms"] is None
    assert result["total_ms"] is None


def test_simulated_machine_mode_does_not_override_unrelated_same_named_flag():
    result = analyze("""class Recipe { public bool IsDryCycle {get;set;} = false; }
        class Demo { Recipe recipe; public int DoWork() {
        if(recipe.IsDryCycle) Thread.Sleep(999); else Thread.Sleep(12); return 0; } }""")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 12


def test_unavailable_and_drycycle_skipped_are_not_missing_parameters():
    unavailable = analyze(
        """class Demo { public int DoWork() {
            throw new Exception("空跑暂不可执行"); Thread.Sleep(500); return 0; } }"""
    )
    assert unavailable["execution_status"] == "unavailable"
    assert unavailable["known_delay_min_ms"] is None
    assert "空跑暂不可执行" in unavailable["status_reason"]
    assert not any(stage["kind"] == "delay" for stage in unavailable["stages"])
    skipped = analyze(
        """class Demo { public void DoWork() {
            if (MachineStateModel.GetInstance().IsDryCycle) return; Thread.Sleep(500); } }"""
    )
    assert skipped["execution_status"] == "skipped"
    assert skipped["known_delay_min_ms"] == skipped["known_delay_max_ms"] == 0


def test_description_does_not_reuse_xml_comment_from_previous_method():
    source = """class Demo {
        /// <summary>上一个动作</summary>
        void Previous() {}
        public int DoWork() { return 0; }
    }"""
    index = SourceIndex([{"path": "x.cs", "content": source, "version": "v"}])
    method = index.by_method[("Demo", "DoWork")][0]
    assert description(method.unit.raw, method.node) == ""
