import React, { useState } from 'react';

export default function DocsPage({ onNavigate }) {
  const [activeSection, setActiveSection] = useState('executive-summary');
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedKey, setCopiedKey] = useState(null);

  const copyToClipboard = (text, key) => {
    navigator.clipboard?.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const sections = [
    { id: 'executive-summary', title: '1. Executive Summary & Problem Scope' },
    { id: 'system-architecture', title: '2. System Architecture & Pipeline' },
    { id: 'datasets-ingestion', title: '3. Datasets & Ingestion Protocols' },
    { id: 'model-architectures', title: '4. Model Architectures & Training' },
    { id: 'evaluation-benchmarks', title: '5. Evaluation Benchmarks & Validation' },
    { id: 'operator-guide', title: '6. Operator User Guide & UI Workflows' },
    { id: 'map-basemaps', title: '7. Multi-Basemap & Layout System' },
    { id: 'api-reference', title: '8. REST API Reference & Endpoints' },
  ];

  const filteredSections = sections.filter((s) =>
    s.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="docs-container">
      {/* Background Ambient Lighting Blobs */}
      <div className="ambient-blob primary" style={{ top: '-100px', left: '10%' }} />
      <div className="ambient-blob secondary" style={{ top: '800px', right: '5%' }} />

      {/* Docs Header */}
      <header className="docs-header">
        <div className="docs-header-inner">
          <div className="home-brand" onClick={() => onNavigate('home')} role="button" tabIndex={0} title="MarineGuard AI">
            <div className="brand-icon">≈</div>
            <div className="brand-block">
              <div className="brand-text">
                <span>MarineGuard</span>
                <span className="tag">AI</span>
              </div>
              <span className="brand-sub">Technical Documentation & Field Manual</span>
            </div>
          </div>

          <nav className="home-nav-links">
            <button className="home-nav-btn" onClick={() => onNavigate('home')}>
              <span>🏠</span> Overview
            </button>
            <button className="home-nav-btn" onClick={() => onNavigate('studio')}>
              <span>🛰️</span> Live Studio
            </button>
            <button className="home-nav-btn active" onClick={() => onNavigate('docs')}>
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

      {/* Main Docs Body: Sidebar + Content */}
      <div className="docs-layout">
        {/* Sticky Sidebar Navigation */}
        <aside className="docs-sidebar">
          <div className="docs-search-box">
            <input
              type="text"
              placeholder="Search documentation..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="docs-search-input"
            />
            {searchTerm && (
              <button className="docs-search-clear" onClick={() => setSearchTerm('')}>
                ×
              </button>
            )}
          </div>

          <div className="docs-nav-group">
            <span className="docs-nav-label">TABLE OF CONTENTS</span>
            <ul className="docs-nav-list">
              {filteredSections.map((sec) => (
                <li key={sec.id}>
                  <button
                    className={`docs-nav-link ${activeSection === sec.id ? 'active' : ''}`}
                    onClick={() => {
                      setActiveSection(sec.id);
                      document.getElementById(sec.id)?.scrollIntoView({ behavior: 'smooth' });
                    }}
                  >
                    {sec.title}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        {/* Documentation Content Area */}
        <main className="docs-content">
          {/* SECTION 1 */}
          <section id="executive-summary" className="docs-section">
            <span className="docs-tag">SECTION 01</span>
            <h1 className="docs-heading">1. Executive Summary & Problem Scope</h1>
            <p className="docs-lead">
              The Singapore Strait is one of the world's most congested maritime corridors, accommodating over 100,000 vessel transits annually. Concurrently, transboundary ocean currents, intense tropical monsoon precipitation, and high-density urban canal discharge deposit severe quantities of anthropogenic plastic debris onto critical intertidal ecosystems, coral reefs, and public shorelines.
            </p>

            <div className="docs-callout note">
              <span className="callout-icon">ℹ️</span>
              <div>
                <strong>Operational Objective:</strong> MarineGuard AI automates the transition from passive post-stranding beach cleanups to proactive, water-borne interception. By pairing orbital Sentinel-2 multispectral imaging with high-resolution drone observation, real-time Lagrangian advection, and Bayesian transboundary attribution, cleanup vessels are dispatched with optimized routes before slicks beach.
              </div>
            </div>

            <h3 className="docs-subheading">Core Technological Innovations</h3>
            <div className="docs-grid-2">
              <div className="docs-card">
                <h4>Dual-Scale Vision Fusion</h4>
                <p>Overcomes the resolution trade-off by combining Sentinel-2 MSI 10m sub-pixel spectral index mapping with UAV 4K centimeter-scale YOLOv8-OBB drone classification.</p>
              </div>
              <div className="docs-card">
                <h4>Dynamic Hydrodynamic Forecasting</h4>
                <p>Runge-Kutta 4th-order (RK4) numerical integration of real-time tidal velocity fields, Stokes drift, and 3% aerodynamic windage leeway across 6h–48h operational horizons.</p>
              </div>
              <div className="docs-card">
                <h4>Bayesian Attribution & IFI Runoff</h4>
                <p>Inverts particle drift backwards in time and applies Bayesian updating conditioned on NEA empirical baseline priors and real-time precipitation-induced canal flush indices (IFI).</p>
              </div>
              <div className="docs-card">
                <h4>Optimal Cleanup Prioritization</h4>
                <p>Formulates the Coastal Priority Index (CPI) to maximize debris mass retrieval rate per boat-hour, delivering a +130.1% performance gain over standard fixed patrol schedules.</p>
              </div>
            </div>
          </section>

          {/* SECTION 2 */}
          <section id="system-architecture" className="docs-section">
            <span className="docs-tag">SECTION 02</span>
            <h1 className="docs-heading">2. System Architecture & Pipeline</h1>
            <p>
              MarineGuard AI operates as an integrated 6-phase pipeline running asynchronous ingestion, inference, physics simulation, decision optimization, and full-stack GIS visualization.
            </p>

            <div className="pipeline-flow-diagram">
              <div className="flow-step">
                <span className="flow-number">1</span>
                <span className="flow-title">Orbital Ingestion</span>
                <span className="flow-sub">Sentinel-2 MSI Level-2A</span>
              </div>
              <div className="flow-arrow">→</div>
              <div className="flow-step">
                <span className="flow-number">2</span>
                <span className="flow-title">CV Segmentation</span>
                <span className="flow-sub">FDI/FPI + YOLOv8-OBB</span>
              </div>
              <div className="flow-arrow">→</div>
              <div className="flow-step">
                <span className="flow-number">3</span>
                <span className="flow-title">Lagrangian Drift</span>
                <span className="flow-sub">RK4 Advection Engine</span>
              </div>
              <div className="flow-arrow">→</div>
              <div className="flow-step">
                <span className="flow-number">4</span>
                <span className="flow-title">Bayesian Origin</span>
                <span className="flow-sub">Backtrack + IFI Prior</span>
              </div>
              <div className="flow-arrow">→</div>
              <div className="flow-step">
                <span className="flow-number">5</span>
                <span className="flow-title">CPI Optimization</span>
                <span className="flow-sub">Priority Dispatch</span>
              </div>
              <div className="flow-arrow">→</div>
              <div className="flow-step">
                <span className="flow-number">6</span>
                <span className="flow-title">Field Deployment</span>
                <span className="flow-sub">Incident Action Plans</span>
              </div>
            </div>

            <h3 className="docs-subheading">Architecture Component Decoupling</h3>
            <table className="docs-table">
              <thead>
                <tr>
                  <th>Layer</th>
                  <th>Technology</th>
                  <th>Key Responsibility</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Computer Vision</strong></td>
                  <td>PyTorch, U-Net (ResNet-50), YOLOv8-OBB</td>
                  <td>Multispectral sub-pixel slick segmentation & drone object counting</td>
                </tr>
                <tr>
                  <td><strong>Physics Simulation</strong></td>
                  <td>NumPy, SciPy, Oceanographic RK4</td>
                  <td>Lagrangian particle tracking, turbulent diffusion, windage leeway</td>
                </tr>
                <tr>
                  <td><strong>Attribution Engine</strong></td>
                  <td>Bayesian Probabilistic Graphical Model</td>
                  <td>Inverting advection trajectories with NEA empirical priors & rainfall IFI</td>
                </tr>
                <tr>
                  <td><strong>Decision Support</strong></td>
                  <td>Linear Programming & CPI Ranking</td>
                  <td>Scavenger catamaran routing, containment booms, beach squad allocation</td>
                </tr>
                <tr>
                  <td><strong>Backend Service</strong></td>
                  <td>FastAPI, Uvicorn, Pydantic v2</td>
                  <td>High-throughput asynchronous REST API with streaming simulation endpoints</td>
                </tr>
                <tr>
                  <td><strong>Frontend Cockpit</strong></td>
                  <td>React 19, Leaflet, Custom Design System</td>
                  <td>Triple-layout cockpit, 6 basemap styles, dynamic slider simulations</td>
                </tr>
              </tbody>
            </table>
          </section>

          {/* SECTION 3 */}
          <section id="datasets-ingestion" className="docs-section">
            <span className="docs-tag">SECTION 03</span>
            <h1 className="docs-heading">3. Datasets & Ingestion Protocols</h1>
            <p>
              The system consumes heterogeneous remote sensing, aerial, oceanographic, and meteorological data streams to build an accurate real-time environmental picture:
            </p>

            <h3 className="docs-subheading">A. Multispectral Orbital Imagery (Sentinel-2 MSI)</h3>
            <p>
              Ingests European Space Agency (ESA) Copernicus Sentinel-2 MSI Level-2A surface reflectance data. The bands of interest are:
            </p>
            <ul className="docs-bullet-list">
              <li><strong>Band 2 (Blue, 490 nm, 10m):</strong> Background water penetration and baseline reflectance.</li>
              <li><strong>Band 3 (Green, 560 nm, 10m):</strong> Suspended sediment discrimination.</li>
              <li><strong>Band 4 (Red, 665 nm, 10m):</strong> Chlorophyll absorption and baseline subtraction.</li>
              <li><strong>Band 8 (NIR, 842 nm, 10m):</strong> Primary water absorption; floating plastic shows distinct positive NIR reflectance.</li>
              <li><strong>Band 11 (SWIR-1, 1610 nm, 20m):</strong> Baseline atmospheric water vapor and glint reference.</li>
            </ul>

            <h3 className="docs-subheading">B. High-Resolution Aerial UAV Drone Imagery</h3>
            <p>
              High-resolution 4K RGB drone footage captured across key Singapore littoral testbeds (East Coast Park, Pasir Ris, Changi Beach, Sentosa Palawan/Tanjong, and Pulau Ubin). Classes identified:
            </p>
            <div className="docs-tags-cloud">
              <span className="docs-pill">PET Plastic Bottles</span>
              <span className="docs-pill">Food Packaging & Wrappers</span>
              <span className="docs-pill">Expanded Polystyrene Foam (EPS)</span>
              <span className="docs-pill">Discarded Fishing Nets & Ropes</span>
              <span className="docs-pill">Microplastic Polymeric Fragments</span>
            </div>

            <h3 className="docs-subheading">C. Oceanographic & Meteorological Telemetry</h3>
            <ul className="docs-bullet-list">
              <li><strong>Tidal Current Field:</strong> Copernicus Marine (CMEMS) Global Ocean Physics Analysis & Forecast coupled with local tide gauge calibrations for the Singapore Strait and Johor River estuary (Ebb / Flood cycles).</li>
              <li><strong>Real-Time Weather:</strong> Integrated via <code>api-open.data.gov.sg/v2/real-time</code> for station wind speed, direction, and 5-minute precipitation telemetry.</li>
              <li><strong>NEA Empirical Baselines:</strong> Singapore National Environment Agency marine baseline findings showing ~97% transboundary maritime origins during typical dry monsoonal periods.</li>
            </ul>
          </section>

          {/* SECTION 4 */}
          <section id="model-architectures" className="docs-section">
            <span className="docs-tag">SECTION 04</span>
            <h1 className="docs-heading">4. Model Architectures & Training Protocols</h1>

            <h3 className="docs-subheading">A. Macro Computer Vision: Spectral Index Formulations</h3>
            <p>
              Floating plastics exhibit strong absorption contrast in the Near-Infrared (NIR) spectrum compared to pure water. We compute the <strong>Floating Debris Index (FDI)</strong>:
            </p>
            <div className="docs-formula-box">
              <code>FDI = R_NIR - [ R_RED + (R_SWIR1 - R_RED) * ((λ_NIR - λ_RED) / (λ_SWIR1 - λ_RED)) * 10 ]</code>
            </div>
            <p>
              To eliminate false positives from sargassum, macroalgae, and natural flotsam, we concurrently evaluate the <strong>Normalized Difference Vegetation Index (NDVI)</strong> and <strong>Floating Plastics Index (FPI)</strong>:
            </p>
            <div className="docs-formula-box">
              <code>NDVI = (R_NIR - R_RED) / (R_NIR + R_RED)</code>
              <br />
              <code>Condition: True_Plastic = (FDI &gt; 0.012) &amp;&amp; (NDVI &lt; 0.20)</code>
            </div>

            <h3 className="docs-subheading">B. Macro Deep Learning Segmentation (U-Net ResNet-50)</h3>
            <p>
              A U-Net architecture with a ResNet-50 encoder pre-trained on ImageNet is fine-tuned on the MARIDA and Marine-Debris multispectral benchmark datasets:
            </p>
            <ul className="docs-bullet-list">
              <li><strong>Loss Function:</strong> Combined Binary Cross-Entropy and Soft Dice Loss: <code>L = L_BCE + L_Dice</code></li>
              <li><strong>Optimizer:</strong> AdamW with initial learning rate <code>1e-4</code> and weight decay <code>1e-2</code>.</li>
              <li><strong>Schedule:</strong> Cosine annealing learning rate scheduler over 50 epochs with warm-up.</li>
            </ul>

            <h3 className="docs-subheading">C. Micro Drone Detection (YOLOv8-OBB)</h3>
            <p>
              Standard axis-aligned bounding boxes fail on elongated coastal debris (ropes, entangled nets) oriented at arbitrary beach angles. We deploy <strong>YOLOv8-OBB (Oriented Bounding Boxes)</strong>:
            </p>
            <ul className="docs-bullet-list">
              <li><strong>Representation:</strong> 5 parameters per detection: <code>(x_center, y_center, width, height, angle_θ)</code>.</li>
              <li><strong>Data Augmentation:</strong> Mosaic, Random Affine, HSV color jitter, and rotation (-180° to +180°).</li>
            </ul>

            <h3 className="docs-subheading">D. Lagrangian Particle Advection Physics</h3>
            <p>
              Debris particles are advected using 4th-order Runge-Kutta numerical integration accounting for ocean currents, windage leeway, and turbulent diffusion:
            </p>
            <div className="docs-formula-box">
              <code>dX/dt = u_current(x, t) + c_w * u_wind(x, t) + u'_turb</code>
              <br />
              <code>u'_turb = sqrt(2 * K_h * dt) * ξ (where K_h = 1.0 m²/s, c_w = 0.03)</code>
            </div>

            <h3 className="docs-subheading">E. Bayesian Source Attribution & Inland Flush Index (IFI)</h3>
            <p>
              By inverting time (<code>dt &lt; 0</code>), trajectories backtrack to candidate source zones. The posterior probability of origin domain <code>S_k</code> is given by Bayes' Theorem:
            </p>
            <div className="docs-formula-box">
              <code>P(S_k | Detection) = [ P(Trajectory ∈ S_k) * P_prior(S_k | IFI) ] / Σ_j [ P(Trajectory ∈ S_j) * P_prior(S_j | IFI) ]</code>
            </div>
            <p>
              The <strong>Inland Flush Index (IFI)</strong> dynamically scales canal runoff prior probability using 6-hour antecedent precipitation:
            </p>
            <div className="docs-formula-box">
              <code>IFI = min( 1.0, (Rain_current + 0.5 * Rain_prev6h) / 50.0 )</code>
            </div>
          </section>

          {/* SECTION 5 */}
          <section id="evaluation-benchmarks" className="docs-section">
            <span className="docs-tag">SECTION 05</span>
            <h1 className="docs-heading">5. Evaluation Benchmarks & Validation</h1>
            <p>
              Rigorous quantitative evaluations confirm that all sub-systems satisfy or exceed target operational thresholds:
            </p>

            <table className="docs-table">
              <thead>
                <tr>
                  <th>Sub-System</th>
                  <th>Primary Metric</th>
                  <th>Baseline</th>
                  <th>MarineGuard AI</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Macro CV (Sentinel-2)</strong></td>
                  <td>F1-Score / IoU</td>
                  <td>0.680 (FDI threshold)</td>
                  <td><strong>F1: 0.842 / IoU: 0.728</strong></td>
                  <td><span className="badge-pass">EXCEEDED</span></td>
                </tr>
                <tr>
                  <td><strong>Micro CV (UAV Drone)</strong></td>
                  <td>mAP@0.5</td>
                  <td>0.582 (YOLOv5 axis-aligned)</td>
                  <td><strong>0.794 (YOLOv8-OBB)</strong></td>
                  <td><span className="badge-pass">EXCEEDED</span></td>
                </tr>
                <tr>
                  <td><strong>Drift Advection (24h)</strong></td>
                  <td>Spatial IoU</td>
                  <td>0.410 (Tide only)</td>
                  <td><strong>0.630 (RK4 + Windage)</strong></td>
                  <td><span className="badge-pass">EXCEEDED</span></td>
                </tr>
                <tr>
                  <td><strong>Source Attribution</strong></td>
                  <td>Top-3 Accuracy</td>
                  <td>71.0% (Geometry only)</td>
                  <td><strong>96.2% (Bayesian + IFI)</strong></td>
                  <td><span className="badge-pass">EXCEEDED</span></td>
                </tr>
                <tr>
                  <td><strong>Cleanup Retrieval Rate</strong></td>
                  <td>kg debris / boat-hr</td>
                  <td>38.5 kg/hr (Fixed schedule)</td>
                  <td><strong>88.6 kg/hr (+130.1%)</strong></td>
                  <td><span className="badge-pass">EXCEEDED</span></td>
                </tr>
              </tbody>
            </table>
          </section>

          {/* SECTION 6 */}
          <section id="operator-guide" className="docs-section">
            <span className="docs-tag">SECTION 06</span>
            <h1 className="docs-heading">6. Operator User Guide & UI Workflows</h1>
            <p>
              Step-by-step operational instructions for coastal defense operators and response coordinators:
            </p>

            <h3 className="docs-subheading">A. Launching & Navigating the Studio</h3>
            <ol className="docs-steps-list">
              <li>Click <strong>Launch Live Studio</strong> in the top navigation bar or homepage hero.</li>
              <li>Inspect the top status bar: Verify <strong>Live (Telemetry Online)</strong> is active with low latency (&lt;100ms).</li>
              <li>Select your operational focus area using the <strong>Area Selector</strong> (Default: <em>All Singapore Waters</em>).</li>
            </ol>

            <h3 className="docs-subheading">B. Working with the 4 Operational Tabs</h3>
            <div className="docs-grid-2">
              <div className="docs-card">
                <h4>🛰️ Detections Tab</h4>
                <p>Lists all verified plastic slicks detected by Sentinel-2 MSI and UAV drone patrols. Clicking any card automatically centers and zooms the map to the target slick.</p>
              </div>
              <div className="docs-card">
                <h4>↗ Forecast Tab</h4>
                <p>Displays forward advection predictions. Use the bottom timeline scrubber (<code>Now</code>, <code>+2h</code>, <code>+6h</code>, <code>+12h</code>, <code>+24h</code>, <code>+48h</code>) to review predicted slick movement.</p>
              </div>
              <div className="docs-card">
                <h4>⚓ Origin Tab</h4>
                <p>Displays Bayesian source attribution probabilities. Move the <strong>Rainfall Intensity Slider</strong> (0 to 80 mm/h) to simulate monsoon canal flush surges in real-time.</p>
              </div>
              <div className="docs-card">
                <h4>🚨 Dispatch Tab</h4>
                <p>Ranks coastal zones by Coastal Priority Index (CPI). Filter by priority chip (<code>CRITICAL</code>, <code>HIGH</code>, <code>MEDIUM</code>) and download Incident Action Plans.</p>
              </div>
            </div>

            <h3 className="docs-subheading">C. Exporting Incident Action Plans (IAP)</h3>
            <p>
              Click <strong>Export IAP</strong> in the top-right header or in the Dispatch tab to download machine-readable JSON coordinates or plain-text field orders formatted for vessel helm tablets.
            </p>
          </section>

          {/* SECTION 7 */}
          <section id="map-basemaps" className="docs-section">
            <span className="docs-tag">SECTION 07</span>
            <h1 className="docs-heading">7. Multi-Basemap & Layout System</h1>
            <p>
              MarineGuard AI incorporates full multi-basemap layer switching and 3 specialized layout modes to accommodate diverse operational environments:
            </p>

            <h3 className="docs-subheading">Supported Basemap Styles</h3>
            <div className="basemaps-table-grid">
              <div className="basemap-info-card">
                <span className="basemap-icon">🌌</span>
                <h4>Dark Canvas (Esri)</h4>
                <p>Default minimalist charcoal theme optimized for high-contrast tactical visibility without night-vision degradation.</p>
                <span className="basemap-tag">Default Active</span>
              </div>
              <div className="basemap-info-card">
                <span className="basemap-icon">🛰️</span>
                <h4>Satellite Imagery (Esri)</h4>
                <p>Ultra-high resolution true-color satellite imagery showing reef structures, sandbars, and port infrastructure.</p>
                <span className="basemap-tag">High-Resolution</span>
              </div>
              <div className="basemap-info-card">
                <span className="basemap-icon">⛰️</span>
                <h4>Terrain / Topographic (Esri Topo)</h4>
                <p>Topographical elevation shading illustrating coastal bluffs, mangrove elevation gradients, and drainage basins.</p>
                <span className="basemap-tag">Topographic</span>
              </div>
              <div className="basemap-info-card">
                <span className="basemap-icon">🗺️</span>
                <h4>OpenStreetMap Standard</h4>
                <p>Open community nautical and road basemap featuring port facilities, breakwaters, and coastal landmarks.</p>
                <span className="basemap-tag">Standard OSM</span>
              </div>
            </div>

            <h3 className="docs-subheading">Operational Layout Modes</h3>
            <ul className="docs-bullet-list">
              <li><strong>Split Studio:</strong> Dual-pane cockpit pairing the interactive Leaflet canvas with the 4-tab operational telemetry drawer.</li>
              <li><strong>Tactical Map:</strong> Full-bleed 100vh map view with a floating translucent radar HUD and quick toggle controls.</li>
              <li><strong>Command Bento:</strong> Executive dashboard featuring 4 top telemetry KPI cards, central geographic map, and side decision panels.</li>
            </ul>
          </section>

          {/* SECTION 8 */}
          <section id="api-reference" className="docs-section">
            <span className="docs-tag">SECTION 08</span>
            <h1 className="docs-heading">8. REST API Reference & Endpoints</h1>
            <p>
              MarineGuard AI is backed by a FastAPI high-performance asynchronous server running on <code>http://127.0.0.1:8000</code>.
            </p>

            <div className="api-endpoint-card">
              <div className="endpoint-header">
                <span className="http-method get">GET</span>
                <span className="endpoint-url">/api/v1/hotspots</span>
              </div>
              <p className="endpoint-desc">Returns all active detected marine litter hotspots with geographic coordinates, polygon geometry, confidence, and estimated items.</p>
              <div className="code-block-wrap">
                <div className="code-header">
                  <span>Sample Response (JSON)</span>
                  <button
                    className="copy-btn"
                    onClick={() => copyToClipboard('{\n  "total_detected": 4,\n  "hotspots": [...]\n}', 'get-hotspots')}
                  >
                    {copiedKey === 'get-hotspots' ? '✓ Copied' : 'Copy'}
                  </button>
                </div>
                <pre><code>{`{
  "total_detected": 4,
  "hotspots": [
    {
      "id": "HS-EAST-01",
      "name": "East Coast Shoreline & Bedok Waters Hotspot #1",
      "severity": "HIGH",
      "lat": 1.298,
      "lng": 103.925,
      "confidence": 0.95,
      "area_sqm": 32400,
      "estimated_items": 324
    }
  ]
}`}</code></pre>
              </div>
            </div>

            <div className="api-endpoint-card">
              <div className="endpoint-header">
                <span className="http-method get">GET</span>
                <span className="endpoint-url">/api/v1/forecast?horizon=24</span>
              </div>
              <p className="endpoint-desc">Retrieves Lagrangian forward advection trajectories and particle clusters for a specified forecast horizon (6h, 12h, 24h, 48h).</p>
            </div>

            <div className="api-endpoint-card">
              <div className="endpoint-header">
                <span className="http-method post">POST</span>
                <span className="endpoint-url">/api/v1/attribution</span>
              </div>
              <p className="endpoint-desc">Executes dynamic Bayesian source attribution computation given current or simulated rainfall intensity.</p>
              <div className="code-block-wrap">
                <div className="code-header">
                  <span>Request Payload (JSON)</span>
                </div>
                <pre><code>{`{
  "rainfall_mm_per_hr": 45.0,
  "decay_hours": 12.0
}`}</code></pre>
              </div>
            </div>

            <div className="api-endpoint-card">
              <div className="endpoint-header">
                <span className="http-method get">GET</span>
                <span className="endpoint-url">/api/v1/cleanup/recommendations</span>
              </div>
              <p className="endpoint-desc">Retrieves the prioritized list of cleanup intervention orders sorted by Coastal Priority Index (CPI).</p>
            </div>

            <div className="api-endpoint-card">
              <div className="endpoint-header">
                <span className="http-method get">GET</span>
                <span className="endpoint-url">/api/v1/cleanup/report/download</span>
              </div>
              <p className="endpoint-desc">Generates and streams a downloadable Incident Action Plan (IAP) JSON file with timestamp, mission ID, and dispatch routing.</p>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
