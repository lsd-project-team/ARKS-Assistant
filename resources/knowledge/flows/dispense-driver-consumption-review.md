# S1/S2 点胶驱动字段消费与完成顺序复核

2026-09-29。29项隔离检查通过。编译完整原EpoxyApplicationLocation类及三个精确原片段：S1 ETEL逐点循环、GuGao队列生成、GuGao发送及完成清理。运动接口全部为惰性命令记录器，没有连接设备。S1/S2调用点另作静态核对，不宣称完整控制器运行通过。

## 字段消费差异

- ETEL逐点发送，包含第一个点；首点速度、加速度、减速度固定0.01。后续目标点使用上一点Speed/1000、Acc/1000，减速度也取Acc/1000而非Dec。XY除1000，每点调用等待。
- ETEL开胶标志取当前目标点，包括末点；真实标记常量为1/65536。等待抛异常时，该循环片段已经打开阀并发送线段；片段外的关胶、退出插补和外层异常清理没有运行，不能据此断言实际设备持续开胶。
- GuGao生成n-1段，直接使用下一点XY，使用起点Speed、Acc、Dec；endVelocityMode固定0，未消费EndSpeed。最后一点的运动参数不用于生成下一段。此处坐标单位只描述代码传参，不推断实际驱动标定。
- GuGao按起点OpenGlueFlag生成IO命令：开胶安排LagOpen，AdvanceClose非零才安排提前关闭；关闭分支发送doValue=1、modal=1。IO先于相应运动命令入队。负延时、NaN速度、Infinity减速度直接传下去；ioIndex转换short可能截断。
- 空数组和单点数组在队列片段内不生成线段，null抛异常；完整方法初始化没有执行，不能推广为完整方法行为。

## 返回码及等待

- IO失败、前一运动指令失败可以被后续成功的运动返回码覆盖；只有最终队列返回码非零才触发该处检查。
- DataEnd持续非零会持续重试；execute持续非零会持续查询。两个原循环内均无超时、暂停或取消检查。测试通过记录器在第4次调用注入异常终止，未给原循环加入保护，也未无限运行。
- Start及状态查询返回码不在该片段中单独拒绝；清理顺序为GroupStop、Ungroup、GroupDisable、StopCommandList，最终bool仅受最后一次返回码控制，前面的清理失败可被覆盖。

## 上层静态绑定

- DispenseController调用GuGaoDrive.Interpolation(1,...)，S2DispenseController调用Interpolation(2,...)；两者均不读取bool返回值，调用之后再关胶。S2绘制路径遇ETEL显式抛“没有开发”。
- GuGao外层catch重新抛通用错误文本，没有保留原异常为InnerException。这是源码观察，不是本次执行覆盖。
- 原指针构造涉及UnsafeAddrOfPinnedArrayElement；记录器不解引用pValue，本次不验证指针固定、数组生命周期或SDK ABI。测试用共享数组记录目标Y，也不证明原生内存布局。

## 可重复验证与未闭环项

执行`node scripts/test-driver-consumption.cjs`及`node scripts/build-driver-consumption-audit.cjs --check`。回执记录完整源文件和测试文件哈希、三个片段的行号与哈希；审计另固定S1/S2调用点证据。提取匹配已限定在GuGao目标Interpolation方法内，避免同名语句在其他方法中重复出现。

完整GuGao初始化、完整控制器、ETEL片段外清理、原生SDK和硬件、运行中编辑一致性、部署Fody织入和全产品构建仍未验收。29项通过证明这些原片段在列出的替身条件下的行为，不证明生产系统正确，也不是缺陷修复。生产源码不变，29个模块组继续部分复核。
