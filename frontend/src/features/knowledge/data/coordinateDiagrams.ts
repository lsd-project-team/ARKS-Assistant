export interface CoordinateArtifact {
  path: string;
  sha256: string;
  specificationSha256: string;
}
export interface CoordinateDiagram extends CoordinateArtifact {
  id: string;
  title: string;
  reading?: CoordinateArtifact;
  narrow?: CoordinateArtifact;
}
// 路径和指纹来自 Archify 3.2.0 finalize 的实际通过回执。
export const coordinateDiagrams = [
  {
    id: 'device-tree',
    narrow: {
      path: 'g0-archify/device-reading.html',
      sha256: '18141b1be7b2eb237203d3496595e74ac259217e8766cf9801051ced1bdba639',
      specificationSha256: '28e3c218e2ae99b4ba4e25e054935ef7bf57c29c5cd282ac0a4d749b74b1b46b',
    },
    title: '设备与相机的典型父级',
    path: 'g0-archify/device-tree.html',
    sha256: 'a2b1c13ad99e306ec337715e955acc2a03b83621fefe6862388b64e964fdc541',
    specificationSha256: '41125b4eae4ec8335fd5fee66d06bdce7dd787e48d00c404bbfe0ae4dc656944',
  },
  {
    id: 'product-tree',
    title: '产品坐标的逐层父链',
    path: 'g0-archify/product-tree.html',
    sha256: 'bc44763ae5e33ffc955b69c5fc2154a97358b0d45857eb74bf1bbc4e9dd0bab7',
    specificationSha256: 'd6de0c64c5bee67da5215bf3e0bb35b6bceae2336bb38959005eef7ffe5b0b38',
  },
  {
    id: 'camera-workflow',
    reading: {
      path: 'g0-archify/camera-reading.html',
      sha256: '64bb14e52d264a092ac59949be57831c70507f45347e4b98d328304d854baa86',
      specificationSha256: 'ba615c8b3c34ab7cf6eb6d7f53ae061d9bd759f8335c5b3cbf4aec8a456046fc',
    },
    title: '相机像素怎样成为 G0 点',
    path: 'g0-archify/camera-workflow.html',
    sha256: '9be54f1597bc6247a3dd4c70e1c2d7f05cfbb77d4277e0683a3a35645c6d77fa',
    specificationSha256: '5f6cfe2bde96abe816377e947367f87ef937361b6d67f9e600b93c17bd023dd8',
  },
] as const;

export const coordinateArtifacts: readonly CoordinateArtifact[] = coordinateDiagrams.flatMap(
  (diagram) => [
    diagram,
    ...('reading' in diagram ? [diagram.reading] : []),
    ...('narrow' in diagram ? [diagram.narrow] : []),
  ],
);
