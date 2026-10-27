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
  readingMinWidth?: number;
  readingFontSize?: number;
}
// 路径和指纹来自 Archify 3.2.0 finalize 的实际通过回执。
export const coordinateDiagrams = [
  {
    id: 'device-tree',
    reading: {
      path: 'g0-archify/device-overview.html',
      sha256: 'ce363902b398a38727e012f7ba2dc5228a14be18db0d6468e232369b6bb9fad1',
      specificationSha256: 'f0568d4fb46dfdd031f60d1e0fde68ac910e6be6d95031f892ed8301ba4c6821',
    },
    readingMinWidth: 840,
    readingFontSize: 20,
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
    reading: {
      path: 'g0-archify/product-reading.html',
      sha256: '5bc6762cf8a9ba5ef379ff9da5844050d79a5b7217913bb96c653184664fbf93',
      specificationSha256: '0db718782120f163b195fdae77378d1085ef520551253f6ef9c52dc9efaf25f2',
    },
    narrow: {
      path: 'g0-archify/product-tree.html',
      sha256: 'bc44763ae5e33ffc955b69c5fc2154a97358b0d45857eb74bf1bbc4e9dd0bab7',
      specificationSha256: 'd6de0c64c5bee67da5215bf3e0bb35b6bceae2336bb38959005eef7ffe5b0b38',
    },
    readingMinWidth: 960,
    readingFontSize: 20,
    title: '产品坐标的逐层父链',
    path: 'g0-archify/product-tree.html',
    sha256: 'bc44763ae5e33ffc955b69c5fc2154a97358b0d45857eb74bf1bbc4e9dd0bab7',
    specificationSha256: 'd6de0c64c5bee67da5215bf3e0bb35b6bceae2336bb38959005eef7ffe5b0b38',
  },
  {
    id: 'camera-workflow',
    reading: {
      path: 'g0-archify/camera-overview.html',
      sha256: '33127602bb80a17ea59e879c4310e85ce6f9fa6beabcc0aaa87246c326d0e780',
      specificationSha256: '36ae2e373d30db8e62166f13c385a191d9d997161f857b689f586b7c5b9ea1ea',
    },
    readingMinWidth: 880,
    readingFontSize: 20,
    narrow: {
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
