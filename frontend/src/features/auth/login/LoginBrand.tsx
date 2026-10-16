export function LoginBrand() {
  return (
    <section className="login-brand-panel" aria-label="ARKS 工程知识空间">
      <div className="login-brand-copy">
        <p className="login-eyebrow">ARKS WORKSPACE</p>
        <h2>工程知识与协作空间</h2>
        <p className="login-brand-description">源码问答 · 功能资料 · 交接协作</p>
      </div>
      <div className="login-brand-visual" aria-hidden="true">
        <svg className="login-engineering-grid" viewBox="0 0 520 360" fill="none">
          <defs>
            <pattern id="login-grid" width="44" height="44" patternUnits="userSpaceOnUse">
              <path d="M44 0H0V44" />
            </pattern>
            <radialGradient id="login-grid-fade">
              <stop offset="0.6" stopColor="white" />
              <stop offset="1" stopColor="black" />
            </radialGradient>
            <mask id="login-grid-mask">
              <rect width="520" height="360" fill="url(#login-grid-fade)" />
            </mask>
          </defs>
          <g mask="url(#login-grid-mask)">
            <rect width="520" height="360" fill="url(#login-grid)" />
            <circle cx="260" cy="172" r="144" strokeDasharray="4 4" />
            <circle cx="408" cy="96" r="32" />
            <circle cx="123" cy="276" r="40" />
            <path d="M260 8V344M68 172H452M116 28V316M404 28V316M60 316H460" />
            <path d="M68 316L103 281M78 316H68V306M68 54V286M62 54H74M62 286H74" />
          </g>
        </svg>
        <div className="login-mark-ground" />
        <img className="login-hero-mark" src="/brand/arks-login-mark.png" alt="" />
      </div>
    </section>
  );
}
