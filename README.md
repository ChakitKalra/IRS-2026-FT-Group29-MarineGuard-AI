# MarineGuard AI

A student project exploring marine litter around Singapore’s coast.

## Project goals

- Detect marine litter in images.
- Predict where litter may accumulate.
- Estimate possible pollution sources.
- Help prioritise cleanup locations.

## Current stage

The frontend supports selecting a coastal area and drawing a polygon. The backend can fetch Sentinel-2 imagery through Google Earth Engine, preview the processed image, and export tiles. A downloaded tile can be sent through the backend to run the MARIDA model and display an experimental possible-debris pixel layer on the map.

## Folder structure

```text
frontend/    React website, map, and setup instructions
backend/     Python code and setup instructions
data/raw/    Place source datasets here (excluded from Git)
README.md    Project overview and setup
```

## Getting started

Use Python 3.12 for the backend environment. The Random Forest checkpoint uses scikit-learn 1.6.1, which supports Python 3.9–3.13; Python 3.12 is the recommended setup. See the [scikit-learn install guide](https://scikit-learn.org/1.6/install.html).

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m backend.app.main
```

For the website, see [frontend setup](frontend/README.md). Backend setup and Earth Engine authentication are in [backend setup](backend/README.md).
