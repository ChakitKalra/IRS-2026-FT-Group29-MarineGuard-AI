"""Predict possible marine-debris pixels in one downloaded Earth Engine tile."""

from __future__ import annotations

import argparse
from pathlib import Path

from backend.marida.prediction import DEFAULT_MODEL_PATH, predict_tile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tile", type=Path, help="Path to one downloaded 11-band Sentinel-2 GeoTIFF")
    parser.add_argument("--output", type=Path, help="Output mask GeoTIFF (defaults beside the input tile)")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH, help="MARIDA RF checkpoint")
    args = parser.parse_args()

    result = predict_tile(args.tile, args.output, args.model)
    print(f"Prediction mask: {result.output_path}")
    print(f"Pixels marked as possible debris: {result.possible_debris_pixels:,} / {result.valid_pixels:,} "
          f"({result.possible_debris_percent:.2f}%)")
    print("Mask values: 1=possible debris, 0=not flagged, 255=no data")


if __name__ == "__main__":
    main()
