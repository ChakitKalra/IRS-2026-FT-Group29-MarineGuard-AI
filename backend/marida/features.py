"""Feature construction used by the MARIDA RF-SS+SI baseline."""

import numpy as np


def ss_si_features(image: np.ndarray) -> np.ndarray:
    """Return 11 Sentinel-2 bands plus MARIDA's eight published indices.

    ``image`` is a band-first raster in the official MARIDA band order:
    440, 490, 560, 665, 705, 740, 783, 842, 865, 1600, and 2200 nm.
    The returned array has shape (19, height, width).
    """
    bands = np.asarray(image, dtype=np.float32)
    if bands.ndim != 3 or bands.shape[0] != 11:
        raise ValueError(f"Expected 11 band-first channels; received {bands.shape}")

    b2, b3, b4 = bands[1], bands[2], bands[3]
    b6, b8, b10 = bands[5], bands[7], bands[9]
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ndvi = (b8 - b4) / (b8 + b4)
        fai = b8 - (b4 + (b10 - b4) * (833.0 - 665.0) / (1614.0 - 665.0))
        fdi = b8 - (b6 + 10.0 * (b10 - b6) * (833.0 - 740.0) / (1614.0 - 740.0))
        si = ((1.0 - b2) * (1.0 - b3) * (1.0 - b4)) ** (1.0 / 3.0)
        ndwi = (b3 - b8) / (b3 + b8)
        nrd = b8 - b4
        ndmi = (b8 - b10) / (b8 + b10)
        bsi = ((b10 + b4) - (b8 + b2)) / ((b10 + b4) + (b8 + b2))
    indices = np.stack((ndvi, fai, fdi, si, ndwi, nrd, ndmi, bsi), axis=0)
    return np.concatenate((bands, indices), axis=0)
