"""Train and validate a ResNet-style MARIDA pixel segmenter."""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import rasterio
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from backend.marida.metrics import marine_debris_scores
from backend.marida.models.resnet_segmentation import ResNetSegmenter
from backend.marida.scripts.train_rf_ss_si import WATER_CLASS_MERGE, patch_files, read_split


class MaridaPatches(Dataset):
    def __init__(self, data_root: Path, patch_ids: list[str], mean: np.ndarray, std: np.ndarray, augment: bool):
        self.data_root = data_root
        self.patch_ids = patch_ids
        self.mean = mean.astype(np.float32)
        self.std = np.maximum(std, 1e-6).astype(np.float32)
        self.augment = augment

    def __len__(self):
        return len(self.patch_ids)

    def __getitem__(self, index):
        image_path, class_path, confidence_path = patch_files(self.data_root, self.patch_ids[index])
        with rasterio.open(image_path) as src:
            image = src.read().astype(np.float32, copy=False)
        with rasterio.open(class_path) as src:
            labels = src.read(1).astype(np.int64, copy=False)
        with rasterio.open(confidence_path) as src:
            confidence = src.read(1).astype(np.float32, copy=False)

        image = np.where(np.isfinite(image), image, self.mean[:, None, None])
        image = (image - self.mean[:, None, None]) / self.std[:, None, None]
        labels = labels.copy()
        for source, target in WATER_CLASS_MERGE.items():
            labels[labels == source] = target

        image = torch.from_numpy(np.ascontiguousarray(image))
        labels = torch.from_numpy(np.ascontiguousarray(labels))
        confidence = torch.from_numpy(np.ascontiguousarray(confidence))
        if self.augment:
            if torch.rand(()) < 0.5:
                image, labels, confidence = image.flip(-1), labels.flip(-1), confidence.flip(-1)
            if torch.rand(()) < 0.5:
                image, labels, confidence = image.flip(-2), labels.flip(-2), confidence.flip(-2)
            turns = int(torch.randint(0, 4, ()).item())
            if turns:
                image = torch.rot90(image, turns, (-2, -1))
                labels = torch.rot90(labels, turns, (-2, -1))
                confidence = torch.rot90(confidence, turns, (-2, -1))
        return image, labels, confidence


def training_normalization(data_root: Path, patch_ids: list[str]):
    total = np.zeros(11, dtype=np.float64)
    total_sq = np.zeros(11, dtype=np.float64)
    count = np.zeros(11, dtype=np.int64)
    for i, patch_id in enumerate(patch_ids, start=1):
        image_path, _, _ = patch_files(data_root, patch_id)
        with rasterio.open(image_path) as src:
            image = src.read().astype(np.float64, copy=False)
        for band in range(11):
            values = image[band][np.isfinite(image[band])]
            total[band] += values.sum()
            total_sq[band] += np.square(values).sum()
            count[band] += values.size
        if i % 100 == 0 or i == len(patch_ids):
            print(f"Computed band statistics: {i}/{len(patch_ids)} training patches", flush=True)
    mean = total / count
    variance = np.maximum(total_sq / count - mean**2, 1e-12)
    return mean.astype(np.float32), np.sqrt(variance).astype(np.float32)


def cached_training_normalization(data_root: Path, patch_ids: list[str], output_dir: Path):
    cache_path = output_dir / "resnet_training_normalization.npz"
    if cache_path.exists():
        cached = np.load(cache_path)
        return cached["mean"], cached["std"]
    mean, std = training_normalization(data_root, patch_ids)
    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez(cache_path, mean=mean, std=std)
    return mean, std


def class_weights(data_root: Path, patch_ids: list[str], device, mode: str):
    counts = np.zeros(12, dtype=np.int64)
    for patch_id in patch_ids:
        _, class_path, _ = patch_files(data_root, patch_id)
        with rasterio.open(class_path) as src:
            labels = src.read(1).astype(np.int64, copy=False)
        for source, target in WATER_CLASS_MERGE.items():
            labels[labels == source] = target
        values, frequencies = np.unique(labels[labels > 0], return_counts=True)
        counts[values] += frequencies
    present = counts > 0
    weights = np.zeros(12, dtype=np.float32)
    inverse = counts[present].sum() / (present.sum() * counts[present])
    weights[present] = np.sqrt(inverse) if mode == "sqrt" else inverse if mode == "balanced" else 1.0
    weights[present] /= weights[present].mean()
    return torch.tensor(weights, dtype=torch.float32, device=device), counts


