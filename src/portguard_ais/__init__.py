"""PortGuard-AIS public package interface."""

from portguard_ais.config import PortGuardConfig
from portguard_ais.models import EncounterAssessment, VesselObservation
from portguard_ais.pipeline import PortGuardPipeline, ProcessingResult

__all__ = [
    "EncounterAssessment",
    "PortGuardConfig",
    "PortGuardPipeline",
    "ProcessingResult",
    "VesselObservation",
]

__version__ = "1.0.0"
