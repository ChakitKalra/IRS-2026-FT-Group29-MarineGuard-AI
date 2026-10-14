# Data

This section holds the source data used by backend experiments. The MARIDA archive is downloaded from [Zenodo record 5151941](https://zenodo.org/records/5151941), the dataset's official distribution. The archive and extracted imagery are intentionally excluded from Git because they are large.

## MARIDA

The archive is expected at `backend/data/MARIDA.zip` (about 1.1 GB). After the download completes, inspect it before extraction:

```sh
mkdir -p backend/data
curl --fail --location --continue-at - 'https://zenodo.org/records/5151941/files/MARIDA.zip?download=1' --output backend/data/MARIDA.zip
python -m backend.marida.scripts.inspect_archive
```

The archive has been downloaded and extracted beneath `backend/data/MARIDA/`. It contains 4,143 GeoTIFFs across 63 dated/tile folders, with official train/validation/test lists containing 694/328/359 patch IDs. The folders include image patches, `_cl` class masks, and `_conf` confidence masks. Class-mask ID `1` is Marine Debris. The large archive and extracted dataset are ignored by Git; keep the source archive unchanged so experiments can be traced to the release.

MARIDA provides Sentinel-2 image patches and pixel labels for marine-debris semantic segmentation. It is a global benchmark, not Singapore-specific data; we will need separate local validation before treating its scores as Singapore performance. Read the dataset's license and citation included with the source release before redistributing any data. Cite the MARIDA paper and Zenodo record when reporting results.

Do not mix patches across train, validation, and test splits. Record any filtering, band selection, normalization, and class remapping in the experiment notes.
