"""Rule-based, explainable encounter geometry classification."""

from portguard_ais.enums import EncounterType
from portguard_ais.geometry.geodesy import relative_bearing_deg, wrap_angle_deg
from portguard_ais.models import RelativeMotion, VesselObservation


def classify_encounter(
    own: VesselObservation,
    target: VesselObservation,
    motion: RelativeMotion,
) -> EncounterType:
    """Classify geometry from the own-vessel perspective without prescribing action."""
    if not motion.converging:
        return EncounterType.DIVERGING

    own_view = relative_bearing_deg(own, target)
    target_view = relative_bearing_deg(target, own)
    course_difference = abs(wrap_angle_deg(target.cog - own.cog))

    if abs(own_view) <= 15.0 and abs(target_view) <= 15.0 and course_difference >= 150.0:
        return EncounterType.HEAD_ON

    same_general_course = course_difference <= 67.5
    if same_general_course and abs(own_view) <= 67.5 and abs(target_view) > 112.5:
        return EncounterType.OVERTAKING
    if same_general_course and abs(own_view) > 112.5 and abs(target_view) <= 67.5:
        return EncounterType.BEING_OVERTAKEN

    if course_difference <= 15.0:
        return EncounterType.PARALLEL

    if 15.0 < own_view <= 112.5:
        return EncounterType.CROSSING_STARBOARD
    if -112.5 <= own_view < -15.0:
        return EncounterType.CROSSING_PORT

    return EncounterType.INDETERMINATE
