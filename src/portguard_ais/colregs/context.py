"""Map encounter geometry to a simplified Rules 13-17 context."""

from portguard_ais.enums import EncounterType, VesselRole
from portguard_ais.models import ColregContext


def colreg_context(encounter_type: EncounterType) -> ColregContext:
    """Return contextual roles; this function does not prescribe a manoeuvre."""
    contexts = {
        EncounterType.HEAD_ON: ColregContext(
            rule="Rule 14",
            own_role=VesselRole.MUTUAL_ACTION,
            target_role=VesselRole.MUTUAL_ACTION,
            explanation="Head-on context; both vessels require coordinated compliance monitoring.",
        ),
        EncounterType.CROSSING_STARBOARD: ColregContext(
            rule="Rule 15",
            own_role=VesselRole.GIVE_WAY,
            target_role=VesselRole.STAND_ON,
            explanation="Target is detected on the own vessel's starboard side.",
        ),
        EncounterType.CROSSING_PORT: ColregContext(
            rule="Rules 15 and 17",
            own_role=VesselRole.STAND_ON,
            target_role=VesselRole.GIVE_WAY,
            explanation="Target is detected on the own vessel's port side.",
        ),
        EncounterType.OVERTAKING: ColregContext(
            rule="Rule 13",
            own_role=VesselRole.GIVE_WAY,
            target_role=VesselRole.STAND_ON,
            explanation="Own vessel is approaching from abaft the target's beam.",
        ),
        EncounterType.BEING_OVERTAKEN: ColregContext(
            rule="Rule 13",
            own_role=VesselRole.STAND_ON,
            target_role=VesselRole.GIVE_WAY,
            explanation="Target vessel is approaching from abaft the own vessel's beam.",
        ),
    }
    return contexts.get(
        encounter_type,
        ColregContext(
            rule=None,
            own_role=VesselRole.MONITOR,
            target_role=VesselRole.MONITOR,
            explanation="No specific Rules 13-17 encounter class was assigned.",
        ),
    )
