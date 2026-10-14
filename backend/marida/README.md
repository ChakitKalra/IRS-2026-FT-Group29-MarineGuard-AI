# MARIDA experiments

This section contains the project's MARIDA baselines. The task is pixel-level semantic segmentation, with Marine Debris (class-mask ID 1) as the target class. The MARIDA dataset and source files live under `backend/data/`.

## Three baselines

1. **RF-SS+SI** — Random Forest using spectral bands plus spectral indices. **Selected starting reference.** The paper reports Marine Debris F1 = 0.80.
2. **RF-SS+SI+GLCM** — Random Forest with bands, indices, and texture features; published Marine Debris F1 = 0.79.
3. **RF-SS** — Random Forest using spectral bands only; published Marine Debris F1 = 0.71.

We are choosing the three strongest comparable published MARIDA baselines for the Marine Debris class. The paper's U-Net result is about 0.50 F1, so it is not in this initial top three. These figures are published results, not measurements from our run. We will first reproduce clean baselines with the dataset's official splits, then tune hyperparameters and compare on the held-out test split only after model choices are fixed.

## Planned layout

- `models/`: one implementation/configuration per baseline.
- `scripts/`: dataset inspection, training, and evaluation commands.
- `outputs/`: local metrics and predictions (ignored by Git).
- `checkpoints/`: local trained weights (ignored by Git).

## Train the selected baseline

After installing `backend/requirements.txt`, run from the repository root:

```sh
python -m backend.marida.scripts.train_rf_ss_si
```

This follows MARIDA's official train/validation patch lists, 11 Sentinel-2 bands, eight published spectral indices, confidence weighting, water-class aggregation, and published Random Forest defaults. It reports Marine Debris precision/recall/F1/IoU on validation and saves local metrics and weights. It leaves the official test split untouched.

## First baseline result

The first RF-SS+SI run produced validation Marine Debris precision **0.866**, recall **0.874**, F1 **0.870**, and IoU **0.770** using 694 training and 328 validation patches. This is an untuned validation result, not a test score; the paper's 0.80 F1 is from its test evaluation, so the two scores are not directly comparable. The serialized model is in `checkpoints/rf_ss_si.joblib`; metrics are in `outputs/rf_ss_si_val_metrics.json`.

## ResNet experiment

A 10-epoch ResNet-style pixel segmenter using the same train/validation splits scored Marine Debris F1 **0.058** (precision **0.524**, recall **0.031**), below RF-SS+SI's **0.870** on that validation split. It did not outperform the Random Forest in this first run. This is an initial CPU run with a small model, so treat it as an experiment rather than a tuned ResNet comparison. We did not use the official test split. Weights and epoch metrics are saved as `checkpoints/resnet_segmentation.pt` and `outputs/resnet_segmentation_val_metrics.json`.

## ResNet tuning screen

We screened nine settings for residual depth, width, dropout, learning rate, weight decay, batch size, class weighting, and loss for three epochs each. The best was width 16 with one residual block per stage, dropout 0.2, learning rate `0.0003`, weight decay `0.001`, batch size 4, balanced class weights, and cross entropy. It scored validation precision **0.093**, recall **0.410**, F1 **0.152**, and IoU **0.082**. RF-SS+SI remains ahead at validation F1 **0.870**. This short screen is preliminary; no official test data was used. See [tuning.md](tuning.md) for the run plan and `outputs/resnet_tuning_summary.json` for all candidates.

## References

- [MARIDA paper](https://doi.org/10.1371/journal.pone.0262247)
- [Official project repository](https://github.com/marine-debris/marine-debris.github.io)
- [MARIDA dataset on Zenodo](https://zenodo.org/records/5151941)
