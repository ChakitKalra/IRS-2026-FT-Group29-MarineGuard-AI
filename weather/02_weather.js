// STEP 2: Inspect GFS weather valid on the satellite image's UTC day.
// Standalone script: paste the complete file into Earth Engine.
var region = ee.Geometry.Rectangle([103.55, 1.10, 104.15, 1.50]);
var start = ee.Date('2026-10-01T00:00:00Z');
var end = start.advance(1, 'day');

// Use only model runs created on/before the requested start time.
// GFS is model output, not a local weather-station measurement.
var runs = ee.ImageCollection('NOAA/GFS0P25')
  .filter(ee.Filter.gte('creation_time', start.advance(-3, 'day').millis()))
  .filter(ee.Filter.lte('creation_time', start.millis()));
Map.centerObject(region, 10);

runs.size().evaluate(function(count, error) {
  if (error) { print('Could not fetch weather:', error); return; }
  if (!count) { print('No model run found for this date.'); return; }
  var runTime = runs.aggregate_max('creation_time');
  var forecasts = runs.filter(ee.Filter.eq('creation_time', runTime))
    .filter(ee.Filter.gte('forecast_time', start.millis()))
    .filter(ee.Filter.lt('forecast_time', end.millis()))
    .sort('forecast_time');

  forecasts.size().evaluate(function(n, err) {
    if (err) { print('Could not fetch forecasts:', err); return; }
    if (!n) { print('No forecasts valid in this time window.'); return; }
    // Display the first forecast valid within the day, not a daily average.
    var image = ee.Image(forecasts.first());
    var weather = image.select([
      'temperature_2m_above_ground',
      'relative_humidity_2m_above_ground'
    ]);
    print('Model run created (UTC):', ee.Date(runTime));
    print('Forecast valid (UTC):', ee.Date(image.get('forecast_time')));
    print('Region averages: temperature (°C), humidity (%):',
      weather.reduceRegion({
        reducer: ee.Reducer.mean(), geometry: region,
        scale: 27830, maxPixels: 1e6
      }));
    Map.addLayer(weather.select('temperature_2m_above_ground').clip(region),
      {min: 24, max: 34, palette: ['blue', 'yellow', 'red']},
      'GFS temperature (°C)');
    print('GFS grid is about 28 km: broad regional context only.');
  });
});
