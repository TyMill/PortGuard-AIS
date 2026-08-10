from portguard_ais.colregs.context import colreg_context
from portguard_ais.enums import EncounterType, VesselRole


def test_crossing_starboard_context() -> None:
    context = colreg_context(EncounterType.CROSSING_STARBOARD)
    assert context.rule == "Rule 15"
    assert context.own_role == VesselRole.GIVE_WAY


def test_indeterminate_context_has_no_specific_rule() -> None:
    context = colreg_context(EncounterType.INDETERMINATE)
    assert context.rule is None
    assert context.own_role == VesselRole.MONITOR
