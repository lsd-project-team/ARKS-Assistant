# Windows 隔离执行适配

Windows 协议 3 已有适配代码和边界测试。当前电脑没有 Windows 容器节点，尚未执行 Windows Hyper-V、SDK 或 ZX2200 构建验收。Linux 协议 2 保持独立，不用 Linux 测试代替 Windows 结果。

## 执行与结果来源

应用可以部署 Linux，通过管理员预先配置的 Docker SSH context 管理独立 Windows 节点。本机 Windows 节点也可使用固定的 Docker named pipe。远端 TLS context 暂不能完成节点物理盘容量核对，会明确拒绝；适配不会开放未认证 Docker 端口。

每次运行采用固定镜像和 Hyper-V 隔离。容器停止时复制源码，启动后管理员主进程只配置工作区 ACL、报告虚拟盘容量并维持 TTL。目标通过节点本机 `docker.exe exec --user ContainerUser` 运行。Docker CLI 官方实现会查询 Engine 的 `ExecInspect.ExitCode`；受信节点上的 .NET Process 直接读取32位退出码，再以结构化帧返回控制端，避免Linux或SSH把256截成0。[Docker exec](https://docs.docker.com/reference/cli/docker/container/exec/)、[退出码实现](https://github.com/docker/cli/blob/master/cli/command/container/exec.go)、[.NET原生退出码](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.process.exitcode?view=netframework-4.8.1)。

桥接程序由短固定PowerShell引导器从有界stdin读取并核对SHA256，避免OpenSSH默认cmd命令长度限制；项目argv作为base64结构化数据，只进入固定docker.exe参数。节点桥先核对Engine身份，以两路字节泵合计限制stdout/stderr；目标输出只能成为base64日志字段，不能冒充结果帧。Windows Job在桥被关闭时回收本机docker.exe；容器目标由独立TTL与停止确认负责终止。通过证据必须包含原始退出码0、实际镜像、节点身份和容量，单独的协议标记或`passed`文本无效。

命令结束后，应用先停止整个容器并确认 `Running=false`，终结后台后代，再复制结果。Moby 的 Windows 实现禁止对运行中的 Hyper-V 容器直接做文件系统复制；因此停止态传输也是平台要求。回传继续逐项检查普通文件、路径、链接、数量和大小，全部通过后才替换工作副本。[Windows 文件传输实现](https://github.com/moby/moby/blob/master/daemon/archive_windows.go)。

监督程序和解释器位于受管理员 ACL 保护的目录，管理员工作目录不进入源码目录。目标不能修改监督程序或延长 TTL。镜像无宿主目录、设备、Docker socket 或管理凭据挂载，网络固定为 none。Hyper-V 和低权限目标身份各自承担不同的隔离职责。[Microsoft 容器安全说明](https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/container-security)。

## 空间核对

`windows_scratch_mb` 是整个 Windows scratch 的预留预算，默认 32768 MB，最低 20480 MB；它不是 `C:\work` 的独立 1 GB 文件配额。Windows 默认动态 VHD、SDK占用以及只扩不缩的实现都可能影响实际容量。受信管理员入口必须报告虚拟盘真实容量，超过声明预算就拒绝运行。[Windows 存储](https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/container-storage)、[scratch 扩容实现](https://github.com/microsoft/hcsshim/blob/main/internal/wclayer/expandscratchsize.go)。

节点物理盘剩余空间由固定只读探针读取 DockerRootDir 所在本地卷。探针仅接受经过验证的已配置 SSH 地址或本机 named pipe；使用 BatchMode、严格 known-host 检查和固定编码的 PowerShell，不携带项目内容或目标命令。容量未知、过期、节点剩余空间不足，或遗留容器的 scratch 预留未知时均拒绝执行。应用还会扣除本服务已创建容器的完整预留，避免只按已写入字节估算并发消耗。

当前Windows节点要求单服务、单应用进程专用，检测到其他服务owner预留会拒绝。应用进程内锁只保证本进程的准入顺序，不提供跨进程原子租约，不能用于多实例共享节点或作为宿主其他程序的磁盘配额。

输出回传仍有独立体积上限。Windows 目前没有实现 Linux `pids-limit` 的等价进程数硬上限，也没有宣称按目标用户实施 NTFS 1 GB 硬配额；CPU、内存、整个 scratch、时限与回传上限各自记录。[Microsoft 资源控制](https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/resource-controls)。

## 准备与显式验收

节点须支持 Windows 容器和 Hyper-V；虚拟机节点还需支持嵌套虚拟化。Windows Home 本机不能提供此执行环境。[Windows 容器要求](https://learn.microsoft.com/en-us/virtualization/windowscontainers/deploy-containers/system-requirements)。

管理员提前准备固定 Windows Server Core / .NET Framework SDK 基础镜像、离线依赖和私有 DLL，再用本仓库 `Dockerfile.windows` 包装。模板不联网恢复项目依赖，不执行项目 Dockerfile。SDK、私有依赖和设备运行分别验收，不能用镜像构建成功代替 ZX2200 编译。

```powershell
backend/.venv/Scripts/python.exe scripts/execution/prepare.py --platform windows `
  --context 已配置的Windows节点context --windows-scratch-mb 32768 `
  --base-image sha256:预先准备的固定Windows基础镜像ID
```

真实验收需要显式设置：

```powershell
$env:ARKS_TEST_WINDOWS_EXECUTION_CONTEXT='已配置的Windows节点context'
$env:ARKS_TEST_WINDOWS_EXECUTION_IMAGE='sha256:固定的可信Windows镜像ID'
cd backend
.venv/Scripts/python.exe -m pytest -q tests/integration/test_windows_container_execution.py
```

未提供节点和镜像时这些测试会跳过。协议、容量、路径和退出码单元测试会正常运行；本机Windows真实子组件验证覆盖原生退出码0/7/256/512/-1、伪造stdout、两路无换行洪泛、超时及取消后Job回收。本机只读容量探针只证明可读取该盘；这些结果均不证明Windows容器、SDK或ZX2200已通过。
