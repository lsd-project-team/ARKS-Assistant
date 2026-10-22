"""参数名决定绑定位置，源码中的实参顺序决定求值与副作用顺序。"""

import pytest

from tests.unit.test_source_timing_dependencies import analyze


@pytest.mark.parametrize(
    ("declarations", "body", "expected"),
    [
        ("void Pause(int first,int second){Thread.Sleep(first);}", "Pause(second:99, first:7);", 7),
        (
            "void Pause(int first=3,int second=99){Thread.Sleep(first);Thread.Sleep(second);}",
            "Pause(second:7);",
            10,
        ),
        (
            "void Pause(int first,int second=99){Thread.Sleep(first);Thread.Sleep(second);}",
            "Pause(first:3,7);",
            10,
        ),
        (
            "void Run(int ms=99,Action cb=null){Thread.Sleep(ms);cb?.Invoke();}",
            "Run(cb:()=>Thread.Sleep(7),ms:3);",
            10,
        ),
        (
            "void Pause(int a,string b){Thread.Sleep(7);}"
            "void Pause(string a,int b){Thread.Sleep(99);}",
            'Pause(b:"x",a:3);',
            7,
        ),
        ("int Echo(int first=99,int second=2)=>first;", "Thread.Sleep(Echo(second:7,first:3));", 3),
        (
            "void Configure(ref int first,ref int second){first=3;second=7;}",
            "int x=1;int y=2;Configure(second:ref y,first:ref x);Thread.Sleep(x);Thread.Sleep(y);",
            10,
        ),
        (
            "void Configure(ref int first,ref int second){first=3;second=7;}",
            "int x=1;int y=2;Configure(/*note*/second:ref y,first:ref x);"
            "Thread.Sleep(x);Thread.Sleep(y);",
            10,
        ),
        (
            "int delay=5;int Read()=>delay;int Change(){delay=9;return 3;}"
            "void Pause(int first,int second){Thread.Sleep(first);Thread.Sleep(second);}",
            "Pause(first:Read(),second:Change());",
            8,
        ),
        (
            "int delay=5;int Read()=>delay;int Change(){delay=9;return 3;}"
            "int Echo(int first,int second)=>first;",
            "Thread.Sleep(Echo(first:Read(),second:Change()));",
            5,
        ),
        (
            "int delay=5;int Change(){delay=9;return 0;}"
            "void Pause(ref int first,int second){Thread.Sleep(first);}",
            "Pause(second:Change(),first:ref delay);",
            9,
        ),
        (
            "int delay=5;int Change(){delay=9;return 0;}"
            "void Pause(ref int first,int second){Thread.Sleep(first);}",
            "Pause(first:ref delay,second:Change());",
            9,
        ),
        (
            "void Pause(ref int first,ref int second){first=3;second=7;Thread.Sleep(first);}",
            "int value=5;Pause(second:ref value,first:ref value);Thread.Sleep(value);",
            14,
        ),
        (
            "int Echo(int first=3,int second=99)=>first;",
            "Thread.Sleep(Echo(second:7));",
            3,
        ),
        (
            "void Configure(out int value){value=3;}",
            "Configure(out _);Thread.Sleep(7);",
            7,
        ),
    ],
)
def test_named_arguments_and_evaluation_order(declarations, body, expected):
    result = analyze(f"class Demo {{{declarations} public int DoWork(){{{body} return 0;}}}}")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == expected
    assert result["total_ms"] == expected


@pytest.mark.parametrize("creation", ["new Worker(second:99,first:7)", "new Worker(first:7)"])
def test_named_constructor_including_optional_arguments(creation):
    result = analyze(f"""class Worker {{
        public Worker(int first,int second=99){{Thread.Sleep(first);}}}}
        class Demo {{public int DoWork(){{{creation};return 0;}}}}""")
    assert result["total_ms"] == 7


def test_named_this_and_base_constructor_parameters():
    result = analyze("""class Base {public Base(int first,int second){Thread.Sleep(first);}}
        class Worker:Base {public Worker():this(second:99,first:7){}
        public Worker(int first,int second):base(second:second,first:first){}}
        class Demo {public int DoWork(){new Worker();return 0;}}""")
    assert result["total_ms"] == 7


