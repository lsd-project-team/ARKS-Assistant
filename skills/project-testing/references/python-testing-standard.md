# Python 测试规范 Skill

## 1. 目标

本 Skill 用于指导 AI 对 Python 项目进行：

- 测试分析
- 测试用例设计
- pytest 测试代码编写
- 测试执行
- 测试失败分析
- 覆盖率分析
- 测试代码质量审查
- 边界与异常场景补充
- 高风险代码的反例验证
- 必要时进行 Mutation Testing

核心原则：

> AI 生成测试代码不代表测试就是正确的。

> 测试的目标不是让代码覆盖率变高，而是尽可能发现真实缺陷。

---

# 2. 默认技术栈

Python 项目默认优先使用：

- pytest
- pytest-cov
- unittest.mock
- monkeypatch
- pytest.mark.parametrize
- pytest.fixture

根据项目实际情况，可以使用：

- Hypothesis：属性测试
- mutmut：Mutation Testing
- pytest-asyncio：异步代码测试

如果项目已经存在测试框架，应优先遵循项目现有规范，不要无理由更换测试框架。

---

# 3. 开始测试前必须做的事情

禁止直接读取一个函数后立即生成测试。

首先分析：

1. 项目结构
2. 测试目录
3. `pyproject.toml`
4. `pytest.ini`
5. `setup.cfg`
6. `requirements.txt`
7. 已有测试代码
8. 被测试模块的调用关系
9. 外部依赖
10. 项目已有测试运行方式

如果项目已经存在测试，应优先复用：

- fixture
- helper
- mock
- test utilities
- 测试数据

避免重复创建。

---

# 4. 测试对象分析

针对每个核心函数、类或模块，先分析：

```text
输入
 ↓
处理逻辑
 ↓
输出
 ↓
副作用
```

同时识别：

```text
正常情况
边界情况
异常情况
非法输入
外部依赖
状态变化
并发
异步
缓存
文件
数据库
网络
```

如果业务规则无法从源码、文档或现有测试中确认：

```text
UNKNOWN_REQUIREMENT
```

不要擅自猜测关键业务行为。

---

# 5. Python 测试文件规范

测试文件默认：

```text
tests/
├── test_user.py
├── test_service.py
├── test_utils.py
└── conftest.py
```

测试函数命名：

```python
def test_login_with_wrong_password_returns_failure():
    ...
```

推荐：

```text
test_<行为>_<条件>_<预期结果>
```

禁止使用：

```python
def test_1():
    ...
```

测试类如果使用，应采用：

```python
class TestUserService:
    ...
```

---

# 6. 基础测试

示例：

生产代码：

```python
def add(a, b):
    return a + b
```

测试：

```python
def test_add():
    assert add(1, 2) == 3
```

测试必须明确验证结果。

不推荐：

```python
def test_add():
    result = add(1, 2)
    assert result is not None
```

因为这种断言通常无法发现真正的逻辑错误。

---

# 7. 测试用例设计

每个重要功能至少考虑以下测试类型。

## 7.1 正常场景

例如：

```python
def test_divide_normal():
    assert divide(10, 2) == 5
```

---

## 7.2 边界场景

重点测试：

```text
0
1
最小值
最大值
最小值 - 1
最大值 + 1
空字符串
空列表
空字典
None
极大数据
极小数据
```

例如：

```python
@pytest.mark.parametrize(
    "value",
    [0, 1, 100]
)
def test_validate_value(value):
    ...
```

如果存在明确范围：

```text
0 <= value <= 100
```

必须重点测试：

```text
-1
0
1
99
100
101
```

---

# 8. 异常测试

如果代码定义了异常行为，必须验证异常。

例如：

```python
def divide(a, b):
    if b == 0:
        raise ValueError("cannot divide by zero")

    return a / b
```

测试：

```python
def test_divide_by_zero_raises_value_error():
    with pytest.raises(ValueError):
        divide(10, 0)
```

