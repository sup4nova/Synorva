import React, { useEffect, useRef, useState } from "react";

const GradientBackground: React.FC = () => {
  const interactiveRef = useRef<HTMLDivElement>(null);
  const [curX, setCurX] = useState(0);
  const [curY, setCurY] = useState(0);
  const [tgX, setTgX] = useState(0);
  const [tgY, setTgY] = useState(0);

  useEffect(() => {
    const moveInterval = setInterval(() => {
      setCurX((prev) => prev + (tgX - prev) / 25);
      setCurY((prev) => prev + (tgY - prev) / 25);
      if (interactiveRef.current) {
        interactiveRef.current.style.transform = `translate(${Math.round(curX)}px, ${Math.round(curY)}px)`;
      }
    }, 1000 / 60);
    return () => clearInterval(moveInterval);
  }, [curX, curY, tgX, tgY]);

  const handleMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = (event.currentTarget as HTMLDivElement).getBoundingClientRect();
    setTgX(event.clientX - rect.left);
    setTgY(event.clientY - rect.top);
  };

  return (
    <div
      className="fixed inset-0 -z-10 overflow-hidden"
      style={{ background: "#0c0a07" }}
      onMouseMove={handleMouseMove}
    >
      {/* Subtle warm grid */}
      <div
        className="absolute inset-0 opacity-[0.025]"
        style={{
          backgroundImage:
            "linear-gradient(hsla(30,40%,60%,1) 1px, transparent 1px), linear-gradient(90deg, hsla(30,40%,60%,1) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
        }}
      />

      {/* Noise texture */}
      <div
        className="absolute inset-0 opacity-[0.035]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
          backgroundRepeat: "repeat",
          backgroundSize: "200px",
        }}
      />

      <svg className="hidden">
        <defs>
          <filter id="goo">
            <feGaussianBlur in="SourceGraphic" stdDeviation="50" result="blur" />
            <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 22 -10" result="goo" />
            <feBlend in="SourceGraphic" in2="goo" />
          </filter>
        </defs>
      </svg>

      <div className="absolute inset-0" style={{ filter: "url(#goo) blur(60px)" }}>
        {/* Orange-burnt blob */}
        <div
          className="absolute rounded-full animate-blob-1"
          style={{
            width: "60vw", height: "60vw",
            top: "5%", left: "0%",
            background: "radial-gradient(circle, hsla(22, 95%, 55%, 0.18) 0%, transparent 70%)",
          }}
        />
        {/* Amber blob */}
        <div
          className="absolute rounded-full animate-blob-2"
          style={{
            width: "50vw", height: "50vw",
            top: "25%", right: "0%",
            background: "radial-gradient(circle, hsla(38, 95%, 58%, 0.13) 0%, transparent 70%)",
          }}
        />
        {/* Coral accent */}
        <div
          className="absolute rounded-full animate-blob-3"
          style={{
            width: "40vw", height: "40vw",
            bottom: "5%", left: "30%",
            background: "radial-gradient(circle, hsla(8, 85%, 55%, 0.09) 0%, transparent 70%)",
          }}
        />
        {/* Interactive mouse layer */}
        <div
          ref={interactiveRef}
          className="absolute"
          style={{
            width: "60vw", height: "60vw",
            top: "-30vw", left: "-30vw",
            background: "radial-gradient(circle, hsla(30, 90%, 65%, 0.07) 0%, transparent 60%)",
          }}
        />
      </div>
    </div>
  );
};

export default GradientBackground;