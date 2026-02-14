"use client";

import { useEffect, useRef } from "react";

type VortexProps = {
  children?: React.ReactNode;
  className?: string;
  backgroundColor?: string;
  rangeY?: number;
  particleCount?: number;
  baseHue?: number;
  colorPalette?: string[];
};

type Particle = {
  angle: number;
  radius: number;
  speed: number;
  size: number;
  color: string;
  alpha: number;
};

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

export function Vortex({
  children,
  className,
  backgroundColor = "#0c1317",
  rangeY = 700,
  particleCount = 420,
  baseHue = 206,
  colorPalette,
}: VortexProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const parentRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const parent = parentRef.current;
    if (!canvas || !parent) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let dpr = 1;
    let animationFrame = 0;
    let centerX = 0;
    let centerY = 0;
    let maxRadius = 0;
    const particles: Particle[] = [];

    const defaultPalette = [baseHue - 8, baseHue + 10, 44, 48];

    const pickHue = () => {
      if (colorPalette && colorPalette.length > 0) {
        return colorPalette[Math.floor(Math.random() * colorPalette.length)];
      }
      return `hsl(${defaultPalette[Math.floor(Math.random() * defaultPalette.length)]} 92% 62%)`;
    };

    const createParticle = (): Particle => {
      const spawnTightness = 0.1 + Math.random() * 0.3;
      return {
        angle: Math.random() * Math.PI * 2,
        radius: Math.random() * maxRadius * spawnTightness,
        speed: 0.003 + Math.random() * 0.012,
        size: 0.8 + Math.random() * 2.4,
        color: pickHue(),
        alpha: 0.22 + Math.random() * 0.58,
      };
    };

    const resetParticle = (particle: Particle) => {
      const next = createParticle();
      particle.angle = next.angle;
      particle.radius = next.radius;
      particle.speed = next.speed;
      particle.size = next.size;
      particle.color = next.color;
      particle.alpha = next.alpha;
    };

    const setupCanvas = () => {
      const rect = parent.getBoundingClientRect();
      width = Math.max(1, Math.floor(rect.width));
      height = Math.max(1, Math.floor(rect.height));
      dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      centerX = width / 2;
      centerY = height / 2;
      maxRadius = Math.min(width * 0.65, rangeY);

      particles.length = 0;
      for (let i = 0; i < particleCount; i += 1) {
        particles.push(createParticle());
      }
    };

    const render = () => {
      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, width, height);

      for (let i = 0; i < particles.length; i += 1) {
        const particle = particles[i];
        particle.angle += particle.speed;
        particle.radius += 0.1 + particle.speed * 24;

        if (particle.radius > maxRadius) {
          resetParticle(particle);
        }

        const t = clamp(particle.radius / maxRadius, 0, 1);
        const x = centerX + Math.cos(particle.angle) * particle.radius;
        const y =
          centerY +
          Math.sin(particle.angle * 1.32) * particle.radius * 0.42 +
          Math.cos(particle.angle * 2.2) * 18;

        const size = Math.max(0.4, particle.size * (1 - t * 0.6));
        const alpha = particle.alpha * (1 - t);

        ctx.save();
        ctx.globalAlpha = alpha;
        ctx.beginPath();
        ctx.fillStyle = particle.color;
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      animationFrame = window.requestAnimationFrame(render);
    };

    setupCanvas();
    render();

    const resizeObserver = new ResizeObserver(() => setupCanvas());
    resizeObserver.observe(parent);

    return () => {
      window.cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
    };
  }, [backgroundColor, baseHue, colorPalette, particleCount, rangeY]);

  return (
    <div ref={parentRef} className={`relative overflow-hidden ${className ?? ""}`}>
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-hidden="true" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(62,147,193,0.14),transparent_40%),radial-gradient(circle_at_80%_80%,rgba(245,163,10,0.12),transparent_38%)]" />
      <div className="relative z-10 h-full w-full">{children}</div>
    </div>
  );
}
