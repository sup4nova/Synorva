import { useState, useEffect, useRef, type ChangeEvent } from 'react'

/* Types */
type AnalyzeResult = { valence: number; arousal: number }
type BuildResult = {
  valence: number
  arousal: number
  mix_url: string
  picks?: Record<string, { path: string; bpm: number | null; key: string | null; valence: number; arousal: number }>
}

/* Emotion states for demo cycling */
const EMOTIONS = [
  { label: 'Serene',      val:  0.55, ar: -0.45, hue: 'cool', tags: ['Ambient', 'Slow', 'Warm pads'] },
  { label: 'Euphoric',    val:  0.75, ar:  0.65, hue: 'warm', tags: ['Uplifting', 'Bright', 'Synthwave'] },
  { label: 'Melancholic', val: -0.55, ar: -0.35, hue: 'cool', tags: ['Piano', 'Minor', 'Reverb'] },
  { label: 'Tense',       val: -0.50, ar:  0.70, hue: 'warm', tags: ['Cinematic', 'Pulse', 'Dissonance'] },
  { label: 'Wistful',     val: -0.10, ar: -0.25, hue: 'cool', tags: ['Strings', 'Soft', 'Nostalgic'] },
]

function emotionFromAnalysis(a: AnalyzeResult) {
  const hue = a.arousal > 0 ? 'warm' : 'cool'
  let label = 'Wistful'
  if (a.valence > 0.2 && a.arousal > 0.2)  label = 'Euphoric'
  else if (a.valence > 0.2 && a.arousal <= 0.2) label = 'Serene'
  else if (a.valence <= 0.2 && a.arousal > 0.2) label = 'Tense'
  else if (a.valence <= 0.2 && a.arousal <= 0.2) label = 'Melancholic'
  return { label, val: a.valence, ar: a.arousal, hue, tags: [] as string[] }
}

function waveformBars(label: string, idx: number, count = 36) {
  return Array.from({ length: count }, (_, i) => {
    const t = i / count
    const seed = (label.charCodeAt(0) + i * 7) % 100
    const base = Math.sin(t * Math.PI * 3 + idx) * 0.4 + 0.5
    return Math.min(0.95, Math.max(0.15, base + (seed / 100) * 0.2))
  })
}

/* Spinner */
function Spinner() {
  return (
    <svg className="spin" width="13" height="13" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.5"
        strokeDasharray="22" strokeDashoffset="8" strokeLinecap="round" />
    </svg>
  )
}

