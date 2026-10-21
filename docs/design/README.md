# ZX2200设计文档

当前两册分别为Transport Unit第7.1版与纠偏过程第3.2版，2026年10月21日。源码检索、阅读和追踪严格限定trunk/AKRS.ZX2200。

| 分册 | PDF | Word | 核查与维护资料 |
|---|---|---|---|
| Transport Unit 7.1 | [阅读PDF](transport-unit/v7.1/TransportUnit设计文档.pdf) | [编辑Word](transport-unit/v7.1/TransportUnit设计文档.docx) | [本册资料](transport-unit/v7.1/README.md) |
| 纠偏过程 3.2 | [阅读PDF](correction-process/v3.2/纠偏过程设计文档.pdf) | [编辑Word](correction-process/v3.2/纠偏过程设计文档.docx) | [本册资料](correction-process/v3.2/README.md) |

TU册补齐搜索人工确认、完整分段、九类输送入口、不同中断点状态和异形连续例。纠偏册补齐Nine缓存与识别寿命、Map支持范围、八入口条件、镜像角度全程、手动测试公式差异和补偿记录寿命。五幅新增工程图与原有概念场景图共同解释设计。

纠偏3.2继续补入设备轴二维补偿、手动两点角度示教、TU区域表自动生成及人工导入/编辑/清空；新增6幅精确工程图。深查记录区分生产、辅助、标定输入和诊断，自动采集窗口的打开入口证据边界单列在配套资料。

当前两册39页与46页。纠偏3.2全部46页重新渲染校样；Word/PDF的127段正文、67项目录/书签和47项图表索引核对通过。TU7.1保留此前39页核查。详见[修订验收对照](publication-acceptance.md)、[TU模板](authoring/v7.1/README.md)及[纠偏模板](authoring/correction-v3.2/README.md)。旧版均保留。

以上为源码静态核查、独立数值验证和代理阅读/版式自检；未运行整套C#业务或设备，纠偏3.2另执行18项纯数值类C#检查。未开展独立真人试读，正文去除指定制作说明，详细证据外置。