如果异常信息属于业务契约，可以进一步验证：

```python
def test_divide_by_zero_error_message():
    with pytest.raises(ValueError, match="cannot divide by zero"):
        divide(10, 0)
```

不要无意义地测试所有异常消息。

---

# 9. 参数化测试

多个输入具有相同测试逻辑时，优先使用：

```python
@pytest.mark.parametrize(
    "a,b,expected",
    [
        (1, 2, 3),
        (5, 6, 11),
        (-1, 1, 0),
        (100, 200, 300),
    ],
)
def test_add(a, b, expected):
    assert add(a, b) == expected
```

参数化测试可以减少重复代码，同时提高边界覆盖。

---

# 10. Fixture 规范

共享测试资源使用 `pytest.fixture`。

例如：

```python
@pytest.fixture
def user():
    return User(
        name="test_user",
        age=20,
    )
```

测试：

```python
def test_user_name(user):
    assert user.name == "test_user"
```

Fixture 应该：

- 简洁
- 单一职责
- 避免过度嵌套
- 避免隐藏重要测试行为

不要为了减少几行代码，把所有测试逻辑都塞进 fixture。

---

# 11. conftest.py

项目级共享 fixture 可以放在：

```text
tests/conftest.py
```

例如：

```python
@pytest.fixture
def mock_database():
    ...
```

但是不要把大量与单个测试模块相关的 fixture 全部放到 `conftest.py`。

原则：

> 共享程度决定 fixture 的放置位置。

---

# 12. Mock 规范

以下依赖通常应该 Mock：

```text
网络请求
数据库
第三方 API
文件系统
时间
随机数
消息队列
硬件设备
外部服务
```

例如：

```python
from unittest.mock import Mock


def test_get_temperature():
    sensor = Mock()
    sensor.read.return_value = 25.5

    result = get_temperature(sensor)

    assert result == 25.5
```

---

# 13. Mock 的重要原则

不要为了让测试简单而 Mock 被测试对象本身。

错误：

```python
service = Mock()
service.get_user.return_value = ...
```

然后测试：

```python
assert service.get_user(...) == ...
```

这实际上是在测试 Mock。

正确方式是：

> Mock 外部依赖，真实执行被测试逻辑。

例如：

```text
真实：
UserService
   ↓
Mock Database
```

而不是：

```text
Mock UserService
   ↓
Mock Database
```

---

# 14. patch 规范

使用 `patch` 时，应优先 patch：

> 被测试模块实际使用的位置。

例如：

```python
# service.py

from requests import get

def fetch_data():
    return get(...)
```

测试时应 patch：

```python
patch("service.get")
```

而不是盲目：

```python
patch("requests.get")
```

原则：

> Patch where the object is used, not where it is defined.

---

# 15. monkeypatch

对于环境变量、配置、函数替换等场景，可以使用：

```python
def test_environment(monkeypatch):
    monkeypatch.setenv("ENV", "test")

    ...
```

测试结束后 pytest 会自动恢复。

---

# 16. 文件系统测试

涉及文件操作时，优先使用 pytest 的：

```python
tmp_path
```

例如：

```python
def test_save_file(tmp_path):
    file_path = tmp_path / "data.txt"

    save_data(file_path, "hello")

    assert file_path.read_text() == "hello"
```

不要让普通单元测试直接写入真实项目目录。

---

# 17. 时间测试

涉及：

```text
datetime
date
time
timeout
过期时间
定时任务
```

时，必须考虑时间依赖。

不要让测试依赖真实当前时间。

例如可以 Mock 时间来源，或者使用项目已有的时间抽象。

目标：

> 同一个测试在不同时间运行，结果应该稳定。

---

# 18. 随机数测试

如果代码使用：

```python
random
uuid
secrets
```

需要考虑测试可重复性。

对于普通业务逻辑，可以 Mock 随机来源：

```python
monkeypatch.setattr(...)
```

避免测试：

```python
assert random_result == 某个固定值
```

