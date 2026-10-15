"""Prepare Earth Engine GeoTIFF tiles for the MARIDA RF-SS+SI model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio

from backend.earth_engine.imagery import SENTINEL2_BANDS
from backend.marida.features import ss_si_features


@dataclass(frozen=True)
class PreparedTile:
    """Per-pixel model inputs and spatial metadata for one satellite tile."""

    features: np.ndarray  # (height * width, 19): 11 bands + 8 indices
    valid_pixels: np.ndarray  # (height, width); False means masked or invalid
    profile: dict  # GeoTIFF metadata for writing a prediction map later


def prepare_tile_for_rf(tile_path: str | Path) -> PreparedTile:
    """Read an 11-band reflectance tile and build the RF's 19 input features.

    The tile must use the same Sentinel-2 band order and reflectance scale as
    the MARIDA training images. Invalid and masked pixels are retained in the
    returned feature array but marked False in ``valid_pixels`` so inference
    can skip them and later restore the map's geospatial layout.
    """
    path = Path(tile_path)
    with rasterio.open(path) as raster:
        if raster.count != len(SENTINEL2_BANDS):
            raise ValueError(
                f"Expected {len(SENTINEL2_BANDS)} Sentinel-2 bands in {path.name}; "
                f"found {raster.count}."
            )
        image = raster.read(out_dtype="float32")
        valid_pixels = raster.dataset_mask() > 0
        profile = raster.profile.copy()

    feature_cube = ss_si_features(image)
    valid_pixels &= np.isfinite(feature_cube).all(axis=0)
    feature_rows = np.moveaxis(feature_cube, 0, -1).reshape(-1, feature_cube.shape[0])
    return PreparedTile(
        features=feature_rows,
        valid_pixels=valid_pixels,
        profile=profile,
    )
