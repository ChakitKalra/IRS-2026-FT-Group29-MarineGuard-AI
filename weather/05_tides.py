"""Fetch modelled sea level (including tides) and combined surface currents."""
from marine_fetch import fetch_step

if __name__ == '__main__':
    # Sea level is relative to mean sea level, not a local tide-table datum.
    # Current velocity includes circulation, tides and wave contributions.
    # Do not add those components again when calculating drift.
    fetch_step('05_tides', [
        'sea_level_height_msl',
        'ocean_current_velocity',
        'ocean_current_direction'
    ], 'meteofrance_seamless')
