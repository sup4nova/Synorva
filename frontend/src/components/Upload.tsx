import { useState, useEffect, useRef, type ChangeEvent } from "react";
import styles from "./Upload.module.css";

type AnalyzeResult = { valence: number; arousal: number };
type BuildResult = {
  valence: number;
  arousal: number;
  mix_url: string;
  picks?: Record<string, { path: string; bpm: number | null; key: string | null; valence: number; arousal: number }>;
};

const DEMO_TRACKS = [
  { name: "dreamy",      valence:  0.60, arousal: -0.30, url: "/demo/track-dreamy.wav" },
  { name: "euphoric",    valence:  0.85, arousal:  0.70, url: "/demo/track-euphoric.wav" },
  { name: "melancholic", valence: -0.50, arousal: -0.20, url: "/demo/track-melancholic.wav" },
];

const Spinner = () => (
  <svg className="animate-spin" width="14" height="14" viewBox="0 0 14 14" fill="none">
    <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="22" strokeDashoffset="8" strokeLinecap="round"/>
  </svg>
);

const ValenceBar = ({ label, value }: { label: string; value: number }) => {
  const pct = Math.round(((value + 1) / 2) * 100);
  return (
    <div className={styles.valenceBar}>
      <div className={styles.barHeader}>
        <span className={styles.barLabel}>{label}</span>
        <span className={`${styles.barValue} ${label.toLowerCase()}`}>{value.toFixed(3)}</span>
      </div>
      <div className={styles.barTrack}>
        <div
          className={`${styles.barFill} ${label.toLowerCase()}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [busyAction, setBusyAction] = useState<"analyze" | "build" | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null);
  const [mixUrl, setMixUrl] = useState<string | null>(null);
  const [picks, setPicks] = useState<BuildResult["picks"] | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const API = import.meta.env.VITE_API_URL ?? "";

  const handleFile = (f: File | null) => {
    setFile(f);
    setMsg(null); setErr(null); setAnalysis(null); setMixUrl(null); setPicks(null);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(f ? URL.createObjectURL(f) : null);
  };

  const onPick = (e: ChangeEvent<HTMLInputElement>) => handleFile(e.target.files?.[0] ?? null);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f && f.type.startsWith("image/")) handleFile(f);
  };

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const onUpload = async () => {
    if (!file) return;
    setLoading(true); setMsg(null); setErr(null);
    try {
      const fd = new FormData(); fd.append("file", file);
      const res = await fetch(`${API}/api/upload-image`, { method: "POST", body: fd });
      const text = await res.text();
      if (!res.ok) throw new Error(text || `HTTP ${res.status}`);
      const json = JSON.parse(text);
      setMsg(`Image saved - ${json.saved_as ?? "OK"}`);
    } catch (e: any) { setErr(e?.message ?? "Upload failed"); }
    finally { setLoading(false); }
  };

  const onAnalyze = async () => {
    if (!file) return;
    setBusy(true); setBusyAction("analyze"); setErr(null); setAnalysis(null);
    try {
      const fd = new FormData(); fd.append("file", file);
      const res = await fetch(`${API}/api/analyze-image`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(await res.text());
      setAnalysis(await res.json());
    } catch (e: any) { setErr(e?.message ?? "Analysis failed"); }
    finally { setBusy(false); setBusyAction(null); }
  };

  const onBuild = async () => {
    if (!file) return;
    setBusy(true); setBusyAction("build"); setErr(null); setMsg(null); setMixUrl(null); setPicks(null);

    if (!API) {
      await new Promise(r => setTimeout(r, 1200));
      const demo = DEMO_TRACKS[Math.floor(Math.random() * DEMO_TRACKS.length)];
      setAnalysis({ valence: demo.valence, arousal: demo.arousal });
      setMixUrl(demo.url);
      setMsg("Track generated (demo mode)");
      setBusy(false); setBusyAction(null);
      return;
    }

    try {
      const fd = new FormData(); fd.append("file", file);
      const res = await fetch(`${API}/api/build-track`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(await res.text());
      const json = (await res.json()) as BuildResult;
      setAnalysis({ valence: json.valence, arousal: json.arousal });
      setMixUrl(API.replace(/\/+$/, "") + json.mix_url);
      setPicks(json.picks ?? null);
      setMsg("Track generated");
    } catch (e: any) { setErr(e?.message ?? "Generation failed"); }
    finally { setBusy(false); setBusyAction(null); }
  };

  return (
    <div className={styles.uploadContainer}>

      {/* Drop zone */}
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`${styles.dropZone} ${dragOver ? styles.dragOver : ''} ${preview ? styles.hasPreview : ''}`}
      >
        <input ref={inputRef} type="file" accept="image/*" onChange={onPick} className={styles.hiddenInput} />

        {preview ? (
          <div className={styles.previewContainer}>
            <img src={preview} alt="preview" className={styles.previewImage} />
            <div className={styles.previewOverlay} />
            <div className={styles.previewInfo}>
              <div className={styles.previewDot} />
              <span className={styles.previewFilename}>{file?.name}</span>
            </div>
          </div>
        ) : (
          <div className={styles.noPreview}>
            <div className={styles.uploadIcon}>
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M9 12V4M9 4L6 7M9 4L12 7" stroke="hsl(22,95%,65%)" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M3 14h12" stroke="hsla(30,15%,55%,0.5)" strokeWidth="1.2" strokeLinecap="round"/>
              </svg>
            </div>
            <div className={styles.uploadText}>
              <p className={styles.uploadMainText}>Drop an image here</p>
              <p className={styles.uploadSubText}>PNG, JPG, WEBP - up to 10 MB</p>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className={styles.actionsGrid}>
        {[
          {
            label: "Upload",
            loadingLabel: "Uploading...",
            isLoading: loading,
            onClick: onUpload,
            disabled: !file || loading,
            color: "hsl(38, 90%, 65%)",
            colorBg: "hsla(38, 90%, 58%, 0.08)",
            colorBorder: "hsla(38, 90%, 58%, 0.22)",
          },
          {
            label: "Analyze",
            loadingLabel: "Analyzing...",
            isLoading: busy && busyAction === "analyze",
            onClick: onAnalyze,
            disabled: !file || busy,
            color: "hsl(22, 95%, 65%)",
            colorBg: "hsla(22, 95%, 58%, 0.07)",
            colorBorder: "hsla(22, 95%, 58%, 0.20)",
          },
          {
            label: "Generate",
            loadingLabel: "Generating...",
            isLoading: busy && busyAction === "build",
            onClick: onBuild,
            disabled: !file || busy,
            color: "hsl(8, 85%, 68%)",
            colorBg: "hsla(8, 85%, 60%, 0.07)",
            colorBorder: "hsla(8, 85%, 60%, 0.20)",
          },
        ].map((btn) => (
          <button
            key={btn.label}
            type="button"
            onClick={btn.onClick}
            disabled={btn.disabled}
            className={`${styles.actionButton} ${btn.disabled ? styles.disabled : ''}`}
            style={{
              background: btn.disabled ? undefined : btn.colorBg,
              border: `1px solid ${btn.disabled ? undefined : btn.colorBorder}`,
              color: btn.disabled ? undefined : btn.color,
            }}
          >
            {btn.isLoading && <Spinner />}
            {btn.isLoading ? btn.loadingLabel : btn.label}
          </button>
        ))}
      </div>

      {/* Analysis result */}
      {analysis && (
        <div className={styles.analysisCard}>
          <p className={styles.labelStyle}>Emotion analysis</p>
          <ValenceBar label="Valence" value={analysis.valence} />
          <ValenceBar label="Arousal" value={analysis.arousal} />
        </div>
      )}

      {/* Audio player */}
      {mixUrl && (
        <div className={styles.audioCard}>
          <div className={styles.audioHeader}>
            <p className={styles.labelStyle}>Generated track</p>
            <a href={mixUrl} download className={styles.downloadLink}>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M6 8V2M6 8L4 6M6 8L8 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 10h8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
              </svg>
              Download
            </a>
          </div>
          <audio
            controls
            src={mixUrl}
            className={styles.audioPlayer}
            style={{ accentColor: "hsl(22,95%,60%)" }}
          />
          {picks && (
            <details>
              <summary className={styles.detailsSummary}>
                <svg className={styles.detailsArrow} width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path d="M3 2l4 3-4 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                Samples used ({Object.keys(picks).length})
              </summary>
              <ul className={styles.sampleList}>
                {Object.entries(picks).map(([typ, p]) => (
                  <li key={typ} className={styles.sampleItem}>
                    <span className={styles.sampleType}>{typ}</span>
                    {" - "}{p.path.split("/").pop()}
                    {p.key && <span className={styles.sampleMeta}> · {p.key}</span>}
                    {p.bpm && <span className={styles.sampleMeta}> · {p.bpm} BPM</span>}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {/* Messages */}
      {msg && (
        <div className={`${styles.message} ${styles.success}`}>
          <div className={`${styles.messageDot} ${styles.success}`} />
          {msg}
        </div>
      )}
      {err && (
        <div className={`${styles.message} ${styles.error}`}>
          <div className={`${styles.messageDot} ${styles.error}`} />
          {err}
        </div>
      )}
    </div>
  );
}
