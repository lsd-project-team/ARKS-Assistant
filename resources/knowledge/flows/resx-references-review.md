# RESX内部外部文件引用核对

检查项目声明中存在的388份resx，解析出134条ResXFileRef，缺失0条。解析只读取XML，禁用DTD及外部解析器，不反序列化嵌入对象。

|资源位置|资源键|缺失文件|
|---|---|---|

此次未发现缺失的ResXFileRef目标。这不证明图像可解码、序列化对象兼容、资源名正确或产物可加载。

资源与目标文件哈希、原始value和行号见[机器回执](resx-references.json)。复现：pwsh -NoProfile -File scripts/build-resx-references.ps1 -Check。范围不含未被项目声明的资源、动态路径及构建时新增项。
