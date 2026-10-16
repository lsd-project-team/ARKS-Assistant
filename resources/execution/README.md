# 可信隔离执行模板

Linux 协议2已执行真实容器回归。Windows 协议3已有 Hyper-V 适配、停止态传输与32位原生退出码桥接；本机只验证了原生进程与只读容量子组件，尚无Windows容器节点，不能宣称Windows、SDK或ZX2200 / .NET Framework 4.8构建已验收。Windows节点准备与实际限制见[Windows执行说明](../../docs/architecture/windows-executor.md)。

Linux 基础镜像须由管理员提前准备，提供 `/usr/local/bin/python`。使用已存在的固定 digest 或完整镜像 ID：

```powershell
backend/.venv/Scripts/python.exe scripts/execution/prepare.py --base-image sha256:<64位镜像ID>
```

该命令只使用本目录内固定模板，构建步骤不联网，不读取业务项目 Dockerfile。准备完成会输出 `executor` 配置和实际镜像 ID；把该配置用于现有代码工作的管理员验证命令。构建或验证缺少依赖时应准备新的可信基础镜像，禁止验证时开放网络、宿主目录、Docker socket 或凭据。

Linux 目标进程永久降为 UID/GID 1000，清空附加组和能力，禁止获得新权限。监督进程保留 SETUID、SETGID、KILL 三项能力，使用只读根目录、独立 PID 命名空间、CPU/内存/进程限制、无网络和受限 tmpfs。源码通过 `docker cp` 进入本次专用 staging 卷；可信程序复制后把该卷根目录锁为 root 0700。目标进程无法向 staging 卷写入，输出只允许写受限工作区和临时目录。

执行结果在 root 专属 `/run/arks` 中生成；目标进程不能伪造通过状态。监督进程会先终止所有目标 UID 后代（含脱离会话的进程），再生成证明。可信导出程序返回 tar 流，应用逐项检查普通文件、路径、大小、数量及大小写冲突，在空目录校验通过后才交换工作副本。原始源码不参与交换。

取消、超时、回传失败后清除本次容器和 staging 卷；服务重启可按 owner 与 verification 标签精确清理遗留资源，保留活跃验证，不执行全局 prune。监督进程另有独立运行截止时间与 120 秒回传窗口。

显式运行真实 Docker 集成验收：

```powershell
$env:ARKS_TEST_EXECUTION_IMAGE='sha256:<准备后得到的镜像ID>'
cd backend
.venv/Scripts/python.exe -m pytest -q tests/integration/test_container_execution.py
```

普通测试不设置该变量时跳过真实 Docker 用例，不拉镜像或启动外部服务。容器共用宿主内核，仍要求维护 Docker/内核和可信基础镜像；这不等于 Windows 虚拟机、真实供应商调用或设备验收。
