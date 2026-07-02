import { useState, useEffect } from 'react'

const base = import.meta.env.BASE_URL

const DEMOS = [
  {
    id: 'euphoric',
    img: `${base}demo/img-euphoric.jpg`,
    label: 'Euphoric',
    val: 0.72,
    ar: 0.61,
    hue: 'warm' as const,
    tags: ['Uplifting', 'Bright', 'Synthwave'],
    audio: `${base}demo/track-euphoric.wav`,
  },
  {
    id: 'dreamy',
    img: `${base}demo/img-dreamy.jpg`,
    label: 'Wistful',
    val: -0.12,
    ar: -0.28,
    hue: 'cool' as const,
    tags: ['Strings', 'Soft', 'Nostalgic'],
    audio: `${base}demo/track-dreamy.wav`,
  },
  {
    id: 'melancholic',
    img: `${base}demo/img-melancholic.jpg`,
    label: 'Melancholic',
    val: -0.52,
    ar: -0.38,
    hue: 'cool' as const,
    tags: ['Piano', 'Minor', 'Reverb'],
    audio: `${base}demo/track-melancholic.wav`,
  },
]

const EMOTIONS = [
  { label: 'Serene',      val:  0.55, ar: -0.45, hue: 'cool' as const, tags: ['Ambient', 'Slow', 'Warm pads'] },
  { label: 'Euphoric',    val:  0.75, ar:  0.65, hue: 'warm' as const, tags: ['Uplifting', 'Bright', 'Synthwave'] },
  { label: 'Melancholic', val: -0.55, ar: -0.35, hue: 'cool' as const, tags: ['Piano', 'Minor', 'Reverb'] },
  { label: 'Tense',       val: -0.50, ar:  0.70, hue: 'warm' as const, tags: ['Cinematic', 'Pulse', 'Dissonance'] },
  { label: 'Wistful',     val: -0.10, ar: -0.25, hue: 'cool' as const, tags: ['Strings', 'Soft', 'Nostalgic'] },
]

function waveformBars(label: string, idx: number, count = 36) {
  return Array.from({ length: count }, (_, i) => {
    const t = i / count
    const seed = (label.charCodeAt(0) + i * 7) % 100
    const base = Math.sin(t * Math.PI * 3 + idx) * 0.4 + 0.5
    return Math.min(0.95, Math.max(0.15, base + (seed / 100) * 0.2))
  })
}

export default function HeroCard() {
  const [selected, setSelected] = useState<typeof DEMOS[0] | null>(null)
  const [emotionIdx, setEmotionIdx] = useState(1)

  useEffect(() => {
    if (selected) return
    const t = setInterval(() => setEmotionIdx(i => (i + 1) % EMOTIONS.length), 3200)
    return () => clearInterval(t)
  }, [selected])

  const cur = selected ?? EMOTIONS[emotionIdx]
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

  return (
    <div id="try">
      {/* Demo image picker */}
      <div className="upload">
        <div className="upload-head">
          <div className="upload-title">
            <span className="upload-title-dot" />
            {selected ? selected.label : 'Choose an image'}
          </div>
          <div className="upload-status">{selected ? 'ready' : 'demo'}</div>
        </div>

        <div className="demo-picks">
          {DEMOS.map(d => (
            <button
              key={d.id}
              className={`demo-pick${selected?.id === d.id ? ' active' : ''}`}
              onClick={() => setSelected(selected?.id === d.id ? null : d)}
            >
              <img src={d.img} alt={d.label} />
              <span className="demo-pick-label">{d.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Analysis bars */}
      {selected && (
        <div className="result-panel" style={{ marginBottom: 10 }}>
          <div className="result-label">Emotion analysis</div>
          {(['val', 'ar'] as const).map((k, i) => {
            const v = selected[k]
            const pct = Math.round(((v + 1) / 2) * 100)
            const name = k === 'val' ? 'valence' : 'arousal'
            return (
              <div className="result-bar-row" key={k}>
                <div className="result-bar-header">
                  <span style={{ textTransform: 'capitalize' }}>{name}</span>
                  <span style={{ color: i === 0 ? 'var(--warm)' : 'var(--cool)' }}>
                    {v >= 0 ? '+' : ''}{v.toFixed(3)}
                  </span>
                </div>
                <div className="result-bar-track">
                  <div className={`result-bar-fill ${name}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Audio player */}
      {selected && (
        <div className="result-panel">
          <div className="audio-player-wrap">
            <div className="audio-player-head">
              <div className="result-label" style={{ margin: 0 }}>Generated track</div>
              <a href={selected.audio} download className="audio-download">
                <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
                  <path d="M6 8V2M6 8L4 6M6 8L8 6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M2 10h8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                </svg>
                Download
              </a>
            </div>
            <audio key={selected.id} controls src={selected.audio} style={{ accentColor: 'var(--warm)' }} />
          </div>
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

        {cur.tags.length > 0 && (
          <div className="va-tags">
            <span className="va-tag lead">{cur.label}</span>
            {cur.tags.map(t => <span key={t} className="va-tag">{t}</span>)}
          </div>
        )}
      </div>
    </div>
  )
}
