# Properties：程序集、设置和界面资源复核

更新：2026-09-28。状态：部分复核；本组是生成资源基础设施，不是设备自动任务。

## 已核实

- AssemblyInfo声明标题/产品AKRS.ZX2200、ComVisible(true)，程序集和文件版本1.5.0.0；不证明部署版本或实际COM注册。
- Settings.Default返回Synchronized创建的实例；Settings.settings的Settings元素为空，生成类没有自定义设置属性。这不代表设备或配方没有其他配置。
- ResourceManager以资源基名和当前程序集延迟创建。Culture setter只保存resourceCulture字段，不直接修改线程文化。
- 代表调用：MainForm初始化界面 → Resources.Home1 → ResourceManager.GetObject → Bitmap强制转换 → 主系统文档页图标。不是运动或调度步骤。
- csproj将Resources.resx声明为EmbeddedResource并关联生成器；尚未验证构建结果。
- Resources.resx本次审计111个data项、108个外部文件引用，引用文件均存在。路径及哈希见审计文件；不证明图像解码、资源反序列化或运行时可用。

## 证据

- [trunk/AKRS.ZX2200/Properties/AssemblyInfo.cs:7](../../trunk/AKRS.ZX2200/Properties/AssemblyInfo.cs#L7) — Assembly metadata
- [trunk/AKRS.ZX2200/Properties/Settings.Designer.cs:11](../../trunk/AKRS.ZX2200/Properties/Settings.Designer.cs#L11) — Settings.Default
- [trunk/AKRS.ZX2200/Properties/Settings.settings:1](../../trunk/AKRS.ZX2200/Properties/Settings.settings#L1) — Empty settings
- [trunk/AKRS.ZX2200/Properties/Resources.Designer.cs:35](../../trunk/AKRS.ZX2200/Properties/Resources.Designer.cs#L35) — ResourceManager and Culture
- [trunk/AKRS.ZX2200/Properties/Resources.Designer.cs:393](../../trunk/AKRS.ZX2200/Properties/Resources.Designer.cs#L393) — Resources.Home1
- [trunk/AKRS.ZX2200/Main/Controls/MainForm.designer.cs:150](../../trunk/AKRS.ZX2200/Main/Controls/MainForm.designer.cs#L150) — MainForm resource assignment
- [trunk/AKRS.ZX2200/AKRS.ZX2200.csproj:3579](../../trunk/AKRS.ZX2200/AKRS.ZX2200.csproj#L3579) — EmbeddedResource

[资源引用审计](properties-resource-audit.json)；[模块复核台账](module-review-status.md)。

## 缺口

- 其余强类型getter和全部界面消费点未逐项映射。
- 构建嵌入、图像解码、语言变体、缺失和类型不匹配异常尚未验证。
- 实际COM需求、部署版本和第三方控件许可环境未核验。
- 本组不替代设备配置、配方保存和生产任务内部步骤专项复核。
