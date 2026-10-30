# 点胶参数编辑、批量应用与端点往返复核

2026-09-29。38项检查通过；回执 `parameter-roundtrip-test.json`；执行器 `scripts/test-parameter-roundtrip.cjs`、`test-parameter-roundtrip.ps1`、`parameter-roundtrip-harness.cs.txt`。生产源码不变。

## 范围

36份完整原始类参与编译，另原样提取31个控件/表单方法或属性（18个控件、13个表单），记录源文件及片段哈希。复用真实Curve、EndpointSetting、模式切换方法和真实System.Data.DataTable。DataGridView、DevExpress网格、格式化显示值及消息投递为替身；值变更回调可关闭或同步调用原CellValueChanged。不是原生控件事件序列、完整产品Framework或现场验收。

## 单行编辑与解析

- 段表只显示EndpointCount-1行；每行对应线段起点的EndpointSetting，终点本身没有独立段表行。
- CellValueChanged不按列选择字段，而是重新解析该行七个参数后一次调用ModifySegmentInfo。EndpointSetting是值类型，最后一列解析失败时，前面已解析的字段不会部分写回曲线。成功时保留原高度补偿和测高标志。
- 负RowIndex被忽略；列0通知仍解析整行；整数溢出和非法文本抛出，Dummied直接要求bool Value，字符串True不满足该强制转换。
- 当前隔离环境中，负速度、负延时、NaN加速度没有被该方法拒绝。de-DE下1,5解析为1.5。en-US下ASCII Infinity被拒绝，但该运行时文化的PositiveInfinitySymbol可解析成正无穷。回执记录运行时和符号；不能把现代运行时解析结果直接外推到部署的Framework版本。

## 两种批量应用并不等价

- “统一参数”BtAutoParam只给当前段表各行设置选中列的Value，然后从模型刷新表格；它依赖CellValueChanged把值写回曲线。禁用替身回调时修改被刷新丢弃；启用同步原回调时只修改当前曲线的段起点，保留终点参数、其他曲线、高度补偿及测高标志。
- “统一所有线段参数”BtAutoAllParam直接遍历所有曲线的全部EndpointUnit，包括未显示为段行的最后一个端点。它用新EndpointSetting重建参数，传入AltitudeCompensation=0，且构造函数未保留HeightMeasurement；因此即使只批量修改速度，高度补偿也清零、测高标志变false。其他可见参数按原值保留。
- 未选单元格、选择索引列时提示并返回。非法批量值在首个端点写入前失败。当前曲线批量回调在后续行解析失败时，先前提交保留，失败行显示值可与模型不同。
- 原全曲线批量循环逐端点重新读取CurrentCell.Value；注入先合法后非法的读取序列时复现部分提交。此项明确为可控读取故障模型，不代表已观察到真实用户编辑并发。
- Designer第951/1142行绑定两类批量按钮，第294行绑定段表CellValueChanged；不把关闭回调的对照实验说成正常UI运行方式。

## 追加展示与选择重入

- 原EndpointAppended表单订阅用固定(10,10,100,0,0,false,0,0)创建段表行，而不是读取原线段起点参数；样本显示速度10但模型为12。完整刷新后恢复模型值12。没有据此推断模型已被覆盖，Rows.Add引起的原生事件顺序尚未模拟。
- 段选择设置HighlightedSegmentIndex并刷新端点对；选择变空时不清高亮也不清端点表。ExecuteAction先ClearSelection，随后SetAction；若目标模式与当前同为None，SetAction跳过，高亮仍可保留。实际发生模式变更时则清高亮。
- 不同曲线选择调用原SetCurrentCurveIndex，受控索引订阅刷新参数，然后ExecuteAction(None)；相同曲线或无选中行则不退出当前模式。ClearSelection订阅异常可阻止后续模式切换。此处使用直接选择响应及可控回调，未验收原生DataGridView重入顺序。

## 当前端点数据表

- 原InitGvSegmentEndpoints创建独立DataTable，六列为PointType、Index、X、Y、Z、HeightMeasurement；原端点刷新复制曲线坐标、补偿和测高标志到两行。实验使用真实DataTable，网格SetRowCellValue只转发DataRow赋值。
- 直接修改该表Z、HeightMeasurement或X不改变Curve；再次选择同一线段时，原刷新从Curve覆盖未写回的数据表值。
- 在Dispense当前C#源码的显式绑定检索中，未发现该DataTable的ColumnChanged/RowChanged订阅或GvSegmentEndpoints值变更订阅。旧dataGridViewEndointCollection_CellValueChanged是另一个WinForms DataGridView方法，仅发现声明，没有当前Designer绑定；它也没有被本次运行验证为可达保存路径。这里不把缺少显式绑定扩张为对运行时反射或外部扩展的穷尽结论。

## 剩余事项

参数往返的上述有限序列已完成。仍需真实DevExpress/DataGridView编辑提交和选择时序、文件保存后的参数回读、生产字段消费、背景动作及绘制验收。82个模块源文件未穷尽，29组继续部分复核。完整产品构建、SDK版本、真实设备和现场配置尚未验证。
