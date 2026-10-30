# 原 SetupZX2200.vdproj 部署清单核验

对原始 SetupZX2200.vdproj 做只读解析，共识别 465 个 File 项：393 个路径在当前工作区可找到，72 个路径缺失；其中 195 个标记为 IsDependency=true，270 个为非依赖项。安装项目设置了 .NET Framework 4.7.2 LaunchCondition（AllowLaterVersions=false），所有 File 项 PackageAs=1。

|项目|结果|
|---|---:|
|File 项|465|
|当前工作区存在|393|
|当前工作区缺失|72|
|依赖项|195|
|工程输出样路径项|289|
|LaunchCondition|.NETFramework,Version=v4.7.2|

缺失项主要是 VisionMaster/VM/Apps/MVD 外部程序集和若干 System.* 文件，解析按 SetupZX2200、主工程 bin\Debug、主工程 libs 三个当前目录候选查找；缺失不等于现场机器不存在，但说明当前工作区不能独立重建安装输入。存在项包括若干 DevExpress、AKRS 工程输出、配置和资源文件；其中当前 bin 文件可能来自历史或隔离编译，不是原始安装包构建成功的证明。

原解决方案的 SetupZX2200.vdproj 在四种解决方案配置中没有 Build.0 选择，且 ProjectOutput 节为空；因此解决方案 Build 不能证明安装器生成。此次没有调用 devenv、Installer、注册表或部署动作，没有写入生产目录。

[测试回执](native-setup-vdproj-test.json)、[审计](native-setup-vdproj-audit.json)、[进度](native-setup-vdproj-progress.json)绑定 vdproj 原字节、所有解析结果、当前存在文件的 SHA 和缺失清单。构建/LC/Fody/PostSharp、外部 VM 依赖和现场安装仍未验收，整体目标未完成。
