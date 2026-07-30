import { useEffect, useRef } from "react";

interface Drop {
  x: number; y: number; speed: number; length: number; opacity: number;
}
interface Petal {
  x: number; y: number; speed: number; swayAmp: number; swayFreq: number;
  phase: number; opacity: number; size: number;
}

const DROP_COUNT = 30;
const PETAL_COUNT = 4;

export default function RainEffect() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    // ── create drops ──
    const drops: Drop[] = Array.from({ length: DROP_COUNT }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      speed: 0.4 + Math.random() * 0.7,
      length: 8 + Math.random() * 14,
      opacity: 0.08 + Math.random() * 0.12,
    }));

    // ── create petals ──
    const petals: Petal[] = Array.from({ length: PETAL_COUNT }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      speed: 0.15 + Math.random() * 0.25,
      swayAmp: 20 + Math.random() * 40,
      swayFreq: 0.008 + Math.random() * 0.012,
      phase: Math.random() * Math.PI * 2,
      opacity: 0.1 + Math.random() * 0.12,
      size: 8 + Math.random() * 10,
    }));

    let frame = 0;
    const loop = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // ── rain ──
      for (const d of drops) {
        d.y += d.speed;
        if (d.y > canvas.height + 20) { d.y = -20; d.x = Math.random() * canvas.width; }
        ctx.beginPath();
        ctx.moveTo(d.x, d.y);
        ctx.lineTo(d.x - 0.5, d.y + d.length);
        ctx.strokeStyle = `rgba(200,215,235,${d.opacity})`;
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }

      // ── petals ──
      for (const p of petals) {
        p.y += p.speed;
        p.phase += p.swayFreq;
        const sway = Math.sin(p.phase) * p.swayAmp;
        if (p.y > canvas.height + 20) { p.y = -20; p.x = Math.random() * canvas.width; }
        ctx.save();
        ctx.translate(p.x + sway, p.y);
        ctx.rotate(Math.sin(p.phase * 1.3) * 0.2);
        ctx.fillStyle = `rgba(245,200,210,${p.opacity})`;
        ctx.beginPath();
        ctx.ellipse(0, 0, p.size, p.size * 0.55, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      frame++;
      animRef.current = requestAnimationFrame(loop);
    };

    animRef.current = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
      }}
    />
  );
}
