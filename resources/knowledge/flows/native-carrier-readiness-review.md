# 原载具计划、力控及拍照点位就绪核验

两轮各100项通过，共200项。未改动的16个原资源程序集、实际SDK共同执行；每轮16个源程序集路径匹配。228个声明/124个源文件严格解码并绑定原字节哈希及UTF16偏移，85个选定IL方法来自原主程序集和实际SDK。十三项新旧绑定检查均通过；89新增冻结输入，362父输入复用，10455+89=10544。整体目标未完成。

## 真实载具计划及持久化

原CarrierConfigRepository.Add两次无匹配CopyName PR源，实际执行空PR仓库Save。原MagazineAllocationsConfig中两个WaferTablet同名、AdapterTablet与实际AdapterConfig/WaffleArray，原StaticAdapterProgram使用相同adapter：三条原getters解析真实晶圆和华夫载具子类型，去重为两个原接收者。未示教/EditState.NewCreate、缺失Nozzle及Component引用仍通过BondProgram及完整离线S2就绪；NozzleName仅检查null/空字符串，"Null"字符串和不存在名称都通过。禁用且外配方的原载具仍被计划解析。

原Save1/Load1的typed carrier JSON重建两个正确子类型的新接收者，料架/静态盘getter随仓库查找自动重绑定；禁用、外配方和未示教状态保留并仍通过离线S2。没有替换单例或Getter，没有私有写入或来源替身。

## 力控及点位门

- 40行四类力值矩阵：Bond/Pickup/IPT Pickup/IPT Place，范围10到100的端点都拒绝，10.1/50/99.9通过，Infinity及-Infinity拒绝，NaN全部通过。单项实际全零ForceConfigItem使标定列表非空后，NaN贴片力也通过完整离线S2。
- 四类mode999都绕过力值范围；在未知相机、其他模式Distance的配置中，Infinity同样通过空标定的离线S2。
- 18行两相机×3取片模式×3放片模式矩阵实测原IsUseForceControl及完整S2标定门。BondCamera下IPT Pickup=Force/Place=Distance时属性false，空标定仍通过，形成漏检；两者Distance时属性true，空标定拒绝，形成误拒绝。UpLookCamera下IPT模式不影响该属性，但BondProgram仍检查IPT Force范围，即使IsIPTConfigrated=false。
- ForceConfig.IsEmpty只看大小力列表是否都为0。一条全零SmallForce或LargeForce真实配置项就足以通过原S2标定门；这不是实际完成标定的证明。
- Dip Force Infinity未进入BondProgram范围检查；空标定时S2拒绝，一条全零SmallForce项后完整离线S2接受。
- 两行零拍照点位：原AKRSPoint3D.IsEmpty=true、与新零对象Equals=false，运行时Equals声明于System.Object；原BondProgram调用对象引用Equals，所以UpLook/Bond两个零点位均通过。原IL的两个System.Object.Equals绑定与实际结果一致。
- 相机模式999时未使用的UpLook/DownLook配置为null仍各传播NullReferenceException，因原条件先访问点位才判断相机。
- 真空延时-1/0/20在PlacementDelay=20时通过，21拒绝。IPT延时41在硬件未配置时忽略、配置时拒绝，等于40通过。

## 计划异常与范围

缺失WaferTablet和静态Adapter名称被实际原解析过滤为零载具，完整离线S2仍ready。缺失料架AdapterTablet则在原GetCarriers传播NullReferenceException，完整S2同样抛出。WaferTablet指向华夫子类型、静态槽指向晶圆子类型均实际InvalidCastException。静态Adapter同一个null槽可被nullable投影过滤，料架Adapter路径则先空引用异常，未到末尾null过滤。

生产Task本轮零个，动作DoWork零次。完整BondProgram.SelfCheck/System2Domain.CheckIsReady已在OffLineWork及公开坐标、禁用ToolBank/工具传感器、实际空硬件下运行；每轮38次原消息分派只调用公开计数回调，不执行UI Action。整Machine.Start/回零Hardware SelfCheck、在线传感器/轴/相机/真实视觉、实际标定、匹配PR复制/VM、真实UI/SQL、Retry、MSBuild/LC/Fody/部署及完整29组业务仍待验收。原生产C#/csproj未修改。

本轮编译与两轮原生运行首次通过，无编译或原生失败候选。独立静态验证草稿遗漏了ForceConfig的两个列表getter调用，失败fafa1f已保存；依据实际IL修复为两getter+两Count，核验通过efa16f。阶段0d4615、冻结64896d、绑定fee09d均同步exit0。

下一步继续完整原启动准备的公共配置与仓库依赖，把已实测的载具/S2就绪门连接到Machine的实际启动准备及异常退出边界；真实S2生产任务、PR/VM与硬件验收保持待办。
