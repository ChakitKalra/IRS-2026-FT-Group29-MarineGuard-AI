"""Baseline model definitions for the MARIDA experiments."""

from dataclasses import dataclass

from .random_forest import make_random_forest


@dataclass(frozen=True)
class Baseline:
    id: str
    title: str
    features: tuple[str, ...]
    published_marine_debris_f1: float


BASELINES = {
    "rf_ss_si": Baseline(
        "rf_ss_si", "RF: spectral bands + indices", ("spectral", "indices"), 0.80
    ),
    "rf_ss_si_glcm": Baseline(
        "rf_ss_si_glcm",
        "RF: spectral bands + indices + GLCM texture",
        ("spectral", "indices", "glcm"),
        0.79,
    ),
    "rf_ss": Baseline("rf_ss", "RF: spectral bands", ("spectral",), 0.71),
}


def create_baseline(model_id: str, *, random_state: int = 5, trees: int = 125):
    """Return the selected baseline specification and its RF estimator.

    Feature arrays must be built in the order listed by ``spec.features``.
    """
    try:
        spec = BASELINES[model_id]
    except KeyError as error:
        raise ValueError(f"Unknown MARIDA baseline: {model_id}") from error
    return spec, make_random_forest(random_state=random_state, trees=trees)


__all__ = ["BASELINES", "Baseline", "create_baseline", "make_random_forest"]
