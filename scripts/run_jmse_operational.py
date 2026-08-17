#!/usr/bin/env python3
"""Run JMSE lead-time, assurance-delay, and runtime-scaling experiments."""

import argparse
from pathlib import Path

from portguard_ais.evaluation.jmse_operational import write_operational_results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="jmse_operational")
    parser.add_argument("--seed-count", type=int, default=30)
    parser.add_argument("--base-seed", type=int, default=20260817)
    parser.add_argument("--steps", type=int, default=18)
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--position-jitter-nm", type=float, default=0.08)
    parser.add_argument("--scaling-repeats", type=int, default=30)
    args = parser.parse_args()

    write_operational_results(
        Path(args.output_dir),
        seed_count=args.seed_count,
        base_seed=args.base_seed,
        steps=args.steps,
        interval_seconds=args.interval_seconds,
        position_jitter_nm=args.position_jitter_nm,
        scaling_repeats=args.scaling_repeats,
    )
    print("JMSE operational evaluation complete")
    print(f"output_dir={args.output_dir}")


if __name__ == "__main__":
    main()
