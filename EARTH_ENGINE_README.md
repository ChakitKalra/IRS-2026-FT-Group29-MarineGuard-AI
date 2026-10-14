# Singapore water imagery — Earth Engine

Purpose: prepare satellite imagery as input for marine debris detection.

## Scripts

| File | Purpose |
| --- | --- |
| `01_region` | Define Singapore and nearby waters. |
| `02_imagery` | Find recent Sentinel-2 images. |
| `03_preprocessing` | Mask clouds and combine tiles from the same date. |
| `04_coastal_water` | Focus on southern Singapore Strait waters and exclude mapped land. |
| `05_area_math` | Estimate total, usable and unavailable water areas. |
| `06_whole_singapore` | Repeat the water analysis across the larger study area. |

Each script runs independently in the Earth Engine Code Editor. Paste its complete code, then click **Save → Run**.

## Latest larger-area result

- Study rectangle: `[103.55, 1.10, 104.15, 1.50]` (west, south, east, north).
- Capture date: **1 October 2026 (UTC)**.
- Total mapped water: **1,572.51 km²**.
- Usable: **1,381.73 km² (87.87%)**; unavailable: **190.78 km²**.

Coverage = usable mapped water area ÷ total mapped water area × 100.

## Limits and next step

Sentinel-2 imagery is searched over the last 30 days; the newest date with at least 50% usable water is selected. Land is excluded using ESA WorldCover 2021. Areas are estimates on a 100-metre calculation grid; haze and missed clouds may remain. The rectangle includes neighbouring waters and is not an official maritime boundary.

Next: export imagery and its valid-pixel mask for a debris model. Training and accuracy testing require separate labelled data; these scripts do not detect debris or predict drift.