这种不稳定测试。

---

# 19. 异步代码

如果项目使用：

```python
async def
await
```

根据项目配置使用：

```text
pytest-asyncio
```

例如：

```python
@pytest.mark.asyncio
async def test_fetch_data():
    result = await fetch_data()

    assert result.status == "OK"
```

必须注意：

- await 是否正确
- 异常是否传播
- timeout
- cancellation
- 并发任务
- 重试

---

# 20. 数据库测试

数据库测试优先：

```text
测试数据库
临时数据库
事务回滚
Mock
```

避免普通单元测试连接生产数据库。

需要测试：

```text
新增
查询
修改
删除
重复数据
不存在的数据
事务失败
回滚
并发
唯一约束
```

---

# 21. API 测试

对于 FastAPI、Flask、Django 等项目，应区分：

```text
Unit Test
Integration Test
API Test
```

API 测试至少验证：

```text
HTTP Status
Response Body
字段类型
字段值
错误响应
参数校验
权限
认证
异常处理
```

不要只测试：

```python
assert response.status_code == 200
```

还应该验证关键业务数据。

---

# 22. 测试状态和副作用

不要只关注返回值。

例如：

```python
result = service.start()
```

除了：

```python
assert result is True
```

还要考虑：

```text
状态是否变化？
数据库是否更新？
事件是否发送？
依赖是否调用？
调用参数是否正确？
错误时是否回滚？
```

例如：

```python
mock_client.send.assert_called_once_with(
    "START"
)
```

---

# 23. AI 测试代码自审查

这是本 Skill 的核心要求。

AI 生成测试后，必须主动审查：

### 23.1 测试是否真的测试了目标逻辑？

不要出现：

```python
result = function()

assert result is not None
```

这种低价值测试。

---

### 23.2 测试是否只是重复实现？

例如：

```python
expected = a + b
assert add(a, b) == expected
```

如果 `add()` 本身的需求就是简单加法，这种测试仍然有价值，但对于复杂算法必须避免：

> 测试代码与生产代码采用完全相同的错误逻辑。

---

### 23.3 测试是否过度依赖实现细节？

优先验证：

```text
输入
→ 行为
→ 输出
```

而不是大量验证：

```text
内部变量
内部函数调用
私有实现
代码行结构
```

除非这些属于明确契约。

---

### 23.4 测试是否存在“永远不会失败”的断言？

例如：

```python
assert result is not None
```

或者：

```python
assert isinstance(result, object)
```

如果无法有效发现缺陷，应重新设计。

---

# 24. Bug Injection / 反例验证

对于核心业务逻辑，AI 应主动思考：

> 如果我故意把生产代码改错，这个测试能不能失败？

例如正确代码：

```python
if age >= 18:
    return True
```

故意修改：

```python
if age > 18:
    return True
```

那么测试必须包含：

```python
def test_age_18_is_adult():
    assert is_adult(18) is True
```

如果测试全部通过：

> 测试覆盖不足。

这比单纯看代码覆盖率更能验证测试质量。

---

# 25. Mutation Testing

对于高风险或者核心算法，可以使用 Mutation Testing。

工具：

```text
mutmut
```

基本思路：

```text
正确代码
   ↓
自动修改代码制造 Bug
   ↓
运行测试
   ↓
测试是否能够发现 Bug
```

例如：

```python
if value >= 100:
```

变异为：

```python
if value > 100:
```

如果测试无法失败，说明测试用例没有覆盖这个行为差异。

Mutation Testing 是可选增强手段，不要求所有项目全部执行。

---

# 26. 覆盖率

可以使用：

```bash
pytest --cov
```

例如：

```bash
pytest --cov=src --cov-report=term-missing
```

覆盖率只能作为参考。

不能认为：

```text
90% coverage = 90%正确
```

重点关注：

```text
Branch
Exception
Boundary
Error Handling
```

尤其是：

```python
if
elif
else
try
except
finally
```

等分支。

---

# 27. 测试分层

