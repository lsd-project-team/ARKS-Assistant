# 迁移工具文件辅助类边界

完整读取DirAndFileHelper.cs的34个公开方法/重载，范围包含目录枚举、创建、删除、复制、大小计算、文件移动复制、文本读写及路径包装。使用完整原文件在内置.NET下运行7项临时文件检查，见[源码哈希和场景回执](changejson-files-test.json)。运行`node scripts/test-changejson-files.cjs`可复现；临时目录只清理本次固定创建项，无生产文件操作。

|原方法|实际边界|
|---|---|
|WriteTextFile，WriteTextFileAllLines|OpenOrCreate不截断旧文件。短写后尾部保留；两种方法均已实读确认|
|MoveFile|向目标文件全路径调用CreateDirectory；目标被建成目录，随后移动失败，源文件保留|
|ClearDirectory|先删除顶层文件，再用默认recursive=false删除子目录；非空子目录导致失败，已有删除不回滚|
|CreateDirectory(origin,newPath)|修改进程当前目录，方法没有恢复；测试恢复原目录后清理|
|ReadTextFile，ReadTextFileAllLines|文件缺失分别返回null、空列表；按行读取还会Trim并丢弃空白行|
|IsFileInUse|不存在返回false；独占读打开失败一律true，不区分占用和其他访问错误|
|CopyDirectory|递归先子目录后当前目录文件，覆盖同名文件；无事务或局部异常恢复，源目录不存在直接返回|
|CopyFile|先创建目标父目录，再检查源是否存在；源缺失不抛出明确错误|
|GetDirectorySize/GetFileSize|不存在返回0，不能据此区分不存在和空文件/目录|
|AppendTextFile|直接AppendAllText，不像WriteTextFile那样先创建父目录|

前五行的指定场景为运行证据，其余为原文检查，不宣称全部输入已测试。枚举、路径等其余方法直接委托Directory/Path，相关权限、重解析点、路径长度和并发变化仍未全面验收。

在Akrs.ChangeJson项目的C#文件中搜索`DirAndFileHelper.`未发现调用。当前迁移按钮使用File.ReadAllText/WriteAllText；以上辅助类行为不是按钮文件写入的实现。外部调用、别名和反射仍未排除。实际产品.NET Framework 4.8构建及运行未完成，生产源码未修改。
