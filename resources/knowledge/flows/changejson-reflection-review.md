# 配置迁移工具反射辅助类隔离验证

对完整原始ReflectionHelper.cs进行了7项检查，使用本机内置PowerShell/.NET编译及运行；不启动UI、不迁移文件。原始文件哈希和结果见[测试回执](changejson-reflection-test.json)，复现命令为`node scripts/test-changejson-reflection.cjs`。

|场景|实际结果|
|---|---|
|同名int/string属性，源目标值不同|目标值均未改变|
|两参数创建有效类型|返回实例|
|两参数创建私有无参构造类型|返回实例|
|两参数创建不存在类型|抛NullReferenceException|
|三参数创建不存在类型|返回null，不抛包装异常|
|三参数创建类型与泛型不兼容|抛InvalidOperationException，内部为InvalidCastException|
|属性复制源对象为null|抛NullReferenceException|

属性复制方法判断`destInfo.PropertyType is ValueType`，检查的是Type对象自身，而非它代表的属性类型。编译器给出CS0184警告；隔离测试明确允许该警告后运行未修改原方法，确认本次int/string样本不会进入赋值分支。这不是深拷贝实现。

全trunk C#（排除bin/obj）对ReflectionHelper及AssignSameProperty具名搜索仅命中本文件声明，未发现直接调用。不能因此排除反射或外部程序集调用，也不能把辅助类问题等同于迁移按钮已经出错；按钮原有路径直接使用Assembly/File。

该验证缩小辅助类契约缺口，不完成模块验收。迁移按钮的文件写入失败、同名映射、并发、真实程序集加载以及.NET Framework 4.8产品构建仍需验证。生产源码未修改。