/* Main component */
export default function HeroCard() {
  /* Upload state */
  const [file, setFile]           = useState<File | null>(null)
  const [preview, setPreview]     = useState<string | null>(null)
  const [dragOver, setDragOver]   = useState(false)
  const [busy, setBusy]           = useState(false)
  const [busyAction, setBusyAction] = useState<'analyze' | 'build' | null>(null)
  const [msg, setMsg]             = useState<string | null>(null)
  const [err, setErr]             = useState<string | null>(null)
  const [analysis, setAnalysis]   = useState<AnalyzeResult | null>(null)
  const [mixUrl, setMixUrl]       = useState<string | null>(null)
  const [picks, setPicks]         = useState<BuildResult['picks'] | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const API = import.meta.env.VITE_API_URL ?? ''

  /* VA demo cycling - stops when real data arrives */
  const [emotionIdx, setEmotionIdx] = useState(1)
  useEffect(() => {
    if (analysis) return
    const t = setInterval(() => setEmotionIdx(i => (i + 1) % EMOTIONS.length), 3200)
    return () => clearInterval(t)
  }, [analysis])

  const cur = analysis ? emotionFromAnalysis(analysis) : EMOTIONS[emotionIdx]
  const x = 50 + cur.val * 40
  const y = 50 - cur.ar * 40
  const bars = waveformBars(cur.label, emotionIdx)

  const pointColor = cur.hue === 'warm' ? 'var(--warm)' : 'var(--cool)'
  const pointGlow  = cur.hue === 'warm'
    ? '0 0 0 4px rgba(255,107,61,0.2), 0 0 36px rgba(255,107,61,0.55)'
    : '0 0 0 4px rgba(139,158,255,0.2), 0 0 36px rgba(139,158,255,0.55)'
  const barGrad = cur.hue === 'warm'
    ? 'linear-gradient(180deg, var(--warm), var(--warm-soft))'
    : 'linear-gradient(180deg, var(--cool), var(--cool-soft))'

  /* File handling */
  const handleFile = (f: File | null) => {
    setFile(f)
    setMsg(null); setErr(null); setAnalysis(null); setMixUrl(null); setPicks(null)
    if (preview) URL.revokeObjectURL(preview)
    setPreview(f ? URL.createObjectURL(f) : null)
  }
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])

  const onPick = (e: ChangeEvent<HTMLInputElement>) => handleFile(e.target.files?.[0] ?? null)
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false)
    const f = e.dataTransfer.files?.[0]
    if (f?.type.startsWith('image/')) handleFile(f)
  }

  /* API calls */
  const onAnalyze = async () => {
    if (!file) return
    setBusy(true); setBusyAction('analyze'); setErr(null); setAnalysis(null)
    try {
      const fd = new FormData(); fd.append('file', file)
      const res = await fetch(`${API}/api/analyze-image`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      setAnalysis(await res.json())
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : 'Analyse failed') }
    finally { setBusy(false); setBusyAction(null) }
  }

  const onBuild = async () => {
    if (!file) return
    setBusy(true); setBusyAction('build'); setErr(null); setMsg(null); setMixUrl(null); setPicks(null)
    try {
      const fd = new FormData(); fd.append('file', file)
      const res = await fetch(`${API}/api/build-track`, { method: 'POST', body: fd })
      if (!res.ok) throw new Error(await res.text())
      const json = (await res.json()) as BuildResult
      setAnalysis({ valence: json.valence, arousal: json.arousal })
      setMixUrl((API ? API.replace(/\/+$/, '') : '') + json.mix_url)
      setPicks(json.picks ?? null)
      setMsg('Track generated successfully')
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : 'Generation failed') }
    finally { setBusy(false); setBusyAction(null) }
  }

  const status = busy
    ? busyAction === 'analyze' ? 'analysing…' : 'generating…'
    : file ? 'ready' : 'idle · ready'

  return (
    <div id="try">
      {/* Upload card */}
      <div className="upload">
        <div className="upload-head">
          <div className="upload-title">
            <span className="upload-title-dot" />
            {file ? file.name.slice(0, 28) + (file.name.length > 28 ? '…' : '') : 'Drop an image'}
          </div>
          <div className="upload-status">{status}</div>
        </div>

        <div
          className={`upload-zone${dragOver ? ' drag' : ''}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
        >
          <input ref={inputRef} type="file" hidden accept="image/*" onChange={onPick} />

          {preview ? (
            <>
              <img src={preview} alt="preview" className="upload-preview" />
              <div className="upload-preview-name">{file?.name}</div>
            </>
          ) : (
            <>
              <div className="upload-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                  stroke="var(--paper-dim)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3v14M6 9l6-6 6 6M5 21h14" />
                </svg>
              </div>
              <div className="upload-headline">Drop a still or <span>browse files</span></div>
              <div className="upload-meta">PNG · JPG · WEBP — up to 10 MB</div>
            </>
          )}
        </div>

        <div className="upload-actions">
          <button className="btn btn-ghost" onClick={onAnalyze} disabled={!file || busy}>
            {busy && busyAction === 'analyze' ? <Spinner /> : null}
            Analyse
          </button>
          <button className="btn btn-primary" onClick={onBuild} disabled={!file || busy}>
            {busy && busyAction === 'build' ? <Spinner /> : null}
            Generate track →
          </button>
        </div>

        <div className="upload-foot">
          <div className="upload-foot-models">
            <span>engine</span>
            <span className="model-chip">synorva-v0.4</span>
          </div>
          <span>~6s · 320kbps</span>
        </div>
      </div>

      {/* Status messages */}
      {msg && (
        <div className="msg-row success">
          <span className="msg-dot success" />{msg}
        </div>
      )}
      {err && (
        <div className="msg-row error">
          <span className="msg-dot error" />{err}
        </div>
      )}

      {/* Analysis bars */}
      {analysis && (
        <div className="result-panel" style={{ marginBottom: 10 }}>
          <div className="result-label">Emotion analysis</div>
          {(['valence', 'arousal'] as const).map(k => {
            const v = analysis[k]
            const pct = Math.round(((v + 1) / 2) * 100)
            return (
              <div className="result-bar-row" key={k}>
                <div className="result-bar-header">
                  <span style={{ textTransform: 'capitalize' }}>{k}</span>
                  <span style={{ color: k === 'valence' ? 'var(--warm)' : 'var(--cool)' }}>
                    {v >= 0 ? '+' : ''}{v.toFixed(3)}
                  </span>
                </div>
                <div className="result-bar-track">
                  <div className={`result-bar-fill ${k}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Audio player */}
      {mixUrl && (
        <div className="result-panel">
          <div className="audio-player-wrap">
            <div className="audio-player-head">
              <div className="result-label" style={{ margin: 0 }}>Generated track</div>
              <a href={mixUrl} download className="audio-download">
                <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
                  <path d="M6 8V2M6 8L4 6M6 8L8 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M2 10h8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                </svg>
                Download
              </a>
            </div>
            <audio controls src={mixUrl} style={{ accentColor: 'var(--warm)' }} />
          </div>
          {picks && (
            <details style={{ marginTop: 10 }}>
              <summary className="samples-summary">
                Samples used ({Object.keys(picks).length})
              </summary>
              <ul className="sample-list">
                {Object.entries(picks).map(([typ, p]) => (
                  <li key={typ} className="sample-item">
                    <span className="sample-type">{typ}</span>
                    {p.path.split('/').pop()}
                    {p.key && <span className="sample-meta"> · {p.key}</span>}
                    {p.bpm && <span className="sample-meta"> · {p.bpm} BPM</span>}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {/* Valence-Arousal card */}
      <div className="va-card">
        <div className="va-head">
          <div>
            <div className="va-title">Emotion projection</div>
            <div className="va-current" style={{ color: cur.hue === 'warm' ? 'var(--warm-soft)' : 'var(--cool-soft)' }}>
              {cur.label}
            </div>
          </div>
          <div className="va-meta">
            <div>valence <b>{cur.val >= 0 ? '+' : ''}{cur.val.toFixed(2)}</b></div>
            <div>arousal <b>{cur.ar >= 0 ? '+' : ''}{cur.ar.toFixed(2)}</b></div>
          </div>
        </div>

        <div className="va-plot">
          <div className="va-axis-x" />
          <div className="va-axis-y" />
          <div className="va-label top">+ arousal</div>
          <div className="va-label bottom">− arousal</div>
          <div className="va-label left">− valence</div>
          <div className="va-label right">+ valence</div>
          <span className="va-quadrant" style={{ top: '13%', left: '13%' }}>tense</span>
          <span className="va-quadrant" style={{ top: '13%', right: '13%' }}>excited</span>
          <span className="va-quadrant" style={{ bottom: '13%', left: '13%' }}>sad</span>
          <span className="va-quadrant" style={{ bottom: '13%', right: '13%' }}>serene</span>
          <span
            className="va-point"
            style={{ left: `${x}%`, top: `${y}%`, background: pointColor, boxShadow: pointGlow }}
          />
        </div>

        <div className="va-waveform">
          {bars.map((h, i) => (
            <div key={i} className="va-wave-bar" style={{ height: `${h * 100}%`, background: barGrad }} />
          ))}
        </div>

        {(cur.tags.length > 0 || !analysis) && (
          <div className="va-tags">
            <span className="va-tag lead">{cur.label}</span>
            {cur.tags.map(t => <span key={t} className="va-tag">{t}</span>)}
          </div>
        )}
      </div>
    </div>
  )
}
