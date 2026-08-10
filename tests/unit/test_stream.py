from datetime import UTC, datetime, timedelta

from portguard_ais.ingestion.stream import iter_snapshots
from portguard_ais.models import VesselObservation


def test_iter_snapshots_sorts_and_groups() -> None:
    first_time = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    second_time = first_time + timedelta(seconds=30)
    observations = [
        VesselObservation(timestamp=second_time, mmsi=3, lat=0, lon=0, sog=1, cog=0),
        VesselObservation(timestamp=first_time, mmsi=2, lat=0, lon=0, sog=1, cog=0),
        VesselObservation(timestamp=first_time, mmsi=1, lat=0, lon=0, sog=1, cog=0),
    ]
    snapshots = list(iter_snapshots(observations))
    assert [[item.mmsi for item in group] for group in snapshots] == [[1, 2], [3]]
