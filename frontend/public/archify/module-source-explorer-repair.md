# 模块源码阅读器漂移修复

完整回归最后一次观察到 `module-source-explorer` 失败，原因是 `module-reviews.json` 的 supporting-document 哈希修复后，嵌入该登记数据的 `module-source-explorer.html` 尚未重新生成。已执行：

`node scripts/build-module-source-explorer.cjs`

随后追加 `--check` 重跑成功，当前阅读器包含 29 个模块、552 条关系和 940 段证据，生成物 SHA-256 为 `0f75b71db61d00ce76adfb0a1ff1446e94aab5ae225d8a370749d2e2af2654ca`。这只修复生成物一致性，不改变模块语义结论或完整回归范围。
