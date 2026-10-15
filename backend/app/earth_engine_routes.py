"""HTTP endpoints for starting and checking Earth Engine tile exports."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from backend.earth_engine.auth import EarthEngineSetupError, initialize_earth_engine
from backend.earth_engine.imagery import (
    SENTINEL2_BANDS,
    NoImageryError,
    build_sentinel2_composite,
)
from backend.earth_engine.tiling import (
    DEFAULT_DRIVE_FOLDER,
    DEFAULT_MAX_TILES,
    TileLimitError,
    grid_tiles,
    start_drive_exports,
    task_status,
)


router = APIRouter(prefix="/api/imagery", tags=["imagery"])


class PolygonInput(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    # GeoJSON order: [longitude, latitude]. The first ring is the outer boundary.
    coordinates: list[list[tuple[float, float]]] = Field(min_length=1, max_length=1)

    @model_validator(mode="after")
    def validate_outer_ring(self):
        ring = self.coordinates[0]
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError("Polygon outer ring must have at least 3 points and be closed.")
        for longitude, latitude in ring:
            if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                raise ValueError("Polygon coordinates must be [longitude, latitude] in degrees.")
        if len(set(ring[:-1])) < 3:
            raise ValueError("Polygon needs at least 3 distinct corner points.")
        return self


class PrepareImageryRequest(BaseModel):
    polygon: PolygonInput
    start_date: date
    end_date: date
    max_scene_cloud_percent: float = Field(default=80.0, ge=0, le=100)
    drive_folder: str = Field(default=DEFAULT_DRIVE_FOLDER, min_length=1, max_length=100)
    max_tiles: int = Field(default=DEFAULT_MAX_TILES, ge=1, le=DEFAULT_MAX_TILES)

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be later than start_date (the end date is exclusive).")
        return self


@router.post("/prepare")
def prepare_imagery(request: PrepareImageryRequest):
    """Search, mask, composite, grid, and queue Drive exports for a polygon."""
    try:
        ee = initialize_earth_engine()
        region = ee.Geometry.Polygon(request.polygon.coordinates)
        image, scene_count = build_sentinel2_composite(
            ee,
            region,
            request.start_date,
            request.end_date,
            request.max_scene_cloud_percent,
        )
        tiles = grid_tiles(ee, region, request.max_tiles)
        if not tiles:
            raise NoImageryError("The selected polygon does not intersect any export tiles.")
        # This RGB rendering lets the frontend display the same processed
        # composite while the full 11-band GeoTIFF tiles export to Drive.
        preview_url = image.getThumbURL(
            {
                "region": region,
                "dimensions": "900x600",
                "format": "png",
                "bands": ["B4", "B3", "B2"],
                "min": 0,
                "max": 0.3,
                "gamma": 1.2,
            }
        )
        tasks = start_drive_exports(ee, image, tiles, request.drive_folder)
    except EarthEngineSetupError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (NoImageryError, TileLimitError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Earth Engine could not create the exports. Check authentication, project access, and task limits.",
        ) from exc

    failed_count = sum(task["state"] == "FAILED_TO_START" for task in tasks)
    return {
        "status": "exports_partial" if failed_count else "exports_started",
        "collection": "COPERNICUS/S2_SR_HARMONIZED",
        "scene_count": scene_count,
        "bands": list(SENTINEL2_BANDS),
        "pixel_size_m": 10,
        "tile_size_pixels": 256,
        "tile_count": len(tasks),
        "preview_url": preview_url,
        "preview_bands": ["B4", "B3", "B2"],
        "started_count": len(tasks) - failed_count,
        "failed_to_start_count": failed_count,
        "drive_folder": request.drive_folder,
        "tasks": tasks,
    }


@router.get("/tasks/{task_id}")
def get_export_status(task_id: str):
    """Return the Earth Engine batch task state for an export."""
    try:
        ee = initialize_earth_engine()
        return task_status(ee, task_id)
    except EarthEngineSetupError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not read Earth Engine task status.") from exc
