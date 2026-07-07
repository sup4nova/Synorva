const steps = [
  {
    num: '01',
    label: 'Ingest',
    title: <>Read the <span className="it">image.</span></>,
    desc: 'Computer vision extracts brightness, warmth, contrast, edges, sharpness and other visual signals — the raw cues a human would feel before they could name them.',
    art: (
      <div className="art-image" />
    ),
  },
  {
    num: '02',
    label: 'Project',
    title: <>Map the <span className="it">emotion.</span></>,
    desc: 'Those features are weighted into a valence-arousal score and classified into one of 8 emotion labels, from aggressive to dreamy.',
    art: (
      <div className="art-spectrum">
        {(['VAL', 'ARO', 'TENS', 'WARM'] as const).map((l, i) => (
          <div className="art-spec-row" key={l}>
            <span className="art-spec-label">{l}</span>
            <div className="art-spec-bar">
              <div className={`art-spec-fill ${['a','b','c','d'][i]}`} />
            </div>
          </div>
        ))}
      </div>
    ),
  },
  {
    num: '03',
    label: 'Render',
    title: <>Compose the <span className="it">track.</span></>,
    desc: 'The valence-arousal score picks the closest-matching kick, bass, melody and riser from a curated sample library, and arranges them into a bar-aligned mix.',
    art: (
      <div className="art-wave">
        {Array.from({ length: 24 }, (_, i) => (
          <div key={i} className="art-wave-bar" style={{ animationDelay: `${i * 60}ms` }} />
        ))}
      </div>
    ),
  },
]

const caps = [
  { val: <>8</>,                                label: 'emotion labels' },
  { val: <>~6<span className="it">s</span></>,  label: 'render time' },
  { val: <>44.1<span className="it">kHz</span></>, label: 'WAV output' },
  { val: <>11</>,                               label: 'visual features' },
]

export default function HowItWorks() {
  return (
    <section className="section" id="how">
      <div className="shell">
        <div className="section-head reveal">
          <div className="section-eyebrow">How it works</div>
          <h2 className="section-title">
            Three passes. From a single frame<br />
            to <span className="it">a finished track.</span>
          </h2>
          <p className="section-sub">
            A multimodal pipeline that doesn't just caption your image — it locates
            it in emotional space and renders music that lives there.
          </p>
        </div>

        <div className="steps">
          {steps.map(s => (
            <div className="step reveal" key={s.num}>
              <div className="step-num"><b>{s.num}</b>{s.label}</div>
              <div className="step-art">{s.art}</div>
              <h3 className="step-title">{s.title}</h3>
              <p className="step-desc">{s.desc}</p>
            </div>
          ))}
        </div>

        <div className="caps">
          {caps.map(c => (
            <div className="cap" key={c.label}>
              <div className="cap-val">{c.val}</div>
              <div className="cap-label">{c.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
