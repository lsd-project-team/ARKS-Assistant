# 迁移工具资源与配置声明核对

通过XML解析核对实际节点（排除注释中的示例），文件哈希及存在性见[可再生回执](changejson-assets.json)。复现：`node scripts/build-changejson-assets.cjs --check`。

- FrmMain.resx、UcChangeNameSpace.resx和Properties/Resources.resx均无实际data节点；UcChangeNameSpace只有文件夹对话框TrayLocation设计器元数据。模板注释里的Bitmap1/Icon1不是资源项。
- Resources.Designer.cs仅提供ResourceManager和Culture包装，资源基名为DXApplication1.Properties.Resources；Settings.settings没有设置项，Settings.Designer.cs仅提供同步Default实例。
- App.config声明.NET Framework 4.8及DevExpress的System DPI模式、RegisterBonusSkins=True。声明不证明现场配置加载成功。
- licenses.licx有GridControl和TextEdit两项，均声明DevExpress 21.2.7.0。尚未执行LC.exe许可证生成，不能用文本存在性代替构建验收。
- AssemblyInfo声明产品/标题Akrs.ChangeJson、程序集/文件版本1.0.0.0、ComVisible(false)；项目AssemblyName和RootNamespace实际为DXApplication1，不能按标题推断输出文件名。
- 项目声明的packages.config在当前项目目录缺失；其他已声明EmbeddedResource/None文件存在。缺少包清单是材料缺口，不等于已证明无法从其他路径解析程序集。
- 既有MSBuild求值已覆盖该项目Debug/Release AnyCPU；完整资源编译、依赖解析、许可证及产品加载仍未验收。

此核对完成列出的声明与资源数据范围，不将旧obj目录中的产物视为当前源码构建成功的证据。
