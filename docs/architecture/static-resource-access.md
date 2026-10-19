# 登录资源与业务静态资料的访问边界

正式服务继续使用 FastAPI 提供现有页面和资料 URL。未登录时仅开放真实登录依赖，工作区分包、资料、索引、源码映射以及未列入清单的旧哈希文件均需要有效会话。

## 构建与运行契约

`frontend/scripts/build/public-assets.mjs` 从 Rollup 的真实分包图选择主入口和 LoginPage，递归跟踪静态 imports；不把工作区动态 imports 自动列为公开。公开分包如果包含 `src/features/knowledge/` 模块，构建直接失败，Windows 路径和大小写变化也不能绕过检查。

随后结合 Vite 清单收集登录所需 CSS、字体及图像，生成 `frontend/dist/public-assets.json`，固定每个公开文件的 SHA-256。公开清单仅描述当前构建，不以 `/assets/` 前缀或扩展名直接放行文件。因此，保留历史资源不会把以前含业务知识的脚本重新公开。

后端 `modules/auth/static_assets.py` 在启动时校验清单、路径、普通文件身份和摘要；清单缺失时没有公开静态文件，API 仍可启动，损坏清单则拒绝启动。后端中间件对公开登录资源之外的静态请求复用现有会话、账号切换和跨站校验，先授权再交给 StaticFiles 处理 Range、HEAD 和条件请求。

私有响应设置 `private, no-store`、`Vary: Cookie`、`X-Frame-Options: SAMEORIGIN` 及 `Cross-Origin-Resource-Policy: same-origin`。资料仍可在本应用的同源 iframe 中打开。登录 UI 的哈希资产可以长期缓存，首页和固定名称登录图像不长期缓存。

## 发布约定

按标准 `npm run build` 生成页面、分包和清单，成功后再发布。完整带上 `.vite/manifest.json` 和 `public-assets.json`，保留旧哈希资源，最后替换首页；重启前应核对当前清单与文件摘要一致。不要只拷贝首页和 JS、遗漏访问清单。

已有旧标签页若在退出后无法加载旧登录分包，需要刷新获取当前首页；不能为兼容旧页面而匿名放行全部旧脚本。已经被下载的旧内容也无法通过服务端访问控制回收。

反向代理必须将页面和静态资源请求一并转给 FastAPI，不能绕过应用把 frontend/dist 直接作为公开静态目录或 CDN 源站。`npm run dev` 和 `npm run preview` 只用于可信的本机开发，不是公司服务入口，它们不提供这套生产会话边界。

这项约束保护应用自带的全局知识资料；项目、对话、账号及交接数据仍使用原有 API 权限。它不取代 Windows 构建节点、真实模型质量或业务验收。
