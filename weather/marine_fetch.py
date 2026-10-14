"""Shared marine API retrieval for steps 5 and 6 (Python, not Earth Engine)."""
import argparse
import datetime as dt
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

SOURCE = 'https://open-meteo.com/en/docs/marine-weather-api'


def fetch_step(step, variables, model):
    parser = argparse.ArgumentParser(description=step)
    parser.add_argument('--date', default='2026-10-01',
                        help='UTC day matching your satellite image')
    parser.add_argument('--latitude', type=float, default=1.20)
    parser.add_argument('--longitude', type=float, default=103.85)
    args = parser.parse_args()
    dt.date.fromisoformat(args.date)
    if not (-90 <= args.latitude <= 90 and -180 <= args.longitude <= 180):
        parser.error('Coordinates are out of range.')

    # Public study coordinates, not a live device location.
    # Use one marine point first; this does not cover all Singapore waters.
    params = {
        'latitude': args.latitude, 'longitude': args.longitude,
        'hourly': ','.join(variables), 'models': model,
        'start_date': args.date, 'end_date': args.date,
        'timezone': 'GMT', 'cell_selection': 'sea', 'velocity_unit': 'ms'
    }
    url = 'https://marine-api.open-meteo.com/v1/marine?' + urllib.parse.urlencode(params)
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'MarineGuard-study/1.0'})
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode('utf-8', errors='replace')
        raise SystemExit('Marine API rejected this request: ' + detail)
    except (urllib.error.URLError, TimeoutError) as error:
        raise SystemExit('Marine API could not be reached: ' + str(error))

    if payload.get('error'):
        raise SystemExit(payload.get('reason', 'Marine API returned an error.'))
    hourly = payload.get('hourly', {})
    times = hourly.get('time', [])
    if not times or any(not t.startswith(args.date + 'T') for t in times):
        raise SystemExit('No matching hourly timestamps; no data file was saved.')
    if payload.get('utc_offset_seconds') != 0:
        raise SystemExit('Unexpected timezone offset; no data file was saved.')
    if any(len(hourly.get(v, [])) != len(times) for v in variables):
        raise SystemExit('Missing or inconsistent variable arrays; no data file was saved.')

    # Retain missing values as null. They must never become zero currents.
    counts = {v: sum(x is not None for x in hourly[v]) for v in variables}
    if any(n == 0 for n in counts.values()):
        raise SystemExit('Required variables have no data at this point/date: ' + str(counts))
    result = {
        'step': step, 'source_documentation': SOURCE, 'request_url': url,
        'requested_model': model,
        'retrieved_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'requested_point': {'latitude': args.latitude, 'longitude': args.longitude},
        'requested_date_utc': args.date,
        'model_run_time': None,
        'model_run_note': 'This endpoint does not identify the original forecast run.',
        'non_null_counts': counts,
        'response': payload
    }
    folder = Path(__file__).resolve().parent / 'data'
    folder.mkdir(exist_ok=True)
    filename = '{}_{}_{}_{}.json'.format(step, args.date, args.latitude, args.longitude)
    path = folder / filename
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print('Saved:', path)
    print('Non-missing hourly values:', counts)
    print('Check returned grid coordinates and units before combining with imagery.')
