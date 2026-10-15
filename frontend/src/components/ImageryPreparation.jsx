import React, { useEffect, useState } from 'react';
import { getImageryTask, predictTile, prepareImagery } from '../services/imageryApi';

function dayString(date) {
  return date.toISOString().slice(0, 10);
}

export default function ImageryPreparation({ polygon, onPrediction }) {
  const today = new Date();
  const [endDate, setEndDate] = useState(dayString(today));
  const [startDate, setStartDate] = useState(dayString(new Date(today.getTime() - 30 * 86400000)));
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [tileFile, setTileFile] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [predictionError, setPredictionError] = useState('');
  const [predicting, setPredicting] = useState(false);
  const [overlayVisible, setOverlayVisible] = useState(true);

  useEffect(() => {
    if (!result?.tasks?.some(task => task.task_id && ['READY', 'RUNNING', 'UNSUBMITTED'].includes(task.state))) return;
    const timer = setInterval(async () => {
      const active = result.tasks.filter(task => task.task_id && ['READY', 'RUNNING', 'UNSUBMITTED'].includes(task.state));
      const updates = await Promise.allSettled(active.map(task => getImageryTask(task.task_id)));
      setResult(current => {
        if (!current) return current;
        const byId = new Map(updates.filter(update => update.status === 'fulfilled').map(update => [update.value.task_id, update.value]));
        return { ...current, tasks: current.tasks.map(task => byId.has(task.task_id) ? { ...task, ...byId.get(task.task_id) } : task) };
      });
    }, 8000);
    return () => clearInterval(timer);
  }, [result]);

  async function submit(event) {
    event.preventDefault();
    setError(''); setResult(null); setPrediction(null); setPredictionError(''); setOverlayVisible(true); onPrediction?.(null); setLoading(true);
    try {
      setResult(await prepareImagery({ polygon, start_date: startDate, end_date: endDate }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const completed = result?.tasks?.filter(task => task.state === 'COMPLETED').length || 0;
  const active = result?.tasks?.filter(task => ['READY', 'RUNNING', 'UNSUBMITTED'].includes(task.state)).length || 0;
  async function runPrediction(event) {
    event.preventDefault();
    if (!tileFile) return;
    setPredictionError(''); setPredicting(true);
    try {
      const value = await predictTile(tileFile);
      setPrediction(value);
      setOverlayVisible(true);
      onPrediction?.({ url: value.overlay_data_url, bounds: value.bounds, visible: true });
    } catch (err) {
      setPredictionError(err.message);
    } finally {
      setPredicting(false);
    }
  }
  return <section className="imagery-panel" aria-labelledby="imagery-title">
    <div className="imagery-heading"><div><p className="eyebrow">EARTH ENGINE</p><h3 id="imagery-title">Prepare satellite imagery</h3></div><span className="imagery-badge">Drawn area</span></div>
    <p className="imagery-copy">Create a cloud-masked Sentinel‑2 composite and inspect its true-colour preview.</p>
    <form className="imagery-form" onSubmit={submit}>
      <label>Start date<input type="date" value={startDate} max={endDate} onChange={event => setStartDate(event.target.value)} required/></label>
      <label>End date<input type="date" value={endDate} min={startDate} onChange={event => setEndDate(event.target.value)} required/></label>
      <button className="reset active" type="submit" disabled={loading}>{loading ? 'Preparing…' : 'Prepare imagery'}</button>
    </form>
    {error && <p className="imagery-error" role="alert">{error}</p>}
    {result && <div className="imagery-result">
      <div className="imagery-summary"><strong>{result.scene_count} scenes</strong><span>{result.tile_count} export tiles</span><span>{completed} completed{active ? ` · ${active} in progress` : ''}</span></div>
      {result.preview_url && <figure className="imagery-preview"><img src={result.preview_url} alt="Cloud-masked Sentinel-2 true-colour composite of the selected coastal area"/><figcaption>Processed composite preview · RGB bands B4, B3, B2 · {result.collection}</figcaption></figure>}
      <div className="task-list" aria-label="Tile export status">{result.tasks.map(task => <div key={task.task_id || task.tile_id}><span>{task.tile_id}</span><span className={task.state === 'COMPLETED' ? 'task-done' : ''}>{task.state.replaceAll('_', ' ')}</span></div>)}</div>
      <p className="imagery-note">The preview shows the processed RGB composite. Drive tiles contain the full 11-band data used for model input.</p>
      <div className="prediction-workflow">
        <h4>Mark possible debris pixels</h4>
        <p>Download one completed tile from Drive, then upload it here to run the MARIDA model.</p>
        <form className="prediction-form" onSubmit={runPrediction}>
          <label>Downloaded GeoTIFF tile<input type="file" accept=".tif,.tiff,image/tiff" onChange={event => setTileFile(event.target.files?.[0] || null)} /></label>
          <button className="reset active" type="submit" disabled={!tileFile || !completed || predicting}>{predicting ? 'Checking pixels…' : 'Mark possible debris'}</button>
        </form>
        {!completed && <p className="imagery-note">Wait for an export tile to finish before uploading it.</p>}
        {predictionError && <p className="imagery-error" role="alert">{predictionError}</p>}
        {prediction && <div className="prediction-result">
          <strong>{prediction.possible_debris_pixels.toLocaleString()} pixels marked</strong>
          <span>{prediction.possible_debris_percent}% of usable tile pixels · MARIDA model</span>
          <button className="reset" type="button" onClick={() => { const visible = !overlayVisible; setOverlayVisible(visible); onPrediction?.({ url: prediction.overlay_data_url, bounds: prediction.bounds, visible }); }}>{overlayVisible ? 'Hide map layer' : 'Show map layer'}</button>
          <p>Experimental preview: this model has not been validated on Singapore observations.</p>
        </div>}
      </div>
    </div>}
  </section>;
}
