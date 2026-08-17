#!/usr/bin/env python3
"""Run the multi-seed JMSE robustness and ablation campaign."""

import argparse
from pathlib import Path

from portguard_ais.evaluation.jmse_campaign import write_jmse_campaign


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="jmse_campaign")
    parser.add_argument("--seed-count", type=int, default=30)
    parser.add_argument("--base-seed", type=int, default=20260817)
    parser.add_argument("--steps", type=int, default=18)
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument(
        "--position-jitter-nm",
        type=float,
        default=0.08,
        help="Per-vessel trajectory offset standard deviation in nautical miles.",
    )
    args = parser.parse_args()

    rows = write_jmse_campaign(
        Path(args.output_dir),
        seed_count=args.seed_count,
        base_seed=args.base_seed,
        steps=args.steps,
        interval_seconds=args.interval_seconds,
        position_jitter_nm=args.position_jitter_nm,
    )
    print("JMSE stochastic geometry campaign complete")
    print(f"rows={len(rows)}")
    print(f"position_jitter_nm={args.position_jitter_nm}")
    print(f"output_dir={args.output_dir}")


if __name__ == "__main__":
    main()
