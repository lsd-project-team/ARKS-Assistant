import type { PresentationTopic } from './presentation';
import type { FlowchartCatalogEntry } from '../types';
import type { CoordinateArtifact } from './coordinateDiagrams';

// 只发布已经逐条复核的专题；全部制作范围保存在开发覆盖清单，避免空目录冒充已完成内容。
export const functionalTopics: PresentationTopic[] = [
  {
    id: 'tool-bank',
    title: '工具库与吸嘴更换',
    summary: '从工具与槽位配置、几何和工具架示教，到取还嘴、在位检测与重复测试。',
    purpose: '分清当前工具名、槽位状态和实际在位，理解换嘴条件与保存边界。',
    conditions: ['工具架、检测开关、工作模式和人工选择共同决定实际路径。'],
    exceptions: ['同名早退、人工忽略、取消、保存与物理动作完成分别判断。'],
    diagrams: ['tool-bank-process'],
  },
  {
    id: 'force-control',
    title: '力控标定与反馈',
    summary: '从压力计连接、大小力与角度标定，到取放力控、实时曲线和结果导出。',
    purpose: '区分原始读数、目标输入、标定样本与生产反馈的实际口径。',
    conditions: ['驱动、通道、标定表、角度和动作模式共同决定路径。'],
    exceptions: ['停止、部分结果、参数保存和实际动作成功分别判断。'],
    diagrams: ['force-control-process'],
  },
  {
    id: 'height-measurement',
    title: '测高与测量工具',
    summary: '从 S1 探针、S2 激光与焊头测高，到产品多点、平面度复测和结果导出。',
    purpose: '区分传感器读数、不同坐标中的高度与最终物料 Z 更新。',
    conditions: ['工位、工具、硬件和对象配置共同决定测量路径。'],
    exceptions: ['跳过、成功返回、保存、复测与设备实际到位分别判断。'],
    diagrams: ['height-measurement-process'],
  },
  {
    id: 'lightness',
    title: '光源控制与亮度标定',
    summary: '从相机灯光对应和手动调光，到六组亮度采集、映射补全与视觉应用。',
    purpose: '区分模板强度、点胶输出与正反向换算的建立和使用。',
    conditions: ['相机、灯光模式、列表顺序和当前缓存状态共同决定路径。'],
    exceptions: ['后台发起、样点保存、字典初始化与设备输出分别判断。'],
    diagrams: ['lightness-process'],
  },
  {
    id: 'global-calibration',
    title: '全局标定与扫描采集',
    summary: '从扫描点和温漂采集，到区域插值、旧驱动映射与 Bond/BC 偏移。',
    purpose: '区分预期轴点、实测结果与不同补偿实现的建立和使用。',
    conditions: ['点列、标定模板、驱动类型和所选入口共同决定路径。'],
    exceptions: ['完成标志、保存、下载与启用分别判断，保留未启用和旧接口边界。'],
    diagrams: ['global-calibration-process'],
  },
  {
    id: 'tool-calibration',
    title: '吸嘴顶针与三点一线校准',
    summary: '区分吸嘴中心、高度、顶针与取片偏移的独立入口、采样和保存。',
    purpose: '把工具示教与定位结果连接到后续校准偏移。',
    conditions: ['工具配置、示教状态、相机选择和物料决定实际路径。'],
    exceptions: ['一键组合未启用，旧接口和失败后的保存分别说明。'],
    diagrams: ['tool-calibration-process'],
  },
  {
    id: 'product-coordinates',
    title: '产品层级与产品坐标',
    summary: '看清载具到焊点的层级、实例展开，以及定位结果怎样改变后续加工目标。',
    purpose: '将产品局部位置、视觉定位和工位偏移连接到同一条坐标父链。',
    conditions: ['普通矩阵与异形结构使用不同的配置，位置和加工顺序分别计算。'],
    exceptions: ['定位更新有差值限值；坐标更新、参数保存和轴到位分别判断。'],
    diagrams: ['product-coordinate-lifecycle'],
  },
  {
    id: 'public-vision',
    title: '视觉模板与公共视觉流程',
    summary: '串起模板加载、采图、定位与缺陷结果，分清各层调用和人工处理。',
    purpose: '把相机图像变成供物料定位和检测使用的结果。',
    conditions: ['模板、硬件、点数配置与运行模式共同决定视觉路径。'],
    exceptions: ['初始化标志、算法调用成功和物料定位成功需要分别判断。'],
    diagrams: ['public-vision-process'],
  },
  {
    id: 'camera-calibration',
    title: '相机与机械坐标标定',
    summary: '从 S1/S2 标定入口到采点、坐标建立、旋转修正与结果保存。',
    purpose: '连接像素、机械位置、焊头偏移与设备坐标。',
    conditions: ['工位、工具确认、采样点阵与公共对中方法共同决定路径。'],
    exceptions: ['中途可能已有写入，任务返回与最终精度复核分别判断。'],
    diagrams: ['camera-calibration-process'],
  },
  {
    id: 'motion-safety',
    title: '安全运动与连续轨迹',
    summary: '从目标转换、软限位和安全高度，到区域过渡、插补与等待停止。',
    purpose: '按工位和运动模式组织轴目标，区分软件门控与实际动作完成。',
    conditions: ['载具、工具、运行模式和所属轴卡共同决定路径。'],
    exceptions: ['子调用返回、驱动等待和停止状态需要分别确认。'],
    diagrams: ['safe-motion-process'],
  },
];

