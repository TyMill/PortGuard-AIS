# Ocean Engineering research track: episodic near-miss candidates

**Status:** exploratory software and preregistered-style experimental *plan*; no
external-data validation or operational safety claim has been established.

**Research separation:** Start from the `main` PortGuard-AIS v1.0.0 codebase.
The graph-based scene reasoning and authority-management work developed in
`research/jmse-runtime-assurance` belongs to the JMSE contribution and is not
a new contribution of the proposed Ocean Engineering study.

## Proposed manuscript concept

*PortGuard-AIS: Uncertainty-Aware Near-Miss Detection and Exposure-Normalized
Traffic Risk Mapping in Confined Port Waters*

The manuscript title is a **target**, not a description of what is already
validated. In particular, uncertainty propagation and exposure normalization
remain to be implemented and evaluated.

## Scope of the present code increment

- `near_miss/episodes.py`: optional segmentation into distinct candidate
  episodes, including same-update risk/DCPA/TCPA criteria, gaps and explicit
  nonhazardous separator updates. The legacy `near_miss/miner.py` remains
  unchanged to preserve the SoftwareX reference run.
- `preprocessing/causal_alignment.py`: opt-in alignment of asynchronous AIS
  rows onto common time ticks using only past observations. Each carried
  measurement retains `source_timestamp`, `age_seconds` and `is_carried`.
  Carry-forward does **not** extrapolate vessel motion; it is appropriate for
  tracking evidence age, not proof of current vessel position.
- `preprocessing/resampling.py`: interpolate COG/heading across 0°/360°
  using angular unwrapping instead of averaging degrees directly.
- `near_miss/exposure_hotspots.py`: opt-in spatial event-intensity map, counting
  segmented candidates at their peak-risk midpoint and dividing by *eligible
  observed pair-hours* in a local metric grid. Pair-time is allocated across
  traversed cells; long observation gaps and implausibly fast pair-midpoint
  changes are excluded and reported. Rates with insufficient exposure are
  undefined, not zero. The denominator is **conditional on the existing
  PortGuard pair-distance prefilter** and must not be described as all port
  traffic exposure. This is an exploratory statistic rather than an
  independently validated maritime casualty-risk index.
- `risk/probabilistic_proximity.py`: opt-in Monte Carlo estimation of minimum
  projected pair separation over a finite horizon, with input-specific Gaussian
  position/SOG/COG uncertainty assumptions, causal age extrapolation, fixed
  random seed, Wilson sampling interval, and distance quantiles. This is **not**
  the probability of an actual collision. AIS position-accuracy metadata alone
  is not sufficient to calibrate a Gaussian standard deviation.

These are engineering prerequisites, **not** evidence of superior collision
prediction or demonstrated real-world safety effectiveness.

## Research questions (to test, not assume)

- RQ1: How does event-wise segmentation affect the precision, recall, event
  counts, duration and temporal agreement of detected near-miss candidates?
- RQ2: How do missing and asynchronous AIS messages, timing jitter, course
  wrap-around and stale measurements change event detection?
- RQ3: Does explicit uncertainty handling improve calibration or robustness
  versus deterministic CPA/TCPA and legacy PortGuard?
- RQ4: Do episode-based and traffic-exposure-normalized hotspot indicators
  yield more stable spatial rankings across independent time windows?

## Planned baselines

B0 — conventional thresholding on DCPA and TCPA.

B1 — legacy PortGuard v1.0 risk score and near-miss miner.

B2 — B1 with improved deterministic episode segmentation (this branch).

B3 — B2 with an uncertainty-aware event decision rule. The Monte Carlo
projected-proximity estimator now exists as a **research component**, but its
threshold, calibration against real error data, time-series aggregation and
comparative validation are **not yet established**. It must not simply rename
the legacy confidence heuristic.

For spatial comparison, benchmark raw risk-update density against
episode-based rates and traffic-exposure-normalized candidate event intensity.
Specify exposure denominators in advance (e.g., valid pair-hours and vessel
passages), taking care not to count carried observations as new AIS reports.

## Experimental data and labels

1. Synthetic controlled encounter families are for regression and mechanism
   checks only. Vary entry geometry, changing speed/course, missed messages,
   false positions, mixed observation cadences and close approaches.
2. Secure *lawfully usable* historical AIS for a confined civilian port area.
   Document collection, vessel coverage, sampling, selection bias, dates,
   quality controls, legal restrictions and reproducibility limitations.
3. Prefer independently adjudicated candidate events (VTS operators, radar,
   incident logs or blinded expert reviews). Do not call a DCPA/TCPA-generated
   threshold its own independent ground truth.
4. Hold out distinct voyages, dates, traffic periods, and preferably another
   port. Avoid contamination by putting updates from the same encounter into
   both train/tuning and test partitions.
5. Freeze parameter settings on a calibration split; report the final
   evaluation unchanged on the holdout split.

## Metrics

- Event-level precision, recall, F1; match predicted and reference episodes
  by predeclared temporal overlap and vessel pair.
- False episode rate per valid vessel-pair-hour, missed episode rate and
  detection lead time. Report the event definition and operational limits.
- Boundary errors: event start/end absolute errors and over-merged/split
  episode counts.
- Under AIS impairment: event recovery, confidence calibration if a
  probabilistic output exists, false alerts and performance by evidence age.
- Hotspot ranking stability across independent weeks, sensitivity to grid
  size and traffic-normalized episode rates with suitable uncertainty bands.
- Computational time and memory scaling with vessel counts and message volume.

## Mandatory ablations and controls

- Episode splitting off/on.
- Same-update criteria off/on.
- Angular interpolation off/on on threshold-crossing COG sequences.
- Causal alignment with max age set to multiple prespecified values.
- Compare carry-forward with a properly implemented motion-aware
  extrapolation baseline, if implemented, keeping source timestamp provenance.
- Compare deterministic versus sampled projected-proximity uncertainty; test
  sensitivity to position/SOG/COG error priors, temporal correlation, bias,
  geometry, and Monte Carlo sample count.
- Grid size, exposure denominator and time-window sensitivity.

## Publication safeguards

- Do not claim real-world collision-avoidance efficacy, navigational
  certification or verified real near misses from AIS proxies alone.
- Cite and differentiate the published JMSE scene-level runtime-assurance
  paper. No duplicate tables, performance claims or methodological novelty.
- Report every baseline that outperforms ours and all adverse scenarios.
- Include a pinned code commit, dataset descriptions and test manifests.
- The December 2024 and February 2026 Ocean Engineering scopes require a
  genuine maritime-engineering application with realistic validation;
  computational reproducibility alone is insufficient.

## Current validation status

The new regression tests are version controlled. The earlier research-branch
suite passed 66 functional tests in CI before adding the probabilistic module.
Subsequent CI runs must be checked before declaring this increment verified.
There has been **no external-data validation**. No B3 event decision threshold or uncertainty calibration has been validated.
The new conditional-exposure hotspot implementation is an experimental
statistic with regression tests; its stability and predictive validity have
not been assessed on independent port traffic data. Numerical experiments are required before any scientific claim.
