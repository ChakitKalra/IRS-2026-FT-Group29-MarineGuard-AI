"""Create aligned 256-by-256 image tiles and export them to Google Drive."""

from __future__ import annotations


TILE_PIXELS = 256
PIXEL_SIZE_METERS = 10
TILE_SIZE_METERS = TILE_PIXELS * PIXEL_SIZE_METERS
OUTPUT_CRS = "EPSG:32648"  # UTM zone 48N covers Singapore.
DEFAULT_DRIVE_FOLDER = "MarineGuard_Earth_Engine_Tiles"
DEFAULT_MAX_TILES = 100


class TileLimitError(ValueError):
    """Raised before export if an area would create too many Drive tasks."""


def grid_tiles(ee, region, max_tiles: int = DEFAULT_MAX_TILES):
    """Return intersecting 2.56 km grid cells, aligned to 10 m pixels."""
    projection = ee.Projection(OUTPUT_CRS)

    def positive_overlap(feature):
        overlap_area = feature.geometry().intersection(region, ee.ErrorMargin(1)).area(1)
        return feature.set("overlap_area", overlap_area)

    grid = (
        region.coveringGrid(projection, TILE_SIZE_METERS)
        .filterBounds(region)
        .map(positive_overlap)
        .filter(ee.Filter.gt("overlap_area", 0))
    )
    tile_count = int(grid.size().getInfo())
    if tile_count == 0:
        return []
    if tile_count > max_tiles:
        raise TileLimitError(
            f"This area needs {tile_count} tiles; the limit is {max_tiles}. Draw a smaller area."
        )
    return grid.toList(tile_count).getInfo()


def start_drive_exports(
    ee,
    image,
    tile_features: list[dict],
    drive_folder: str = DEFAULT_DRIVE_FOLDER,
    name_prefix: str = "marineguard_sentinel2",
) -> list[dict]:
    """Start one Earth Engine batch export per tile and return task metadata."""
    tasks = []
    for index, feature in enumerate(tile_features, start=1):
        tile_id = f"tile_{index:04d}"
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=f"{name_prefix}_{tile_id}",
            folder=drive_folder,
            fileNamePrefix=f"{name_prefix}_{tile_id}",
            region=ee.Geometry(feature["geometry"]),
            dimensions=f"{TILE_PIXELS}x{TILE_PIXELS}",
            crs=OUTPUT_CRS,
            maxPixels=TILE_PIXELS * TILE_PIXELS,
            fileFormat="GeoTIFF",
        )
        coordinates = feature["geometry"].get("coordinates", [[]])[0]
        longitudes = [point[0] for point in coordinates]
        latitudes = [point[1] for point in coordinates]
        bounds = [min(longitudes), min(latitudes), max(longitudes), max(latitudes)]
        try:
            task.start()
            tasks.append(
                {"tile_id": tile_id, "task_id": task.id, "state": "READY", "bounds": bounds}
            )
        except Exception as exc:
            tasks.append(
                {
                    "tile_id": tile_id,
                    "state": "FAILED_TO_START",
                    "error": str(exc),
                    "bounds": bounds,
                }
            )
    return tasks


def task_status(ee, task_id: str) -> dict:
    """Read the current Earth Engine status for one export task."""
    results = ee.data.getTaskStatus(task_id)
    if not results:
        raise ValueError("Earth Engine did not return a status for that task ID.")
    status = results[0]
    return {
        "task_id": task_id,
        "state": status.get("state", "UNKNOWN"),
        "description": status.get("description"),
        "error_message": status.get("error_message"),
        "destination": status.get("destination_uris", []),
    }
