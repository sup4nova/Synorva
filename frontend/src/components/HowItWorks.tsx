const steps = [
  {
    num: '01',
    label: 'Read',
    title: <>Read the <span className="it">image.</span></>,
    desc: 'A vision encoder parses composition, palette, contrast and subject a extracting the perceptual signals a human would feel before they could name them.',
    art: (
      <div className="art-image" />
    ),
  },
  {
    num: '02',
    label: 'Project',
    title: <>Map the <span className="it">emotion.</span></>,
    desc: 'Maps the image embedding to a valence-arousal space and four perceptual dimensions-tension, warmth, density, and motion-based on calibrations from annotated film scores',
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
    desc: 'The coordinates are used to guide an audio diffusion model conditioned on genre presets, generating a coherent 30-second loop that seamlessly repeats and is ready to use in your projects',
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
  { val: <>8<span className="it">d</span></>,    label: 'emotion axes' },
  { val: <>~6<span className="it">s</span></>,   label: 'render time' },
  { val: <>320<span className="it">kbps</span></>, label: 'audio quality' },
  { val: <>12<span className="it">+</span></>,   label: 'genre presets' },
]

export default function HowItWorks() {
  return (
    <section className="section" id="how">
      <div className="shell">
        <div className="caps" style={{ marginBottom: 48 }}>
          {caps.map(c => (
            <div className="cap" key={c.label}>
              <div className="cap-val">{c.val}</div>
              <div className="cap-label">{c.label}</div>
            </div>
          ))}
        </div>

        <div className="section-head reveal">
          <div className="section-eyebrow">How it works</div>
          <h2 className="section-title">
            A multimodal pipeline that doesn't <span className="it">just caption your image</span>
          </h2>
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
      </div>
    </section>
  )
}
