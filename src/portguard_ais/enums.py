"""Shared enumerations."""

from enum import StrEnum


class EncounterType(StrEnum):
    """Relative encounter geometry from the own-vessel perspective."""

    HEAD_ON = "head-on"
    CROSSING_STARBOARD = "crossing-starboard"
    CROSSING_PORT = "crossing-port"
    OVERTAKING = "overtaking"
    BEING_OVERTAKEN = "being-overtaken"
    PARALLEL = "parallel"
    DIVERGING = "diverging"
    INDETERMINATE = "indeterminate"


class RiskLevel(StrEnum):
    """Human-readable risk severity."""

    SAFE = "safe"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertState(StrEnum):
    """Lifecycle state for a tracked encounter."""

    SAFE = "safe"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"
    RESOLVING = "resolving"
    CLOSED = "closed"


class VesselRole(StrEnum):
    """Simplified navigational role in an encounter."""

    GIVE_WAY = "give-way"
    STAND_ON = "stand-on"
    MUTUAL_ACTION = "mutual-action"
    MONITOR = "monitor"
    UNDETERMINED = "undetermined"


class RiskTrend(StrEnum):
    """Direction of risk evolution across repeated observations."""

    INCREASING = "increasing"
    STABLE = "stable"
    DECREASING = "decreasing"
    INSUFFICIENT = "insufficient-data"
