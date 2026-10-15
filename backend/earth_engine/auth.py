"""Earth Engine authentication helpers for local development and the API."""

from __future__ import annotations

import os

import ee


class EarthEngineSetupError(RuntimeError):
    """Raised when Earth Engine cannot be initialized for this project."""


def project_id() -> str:
    value = os.getenv("EARTH_ENGINE_PROJECT", "").strip()
    if not value:
        raise EarthEngineSetupError(
            "Set EARTH_ENGINE_PROJECT to a Google Cloud project enabled for Earth Engine."
        )
    return value


def initialize_earth_engine():
    """Initialize from credentials previously created with ee.Authenticate()."""
    try:
        ee.Initialize(project=project_id())
    except EarthEngineSetupError:
        raise
    except Exception as exc:
        raise EarthEngineSetupError(
            "Earth Engine authentication is missing or invalid. Run "
            "`earthengine authenticate`, then set EARTH_ENGINE_PROJECT."
        ) from exc
    return ee


def authenticate_interactively() -> None:
    """Run once from a terminal; never call this from an API request."""
    ee.Authenticate()
    ee.Initialize(project=project_id())


if __name__ == "__main__":
    authenticate_interactively()
    print(f"Earth Engine is ready for project {project_id()}.")
