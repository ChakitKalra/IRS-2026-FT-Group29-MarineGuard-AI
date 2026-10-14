"""Train and validate the MARIDA RF spectral-signatures-plus-indices baseline."""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import rasterio
from joblib import dump
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.marida.features import ss_si_features
from backend.marida.metrics import marine_debris_scores
from backend.marida.models.random_forest import make_random_forest


WATER_CLASS_MERGE = {12: 7, 13: 7, 14: 7, 15: 7}


def read_split(data_root: Path, split_name: str):
    split_path = data_root / "splits" / f"{split_name}_X.txt"
    return [line.strip() for line in split_path.read_text().splitlines() if line.strip()]


def patch_files(data_root: Path, patch_id: str):
    folder_id = "S2_" + patch_id.rsplit("_", 1)[0]
    patch_name = "S2_" + patch_id
    folder = data_root / "patches" / folder_id
    return (
        folder / f"{patch_name}.tif",
        folder / f"{patch_name}_cl.tif",
        folder / f"{patch_name}_conf.tif",
    )


def load_split(data_root: Path, split_name: str):
    feature_parts, label_parts, weight_parts = [], [], []
    class_counts = Counter()
    skipped_nonfinite = 0
    patch_ids = read_split(data_root, split_name)

    for position, patch_id in enumerate(patch_ids, start=1):
        image_path, class_path, confidence_path = patch_files(data_root, patch_id)
        with rasterio.open(image_path) as src:
            image = src.read()
        with rasterio.open(class_path) as src:
            labels = src.read(1).astype(np.uint8, copy=False)
        with rasterio.open(confidence_path) as src:
            confidence = src.read(1).astype(np.uint8, copy=False)

        if image.shape[0] != 11 or labels.shape != image.shape[1:] or confidence.shape != labels.shape:
            raise ValueError(f"Unexpected raster dimensions in {patch_id}: {image.shape}, {labels.shape}")

        annotated = labels > 0
        if not np.any(annotated):
            continue

        features = ss_si_features(image).reshape(19, -1)[:, annotated.ravel()].T
        y = labels[annotated].astype(np.uint8, copy=True)
        confidence_values = confidence[annotated]
        finite = np.isfinite(features).all(axis=1)
        skipped_nonfinite += int((~finite).sum())
        features, y, confidence_values = features[finite], y[finite], confidence_values[finite]

        for original, mapped in WATER_CLASS_MERGE.items():
            y[y == original] = mapped
        # MARIDA confidence IDs are 1=high, 2=moderate, 3=low. Match the
        # official baseline's inverse-confidence sample weighting.
        weights = 1.0 / np.clip(confidence_values.astype(np.float32), 1, 3)

        feature_parts.append(features.astype(np.float32, copy=False))
        label_parts.append(y)
        weight_parts.append(weights)
        class_counts.update(map(int, y))
        if position % 100 == 0 or position == len(patch_ids):
            print(f"Loaded {split_name}: {position}/{len(patch_ids)} patches", flush=True)

    if not feature_parts:
        raise RuntimeError(f"No annotated pixels found for {split_name} split")
    return (
        np.concatenate(feature_parts),
        np.concatenate(label_parts),
        np.concatenate(weight_parts),
        class_counts,
        skipped_nonfinite,
        len(patch_ids),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("backend/data/MARIDA"))
    parser.add_argument("--trees", type=int, default=125)
    parser.add_argument("--max-depth", type=int, default=20)
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=Path("backend/marida"))
    args = parser.parse_args()

    started = time.perf_counter()
    print("Loading official MARIDA train split…", flush=True)
    x_train, y_train, w_train, train_counts, train_skipped, train_patch_count = load_split(args.data, "train")
    print(f"Training pixels: {len(y_train):,}; classes: {dict(sorted(train_counts.items()))}", flush=True)
    print("Loading official MARIDA validation split…", flush=True)
    x_val, y_val, _, val_counts, val_skipped, val_patch_count = load_split(args.data, "val")
    print(f"Validation pixels: {len(y_val):,}; classes: {dict(sorted(val_counts.items()))}", flush=True)

    classifier = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("rf", make_random_forest(random_state=args.seed, trees=args.trees, max_depth=args.max_depth)),
        ],
        verbose=False,
    )
    print("Training RF-SS+SI…", flush=True)
    fit_started = time.perf_counter()
    classifier.fit(x_train, y_train, rf__sample_weight=w_train)
    fit_seconds = time.perf_counter() - fit_started
    print("Predicting validation pixels…", flush=True)
    prediction = classifier.predict(x_val)
    scores = marine_debris_scores(y_val, prediction, class_id=1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = args.output_dir / "checkpoints"
    output_dir = args.output_dir / "outputs"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = checkpoint_dir / "rf_ss_si.joblib"
    metrics_path = output_dir / "rf_ss_si_val_metrics.json"
    dump(classifier, model_path)
    report = {
        "model": "rf_ss_si",
        "dataset": "MARIDA",
        "evaluation_split": "validation",
        "training_patch_count": train_patch_count,
        "validation_patch_count": val_patch_count,
        "training_annotated_pixels": int(len(y_train)),
        "validation_annotated_pixels": int(len(y_val)),
        "training_class_counts_after_water_merge": dict(sorted(train_counts.items())),
        "validation_class_counts_after_water_merge": dict(sorted(val_counts.items())),
        "target_class": "Marine Debris",
        "target_class_mask_id": 1,
        "target_metrics": scores,
        "model_parameters": {"n_estimators": args.trees, "max_depth": args.max_depth, "random_state": args.seed},
        "features": ["11 Sentinel-2 spectral bands", "NDVI", "FAI", "FDI", "SI", "NDWI", "NRD", "NDMI", "BSI"],
        "sample_weight": "inverse confidence ID (1=high, 2=moderate, 3=low)",
        "nonfinite_annotated_pixels_skipped": {"train": train_skipped, "validation": val_skipped},
        "fit_seconds": round(fit_seconds, 2),
        "total_seconds": round(time.perf_counter() - started, 2),
        "test_split_used": False,
    }
    metrics_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    print(f"Model saved: {model_path}", flush=True)
    print(f"Metrics saved: {metrics_path}", flush=True)


if __name__ == "__main__":
    main()
