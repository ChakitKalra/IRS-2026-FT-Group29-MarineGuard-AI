"""Evaluation helpers focused on the rare Marine Debris class."""

import numpy as np
from sklearn.metrics import precision_recall_fscore_support


def marine_debris_scores(y_true, y_pred, class_id: int = 1) -> dict[str, float]:
    """Calculate pixel-level precision, recall, F1, and IoU for one class."""
    truth = np.asarray(y_true).reshape(-1)
    prediction = np.asarray(y_pred).reshape(-1)
    if truth.shape != prediction.shape:
        raise ValueError("Truth and prediction must contain the same number of pixels")

    precision, recall, f1, _ = precision_recall_fscore_support(
        truth,
        prediction,
        labels=[class_id],
        average="micro",
        zero_division=0,
    )
    iou = f1 / (2.0 - f1) if f1 < 2.0 else 0.0
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "iou": float(iou),
    }
