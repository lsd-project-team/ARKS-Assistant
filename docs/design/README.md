# ZX2200设计文档

当前两册分别为Transport Unit第7.2版与纠偏过程第3.2版，2026年10月21日。源码检索、阅读和追踪严格限定trunk/AKRS.ZX2200，业务源码保持只读。

| 分册 | PDF | Word | 核查与维护资料 |
|---|---|---|---|
| Transport Unit 7.2 | [阅读PDF](transport-unit/v7.2/TransportUnit设计文档.pdf) | [编辑Word](transport-unit/v7.2/TransportUnit设计文档.docx) | [本册资料](transport-unit/v7.2/README.md) |
| 纠偏过程 3.2 | [阅读PDF](correction-process/v3.2/纠偏过程设计文档.pdf) | [编辑Word](correction-process/v3.2/纠偏过程设计文档.docx) | [本册资料](correction-process/v3.2/README.md) |

TU7.2在既有模型、坐标、交接与Mapping导入基础上，补齐整线/局部清空、配方与生产Mapping差异、异形节点编辑、辅助对象与补偿工作模式、节点引用反查、位置服务参考系，以及两点示教的分阶段写回与取消边界。新增6幅工程图，核查记录包括新Mapping关闭只写内存等实际实现差异。

纠偏3.2继续补入设备轴二维补偿、手动两点角度示教、TU区域表自动生成及人工导入/编辑/清空；新增6幅精确工程图。深查记录区分生产、辅助、标定输入和诊断，自动采集窗口的打开入口证据边界单列在配套资料。

当前两册47页与46页。TU7.2为24图24表，Word/PDF的152段正文、451个表格单元格、67项目录/书签及48项图表索引核对通过，全部页面重新渲染校样。纠偏3.2保留此前46页、127段正文、67项目录/书签和47项图表索引核查。详见[修订验收对照](publication-acceptance.md)、[TU模板](authoring/v7.2/README.md)及[纠偏模板](authoring/correction-v3.2/README.md)。旧版均保留，包括[TU7.1 PDF](transport-unit/v7.1/TransportUnit设计文档.pdf)。

以上为源码静态核查、独立数值验证和代理阅读/版式自检；未运行整套C#业务或设备，纠偏3.2另执行18项纯数值类C#检查。未开展独立真人试读，正文去除指定制作说明，详细证据外置。
