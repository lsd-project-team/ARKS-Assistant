# 语言切换：生产入口、翻译文件与控件应用

更新：2026-09-28。部分复核；未运行设备程序。

## 流程摘要

UcMainSystem 的语言选择 EditValueChanged → LocalizationManager.ChangeLanguage → 语言不同则更新设置并 Save →遍历 Application.OpenForms，为窗体和子 XtraUserControl 调用 FormLocalizer.LocalizeForm →加载翻译JSON →调用控件的 ILanguage.GetUI（若实现）→有窗体翻译则按键查找组件并赋值。它是用户界面维护链，不是自动生产状态转换。

## 主链证据

|步骤|条件与行为|源码|
|---|---|---|
|事件入口|EditValueChanged 显式绑定；将 EditValue 强转 LanguageEnum 后切换语言，并逐个刷新窗体和子控件|[绑定:3192](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.designer.cs#L3192)、[处理:1980](../../trunk/AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.cs#L1980)|
|保存|仅语言变化时修改单例Language并Save；不负责广播或界面遍历，遍历在调用方|[Manager:53](../../trunk/AKRS.ZX2200/Localization/LocalizationManager.cs#L53)|
|设置位置|Singleton文件路径为 StartupPath/language_settings.json；Language默认Chinese；外部基类加载保存细节未证明|[LanguageSettings:17](../../trunk/AKRS.ZX2200/Localization/LanguageSettings.cs#L17)|
|翻译初始化|Manager.Initialize在锁内以标志限制一次初始化；GetUI/GetMessage会EnsureInitialized|[Manager:22](../../trunk/AKRS.ZX2200/Localization/LocalizationManager.cs#L22)|
|窗体本地化|直接 Cache.Initialize(formName) →可选 ILanguage.GetUI →HasFormTranslation →按翻译键应用；外围catch仅Debug输出|[FormLocalizer:66](../../trunk/AKRS.ZX2200/Localization/FormLocalizer.cs#L66)|
|缓存加载|Initialize始终调用通用翻译加载，并为提供的非空窗体名调用LoadFormTranslation；不应把它等同Manager的一次性门控|[Cache:46](../../trunk/AKRS.ZX2200/Localization/LocalizationCache.cs#L46)|
|文件选择|从StartupPath向上找含csproj/sln目录，存在其Localization/Data则优先，否则用StartupPath/Localization/Data；Forms/窗体名.json用UTF8读取并JObject.Parse|[路径:207](../../trunk/AKRS.ZX2200/Localization/LocalizationCache.cs#L207)、[加载:268](../../trunk/AKRS.ZX2200/Localization/LocalizationCache.cs#L268)|
|组件应用|遍历JObject键，找到组件才应用；优先JSON Property，否则默认属性；当前语言非空字符串才赋值，另处理Hint/额外属性|[遍历:97](../../trunk/AKRS.ZX2200/Localization/FormLocalizer.cs#L97)、[应用:230](../../trunk/AKRS.ZX2200/Localization/FormLocalizer.cs#L230)|
|实际赋值|反射公开实例属性，转换类型后SetValue；不可写/不存在或异常仅Debug信息|[赋值:338](../../trunk/AKRS.ZX2200/Localization/FormLocalizer.cs#L338)|

## 缺失与异常分支

LoadFormTranslation 文件不存在或解析异常时记录_nonExistentForms；EnsureFormLoaded仅在未加载且未记录不存在时加载。LocalizeForm直接Initialize会尝试LoadFormTranslation，不能笼统宣称失败后永远不重试。见 [Cache:257–294](../../trunk/AKRS.ZX2200/Localization/LocalizationCache.cs#L257)。

GetValueFromJObject只读指定语言，空值返回null，不自动退回中文；Manager的GetFormTranslation/GetCategoryTranslation捕获异常后也返回null。[Cache:375](../../trunk/AKRS.ZX2200/Localization/LocalizationCache.cs#L375)、[Manager:83](../../trunk/AKRS.ZX2200/Localization/LocalizationManager.cs#L83)。UI主文本无翻译时在此赋值分支跳过，可能保留原显示文本；不能认为每次切换得到完整一致的新语言。

入口强转、ChangeLanguage保存和遍历没有本地catch/汇总确认；外部Save若抛错可能阻止后续刷新。FormLocalizer的catch及返回值又不提供完整成功统计，因此保存了语言选择不等于全部界面翻译成功。

## 尚未完成

- 公共/消息分类文件全量、翻译键覆盖率与实际资源缺失未审计；本次没有据路径声明文件全部存在。
- FindComponentByKey全部控件类型与层级、额外属性转换、Cache.ClearCache及线程安全仍需完整复核。
- ILanguage各实现、所有调用方、外部Singleton持久化和启动期初次本地化尚未全部闭合。
- 未构建或运行语言切换，没有将调试日志当作用户可见故障告警，也没有将此维护链当作生产循环。
