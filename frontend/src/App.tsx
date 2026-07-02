import { useEffect } from 'react'
import Navbar from './components/Navbar'
import HeroCard from './components/HeroCard'
import HowItWorks from './components/HowItWorks'
import Footer from './components/Footer'

// Adds .in to .reveal elements when they enter the viewport
function useScrollReveal() {
  useEffect(() => {
    const io = new IntersectionObserver(
      entries => entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target) } }),
      { threshold: 0.12 }
    )
    document.querySelectorAll('.reveal').forEach(el => io.observe(el))
    return () => io.disconnect()
  }, [])
}

export default function App() {
  useScrollReveal()

  return (
    <>
      <Navbar />

      <main>
        {/* Hero */}
        <section className="hero">
          <div className="hero-bg">
            <div className="hero-glow-a" />
            <div className="hero-glow-b" />
          </div>

          <div className="shell">
            <div className="hero-pill">
              <span className="hero-pill-dot">v0.4 beta</span>
              <span>Multimodal · Image → Emotion → Music</span>
            </div>

            <div className="hero-grid">
              {/* Left: title + subtitle + video */}
              <div>
                <h1 className="hero-title">
                  See sound.<br />
                  Hear images.<br />
                  <span className="grad">Compose feeling.</span>
                </h1>
                <p className="hero-sub">
                  Synorva reads the emotion in image and synthesizes a coherent
                  audio track from it, mapped through a <b>valence-arousal model</b> tuned
                  for cinematic, ambient and electronic genres.
                </p>
                <div className="hero-video">
                  <div className="hero-video-frame">
                    <div className="hero-video-glow" />
                    <div className="hero-video-soon">
                      <span className="hero-video-badge">Coming soon</span>
                      <div className="hero-video-play">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                          <path d="m6 4 14 8-14 8V4Z" />
                        </svg>
                      </div>
                      <div className="hero-video-text">
                        <strong>Product demo in production</strong>
                        <span>A full walkthrough of the live engine is being recorded</span>
                      </div>
                    </div>
                  </div>
                  <div className="hero-video-cap">
                  </div>
                </div>
              </div>

              {/* Right: upload + VA card */}
              <HeroCard />
            </div>
          </div>
        </section>

        <HowItWorks />
      </main>

      <Footer />
    </>
  )
}
