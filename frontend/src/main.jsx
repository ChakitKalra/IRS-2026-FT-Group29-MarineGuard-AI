import React, { useEffect, useState, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import { MapContainer, TileLayer, CircleMarker, Popup, Polygon, Polyline, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './styles.css';
import Homepage from './Homepage';
import DocsPage from './DocsPage';
import {
  areas,
  tiles,
  colors,
  phase1Tiles,
  phase1Polygons,
  liveWeatherData,
  driftForecasts,
  sourceAttributionData,
  sourceDomainPolygons,
  backtrackingTrajectories,
  estimatedOriginMarkers,
  cleanupDecisionData,
  dispatchTargetMarkers,
} from './data';

export const BASEMAP_PRESETS = {
  'dark-canvas': {
    id: 'dark-canvas',
    name: 'Dark Canvas (Esri)',
    icon: '🌌',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
    maxZoom: 16,
  },
  'satellite': {
    id: 'satellite',
    name: 'Satellite (Esri)',
    icon: '🛰️',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri, Maxar, Earthstar Geographics, CNES/Airbus DS',
    maxZoom: 18,
  },
  'terrain': {
    id: 'terrain',
    name: 'Terrain / Topo (Esri)',
    icon: '⛰️',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; DeLorme, NAVTEQ, USGS',
    maxZoom: 18,
  },
  'osm': {
    id: 'osm',
    name: 'OpenStreetMap',
    icon: '🗺️',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  },
};

function BasemapSelector({ activeBasemap, onChange }) {
  return (
    <div className="basemap-selector-wrap" title="Switch Basemap Style (Dark, Satellite, Terrain, OpenStreetMap)">
      <select
        className="basemap-select"
        value={activeBasemap}
        onChange={(e) => onChange(e.target.value)}
        aria-label="Select Basemap Style"
      >
        {Object.entries(BASEMAP_PRESETS).map(([key, style]) => (
          <option key={key} value={key}>
            {style.icon} {style.name}
          </option>
        ))}
      </select>
    </div>
  );
}

function insidePolygon(point, vs) {
  const x = point[0], y = point[1];
  let inside = false;
  for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
    const xi = vs[i][0], yi = vs[i][1];
    const xj = vs[j][0], yj = vs[j][1];
    const intersect = ((yi > y) !== (yj > y)) && (x < ((xj - xi) * (y - yi)) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

function MapPosition({ area, selected }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(selected ? [selected.lat, selected.lng] : area.center, selected ? 14 : area.zoom, { duration: 0.8 });
  }, [area, selected, map]);
  return null;
}

function DrawClicks({ mode, onPoint }) {
  useMapEvents({
    click(e) {
      if (mode) onPoint([e.latlng.lat, e.latlng.lng]);
    },
  });
  return null;
}

function CoastalMap({
  area,
  selected,
  visible,
  onSelect,
  drawMode,
  draftPoints,
  onDraftPoint,
  showCurrentVectors,
  showAttributionLayer,
  showDispatchTargets,
  timeView,
  activeBasemap = 'dark-canvas',
}) {
  const currentTile = BASEMAP_PRESETS[activeBasemap] || BASEMAP_PRESETS['dark-canvas'];

  return (
    <MapContainer
      center={areas[0].center}
      zoom={11}
      scrollWheelZoom={true}
      doubleClickZoom={!drawMode}
      className="coastal-map-fill"
      aria-label="Singapore coastal intelligence map"
    >
      <TileLayer
        key={activeBasemap}
        attribution={currentTile.attribution}
        url={currentTile.url}
        maxZoom={currentTile.maxZoom}
      />
      <MapPosition area={area} selected={selected} />
      <DrawClicks mode={drawMode} onPoint={onDraftPoint} />

      {/* Candidate Source Domain Polygons (Phase 4) */}
      {showAttributionLayer &&
        sourceDomainPolygons.map((domain) => (
          <Polygon
            key={`domain-${domain.id}`}
            positions={domain.coordinates}
            pathOptions={{
              color: domain.color,
              fillColor: domain.color,
              fillOpacity: 0.12,
              weight: 1.5,
              dashArray: '4 4',
            }}
          >
            <Popup>
              <div style={{ minWidth: '180px' }}>
                <strong style={{ color: domain.color }}>{domain.name}</strong>
                <div style={{ color: '#8a8f98', margin: '4px 0 6px' }}>
                  {domain.category === 'marine_transboundary' ? '🌊 Marine / Transboundary' : '🏙️ Inland / Local Runoff'}
                </div>
                <div><b>Baseline Prior:</b> {(domain.baseline_prior * 100).toFixed(1)}%</div>
                <div style={{ fontSize: '10px', color: '#8a8f98', marginTop: '4px' }}>{domain.description}</div>
              </div>
            </Popup>
          </Polygon>
        ))}

      {/* Reverse Backtracking Trajectories (Phase 4) */}
      {showAttributionLayer &&
        backtrackingTrajectories.map((bt, i) => (
          <Polyline
            key={`backtrack-${bt.hotspot_id}-${i}`}
            positions={bt.coordinates}
            pathOptions={{
              color: bt.color,
              weight: selected?.id === bt.hotspot_id ? 4 : 2,
              opacity: 0.85,
              dashArray: '3 6',
            }}
          />
        ))}

      {/* Estimated Origins (Phase 4) */}
      {showAttributionLayer &&
        estimatedOriginMarkers.map((orig) => (
          <CircleMarker
            key={`origin-${orig.hotspot_id}`}
            center={[orig.lat, orig.lng]}
            radius={7}
            pathOptions={{
              color: '#ffffff',
              fillColor: orig.color,
              fillOpacity: 0.95,
              weight: 2,
            }}
          >
            <Popup>
              <strong>Estimated Release Origin</strong>
              <br />
              Source: <b>{orig.dominant_source_name}</b>
              <br />
              Transit Time: <b>~{orig.release_hours_ago} hours ago</b>
            </Popup>
          </CircleMarker>
        ))}

      {/* Tidal Surface Current Vectors (Phase 2) */}
      {showCurrentVectors &&
        (liveWeatherData?.current_points || []).map((pt, i) => {
          const lat = pt.lat ?? pt.latitude;
          const lng = pt.lng ?? pt.longitude;
          if (lat == null || lng == null) return null;
          const heading = pt.heading_deg ?? pt.direction_towards_deg ?? 248.0;
          const lat2 = lat + 0.012 * Math.cos((heading * Math.PI) / 180);
          const lng2 = lng + 0.012 * Math.sin((heading * Math.PI) / 180);
          return (
            <React.Fragment key={`cur-${i}`}>
              <Polyline
                positions={[[lat, lng], [lat2, lng2]]}
                pathOptions={{ color: '#38bdf8', weight: 1.5, opacity: 0.7 }}
              />
              <CircleMarker
                center={[lat, lng]}
                radius={2}
                pathOptions={{ color: '#38bdf8', fillColor: '#38bdf8', fillOpacity: 0.9 }}
              />
            </React.Fragment>
          );
        })}

      {/* Forward Trajectory Polylines (Phase 3) */}
      {timeView !== 'current' &&
        visible.map((fc) => (
          <React.Fragment key={`fc-traj-${fc.id}`}>
            {fc.trajectory_points && fc.trajectory_points.length > 1 && (
              <Polyline
                positions={fc.trajectory_points}
                pathOptions={{
                  color: fc.status === 'Beached Accumulation' ? '#ff4757' : '#38bdf8',
                  weight: selected?.id === fc.id ? 4 : 2,
                  dashArray: fc.status === 'Beached Accumulation' ? '5 5' : '6 4',
                  opacity: 0.85,
                }}
              />
            )}
          </React.Fragment>
        ))}

      {/* Sentinel-2 Satellite Debris Slick Polygons (Phase 1) */}
      {timeView === 'current' &&
        phase1Polygons.map((poly) => (
          <Polygon
            key={poly.id}
            positions={poly.coordinates}
            pathOptions={{ color: '#ff4757', fillColor: '#ff6b81', fillOpacity: 0.35, weight: 1.5 }}
          >
            <Popup>
              <strong>{poly.id} · Satellite Slick</strong>
              <br />
              Sensor: Sentinel-2 MSI (10m)
              <br />
              Estimated Area: <b>{poly.properties?.area_sq_meters?.toLocaleString()} m²</b>
              <br />
              Spectral FDI Anomaly: Detected
            </Popup>
          </Polygon>
        ))}

      {/* Point Observations & Forecast Accumulations */}
      {visible.map((tile) => {
        const markerColor = colors[tile.label] || '#ff806f';
        const isSelected = selected?.id === tile.id;
        const isBeached = tile.status === 'Beached Accumulation';
        return (
          <CircleMarker
            key={tile.id}
            center={[tile.lat, tile.lng]}
            radius={isSelected ? 13 : isBeached ? 10 : 8}
            pathOptions={{
              color: isSelected ? '#ffffff' : markerColor,
              fillColor: isBeached ? '#ff4757' : markerColor,
              fillOpacity: 0.9,
              weight: isSelected ? 3 : 2,
            }}
            eventHandlers={{ click: () => onSelect(tile) }}
          >
            <Popup>
              <div style={{ minWidth: '160px' }}>
                <strong style={{ fontSize: '13px' }}>{tile.name}</strong>
                <div style={{ color: '#8a8f98', margin: '4px 0 6px' }}>Status: {tile.label}</div>
                <div>Severity: <b>{tile.severity}</b></div>
                <div>Confidence: <b>{tile.confidence}%</b></div>
                {tile.target_shore && (
                  <div style={{ color: '#ff6b81', marginTop: '4px' }}>
                    Shore Target: <b>{tile.target_shore}</b> ({tile.beached_prob}%)
                  </div>
                )}
                {tile.total_area_sq_m && (
                  <div>Area: {tile.total_area_sq_m.toLocaleString()} m²</div>
                )}
              </div>
            </Popup>
          </CircleMarker>
        );
      })}

      {/* Dispatch Target Markers (Phase 5) */}
      {showDispatchTargets &&
        dispatchTargetMarkers.map((target) => (
          <CircleMarker
            key={`dispatch-pin-${target.order_id}`}
            center={[target.lat, target.lng]}
            radius={11}
            pathOptions={{
              color: '#ffffff',
              fillColor: target.priority_tier?.toLowerCase() === 'critical' ? '#ff4757' : '#ffa502',
              fillOpacity: 0.95,
              weight: 2.5,
            }}
          >
            <Popup>
              <strong>🚨 {target.order_id} · Priority Target</strong>
              <br />
              Action: <b>{target.intervention_type}</b>
              <br />
              CPI Score: <b>{target.cpi_score}</b> ({target.priority_tier?.toUpperCase()})
              <br />
              Resource: <b>{target.assigned_assets}</b>
              <br />
              Window: <b>{target.optimal_window_hours}</b>
            </Popup>
          </CircleMarker>
        ))}

      {/* Drawn Polygon Coordinates */}
      {draftPoints.length > 0 && (
        <Polyline positions={draftPoints} pathOptions={{ color: '#5e6ad2', dashArray: '4 4' }} />
      )}
    </MapContainer>
  );
}

function App() {
  // View Router State ('home' | 'studio' | 'docs')
  const [currentView, setCurrentView] = useState(() => {
    const hash = window.location.hash.toLowerCase();
    if (hash.includes('docs')) return 'docs';
    if (hash.includes('studio')) return 'studio';
    return 'home';
  });

  // Basemap Style State ('dark-canvas' | 'satellite' | 'terrain' | 'osm')
  const [activeBasemap, setActiveBasemap] = useState('dark-canvas');

  // Navigation & Layout State (3 Layout Modes)
  const [layoutMode, setLayoutMode] = useState('split'); // 'split' | 'tactical' | 'bento'
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const [activeTab, setActiveTab] = useState('detections'); // 'detections' | 'forecast' | 'attribution' | 'dispatch'

  // Map Controls State
  const [showCurrentVectors, setShowCurrentVectors] = useState(true);
  const [showAttributionLayer, setShowAttributionLayer] = useState(true);
  const [showDispatchTargets, setShowDispatchTargets] = useState(true);
  const [areaId, setAreaId] = useState('all');
  const [timeView, setTimeView] = useState('current');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    const handleHash = () => {
      const hash = window.location.hash.toLowerCase();
      if (hash.includes('docs')) setCurrentView('docs');
      else if (hash.includes('studio')) setCurrentView('studio');
      else setCurrentView('home');
    };
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const navigateTo = (view) => {
    setCurrentView(view);
    window.location.hash = view === 'home' ? '#/' : `#/${view}`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Polygon Drawing
  const [drawMode, setDrawMode] = useState(null);
  const [draftPoints, setDraftPoints] = useState([]);
  const [drawnArea, setDrawnArea] = useState(null);
  const [areaName, setAreaName] = useState('');

  // Phase 6 Full-Stack Integration State
  const [apiStatus, setApiStatus] = useState('checking'); // 'live' | 'offline' | 'checking'
  const [apiLatency, setApiLatency] = useState(0);
  const [rainfallSim, setRainfallSim] = useState(12.0);
  const [simRunning, setSimRunning] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [dispatchFilter, setDispatchFilter] = useState('all'); // 'all' | 'critical' | 'high' | 'low'

  const timeLabels = {
    current: 'Current (t = 0h)',
    '2': '+2h Forecast',
    '6': '+6h Forecast',
    '12': '+12h Forecast',
    '24': '+24h Forecast',
    '48': '+48h Forecast',
  };

  const syncBackendData = async () => {
    setApiStatus('checking');
    const t0 = performance.now();
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/health');
      if (res.ok) {
        const t1 = performance.now();
        setApiLatency(Math.max(1, Math.round(t1 - t0)));
        setApiStatus('live');
      } else {
        setApiStatus('offline');
      }
    } catch {
      setApiStatus('offline');
    }
  };

  useEffect(() => {
    syncBackendData();
    const interval = setInterval(syncBackendData, 20000);
    return () => clearInterval(interval);
  }, []);

  const runAttributionSimulation = async () => {
    setSimRunning(true);
    const targetId = selected?.originId || selected?.id || 'HS-EAST-01';
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/attribution', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hotspot_id: targetId,
          rainfall_rate_mmh: parseFloat(rainfallSim),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSimResult(data.attribution);
      }
    } catch (err) {
      console.warn('Simulation API call fallback:', err);
    } finally {
      setSimRunning(false);
    }
  };

  const downloadIAP = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/cleanup/report/download');
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `marineguard_incident_action_plan_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
        return;
      }
    } catch (err) {
      console.warn('API download fallback:', err);
    }
    const fallbackBlob = new Blob([JSON.stringify(cleanupDecisionData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(fallbackBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `marineguard_incident_action_plan_offline.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportDispatchBriefText = () => {
    const orders = cleanupDecisionData?.dispatch_recommendations || [];
    let text = `================================================================================\n`;
    text += `MARINEGUARD AI — COASTAL DISPATCH INCIDENT ACTION PLAN (IAP)\n`;
    text += `Generated: ${new Date().toUTCString()}\n`;
    text += `Authority: Maritime & Port Authority of Singapore / National Environment Agency\n`;
    text += `================================================================================\n\n`;
    orders.forEach((o, idx) => {
      text += `[ORDER #${idx + 1}] ${o.order_id} — ${o.hotspot_name}\n`;
      text += `  * PRIORITY: ${o.priority_tier?.toUpperCase()} (CPI Score: ${o.cpi_score})\n`;
      text += `  * INTERVENTION: ${o.intervention_type}\n`;
      text += `  * TIME WINDOW: ${o.optimal_window_hours} (Deadline: T+${o.action_deadline_hours}h)\n`;
      text += `  * STAGING BASE: ${o.staging_base}\n`;
      text += `  * ASSETS & CREW: ${o.assigned_assets} (${o.recommended_crew_size} personnel)\n`;
      text += `  * TARGET MASS: ~${o.expected_debris_mass_kg} kg | Prevention Rate: ${o.stranding_prevention_likelihood_pct}%\n`;
      text += `  * TACTICAL BRIEF: ${o.operational_instructions}\n\n`;
    });
    text += `================================================================================\n`;
    text += `OPERATIONAL BENCHMARK SUMMARY:\n`;
    text += `AI Retrieval Rate: 88.6 kg/hr (+130.1% vs 48h Routine Sweeps)\n`;
    text += `Response Latency: 2.4 hours (-90.0% reduction)\n`;
    text += `Water-borne Interception: 79.2% prevention before beach stranding\n`;
    text += `================================================================================\n`;

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `marineguard_tactical_brief_${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const activeHorizon = timeView !== 'current' ? driftForecasts?.horizons?.[timeView] : null;

  // Active dataset depending on forecast time view
  let activeDataset = phase1Tiles;
  if (timeView !== 'current' && activeHorizon?.hotspots) {
    activeDataset = activeHorizon.hotspots.map((fc) => {
      const orig = phase1Tiles.find((t) => t.id === fc.origin_hotspot_id) || {};
      return {
        id: fc.forecast_id,
        originId: fc.origin_hotspot_id,
        area: fc.origin_sector || orig.area || 'east',
        name: `${orig.name || fc.origin_hotspot_id} -> ${fc.status}`,
        lat: fc.predicted_lat,
        lng: fc.predicted_lng,
        label: fc.status,
        status: fc.status,
        target_shore: fc.target_shore,
        beached_prob: fc.beached_probability_pct,
        confidence: orig.confidence || 85,
        severity: fc.risk_level,
        detection_count: fc.predicted_items,
        trajectory_points: fc.trajectory_points,
      };
    });
  }

  const area = areaId === '__drawn__' && drawnArea ? drawnArea : areas.find((a) => a.id === areaId) || areas[0];
  const visible = activeDataset.filter(
    (t) => areaId === 'all' || (area.polygon ? insidePolygon([t.lat, t.lng], area.polygon) : t.area === areaId)
  );

  const selectedReport = selected
    ? sourceAttributionData?.attribution_reports?.find(
        (r) => r.hotspot_id === (selected.originId || selected.id)
      ) || sourceAttributionData?.attribution_reports?.[0]
    : sourceAttributionData?.attribution_reports?.[0];

  const filteredOrders = (cleanupDecisionData?.dispatch_recommendations || []).filter(
    (o) => dispatchFilter === 'all' || o.priority_tier?.toLowerCase() === dispatchFilter
  );

  if (currentView === 'home') {
    return (
      <Homepage
        onNavigate={navigateTo}
        liveMetrics={{
          currentSpeed: liveWeatherData?.mean_current_knots ? `${liveWeatherData.mean_current_knots} kts` : '1.04 kts',
          currentHeading: liveWeatherData?.current_heading_deg ? `${liveWeatherData.current_heading_deg}°` : '248°',
        }}
      />
    );
  }

  if (currentView === 'docs') {
    return <DocsPage onNavigate={navigateTo} />;
  }

  return (
    <>
      {/* Layered Ambient Background */}
      <div className="ambient-background">
        <div className="ambient-blob-1" />
        <div className="ambient-blob-2" />
        <div className="grid-overlay" />
      </div>

      {/* Top Mission Command Navigation */}
      <header className="top-navbar">
        <div className="nav-left">
          <div
            className="brand-badge"
            onClick={() => navigateTo('home')}
            role="button"
            tabIndex={0}
            style={{ cursor: 'pointer' }}
            title="Return to Homepage Overview"
          >
            <div className="brand-icon">≈</div>
            <div className="brand-text">
              <span>MarineGuard</span>
              <span className="tag">AI</span>
            </div>
          </div>

          {/* Map Layout Switcher */}
          <div className="layout-switcher" title="Experiment with different interactive map layouts">
            <button
              className={`layout-btn ${layoutMode === 'split' ? 'active' : ''}`}
              onClick={() => setLayoutMode('split')}
              title="Split Cockpit View: Map + Operational Drawer"
            >
              <span>◫</span> Split Studio
            </button>
            <button
              className={`layout-btn ${layoutMode === 'tactical' ? 'active' : ''}`}
              onClick={() => setLayoutMode('tactical')}
              title="Tactical Full-Bleed Map with Floating HUD"
            >
              <span>⛶</span> Tactical Map
            </button>
            <button
              className={`layout-btn ${layoutMode === 'bento' ? 'active' : ''}`}
              onClick={() => setLayoutMode('bento')}
              title="Command Bento Grid: Executive Overview"
            >
              <span>▦</span> Command Bento
            </button>
          </div>
        </div>

        {/* Live Environmental Telemetry Ticker */}
        <div className="nav-center">
          <div className="telemetry-item" title="Tidal Surface Current Speed & Heading">
            <span>🌊</span>
            <span>{liveWeatherData?.mean_current_knots || '1.04'} kts @ {liveWeatherData?.current_heading_deg || '248'}°</span>
          </div>
          <div className="telemetry-item" title="data.gov.sg Wind Leeway">
            <span>💨</span>
            <span>{liveWeatherData?.avg_wind_knots || '6.0'} kts @ {liveWeatherData?.wind_direction_from_deg || '156'}°</span>
          </div>
          <div className="telemetry-item" title="Canal Runoff & Inland Flushing Index">
            <span>🌧️</span>
            <span>{liveWeatherData?.inland_flushing_risk || 'Low'} Risk</span>
          </div>
        </div>

        {/* Right Actions & Live Status */}
        <div className="nav-right">
          <div className={`api-pill ${apiStatus === 'live' ? 'live' : 'offline'}`} title="FastAPI REST API Status">
            <span className="ping-dot" />
            <span>{apiStatus === 'live' ? `Live (${apiLatency}ms)` : 'Offline Store'}</span>
            <button className="btn-icon-ghost" onClick={syncBackendData} title="Re-sync API">⟳</button>
          </div>

          <button className="btn-primary-action" onClick={downloadIAP} title="Download official Incident Action Plan via FastAPI GET /api/v1/cleanup/report/download">
            <span>📥</span> Export IAP
          </button>

          {/* Hamburger Menu: Tab Switcher Contents (Navigate to Docs, Homepage, and Studio) */}
          <div className="hamburger-wrap" ref={menuRef}>
            <button
              className={`btn-hamburger ${menuOpen ? 'active' : ''}`}
              onClick={() => setMenuOpen(!menuOpen)}
              title="Page Navigation Menu"
              aria-label="Navigation Menu"
            >
              <span>☰</span>
            </button>
            {menuOpen && (
              <div className="hamburger-popover">
                <div className="popover-header">
                  <span className="popover-label">PAGE NAVIGATION</span>
                  <span className="popover-badge">STUDIO ACTIVE</span>
                </div>
                <div className="popover-menu-list">
                  <button
                    className="popover-item"
                    onClick={() => { navigateTo('home'); setMenuOpen(false); }}
                  >
                    <span className="item-icon">🏠</span>
                    <div className="item-details">
                      <span className="item-title">Overview</span>
                      <span className="item-desc">Platform Landing &amp; Live Telemetry</span>
                    </div>
                  </button>
                  <button
                    className="popover-item active"
                    onClick={() => { navigateTo('studio'); setMenuOpen(false); }}
                  >
                    <span className="item-icon">🛰️</span>
                    <div className="item-details">
                      <span className="item-title">Live Studio</span>
                      <span className="item-desc">Tactical GIS &amp; Dispatch Console</span>
                    </div>
                    <span className="item-check">●</span>
                  </button>
                  <button
                    className="popover-item"
                    onClick={() => { navigateTo('docs'); setMenuOpen(false); }}
                  >
                    <span className="item-icon">📖</span>
                    <div className="item-details">
                      <span className="item-title">Docs &amp; Guide</span>
                      <span className="item-desc">Methodology, Models &amp; API Reference</span>
                    </div>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* =========================================================================
          LAYOUT 1: SPLIT STUDIO (COCKPIT VIEW)
          ========================================================================= */}
      {layoutMode === 'split' && (
        <div className="split-studio-container">
          {/* Left: Map Viewport with Floating Glass Controls */}
          <div className="map-studio-col">
            <div className="studio-map-header">
              {/* Area & Draw Selector */}
              <div className="glass-toolbar">
                <span style={{ color: '#8a8f98', fontSize: '11px' }}>📍 Area:</span>
                <select
                  className="glass-select"
                  value={drawMode ? '__draw__' : areaId}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === '__draw__') {
                      setDrawMode('polygon');
                      setDraftPoints([]);
                    } else {
                      setDrawMode(null);
                      setAreaId(val);
                    }
                  }}
                >
                  <option value="all">All Singapore Waters</option>
                  {areas.filter((a) => a.id !== 'all').map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                  <option value="__draw__">Draw Custom Polygon…</option>
                </select>
              </div>

              {/* Layer Toggles */}
              <div className="glass-toolbar layer-toggles-bar">
                <button
                  className={`layer-pill ${showCurrentVectors ? 'active accent-blue' : ''}`}
                  onClick={() => setShowCurrentVectors(!showCurrentVectors)}
                >
                  🌊 Currents
                </button>
                <button
                  className={`layer-pill ${showAttributionLayer ? 'active accent-amber' : ''}`}
                  onClick={() => setShowAttributionLayer(!showAttributionLayer)}
                >
                  ⚓ Attribution
                </button>
                <button
                  className={`layer-pill ${showDispatchTargets ? 'active accent-red' : ''}`}
                  onClick={() => setShowDispatchTargets(!showDispatchTargets)}
                >
                  🚨 Dispatch ({dispatchTargetMarkers.length})
                </button>
                <BasemapSelector activeBasemap={activeBasemap} onChange={setActiveBasemap} />
              </div>
            </div>

            {/* Main Interactive Leaflet Map */}
            <CoastalMap
              area={area}
              selected={selected}
              visible={visible}
              onSelect={setSelected}
              drawMode={drawMode}
              draftPoints={draftPoints}
              onDraftPoint={(pt) => setDraftPoints((p) => [...p, pt])}
              showCurrentVectors={showCurrentVectors}
              showAttributionLayer={showAttributionLayer}
              showDispatchTargets={showDispatchTargets}
              timeView={timeView}
              activeBasemap={activeBasemap}
            />

            {/* Bottom Floating Timeline Stepper */}
            <div className="studio-map-timeline">
              <span className="timeline-label">Advection Horizon</span>
              <div className="horizon-stepper">
                {Object.entries(timeLabels).map(([k, label]) => (
                  <button
                    key={k}
                    className={`horizon-step-btn ${timeView === k ? 'active' : ''}`}
                    onClick={() => {
                      setTimeView(k);
                      setSelected(null);
                    }}
                  >
                    {k === 'current' ? 'Now (0h)' : `+${k}h`}
                  </button>
                ))}
              </div>
              <div className="timeline-stats">
                {timeView === 'current' ? (
                  <span>Showing <b>{visible.length}</b> verified clusters</span>
                ) : (
                  <span>
                    Stranded on Beaches: <strong>{activeHorizon?.beached_percentage || 0}%</strong>
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Right: Operational Command Drawer */}
          <div className="studio-drawer">
            {/* Tabs Header */}
            <div className="drawer-tabs-header">
              <button
                className={`drawer-tab ${activeTab === 'detections' ? 'active' : ''}`}
                onClick={() => setActiveTab('detections')}
              >
                🛰️ Detections <span className="tab-badge">{phase1Tiles.length}</span>
              </button>
              <button
                className={`drawer-tab ${activeTab === 'forecast' ? 'active' : ''}`}
                onClick={() => setActiveTab('forecast')}
              >
                ↗ Forecast <span className="tab-badge">{timeView === 'current' ? '0h' : `+${timeView}h`}</span>
              </button>
              <button
                className={`drawer-tab ${activeTab === 'attribution' ? 'active' : ''}`}
                onClick={() => setActiveTab('attribution')}
              >
                ⚓ Origin
              </button>
              <button
                className={`drawer-tab ${activeTab === 'dispatch' ? 'active' : ''}`}
                onClick={() => setActiveTab('dispatch')}
              >
                🚨 Dispatch <span className="tab-badge">{filteredOrders.length}</span>
              </button>
            </div>

            {/* Drawer Body Scroll */}
            <div className="drawer-content-scroll">
              {/* TAB 1: DETECTIONS */}
              {activeTab === 'detections' && (
                <div>
                  <div className="drawer-section-title">
                    <h3>Active Coastal Hotspots</h3>
                    <span>Sentinel-2 MSI + UAV TACO</span>
                  </div>
                  <div className="hotspot-cards-list">
                    {phase1Tiles.map((hs) => (
                      <div
                        key={hs.id}
                        className={`hotspot-item-card ${selected?.id === hs.id ? 'selected' : ''}`}
                        onClick={() => setSelected(hs)}
                      >
                        <div className="hotspot-top-meta">
                          <span className="hotspot-id">{hs.id}</span>
                          <span className={`severity-pill ${hs.severity?.toLowerCase()}`}>{hs.severity}</span>
                        </div>
                        <div className="hotspot-name">{hs.name}</div>
                        <div className="hotspot-metrics-row">
                          <span>Confidence: <strong>{hs.confidence}%</strong></span>
                          <span>Area: <strong>{hs.total_area_sq_m?.toLocaleString()} m²</strong></span>
                          <span>Items: <strong>{hs.detection_count}</strong></span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Draw polygon tool if active */}
                  {drawMode && (
                    <div className="sim-interactive-card">
                      <div style={{ fontWeight: 600, marginBottom: '6px' }}>Polygon Drawing Active</div>
                      <div style={{ fontSize: '11px', color: '#8a8f98', marginBottom: '8px' }}>
                        Click anywhere on map to add points ({draftPoints.length} added).
                      </div>
                      <button
                        className="btn-primary-action"
                        disabled={draftPoints.length < 3}
                        onClick={() => {
                          setDrawnArea({
                            id: '__drawn__',
                            name: areaName || 'Custom Zone',
                            center: [draftPoints[0][0], draftPoints[0][1]],
                            zoom: 13,
                            polygon: draftPoints,
                          });
                          setAreaId('__drawn__');
                          setDrawMode(null);
                        }}
                      >
                        Save Polygon Area
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: FORECAST */}
              {activeTab === 'forecast' && (
                <div>
                  <div className="drawer-section-title">
                    <h3>Lagrangian Drift Forecast</h3>
                    <span>4th-Order Runge-Kutta ({timeView === 'current' ? '+0h' : `+${timeView}h`})</span>
                  </div>

                  {/* Advection Horizon Time Switcher Buttons in Forecast Section */}
                  <div className="forecast-horizon-card">
                    <div className="forecast-horizon-header">
                      <span className="forecast-horizon-label">Advection Horizon</span>
                      <span className="forecast-horizon-badge">{timeLabels[timeView]}</span>
                    </div>
                    <div className="horizon-stepper drawer-horizon-stepper">
                      {Object.entries(timeLabels).map(([k]) => (
                        <button
                          key={k}
                          className={`horizon-step-btn ${timeView === k ? 'active' : ''}`}
                          onClick={() => {
                            setTimeView(k);
                            setSelected(null);
                          }}
                        >
                          {k === 'current' ? 'Now (0h)' : `+${k}h`}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="forecast-metric-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                      <span style={{ color: '#ff6b81' }}>Beach Stranding Probability:</span>
                      <strong style={{ color: '#ff6b81' }}>{activeHorizon?.beached_percentage || 0}%</strong>
                    </div>
                    <div className="forecast-progress-bar">
                      <div
                        className="progress-fill-beached"
                        style={{ width: `${activeHorizon?.beached_percentage || 0}%` }}
                      />
                      <div
                        className="progress-fill-floating"
                        style={{ width: `${100 - (activeHorizon?.beached_percentage || 0)}%` }}
                      />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#8a8f98' }}>
                      <span>Stranded Debris</span>
                      <span>Floating Marine Plume</span>
                    </div>
                  </div>

                  {activeHorizon?.top_impacted_shores && (
                    <div className="forecast-metric-card">
                      <div style={{ fontSize: '11px', fontWeight: 600, marginBottom: '8px' }}>
                        Vulnerable Coastal Impact Zones:
                      </div>
                      {Object.entries(activeHorizon.top_impacted_shores).map(([shore, count]) => (
                        <div key={shore} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: '11px' }}>
                          <span style={{ color: '#8a8f98' }}>{shore}</span>
                          <span style={{ fontFamily: 'var(--font-mono)', color: '#ff6b81', fontWeight: 600 }}>{count} debris units</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: SOURCE ATTRIBUTION */}
              {activeTab === 'attribution' && (
                <div>
                  <div className="drawer-section-title">
                    <h3>Probabilistic Origin Attribution</h3>
                    <span>Reverse RK4 (-48h) + Bayesian Prior</span>
                  </div>

                  <div className="attribution-overview-box">
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                      <span>🌊 Marine & Shipping: <b>{sourceAttributionData?.global_summary?.average_marine_transboundary_pct || 87.9}%</b></span>
                      <span>🏙️ Inland Runoff: <b>{sourceAttributionData?.global_summary?.average_inland_local_pct || 12.1}%</b></span>
                    </div>
                    <div className="attribution-bar-split">
                      <div
                        className="bar-marine"
                        style={{ width: `${sourceAttributionData?.global_summary?.average_marine_transboundary_pct || 87.9}%` }}
                      />
                      <div
                        className="bar-inland"
                        style={{ width: `${sourceAttributionData?.global_summary?.average_inland_local_pct || 12.1}%` }}
                      />
                    </div>
                  </div>

                  <div className="domain-breakdown-list">
                    {(sourceAttributionData?.attribution_reports?.[0]?.breakdown || []).map((dom) => (
                      <div key={dom.source_id} className="domain-row">
                        <div className="domain-label">
                          <span className="domain-dot" style={{ background: dom.color }} />
                          <span>{dom.source_name}</span>
                        </div>
                        <span className="domain-val" style={{ color: dom.color }}>{dom.percentage}%</span>
                      </div>
                    ))}
                  </div>

                  {/* Interactive Dynamic Simulator */}
                  <div className="sim-interactive-card">
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#ededef' }}>
                      ⚡ Dynamic Bayesian Coupling Simulator
                    </div>
                    <div style={{ fontSize: '10px', color: '#8a8f98', margin: '4px 0 10px' }}>
                      Couples precipitation with Inland Flushing Index (IFI) via <code>POST /api/v1/attribution</code>.
                    </div>

                    <div className="sim-slider-container">
                      <label>
                        <span>Simulated Rain Rate:</span>
                        <strong style={{ color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>{rainfallSim} mm/h</strong>
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="50"
                        step="2"
                        value={rainfallSim}
                        onChange={(e) => setRainfallSim(e.target.value)}
                      />
                    </div>

                    <button
                      className="btn-primary-action"
                      style={{ width: '100%', justifyContent: 'center' }}
                      disabled={simRunning}
                      onClick={runAttributionSimulation}
                    >
                      {simRunning ? 'Evaluating Physics...' : 'Run Dynamic Attribution ↗'}
                    </button>

                    {simResult && (
                      <div style={{ fontSize: '10px', color: '#38bdf8', marginTop: '10px', fontFamily: 'var(--font-mono)', lineHeight: 1.5 }}>
                        ✓ Evaluated for {simResult.hotspot_name}: Top Source <b>{simResult.classification?.top_source_name} ({simResult.classification?.top_source_percentage}%)</b> with {simResult.environmental_context?.inland_flushing_risk} IFI Risk.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 4: DISPATCH OPTIMIZER */}
              {activeTab === 'dispatch' && (
                <div>
                  <div className="drawer-section-title">
                    <h3>Cleanup Decision Support</h3>
                    <span>Coastal Priority Index (CPI)</span>
                  </div>

                  {/* Priority Filter Chips */}
                  <div className="dispatch-filter-chips">
                    {['all', 'critical', 'high', 'low'].map((f) => (
                      <button
                        key={f}
                        className={`filter-btn ${dispatchFilter === f ? 'active' : ''}`}
                        onClick={() => setDispatchFilter(f)}
                      >
                        {f.toUpperCase()}
                      </button>
                    ))}
                  </div>

                  {/* Orders List */}
                  {filteredOrders.map((order) => {
                    const tier = order.priority_tier?.toLowerCase() || 'medium';
                    return (
                      <div key={order.order_id} className={`dispatch-order-card ${tier}`}>
                        <div className="order-headline">
                          <span className="order-title">{order.hotspot_name}</span>
                          <span className={`severity-pill ${tier}`}>CPI {order.cpi_score}</span>
                        </div>
                        <div className="order-intervention-badge">⚡ {order.intervention_type}</div>

                        <div className="order-details-grid">
                          <div>Base: <b>{order.staging_base}</b></div>
                          <div>Window: <b>{order.optimal_window_hours}</b></div>
                          <div>Assets: <b>{order.assigned_assets}</b></div>
                          <div>Crew: <b>{order.recommended_crew_size} Pax</b></div>
                        </div>

                        <div className="order-actions-bar">
                          <span style={{ fontSize: '10px', color: '#4ade80', fontFamily: 'var(--font-mono)' }}>
                            🛡️ {order.stranding_prevention_likelihood_pct}% Prevention
                          </span>
                          <button
                            className="btn-locate-target"
                            onClick={() => {
                              const matched = phase1Tiles.find((t) => t.id === order.hotspot_id);
                              if (matched) setSelected(matched);
                            }}
                          >
                            Target on Map ⌖
                          </button>
                        </div>
                      </div>
                    );
                  })}

                  {/* Download Options */}
                  <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
                    <button className="btn-locate-target" style={{ flex: 1 }} onClick={exportDispatchBriefText}>
                      📄 Tactical Brief
                    </button>
                    <button className="btn-primary-action" style={{ flex: 1, justifyContent: 'center' }} onClick={downloadIAP}>
                      📥 Download IAP
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          LAYOUT 2: TACTICAL MAP (IMMERSIVE FULLSCREEN HUD)
          ========================================================================= */}
      {layoutMode === 'tactical' && (
        <div className="tactical-map-container">
          {/* Floating Left Telemetry HUD */}
          <div className="tactical-hud-left">
            <div className="tactical-telemetry-hud">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', fontWeight: 600, color: '#ededef' }}>SINGAPORE STRAIT RADAR</span>
                <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>LIVE</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                <div>Surface Speed: <b style={{ color: '#ededef' }}>{liveWeatherData?.mean_current_knots} kts</b></div>
                <div>Current Heading: <b style={{ color: '#ededef' }}>{liveWeatherData?.current_heading_deg}°</b></div>
                <div>Wind Leeway: <b style={{ color: '#ededef' }}>{liveWeatherData?.avg_wind_knots} kts</b></div>
                <div>Tidal Stage: <b style={{ color: '#ededef' }}>{liveWeatherData?.tidal_stage?.split(' ')[0]}</b></div>
              </div>
            </div>

            {/* Quick Layer Bar */}
            <div className="glass-toolbar">
              <button
                className={`layer-pill ${showCurrentVectors ? 'active accent-blue' : ''}`}
                onClick={() => setShowCurrentVectors(!showCurrentVectors)}
              >
                🌊 Currents
              </button>
              <button
                className={`layer-pill ${showAttributionLayer ? 'active accent-amber' : ''}`}
                onClick={() => setShowAttributionLayer(!showAttributionLayer)}
              >
                ⚓ Attribution
              </button>
              <button
                className={`layer-pill ${showDispatchTargets ? 'active accent-red' : ''}`}
                onClick={() => setShowDispatchTargets(!showDispatchTargets)}
              >
                🚨 Dispatch
              </button>
              <BasemapSelector activeBasemap={activeBasemap} onChange={setActiveBasemap} />
            </div>
          </div>

          {/* Full Screen Map */}
          <CoastalMap
            area={area}
            selected={selected}
            visible={visible}
            onSelect={setSelected}
            drawMode={drawMode}
            draftPoints={draftPoints}
            onDraftPoint={(pt) => setDraftPoints((p) => [...p, pt])}
            showCurrentVectors={showCurrentVectors}
            showAttributionLayer={showAttributionLayer}
            showDispatchTargets={showDispatchTargets}
            timeView={timeView}
            activeBasemap={activeBasemap}
          />

          {/* Floating Right Detail Card if selected */}
          {selected && (
            <div className="tactical-hud-right">
              <div className="tactical-telemetry-hud" style={{ background: 'rgba(10, 10, 15, 0.92)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span className="hotspot-id">{selected.originId || selected.id}</span>
                  <button className="btn-icon-ghost" onClick={() => setSelected(null)}>✕</button>
                </div>
                <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>{selected.name}</div>
                <div style={{ fontSize: '11px', color: '#8a8f98', marginBottom: '10px' }}>
                  Coordinates: {selected.lat.toFixed(4)}°N, {selected.lng.toFixed(4)}°E
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px', marginBottom: '12px' }}>
                  <div>Confidence: <b>{selected.confidence}%</b></div>
                  <div>Severity: <b>{selected.severity}</b></div>
                </div>
                {selectedReport && (
                  <div style={{ fontSize: '10px', color: '#8a8f98', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '8px' }}>
                    Dominant Origin: <b style={{ color: '#38bdf8' }}>{selectedReport.classification?.top_source_name}</b> ({selectedReport.classification?.top_source_percentage}%)
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Floating Bottom Timeline */}
          <div className="studio-map-timeline">
            <span className="timeline-label">Advection Horizon</span>
            <div className="horizon-stepper">
              {Object.entries(timeLabels).map(([k]) => (
                <button
                  key={k}
                  className={`horizon-step-btn ${timeView === k ? 'active' : ''}`}
                  onClick={() => setTimeView(k)}
                >
                  {k === 'current' ? 'Now (0h)' : `+${k}h`}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          LAYOUT 3: COMMAND BENTO (EXECUTIVE OVERVIEW VIEW)
          ========================================================================= */}
      {layoutMode === 'bento' && (
        <div className="command-bento-container">
          {/* Top 4 KPI Cards */}
          <div className="bento-telemetry-row">
            <div className="bento-kpi-card">
              <div className="kpi-title">SURFACE CURRENT</div>
              <div className="kpi-val">{liveWeatherData?.mean_current_knots} kts</div>
              <div className="kpi-sub">{liveWeatherData?.tidal_stage}</div>
            </div>
            <div className="bento-kpi-card">
              <div className="kpi-title">WINDAGE LEEWAY</div>
              <div className="kpi-val">{liveWeatherData?.avg_wind_knots} kts</div>
              <div className="kpi-sub">Bearing {liveWeatherData?.wind_direction_from_deg}° SSE (data.gov.sg)</div>
            </div>
            <div className="bento-kpi-card">
              <div className="kpi-title">CANAL RUNOFF RISK</div>
              <div className="kpi-val" style={{ color: '#4ade80' }}>{liveWeatherData?.inland_flushing_risk} IFI</div>
              <div className="kpi-sub">{liveWeatherData?.island_max_rain_mm_hr} mm/h Precipitation</div>
            </div>
            <div className="bento-kpi-card">
              <div className="kpi-title">RETRIEVAL EFFICIENCY</div>
              <div className="kpi-val" style={{ color: '#4ade80' }}>+130.1%</div>
              <div className="kpi-sub">88.6 kg/hr vs 38.5 kg/hr Baseline</div>
            </div>
          </div>

          {/* Bento Main Grid */}
          <div className="bento-main-grid">
            {/* Map Card */}
            <div className="bento-map-card">
              <div className="studio-map-header">
                <div className="glass-toolbar">
                  <span style={{ fontSize: '11px', color: '#8a8f98' }}>Horizon:</span>
                  <select
                    className="glass-select"
                    value={timeView}
                    onChange={(e) => setTimeView(e.target.value)}
                  >
                    {Object.entries(timeLabels).map(([k, label]) => (
                      <option key={k} value={k}>{label}</option>
                    ))}
                  </select>
                </div>
                <div className="glass-toolbar layer-toggles-bar">
                  <button
                    className={`layer-pill ${showCurrentVectors ? 'active accent-blue' : ''}`}
                    onClick={() => setShowCurrentVectors(!showCurrentVectors)}
                  >
                    🌊 Currents
                  </button>
                  <button
                    className={`layer-pill ${showDispatchTargets ? 'active accent-red' : ''}`}
                    onClick={() => setShowDispatchTargets(!showDispatchTargets)}
                  >
                    🚨 Dispatch
                  </button>
                  <BasemapSelector activeBasemap={activeBasemap} onChange={setActiveBasemap} />
                </div>
              </div>

              <CoastalMap
                area={area}
                selected={selected}
                visible={visible}
                onSelect={setSelected}
                drawMode={drawMode}
                draftPoints={draftPoints}
                onDraftPoint={(pt) => setDraftPoints((p) => [...p, pt])}
                showCurrentVectors={showCurrentVectors}
                showAttributionLayer={showAttributionLayer}
                showDispatchTargets={showDispatchTargets}
                timeView={timeView}
                activeBasemap={activeBasemap}
              />
            </div>

            {/* Side Bento Stack */}
            <div className="bento-side-stack">
              {/* Attribution Card */}
              <div className="bento-panel-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600 }}>Bayesian Source Distribution</span>
                  <span style={{ fontSize: '10px', color: '#8a8f98', fontFamily: 'var(--font-mono)' }}>NEA Empirical Baseline</span>
                </div>
                <div className="attribution-bar-split" style={{ height: '10px', margin: '10px 0 14px' }}>
                  <div
                    className="bar-marine"
                    style={{ width: `${sourceAttributionData?.global_summary?.average_marine_transboundary_pct || 87.9}%` }}
                  />
                  <div
                    className="bar-inland"
                    style={{ width: `${sourceAttributionData?.global_summary?.average_inland_local_pct || 12.1}%` }}
                  />
                </div>
                <div className="domain-breakdown-list">
                  {(sourceAttributionData?.attribution_reports?.[0]?.breakdown || []).slice(0, 3).map((d) => (
                    <div key={d.source_id} className="domain-row">
                      <div className="domain-label">
                        <span className="domain-dot" style={{ background: d.color }} />
                        <span>{d.source_name}</span>
                      </div>
                      <span className="domain-val">{d.percentage}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top Priority Action Card */}
              <div className="bento-panel-card" style={{ borderLeft: '3px solid var(--tier-critical)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600 }}>Top Intervention Order</span>
                  <span className="severity-pill critical">CPI 100.0</span>
                </div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#ededef', marginBottom: '4px' }}>
                  East Coast Park (ECP) Coastal Waters
                </div>
                <div style={{ fontSize: '11px', color: '#38bdf8', marginBottom: '8px' }}>
                  ⚡ Rapid Water-Borne Scavenger Vessel Intercept
                </div>
                <div style={{ fontSize: '10px', color: '#8a8f98', lineHeight: 1.5, marginBottom: '12px' }}>
                  Deploy MPA skimmer catamaran to intercept incoming floating plastic slick before shoreline stranding.
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="btn-primary-action" style={{ flex: 1, justifyContent: 'center' }} onClick={downloadIAP}>
                    📥 Download IAP
                  </button>
                  <button className="btn-locate-target" style={{ flex: 1 }} onClick={exportDispatchBriefText}>
                    📄 Field Brief
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

const rootElement = document.getElementById('root');
if (rootElement) {
  createRoot(rootElement).render(<App />);
}
