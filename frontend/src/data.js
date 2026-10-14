export const areas = [
  { id: 'all', name: 'Singapore coast', center: [1.32,103.86], zoom: 11 },
  { id: 'east', name: 'East Coast', center: [1.303,103.933], zoom: 13 },
  { id: 'pasir', name: 'Pasir Ris', center: [1.383,103.953], zoom: 13 },
  { id: 'south', name: 'Southern coast', center: [1.265,103.818], zoom: 13 },
];
// Fictional observations for frontend interaction only. No model inference involved.
export const tiles = [
  { id: 'MG-001', area: 'east', name: 'East Coast shoreline', lat: 1.303, lng: 103.929, label: 'Marine debris', confidence: 87, severity: 'High' },
  { id: 'MG-002', area: 'east', name: 'Bedok coastal waters', lat: 1.311, lng: 103.950, label: 'Natural organic material', confidence: 74, severity: 'Medium' },
  { id: 'MG-003', area: 'pasir', name: 'Pasir Ris beach', lat: 1.381, lng: 103.953, label: 'Marine debris', confidence: 82, severity: 'High' },
  { id: 'MG-004', area: 'pasir', name: 'Eastern coastal waters', lat: 1.386, lng: 103.966, label: 'Foam', confidence: 69, severity: 'Low' },
  { id: 'MG-005', area: 'south', name: 'Labrador coast', lat: 1.263, lng: 103.802, label: 'Marine debris', confidence: 76, severity: 'Medium' },
  { id: 'MG-006', area: 'south', name: 'Sentosa coastal waters', lat: 1.250, lng: 103.831, label: 'Natural organic material', confidence: 79, severity: 'Low' },
];
export const colors = { 'Marine debris': '#ff806f', 'Natural organic material': '#e6b96c', 'Foam': '#9cd6ee' };
