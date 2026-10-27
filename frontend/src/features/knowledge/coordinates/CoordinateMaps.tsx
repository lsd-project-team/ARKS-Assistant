import type { ReactNode } from 'react';

function Box({
  x,
  y,
  label,
  detail,
  root = false,
}: {
  x: number;
  y: number;
  label: string;
  detail?: string;
  root?: boolean;
}) {
  return (
    <g className={root ? 'g0-map-box g0-map-root' : 'g0-map-box'}>
      <rect x={x} y={y} width="140" height="58" rx="9" />
      <text x={x + 70} y={y + (detail ? 24 : 34)} textAnchor="middle">
        {label}
      </text>
      {detail && (
        <text className="g0-map-detail" x={x + 70} y={y + 43} textAnchor="middle">
          {detail}
        </text>
      )}
    </g>
  );
}

function Figure({
  label,
  children,
  caption,
  height = 280,
  compact,
  compactHeight = 465,
}: {
  label: string;
  children: ReactNode;
  caption: string;
  height?: number;
  compact?: ReactNode;
  compactHeight?: number;
}) {
  return (
    <figure className="g0-figure">
      <svg
        className={compact ? 'g0-map-wide' : undefined}
        viewBox={`0 0 660 ${height}`}
        role="img"
        aria-label={label}
      >
        {children}
      </svg>
      {compact && (
        <svg
          className="g0-map-compact"
          viewBox={`0 0 360 ${compactHeight}`}
          role="img"
          aria-label={label}
        >
          {compact}
        </svg>
      )}
      <figcaption>{caption}</figcaption>
    </figure>
  );
}

export function CoordinateMap() {
  return (
    <Figure
      label="G0、四个设备普通坐标及相机从属坐标的典型关系图"
      caption="普通坐标描述设备位置；相机从属坐标把识别结果接入对应设备坐标。"
      compact={
        <>
          <path
            className="g0-map-line"
            d="M180 68V90H4V424M4 139H10M4 234H10M4 329H10M4 424H10M150 234H205M150 329H205M150 424H205"
          />
          <Box x={110} y={10} label="G0" detail="统一参考" root />
          <Box x={10} y={110} label="输送坐标" detail="Transport" />
          <Box x={10} y={205} label="点胶坐标" detail="Dispense" />
          <Box x={10} y={300} label="固晶坐标" detail="Bond" />
          <Box x={10} y={395} label="晶圆台坐标" detail="WaferTable" />
          <Box x={205} y={205} label="点胶相机" detail="从属坐标" />
          <Box x={205} y={300} label="Bond 相机 / 上视" detail="各自的从属坐标" />
          <Box x={205} y={395} label="晶圆相机" detail="从属坐标" />
        </>
      }
    >
      <path
        className="g0-map-line"
        d="M330 68V92H80V110M330 92H245V110M330 92H410V110M330 92H575V110M245 168V210M410 168V210M575 168V210"
      />
      <Box x={260} y={10} label="G0" detail="统一参考" root />
      <Box x={10} y={110} label="输送坐标" detail="Transport" />
      <Box x={175} y={110} label="点胶坐标" detail="Dispense" />
      <Box x={340} y={110} label="固晶坐标" detail="Bond" />
      <Box x={505} y={110} label="晶圆台坐标" detail="WaferTable" />
      <Box x={175} y={210} label="点胶相机" detail="从属坐标" />
      <Box x={340} y={210} label="Bond 相机 / 上视" detail="各自的从属坐标" />
      <Box x={505} y={210} label="晶圆相机" detail="从属坐标" />
    </Figure>
  );
}

