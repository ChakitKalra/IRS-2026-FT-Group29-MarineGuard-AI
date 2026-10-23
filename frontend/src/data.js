import detectedData from './detected_hotspots.json';
import liveWeather from './live_weather_currents.json';
import forecastData from './drift_forecasts.json';

export const areas = [
  { id: 'all', name: 'Singapore coast', center: [1.32, 103.86], zoom: 11 },
  { id: 'east', name: 'East Coast', center: [1.303, 103.933], zoom: 13 },
  { id: 'pasir', name: 'Pasir Ris', center: [1.383, 103.953], zoom: 13 },
  { id: 'south', name: 'Southern coast', center: [1.265, 103.818], zoom: 13 },
];

// Fictional observations for demo mode
export const tiles = [
  { id: 'MG-001', area: 'east', name: 'East Coast shoreline', lat: 1.303, lng: 103.929, label: 'Marine debris', confidence: 87, severity: 'High', source: 'Simulated' },
  { id: 'MG-002', area: 'east', name: 'Bedok coastal waters', lat: 1.311, lng: 103.950, label: 'Natural organic material', confidence: 74, severity: 'Medium', source: 'Simulated' },
  { id: 'MG-003', area: 'pasir', name: 'Pasir Ris beach', lat: 1.381, lng: 103.953, label: 'Marine debris', confidence: 82, severity: 'High', source: 'Simulated' },
  { id: 'MG-004', area: 'pasir', name: 'Eastern coastal waters', lat: 1.386, lng: 103.966, label: 'Foam', confidence: 69, severity: 'Low', source: 'Simulated' },
  { id: 'MG-005', area: 'south', name: 'Labrador coast', lat: 1.263, lng: 103.802, label: 'Marine debris', confidence: 76, severity: 'Medium', source: 'Simulated' },
  { id: 'MG-006', area: 'south', name: 'Sentosa coastal waters', lat: 1.250, lng: 103.831, label: 'Natural organic material', confidence: 79, severity: 'Low', source: 'Simulated' },
];

export const colors = {
  'Marine debris': '#ff806f',
  'Marine debris slick': '#ff6b57',
  'Plastic bottles & fragments': '#ff9f43',
  'Styrofoam & food containers': '#ffd32a',
  'Can & beverage packaging': '#0abde3',
  'Natural organic material': '#e6b96c',
  'Foam': '#9cd6ee',
  'Beached Accumulation': '#ff4757',
  'Floating Plume': '#ffa502',
};

// Map sector IDs from backend clustering to frontend area filter IDs
const sectorToAreaMap = {
  east_coast: 'east',
  pasir_ris_changi: 'pasir',
  southern_islands: 'south',
  jurong_tuas: 'south',
  johor_strait_north: 'pasir',
  singapore_strait_deep: 'east',
};

// Transform verified Phase 1 outputs into tile observations for the UI
export const phase1Tiles = (detectedData?.hotspots || []).map((hs) => {
  const primaryItem = Object.keys(hs.item_breakdown || {})[0] || 'Marine debris';
  return {
    id: hs.hotspot_id,
    area: sectorToAreaMap[hs.sector_id] || 'east',
    name: hs.name,
    lat: hs.centroid_lat,
    lng: hs.centroid_lng,
    label: primaryItem,
    confidence: hs.composite_confidence,
    severity: hs.severity,
    source: (hs.sources || []).join(' + '),
    radius_meters: hs.radius_meters,
    detection_count: hs.detection_count,
    total_area_sq_m: hs.total_area_sq_m,
    item_breakdown: hs.item_breakdown,
    detection_ids: hs.detection_ids,
  };
});

