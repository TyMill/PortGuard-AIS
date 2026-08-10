# Risk model

The risk score is a normalized weighted combination of five bounded components:

- DCPA severity;
- TCPA urgency;
- current range;
- radial closing speed;
- predicted dynamic-domain intrusion.

Every component and weight is exported. The score is therefore auditable and can be recalibrated
for a port without hiding the decision inside a black box.

The constant-velocity CPA/TCPA assumption is a short-horizon approximation. Results must be
recalculated whenever a new AIS observation arrives.
