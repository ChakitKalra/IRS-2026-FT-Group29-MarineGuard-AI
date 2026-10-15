"""Sentinel-2 search, cloud masking, and compositing."""

from __future__ import annotations

from datetime import date


SENTINEL2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
# These are the 11 reflectance channels used by the MARIDA ResNet input.
SENTINEL2_BANDS = ("B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12")
SCL_CLOUD_CLASSES = (0, 1, 3, 8, 9, 10, 11)  # no data, defective, shadow, cloud, cirrus, snow/ice


class NoImageryError(ValueError):
    """Raised when the requested time and region contain no suitable scenes."""


def _mask_clouds(image, ee):
    scl = image.select("SCL")
    clear = scl.remap(
        list(SCL_CLOUD_CLASSES),
        [0] * len(SCL_CLOUD_CLASSES),
        1,
    )
    return (
        image.updateMask(clear)
        .select(list(SENTINEL2_BANDS))
        .multiply(0.0001)
        .copyProperties(image, ["system:time_start", "CLOUDY_PIXEL_PERCENTAGE"])
    )


def build_sentinel2_composite(
    ee,
    region,
    start_date: date,
    end_date: date,
    max_scene_cloud_percent: float = 80.0,
):
    """Return an 11-band, cloud-masked median composite and scene count.

    ``end_date`` is exclusive, matching Earth Engine's filterDate behavior.
    Reflectance is converted from Sentinel-2 integer scale to 0–1 units.
    """
    collection = (
        ee.ImageCollection(SENTINEL2_COLLECTION)
        .filterBounds(region)
        .filterDate(start_date.isoformat(), end_date.isoformat())
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", max_scene_cloud_percent))
    )
    scene_count = int(collection.size().getInfo())
    if scene_count == 0:
        raise NoImageryError("No Sentinel-2 scenes match this polygon, date range, and cloud limit.")

    composite = (
        collection.map(lambda image: _mask_clouds(image, ee))
        .median()
        .select(list(SENTINEL2_BANDS))
        .clip(region)
    )
    return composite, scene_count
