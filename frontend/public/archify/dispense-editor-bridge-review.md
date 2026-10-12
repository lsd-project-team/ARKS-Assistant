# 点胶编辑确认与业务配置桥接复核

2026-09-29。31项限定隔离检查通过。直接编译九份完整原文件：六份编辑数据原类、EpoxyApplicationLocation、EpoxyApplication、DispenseEnum；精确提取UcEpoxyApplication的编辑按钮、双向转换、Confirm四个方法及DispenserMoveHelper两个范围判断方法，共六个原方法。

## 参数往返

- 业务坐标mm转为float后乘1000送编辑器，回写除1000；测试1.25/-2.5正常往返。此样本不证明全域精度。
- Speed、EndSpeed和AltitudeCompensation进入编辑器时显式转int：12.9、5.8、7.9分别变为12、5、7。开胶标志与Dummied互反，HeightMeasurement直接设false。
- InitPatternData重新new业务点，未赋EndSpeed，回写变为0；Dec取编辑器Acc，因此原Dec=66.5、Acc=44.5回写后Dec=44.5。
- 重建点还未赋Z、Index、Name、Type，原非默认字段回落为0/null/Dispense。业务类原默认值参与真实测试，没有在替身中模拟这些默认值。
- InitPatternData调用预处理但丢弃返回值，之后Refresh。预处理在本测试中为记录输入/返回独立对象/故障注入的替身；不把测试描述为真实克隆或生产轨迹执行。

## 编辑确认、重试与失败

- 首次Cancel保留原点对象，正常释放编辑器、清空窗口引用并刷新列表。
- OK先清空原胶路，再GetContent和InitPatternData。GetContent失败时旧胶路已清空；处理器没有finally，编辑器引用仍在、未Dispose、列表未刷新。
- 不合理速度-1经OK回写后触发再次打开；第二次Cancel保留已经回写的不合理点。重试SetContent接收上一轮编辑结果；不是事务取消。
- ShowDialog失败保留原点但不释放窗口；预处理失败则新点已回写、Refresh尚未发生。
- InitPatternData(null)先清空再抛错；后续曲线为null时前面的有效曲线已替换。
- 成功编辑OK更新内存配置，本按钮没有调用两个Save。保存发生在独立Confirm。

## 合理性检查与保存

- EpoxyIsReasonable getter运行真实IsDataReasonAble：所有点的零Acc/Dec改100、零Speed改10，包括末点。随后只检查每条曲线末点以外的范围。
- 空曲线通过；单个负速度点通过；末点负值不被范围校验。NaN通过基于大小比较的判断，非末点正无穷速度不通过。未将这些结果视为产品验收合格。
- Confirm逐项更新模型，再依次调用EpoxyApplicationRepository.Save、System1Program.Save。测试保存替身记录顺序；不证明落盘成功。
- 第一Save抛错时第二Save未调用，内存字段保留；第二Save抛错时第一Save已调用，无回滚。早期控件读取异常或策略类型转换异常会留下此前更新字段，两次Save尚未调用。
- 无吸嘴选择写入字面字符串“Null”。

## 上下游边界

Designer中BtEditPattern.Click明确绑定被测处理器。既有S1/S2消费路径见[编辑器源码报告](dispense-pattern-editor-source-review.md)。本轮另核对原预处理会对Dec做默认值和倍率变换，Z会加目标Z，但未执行此预处理或运动驱动，不能把字段往返损失直接等同于已验证设备轨迹错误。

## 验证

`node scripts/test-editor-bridge.cjs`生成`editor-bridge-test.json`，登记原文件、精确原方法起止行、片段哈希及测试文件哈希。`node scripts/build-editor-bridge-audit.cjs --check`检查报告、回执和Designer源文件一致性。

控件、对话框、保存、预处理、基类和元数据属性是明确的惰性替身；原业务模型及合理性检查完整保留。未运行原生WinForms/DevExpress事件循环、配置真实落盘、生产克隆、全部字段的驱动消费、完整构建或设备。生产源码未修改，29组继续部分复核。
