import React, { useEffect, useRef, useState } from "react";

const GradientBackground: React.FC = () => {
  const interactiveRef = useRef<HTMLDivElement>(null);
  const [curX, setCurX] = useState(0);
  const [curY, setCurY] = useState(0);
  const [tgX, setTgX] = useState(0);
  const [tgY, setTgY] = useState(0);
  const [isSafari, setIsSafari] = useState(false);

  useEffect(() => {
    setIsSafari(/^((?!chrome|android).)*safari/i.test(navigator.userAgent));
  }, []);

  // adoucit le suivi de la souris
  useEffect(() => {
    const moveInterval = setInterval(() => {
      setCurX((prev) => prev + (tgX - prev) / 20);
      setCurY((prev) => prev + (tgY - prev) / 20);

      if (interactiveRef.current) {
        interactiveRef.current.style.transform = `translate(${Math.round(
          curX
        )}px, ${Math.round(curY)}px)`;
      }
    }, 1000 / 60);

    return () => clearInterval(moveInterval);
  }, [curX, curY, tgX, tgY]);

  // calcule les coords par rapport au conteneur plein écran (event.currentTarget)
  const handleMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    const rect = (event.currentTarget as HTMLDivElement).getBoundingClientRect();
    setTgX(event.clientX - rect.left);
    setTgY(event.clientY - rect.top);
  };

  return (
    <>
      {/* FOND PLEIN ÉCRAN FIXE, DERRIÈRE TOUT */}
      <div
        className="fixed inset-0 -z-10 overflow-hidden bg-[linear-gradient(40deg,rgb(108,0,162),rgb(0,17,82))]"
        onMouseMove={handleMouseMove}
      >
        <svg className="hidden">
          <defs>
            <filter id="blurMe">
              <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur" />
              <feColorMatrix
                in="blur"
                mode="matrix"
                values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 18 -8"
                result="goo"
              />
              <feBlend in="SourceGraphic" in2="goo" />
            </filter>
          </defs>
        </svg>

        <div
          className={`gradients-container absolute inset-0 ${
            isSafari ? "blur-2xl" : "[filter:url(#blurMe)_blur(40px)]"
          }`}
        >
          <div className="absolute w-[80%] h-[80%] top-[calc(50%-40%)] left-[calc(50%-40%)] [background:radial-gradient(circle_at_center,_rgba(18,113,255,0.8)_0,_rgba(18,113,255,0)_50%)] [mix-blend-mode:hard-light] animate-first opacity-100" />
          <div className="absolute w-[80%] h-[80%] top-[calc(50%-40%)] left-[calc(50%-40%)] [background:radial-gradient(circle_at_center,_rgba(221,74,255,0.8)_0,_rgba(221,74,255,0)_50%)] [mix-blend-mode:hard-light] animate-second opacity-100" />
          <div className="absolute w-[80%] h-[80%] top-[calc(50%-40%)] left-[calc(50%-40%)] [background:radial-gradient(circle_at_center,_rgba(100,220,255,0.8)_0,_rgba(100,220,255,0)_50%)] [mix-blend-mode:hard-light] animate-third opacity-100" />
          <div className="absolute w-[80%] h-[80%] top-[calc(50%-40%)] left-[calc(50%-40%)] [background:radial-gradient(circle_at_center,_rgba(200,50,50,0.8)_0,_rgba(200,50,50,0)_50%)] [mix-blend-mode:hard-light] animate-fourth opacity-70" />
          <div className="absolute w-[80%] h-[80%] top-[calc(50%-40%)] left-[calc(50%-40%)] [background:radial-gradient(circle_at_center,_rgba(180,180,50,0.8)_0,_rgba(180,180,50,0)_50%)] [mix-blend-mode:hard-light] animate-fifth opacity-100" />

          {/* couche interactive déplacée par JS : plein écran, pas de -top/-left */}
          <div
            ref={interactiveRef}
            className="absolute inset-0 [background:radial-gradient(circle_at_center,_rgba(140,100,255,0.8)_0,_rgba(140,100,255,0)_50%)] [mix-blend-mode:hard-light] opacity-70"
          />
        </div>
      </div>
      {/* Aucun contenu ici : ce composant ne rend QUE le fond */}
    </>
  );
};

export default GradientBackground;
