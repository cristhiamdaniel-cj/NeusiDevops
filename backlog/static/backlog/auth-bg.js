// =====================  NEUSI · AUTH BACKGROUND  =====================
(function () {
  const canvas = document.createElement('canvas');
  canvas.id = 'neusi-bg';
  document.body.appendChild(canvas);
  const ctx = canvas.getContext('2d');

  let W = 0, H = 0;
  const DPR = Math.min(window.devicePixelRatio || 1, 2);
  function resize() {
    W = canvas.width  = Math.floor(window.innerWidth  * DPR);
    H = canvas.height = Math.floor(window.innerHeight * DPR);
    canvas.style.width  = window.innerWidth  + 'px';
    canvas.style.height = window.innerHeight + 'px';
  }
  resize();
  window.addEventListener('resize', resize);

  // Parámetros “grandes”
  const CFG = {
    points: Math.min(110, Math.floor((window.innerWidth * window.innerHeight)/14000)), // densidad
    maxDist: 220 * DPR,           // distancia para líneas
    mouseRadius: 300 * DPR,       // radio de influencia del mouse
    baseSpeed: 0.12,              // velocidad base
    repelStrength: 0.045,         // fuerza repulsión
    attractStrength: 0.02         // fuerza atracción
  };

  const mouse = { x: -9999, y: -9999, down: false };
  window.addEventListener('mousemove', e => {
    const r = canvas.getBoundingClientRect();
    mouse.x = (e.clientX - r.left) * DPR;
    mouse.y = (e.clientY - r.top ) * DPR;
  });
  window.addEventListener('mouseleave', () => { mouse.x = mouse.y = -9999; });
  window.addEventListener('mousedown', () => mouse.down = true);
  window.addEventListener('mouseup',   () => mouse.down = false);

  function rand(a,b){ return a + Math.random()*(b-a); }

  const pts = [];
  for(let i=0;i<CFG.points;i++){
    pts.push({
      x: rand(0,W),
      y: rand(0,H),
      vx: rand(-CFG.baseSpeed, CFG.baseSpeed),
      vy: rand(-CFG.baseSpeed, CFG.baseSpeed)
    });
  }

  function step(){
    ctx.clearRect(0,0,W,H);

    // Dibujar conexiones
    for(let i=0;i<pts.length;i++){
      for(let j=i+1;j<pts.length;j++){
        const dx = pts[i].x - pts[j].x;
        const dy = pts[i].y - pts[j].y;
        const d2 = dx*dx + dy*dy;
        if (d2 < CFG.maxDist * CFG.maxDist){
          const a = 1 - Math.sqrt(d2)/CFG.maxDist;
          ctx.strokeStyle = `rgba(255,255,255,${0.08 * a})`;
          ctx.lineWidth = 1 * DPR;
          ctx.beginPath();
          ctx.moveTo(pts[i].x, pts[i].y);
          ctx.lineTo(pts[j].x, pts[j].y);
          ctx.stroke();
        }
      }
    }

    // Mover puntos + interacción con mouse
    for(const p of pts){
      // borde rebotante
      p.x += p.vx;
      p.y += p.vy;
      if(p.x < 0 || p.x > W) p.vx *= -1;
      if(p.y < 0 || p.y > H) p.vy *= -1;

      // interacción mouse (repelente o suave atracción si está presionado)
      const dx = p.x - mouse.x;
      const dy = p.y - mouse.y;
      const d2 = dx*dx + dy*dy;
      const rad2 = CFG.mouseRadius * CFG.mouseRadius;
      if (d2 < rad2){
        const d = Math.max(Math.sqrt(d2), 0.001);
        const ux = dx/d, uy = dy/d;
        const f = (mouse.down ? -CFG.attractStrength : CFG.repelStrength) * (1 - d/CFG.mouseRadius);
        p.vx += ux * f * 6;
        p.vy += uy * f * 6;
      }

      // partícula
      ctx.fillStyle = 'rgba(255,255,255,0.9)';
      ctx.beginPath();
      ctx.arc(p.x, p.y, 2.2*DPR, 0, Math.PI*2);
      ctx.fill();
    }

    // “scan line” suave (opcional)
    const t = Date.now() * 0.00008;
    const scanY = (Math.sin(t) * 0.5 + 0.5) * H;
    const grad = ctx.createLinearGradient(0, scanY-2, 0, scanY+2);
    grad.addColorStop(0,   'rgba(255,255,255,0)');
    grad.addColorStop(0.5, 'rgba(255,255,255,0.05)');
    grad.addColorStop(1,   'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, scanY-2, W, 4);

    requestAnimationFrame(step);
  }
  step();
})();
