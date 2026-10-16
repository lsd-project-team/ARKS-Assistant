# 原始源码编码、另名保真编译与阅读器修复

全仓库1436个C#原文件的字节审计、16工程1410个实际Compile项的另名保真编译及独立重放已完成。原文件、旧编译器、旧程序集、正式1328和旧阅读器保持冻结；新路径已经恢复PR中文字符串。此阶段验收原始字节解码及新阅读器，资源/原生宿主迁移尚未完成，也没有完成原项目Build或部署验收。

## 原始字节与编译项

1436文件中1427为UTF8 BOM、2为无BOM严格UTF8、7为无BOM非UTF8。7文件全部严格CP936解码成功、没有U+FFFD且能够按CP936还原全部原始字节；1436文件都完成严格解码与字节往返。1410实际Compile文件和未编译26文件单独登记，编译项没有增删。

|原文件|Compile|变更词法值|
|---|---|---|
|PR/Controls/FrmHardwareSet.cs|是|4|
|PR/Controls/FrmHardwareSet.designer.cs|是|20|
|PR/Controls/FrmName.cs|是|2|
|PR/Controls/FrmName.designer.cs|是|4|
|PR/Models/Entities/PREntity.cs|是|38|
|PR/Models/TemplateConfigs/PRTemplateConfig.cs|否|0|
|ZX2200/Main/Controls/Ucmain/SplashScreen1.cs|是|0|

与冻结编译器默认ReadAllText相比，7文件文本不同、其中6实际编译。68个词法值变化均在PR中，41普通字符串词法项和27插值文本词法项；其他2个legacy文件只有注释等文本差异。无词法数量/种类错位。这里的68不是68个独立运行断言，严格解码/字节往返也不能独自证明任意文件的历史作者编码，因此继续用实际编译器解码作对照。

## 本机编译器解码对照

实际bundled Roslyn5的EncodedStringText.Create(Stream,Encoding,SourceHashAlgorithm,bool)以null默认编码直接读取1436个原文件，1436个解码文本哈希和显式策略一致：BOM/严格UTF8优先，7文件落到本机ANSI936。Framework本机ANSI同样为936。

安装的Framework csc.exe 4.8.9221.0分别真正编译无BOM CP936、UTF8 BOM、无BOM UTF8及显式/codepage:936的4个隔离探针，4子编译实际exit0，IL均保留由原PR词法值导出的D:\视觉定位成功图像\和D:\视觉定位失败图像\。探针没有PR方法/设备/目录执行，不等于原工程整体编译。Microsoft的[CodePage文档](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-options/advanced#codepage)说明源编码选项；[Roslyn解码实现](https://source.dot.net/Microsoft.CodeAnalysis.Workspaces/src/roslyn/src/Compilers/Core/Portable/EncodedStringText.cs.html)说明严格UTF8失败后的回退。这些规则与本机直接观测一致，原部署使用的具体工具链仍未识别。

额外只读检查checkout已有obj/bin的5个PR DLL，3个不同文件哈希，未找到本轮Excute的D盘目录字面量。它们不能用来证明现有完整源文件的历史编译效果或部署正确性。假定libs目录的PR DLL不存在，记录为不可用，未制造替代文件。

## 另名编译、源工程元数据与逐方法IL

新compile-encoding-preserving-project-source.ps1先验证原始字节SHA，再按审计清单严格解码并验证文本SHA。旧compile-original-project-source.ps1保持原SHA，新的1410源项/平台/定义/unsafe/外部与Framework元数据配置继承已有验证范围。

三轮各16工程共48次实际编译exit0：bootstrap保持冻结的源码工程引用，bound转为第一轮新程序集，replay引用bound程序集。后两轮各130个源码工程元数据引用放置；16程序集bootstrap/bound哈希都一致、bound/replay哈希都一致。15个程序集和冻结raw-source产物完全相同，仅PR改变。不是完整MSBuild、.NET4.8目标包、许可证或Fody验收；新raw-source程序集也还没有嵌入388资源/1498条目。

16程序集18286方法体逐指令文本/偏移与异常范围比较，没有其他差异，PR出现59处ldstr操作数变化，其他程序集0处；字段常量比较也未发现变化。59处都由含U+FFFD的旧字符串恢复为新中文字符串，原PR两种目录常量在新IL恢复。68源码词法发生点会经过插值等编译转换，故59个IL位置不是68个源码位置的另一种覆盖率。这里也不宣称所有自定义属性、ABI、资源、PDB或运行结果等价。

## 独立阅读器及实际浏览器验证

旧module-source-explorer.html SHA76edcc8c...不变。新[module-source-explorer-encoding-preserving.html](module-source-explorer-encoding-preserving.html)保持29模块、552关系、940基础快照、40专题/3817专题快照及同一ID/范围，用原字节审计策略解码；Node GBK/UTF8文本SHA与.NET审计一致。额外阅读器csproj等文件单独严格UTF8审计，Windows路径匹配按大小写不敏感规范化。

12个既有PR/PREntity快照恢复中文，原始文件哈希没有变化。实际Edge154 headless完成PR模块→关系查找→证据按钮点击、修复中文精确显示、深链接重载、4757快照逐项呈现、专题搜索及空结果边界、1600/1440/850/390窗口无横向溢出。浏览器无pageerror；截图和结果保持。生成时reader-results的browserInteractionVerified=false是生成阶段事实，后续独立reader-browser-results是真实浏览器通过记录，未涂改历史生成记录。

## 失败保留与后续

初始字节审计exit0但ordered-dictionary分组计数产生空policy键，singleton编译成员序列化为字符串；完整初始文件保留在audit-v1，新审计单独修正，原始/文本哈希及68词法变化一致。3次探针包装失败分别是PowerShell5默认ANSI读取BOMless UTF8 JSON、未冻结检查器Where-Object语法、可选旧DLL路径缺失；实际编译探针产物逐阶段保存。2次阅读器准备失败分别是非C#证据需另审计、Windows路径大小写；未产出错误新阅读器。浏览器第一失败是测试直接openEvidence只换面板不更新路由，reload恢复上一真实点击的片段；改用真实按钮点击后通过。检查器初稿语法错误也保留。没有把外层处理成功改成子进程成功。

本阶段新增317冻结绑定，父3579合计3896；与既有实际业务断言1328/60/41等不相加。旧含损坏中文的源码/资源程序集以及旧阅读器仍是历史冻结路径，新路径完成原始解码和raw-source编译，但需要**另名源码资源程序集保真迁移及代表原生宿主重放**后才能接替运行验证。之后继续其他等待/异常退出、真实SQL持久化、配方生产链、在线PR/校准/测量/IO下层、完整构建/部署/真实UI设备。16工程/29组/1436文件/13项整体未完成。

见[测试](source-encoding-fidelity-test.json)、[审计](source-encoding-fidelity-audit.json)、[进度](source-encoding-fidelity-progress.json)。
