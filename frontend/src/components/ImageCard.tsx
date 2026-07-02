import type { ReactNode } from "react";

type Props = {
  title?: string;
  subtitle?: string;
  children: ReactNode;
};

const ImageCard = ({
  title = "Sound analysis",
  subtitle = "Drop an image to generate a track matched to its emotion",
  children,
}: Props) => (
  <div
    className="relative overflow-hidden"
    style={{
      width: "40rem",
      height: "25rem",
      borderRadius: "20px",
      background: "rgba(12, 10, 7, 0.82)",
      border: "1px solid hsla(30, 30%, 100%, 0.07)",
      backdropFilter: "blur(28px)",
      boxShadow:
        "0 0 0 1px hsla(22, 60%, 100%, 0.03), 0 32px 64px -12px hsla(20,40%,4%,0.7), 0 0 80px -20px hsla(22,95%,50%,0.08)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
    }}
  >
    {/* Top accent line */}
    <div
      className="absolute top-0 left-0 right-0 h-px"
      style={{
        background:
          "linear-gradient(90deg, transparent, hsla(22,95%,60%,0.7), hsla(38,95%,60%,0.5), transparent)",
      }}
    />

    {/* Subtle inner glow at top */}
    <div
      className="absolute top-0 left-0 right-0 h-32 pointer-events-none"
      style={{
        background: "radial-gradient(ellipse at 50% -10%, hsla(22,95%,55%,0.06) 0%, transparent 70%)",
      }}
    />

    <div className="px-8 pt-8 pb-4">
      <div className="flex items-center gap-2 mb-1 justify-center">
        {/* Logo mark */}
        <div
          className="w-6 h-6 rounded-md flex items-center justify-center"
          style={{
            background: "linear-gradient(135deg, hsla(22,95%,55%,0.25), hsla(38,95%,58%,0.25))",
            border: "1px solid hsla(22,95%,60%,0.3)",
          }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 1L11 6L6 11L1 6L6 1Z" stroke="hsl(30,95%,65%)" strokeWidth="1.2" fill="none"/>
            <circle cx="6" cy="6" r="1.5" fill="hsl(30,95%,65%)"/>
          </svg>
        </div>
        <h2
          className="text-sm font-semibold tracking-widest uppercase"
          style={{
            color: "hsl(30, 90%, 68%)",
            fontFamily: "'DM Mono', 'Fira Code', monospace",
            letterSpacing: "0.15em",
          }}
        >
          {title}
        </h2>
      </div>
      {subtitle && (
        <p
          className="text-xs mt-2 leading-relaxed"
          style={{
            color: "hsla(30, 15%, 65%, 0.75)",
            fontFamily: "'DM Sans', sans-serif",
            marginBottom: "1.5rem",
          }}
        >
          {subtitle}
        </p>
      )}
    </div>

    <div className="px-8 pb-8">{children}</div>
  </div>
);

export default ImageCard;