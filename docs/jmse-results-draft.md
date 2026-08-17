# JMSE Results and Discussion Draft

## Experimental status

The controlled experimental campaign is considered complete for the current manuscript scope. The evidence supports mechanism-level and controlled-robustness claims for scene reasoning, temporal stabilization, and runtime assurance. It does **not** support claims of certified navigation safety or real-world VTS effectiveness.

## 1. Progressive baseline comparison

Across the 30-seed geometry-jitter robustness campaign (`position_jitter_nm = 0.08`), the progressive baselines produced the following mean performance:

| Method | Precision | Recall | F1 | False-alert rate |
|---|---:|---:|---:|---:|
| B0 CPA/TCPA | 0.5895 | 0.6622 | 0.6234 | 0.4547 |
| B1 pairwise static | 0.6029 | 0.7329 | 0.6613 | 0.4759 |
| B2 pairwise temporal | 0.6757 | 0.8310 | 0.7451 | 0.3936 |
| B3 scene static | 0.6048 | 0.6998 | 0.6486 | 0.4508 |
| B4 scene temporal | 0.6891 | 0.8212 | 0.7491 | 0.3655 |
| OURS assured output | 0.6838 | 0.8012 | 0.7376 | 0.3655 |

For B4, between-seed variability was non-zero: precision SD 0.0103, recall SD 0.0309, F1 SD 0.0151, and false-alert-rate SD 0.0205. The approximate 95% interval for B4 F1 was 0.7437--0.7545.

The central finding is therefore not a large increase in F1 over pairwise temporal reasoning. Relative to B2, B4 primarily improves alert selectivity: precision increases from 0.6757 to 0.6891 and false-alert rate decreases from 0.3936 to 0.3655, while recall decreases modestly from 0.8310 to 0.8212. The resulting F1 improvement is small (0.7451 to 0.7491). This supports the interpretation that scene-level reasoning acts mainly as a false-alert-control mechanism in the tested operating region.

## 2. Scene-coupling ablation

Removing graph coupling produced B4-like performance of precision 0.6873, recall 0.8308, F1 0.7520, and false-alert rate 0.3729.

Compared with FULL B4, graph coupling therefore introduces a measurable trade-off:

- false-alert rate improves from 0.3729 to 0.3655;
- precision improves slightly from 0.6873 to 0.6891;
- recall decreases from 0.8308 to 0.8212;
- F1 decreases slightly from 0.7520 to 0.7491.

Accordingly, coupling should **not** be presented as an unconditional accuracy improvement. Its supported role is conservative scene-level suppression of some alerts in densely coupled situations. In the current controlled ensemble, this improves selectivity at a small sensitivity cost.

## 3. Persistence and temporal stability

The deterministic mechanism-verification ablation showed that removing temporal persistence reduced B4 F1 from 0.7613 to 0.6540, reduced recall from 0.8252 to 0.7203, and increased false-alert rate from 0.3379 to 0.4759.

This was the strongest temporal ablation effect in the canonical benchmark. Persistence prevents isolated risk excursions from immediately changing scene state and is therefore a central component of temporal stabilization.

## 4. Hysteresis boundary-stress experiment

The main scenario suite did not materially activate the release-margin hysteresis mechanism. A dedicated threshold-chatter probe was therefore used.

A ten-update risk sequence oscillating around the WARNING/WATCH boundary produced:

- with hysteresis: 1 state transition;
- without hysteresis: 10 state transitions.

The hysteresis mechanism therefore reduced state chatter by 90% in the dedicated boundary-stress test. The supported claim is mechanism-specific: hysteresis suppresses repeated threshold crossings near a release boundary. It should not be claimed to improve aggregate F1 in the main benchmark.

## 5. Runtime assurance under degraded evidence

Across the controlled degraded-input suite, the runtime supervisor detected every injected degraded step (`degraded_input_detection_rate = 1.0`). It produced:

- overconfident critical rate = 0.0;
- inappropriate intervention rate = 0.0;
- 6 authority-capped steps;
- 9 `HUMAN_VERIFY` steps;
- 3 `FALLBACK` steps.

These assurance counts remained invariant across the 30 geometry-jitter seeds. This invariance reflects deterministic evidence-quality gates for the injected degraded-input conditions rather than independent real-world safety trials.

The assured operational output achieved precision 0.6838, recall 0.8012, F1 0.7376, and false-alert rate 0.3655. Its lower recall relative to latent B4 hazard state is expected because runtime assurance may deliberately withhold or downgrade automated hazard authority when evidence is insufficient.

