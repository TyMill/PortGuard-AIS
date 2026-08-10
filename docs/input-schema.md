# Input schema

Timestamps must be timezone-aware. MMSI, latitude, longitude, SOG and COG are mandatory. Invalid
rows, duplicate timestamp/MMSI records and speeds above the configured maximum are reported by the
cleaning stage.

Optional dimensions improve the dynamic ship-domain estimate. Optional position accuracy and
heading fields improve the assessment confidence indicator.
