# MarineGuard AI

A student project exploring marine litter around Singapore’s coast.

## Project goals

- Detect marine litter in images.
- Predict where litter may accumulate.
- Estimate possible pollution sources.
- Help prioritise cleanup locations.

## Current stage

Frontend prototype implemented with a Singapore map, Singapore wide view, a Coastal area dropdown with polygon drawing, time controls, observation cards, and demo report export. All displayed observations are fictional. No backend APIs, AI models, or data integrations have been implemented.

## Folder structure

```text
frontend/    React website, map, and setup instructions
backend/     Python code and setup instructions
data/raw/    Place source datasets here (excluded from Git)
README.md    Project overview and setup
```

## Getting started

Requires Python 3.9 or newer. No external packages are needed yet.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m backend.app.main
```

The starter prints a project message. Next, we will choose a small dataset and begin exploring it.

See [frontend setup](frontend/README.md) and [backend setup](backend/README.md) for details. The frontend now uses React, Vite, and Leaflet. Backend dependencies will be added as required.
