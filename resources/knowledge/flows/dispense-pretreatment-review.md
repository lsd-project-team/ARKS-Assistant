# 点胶真实克隆与生产预处理复核

2026-09-29。30项检查通过。五份完整原类文件（点配置、胶型、枚举、BaseDsSetting、PropertyChangeAop）配合四个精确原方法（项目内ObjectHelper.Clone、EpoxyPretreatment、两种范围判断）。由本机Roslyn编译，使用系统Windows PowerShell/.NET Framework执行，实际CLR版本和Framework Release见`pretreatment-test.json`。不是现代.NET上替换BinaryFormatter，也没有把同名外部助手误认为实际调用目标。

## 克隆隔离

- 原Clone通过BinaryFormatter在内存流中序列化和反序列化。样本模型、胶路List、点数组、点对象都与原对象分离；修改克隆点和RecipeIDList不影响原对象。
- 基类Name、CreateTime和RecipeID值保留，RecipeIDList独立。对象图内两个位置原先指向同一点时，克隆仍保持内部别名关系，但指向独立于源的新点。深复制不等于取消内部共享引用。
- PropertyChangeAop原PropertyChanged字段带NonSerialized，克隆中不保留委托。BinaryFormatter不调用EpoxyIsReasonable getter，因而不会意外触发其零值归一化副作用。
- null输入抛ArgumentNullException；含不可序列化派生点时整个克隆抛SerializationException。
- 本地测试没有运行Fody织入后的程序集，不能据此证明部署对象的所有事件与代理行为相同，也不证明编辑并发期间的原子快照。

## 预处理正常路径

- 在显式Drawing策略下，两点(2,4)/(6,12)按SizeX=8、SizeY=4归一化为(-4,-2)/(4,2)。原默认枚举为SingleDotOnly，已单独覆盖两点中点分支。
- 配置角度与传入角度相加，再添加传入目标X/Y；点Z加目标Z。helper中配置OffsetX/Y/Z不直接参与本方法的最终平移；这不表示上层控制器不使用这些字段。
- Speed、Acc、Dec乘SpindleSpeedPercentage；EndSpeed不跟随缩放。高度补偿、开胶标志、点类型、名称、序号和延时等样本字段保留。
- 返回独立预处理对象，原坐标、速度不改变。此证据补充此前编辑器丢弃预处理返回值的调用顺序复核。

## 边界行为

- 非正Speed先改100，非正Acc/Dec先改1000，再乘百分比。百分比0产生零参数，负百分比产生负参数，无二次校验。NaN速度、正无穷加速度可保留。
- 零跨度轴产生的NaN会被置0；单个点最终归一到原点。宽度0使轴塌缩，负宽度使轴反射。
- 第一条曲线为空时，没有进入i=0/j=0的极值初始化；后续全正点的最小值会包含初始0，从而改变归一化结果。实测同样点组首点从(-4,-2)变为(-4/3,-2/3)。
- SingleDotOnly且正好两点时，只将第一点改为两点中点，保留第二点及数组长度。
- 一个X为NaN可使整组X极值运算传播NaN，之后清理成0；但NaN旋转角和无限目标偏移在清理之后才参与变换，仍会产生NaN/Infinity坐标。
- 空胶路列表返回空克隆；null曲线或null目标会抛异常。目标失败案例中原配置未被改写。

## 运行与范围

执行`node scripts/test-pretreatment.cjs`。回执登记原文件、提取方法行号与哈希、测试文件、CLR及Framework Release；`build-pretreatment-audit.cjs --check`验证证据一致性。生成程序集只在系统临时目录运行，清理时验证目录父级和专用前缀。

外部配置单例、元数据属性、日志和点容器为明确惰性替身；数据基类及通知字段来自原始完整源码。未执行Fody织入、真实控件、持久化、控制器或运动驱动；只使用本地构造可信对象进行内存克隆，不反序列化外部文件。生产源码未修改，29组继续部分复核。
