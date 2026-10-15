# Earth Engine imagery pipeline

This backend accepts a GeoJSON polygon and date range, creates a cloud-masked Sentinel-2 composite, returns an RGB preview for the frontend, and queues aligned 256×256 GeoTIFF tiles in Google Drive. The preview uses B4/B3/B2; each exported tile keeps all 11 reflectance bands for the current ResNet. It does not run model inference.

## One-time setup

Install backend requirements, authenticate with a Google account that has Earth Engine access, and set a Cloud project enabled for Earth Engine:

```sh
python -m pip install -r backend/requirements.txt
earthengine authenticate
export EARTH_ENGINE_PROJECT="your-earth-engine-project-id"
```

Exports use the authenticated account's Drive. `drive_folder` is a Drive folder **name** (the Earth Engine export API does not take a folder ID). The default folder is `MarineGuard_Earth_Engine_Tiles`.

## Run and verify

Start the API with `python -m backend.app.main`. Draw an area in the frontend and submit its date range; the page displays the processed RGB preview and polls export progress. The API call is `POST /api/imagery/prepare`; the end date is exclusive. Check an individual task at `GET /api/imagery/tasks/{task_id}`. After Drive exports finish, download or sync the GeoTIFFs and run:

```sh
python -m backend.earth_engine.verify_tiles path/to/downloaded/tiles
```

The verifier checks 11 bands, 256×256 pixels, 10 m pixel size, UTM zone 48N, and valid pixel data. Keep tiles from the same date range and export settings together; do not use them for inference until the model's normalization and band order are applied.
