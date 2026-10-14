# Step 5 — tides and tidal currents

Use [MPA tidal information](https://www.mpa.gov.sg/port-marine-ops/marine-services/charts-tidal-info-atons-and-hydrography/tidal-information) and [Singapore Tide Tables](https://www.mpa.gov.sg/who-we-are/newsroom-resources/publications/singapore-tide-tables) to identify suitable local stations and predictions.

Runnable first source: `05_tides.py` retrieves Open-Meteo modelled sea level and combined surface currents. Run `python3 weather/05_tides.py` from the project folder. Default: 1 October 2026, southern-water point (1.20, 103.85). Outputs go to `weather/data/`. MPA station data remains a separate validation source, not connected by this script.

- Tide height: water level in metres, with the source's vertical datum.
- Tidal current: horizontal speed and direction; needed for debris movement.
- Preserve station coordinates, source, timezone and valid timestamp.
- Convert Singapore time (UTC+8) to UTC before matching satellite and wind data.

Tide height alone cannot supply a current vector. Station values also do not describe every channel around Singapore.

The API sea level uses global mean sea level, not a local station datum. Its currents already include wave and tidal contributions. Its roughly 8-km model grid is a first regional input, not detailed channel flow. Missing/unavailable dates are reported rather than replaced.
