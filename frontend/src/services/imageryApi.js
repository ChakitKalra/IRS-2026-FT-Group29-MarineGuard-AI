const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

async function request(path, options) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new Error('Cannot reach the backend. Start the MarineGuard API on port 8000.');
  }
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || 'Imagery request failed.');
  return body;
}

export function prepareImagery({ polygon, start_date, end_date }) {
  const closedRing = polygon.map(([lat, lon]) => [lon, lat]);
  closedRing.push(closedRing[0]);
  return request('/api/imagery/prepare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ polygon: { type: 'Polygon', coordinates: [closedRing] }, start_date, end_date }),
  });
}

export function getImageryTask(taskId) {
  return request(`/api/imagery/tasks/${encodeURIComponent(taskId)}`);
}

export async function predictTile(file) {
  const url = `${API_URL}/api/predictions/tile?filename=${encodeURIComponent(file.name)}`;
  let response;
  try {
    response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file });
  } catch {
    throw new Error('Cannot reach the backend. Start the MarineGuard API on port 8000.');
  }
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || 'Tile prediction failed.');
  return body;
}
