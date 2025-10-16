"use client";
import { useEffect } from "react";

export default function Polygons() {
  useEffect(() => {
    // ---- configuración ligera (igual al login) ----
    const prefersReduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduce) return;

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d")!;
    canvas.style.position = "fixed";
    canvas.style.inset = "0";
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.pointerEvents = "none";
    canvas.style.zIndex = "0";
    document.body.appendChild(canvas);

    let DPR = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
    let W = (canvas.width = Math.floor(window.innerWidth * DPR));
    let H = (canvas.height = Math.floor(window.innerHeight * DPR));

    const CFG = {
      P: 90,
      SPEED: 0.25,
      R: 2.4,
      LW: 1.2,
      LINK: 180,
      MAXA: 0.9,
      COLOR: "rgba(207,215,255,1)",
      GLOW: true,
    };

    const pts: { x: number; y: number; vx: number; vy: number }[] = [];
    const rnd = (a: number, b: number) => Math.random() * (b - a) + a;
    const mk = () => ({ x: rnd(0, W), y: rnd(0, H), vx: rnd(-CFG.SPEED, CFG.SPEED), vy: rnd(-CFG.SPEED, CFG.SPEED) });
    const init = () => {
      pts.length = 0;
      const n = Math.max(28, Math.round(CFG.P * (W * H) / (1920 * 1080) * (1 / (DPR * 0.9))));
      for (let i = 0; i < n; i++) pts.push(mk());
    };

    const step = () => {
      ctx.clearRect(0, 0, W, H);
      ctx.lineWidth = CFG.LW * DPR;
      ctx.strokeStyle = CFG.COLOR;
      ctx.shadowColor = CFG.GLOW ? "rgba(148,163,255,.35)" : "transparent";
      ctx.shadowBlur = CFG.GLOW ? 6 * DPR : 0;

      const link = CFG.LINK * DPR;
      for (let i = 0; i < pts.length; i++) {
        const p1 = pts[i];
        p1.x += p1.vx; p1.y += p1.vy;
        if (p1.x < 0 || p1.x > W) p1.vx *= -1;
        if (p1.y < 0 || p1.y > H) p1.vy *= -1;

        // nodo
        ctx.beginPath();
        ctx.fillStyle = CFG.COLOR;
        ctx.arc(p1.x, p1.y, CFG.R * DPR, 0, Math.PI * 2);
        ctx.fill();

        for (let j = i + 1; j < pts.length; j++) {
          const p2 = pts[j];
          const dx = p1.x - p2.x, dy = p1.y - p2.y;
          const d = Math.hypot(dx, dy);
          if (d < link) {
            const a = Math.max(0, CFG.MAXA * (1 - d / link));
            ctx.globalAlpha = a;
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
            ctx.globalAlpha = 1;
          }
        }
      }
      req = requestAnimationFrame(step);
    };

    let req = requestAnimationFrame(step);
    init();

    const onResize = () => {
      DPR = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
      W = canvas.width = Math.floor(window.innerWidth * DPR);
      H = canvas.height = Math.floor(window.innerHeight * DPR);
      init();
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(req);
      window.removeEventListener("resize", onResize);
      canvas.remove();
    };
  }, []);

  return null;
}
