// STEP 1: Define where and when to collect weather data.
// Paste this complete file into the Google Earth Engine Code Editor.

// Use the same study rectangle as 06_whole_singapore.
// Order: west longitude, south latitude, east longitude, north latitude.
// Includes nearby foreign waters; this is not a maritime boundary.
var region = ee.Geometry.Rectangle([103.55, 1.10, 104.15, 1.50]);

// Your selected satellite imagery was captured on 1 October 2026.
// Start with that UTC day. Later, match the actual capture time
// of each satellite tile before calculating debris movement.
var start = ee.Date('2026-10-01T00:00:00Z');
var end = start.advance(1, 'day');

// Display the weather study area and requested time window.
Map.centerObject(region, 10);
Map.addLayer(region, {color: 'blue'}, 'Weather study area');
print('Start (UTC):', start);
print('End (UTC, excluded):', end);
print('Next step: fetch weather and wind for this time window.');
