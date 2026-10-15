"""HTTP endpoint for previewing MARIDA model predictions on one tile."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException, Query, Request
from PIL import Image
from rasterio.warp import transform_bounds

from backend.marida.prediction import DEFAULT_MODEL_PATH, predict_tile

router = APIRouter(prefix="/api/predictions", tags=["predictions"])
MAX_TILE_BYTES = 20 * 1024 * 1024


@router.post("/tile")
async def predict_uploaded_tile(
    request: Request,
    filename: str = Query(min_length=1, max_length=200),
):
    """Accept one downloaded GeoTIFF and return its debris layer and map bounds."""
    if Path(filename).suffix.lower() not in {".tif", ".tiff"}:
        raise HTTPException(status_code=415, detail="Upload one GeoTIFF tile (.tif or .tiff).")
    if not DEFAULT_MODEL_PATH.is_file():
        raise HTTPException(status_code=503, detail="The MARIDA RF model checkpoint is missing.")
    declared_size = request.headers.get("content-length")
    if declared_size and int(declared_size) > MAX_TILE_BYTES:
        raise HTTPException(status_code=413, detail="Tile is larger than the 20 MB upload limit.")
    content = await request.body()
    if len(content) > MAX_TILE_BYTES:
        raise HTTPException(status_code=413, detail="Tile is larger than the 20 MB upload limit.")

    try:
        with TemporaryDirectory(prefix="marineguard-prediction-") as temp_dir:
            tile_path = Path(temp_dir) / Path(filename).name
            mask_path = Path(temp_dir) / "debris_mask.tif"
            tile_path.write_bytes(content)
            summary = predict_tile(tile_path, mask_path)
            with rasterio.open(mask_path) as raster:
                mask = raster.read(1)
                bounds = transform_bounds(raster.crs, "EPSG:4326", *raster.bounds, densify_pts=21)

        rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
        rgba[mask == 1] = (255, 91, 83, 190)
        image_buffer = BytesIO()
        Image.fromarray(rgba, mode="RGBA").save(image_buffer, format="PNG", optimize=True)
        png_data = base64.b64encode(image_buffer.getvalue()).decode("ascii")
        west, south, east, north = bounds
        return {
            "status": "experimental_prediction",
            "model": "MARIDA RF-SS+SI",
            "possible_debris_pixels": summary.possible_debris_pixels,
            "valid_pixels": summary.valid_pixels,
            "possible_debris_percent": round(summary.possible_debris_percent, 3),
            "overlay_data_url": f"data:image/png;base64,{png_data}",
            "bounds": [[south, west], [north, east]],
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process this tile: {exc}") from exc
