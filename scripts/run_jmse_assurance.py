#!/usr/bin/env python3
"""Run the controlled JMSE scene-risk and runtime-assurance benchmark."""

import argparse
from pathlib import Path

from portguard_ais.evaluation.jmse_benchmark import write_jmse_benchmark


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="jmse_run")
    parser.add_argument("--steps", type=int, default=18)
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--seed", type=int, default=20260817)
    args = parser.parse_args()

    result = write_jmse_benchmark(
        Path(args.output_dir),
        steps=args.steps,
        interval_seconds=args.interval_seconds,
        seed=args.seed,
    )
    print("JMSE controlled benchmark complete")
    for item in result.methods:
        print(
            f"{item.method}: precision={item.precision:.3f} recall={item.recall:.3f} "
            f"f1={item.f1:.3f} false_alert_rate={item.false_alert_rate:.3f}"
        )
    print(
        "assurance: "
        f"degraded_steps={result.assurance.degraded_steps} "
        f"human_verify={result.assurance.human_verify_steps} "
        f"fallback={result.assurance.fallback_steps} "
        f"overconfident_critical={result.assurance.overconfident_critical_steps}"
    )


if __name__ == "__main__":
    main()
