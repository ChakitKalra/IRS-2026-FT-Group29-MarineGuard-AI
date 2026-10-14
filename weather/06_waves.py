"""Fetch wave height, direction and period for the same point and UTC day."""
from marine_fetch import fetch_step

if __name__ == '__main__':
    # Wave direction is FROM; current direction in step 5 is TOWARDS.
    # These wave descriptors are not a Stokes-drift velocity vector.
    fetch_step('06_waves', [
        'wave_height', 'wave_direction', 'wave_period'
    ], 'meteofrance_seamless')
