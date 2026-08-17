# JMSE research track: multi-vessel risk and runtime assurance

## Working title

**AI-Driven Maritime Traffic Risk Assessment for Smart Seaports: Multi-Vessel Conflict Reasoning and Runtime Safety Assurance**

## Separation from the SoftwareX contribution

PortGuard-AIS 1.0 remains the software contribution: validated AIS ingestion, pairwise CPA/TCPA geometry, COLREG context, explainable pairwise risk scoring, near-miss mining, risk trends, and stateful pairwise alerts.

The JMSE contribution is methodological and experimental. It must introduce and validate capabilities that are not the core claim of the SoftwareX paper:

1. scene-level interaction reasoning over a weighted multi-vessel graph;
2. explicit aggregation of pairwise risk, graph coupling, traffic complexity, and uncertainty into a scene-risk state;
3. runtime assurance of the *decision-support layer*, not autonomous trajectory control;
4. degraded-input handling, authority downgrading, and safe fallback semantics;
5. a new benchmark with complex multi-vessel, transient, cascading, delayed, missing, and corrupted AIS conditions;
6. progressive baselines and ablations designed around the scientific hypotheses below.

The JMSE paper must not reuse the SoftwareX benchmark tables as its principal evidence.

## Scientific gap

Recent work already covers multi-ship collision-risk prediction, graph learning, spatiotemporal risk, traffic-complexity evaluation, collision-avoidance control, and runtime-assured autonomous navigation. The defensible gap is narrower:

> Existing studies largely optimize risk prediction or autonomous control, whereas seaport decision support still lacks a transparent scene-level framework that combines multi-vessel interaction reasoning, temporal risk evolution, input-quality awareness, and runtime assurance of alert authority under degraded AIS conditions.

Closest contemporary work to distinguish from includes:

- Wang et al., 2026, *JMSE*, graph learning for multi-ship collision-risk prediction, DOI: 10.3390/jmse14070658.
- Zhang et al., 2026, *Ocean Engineering*, multi-ship encounter risk with hierarchical VCRO, DOI: 10.1016/j.oceaneng.2026.125568.
- Zhao et al., 2026, *Reliability Engineering & System Safety*, real-time graph-based traffic complexity with multi-source fusion, DOI: 10.1016/j.ress.2026.112380.
- Yin et al., 2026, *Ocean Engineering*, reliability-calibrated spatiotemporal encounter-risk forecasting, DOI: 10.1016/j.oceaneng.2026.125752.
- Wang et al., 2026, *Symmetry*, runtime-assured predictive safety control for ASVs, DOI: 10.3390/sym18071123.
- Ge et al., 2026, *Expert Systems with Applications*, safety-assured ASV navigation with formal verification, DOI: 10.1016/j.eswa.2026.131367.

Our scope explicitly excludes fairway design, route generation, waypoint planning, and autonomous avoidance-trajectory prescription.

## Hypotheses

**H1. Scene reasoning.** Weighted multi-vessel scene reasoning improves identification of complex port conflicts relative to independent pairwise thresholding.

**H2. Temporal stability.** Temporal persistence and scene-state hysteresis reduce false and oscillatory alerts without a material increase in missed hazardous scenes.

**H3. Runtime assurance.** Input-quality-aware runtime assurance reduces unsafe or overconfident alert escalation under stale, missing, noisy, or low-confidence AIS data.

**H4. Operational usefulness.** The proposed assurance layer improves alert precision and authority calibration while preserving actionable warning lead time.

## Proposed architecture

```text
AIS observations
    -> validation / freshness / anomaly checks
    -> pairwise PortGuard-AIS assessments
    -> weighted encounter graph
    -> scene coupling + complexity features
    -> scene risk aggregation
    -> temporal scene monitor
    -> runtime assurance supervisor
    -> NO ALERT / ADVISORY / WARNING / CRITICAL / HUMAN VERIFY
```

### 1. Weighted encounter graph

Nodes represent vessels. Edges represent active encounters and carry:

- pairwise PortGuard-AIS risk score;
- DCPA and TCPA;
- relative speed and closing speed;
- encounter type / COLREG context;
- pairwise confidence;
- domain violation indicator.

