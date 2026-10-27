#!/usr/bin/env python3
"""Plot whole-band efficiency and output power from a saved results JSON."""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("results", help="results JSON: {name: [[f_GHz, pout_dBm, eff_pct], ...]}")
    ap.add_argument("--out", default="figs/compare", help="output path stem (writes .png and .svg)")
    ap.add_argument("--f-lo", type=float, default=1.6)
    ap.add_argument("--f-hi", type=float, default=2.6)
    ap.add_argument("--target", type=float, default=60.0)
    ap.add_argument("--title", default=None)
    args = ap.parse_args(argv)

    sys.path.insert(0, "src")
    from emlayout.plotting import plot, load_results, stats

    path = plot(args.results, args.out, f_lo=args.f_lo, f_hi=args.f_hi,
                target=args.target, title=args.title)
    data = load_results(args.results)
    for name, rows in data.items():
        s = stats(rows, args.f_lo, args.f_hi)
        if s:
            print(f"{name:<24} min {s['min_efficiency']:5.2f}% @ {s['min_freq']:.2f} GHz   "
                  f"mean {s['mean_efficiency']:5.2f}%   Pout_min {s['min_pout']:5.2f} dBm")
    print(f"figure: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())