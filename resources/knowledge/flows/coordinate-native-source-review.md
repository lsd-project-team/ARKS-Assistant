# 完整原坐标程序集原生几何与VM依赖边界

完整13份原 Compile 项构成的 CoordinateSystems 程序集，在原生 CLR 4.0.30319.42000 中通过124项独立检查；实际 SDK 点类型、运算符和原 TransformTool 均被引用，没有测试替身声明。编译及几何检查重放后，产物哈希、案例名称与顺序一致。真实 VM/标定调用的5项观察均失败，实际退出码1已保留并重放；本报告不认定厂商运行或标定验收通过。详见[输入与结果](coordinate-native-source-test.json)、[来源审计](coordinate-native-source-audit.json)及[进度](coordinate-native-source-progress.json)。

## 几何范围

验证六种弧度/四组3D输入的正反转换；九种两层组合及逆序；Init复制或替换Distance、列表清理与null异常顺序；现代修正XYZ±10/角度±0.2和旧XY±5/Z±2阈值；角度NaN可进入状态；实际 SDK 点运算与参数别名；从属坐标只处理自己及直接父级、缺父与未实现逆转换；旧2D Vm/未知类型输出零，3D Vm逆转换直接拒绝。

普通坐标树根的自身变换被排除；缺失父级使当前对象视为根，返回未转换点。两节点父级环的原遍历在专用线程进入后100ms未完成；随后只中止并回收该测试线程。124项中包括3项线程进入/限时观察/回收检查，不能全部称为业务分支，也不能单靠100ms观察断言永不终止。源码循环同时未设置环检测；没有向现场设备配置植入环。

## 旧元数据失败的编码原因

对原主程序模型测试的同一输入文件，原生 PowerShell默认读取把UTF-8目录 VM算子 解码为乱码，MVDCalibTrans.Net 路径因而不存在。使用 ReadAllText 正确解码后，该文件全部162个引用的 AssemblyName 元数据预读通过并重放。坐标输入中两处 Unicode 路径也有相同差异；普通坐标构造与正向转换烟测通过。早期真实失败日志和旧冻结报告保持，本次提供更明确的原因；元数据可读不等于SDK原生算法可用。

## 真实VM尝试

原 StaticPara.CoordinateSystemPath 是公开可配置属性，测试设置为工作区内隔离目录，未替换源码或SDK。两次3D Vm正向都在实际 CCalibTransTool 工具创建时抛出 DllNotFoundException，模块名 MVD_Algorithm.dll；缓存工具仍null。实际标定列表 Init 的 Save 和null列表 Save 都因所需 MVDSDK.VMControls.BaseInterface 加载失败而中断；输入Upper/Own列表引用或null已经提交。之后调用Element Init抛NullReferenceException。没有生成标定文件。

只读Cecil核对显示 MVD_Algorithm.Net 明确导入 MVD_Algorithm.dll；MVDVMControlBaseClass.Net 4.2.1.4引用 MVDSDK.VMControls.BaseInterface 1.0.0.0、公钥9ed2c71b49c799a5。仓库两份名为VMControls.BaseInterface的文件实际上提供另一程序集名称及公钥14444b8df74b6e6a，不能靠文件名相似认定可替换。完整输入元数据映射没有改变这些失败，重复失败证据保持。当前库搜索环境的缺失可能包含原生模块或其依赖，尚未定位原生加载器的唯一根因，也未补造或改写厂商程序集。

## 证据与剩余

新增36项输入冻结并绑定父2052项，合计2088项冻结绑定。测试支架早期声明错误与复制脚本根路径错误均单列为测试准备失败，不当成生产或厂商缺陷。完整原13份源码与既有16工程1410项、原生98项、1328/278/119及阅读器40专题/3817快照保持，生产源码未改，124项不并入旧断言计数。

真实VM标定、相机模式/分辨率、所有高阶变换及设备精度仍未验收。缺失Parameters、net48 targeting pack、MSBuild资源/LC/签名与Fody/PostSharp织入、完整部署/UI/设备运行仍待完成。接续优先补源码构建资源/织入边界和可用运行依赖，再推进原域/具体动作、PR/校准/测量、IO稳定性与29组/13项整体验收。