Graph-level descriptors should include:

- vessel count;
- active-edge count;
- weighted degree distribution;
- maximum weighted degree;
- risk-weighted density;
- number and size of conflict components;
- edge-risk concentration;
- proportion of low-confidence edges.

### 2. Scene risk

Initial interpretable formulation:

`R_scene = alpha * R_peak + beta * R_mean_top_k + gamma * C_graph + delta * U_scene`

where:

- `R_peak` is the maximum pairwise risk;
- `R_mean_top_k` is the mean of the top-k pairwise risks;
- `C_graph` is a bounded interaction/coupling score derived from graph structure;
- `U_scene` is a bounded uncertainty/degradation penalty.

All terms remain explicit and ablatable. The final formulation must be calibrated experimentally rather than selected only by intuition.

### 3. Temporal scene state

Scene states:

`NORMAL -> WATCH -> WARNING -> CRITICAL`

Transitions use:

- entry thresholds;
- release thresholds;
- persistence updates;
- trend / risk acceleration;
- minimum residence time where justified.

This layer is separate from the existing pairwise `AlertStateMachine`.

### 4. Runtime assurance supervisor

The supervisor governs *decision-support authority*. It does not steer the ship.

Candidate assurance modes:

- `NOMINAL`: data quality and confidence satisfy requirements;
- `DEGRADED`: scene assessment remains informative but alert wording/authority is reduced;
- `HUMAN_VERIFY`: critical risk coincides with insufficient confidence or contradictory/degraded evidence;
- `FALLBACK`: input validity or freshness is insufficient for a trustworthy automated risk statement.

Monitors should include:

- observation freshness;
- missing-vessel or missing-field fraction;
- minimum / mean pairwise confidence;
- kinematic anomaly presence;
- scene coverage consistency;
- abrupt confidence collapse;
- computational deadline / latency;
- scene-risk versus evidence-confidence consistency.

Example authority rule:

> A nominal `CRITICAL` scene with inadequate evidence quality is not emitted as an unqualified critical collision claim; it is converted to `HUMAN_VERIFY` with an explicit degraded-input rationale.

## Benchmark scenarios

### Canonical geometry

1. head-on;
2. crossing;
3. overtaking.

### Port-constrained traffic

4. narrow port entrance;
5. bottleneck / channel convergence;
6. three-vessel convergence;
7. five-vessel congestion.

### Interaction-specific stress tests

8. cascading conflict: a safe response relative to vessel B creates increasing conflict with vessel C;
9. transient false-positive: brief pairwise risk spike that should not generate persistent scene escalation;
10. risk handoff: dominant risk shifts from one vessel pair to another while scene risk remains elevated.

### Degraded-input assurance tests

11. delayed AIS updates;
12. random message dropout;
13. missing heading / length / accuracy fields;
14. noisy positions;
15. implausible position jump / spoof-like kinematic anomaly;
16. mixed-confidence scene with one high-risk but low-confidence pair.

Each scenario should be repeated over multiple randomized seeds and severity levels.

## Baselines

- **B0:** CPA/TCPA threshold baseline.
- **B1:** current PortGuard-AIS pairwise risk thresholding.
- **B2:** pairwise risk + existing stateful alert lifecycle.
- **B3:** scene aggregation without temporal monitoring.
- **B4:** scene aggregation + temporal monitoring without runtime assurance.
- **OURS:** scene aggregation + temporal monitoring + runtime assurance.

## Ablations

- no graph coupling term;
- no uncertainty/degradation term;
- no temporal persistence;
- no hysteresis;
- no trend term;
- no assurance supervisor;
- fixed-confidence versus data-quality-aware confidence.

## Metrics

### Detection

- precision, recall, F1;
- missed hazardous scenes;
- false alert rate;
- false critical-alert rate.

### Temporal

- warning lead time;
- time to first correct escalation;
- alert oscillation count;
- unnecessary state transitions;
- persistence after hazard resolution.

### Scene reasoning

- complex-conflict detection rate;
- cascading-conflict detection rate;
- risk-handoff continuity;
- scene severity calibration.

