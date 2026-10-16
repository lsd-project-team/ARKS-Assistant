# 点胶模板真实文件往返复核

2026-09-29。22项检查通过。直接编译PatternFile、EPEData、EPEPointData、Point2D、EndpointSetting、EndpointFlags、BackgroundImageInfo七份未修改原类，加载仓库libs/AKRS.Base.dll（1.1.7.0），在.NET 10.0.11运行真实SXml、Bitmap和隔离临时文件IO。未使用替代序列化器。

## 往返结果

- 有背景图模板能保存并回读：像素比、芯片尺寸、小数坐标、点顺序、背景矩阵和抽样像素保留。八个已序列化工艺参数（含高度补偿与空过标志）保留。
- 点参数与默认参数的HeightMeasurement原为true，回读均为false。原AddInfo未写入该字段，RetrieveInfo构造新EndpointSetting时不会恢复该标志。通过检查不代表此行为符合产品要求。
- 空曲线列表可往返；仅含一个空曲线的列表回读变为空列表，空曲线身份不保留。
- EPEData构造器虽然注释称图像可为空，实际调用BackgroundImageInfo构造器会拒绝null。

## 文件状态与故障

- 已构造对象的Image属性可设null。SaveFile仍能创建XML但不创建背景图；ReadFile先复制同名bmp，缺图时捕获异常并返回null，无法读回刚保存的模板。
- 对已有模板保存Image=null不会删除旧bmp；回读得到新参数与旧图像。
- 使用真实FileShare.None锁定XML：SaveFile抛错、XML旧字节保留，但同名背景图片已经写入。两文件保存不是原子提交。
- 损坏XML与缺失文件返回null。ReadFile成功会产生tmp_*.bmp副本。
- ClearTmpFiles吞掉被锁临时文件的删除异常，保留非tmp名称图片；解锁后再次清理可删除匹配临时文件。

## 证据与边界

运行`node scripts/test-pattern-roundtrip.cjs`。回执`pattern-roundtrip-test.json`记录各项断言、七份原类、实际DLL和测试文件哈希；`build-pattern-roundtrip-audit.cjs --check`核对回执及报告。临时目录在用户系统临时目录下生成独立GUID，清理前验证绝对路径父目录，不接触生产模板或设备。

本轮验证实际保存回读和上述故障，不覆盖全部XML缺字段、跨区域数值格式、所有图片格式、文件系统中断、原生表单调用时序、部署.NET Framework兼容性、完整产品构建或设备运行。29组仍部分复核；生产源码未修改。