export function ProductChain() {
  return (
    <Figure
      label="G0 到输送、载具、基板、模块和焊点的父子坐标链"
      caption="焊点的本地位置依次转换到各层上层，最终得到 G0 位置。"
      height={190}
      compactHeight={480}
      compact={
        <>
          <path
            className="g0-map-line"
            d="M180 68V90M180 148V170M180 228V250M180 308V330M180 388V410"
          />
          {['G0', '输送坐标', '载具', '基板', '模块', '焊点'].map((label, index) => (
            <Box key={label} x={110} y={10 + 80 * index} label={label} root={index === 0} />
          ))}
        </>
      }
    >
      <path className="g0-map-line" d="M150 39H255M395 39H500M570 68V112M500 141H395M255 141H150" />
      <Box x={10} y={10} label="G0" root />
      <Box x={255} y={10} label="输送坐标" />
      <Box x={500} y={10} label="载具" />
      <Box x={500} y={112} label="基板" />
      <Box x={255} y={112} label="模块" />
      <Box x={10} y={112} label="焊点" />
      <text className="g0-map-detail" x="80" y="97" textAnchor="middle">
        本地目标点
      </text>
    </Figure>
  );
}

export function CameraMap() {
  return (
    <Figure
      label="相机像素经标定、加拍照位置、直接父级变换得到 G0 点"
      caption="两个输入必须配套：这次识别的像素点，以及这次拍照对应的上层位置。"
      height={245}
      compactHeight={400}
      compact={
        <>
          <defs>
            <marker
              id="g0-camera-arrow-compact"
              markerWidth="7"
              markerHeight="7"
              refX="6"
              refY="3.5"
              orient="auto"
            >
              <path d="M0 0L7 3.5L0 7" fill="currentColor" />
            </marker>
          </defs>
          <path
            className="g0-map-line g0-map-arrow"
            markerEnd="url(#g0-camera-arrow-compact)"
            d="M150 49H205M275 78V200M150 229H205M275 258V320"
          />
          <Box x={10} y={20} label="相机像素点" detail="CenterX / CenterY" />
          <Box x={205} y={20} label="相机标定变换" detail="Forward" />
          <Box x={10} y={200} label="拍照时上层位置" detail="调用者提供" />
          <Box x={205} y={200} label="两点相加" detail="位于父坐标中" />
          <Box x={205} y={320} label="G0 点" detail="父级 Forward 后" root />
          <text className="g0-map-detail" x="265" y="299" textAnchor="end">
            父级变换
          </text>
        </>
      }
    >
      <defs>
        <marker
          id="g0-camera-arrow"
          markerWidth="7"
          markerHeight="7"
          refX="6"
          refY="3.5"
          orient="auto"
        >
          <path d="M0 0L7 3.5L0 7" fill="currentColor" />
        </marker>
      </defs>
      <path
        className="g0-map-line g0-map-arrow"
        markerEnd="url(#g0-camera-arrow)"
        d="M150 49H255"
      />
      <path
        className="g0-map-line g0-map-arrow"
        markerEnd="url(#g0-camera-arrow)"
        d="M325 78V155"
      />
      <path
        className="g0-map-line g0-map-arrow"
        markerEnd="url(#g0-camera-arrow)"
        d="M150 184H255"
      />
      <path
        className="g0-map-line g0-map-arrow"
        markerEnd="url(#g0-camera-arrow)"
        d="M395 184H500"
      />
      <Box x={10} y={20} label="相机像素点" detail="CenterX / CenterY" />
      <Box x={255} y={20} label="相机标定变换" detail="Forward" />
      <Box x={10} y={155} label="拍照时上层位置" detail="调用者提供" />
      <Box x={255} y={155} label="两点相加" detail="位于父坐标中" />
      <Box x={500} y={155} label="G0 点" detail="父级 Forward 后" root />
      <text className="g0-map-detail" x="445" y="172" textAnchor="middle">
        父级变换
      </text>
    </Figure>
  );
}

export function StorageMap() {
  return (
    <div className="g0-storage" aria-label="坐标参数、标定文件与内存对象的保存关系">
      <div>
        <b>坐标目录 JSON</b>
        <span>名称、父级名称、平移、角度、模式与采点</span>
      </div>
      <div>
        <b>标定文件 .iwcal</b>
        <span>相机像素到物理 XY 的转换关系</span>
      </div>
      <div>
        <b>内存中的对象</b>
        <span>父引用与转换工具按需重建，旧引用需单独核对</span>
      </div>
    </div>
  );
}
