export interface GuidedDiagram {
  path: string;
  title: string;
  sha256: string;
  specSha256: string;
  steps: Record<string, string[]>;
}

// 同一阅读步骤可以覆盖条件与返回节点；点击任一分支仍回到对应说明。
export const guidedDiagrams: Record<string, GuidedDiagram> = {
  boot: {
    path: 'startup-reading/boot.html',
    title: '开机回零与主窗体门控',
    sha256: 'e4b6d41678deca115059b87bba37d9ffeaf1fb300fc7af189884845760fb210e',
    specSha256: '2d71621d0e3a4733ab37dd9141824d89b71bb31131c8fe7fc1fb9bc92a605fb0',
    steps: {
      'boot-option': ['boot-option'],
      'boot-home': ['boot-home', 'boot-form'],
      'boot-load': ['boot-gate', 'boot-blocked', 'boot-load'],
    },
  },
  home: {
    path: 'startup-reading/home.html',
    title: 'AllAxisGoHome 的正常返回路径',
    sha256: '8d4ffc5bb7368f790a31009e5b86deee682de25228c6bb714ed8a0e2e13d1c1d',
    specSha256: '685144f60e42e9c3bafdf341c97560d732ce0664fbb3ef0a732f42054d422792',
    steps: {
      'home-confirm': ['home-confirm', 'home-failed'],
      'home-prepare': ['home-prepare'],
      'home-all-axes': ['home-check'],
      'home-success': ['home-success'],
    },
  },
  'production-start': {
    path: 'startup-reading/production.html',
    title: '确认、准备检查与任务放行',
    sha256: '1cf8102d7a3f26d26285f902ae270948ca19ac1a49ae1982d1fd470e7c6af73b',
    specSha256: 'b671cfe6c294738cf9f9f0f080ff590e4f61d99cc50ca4cfb5fc242cacb09709',
    steps: {
      operator: ['production-confirm'],
      reset: ['production-reset'],
      gates: ['production-gates', 'production-return'],
      safe: ['production-safe'],
      environment: ['production-environment'],
      working: ['production-working'],
      dispatch: ['production-dispatch'],
    },
  },
};

export const hasGuidedReading = (page: string) =>
  ['startup', 'startup-workflow', 'machine-start-readiness-workflow'].includes(page);
