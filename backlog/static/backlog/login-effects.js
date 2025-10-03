/* ==========================================================
   NEUSI · Fondo “polygons” con interacción de mouse
   - Líneas más grandes
   - Atracción suave al cursor
   - Altamente configurable (ver sección CONFIG)
   ========================================================== */

(function () {
  // ====================== CONFIG ==========================
  const CONFIG = {
    POINTS: 95,        // Cantidad de puntos (más = más líneas)
    SPEED: 0.25,           // Velocidad base de movimiento
    NODE_RADIUS: 2.4,      // Radio del punto (nodo)
    LINE_WIDTH: 1.2,       // Grosor de las líneas
    LINK_DISTANCE: 180,    // Distancia máx. para dibujar línea (más grande => redes más “largas”)
    MOUSE_INFLUENCE: 240,  // Radio de influencia del cursor
    MOUSE_FORCE: 0.06,     // Fuerza con que los nodos son atraídos hacia el cursor
    FADE_LINES_WITH_DIST: true, // Atenuar línea con la distancia
    MAX_OPACITY: 0.9,      // Opacidad máxima de la línea en el centro
    COLOR: 'rgba(207, 215, 255, 1)', // Color base de las líneas/puntos
    GLOW: true,            // Halo sutil para líneas
  };

  // ====================== CANVAS ==========================
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  canvas.style.position = 'fixed';
  canvas.style.left = 0;
  canvas.style.top = 0;
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  canvas.style.pointerEvents = 'none'; // El canvas no captura clicks
  canvas.style.zIndex = 1;             // Debajo del contenido (el CSS ya pone el contenido en z-index:3)
  document.body.appendChild(canvas);

  let W = canvas.width  = window.innerWidth  * devicePixelRatio;
  let H = canvas.height = window.innerHeight * devicePixelRatio;

  // ====================== ESTADO ==========================
  const points = [];
  const mouse = { x: -9999, y: -9999, active: false };

  function rand(min, max) { return Math.random() * (max - min) + min; }

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
    const count = Math.round(CONFIG.POINTS * (W * H) / (1920 * 1080)); // Escala con tamaño de pantalla
    for (let i = 0; i < count; i++) points.push(createPoint());
  }

  // ====================== INTERACCIÓN ======================
  window.addEventListener('mousemove', (e) => {
    const rect = document.body.getBoundingClientRect();
    mouse.x = (e.clientX - rect.left) * devicePixelRatio;
    mouse.y = (e.clientY - rect.top)  * devicePixelRatio;
    mouse.active = true;
  });
  window.addEventListener('mouseleave', () => { mouse.active = false; });

  window.addEventListener('resize', () => {
    W = canvas.width  = window.innerWidth  * devicePixelRatio;
    H = canvas.height = window.innerHeight * devicePixelRatio;
    init();
  });

  // ====================== DIBUJO ==========================
  function step() {
    ctx.clearRect(0, 0, W, H);

    // Actualizar puntos
    for (const p of points) {
      // Atracción al mouse (parcial, con amortiguación)
      if (mouse.active) {
        const dx = mouse.x - p.x;
        const dy = mouse.y - p.y;
        const dist2 = dx*dx + dy*dy;
        const r = CONFIG.MOUSE_INFLUENCE * devicePixelRatio;
        if (dist2 < r*r) {
          const d = Math.sqrt(dist2) || 0.001;
          const ux = dx / d, uy = dy / d;
          const force = (1 - d / r) * CONFIG.MOUSE_FORCE;
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

    // Dibujar conexiones
    ctx.lineWidth = CONFIG.LINE_WIDTH * devicePixelRatio;
    ctx.strokeStyle = CONFIG.COLOR;

    if (CONFIG.GLOW) {
      ctx.shadowColor = 'rgba(148, 163, 255, 0.35)'; // halo azulado
      ctx.shadowBlur = 6 * devicePixelRatio;
    } else {
      ctx.shadowBlur = 0;
    }

    const linkDist = CONFIG.LINK_DISTANCE * devicePixelRatio;
    for (let i = 0; i < points.length; i++) {
      const p1 = points[i];

      // Nodo
      ctx.beginPath();
      ctx.fillStyle = CONFIG.COLOR;
      ctx.arc(p1.x, p1.y, CONFIG.NODE_RADIUS * devicePixelRatio, 0, Math.PI * 2);
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
  step();
})();
