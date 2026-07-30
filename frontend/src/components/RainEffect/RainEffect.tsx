import { useEffect, useRef } from "react";

interface Drop {
  x: number; y: number;
  rx: number; ry: number;
  rotation: number;
  opacity: number;
  // sliding drops
  sliding: boolean;
  speed: number;
  swayAmp: number; swayFreq: number; phase: number;
  trailY: number;
  trailOpacity: number;
}

const TOTAL = 75;
const SLIDERS = 6;

function drawDroplet(ctx: CanvasRenderingContext2D, d: Drop) {
  ctx.save();
  ctx.translate(d.x, d.y);
  ctx.rotate(d.rotation);

  // Body — radial gradient for 3D convex look
  const bodyGrad = ctx.createRadialGradient(
    -d.rx * 0.15, -d.ry * 0.2, 0,
    0, 0, Math.max(d.rx, d.ry)
  );
  bodyGrad.addColorStop(0, `rgba(255,255,255,${d.opacity * 1.3})`);
  bodyGrad.addColorStop(0.45, `rgba(220,225,230,${d.opacity * 0.5})`);
  bodyGrad.addColorStop(0.8, `rgba(180,190,200,${d.opacity * 0.18})`);
  bodyGrad.addColorStop(1, `rgba(140,155,170,0)`);

  ctx.beginPath();
  ctx.ellipse(0, 0, d.rx, d.ry, 0, 0, Math.PI * 2);
  ctx.fillStyle = bodyGrad;
  ctx.fill();

  // Edge shadow ring — light refraction look
  ctx.beginPath();
  ctx.ellipse(0, 0, d.rx, d.ry, 0, 0, Math.PI * 2);
  ctx.strokeStyle = `rgba(150,165,175,${d.opacity * 0.35})`;
  ctx.lineWidth = 0.6;
  ctx.stroke();

  // Highlight spot — top-left bright reflection
  const hlGrad = ctx.createRadialGradient(-d.rx * 0.3, -d.ry * 0.35, 0, -d.rx * 0.3, -d.ry * 0.35, d.rx * 0.55);
  hlGrad.addColorStop(0, `rgba(255,255,255,${d.opacity * 0.9})`);
  hlGrad.addColorStop(1, `rgba(255,255,255,0)`);
  ctx.beginPath();
  ctx.ellipse(-d.rx * 0.3, -d.ry * 0.35, d.rx * 0.55, d.ry * 0.55, 0, 0, Math.PI * 2);
  ctx.fillStyle = hlGrad;
  ctx.fill();

  ctx.restore();
}

function drawTrail(ctx: CanvasRenderingContext2D, d: Drop) {
  if (d.trailOpacity <= 0) return;
  const grad = ctx.createLinearGradient(d.x, d.trailY, d.x, d.y);
  grad.addColorStop(0, `rgba(200,210,218,0)`);
  grad.addColorStop(0.5, `rgba(210,218,224,${d.trailOpacity * 0.3})`);
  grad.addColorStop(1, `rgba(220,225,230,${d.trailOpacity * 0.15})`);
  ctx.beginPath();
  ctx.moveTo(d.x - d.rx * 0.3, d.y);
  ctx.lineTo(d.x - d.rx * 0.15, d.trailY);
  ctx.lineTo(d.x + d.rx * 0.15, d.trailY);
  ctx.lineTo(d.x + d.rx * 0.3, d.y);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();
}

function spawnDrop(canvasW: number, canvasH: number, slidersOnly: boolean): Drop {
  const sliding = slidersOnly || (!slidersOnly && Math.random() < SLIDERS / TOTAL);
  const big = sliding || Math.random() < 0.12;
  const size = big ? 5 + Math.random() * 10 : 1.5 + Math.random() * 5;
  const ratio = 0.7 + Math.random() * 0.5;
  return {
    x: Math.random() * canvasW,
    y: Math.random() * canvasH,
    rx: size,
    ry: size * ratio,
    rotation: (Math.random() - 0.5) * 0.6,
    opacity: 0.22 + Math.random() * 0.38,
    sliding,
    speed: sliding ? 0.06 + Math.random() * 0.2 : 0,
    swayAmp: sliding ? 3 + Math.random() * 12 : 0,
    swayFreq: sliding ? 0.004 + Math.random() * 0.008 : 0,
    phase: Math.random() * Math.PI * 2,
    trailY: 0,
    trailOpacity: 0,
  };
}

export default function RainEffect() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const dropsRef = useRef<Drop[]>([]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      // Respawn drops
      const arr: Drop[] = [];
      for (let i = 0; i < SLIDERS; i++) arr.push(spawnDrop(canvas.width, canvas.height, true));
      for (let i = 0; i < TOTAL - SLIDERS; i++) arr.push(spawnDrop(canvas.width, canvas.height, false));
      dropsRef.current = arr;
    };
    resize();
    window.addEventListener("resize", resize);

    const loop = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const d of dropsRef.current) {
        if (d.sliding && !mq.matches) {
          d.phase += d.swayFreq;
          const sway = Math.sin(d.phase) * d.swayAmp;
          const prevY = d.y;
          d.y += d.speed;
          // Update trail
          if (d.y - d.trailY > d.ry * 3) d.trailY = prevY;
          d.trailOpacity = Math.max(0, d.trailOpacity - 0.002);
          if (d.y - d.trailY > d.ry * 1.2) d.trailOpacity = Math.min(0.5, d.trailOpacity + 0.04);
          d.x += sway * 0.02;
          if (d.y > canvas.height + d.ry) {
            d.y = -d.ry;
            d.x = Math.random() * canvas.width;
            d.trailY = d.y;
            d.trailOpacity = 0;
          }
        }
        drawTrail(ctx, d);
        drawDroplet(ctx, d);
      }
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
        position: "fixed", inset: 0, zIndex: 1,
        pointerEvents: "none",
      }}
    />
  );
}
