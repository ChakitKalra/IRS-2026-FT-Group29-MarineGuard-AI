"""Run a compact ResNet hyperparameter screen on MARIDA validation data."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


PLAN = [
    {"layers": "1,1,1,1", "width": 8, "dropout": 0.0, "lr": 0.001, "weight_decay": 0.0001, "batch_size": 8, "class_weight": "sqrt", "loss": "cross_entropy"},
    {"layers": "1,1,1,1", "width": 8, "dropout": 0.2, "lr": 0.001, "weight_decay": 0.001, "batch_size": 8, "class_weight": "balanced", "loss": "cross_entropy"},
    {"layers": "1,1,1,1", "width": 8, "dropout": 0.35, "lr": 0.0003, "weight_decay": 0.001, "batch_size": 8, "class_weight": "balanced", "loss": "cross_entropy"},
    {"layers": "2,2,2,2", "width": 8, "dropout": 0.2, "lr": 0.001, "weight_decay": 0.0001, "batch_size": 8, "class_weight": "balanced", "loss": "cross_entropy"},
    {"layers": "2,2,2,2", "width": 8, "dropout": 0.35, "lr": 0.0003, "weight_decay": 0.001, "batch_size": 8, "class_weight": "sqrt", "loss": "cross_entropy"},
    {"layers": "1,1,1,1", "width": 16, "dropout": 0.2, "lr": 0.0003, "weight_decay": 0.001, "batch_size": 4, "class_weight": "balanced", "loss": "cross_entropy"},
    {"layers": "1,1,1,1", "width": 16, "dropout": 0.5, "lr": 0.001, "weight_decay": 0.0001, "batch_size": 4, "class_weight": "none", "loss": "cross_entropy"},
    {"layers": "1,1,1,1", "width": 8, "dropout": 0.0, "lr": 0.001, "weight_decay": 0.0001, "batch_size": 8, "class_weight": "none", "loss": "focal"},
    {"layers": "2,2,2,2", "width": 8, "dropout": 0.5, "lr": 0.0003, "weight_decay": 0.01, "batch_size": 8, "class_weight": "balanced", "loss": "focal"},
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="print the candidate settings as JSON and exit")
    parser.add_argument("--epochs", type=int, default=3, help="screening epochs per configuration")
    args = parser.parse_args()
    if args.plan:
        print(json.dumps(PLAN, indent=2))
        return

    root = Path(__file__).resolve().parents[3]
    metrics_dir = root / "backend/marida/outputs"
    checkpoint_dir = root / "backend/marida/checkpoints"
    results = []
    for index, config in enumerate(PLAN, start=1):
        name = f"resnet_tune_{index:02d}"
        command = [
            sys.executable, "-m", "backend.marida.scripts.train_resnet",
            "--epochs", str(args.epochs), "--batch-size", str(config["batch_size"]),
            "--learning-rate", str(config["lr"]), "--weight-decay", str(config["weight_decay"]),
            "--width", str(config["width"]), "--layers", config["layers"],
            "--dropout", str(config["dropout"]), "--class-weight", config["class_weight"],
            "--loss", config["loss"], "--run-name", name,
        ]
        print(f"\n[{index}/{len(PLAN)}] {name}: {json.dumps(config)}", flush=True)
        subprocess.run(command, cwd=root, check=True)
        report = json.loads((metrics_dir / f"{name}_val_metrics.json").read_text())
        results.append({"run": name, "configuration": config, **report})

    results.sort(key=lambda item: item["target_metrics"]["f1"], reverse=True)
    summary = {
        "dataset": "MARIDA",
        "selection_split": "validation",
        "selection_metric": "Marine Debris F1",
        "epochs_per_configuration": args.epochs,
        "official_test_split_used": False,
        "ranked_runs": results,
        "best_run": results[0]["run"],
        "best_configuration": results[0]["configuration"],
        "best_validation_metrics": results[0]["target_metrics"],
    }
    summary_path = metrics_dir / "resnet_tuning_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    best_checkpoint = checkpoint_dir / f"{results[0]['run']}.pt"
    selected_checkpoint = checkpoint_dir / "resnet_segmentation_tuned.pt"
    shutil.copy2(best_checkpoint, selected_checkpoint)
    print(json.dumps({key: summary[key] for key in ("best_run", "best_configuration", "best_validation_metrics")}, indent=2))
    print(f"Summary saved: {summary_path}")
    print(f"Selected weights: {selected_checkpoint}")


if __name__ == "__main__":
    main()
