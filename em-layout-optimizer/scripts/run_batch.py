#!/usr/bin/env python3
"""Run an external EM command over a list of candidate directories.

The command is a template, so the tool stays vendor-neutral:

    python scripts/run_batch.py candidates.txt \
        --cmd "mysolver -mesh fine -o {out} {project}" \
        --jobs 2

Each line of candidates.txt is a directory that contains the project to solve.
Runs are sequential per worker; {dir}, {out} and {name} are substituted.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import subprocess
import sys
import time


def run_one(directory: str, template: str, log_path: str) -> tuple[str, int, float]:
    out = os.path.join(directory, "out")
    os.makedirs(out, exist_ok=True)
    name = os.path.basename(os.path.normpath(directory))
    cmd = template.format(dir=directory, out=out, name=name)
    t0 = time.time()
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"$ {cmd}\n")
        rc = subprocess.call(cmd, shell=True, cwd=directory, stdout=log, stderr=subprocess.STDOUT)
    return name, rc, time.time() - t0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("candidates", help="text file, one directory per line")
    ap.add_argument("--cmd", required=True, help="command template")
    ap.add_argument("--jobs", type=int, default=1, help="parallel workers (1 = serial)")
    ap.add_argument("--log", default="run_batch.log")
    args = ap.parse_args(argv)

    with open(args.candidates, encoding="utf-8") as fh:
        dirs = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    if not dirs:
        print("no candidates", file=sys.stderr)
        return 2

    t0 = time.time()
    failures = 0
    with cf.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {pool.submit(run_one, d, args.cmd, args.log): d for d in dirs}
        for fut in cf.as_completed(futures):
            name, rc, sec = fut.result()
            print(f"{name:<28} rc={rc:<3} {sec:6.1f} s")
            failures += 0 if rc == 0 else 1
    print(f"done: {len(dirs)} candidates, {failures} failures, {time.time() - t0:.0f} s total")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())