/* ==========================================================
   NEUSI · Fondo “polygons” con interacción
   - Optimizado para MÓVIL (reduce motion / menos puntos)
   - Z-index seguro bajo el contenido (no bloquea taps)
   ========================================================== */
(function () {
  // ======== GUARDAS DE RENDIMIENTO / ACCESIBILIDAD ========
  const prefersReduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const vw = Math.min(window.innerWidth, window.innerHeight);
  const isTinyScreen = vw < 360;            // pantallas muy pequeñas
  const isMobile = /Mobi|Android/i.test(navigator.userAgent);

  if (prefersReduce || isTinyScreen) {
    // No dibujar efecto en condiciones adversas
    return;
  }

  // ====================== CONFIG ==========================
  const CONFIG = {
    POINTS: 95,                // base escritorio
    SPEED: 0.25,
    NODE_RADIUS: 2.4,
    LINE_WIDTH: 1.2,
    LINK_DISTANCE: 180,
    MOUSE_INFLUENCE: 240,
    MOUSE_FORCE: 0.06,
    FADE_LINES_WITH_DIST: true,
    MAX_OPACITY: 0.9,
    COLOR: 'rgba(207, 215, 255, 1)',
    GLOW: true,
  };

  // Reducir carga en móvil (≈50–60%)
  if (isMobile || window.innerWidth < 480) {
    CONFIG.POINTS = Math.max(40, Math.round(CONFIG.POINTS * 0.55));
    CONFIG.LINK_DISTANCE = 150;
    CONFIG.MOUSE_INFLUENCE = 200;
  }

  // ====================== CANVAS ==========================
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  canvas.style.position = 'fixed';
  canvas.style.left = 0;
  canvas.style.top = 0;
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  canvas.style.pointerEvents = 'none'; // no captura clics/taps
  canvas.style.zIndex = 0;             // bajo el contenido
  document.body.appendChild(canvas);

  let DPR = Math.max(1, Math.min(window.devicePixelRatio || 1, 2)); // cap DPR a 2
  let W = canvas.width  = Math.floor(window.innerWidth  * DPR);
  let H = canvas.height = Math.floor(window.innerHeight * DPR);

  // ====================== ESTADO ==========================
  const points = [];
  const mouse = { x: -9999, y: -9999, active: false };

  const rand = (min, max) => Math.random() * (max - min) + min;

  function createPoint() {
    return {
      x: rand(0, W),
      y: rand(0, H),
      vx: rand(-CONFIG.SPEED, CONFIG.SPEED),
      vy: rand(-CONFIG.SPEED, CONFIG.SPEED)
    };
  }

  function init() {
    points.length = 0;
    // Escala por área de pantalla (normalizado a 1920x1080)
    const baseCount = Math.round(CONFIG.POINTS * (W * H) / (1920 * 1080) * (1 / (DPR * 0.9)));
    const count = Math.max(28, baseCount);
    for (let i = 0; i < count; i++) points.push(createPoint());
  }

  // ====================== INTERACCIÓN ======================
  window.addEventListener('mousemove', (e) => {
    const rect = document.body.getBoundingClientRect();
    mouse.x = (e.clientX - rect.left) * DPR;
    mouse.y = (e.clientY - rect.top)  * DPR;
    mouse.active = true;
  }, { passive: true });

  window.addEventListener('touchmove', (e) => {
    const t = e.touches[0];
    if (!t) return;
    const rect = document.body.getBoundingClientRect();
    mouse.x = (t.clientX - rect.left) * DPR;
    mouse.y = (t.clientY - rect.top)  * DPR;
    mouse.active = true;
  }, { passive: true });

  window.addEventListener('mouseleave', () => { mouse.active = false; });
  window.addEventListener('touchend', () => { mouse.active = false; });

  // Resize con throttle
  let resizeTick = false;
  function onResize() {
    if (resizeTick) return;
    resizeTick = true;
    requestAnimationFrame(() => {
      DPR = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
      W = canvas.width  = Math.floor(window.innerWidth  * DPR);
      H = canvas.height = Math.floor(window.innerHeight * DPR);
      init();
      resizeTick = false;
    });
  }
  window.addEventListener('resize', onResize);

  // Pausa si la pestaña no está visible (ahorra batería)
  let running = true;
  document.addEventListener('visibilitychange', () => {
    running = !document.hidden;
    if (running) requestAnimationFrame(step);
  });

  // ====================== DIBUJO ==========================
  function step() {
    if (!running) return;

    ctx.clearRect(0, 0, W, H);

    // Actualizar puntos
    const mouseR = CONFIG.MOUSE_INFLUENCE * DPR;
    for (const p of points) {
      if (mouse.active) {
        const dx = mouse.x - p.x;
        const dy = mouse.y - p.y;
        const dist2 = dx*dx + dy*dy;
        if (dist2 < mouseR*mouseR) {
          const d = Math.sqrt(dist2) || 0.001;
          const ux = dx / d, uy = dy / d;
          const force = (1 - d / mouseR) * CONFIG.MOUSE_FORCE;
          p.vx += ux * force;
          p.vy += uy * force;
        }
      }

      p.x += p.vx;
      p.y += p.vy;

      // Rebote en bordes
      if (p.x < 0 || p.x > W) p.vx *= -1;
      if (p.y < 0 || p.y > H) p.vy *= -1;
    }

    // Dibujar conexiones + nodos
    ctx.lineWidth = CONFIG.LINE_WIDTH * DPR;
    ctx.strokeStyle = CONFIG.COLOR;
    ctx.shadowColor = CONFIG.GLOW ? 'rgba(148,163,255,0.35)' : 'transparent';
    ctx.shadowBlur = CONFIG.GLOW ? 6 * DPR : 0;

    const linkDist = CONFIG.LINK_DISTANCE * DPR;
    for (let i = 0; i < points.length; i++) {
      const p1 = points[i];

      // Nodo
      ctx.beginPath();
      ctx.fillStyle = CONFIG.COLOR;
      ctx.arc(p1.x, p1.y, CONFIG.NODE_RADIUS * DPR, 0, Math.PI * 2);
      ctx.fill();

      for (let j = i + 1; j < points.length; j++) {
        const p2 = points[j];
        const dx = p1.x - p2.x;
        const dy = p1.y - p2.y;
        const d = Math.hypot(dx, dy);
        if (d < linkDist) {
          let alpha = CONFIG.MAX_OPACITY;
          if (CONFIG.FADE_LINES_WITH_DIST) {
            alpha = Math.max(0, CONFIG.MAX_OPACITY * (1 - d / linkDist));
          }
          ctx.globalAlpha = alpha;
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      }
    }

    requestAnimationFrame(step);
  }

  // Init & run
  init();
  requestAnimationFrame(step);
})();
