import type { PresentationTopic } from './presentation';
import type { FlowchartCatalogEntry } from '../types';
import type { CoordinateArtifact } from './coordinateDiagrams';

// 只发布已经逐条复核的专题；全部制作范围保存在开发覆盖清单，避免空目录冒充已完成内容。
export const functionalTopics: PresentationTopic[] = [
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
