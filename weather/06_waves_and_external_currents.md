# Step 6 — external currents and waves

Earth Engine's HYCOM archive does not cover our October 2026 imagery. Inspect [Copernicus Marine Global Ocean Physics](https://data.marine.copernicus.eu/product/GLOBAL_ANALYSISFORECAST_PHY_001_024/description) for matching current data; verify historical availability before downloading.

Its SMOC dataset includes combined surface-current contributions from circulation, tides and wave drift. If used, do not add the same tide/wave contributions again.

Needed inputs: spatial east/north surface velocities in m/s, UTC validity times, coordinates, source and model run time. Wave height alone is not a wave-drift vector.

Runnable first source: `python3 weather/06_waves.py` retrieves wave height, direction and period via Open-Meteo. Step 5 retrieves combined surface currents through the same provider. Default date/point matches step 5; outputs go to `weather/data/`. These are point samples, not full-area fields. Direct Copernicus downloads are not implemented.

Wave direction is where waves come FROM; current direction is where flow goes TOWARDS. Preserve units and validity times. The endpoint does not expose the original model run time, so these outputs cannot establish what forecasts were available at the satellite capture time.
