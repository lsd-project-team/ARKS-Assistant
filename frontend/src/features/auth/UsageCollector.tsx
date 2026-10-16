import { useEffect } from 'react';
import { useAuth } from './AuthContext';
import { sessionFetch } from './session';
import { activeSlice } from './activity';

export function UsageCollector() {
  const user = useAuth().session?.user;
  useEffect(() => {
    if (user?.role !== 'user') return;
    const visit = crypto.randomUUID();
    let sequence = 0,
      pendingMs = 0,
      previous = performance.now();
    let interaction = previous,
      visible = !document.hidden,
      focused = document.hasFocus();
    function tick() {
      const now = performance.now();
      pendingMs = Math.min(
        15000,
        pendingMs + activeSlice(now - previous, now - interaction, visible, focused),
      );
      previous = now;
    }
    function flush() {
      tick();
      const active_ms = Math.floor(pendingMs);
      pendingMs = 0;
      void sessionFetch('/api/usage/heartbeat', {
        method: 'POST',
        keepalive: true,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ visit_id: visit, sequence: ++sequence, active_ms }),
      }).catch(() => {
        /* 未送达的时间不补造；下一次按真实活动继续采集。 */
      });
    }
    const act = () => {
      tick();
      interaction = performance.now();
    };
    const visibility = () => {
      tick();
      visible = !document.hidden;
      if (visible) interaction = performance.now();
      flush();
    };
    const focus = () => {
      tick();
      focused = true;
      interaction = performance.now();
    };
    const blur = () => {
      tick();
      focused = false;
      flush();
    };
    const events = ['pointerdown', 'pointermove', 'keydown', 'wheel', 'touchstart'] as const;
    events.forEach((event) => window.addEventListener(event, act, { passive: true }));
    document.addEventListener('visibilitychange', visibility);
    window.addEventListener('focus', focus);
    window.addEventListener('blur', blur);
    window.addEventListener('pagehide', flush);
    // 延迟到首个绘制，避免 StrictMode 的试挂载制造一次额外访问。
    const first = requestAnimationFrame(flush);
    const ticker = window.setInterval(tick, 1000);
    const sender = window.setInterval(() => {
      if (!document.hidden) flush();
    }, 10000);
    return () => {
      cancelAnimationFrame(first);
      clearInterval(ticker);
      clearInterval(sender);
      events.forEach((event) => window.removeEventListener(event, act));
      document.removeEventListener('visibilitychange', visibility);
      window.removeEventListener('focus', focus);
      window.removeEventListener('blur', blur);
      window.removeEventListener('pagehide', flush);
    };
  }, [user?.id, user?.role]);
  return null;
}
