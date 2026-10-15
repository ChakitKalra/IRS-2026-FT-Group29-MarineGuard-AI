"""Run the MARIDA RF-SS+SI model on a Sentinel-2 tile."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import rasterio

from backend.marida.preprocessing import prepare_tile_for_rf

DEFAULT_MODEL_PATH = Path(__file__).parent / "checkpoints" / "rf_ss_si.joblib"
DEBRIS_CLASS_ID = 1
INVALID_PIXEL = 255


@dataclass(frozen=True)
class TilePrediction:
    """Summary of the saved one-band debris mask."""

    output_path: Path
    valid_pixels: int
    possible_debris_pixels: int

    @property
    def possible_debris_percent(self) -> float:
        if not self.valid_pixels:
            return 0.0
        return 100.0 * self.possible_debris_pixels / self.valid_pixels


def predict_tile(
    tile_path: str | Path,
    output_path: str | Path | None = None,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> TilePrediction:
    """Save a georeferenced mask where 1 marks pixels predicted as debris."""
    tile_path = Path(tile_path)
    output_path = Path(output_path) if output_path else tile_path.with_name(f"{tile_path.stem}_debris_mask.tif")
    model_path = Path(model_path)

    prepared = prepare_tile_for_rf(tile_path)
    model = joblib.load(model_path)
    expected_features = getattr(model, "n_features_in_", None)
    if expected_features is not None and expected_features != prepared.features.shape[1]:
        raise ValueError(
            f"Model expects {expected_features} features, but preprocessing created "
            f"{prepared.features.shape[1]}. Check the model and tile band setup."
        )

    valid = prepared.valid_pixels.ravel()
    mask = np.full(valid.shape, INVALID_PIXEL, dtype=np.uint8)
    if valid.any():
        labels = model.predict(prepared.features[valid])
        mask[valid] = (labels == DEBRIS_CLASS_ID).astype(np.uint8)

    height, width = prepared.valid_pixels.shape
    profile = prepared.profile.copy()
    profile.update(driver="GTiff", count=1, dtype="uint8", nodata=INVALID_PIXEL, compress="deflate")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as destination:
        destination.write(mask.reshape(height, width), 1)
        destination.set_band_description(1, "Possible marine debris (1=yes, 0=no, 255=no data)")

    return TilePrediction(
        output_path=output_path,
        valid_pixels=int(valid.sum()),
        possible_debris_pixels=int(np.count_nonzero(mask == DEBRIS_CLASS_ID)),
    )
