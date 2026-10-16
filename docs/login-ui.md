# 登录页 UI

2026-10-15。按已确认的浅色效果图实现，登录入口为 `http://127.0.0.1:8765/#login`。现已接入真实账号和服务端会话；未登录时先显示登录页，登录后恢复原目标页面。管理员与普通用户的范围见 [账号与交接访问控制](accounts-and-handover-access.md)。账号入口位于工作页面右上角，保持原左侧导航布局。

## 页面

- 左侧品牌展示与工程网格，右侧登录表单；复用现有字体、细线图标与主题变量。按页面批注移除左侧 ZX2200 标签和底部产品署名，主内容保持垂直居中。
- 支持纯白、柔和灰绿和深色，可通过右上角外观按钮切换。窄屏改为上下布局，页面可滚动，尊重减少动画的系统偏好。
- 密码显示开关、账号自动填充、记住账号、必填校验、密码重置提示、提交中与失败状态。
- 登录页独立加载，不读取项目、会话和源码数据。离开页面会取消等待中的登录请求。

## 认证接口边界

全局 `POST /api/auth/login` 校验 `username`、`password`，返回服务端身份和 CSRF 令牌，使用 HttpOnly、SameSite=Strict 的同源会话 Cookie；HTTPS 下增加 Secure。`GET /api/auth/session` 恢复身份，`POST /api/auth/logout` 撤销会话。普通用户没有角色选择或自行提权入口。

“记住账号”只写入 `arks-login-account`，不保存密码或凭证。不直接显示服务端错误正文，避免错误响应回显敏感字段。业务写入带 CSRF 令牌；失效会话返回登录页。账号切换前清除全部查询缓存，各窗口通过广播重新核对身份。右上角菜单提供个人信息、修改密码和退出登录；账号新增、角色调整与禁用仍可使用本机维护命令。

## 品牌素材

`frontend/public/brand/arks-assistant-icon.png` 为原有标识。新增 `frontend/public/brand/arks-login-mark.png` 使用内置 ImageGen，以原有标识为参考提取独立的金属 A 图形，透明背景，1536 × 1024；工程网格由页面 SVG 绘制，原有标识未覆盖。

生成提示词：

> Use case: background-extraction. Asset type: transparent brand sculpture for ARKS login page. The input is the existing ARKS app icon. Isolate ONLY its central sculptural folded ribbon capital A symbol, retaining the exact rounded arch shape, the open interior, the fold of the left leg turning inward, the rounded ends, the beautiful satin silver-blue metal shading and its existing identity. Remove the rounded-square white app-icon plate completely, remove all background, remove the plate's shadow and every outer edge. Output one large centered, crisply edged metallic A symbol with generous transparent padding, true alpha transparency. Keep the symbol's appearance faithful to the original image; do not redesign it into a conventional triangular A, do not add a crossbar, lettering, grid, base, watermark, or extra objects. The result should be the existing metallic A ribbon mark floating on actual transparent background, suitable for placement over a pale gray engineering grid. The A itself retains opaque silver metal material.

## 检查

完整构建包含 TypeScript 与源码资料检查。2026-10-15 前端 125 项、认证与改密及备份校验相关后端 11 项测试通过。2026-10-14 全量后端回归为 240 项通过、1 项原有环境检查跳过。认证和账号切换均通过本机服务与浏览器验收。

登录页已检查白色、灰绿、深色及手机布局；1280 × 720、1024 × 768 桌面窗口能完整显示登录区域，320px 与 390px 窄屏无横向溢出。显示密码和密码重置提示正常；错误登录不会进入工作台，成功登录恢复目标页面。右上角菜单另检查 430px 窄窗口，完整账号和身份仍可从菜单读取。

实际截图保存于 `output/login-ui/login-desktop.jpg`、`output/login-ui/login-mobile.jpg`。预览检查结束后恢复原有灰绿外观，清空测试账号与密码，撤销临时视口尺寸。
