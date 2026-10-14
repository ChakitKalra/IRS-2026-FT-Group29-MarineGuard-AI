# MarineGuard AI backend

The backend currently has two research sections:

- [`data/`](data/README.md): source datasets and dataset handling.
- [`marida/`](marida/README.md): MARIDA model baselines and evaluation.

The initial experiment compares the three strongest MARIDA Random Forest feature sets for Marine Debris, with bands plus indices as the selected starting model. A ResNet-style pixel segmenter has also been trained as an experiment; validation results are recorded in [`marida/README.md`](marida/README.md).

## Setup

From the repository root, with Python 3.9 or newer:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

The existing `python -m backend.app.main` entry point remains a minimal app placeholder. MARIDA training is run with `python -m backend.marida.scripts.train_rf_ss_si`.
