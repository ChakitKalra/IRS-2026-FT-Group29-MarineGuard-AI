// STEP 4: Check whether Earth Engine has currents for our image date.
// Never replace missing currents with old data and call it current.
var region = ee.Geometry.Rectangle([103.55, 1.10, 104.15, 1.50]);
var start = ee.Date('2026-10-01T00:00:00Z');
var end = start.advance(1, 'day');
var archive = ee.ImageCollection('HYCOM/sea_water_velocity');
var matching = archive.filterBounds(region).filterDate(start, end);
Map.centerObject(region, 10);
Map.addLayer(region, {color: 'blue'}, 'Current study area');
print('Requested day (UTC):', start);
print('Newest timestamp in HYCOM archive (UTC):',
  ee.Date(archive.aggregate_max('system:time_start')));
print('Matching current images:', matching.size());
matching.size().evaluate(function(count, error) {
  if (error) { print('Availability check failed:', error); return; }
  if (!count) {
    print('No matching currents. Obtain external current data for this date.');
    print('Do not use the archive’s old currents for an October 2026 prediction.');
    return;
  }
  // Apply the catalog scale factor to obtain surface velocity in m/s.
  var image = ee.Image(matching.sort('system:time_start').first());
  var velocity = image.select(['velocity_u_0', 'velocity_v_0']).multiply(0.001);
  print('Current timestamp (UTC):', image.date());
  print('Surface velocity image (east/north, m/s):', velocity);
  print('HYCOM grid is about 9 km; narrow coastal channels need finer data.');
});
