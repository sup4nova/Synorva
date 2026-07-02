import { useEffect } from 'react'
import Navbar from './components/Navbar'
import HeroCard from './components/HeroCard'
import HowItWorks from './components/HowItWorks'
import Footer from './components/Footer'

/* Scroll-reveal: add .in to .reveal elements when they enter the viewport */
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
            <div className="hero-grid">
              {/* Left: title + subtitle */}
              <div>
                <h1 className="hero-title">
                  See sound.<br />
                  Hear images.<br />
                  <span className="grad">Compose feeling.</span>
                </h1>
                <p className="hero-sub">
                  Synorva reads the emotion in a still image and synthesizes a coherent
                  audio track from it mapped through <b>valence-arousal model</b>.
                </p>
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
