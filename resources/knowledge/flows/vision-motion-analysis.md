# ZX2200 视觉、运动与补偿链路

## 源码确认的调用链

动作节点先按 `AccuracyMode`、`AdjustCamera` 和硬件配置选择实际校正节点。`UpLookCorrectionActionNode.DoWork:131–520` 和 `SubstrateCameraCorrectionActionNode.DoWork:136–520` 在不适用的相机模式下直接返回 Success；适用时移动到视觉位置、调用 PR、读取结果并计算坐标补偿。

`VisionService.Vision:73–151` 从 `VisionEntityRepository` 查找 `PREntity`，缺失时弹窗并返回 null；找到后在对象锁内调用 `PREntity.DoWork`。Success 且结果为 `MatchResult` 时只返回中心点和角度；Fail 返回 null。算法本身不在 ZX2200 源码中展开。

运动动作由 BondModule/BondHead 控制器和轴对象执行。`UpLookCorrectionActionNode` 根据 `AxisMoveModeEnum` 选择绝对移动或插补移动；绝对移动会分别向 X/Y/Z/T 轴发送命令，插补路径还会启动轴 T 的并发任务并检测超时。`MotionService2.cs` 当前为空，实际运动封装在各模块控制器和外部驱动边界。

视觉结果进入偏移、旋转、温度或区域补偿，再写入 BondPosition/运行时状态，供后续取晶、校正和固晶使用。`VisionService.DistanceCheck:239–323` 可比较两点距离，超差弹出“手动对点/忽略/跳过/停止”选择。

图片保存不是同步提交：`SaveVisionImage:182–229` 创建目录并把 Bitmap 放入 `BlockingCollection`，`SaveBitmap:337–351` 的后台线程再写 BMP。PR 失败不会自动证明运动失败；具体动作节点根据返回值决定 Retry、Ignore、Abort 或 Stop。

## 证据

- `Infrastructure/Service/VisionService.cs:73–151,182–229,239–323,337–351`：PR 调用、失败分支、距离检查、异步存图。
- `BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs:131–520,619–880,1851–2008`：相机选择、补偿和轴移动。
- `BondSystem/Models/ActionNodes/BPActionNode/SubstrateCameraCorrectionActionNode.cs:136–407,520–603`：基板相机校正和运动。
- `Infrastructure/Service/MotionService2.cs`：当前文件为空，不能把它描述成实际运动实现。
- `AKRS.ZX2200.csproj`：VisionMaster、Modbus、MathNet、ONNX 和其他硬件/算法引用。

对应图：[vision-motion-workflow.html](vision-motion-workflow.html)，源文件：[vision-motion-workflow.archify.json](vision-motion-workflow.archify.json)。
