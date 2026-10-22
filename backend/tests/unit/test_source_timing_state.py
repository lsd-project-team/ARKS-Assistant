"""运行中的参数修改必须进入后续耗时，不能重新读取声明初值。"""

from tests.unit.test_source_timing_dependencies import analyze


def test_called_method_updates_same_instance_and_explicit_this_alias():
    result = analyze("""class Demo {int delay=5;
        void Configure(){this.delay=7;}
        public int DoWork(){Configure();Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 7


def test_static_field_change_is_shared_across_classes_and_calls():
    result = analyze("""class Settings {public static int Delay=5;
        public static void Configure(){Delay=9;}}
        class Demo {public int DoWork(){Settings.Configure();
        Thread.Sleep(Settings.Delay);return 0;}}""")
    assert result["total_ms"] == 9


def test_new_instances_keep_separate_state_and_object_aliases_share_it():
    result = analyze("""class Settings {public int Delay=5;}
        class Demo {public int DoWork(){var first=new Settings();
        var second=new Settings();var alias=first;alias.Delay=7;
        Thread.Sleep(first.Delay);Thread.Sleep(second.Delay);return 0;}}""")
    assert result["total_ms"] == 12


def test_object_parameter_writes_reach_caller_without_changing_other_objects():
    result = analyze("""class Settings {public int Delay=5;}
        class Demo {void Configure(Settings settings){settings.Delay=7;}
        public int DoWork(){var first=new Settings();var second=new Settings();
        Configure(first);Thread.Sleep(first.Delay);Thread.Sleep(second.Delay);return 0;}}""")
    assert result["total_ms"] == 12


def test_getter_and_setter_share_the_receivers_backing_field():
    result = analyze("""class Settings {int delay=5;
        public int Delay {get{return delay;} set{delay=value+2;}}}
        class Demo {public int DoWork(){var settings=new Settings();
        settings.Delay=7;Thread.Sleep(settings.Delay);return 0;}}""")
    assert result["total_ms"] == 9


def test_unknown_receiver_alias_cannot_reuse_another_members_initial_value():
    result = analyze("""class Settings {public int Delay=5;}
        class Demo {Settings first,second;
        public int DoWork(){first.Delay=7;Thread.Sleep(second.Delay);return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None


def test_ref_and_out_parameters_change_the_callers_delay():
    result = analyze("""class Demo {void Configure(ref int delay){delay=7;}
        void Read(out int delay){delay=3;}
        public int DoWork(){int delay=5;Configure(ref delay);Thread.Sleep(delay);
        Read(out delay);Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 10


def test_unresolved_out_parameter_invalidates_the_previous_local_value():
    result = analyze("""class Demo {External api;
        public int DoWork(){int delay=5;api.TryRead(out delay);
        Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None


def test_background_write_has_unknown_order_and_awaited_write_is_visible():
    background = analyze("""class Demo {int delay=5;
        public int DoWork(){Task.Run(()=>{delay=7;});Thread.Sleep(delay);return 0;}}""")
    assert background["total_ms"] is None
    assert background["known_delay_max_ms"] is None
    joined = analyze("""class Demo {int delay=5;
        public async Task DoWork(){await Task.Run(()=>{delay=7;});
        Thread.Sleep(delay);}}""")
    assert joined["total_ms"] == 7


def test_conditional_write_is_merged_without_applying_the_other_branch():
    result = analyze("""class Demo {bool condition;int delay=5;
        public int DoWork(){var x=condition ? Change() : 0;
        Thread.Sleep(delay);return 0;}
        int Change(){delay=7;return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None


def test_loop_write_does_not_restore_the_initial_field_value():
    result = analyze("""class Demo {int delay=5;bool repeat;
        public int DoWork(){while(repeat){delay=7;}Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] is None
    assert result["known_delay_max_ms"] is None


def test_constructor_state_is_used_after_creation_and_does_not_change_caller_this():
    result = analyze("""class Settings {public int Delay;
        public Settings(int delay){Delay=delay;}}
        class Demo {int delay=3;public int DoWork(){var settings=new Settings(7);
        Thread.Sleep(settings.Delay);Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 10


def test_recursive_receiver_property_stays_unknown_without_unbounded_evaluation():
    result = analyze("""class Settings {public Settings Next=>this;
        public int Delay {get{return Next.Delay;}}}
        class Demo {Settings settings;public int DoWork(){
        Thread.Sleep(settings.Delay);return 0;}}""")
    assert result["total_ms"] is None


def test_object_initializer_custom_setter_updates_the_value_read_by_getter():
    result = analyze("""class Settings {int delay=5;
        public int Delay {get{return delay;} set{delay=value+2;}}}
        class Demo {public int DoWork(){var settings=new Settings {Delay=7};
        Thread.Sleep(settings.Delay);return 0;}}""")
    assert result["total_ms"] == 9


def test_value_projection_cache_is_limited_to_one_evaluation_and_parameter_context():
    result = analyze("""class Demo {int delay=5;int Echo(int value)=>value;
        public int DoWork(){Thread.Sleep(Echo(3)+Echo(7));Thread.Sleep(delay);
        delay=7;Thread.Sleep(delay);return 0;}}""")
    assert result["total_ms"] == 22