### Assurance

- unsafe/overconfident escalation rate under degraded inputs;
- degraded-input detection rate;
- `HUMAN_VERIFY` precision;
- fallback activation rate;
- inappropriate fallback rate;
- authority-calibration error.

### Computation

- mean latency;
- P95 latency;
- P99 latency;
- missed computational deadlines.

## Controlled mechanism-verification results

The current controlled synthetic benchmark is intended to verify mechanisms, not claim real-world VTS accuracy or certified navigation safety.

### Progressive baseline result

The strongest pure hazard detector is **B4 (scene + temporal)** with precision 0.7066, recall 0.8252, F1 0.7613, and false-alert rate 0.3379. The assured operational output has F1 0.7492 because runtime assurance may deliberately cap alert authority or replace an automated hazard statement with `HUMAN_VERIFY`/`FALLBACK`.

### Runtime assurance result

Under the controlled degraded-input suite, the revised supervisor detected all 18 degraded steps, produced zero overconfident `CRITICAL` outputs, zero inappropriate interventions, and zero inappropriate fallbacks. Six steps were authority-capped, nine required human verification, and three triggered fallback.

### Ablation result

- Removing graph coupling reduces B4 F1 from 0.7613 to 0.7468 and increases false-alert rate from 0.3379 to 0.3793 while preserving recall at 0.8252. In the current benchmark, coupling mainly improves precision/false-alert control rather than sensitivity.
- Removing persistence reduces B4 F1 from 0.7613 to 0.6540, recall from 0.8252 to 0.7203, and increases false-alert rate to 0.4759. Persistence is the strongest temporal contribution in the main scenario suite.
- Removing hysteresis does not change the aggregate benchmark outcomes because the main scenarios do not repeatedly cross the release boundary.

### Dedicated hysteresis probe

A threshold-chatter mechanism probe was therefore evaluated separately. A ten-update sequence oscillating around the warning threshold produced:

- **with hysteresis:** 1 state transition; state remained `WARNING` after entry;
- **without hysteresis:** 10 state transitions, alternating `WARNING` and `WATCH`.

Thus, hysteresis reduced threshold chatter by **90% (10 -> 1 transitions)** in the dedicated boundary-stress test. This result should be presented as a mechanism-specific stability result, not as an aggregate F1 improvement.

### Multi-seed interpretation

The first 30-seed campaign yielded zero standard deviation in aggregate decision metrics because the seeded perturbations did not cross decision thresholds. These repetitions demonstrate decision-level invariance over the tested perturbation range, but must **not** be treated as 30 independent real-world trials or used to imply inferential significance. A subsequent robustness campaign should perturb relative geometry/severity sufficiently to produce meaningful variation in CPA/TCPA and scene-risk margins.

## Required article figures

1. system architecture: pairwise PortGuard-AIS -> scene graph -> temporal monitor -> assurance supervisor;
2. representative weighted encounter graph for a multi-vessel port scene;
3. scene-risk timeline comparing B1/B2/B4/OURS;
4. degraded-AIS case showing risk, confidence, and assurance mode;
5. performance comparison across baselines;
6. ablation results;
7. latency distribution or scaling with vessel count;
8. dedicated hysteresis boundary-stress figure showing `WARNING/WATCH` chatter with and without hysteresis.

## Required article tables

1. closest literature and explicit novelty boundary;
2. scenario matrix and injected disturbances;
3. baselines and ablations;
4. primary detection/temporal results;
5. assurance results under degraded inputs;
6. computational scaling results.

## Claims to avoid before evidence exists

- "first" multi-vessel graph risk method;
- "first" runtime-assured maritime system;
- autonomous collision avoidance claims;
- real-world VTS effectiveness without live-port validation;
- safety certification claims;
- claims that synthetic classification consistency equals real-world accuracy.

## Target contribution statement

The intended contribution is a transparent, reproducible framework for **scene-level maritime traffic risk reasoning and runtime assurance of AI-assisted seaport decision support**, explicitly separating risk estimation from the authority to issue operationally strong alerts under uncertain or degraded AIS evidence.
