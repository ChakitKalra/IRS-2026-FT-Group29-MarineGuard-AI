// STEP 3: Build a wind time series from one GFS model run.
// Each row preserves forecast validity time and model creation time.
var region = ee.Geometry.Rectangle([103.55, 1.10, 104.15, 1.50]);
var start = ee.Date('2026-10-01T00:00:00Z');
var end = start.advance(1, 'day');
var runs = ee.ImageCollection('NOAA/GFS0P25')
  .filter(ee.Filter.gte('creation_time', start.advance(-3, 'day').millis()))
  .filter(ee.Filter.lte('creation_time', start.millis()));
Map.centerObject(region, 10);

runs.size().evaluate(function(count, error) {
  if (error) { print('Could not fetch wind:', error); return; }
  if (!count) { print('No model run found for this date.'); return; }
  var runTime = runs.aggregate_max('creation_time');
  var forecasts = runs.filter(ee.Filter.eq('creation_time', runTime))
    .filter(ee.Filter.gte('forecast_time', start.millis()))
    .filter(ee.Filter.lt('forecast_time', end.millis()))
    .sort('forecast_time');

  forecasts.size().evaluate(function(n, err) {
    if (err) { print('Could not fetch forecasts:', err); return; }
    if (!n) { print('No wind forecasts valid in this window.'); return; }

    // u is eastward wind; v is northward wind. Both use metres/second.
    // Keep components: drift calculations need direction as well as speed.
    function windBands(image) {
      var u = image.select('u_component_of_wind_10m_above_ground').rename('u_m_s');
      var v = image.select('v_component_of_wind_10m_above_ground').rename('v_m_s');
      var speed = u.pow(2).add(v.pow(2)).sqrt().rename('speed_m_s');
      return u.addBands(v).addBands(speed);
    }

    // These are broad region averages, not spatial fields for a drift model.
    var table = ee.FeatureCollection(forecasts.toList(n).map(function(item) {
      var image = ee.Image(item);
      var averages = windBands(image).reduceRegion({
        reducer: ee.Reducer.mean(), geometry: region,
        scale: 27830, maxPixels: 1e6
      });
      return ee.Feature(null, averages).set({
        valid_time_utc: ee.Date(image.get('forecast_time')).format("YYYY-MM-dd'T'HH:mm:ss'Z'"),
        model_run_utc: ee.Date(runTime).format("YYYY-MM-dd'T'HH:mm:ss'Z'"),
        forecast_hours: image.get('forecast_hours')
      });
    }));
    print('Wind time series (m/s):', table);
    print('Positive u = east; positive v = north. Speed is mean pixel speed.');
    Map.addLayer(windBands(ee.Image(forecasts.first())).select('speed_m_s').clip(region),
      {min: 0, max: 15, palette: ['white', 'cyan', 'purple']}, 'First wind forecast (m/s)');

    // Run the export manually from the Tasks tab to save a CSV to Drive.
    Export.table.toDrive({
      collection: table, description: 'Singapore_wind_20261001',
      fileFormat: 'CSV',
      selectors: ['valid_time_utc', 'model_run_utc', 'forecast_hours',
        'u_m_s', 'v_m_s', 'speed_m_s']
    });
  });
});
