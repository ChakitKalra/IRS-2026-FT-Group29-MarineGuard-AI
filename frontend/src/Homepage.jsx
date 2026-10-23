import React from 'react';

export default function Homepage({ onNavigate, liveMetrics = {} }) {
  const pillars = [
    {
      icon: '🛰️',
      title: 'Detect',
      subtitle: 'Identify Coastal Litter',
      desc: 'Combines satellite and aerial drone imaging to locate floating plastic slicks and debris accumulation across Singapore’s waterways.',
    },
    {
      icon: '↗',
      title: 'Predict',
      subtitle: 'Forecast Debris Drift',
      desc: 'Simulates where marine debris travels up to 48 hours in advance using real-time tidal currents and meteorological wind patterns.',
    },
    {
      icon: '🚨',
      title: 'Act',
      subtitle: 'Dispatch Cleanup Teams',
      desc: 'Generates prioritized cleanup orders, incident action plans, and vessel interception routes before litter strands on beaches.',
    },
  ];

  return (
    <div className="home-container">
      {/* Background Ambient Lighting Blobs */}
      <div className="ambient-blob primary" style={{ top: '-150px', left: '20%' }} />
      <div className="ambient-blob secondary" style={{ top: '400px', right: '10%' }} />

      {/* Top Floating Header */}
      <header className="home-header">
        <div className="home-header-inner">
          <div className="home-brand" onClick={() => onNavigate('home')} role="button" tabIndex={0} title="MarineGuard AI">
            <div className="brand-icon">≈</div>
            <div className="brand-block">
              <div className="brand-text">
                <span>MarineGuard</span>
                <span className="tag">AI</span>
              </div>
              <span className="brand-sub">Singapore Coastal Intelligence</span>
            </div>
          </div>

          <nav className="home-nav-links">
            <button className="home-nav-btn active" onClick={() => onNavigate('home')}>
              <span>🏠</span> Overview
            </button>
            <button className="home-nav-btn" onClick={() => onNavigate('studio')}>
              <span>🛰️</span> Live Studio
            </button>
            <button className="home-nav-btn" onClick={() => onNavigate('docs')}>
              <span>📖</span> Docs & Guide
            </button>
          </nav>

          <div className="home-header-actions">
            <div className="live-status-pill">
              <span className="live-dot" />
              <span>Telemetry Online (19ms)</span>
            </div>
            <button className="btn-primary" onClick={() => onNavigate('studio')}>
              <span>Launch Studio</span>
              <span className="arrow-icon">→</span>
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="home-hero">
        <div className="hero-pill-badge">
          <span className="hero-pill-dot" />
          <span>SINGAPORE COASTAL INTELLIGENCE PLATFORM</span>
        </div>

        <h1 className="hero-headline">
          Intelligent Marine Litter Tracking &amp; <br />
          <span className="hero-gradient-text">Predictive Coastal Defense</span>
        </h1>

        <p className="hero-subtext">
          MarineGuard AI monitors Singapore waters in real time—detecting floating plastic debris, predicting its movement with ocean currents, and optimizing cleanup missions before shorelines are impacted.
        </p>

        <div className="hero-cta-group">
          <button className="btn-primary hero-btn" onClick={() => onNavigate('studio')}>
            <span>🛰️ Launch Live Studio</span>
            <span className="arrow-icon">→</span>
          </button>
          <button className="btn-secondary hero-btn" onClick={() => onNavigate('docs')}>
            <span>📖 Read Documentation &amp; Guide</span>
          </button>
        </div>

        {/* Live Quick Telemetry Strip */}
        <div className="hero-stats-grid">
          <div className="hero-stat-card">
            <span className="stat-label">System Status</span>
            <span className="stat-value">Active</span>
            <span className="stat-note">Live Telemetry Synchronized</span>
          </div>
          <div className="hero-stat-card">
            <span className="stat-label">Verified Hotspots</span>
            <span className="stat-value">4 Slicks</span>
            <span className="stat-note">Across Singapore Waters</span>
          </div>
          <div className="hero-stat-card">
            <span className="stat-label">Surface Current</span>
            <span className="stat-value">{liveMetrics.currentSpeed || '1.04 kts'}</span>
            <span className="stat-note">{liveMetrics.currentHeading || '248°'} Ebb Flow</span>
          </div>
          <div className="hero-stat-card">
            <span className="stat-label">Cleanup Efficiency</span>
            <span className="stat-value">+130%</span>
            <span className="stat-note">Over Standard Schedules</span>
          </div>
        </div>
      </section>

      {/* 3 Core Pillars Section */}
      <section className="home-section" style={{ paddingBottom: '60px' }}>
        <div className="section-header-block" style={{ marginBottom: '36px' }}>
          <span className="section-badge">HOW IT HELPS</span>
          <h2 className="section-title">From Observation to Action</h2>
          <p className="section-desc">
            A proactive coastal protection system designed for maritime operators, port authorities, and environmental response teams.
          </p>
        </div>

        <div className="bento-grid">
          {pillars.map((p, idx) => (
            <div key={idx} className="bento-card col-span-1">
              <div className="bento-tag-wrap" style={{ marginBottom: '14px' }}>
                <span className="bento-icon">{p.icon}</span>
                <span className="bento-badge">{p.title.toUpperCase()}</span>
              </div>
              <h3 className="bento-title" style={{ fontSize: '18px', marginBottom: '8px' }}>{p.subtitle}</h3>
              <p className="bento-desc" style={{ marginBottom: '0' }}>{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Direct Studio & Docs Gateway Section */}
      <section className="home-cta-banner" style={{ marginTop: '0', marginBottom: '60px' }}>
        <div className="cta-banner-content" style={{ padding: '48px 32px' }}>
          <h2>Interactive Coastal Map &amp; Complete Documentation</h2>
          <p style={{ maxWidth: '640px', margin: '0 auto 24px' }}>
            Explore the live map in 3 specialized layouts (Split Studio, Tactical Map, and Command Bento) or read our comprehensive technical guide detailing data sources, models, and API endpoints.
          </p>
          <div className="banner-btns">
            <button className="btn-primary" onClick={() => onNavigate('studio')}>
              <span>Open Live Studio</span>
              <span className="arrow-icon">→</span>
            </button>
            <button className="btn-secondary" onClick={() => onNavigate('docs')}>
              <span>Explore Technical Docs</span>
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
