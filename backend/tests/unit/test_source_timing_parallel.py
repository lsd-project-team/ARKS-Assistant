"""Parallel.ForEach不保证固定并行度；共享写入不能按隔离副本假定为常量。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("methods", "body", "bounds"),
    [
        ("", "Parallel.ForEach(new[]{20,30},ms=>Thread.Sleep(ms));", (30, 50)),
        ("", "Parallel.ForEach(new[]{20},ms=>Thread.Sleep(ms));", (20, 20)),
        ("", "Parallel.ForEach(new int[]{},ms=>Thread.Sleep(999));", (0, 0)),
        ("", "Parallel.ForEach(new[]{0,0},ms=>Thread.Sleep(ms));", (0, 0)),
        ("", "Parallel.ForEach(Enumerable.Range(1,3),ms=>Thread.Sleep(ms*10));", (30, 60)),
        ("", "Parallel.ForEach(new[]{20,30},(ms,state)=>Thread.Sleep(ms));", (30, 50)),
        (
            "",
            "Parallel.ForEach(new[]{5,5,5},(ms,state,index)=>Thread.Sleep((int)index*10));",
            (20, 30),
        ),
        (
            "void Pause(int ms){Thread.Sleep(ms);}",
            "Parallel.ForEach(new[]{20,30},Pause);",
            (30, 50),
        ),
        ("", "int delay=5;Parallel.ForEach(new[]{20,30},ms=>Thread.Sleep(ms+delay));", (35, 60)),
        (
            "",
            "Parallel.ForEach(new[]{20,30},new ParallelOptions{MaxDegreeOfParallelism=1},"
            "ms=>Thread.Sleep(ms));",
            (50, 50),
        ),
        (
            "",
            "Parallel.ForEach(new[]{20,30},new ParallelOptions{MaxDegreeOfParallelism=2},"
            "ms=>Thread.Sleep(ms));",
            (30, 50),
        ),
        (
            "",
            "var options=new ParallelOptions{MaxDegreeOfParallelism=1};"
            "options.MaxDegreeOfParallelism=2;Parallel.ForEach(new[]{20,30},options,ms=>Thread.Sleep(ms));",
            (30, 50),
        ),
        (
            "int[] Values(){Thread.Sleep(5);return new[]{20,30};}",
            "Parallel.ForEach(body:ms=>Thread.Sleep(ms),source:Values());",
            (35, 55),
        ),
        (
            "",
            "Parallel.ForEach(new[]{20,30},ms=>{int delay=ms;"
            "Action read=()=>Thread.Sleep(delay);read();});",
            (30, 50),
        ),
        ("", "Parallel.ForEach(new[]{20,30},ms=>Task.Run(()=>Thread.Sleep(999)));", (0, 0)),
        (
            "",
            "Parallel.ForEach(new[]{20,30},async ms=>{Thread.Sleep(3);await Task.Delay(ms);"
            "Thread.Sleep(2);});",
            (3, 6),
        ),
    ],
)
def test_known_parallel_work_keeps_valid_software_delay_bounds(methods, body, bounds):
    result = analyze(f"class Demo {{{methods}public int DoWork(){{{body}return 0;}}}}")
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == bounds
    assert result["total_ms"] == (bounds[0] if bounds[0] == bounds[1] else None)
    if "new int[]{}" in body:
        assert not any(stage.get("milliseconds") == 999 for stage in result["stages"])


@pytest.mark.parametrize(
    "body",
    [
        "int[] values;Parallel.ForEach(values,ms=>Thread.Sleep(10));",
        "Parallel.ForEach(new[]{20,30},ExternalCallback());",
        "Parallel.ForEach(new[]{20,30},new ParallelOptions{MaxDegreeOfParallelism=0},"
        "ms=>Thread.Sleep(ms));",
        "Parallel.ForEach(new[]{20,30},new ParallelOptions{MaxDegreeOfParallelism=-2},"
        "ms=>Thread.Sleep(ms));",
        "Parallel.ForEach(new[]{20,30},new ParallelOptions{CancellationToken=token},"
        "ms=>Thread.Sleep(ms));",
        "Parallel.ForEach(new[]{20,30},(ms,state)=>{state.Stop();Thread.Sleep(ms);});",
        "Parallel.ForEach(new[]{20,30},(ms,state)=>{state.Break();Thread.Sleep(ms);});",
    ],
)
def test_unknown_count_control_or_configuration_cannot_become_a_fixed_parallel_duration(body):
    result = analyze(f"class Demo {{public int DoWork(){{{body}return 0;}}}}")
    assert result["total_ms"] is None


@pytest.mark.parametrize(
    "body",
    [
        "int delay=5;Parallel.ForEach(new[]{20,30},ms=>{delay=ms;Thread.Sleep(delay);});",
        "Parallel.ForEach(new[]{20,30},ms=>{delay=ms;Thread.Sleep(delay);});",
    ],
)
def test_parallel_shared_writes_do_not_produce_isolated_copy_delay_values(body):
    result = analyze(f"class Demo {{int delay=5;public int DoWork(){{{body}return 0;}}}}")
    assert result["total_ms"] is None and result["known_delay_max_ms"] is None
    assert result["known_delay_min_ms"] == 0


def test_fixed_delay_survives_an_unknown_shared_delay_and_the_final_state_is_not_guessed():
    result = analyze("""class Demo {int delay=5;public int DoWork(){
        Parallel.ForEach(new[]{20,30},ms=>{Thread.Sleep(5);delay=ms;Thread.Sleep(delay);});
        Thread.Sleep(delay);return 0;}}""")
    assert result["known_delay_min_ms"] == 5
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None


def test_parallel_callback_locals_and_new_objects_are_not_shared_between_iterations():
    result = analyze("""class Box {public int delay;}class Demo {public int DoWork(){
        Parallel.ForEach(new[]{20,30},ms=>{var box=new Box{delay=ms};Thread.Sleep(box.delay);});
        return 0;}}""")
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == (30, 50)


def test_parallel_like_source_method_uses_its_actual_body():
    result = analyze("""class Parallel {public static void ForEach(int[] items,Action<int> cb){
        Thread.Sleep(17);}}class Demo {public int DoWork(){
        Parallel.ForEach(new[]{20,30},ms=>Thread.Sleep(999));return 0;}}""")
    assert result["total_ms"] == 17
    assert not any(stage.get("milliseconds") == 999 for stage in result["stages"])


@pytest.mark.parametrize("degree", [1, 2])
def test_waiting_on_the_same_existing_task_does_not_multiply_its_duration_by_the_degree(degree):
    result = analyze(f"""class Demo {{public int DoWork(){{var task=Task.Delay(20);
        Parallel.ForEach(new[]{{1,2,3,4,5,6}},
            new ParallelOptions{{MaxDegreeOfParallelism={degree}}},
            value=>task.Wait());return 0;}}}}""")
    assert result["known_delay_min_ms"] <= 20 <= result["known_delay_max_ms"]


def test_unknown_axis_list_retains_the_real_callback_receiver_type():
    result = analyze("""class Axis {public void StopMove(bool wait,bool abrupt){Thread.Sleep(17);}}
        class Demo {List<Axis> axes;public int DoWork(){
        Parallel.ForEach(axes,(axis,state,index)=>axis.StopMove(false,true));return 0;}}""")
    assert result["known_delay_min_ms"] == 0 and result["known_delay_max_ms"] is None
    assert any(
        stage["method"] == "Axis.StopMove" and stage.get("milliseconds") == 17
        for stage in result["stages"]
    )


def test_shared_list_mutation_cannot_turn_a_concurrent_count_into_a_constant():
    result = analyze("""using System.Collections.Generic;class Demo {public int DoWork(){
        var items=new List<int>();
        Parallel.ForEach(new[]{1,2},i=>{items.Add(i);Thread.Sleep(items.Count);});
        return 0;}}""")
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None


def test_shared_task_reassignment_does_not_reuse_a_private_task_index():
    result = analyze("""class Demo {public int DoWork(){var task=Task.Delay(5);
        Parallel.ForEach(new[]{20,30},ms=>{task=Task.Delay(ms);task.Wait();});return 0;}}""")
    assert result["known_delay_min_ms"] == 0
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None


def test_a_second_execution_of_the_same_parallel_loop_gets_a_new_loop_state():
    result = analyze("""class Demo {public int DoWork(){for(int pass=0;pass<2;pass++){
        Parallel.ForEach(new[]{20,30},(ms,state)=>{if(pass==0)state.Stop();Thread.Sleep(ms);});}
        return 0;}}""")
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == (50, 100)


def test_large_known_parallel_input_retains_the_unexpanded_remainder():
    result = analyze("""class Demo {public int DoWork(){
        Parallel.ForEach(Enumerable.Range(0,1000),i=>Thread.Sleep(10));return 0;}}""")
    assert result["truncated"] and result["known_delay_max_ms"] is None
    assert result["total_ms"] is None


@pytest.mark.parametrize(
    "body",
    [
        "var local=new[]{ms};local[0]=ms;Thread.Sleep(local[0]);",
        "var local=new System.Collections.Generic.List<int>();"
        "local.Add(ms);Thread.Sleep(local[0]);",
        "var local=new[]{ms}.ToArray();local[0]=ms;Thread.Sleep(local[0]);",
    ],
)
def test_callback_private_collections_do_not_become_shared_state(body):
    result = analyze(f"""class Demo {{public int DoWork(){{
        Parallel.ForEach(new[]{{20,30}},ms=>{{{body}}});return 0;}}}}""")
    assert (result["known_delay_min_ms"], result["known_delay_max_ms"]) == (30, 50)


def test_a_mutated_source_array_cannot_supply_pre_mutation_callback_values():
    result = analyze("""class Demo {public int DoWork(){var values=new[]{20,30};
        Parallel.ForEach(values,ms=>{values[1]=999;Thread.Sleep(ms);});return 0;}}""")
    assert result["known_delay_max_ms"] is None
    assert result["total_ms"] is None


def test_a_published_private_array_can_be_modified_through_the_shared_reference():
    result = analyze("""class Demo {int[] shared=new[]{5};public int DoWork(){
        Parallel.ForEach(new[]{20,30},ms=>{var local=new[]{ms};shared=local;
            shared[0]=999;Thread.Sleep(local[0]);});return 0;}}""")
    assert result["known_delay_max_ms"] is None
    assert result["total_ms"] is None


def test_shared_write_discovery_rechecks_branches_exposed_by_other_iterations():
    result = analyze("""class Demo {int a=0,b=100;public int DoWork(){
        Parallel.ForEach(new[]{0,1},i=>{if(i==0)a=1;if(i==1 && a==1)b=1;Thread.Sleep(b);});
        return 0;}}""")
    assert result["known_delay_min_ms"] == 0 and result["known_delay_max_ms"] is None


def test_incomplete_shared_write_discovery_invalidates_the_following_member_read(monkeypatch):
    from app.modules.action_timing import source_parallel

    monkeypatch.setattr(source_parallel, "MAX_SHARED_ROUNDS", 1)
    result = analyze("""class Demo {int a=0,b=100;public int DoWork(){
        Parallel.ForEach(new[]{0,1},i=>{if(i==0)a=1;if(i==1 && a==1)b=1;});
        Thread.Sleep(b);return 0;}}""")
    assert result["truncated"] and result["known_delay_min_ms"] == 0
    assert result["known_delay_max_ms"] is None and result["total_ms"] is None
