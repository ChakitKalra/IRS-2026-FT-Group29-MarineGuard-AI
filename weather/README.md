# Weather inputs for Singapore debris analysis

Work through one script at a time in the [Earth Engine Code Editor](https://code.earthengine.google.com/). Paste the complete file, then click **Save → Run**.

## Step 1 — region and time

`01_region_and_time.js` defines the same larger Singapore study rectangle as the imagery workflow and selects **1 October 2026 (UTC)**. Expected result: a blue region on the map and start/end dates in the Console. It does not fetch weather yet.

## Files — follow in order

| File | Purpose |
| --- | --- |
| `01_region_and_time.js` | Define the area and UTC day. |
| `02_weather.js` | Display GFS temperature and humidity for the first valid forecast. |
| `03_wind.js` | Build wind-component time series; optionally export through Tasks. |
| `04_current_availability.js` | Check matching HYCOM availability; do not substitute old data. |
| `05_tides.py` | Retrieve modelled sea level and combined surface currents at a marine point. |
| `06_waves.py` | Retrieve wave height, direction and period at that same point. |

Each `.js` script is independent and includes its own area/date settings. The `.md` files are notes, not runnable Earth Engine scripts. Weather uses one GFS run created on/before the requested day; forecast validity and run times are printed separately. Its roughly 28-km grid gives regional context, not detailed coastal conditions. Match environmental data to actual satellite capture times before predicting drift; the current day window is only a starting point.

Scripts were checked for JavaScript syntax locally, but have not been run in an authenticated Earth Engine session. No debris movement prediction is implemented yet.

## Run steps 5 and 6 locally

These are Python scripts, not Earth Engine scripts. They use Python's standard library; no installation or API key is needed for the public noncommercial endpoint.

From the project folder:

```sh
python3 weather/05_tides.py
python3 weather/06_waves.py
```

Both default to **1 October 2026 (UTC)** at **1.20°N, 103.85°E**. Change a date or location with `--date YYYY-MM-DD --latitude 1.20 --longitude 103.85`. JSON files are saved in `weather/data/`, including units, timestamps, returned grid location and provenance. The helper is `marine_fetch.py`; the two Markdown notes explain interpretation.

They request [Open-Meteo marine data](https://open-meteo.com/en/docs/marine-weather-api). If a date or variable is unavailable, the scripts stop rather than substitute another day. Combined currents already contain tidal/wave contributions. Point data does not cover the whole region; a spatial grid and validation are still needed. Forecast run provenance is unavailable through this endpoint.

Verification: both API requests reached the provider, but all requested values were null for **1 October 2026 at (1.20, 103.85)**. Neither script saved a data file. Python syntax checks passed. A source supplying this date/location is still needed before drift modelling.

Sources: [GFS weather](https://developers.google.com/earth-engine/datasets/catalog/NOAA_GFS0P25), [HYCOM currents](https://developers.google.com/earth-engine/datasets/catalog/HYCOM_sea_water_velocity), [MPA tidal information](https://www.mpa.gov.sg/port-marine-ops/marine-services/charts-tidal-info-atons-and-hydrography/tidal-information).

Earth Engine's HYCOM archive currently ends in September 2024, so it cannot supply currents for our October 2026 imagery. A matching external current source will be needed.