export const functionalCatalogEntries: FlowchartCatalogEntry[] = functionalTopics.map((topic) => ({
  id: topic.diagrams[0],
  inlineTopic: topic.id,
  title: topic.title,
  type: 'architecture',
  typeLabel: '功能图谱',
  group: 'reader',
  groupLabel: '07 功能阅读',
  status: 'source-reviewed-inline',
}));

export const functionalArtifacts: Record<string, CoordinateArtifact> = {
  'tool-change-overview': {
    path: 'functional-atlas/tool-change-overview.html',
    sha256: 'd6ced45d4afdb494c3b6dd9ddb5c689d6aba378753bddef36e0a299da0d9ddeb',
    specificationSha256: 'da40b3cefd0664c8c7c646cb1c1938443b687255193c2b0a7420e271ea118a70',
  },
  'tool-change-reading': {
    path: 'functional-atlas/tool-change-reading.html',
    sha256: 'fd9865c5fd35b55dd22d527960c8cd6886460bf2d45027328b330f5f722c557a',
    specificationSha256: '8dc83635f4a7d28a2a20879c8df5d3de3691fba24c6f467dd521ff01158f5c27',
  },
  'force-calibration-overview': {
    path: 'functional-atlas/force-calibration-overview.html',
    sha256: '887ccb43832de166dc440decbe9320ca6d02307bccbd3f9a129ad074a52b97d9',
    specificationSha256: 'd13dee5b8ac87e447215f1232cfa981f3b787d722674e99313cc554c841425d8',
  },
  'force-input-overview': {
    path: 'functional-atlas/force-input-overview.html',
    sha256: '525649a807a9991cf61057d5f2e40934ffa3f63ab6aed9ee8e9fb95b20ec6766',
    specificationSha256: 'c7a83800a7b12c5da2599003187f52c05ceccd5cfec2ca7c834775bd36f92388',
  },
  'force-calibration-dispatch': {
    path: 'functional-atlas/force-calibration-dispatch.html',
    sha256: '289d02d083f8421e0f204cd5611abdf0633857325996ad0d6fb16e83b948b159',
    specificationSha256: 'e1fc124ff44b80dcd94a7660b0f77fe181b3cf2e034e7eca4799156f20cf746a',
  },
  'force-input-conversion': {
    path: 'functional-atlas/force-input-conversion.html',
    sha256: 'bc7852d4f413063d21ac0e24b3ba41453bc7d76ff403a3c9400c58e82469af7f',
    specificationSha256: '5e00aaa2b83911d733477dc108726934651c819244142fb5c7cd7d916677b9b4',
  },
  'height-s1-writeback': {
    path: 'functional-atlas/height-s1-writeback.html',
    sha256: 'e6df853337bcf4f84e54884665edc92115f6abaa1b919e6abc76a5e0733b7675',
    specificationSha256: '3640c42083f2efd2802d6ec295b59a45d751d62bb73fec4044a0bcdb1614f1ae',
  },
  'height-flat-batch': {
    path: 'functional-atlas/height-flat-batch.html',
    sha256: 'a51a8184aa27d1dd31aeef27b248a18fc47856f01d7f050faf158907f41cd7d7',
    specificationSha256: 'ff7cca427610aaf1a730253d4ee6103f24530a00ca36e0322cfc43483622ba8b',
  },
  'lightness-calibration': {
    path: 'functional-atlas/lightness-calibration.html',
    sha256: '7afb12ac4c962fb44959836d203cbafcf119af566b3cf5f8b27b4ca2e545c3c2',
    specificationSha256: '900f2867b4ef02e1da33e42055e9ce751a4ef713505bfa0b0bfa7db2b80eafd8',
  },
  'lightness-alarm-edit': {
    path: 'functional-atlas/lightness-alarm-edit.html',
    sha256: 'b7368f885432b81cb8164ee41c714dffd780110630a2605f2b7a9b1ce1b31724',
    specificationSha256: '118d70ede9090655136b1dfb0549b6a77143e6fd428e29d8c4f7c9411491d8fc',
  },
  'global-region-chain': {
    path: 'functional-atlas/global-region-chain.html',
    sha256: '6368e43fdce385ee9712c93a3f92ec4bfc500ddc0a0f8cebf3ca1f56d924e702',
    specificationSha256: '966faa70d55c6b5ee712d57634e64b8419b7bac3d67fcf54436f23a5616580a7',
  },
  'global-driver-mapping': {
    path: 'functional-atlas/global-driver-mapping.html',
    sha256: 'db0ebba018dd097f2fa1d7291ac9d8cd3bdebb54fb53e80c6d9deefde36a5be9',
    specificationSha256: '4af64cb504c40ef6b3f338a5cd9866c1b732be22d4517c40bc89eb8520c4ab60',
  },
  'tool-calibration-entry': {
    path: 'functional-atlas/tool-calibration-entry.html',
    sha256: 'a022b2af9bd3a9210c50e69e44efb3e25b774fd4542dc4a01c2dd4a770452bb9',
    specificationSha256: '09679f6fcdd0e41d6da317036ee8e5ed1862f78c32bf9294cbdb0fdd129eb568',
  },
  'safe-motion-reading': {
    path: 'functional-atlas/safe-motion-reading.html',
    sha256: 'f0e055f26cfd9a9b5f8a50cdcceb813a10287794fa55d23ae208cf5d4417f41d',
    specificationSha256: '4a61ee89f8cc8c3d0e172560a9eb58d480b9261cdea06d0995dda53e20dc7098',
  },
  'safe-motion-branches': {
    path: 'functional-atlas/safe-motion-branches.html',
    sha256: '4d94e3b2ea036bf6008eb8ad79a01f11fb9d95b6a5646868c1dd891a74a10e3f',
    specificationSha256: '5c8768441721740279574c79b3f9c30a16be02446577c1944602d66a00bf00a8',
  },
  'camera-calibration': {
    path: 'functional-atlas/camera-calibration.html',
    sha256: 'c4ee19672e758363cb8f5c877b426ec48985b5fe428926782871d85ea95a75d8',
    specificationSha256: 'b4b49dbe5f57358fcc2429aa841cf3bc009be55fe4c264188e52f8392d864190',
  },
  'vision-point': {
    path: 'functional-atlas/vision-point.html',
    sha256: '99b6d6b8861bc64db92ef5b51aae70bcaea317346afc653b90f44245f292d5ca',
    specificationSha256: '15a2e8e7acee52af62928c2f7a015381d1ff0cee184cf97e2c508fb93859ade0',
  },
  'product-update': {
    path: 'functional-atlas/product-update.html',
    sha256: '549a0bb2d54fe761b0d1a6f76b54b7c3666dbc6903fa88418481630ad50a0eba',
    specificationSha256: '7e3f63c9c35218f8d98a1dfa5283b9c0ae8cffcc4199a71199a0fbeac1c9f043',
  },
};