@pytest.mark.parametrize(
    "call",
    [
        "GetPause(other:7);",
        "GetPause(first:3,first:7);",
        "GetPause(second:7);",
        "GetPause(second:7,3);",
    ],
)
def test_invalid_named_source_call_is_not_silently_a_zero_cost_getter(call):
    result = analyze(f"""class Demo {{
        int GetPause(int first,int second=99){{Thread.Sleep(first);return 0;}}
        public int DoWork(){{{call}return 0;}}}}""")
    assert result["total_ms"] is None
    assert any(stage["kind"] == "unresolved" for stage in result["stages"])


def test_unknown_source_call_preserves_only_the_explicitly_resolved_delay_components():
    result = analyze("""class Demo {int GetPause(int first){Thread.Sleep(first);return 0;}
        public int DoWork(){GetPause(other:99);Thread.Sleep(7);return 0;}}""")
    assert result["known_delay_min_ms"] == result["known_delay_max_ms"] == 7
    assert result["total_ms"] is None and result["execution_status"] == "partial"


def test_method_group_receiver_is_captured_before_later_argument_changes_it():
    result = analyze("""class Worker {public int Delay;public void Work(){Thread.Sleep(Delay);}}
        class Demo {Worker selected;Worker second;int Change(){selected=second;return 0;}
        void Run(Action cb,int unused){cb();}
        public int DoWork(){selected=new Worker {Delay=5};second=new Worker {Delay=9};
        Run(cb:selected.Work,unused:Change());return 0;}}""")
    assert result["total_ms"] == 5


def test_call_receiver_is_captured_before_arguments_change_it():
    result = analyze("""class Worker {public int Delay;
        public void Work(int unused){Thread.Sleep(Delay);}}
        class Demo {Worker selected;Worker second;int Change(){selected=second;return 0;}
        public int DoWork(){selected=new Worker {Delay=5};second=new Worker {Delay=9};
        selected.Work(Change());return 0;}}""")
    assert result["total_ms"] == 5


def test_return_projection_keeps_the_original_call_receiver():
    result = analyze("""class Worker {public int Delay;
        public int Read(int unused)=>Delay;}
        class Demo {Worker selected;Worker second;int Change(){selected=second;return 0;}
        public int DoWork(){selected=new Worker {Delay=5};second=new Worker {Delay=9};
        Thread.Sleep(selected.Read(Change()));return 0;}}""")
    assert result["total_ms"] == 5


def test_ref_member_keeps_its_original_receiver_when_later_argument_replaces_it():
    result = analyze("""class Worker {public int Delay;}
        class Demo {Worker selected;Worker second;int Change(){selected=second;return 0;}
        void Configure(ref int delay,int unused){delay=7;}
        public int DoWork(){selected=new Worker {Delay=5};second=new Worker {Delay=9};
        Worker original=selected;Configure(delay:ref selected.Delay,unused:Change());
        Thread.Sleep(original.Delay);Thread.Sleep(selected.Delay);return 0;}}""")
    assert result["total_ms"] == 16


def test_unknown_member_receivers_do_not_share_a_definite_reference_address():
    result = analyze("""class Worker {public int Delay;}
        class Demo {Worker first;Worker second;
        void Pause(ref int a,ref int b){a=3;b=7;Thread.Sleep(a);}
        public int DoWork(){Pause(ref first.Delay,ref second.Delay);return 0;}}""")
    # 两对象相同则Sleep(7)，不同则Sleep(3)，源码尚不能确定它们的实际引用。
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None
    assert all(s.get("milliseconds") is None for s in result["stages"] if s["kind"] == "delay")


def test_catalog_resolution_does_not_override_explicit_callback_parameter_type():
    from app.modules.action_timing.source_estimator import Estimator
    from app.modules.action_timing.source_index import SourceIndex, walk

    source = """class Demo {string n;void Pause(int n){Thread.Sleep(7);}
        void Pause(string n){Thread.Sleep(999);}
        public int DoWork(){Action<int> cb=(int n)=>Pause(n);cb(1);return 0;}}"""
    index = SourceIndex([{"path": "main.cs", "content": source, "version": "test"}])
    method = index.by_method[("Demo", "DoWork")][0]
    # 目录先用外层声明上下文读取lambda；实际执行须使用lambda自己的int参数。
    for node in walk(method.body):
        if node.type == "invocation_expression":
            index.resolve(node, method)
    assert Estimator(index).estimate(method)["total_ms"] == 7
