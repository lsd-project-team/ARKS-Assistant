# 任务：跨语言仓库增加 full_name 与 initials

工作区是一个跨语言小仓库：

- `service/`：Python 服务，`to_payload` 把用户序列化为 JSON 字典；
- `client/`：Node ESM 客户端，`displayName`/`userId` 消费该 payload；
- 现有测试：`tests/test_api.py`（5 个）与 `client/test/client.test.mjs`（4 个），全部通过。

要求（不得修改现有测试文件）：

1. `service/api.py` 的 `to_payload(user)` 增加 `full_name` 字段：`f"{first} {last}".strip()`；
2. `client/client.mjs`：
   - `displayName(payload)` 优先返回 `payload.full_name`，缺失时回退 `first + last`；
   - 新增 `initials(payload)`：返回名字首字母大写（如 `"Ada Lovelace" -> "AL"`），
     名字为空返回 `""`，只取 `full_name`（缺失时用 first/last 拼接）；
3. 保持 `userId`、`list_payload` 等现有行为；
4. README 补充新字段/新函数说明；不要留 TODO/占位。

完成前分别运行：

```
python -m pytest -q
node --test client/test/client.test.mjs
```

两项都通过；不要安装新依赖。