def evaluate(model, loader, device):
    model.eval()
    true_parts, pred_parts = [], []
    with torch.inference_mode():
        for images, labels, _ in loader:
            logits = model(images.to(device))
            predictions = logits.argmax(dim=1).cpu().numpy()
            truth = labels.numpy()
            annotated = truth > 0
            true_parts.append(truth[annotated])
            pred_parts.append(predictions[annotated])
    y_true = np.concatenate(true_parts)
    y_pred = np.concatenate(pred_parts)
    return marine_debris_scores(y_true, y_pred, class_id=1), y_true, y_pred


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("backend/data/MARIDA"))
    parser.add_argument("--output-dir", type=Path, default=Path("backend/marida"))
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.0)
    parser.add_argument("--layers", default="1,1,1,1", help="Residual blocks per encoder stage")
    parser.add_argument("--class-weight", choices=("sqrt", "balanced", "none"), default="sqrt")
    parser.add_argument("--loss", choices=("cross_entropy", "focal"), default="cross_entropy")
    parser.add_argument("--focal-gamma", type=float, default=2.0)
    parser.add_argument("--run-name", default="resnet_segmentation")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=0)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))
    started = time.perf_counter()
    train_ids, val_ids = read_split(args.data, "train"), read_split(args.data, "val")
    mean, std = cached_training_normalization(args.data, train_ids, args.output_dir / "outputs")
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Training on {device}; train={len(train_ids)} patches, validation={len(val_ids)} patches", flush=True)

    train_data = MaridaPatches(args.data, train_ids, mean, std, augment=True)
    val_data = MaridaPatches(args.data, val_ids, mean, std, augment=False)
    train_loader = DataLoader(
        train_data,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        pin_memory=False,
    )
    val_loader = DataLoader(val_data, batch_size=args.batch_size, shuffle=False, num_workers=args.workers)

    layers = tuple(int(value.strip()) for value in args.layers.split(","))
    if len(layers) != 4 or any(value < 1 for value in layers):
        parser.error("--layers must be four comma-separated positive integers")
    weights, train_counts = class_weights(args.data, train_ids, device, args.class_weight)
    model = ResNetSegmenter(
        in_channels=11, num_classes=12, width=args.width, layers=layers, dropout=args.dropout
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
    best_f1 = -1.0
    best_epoch = 0
    history = []
    checkpoint_dir = args.output_dir / "checkpoints"
    output_dir = args.output_dir / "outputs"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / f"{args.run_name}.pt"

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss, seen_batches = 0.0, 0
        for images, labels, confidence in train_loader:
            images, labels = images.to(device), labels.to(device)
            confidence = confidence.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            unweighted_loss_map = nn.functional.cross_entropy(logits, labels, ignore_index=0, reduction="none")
            class_weight_map = weights[labels.clamp(min=0, max=weights.numel() - 1)]
            loss_map = unweighted_loss_map * class_weight_map
            if args.loss == "focal":
                probabilities = torch.exp(-unweighted_loss_map)
                loss_map = (1.0 - probabilities).pow(args.focal_gamma) * loss_map
            confidence_weights = 1.0 / confidence.clamp(min=1.0, max=3.0)
            valid_weights = confidence_weights * (labels > 0)
            loss = (loss_map * valid_weights).sum() / valid_weights.sum().clamp_min(1.0)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            running_loss += float(loss.detach().cpu())
            seen_batches += 1

        scores, _, _ = evaluate(model, val_loader, device)
        epoch_result = {"epoch": epoch, "train_loss": running_loss / max(seen_batches, 1), **scores}
        history.append(epoch_result)
        print(
            f"Epoch {epoch}/{args.epochs}: loss={epoch_result['train_loss']:.4f}, "
            f"val debris F1={scores['f1']:.4f}, precision={scores['precision']:.4f}, "
            f"recall={scores['recall']:.4f}",
            flush=True,
        )
        if scores["f1"] > best_f1:
            best_f1, best_epoch = scores["f1"], epoch
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "band_mean": torch.from_numpy(mean),
                    "band_std": torch.from_numpy(std),
                    "model_config": {
                        "in_channels": 11, "num_classes": 12, "width": args.width,
                        "layers": layers, "dropout": args.dropout,
                    },
                    "epoch": epoch,
                    "validation_metrics": scores,
                },
                checkpoint_path,
            )

    baseline_metrics_path = output_dir / "rf_ss_si_val_metrics.json"
    baseline_f1 = None
    if baseline_metrics_path.exists():
        baseline_f1 = json.loads(baseline_metrics_path.read_text())["target_metrics"]["f1"]
    best_scores = {key: value for key, value in next(row for row in history if row["epoch"] == best_epoch).items() if key != "epoch" and key != "train_loss"}
    report = {
        "model": "resnet_segmentation",
        "dataset": "MARIDA",
        "evaluation_split": "validation",
        "training_patch_count": len(train_ids),
        "validation_patch_count": len(val_ids),
        "target_class": "Marine Debris",
        "target_class_mask_id": 1,
        "target_metrics": best_scores,
        "rf_ss_si_validation_f1": baseline_f1,
        "f1_delta_vs_rf_ss_si": None if baseline_f1 is None else round(best_scores["f1"] - baseline_f1, 6),
        "best_epoch": best_epoch,
        "history": history,
        "training_class_counts_after_water_merge": {str(i): int(n) for i, n in enumerate(train_counts) if n},
        "model_parameters": {
            "architecture": "residual encoder-decoder",
            "width": args.width,
            "dropout": args.dropout,
            "residual_blocks_per_stage": layers,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
            "class_weight": args.class_weight,
            "loss": args.loss,
            "focal_gamma": args.focal_gamma if args.loss == "focal" else None,
            "seed": args.seed,
            "device": str(device),
        },
        "training_loss": f"{args.loss} on annotated pixels, {args.class_weight} class weights, inverse-confidence weighted",
        "test_split_used": False,
        "total_seconds": round(time.perf_counter() - started, 2),
    }
    metrics_path = output_dir / f"{args.run_name}_val_metrics.json"
    metrics_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    print(f"Model saved: {checkpoint_path}", flush=True)
    print(f"Metrics saved: {metrics_path}", flush=True)


if __name__ == "__main__":
    main()
