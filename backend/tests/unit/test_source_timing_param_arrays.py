"""params正常数组与展开形式使用同一份正文；参数顺序、别名与空数组分别验证。"""

from pathlib import Path

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("declarations", "body", "expected"),
    [
        ("void Run(params int[] ms){foreach(int n in ms)Thread.Sleep(n);}", "Run(7,11);", 18),
        ("void Run(params int[] ms){foreach(int n in ms)Thread.Sleep(n);}", "Run();", 0),
        (
            "void Run(params int[] ms){foreach(int n in ms)Thread.Sleep(n);}",
            "Run(new[]{7,11});",
            18,
        ),
        (
            "void Run(params int[] ms){foreach(int n in ms)Thread.Sleep(n);}",
            "Run(ms:new[]{7,11});",
            18,
        ),
        ("void Run(params object[] args){Thread.Sleep(args.Length);}", "Run(new int[]{7,11});", 1),
        (
            "void Run(params int[] ms){ms[0]=13;}",
            "int[] ms=new[]{7};Run(ms);Thread.Sleep(ms[0]);",
            13,
        ),
        (
            "void Run(int ms=2,params int[] rest){Thread.Sleep(ms);"
            "foreach(int n in rest)Thread.Sleep(n);}",
            "Run();",
            2,
        ),
        (
            "void Run(int ms=2,params int[] rest){Thread.Sleep(ms);"
            "foreach(int n in rest)Thread.Sleep(n);}",
            "Run(rest:new[]{7,11});",
            20,
        ),
        (
            "void Run(int ms=2,params int[] rest){Thread.Sleep(ms);"
            "foreach(int n in rest)Thread.Sleep(n);}",
            "Run(3,5,7);",
            15,
        ),
        (
            "int Read(){Thread.Sleep(2);return 7;}"
            "void Run(params int[] ms){foreach(int n in ms)Thread.Sleep(n);}",
            "Run(Read(),Read());",
            18,
        ),
        (
            "void Run(Delegate cb,params object[] args){cb.DynamicInvoke(args);}",
            "Run((Action)(()=>Thread.Sleep(7)));",
            7,
        ),
        (
            "void Run(Delegate cb,params object[] args){cb.DynamicInvoke(args);}",
            "Action<int> cb=n=>Thread.Sleep(n);Run(cb,7);",
            7,
        ),
        (
            "void Run(Delegate cb,params object[] args){cb.DynamicInvoke(args);}",
            "Action<int> cb=n=>Thread.Sleep(n);Run(cb,new object[]{11});",
            11,
        ),
        (
            "void Run(Delegate cb,params object[] args){cb.DynamicInvoke(args);}",
            "Action<int> cb=n=>Thread.Sleep(n);Run(cb,args:new object[]{13});",
            13,
        ),
    ],
)
def test_param_array_forms_follow_their_actual_elements(declarations, body, expected):
    report = analyze(f"class Demo {{{declarations} public int DoWork(){{{body}return 0;}}}}")
    assert report["total_ms"] == expected


@pytest.mark.parametrize(
    ("kind", "callback", "args", "expected"),
    [
        ("Action", "()=>Thread.Sleep(19)", "new object[0]", 19),
        ("Func<Task>", "()=>Task.Delay(23)", "new object[0]", 23),
        ("Action<int>", "n=>Thread.Sleep(n)", "new object[]{29}", 29),
    ],
)
def test_actual_async_helper_reaches_the_bound_callback(kind, callback, args, expected):
    root = Path(__file__).resolve().parents[3]
    helper = (root / "trunk/AKRS.ZX2200/Infrastructure/Utils/AsyncHelper.cs").read_text(
        encoding="utf-8-sig"
    )
    report = analyze(
        f"""using AKRS.ZX2200.Infrastructure.Utils;
        class Demo {{public int DoWork(){{{kind} cb={callback};
        AsyncHelper.ExecuteAsync(cb,null,{args}).Wait();return 0;}}}}""",
        helper,
    )
    stages = [stage for stage in report["stages"] if stage["kind"] == "delay"]
    assert len(stages) == 1
    assert stages[0]["milliseconds"] == expected and not stages[0]["background"]
    assert report["total_ms"] is None  # 源码catch的异常恢复条件继续保留。
    assert any(
        stage["kind"] == "unresolved" and "catch" in stage["code"] for stage in report["stages"]
    )


def test_fixed_arity_overload_wins_over_an_equally_typed_expanded_param_array():
    report = analyze("""class Demo {void Run(int n){Thread.Sleep(n);}
        void Run(params int[] values){Thread.Sleep(999);}
        public int DoWork(){Run(7);return 0;}}""")
    assert report["total_ms"] == 7
