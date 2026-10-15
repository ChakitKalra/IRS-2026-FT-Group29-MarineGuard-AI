"""Check downloaded or Drive-synced Earth Engine GeoTIFF tiles."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import rasterio

from backend.earth_engine.imagery import SENTINEL2_BANDS
from backend.earth_engine.tiling import OUTPUT_CRS, PIXEL_SIZE_METERS, TILE_PIXELS


def verify_tile(path: Path) -> list[str]:
    issues = []
    try:
        with rasterio.open(path) as raster:
            if raster.count != len(SENTINEL2_BANDS):
                issues.append(f"expected 11 bands, found {raster.count}")
            if (raster.height, raster.width) != (TILE_PIXELS, TILE_PIXELS):
                issues.append(f"expected 256x256 pixels, found {raster.width}x{raster.height}")
            if raster.crs is None or raster.crs.to_string() != OUTPUT_CRS:
                issues.append(f"expected {OUTPUT_CRS}, found {raster.crs}")
            if not np.isclose(abs(raster.transform.a), PIXEL_SIZE_METERS) or not np.isclose(
                abs(raster.transform.e), PIXEL_SIZE_METERS
            ):
                issues.append("pixel size is not 10 metres")
            if raster.count == len(SENTINEL2_BANDS) and (raster.height, raster.width) == (
                TILE_PIXELS,
                TILE_PIXELS,
            ):
                valid = raster.read(1, masked=True).compressed()
                if valid.size == 0:
                    issues.append("tile contains no valid pixels")
                elif not np.isfinite(valid).all():
                    issues.append("tile contains NaN or infinite reflectance")
    except Exception as exc:
        issues.append(f"could not read GeoTIFF: {exc}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Folder containing downloaded .tif tiles")
    args = parser.parse_args()
    files = sorted(args.directory.glob("*.tif")) + sorted(args.directory.glob("*.tiff"))
    if not files:
        print(f"No GeoTIFF tiles found in {args.directory}")
        return 1

    failed = 0
    for path in files:
        issues = verify_tile(path)
        if issues:
            failed += 1
            print(f"FAIL {path.name}: {'; '.join(issues)}")
        else:
            print(f"OK   {path.name}: 11 bands, 256x256, 10 m, {OUTPUT_CRS}")
    print(f"Checked {len(files)} tile(s); {len(files) - failed} passed, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
