# 胶量检测算法：选择、输入与结果

2026-09-28。限定复核EpoxyDetectAlg路径；不能根据业务方法名推断所有胶量检测配方都选用了此算法，实际选择须结合PR配置。

## 执行顺序

1. AlgsFactory.Create按枚举创建算法；EpoxyDetectAlg对应独立实现，未知枚举default回落FastModelAlg。SetAlgFlowType同类型直接true，否则创建、写AlgFlowType、替换Alg后InitVmProcedure；初始化内部catch仅记录日志，所以调用返回true不证明VM初始化成功。没有这里的回滚。[工厂23–121](../../trunk/AKRS.Galaxy2.PR/Models/Algs/AlgsFactory.cs#L23)；[切换817–852](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L817)；[初始化291–319](../../trunk/AKRS.Galaxy2.PR/Models/Algs/BaseAlg.cs#L291)。
2. PREntity先SetImage再FindModel。SetImage可按需初始化VM，图像源模块非null才SetImageData，同时构造四分之一大小SourceImg；成功路径会Dispose传入Bitmap。catch只记录日志，没有失败返回值，因此调用方仍可继续FindModel；是否使用旧图不能从此代码保证，需SDK测试。[输入252–286](../../trunk/AKRS.Galaxy2.PR/Models/Algs/BaseAlg.cs#L252)；[调用509–511](../../trunk/AKRS.Galaxy2.PR/Models/Entities/PREntity.cs#L509)。
3. EpoxyDetectAlg.FindModel取得VM过程、清空MatchResults，设置IsFirPR。粗定位启用时设置FirPRType并取BLOB分析1，否则取BLOB分析2；模块null返回false，随后Run并读取过程输出。[63–128](../../trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs#L63)。
4. 两分支分别读取1BlobCenterX/Y/Area或2BlobCenterX/Y/Area。这里只检查X数组非空非零；后续按X长度索引Y/Area，未见在此分支提前校验三者等长。异常由方法末尾catch记录并返回false。[103–139](../../trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs#L103)；[412–415](../../trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs#L412)。
5. 粗定位分支还按类型读取快速/高精度/灰度/轮廓匹配中心；但生成BlobResult使用原始X/Y，减Crudex/Crudey的另一路代码被注释。IsOutputTotal时中心为各结果算术平均、面积相加，不是按面积加权中心。[141–195](../../trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs#L141)；[269–308](../../trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs#L269)。
6. 检出结果生成BlobResult列表，每项含中心、面积、IsSuccess=true，共享bitmapResult，然后返回true。无X结果时可生成IsSuccess=false的显示结果并返回false；异常仅日志+false，没有本地重试。数量、面积/偏移合格判定在后续PostBondEpoxyCheck，不是FindModel的true本身。[269–316](../../trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs#L269)；[394–415](../../trunk/AKRS.Galaxy2.PR/Models/Algs/EpoxyDetectAlg.cs#L394)；[业务检测361](../../trunk/AKRS.ZX2200/BondSystem/Models/Repositories/PostBondInspection/PostBondInspection.cs#L361)。

## 输入输出和后续缺口

输入：PR算法类型、配置prc/默认算法prc、相机Bitmap、粗定位开关/类型及输出聚合选项。输出：bool和BlobResult列表、显示图像、日志。VM过程、模块命名及Halcon绘图是实际依赖；源码不能替代prc内容和SDK运行证据。

- 继续其他派生算法以及配置到运行算法实例的完整绑定；不要把此分支推广到全部视觉业务。
- 验证图像注入失败后输入状态、Bitmap重复Dispose/共享显示图所有权、空或长度不一致的输出、粗定位失败等场景。
- 工厂default及替换后初始化失败的实际影响，需配置测试；未修改生产代码或运行设备。
