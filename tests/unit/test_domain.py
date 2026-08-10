from portguard_ais.config import DomainConfig
from portguard_ais.models import RelativeMotion, VesselObservation
from portguard_ais.risk.domain import assess_ship_domain


def test_domain_violation_at_zero_dcpa(eastbound: VesselObservation) -> None:
    motion = RelativeMotion(
        current_distance_nm=1.0,
        dcpa_nm=0.0,
        tcpa_min=5.0,
        relative_speed_kn=10.0,
        closing_speed_kn=10.0,
        converging=True,
        relative_bearing_deg=0.0,
        cpa_east_nm=0.0,
        cpa_north_nm=0.0,
    )
    domain = assess_ship_domain(eastbound, motion, DomainConfig())
    assert domain.violated
    assert domain.forward_nm > domain.aft_nm
