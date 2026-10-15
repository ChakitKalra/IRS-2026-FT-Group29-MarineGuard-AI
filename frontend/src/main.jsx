import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { MapContainer, TileLayer, CircleMarker, Popup, Polygon, Polyline, ImageOverlay, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './styles.css';
import { areas, tiles, colors } from './data';
import ImageryPreparation from './components/ImageryPreparation';

function MapPosition({ area, selected }) {
  const map = useMap();
  useEffect(() => { map.flyTo(selected ? [selected.lat, selected.lng] : area.center, selected ? 15 : area.zoom, { duration: 0.7 }); }, [area, selected, map]);
  return null;
}
function DrawClicks({ mode, onPoint, firstPoint, canClose, onClose, onHoverClose }) {
  const map = useMap();
  useMapEvents({
    click(e) {
      if (!mode) return;
      if (canClose && firstPoint) {
        const start = map.latLngToContainerPoint(firstPoint);
        const clicked = map.latLngToContainerPoint(e.latlng);
        if (start.distanceTo(clicked) <= 22) { onClose(); return; }
      }
      onPoint([e.latlng.lat, e.latlng.lng]);
    },
    mousemove(e) {
      const nearStart = Boolean(mode && canClose && firstPoint && map.latLngToContainerPoint(firstPoint).distanceTo(map.latLngToContainerPoint(e.latlng)) <= 26);
      onHoverClose(nearStart);
    },
  });
  return null;
}
function CoastalMap({ area, selected, visible, onSelect, drawMode, draftPoints, onDraftPoint, onClosePolygon, path, predictionOverlay }) {
  const [hoveringStart, setHoveringStart] = useState(false);
  return <MapContainer center={areas[0].center} zoom={11} scrollWheelZoom={false} doubleClickZoom={!drawMode} className={`coastal-map ${drawMode ? 'drawing' : ''}`} aria-label="Singapore coastal monitoring map">
    <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
    {predictionOverlay?.visible && <ImageOverlay url={predictionOverlay.url} bounds={predictionOverlay.bounds} opacity={0.9} />}
    <MapPosition area={area} selected={selected}/><DrawClicks mode={drawMode} onPoint={onDraftPoint} firstPoint={draftPoints[0]} canClose={draftPoints.length>=3} onClose={onClosePolygon} onHoverClose={setHoveringStart}/>
    {area.polygon&&<Polygon positions={area.polygon} pathOptions={{color:'#9bbcff',fillColor:'#7299ef',fillOpacity:.16,weight:2}} interactive={!drawMode}/>}
    {draftPoints.length>=2&&<Polyline positions={hoveringStart&&draftPoints.length>=3?[...draftPoints,draftPoints[0]]:draftPoints} pathOptions={{color:hoveringStart?'#ffffff':'#9bbcff',weight:hoveringStart?3:2,dashArray:'6 5'}} interactive={false}/>}
    {draftPoints.map((point,index)=><CircleMarker key={`draft-${index}`} center={point} radius={index===0&&hoveringStart?13:8} bubblingMouseEvents={false} pathOptions={{color:index===0&&hoveringStart?'#ffffff':'#09142c',fillColor:index===0&&hoveringStart?'#ffffff':'#a2c2ff',fillOpacity:1,weight:index===0&&hoveringStart?4:3}} interactive={index===0&&draftPoints.length>=3} eventHandlers={index===0&&draftPoints.length>=3?{mouseover:()=>setHoveringStart(true),mouseout:()=>setHoveringStart(false),click:event=>{event.originalEvent?.stopPropagation();onClosePolygon();}}:{}}><Popup>{index===0&&draftPoints.length>=3?'Click the highlighted starting point to close the polygon':`Point ${index+1}`}</Popup></CircleMarker>)}
    {path?.length>1&&<><Polyline positions={path} pathOptions={{color:'#ff9c75',weight:4,dashArray:'8 8'}}/>{path.slice(1).map((point,index)=><CircleMarker key={`path-${index}`} center={point} radius={index===path.length-2?8:5} pathOptions={{color:'#101831',fillColor:'#ffc28e',fillOpacity:1,weight:2}}><Popup>Illustrative position after {index===0?2:index===1?4:24} hours</Popup></CircleMarker>)}</>}
    {visible.map(tile => <CircleMarker key={tile.id} center={[tile.lat,tile.lng]} radius={selected?.id === tile.id ? 15 : 10} interactive={!drawMode} pathOptions={{ color: colors[tile.label], fillColor: colors[tile.label], fillOpacity: 0.8, weight: 3 }} eventHandlers={{click: () => onSelect(tile)}}>
      <Popup><strong>{tile.name}</strong><br/>{tile.label}<br/>Demo confidence: {tile.confidence}%<br/>Fictional observation</Popup>
    </CircleMarker>)}
  </MapContainer>;
}
const systemStages = [
  { number: '01', title: 'Data sources', tag: 'INPUTS', items: ['Sentinel-2 satellite imagery', 'MARIDA labelled examples', 'Currents, wind & field notes'] },
  { number: '02', title: 'Prepare imagery', tag: 'GOOGLE EARTH ENGINE', items: ['Select Singapore coast & dates', 'Mask clouds, derive bands / indices', 'Align inputs for analysis'] },
  { number: '03', title: 'Detect litter', tag: 'AI MODEL', items: ['Classify debris, foam & natural matter', 'Estimate confidence and location', 'Validate before relying on results'] },
  { number: '04', title: 'Estimate movement', tag: 'FORECAST', items: ['Combine detections with currents / wind', 'Project illustrative 2 / 4 / 24-hour paths', 'Identify possible accumulation areas'] },
  { number: '05', title: 'Explore the coast', tag: 'MARINEGUARD MAP', items: ['Choose a coastal area', 'Review detections and hotspots', 'Support monitoring and cleanup planning'] },
];
function StageIllustration({ index }) {
  const labels = ['Concept illustration of satellite imagery over a coast', 'Concept illustration of satellite image preprocessing', 'Concept illustration of marine litter detection boxes', 'Concept illustration of predicted debris movement over time', 'Concept illustration of a coastal monitoring map'];
  return <svg className={`stage-art stage-art-${index + 1}`} viewBox="0 0 320 112" role="img" aria-label={labels[index]}>
    <defs><linearGradient id={`sea-${index}`} x1="0" x2="1" y1="0" y2="1"><stop stopColor="#1d3b70"/><stop offset="1" stopColor="#102344"/></linearGradient><pattern id={`grid-${index}`} width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="#8fb7f5" strokeOpacity=".14" strokeWidth="1"/></pattern></defs>
    <rect width="320" height="112" rx="6" fill={`url(#sea-${index})`}/><rect width="320" height="112" rx="6" fill={`url(#grid-${index})`}/>
    {index===0&&<><path d="M0 77 Q55 54 105 72T210 68T320 55V112H0Z" fill="#2d6281" opacity=".7"/><path d="M0 88 Q52 69 103 85T212 81T320 68" fill="none" stroke="#90d5e6" strokeOpacity=".55" strokeWidth="2"/><path d="M228 14h28v16h-28zM219 18h9v8h-9zm37 0h9v8h-9zM238 30l-16 33m16-33 17 33" fill="none" stroke="#b7d4ff" strokeWidth="1.5"/><circle cx="240" cy="66" r="18" fill="#89bfff" opacity=".12"/><path d="M20 40h70M20 46h48" stroke="#9ac9eb" strokeOpacity=".5"/><text x="20" y="31" className="art-label">SENTINEL-2 · COASTAL PASS</text></>}
    {index===1&&<><g>{Array.from({length:20},(_,i)=><rect key={i} x={30+(i%5)*32} y={25+Math.floor(i/5)*16} width="25" height="11" rx="2" fill={['#4e8bc0','#6cc0d0','#294e85','#8bc9dc'][i%4]} opacity={i%6===0?.35:.82}/>)}</g><path d="M185 21h91v67h-91z" fill="#102344" stroke="#9dc6ed" strokeOpacity=".45"/><path d="M197 72l17-20 14 9 16-26 19 21" fill="none" stroke="#90d9df" strokeWidth="2"/><path d="M187 55h88" stroke="#d1eaff" strokeOpacity=".55" strokeDasharray="4 5"/><circle cx="248" cy="37" r="7" fill="#d9f2ff" fillOpacity=".3"/><text x="20" y="100" className="art-label">CLOUD MASK · SPECTRAL FEATURES</text></>}
    {index===2&&<><path d="M0 79 Q54 55 103 72T211 70T320 52V112H0Z" fill="#20546e"/><path d="M35 25h64v38H35zM174 42h54v37h-54zM246 18h44v31h-44z" fill="none" stroke="#ff9c81" strokeWidth="2"/><path d="M35 25h10m-10 0v10m54-10H89m10 0v10M174 42h10m-10 0v10m44-10h-10m10 0v10" stroke="#ffc19a" strokeWidth="2"/><circle cx="122" cy="61" r="5" fill="#a3d7ff"/><circle cx="152" cy="37" r="4" fill="#ffd58e"/><rect x="35" y="82" width="60" height="15" rx="3" fill="#132644"/><text x="42" y="92" className="art-label">DEBRIS · 0.87</text></>}
    {index===3&&<><path d="M18 18v72h284" fill="none" stroke="#8cb0de" strokeOpacity=".48"/><path d="M19 42h283M19 66h283" stroke="#8cb0de" strokeOpacity=".16"/><path d="M45 71C95 72 105 58 148 59S201 39 245 43 275 29 293 24" fill="none" stroke="#a4c8ff" strokeWidth="2.5" strokeDasharray="5 5"/><circle cx="45" cy="71" r="5" fill="#ffac88"/><circle cx="148" cy="59" r="5" fill="#b2d1ff"/><circle cx="245" cy="43" r="5" fill="#b2d1ff"/><circle cx="293" cy="24" r="5" fill="#83d3df"/><text x="31" y="101" className="art-label">NOW</text><text x="132" y="101" className="art-label">2H</text><text x="230" y="101" className="art-label">4H</text><text x="278" y="101" className="art-label">24H</text></>}
    {index===4&&<><path d="M0 78 Q55 52 98 72T189 65T320 62V112H0Z" fill="#27607a"/><path d="M0 78 Q55 52 98 72T189 65T320 62" fill="none" stroke="#83d3df" strokeWidth="2"/><path d="M54 83C103 67 129 95 175 72S230 64 268 38" fill="none" stroke="#b4ceff" strokeDasharray="5 5" strokeWidth="2"/><circle cx="54" cy="83" r="6" fill="#ff9581"/><circle cx="175" cy="72" r="5" fill="#ffbf88"/><circle cx="268" cy="38" r="5" fill="#9bcbff"/><rect x="214" y="15" width="83" height="18" rx="4" fill="#15294b" stroke="#90aee0" strokeOpacity=".5"/><text x="224" y="27" className="art-label">COASTAL VIEW</text><text x="23" y="103" className="art-label">DETECTIONS · AREAS · OUTLOOK</text></>}
  </svg>;
}
function SystemDesign() {
  return <section id="how-it-works" className="system-section" aria-labelledby="system-title">
    <div className="system-heading"><div><p className="eyebrow">SYSTEM DESIGN</p><h2 id="system-title">How MarineGuard AI works</h2></div><p>From satellite and ocean data to a coastal map.<br/>Follow the planned path through the system.</p></div>
    <div className="system-status"><span className="status-pulse"/> Planned architecture · backend and live data connections are still in development.</div>
    <div className="system-flow" aria-label="Planned system flow from data sources, through image preparation, litter detection and movement estimates, to the MarineGuard map.">
      {systemStages.map((stage,index)=><React.Fragment key={stage.number}>
        <article className="system-stage" style={{'--stage-index':index}}>
          <div className="stage-top"><span className="stage-number">{stage.number}</span><span className="stage-tag">{stage.tag}</span></div>
          <StageIllustration index={index}/>
          <h3>{stage.title}</h3><ul>{stage.items.map(item=><li key={item}>{item}</li>)}</ul>
        </article>
        {index<systemStages.length-1&&<span className="flow-arrow" aria-hidden="true"><span/></span>}
      </React.Fragment>)}
    </div>
    <div className="system-outputs"><div className="output-intro"><p className="eyebrow">WHAT COMES OUT</p><h3>Signals people can act on</h3></div><div className="output-card"><span className="output-icon detection-icon">●</span><div><strong>Detection layer</strong><small>Class · location · confidence</small></div></div><div className="output-card"><span className="output-icon drift-icon">↗</span><div><strong>Drift outlook</strong><small>2h · 4h · 24h scenarios</small></div></div><div className="output-card"><span className="output-icon map-icon">⌖</span><div><strong>Coastal map</strong><small>Area view · possible hotspots</small></div></div></div>
    <p className="system-footnote">The model layer is an experimental MARIDA preview; the sample observations remain fictional, and Singapore validation is still needed.</p>
  </section>;
}
function App() {
  const [drawnArea,setDrawnArea]=useState(null);
  const [areaId,setAreaId] = useState('all');
  const [areaName,setAreaName] = useState('');
  const [drawMode,setDrawMode]=useState(null), [draftPoints,setDraftPoints]=useState([]), [areaError,setAreaError]=useState('');
  const [timeView,setTimeView] = useState('current');
  const timeLabels = { current: 'Current state', '2': 'Expected in 2 hours', '4': 'Expected in 4 hours', '24': 'Expected in 24 hours' };
  const [selected,setSelected] = useState(null);
  const [predictionOverlay,setPredictionOverlay] = useState(null);
  const area = areaId==='__drawn__'&&drawnArea ? drawnArea : areas.find(a=>a.id===areaId)||areas[0];
  const visible = tiles.filter(t=>areaId==='all'||(area.polygon?insidePolygon([t.lat,t.lng],area.polygon):t.area===areaId));
  function selectArea(e){const value=e.target.value;setSelected(null);setAreaError('');if(value==='__draw_polygon__'){setAreaName('');setDrawMode('polygon');setDraftPoints([]);setAreaId('all');return;}setDrawMode(null);setDraftPoints([]);setAreaId(value||'all');if(value!=='__drawn__')setDrawnArea(null);}
  function finishDrawing(){if(draftPoints.length<3){setAreaError('Add at least 3 points on the map.');return;}const center=[draftPoints.reduce((s,p)=>s+p[0],0)/draftPoints.length,draftPoints.reduce((s,p)=>s+p[1],0)/draftPoints.length];setDrawnArea({id:'__drawn__',name:areaName.trim()||'Current drawn area',center,zoom:13,polygon:draftPoints});setAreaId('__drawn__');setDrawMode(null);setDraftPoints([]);setAreaError('');}
  function selectTime(e) { setTimeView(e.target.value); }
  const path = selected?.label === 'Marine debris' && timeView !== 'current' ? getDriftPath(selected, Number(timeView)) : null;
  function exportReport() {
    const report = { project: 'MarineGuard AI', data_status: 'Synthetic demonstration; not real detections', area: area.name, time_view: timeLabels[timeView], forecast_available: false, observations: visible };
    const url = URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
    const a=document.createElement('a'); a.href=url; a.download='marineguard-demo-report.json'; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  return <>
    <header className="nav"><a href="#" className="brand"><span className="brand-symbol">≈</span> MarineGuard<span className="ai">AI</span></a><nav aria-label="Main navigation"><a href="#explore">Explore coast</a><a href="#how-it-works">How it works</a><a href="#about">Our mission</a><span className="prototype">Research prototype</span></nav></header>
    <main>
      <section className="hero"><div className="hero-content"><p className="eyebrow">COASTAL INTELLIGENCE · SINGAPORE</p><h1>A clearer view.<br/>A cleaner coast.</h1><p className="intro">Explore marine litter across Singapore’s coast.<br/>Turn observations into better cleanup decisions.</p><a className="primary" href="#explore">Explore the coast <span>↗</span></a><p className="hero-note">Built for the waters we share.</p></div><div className="ocean" aria-hidden="true"><div className="orbit orbit-one"></div><div className="orbit orbit-two"></div><div className="ocean-label">1.3521° N &nbsp; 103.8198° E<br/><span>SINGAPORE STRAIT</span></div><div className="signal s1"></div><div className="signal s2"></div><div className="signal s3"></div></div></section>
      <section id="explore" className="explore"><div className="section-heading"><div><p className="eyebrow">EXPLORE THE COAST</p><h2>Every observation has a location.</h2></div><p>Choose an area. Explore the map.<br/>Inspect what’s happening along the coast.</p></div>
        <div className="demo-notice"><span className="notice-dot"></span> Demo mode — all observations, confidence scores, and severity levels below are fictional.{timeView!=='current'&&<span> Path preview is illustrative only; it does not use live currents or wind.</span>}</div>
        <div className="map-shell"><div className="map-toolbar"><div className="field"><label htmlFor="area">Choose an area</label><select id="area" value={drawMode?"__draw_polygon__":areaId==="all"?"":areaId} onChange={selectArea}><option value="">Select a place…</option><optgroup label="Named coastal areas">{[...areas].filter(a=>a.id!=="all").map(a=><option key={a.id} value={a.id}>{a.name}</option>)}</optgroup>{drawnArea&&<optgroup label="Your current polygon"><option value="__drawn__">{drawnArea.name}</option></optgroup>}<optgroup label="Custom area"><option value="__draw_polygon__">Draw a polygon…</option></optgroup></select></div><div className="field"><label htmlFor="time-view">Time view</label><select id="time-view" value={timeView} onChange={selectTime}>{Object.entries(timeLabels).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></div><div className="map-count"><strong>{visible.length}</strong> demo observations</div><button className="reset" onClick={()=>{setAreaId('all');setTimeView('current');setSelected(null);setDrawMode(null);setDraftPoints([]);setDrawnArea(null);setAreaError('');}}>Reset view ↺</button></div>
          {drawMode==='polygon'&&<div className="area-tools"><div className="area-entry"><input aria-label="Area name" placeholder="Name this area" value={areaName} onChange={e=>setAreaName(e.target.value)}/><span>{draftPoints.length} point{draftPoints.length===1?'':'s'} · Click on the map to add corners{draftPoints.length>=3?' or click the first point to close':''}.</span><button className="reset" disabled={!draftPoints.length} onClick={()=>setDraftPoints(v=>v.slice(0,-1))}>Undo last point</button><button className="reset active" disabled={draftPoints.length<3} onClick={finishDrawing}>Finish polygon</button><button className="reset" onClick={()=>{setDrawMode(null);setDraftPoints([]);setDrawnArea(null);setAreaError('');}}>Cancel</button></div>{areaError&&<p className="area-error">{areaError}</p>}</div>}<CoastalMap area={area} selected={selected} visible={visible} onSelect={setSelected} drawMode={drawMode} draftPoints={draftPoints} onDraftPoint={point=>setDraftPoints(v=>[...v,point])} onClosePolygon={finishDrawing} path={path} predictionOverlay={predictionOverlay}/>{areaId==='__drawn__'&&drawnArea&&<ImageryPreparation polygon={drawnArea.polygon} onPrediction={setPredictionOverlay}/ >}{path&&<p className="path-note">Dashed line shows a demo movement scenario for {selected.id} in the selected time window.</p>}{timeView!=='current'&&!path&&<p className="path-note">Select <b>Trace path</b> on a Marine debris observation to preview where it might drift.</p>}<div className="map-legend">{Object.entries(colors).map(([name,color])=><span key={name}><i style={{background:color}}></i>{name}</span>)}{predictionOverlay?.visible&&<span><i className="prediction-dot"></i>Possible debris · experimental</span>}<span className="map-hint">{drawMode?'Click map to add polygon corners':'Select a marker to inspect'}</span></div></div>
        <div className="results-heading"><h3>Coastal observations <span>{visible.length.toString().padStart(2,'0')}</span></h3><button className="text-button" onClick={exportReport}>Download demo report ↓</button></div>
        <div className="observations">{visible.map(tile=><article key={tile.id} className={`observation ${selected?.id===tile.id?'selected':''}`}><div className="tile-id"><i style={{background:colors[tile.label]}}></i>{tile.id}<span className={`severity ${tile.severity.toLowerCase()}`}>{tile.severity} · demo</span></div><h4>{tile.name}</h4><p>{tile.label}</p><div className="tile-meta"><span>{tile.lat.toFixed(3)}° N, {tile.lng.toFixed(3)}° E</span><span>{tile.confidence}% demo confidence</span></div><button onClick={()=>{setSelected(tile);if(tile.label==='Marine debris'&&timeView==='current')setTimeView('2');document.getElementById('explore').scrollIntoView({behavior:'smooth'});}}>{tile.label==='Marine debris'?'Trace path':'View on map'} <span>↗</span></button></article>)}</div>
        {visible.length===0 && <p className="empty">No demo observations fall inside this area. Try another area or draw a larger polygon.</p>}
      </section>
      <SystemDesign/>
      <section id="about" className="mission"><p className="eyebrow">OUR MISSION</p><h2>Understand the litter.<br/>Protect the coastline.</h2><p>MarineGuard AI is a student research project exploring how satellite imagery and environmental data can support marine litter detection, future accumulation forecasts, and cleanup planning in Singapore.</p><div className="mission-status">Current stage: Earth Engine imagery and experimental MARIDA pixel predictions are connected. Singapore validation is still needed.</div></section>
    </main><footer><a href="#" className="brand">MarineGuard<span className="ai">AI</span></a><span>Singapore coastal intelligence</span><span>Research prototype · 2026</span></footer>
  </>;
}
function getDriftPath(tile,horizon){const vectors={'MG-001':[0.00045,0.0008],'MG-003':[-0.00035,0.00075],'MG-005':[0.0004,-0.00075]};const [dLat,dLng]=vectors[tile.id]||[0.00035,0.00065];return [0,2,4,24].filter(hours=>hours<=horizon).map(hours=>[tile.lat+dLat*hours,tile.lng+dLng*hours]);}
function insidePolygon([lat,lng],p){let inside=false;for(let i=0,j=p.length-1;i<p.length;j=i++){const [yi,xi]=p[i],[yj,xj]=p[j];if(((xi>lng)!==(xj>lng))&&(lat<(yj-yi)*(lng-xi)/(xj-xi||Number.EPSILON)+yi))inside=!inside;}return inside;}
createRoot(document.getElementById('root')).render(<App/>);
