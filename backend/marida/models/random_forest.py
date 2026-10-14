"""Random Forest baselines operating on per-pixel feature vectors."""

from sklearn.ensemble import RandomForestClassifier


def make_random_forest(
    *, random_state: int = 5, trees: int = 125, max_depth: int = 20
) -> RandomForestClassifier:
    """Return the shared RF setup for RF-SS and RF-SS+SI.

    Select the variant by supplying spectral bands alone (RF-SS) or bands plus
    derived spectral indices (RF-SS+SI) as columns to ``fit``/``predict``.
    """
    return RandomForestClassifier(
        n_estimators=trees,
        criterion="gini",
        max_depth=max_depth,
        min_samples_leaf=1,
        oob_score=True,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=random_state,
    )
