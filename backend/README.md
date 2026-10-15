# MarineGuard AI backend

The backend currently has two research sections:

- [`data/`](data/README.md): source datasets and dataset handling.
- [`marida/`](marida/README.md): MARIDA model baselines and evaluation.

The initial experiment compares the three strongest MARIDA Random Forest feature sets for Marine Debris, with bands plus indices as the selected starting model. A ResNet-style pixel segmenter has also been trained as an experiment; validation results are recorded in [`marida/README.md`](marida/README.md).

## Setup

From the repository root, use Python 3.12. The saved MARIDA Random Forest checkpoint was created with scikit-learn 1.6.1, so `backend/requirements.txt` pins that version to avoid loading the model with a different scikit-learn release.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

MARIDA training is run with `python -m backend.marida.scripts.train_rf_ss_si`. To mark possible debris pixels in a downloaded Earth Engine tile, use `python -m backend.marida.scripts.predict_tile path/to/tile.tif`; the website also accepts one downloaded tile and displays the experimental pixel layer on the map. See [`marida/README.md`](marida/README.md) for the mask values and limits.

## Earth Engine imagery pipeline

The backend can prepare Sentinel-2 imagery for a selected polygon, return a true-colour preview, export 256×256 tiles to the authenticated Google Drive, and report export task status. Setup and verification instructions are in [`earth_engine/README.md`](earth_engine/README.md). This pipeline prepares imagery only; it does not run model inference.