// Extract any Sentinel-2 polygon geometries for overlay rendering
export const phase1Polygons = (detectedData?.satellite_polygons?.features || [])
  .filter((f) => f.geometry && f.geometry.type === 'Polygon')
  .map((f) => {
    // GeoJSON is [lng, lat], Leaflet Polygon expects [lat, lng]
    const coords = (f.geometry.coordinates[0] || []).map(([lng, lat]) => [lat, lng]);
    return {
      id: f.id,
      coordinates: coords,
      properties: f.properties,
    };
  });

// Live Phase 2 Environmental Data
export const liveWeatherData = liveWeather;

// Phase 3 Multi-Horizon Lagrangian Drift Forecasts
export const driftForecasts = forecastData;

// Phase 4 Probabilistic Source Attribution & Reverse Backtracking
import attributionData from './source_attribution.json';
export const sourceAttributionData = attributionData;

// Transform source domain polygons for Leaflet ([lng, lat] -> [lat, lng])
export const sourceDomainPolygons = (attributionData?.geojson_layers?.source_domains?.features || [])
  .filter((f) => f.geometry && f.geometry.type === 'Polygon')
  .map((f) => {
    const coords = (f.geometry.coordinates[0] || []).map(([lng, lat]) => [lat, lng]);
    return {
      id: f.properties?.id,
      name: f.properties?.name,
      category: f.properties?.category,
      color: f.properties?.color || '#f59e0b',
      description: f.properties?.description,
      baseline_prior: f.properties?.baseline_prior,
      coordinates: coords,
    };
  });

// Transform reverse backtracking trajectories for Leaflet
export const backtrackingTrajectories = (attributionData?.geojson_layers?.backtracking_trajectories?.features || [])
  .filter((f) => f.geometry && f.geometry.type === 'LineString')
  .map((f) => {
    const coords = (f.geometry.coordinates || []).map(([lng, lat]) => [lat, lng]);
    return {
      hotspot_id: f.properties?.hotspot_id,
      hotspot_name: f.properties?.hotspot_name,
      dominant_source_name: f.properties?.dominant_source_name,
      color: f.properties?.color || '#00d2d3',
      release_hours_ago: f.properties?.release_hours_ago,
      coordinates: coords,
    };
  });

// Transform estimated origin markers for Leaflet
export const estimatedOriginMarkers = (attributionData?.geojson_layers?.origin_markers?.features || [])
  .filter((f) => f.geometry && f.geometry.type === 'Point')
  .map((f) => {
    const [lng, lat] = f.geometry.coordinates;
    return {
      hotspot_id: f.properties?.hotspot_id,
      hotspot_name: f.properties?.hotspot_name,
      dominant_source_id: f.properties?.dominant_source_id,
      dominant_source_name: f.properties?.dominant_source_name,
      color: f.properties?.color || '#f59e0b',
      release_hours_ago: f.properties?.release_hours_ago,
      lat,
      lng,
    };
  });

// Phase 5 Cleanup Decision Support & Resource Optimization
import cleanupData from './cleanup_recommendations.json';
export const cleanupDecisionData = cleanupData;

// Transform dispatch target coordinates for Leaflet map markers
export const dispatchTargetMarkers = (cleanupData?.geojson_dispatch_targets?.features || [])
  .filter((f) => f.geometry && f.geometry.type === 'Point')
  .map((f) => {
    const [lng, lat] = f.geometry.coordinates;
    return {
      order_id: f.properties?.order_id,
      hotspot_id: f.properties?.hotspot_id,
      hotspot_name: f.properties?.hotspot_name,
      cpi_score: f.properties?.cpi_score,
      priority_tier: f.properties?.priority_tier,
      intervention_type: f.properties?.intervention_type,
      assigned_assets: f.properties?.assigned_assets,
      recommended_crew_size: f.properties?.recommended_crew_size,
      optimal_window_hours: f.properties?.optimal_window_hours,
      expected_debris_mass_kg: f.properties?.expected_debris_mass_kg,
      stranding_prevention_likelihood_pct: f.properties?.stranding_prevention_likelihood_pct,
      lat,
      lng,
    };
  });
