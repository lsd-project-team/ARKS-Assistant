"""相同源码的互斥跳转不能因Python散列随机化改变统计依据的展开顺序。"""

import json
import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("seed", ["1", "2", "3", "7"])
def test_unknown_jump_branches_keep_source_order_across_processes(seed):
    source = """class Demo {bool option;public int DoWork(){
        if(option)goto First;else goto Second;
        First:Thread.Sleep(11);return 0;
        Second:Thread.Sleep(13);return 0;}}"""
    script = """import json,sys
from tests.unit.test_source_timing_dependencies import analyze
result=analyze(json.load(sys.stdin))
print(json.dumps({'bounds':[result['known_delay_min_ms'],result['known_delay_max_ms']],
 'delays':[row['milliseconds'] for row in result['stages'] if row['kind']=='delay']}))
"""
    process = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps(source),
        text=True,
        capture_output=True,
        timeout=15,
        env={**os.environ, "PYTHONHASHSEED": seed},
        check=True,
    )
    assert json.loads(process.stdout) == {"bounds": [11, 13], "delays": [11, 13]}
