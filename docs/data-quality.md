# Data quality and anomaly checks

`detect_kinematic_anomalies()` compares consecutive positions for each MMSI and reports implied
speeds above a configurable threshold. The result is an audit record, not an automatic deletion:
researchers can decide whether the jump reflects bad data, identity reuse, spoofing, a timestamp
problem or a real exceptional case.