Python 项目建议：

```text
tests/
├── unit/
├── integration/
└── e2e/
```

### Unit Test

特点：

```text
快
独立
Mock外部依赖
```

测试：

```text
函数
类
算法
业务逻辑
```

### Integration Test

测试：

```text
数据库
文件
API
模块之间交互
第三方服务
```

### E2E Test

模拟真实用户或真实业务流程。

不要把所有测试都做成 E2E。

---

# 28. 测试优先级

对于普通 Python 项目：

```text
P0：核心业务逻辑
P0：异常处理
P0：边界条件

P1：模块交互
P1：外部接口
P1：数据一致性

P2：一般工具函数
P2：非核心分支

P3：低风险代码
```

测试资源优先投入高风险代码。

---

# 29. 测试失败分析

测试失败时，禁止直接修改测试让它通过。

必须判断：

```text
1. Production Bug
2. Test Bug
3. Environment Problem
4. Test Data Problem
5. Requirement Ambiguity
```

例如：

```text
Test:
test_login_wrong_password

Result:
FAILED

Expected:
status == "FAILED"

Actual:
status == "SUCCESS"

Analysis:
疑似 Production Bug。

Reason:
错误密码没有被正确拒绝。
```

---

# 30. 禁止为了测试修改生产代码

如果发现生产代码存在问题：

优先：

```text
发现 Bug
↓
记录 Bug
↓
保留能够复现 Bug 的测试
↓
修复生产代码
↓
重新运行测试
```

不要：

```text
生产代码有 Bug
↓
修改测试预期
↓
让测试通过
```

---

# 31. 测试执行要求

生成测试后，应实际执行：

```bash
pytest
```

必要时：

```bash
pytest -v
```

指定测试：

```bash
pytest tests/test_xxx.py
```

指定测试函数：

```bash
pytest tests/test_xxx.py::test_xxx
```

覆盖率：

```bash
pytest --cov
```

不要只生成测试代码然后声称：

```text
测试通过
```

除非确实执行过测试。

---

# 32. 测试报告

完成后输出：

```text
## Test Summary

Test Files:
    xx

Test Cases:
    xx

Passed:
    xx

Failed:
    xx

Skipped:
    xx

Coverage:
    xx%

## Tested Areas

- Normal cases
- Boundary cases
- Exception cases
- Invalid input
- External dependencies

## Bugs Found

- xxx

## Test Limitations

- xxx

## Untested Risks

- xxx

## Test Quality

High / Medium / Low
```

---

# 33. 最终检查清单

提交测试代码之前必须检查：

```text
[ ] 是否理解了被测试代码？
[ ] 是否查看已有测试？
[ ] 是否查看项目测试配置？
[ ] 是否覆盖正常流程？
[ ] 是否覆盖边界？
[ ] 是否覆盖异常？
[ ] 是否覆盖非法输入？
[ ] 是否考虑 None？
[ ] 是否考虑错误类型？
[ ] 是否测试关键分支？
[ ] 是否测试副作用？
[ ] 是否正确使用 Mock？
[ ] 是否存在过度 Mock？
[ ] 是否存在无效断言？
[ ] 是否存在测试代码与生产代码重复实现？
[ ] 测试是否相互独立？
[ ] 测试是否可重复执行？
[ ] 是否实际运行 pytest？
[ ] 是否分析失败原因？
[ ] 是否检查测试自身的可靠性？
[ ] 核心逻辑是否需要 Mutation Testing？
```

---

# 34. 最重要的原则

始终遵循：

> **不要为了覆盖代码而写测试，要为了发现 Bug 而写测试。**

> **不要默认相信 AI 生成的测试。**

> **测试代码也必须被审查。**

> **高覆盖率不等于高质量测试。**

> **好的测试应该能够让错误的实现失败。**

> **正常场景证明功能能工作，边界和异常场景证明功能不会轻易失控。**

> **对于核心业务，优先设计反例，而不是堆积测试数量。**