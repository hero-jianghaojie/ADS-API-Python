#!/usr/bin/env python3
"""Self-test: the three gates must accept a valid edit and reject the bad ones."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from emlayout import connectivity, guard, polygons  # noqa: E402


def main() -> int:
    base = polygons.load(os.path.join(ROOT, "examples", "demo_layout.poly"))
    ports = connectivity.load_ports(os.path.join(ROOT, "examples", "demo_ports.json"))

    idx = polygons.select(base, lambda b: abs(b.w - 0.8) < 0.05 and b.h > 2.5)
    edited = polygons.apply(base, idx, lambda p: polygons.stretch_edge(p, "top", 0.3))
    touched = guard.assert_changed(base, edited, what="stub length")
    assert touched == 3, touched
    assert connectivity.check_edit(base, edited, ports)["ok"]

    try:
        guard.assert_changed(base, base, what="noop")
    except AssertionError:
        pass
    else:
        raise SystemExit("guard did not reject a no-op edit")

    broken = polygons.apply(base, [4], lambda p: polygons.translate(p, dx=5.0))
    assert not connectivity.check_edit(base, broken, ports)["ok"]

    floating = {"P1": (-20.0, 4.5), "P2": (26.0, 4.5)}
    assert not connectivity.check_edit(base, base, floating)["ok"]

    print("selftest ok: valid edit accepted, no-op / open-circuit / floating port rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())