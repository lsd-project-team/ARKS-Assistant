export type DiagramBounds = readonly [number, number, number, number];
export interface Camera {
  x: number;
  y: number;
  scale: number;
}
export interface Viewport {
  width: number;
  height: number;
}
const margin = 24;

export function fitCamera(bounds: DiagramBounds, viewport: Viewport): Camera {
  const [x, y, width, height] = bounds;
  return {
    x: x + width / 2,
    y: y + height / 2,
    scale: Math.min(
      Math.max(1, viewport.width - margin * 2) / width,
      Math.max(1, viewport.height - margin * 2) / height,
    ),
  };
}

/** 图比窗口小时固定在中央；放大后也不能拖过边缘，把一整侧移出可访问范围。 */
export function boundCamera(camera: Camera, bounds: DiagramBounds, viewport: Viewport): Camera {
  const [x, y, width, height] = bounds;
  const constrain = (center: number, start: number, size: number, pixels: number) => {
    const half = pixels / camera.scale / 2;
    if (half * 2 >= size) return start + size / 2;
    return Math.min(start + size - half, Math.max(start + half, center));
  };
  return {
    ...camera,
    x: constrain(camera.x, x, width, viewport.width),
    y: constrain(camera.y, y, height, viewport.height),
  };
}

export function zoomCamera(
  camera: Camera,
  bounds: DiagramBounds,
  viewport: Viewport,
  factor: number,
  anchor = { x: viewport.width / 2, y: viewport.height / 2 },
): Camera {
  const fitted = fitCamera(bounds, viewport).scale;
  const scale = Math.min(Math.max(4, fitted), Math.max(fitted / 4, camera.scale * factor));
  const dx = anchor.x - viewport.width / 2,
    dy = anchor.y - viewport.height / 2;
  return boundCamera(
    {
      scale,
      x: camera.x + dx / camera.scale - dx / scale,
      y: camera.y + dy / camera.scale - dy / scale,
    },
    bounds,
    viewport,
  );
}

export function cameraViewBox(camera: Camera, viewport: Viewport) {
  const width = viewport.width / camera.scale,
    height = viewport.height / camera.scale;
  return [camera.x - width / 2, camera.y - height / 2, width, height];
}

// 长竖图随页面延展，避免被固定高度压成小字；图内不再出现裁切或滚动条。
export function diagramHeight(bounds: DiagramBounds, width: number) {
  const scale = Math.min(1.5, Math.max(1, width - margin * 2) / bounds[2]);
  return Math.max(320, Math.ceil(bounds[3] * scale + margin * 2));
}