## 6. Warning lead time and operational delay

Fifteen of the sixteen controlled scenarios contained a hazardous interval; the transient-false-positive scenario intentionally contained none.

Across all 30 geometry-jitter seeds, all six methods detected all 15 hazardous scenarios within the evaluation horizon (`scenario_detection_rate = 1.0`) and no method produced a late first detection (`late_detection_rate = 0.0`).

Mean warning lead times were:

| Method | Mean warning lead time (s) | Median lead time (s) |
|---|---:|---:|
| B0 CPA/TCPA | 110.0 | 120 |
| B1 pairwise static | 110.0 | 120 |
| B2 pairwise temporal | 93.87 | 90 |
| B3 scene static | 110.0 | 120 |
| B4 scene temporal | 93.67 | 90 |
| OURS assured output | 93.67 | 90 |

B4 mean lead time varied slightly across seeds (SD approximately 0.76 s). Most importantly, the runtime assurance layer introduced **zero additional first-action delay** relative to the latent B4 scene-hazard state in all 30 seeds: mean assurance delay = 0 s and maximum assurance delay = 0 s across the 15 comparable hazardous scenarios.

This directly supports the operational-usefulness hypothesis for the controlled benchmark: authority gating did not postpone the first actionable warning/verification output.

## 7. Computational scaling

End-to-end scene-processing latency was measured for dense radial synthetic scenes with increasing vessel counts. Each scene size was repeated 30 times.

| Vessels | Pairwise encounters | Mean latency (ms) | P95 (ms) | P99 (ms) | Max (ms) | Missed 1000-ms deadlines |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 1 | 0.0335 | 0.0402 | 0.0474 | 0.0494 | 0 |
| 5 | 10 | 0.1981 | 0.2086 | 0.2155 | 0.2180 | 0 |
| 10 | 45 | 0.8222 | 0.8846 | 0.9748 | 1.0020 | 0 |
| 20 | 190 | 3.8651 | 3.8853 | 8.8561 | 10.8852 | 0 |
| 40 | 780 | 15.8314 | 19.9466 | 23.8455 | 24.1318 | 0 |

The observed growth is consistent with the pairwise-interaction structure of the current implementation: 40 vessels yield 780 pairwise encounters. Despite this increase, P99 latency remained approximately 23.85 ms at 40 vessels, and no 1000-ms computational deadlines were missed.

These timing results characterize the specific execution environment used for the benchmark and should not be interpreted as a universal hard real-time guarantee. They do, however, demonstrate substantial computational headroom for the tested controlled scenes.

## 8. Hypothesis-level interpretation

### H1 -- Scene reasoning

**Partially supported.** Scene-temporal reasoning improves precision and reduces false-alert rate relative to pairwise temporal reasoning, but the F1 gain is small and recall is slightly lower. Graph coupling itself is a selectivity-versus-sensitivity trade-off rather than a monotonic accuracy improvement.

### H2 -- Temporal stability

**Supported at mechanism level.** Persistence has a large beneficial effect in the canonical benchmark, while the dedicated hysteresis probe reduces threshold chatter by 90%. The two temporal mechanisms address distinct failure modes: isolated excursions and repeated boundary crossings.

### H3 -- Runtime assurance

**Supported for the controlled degraded-input suite.** All injected degraded steps were detected, no overconfident `CRITICAL` output was produced, and no inappropriate intervention or fallback occurred under nominal conditions.

### H4 -- Operational usefulness

**Supported within the controlled benchmark.** The assured output preserved the same mean warning lead time as B4 (approximately 93.7 s), introduced zero additional first-action delay, and the pipeline remained well below the 1000-ms computational deadline up to 40 vessels in the tested environment.

## 9. Manuscript claim boundary

The manuscript should state that the experiments establish controlled mechanism verification and robustness under synthetic geometry/evidence perturbations. They do not establish:

- certified collision-avoidance safety;
- real-world VTS effectiveness;
- autonomous navigation performance;
- general hard real-time guarantees across hardware platforms;
- statistical independence equivalent to multiple real-world port trials.

## 10. Recommended Results structure

1. Progressive baseline performance and robustness across geometry-jitter seeds.
2. Component ablations: coupling, persistence, and dedicated hysteresis probe.
3. Runtime assurance under degraded AIS evidence.
4. Warning lead time and assurance delay.
5. Computational scaling.
6. Synthesis against H1--H4.

This structure cleanly separates hazard estimation from decision authority and avoids treating `FALLBACK` as a conventional detector miss.