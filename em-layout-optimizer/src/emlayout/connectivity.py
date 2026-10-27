"""Connectivity gates for layout edits.

Two questions decide whether an edited layout may be sent to the solver:

1. does it still have the same number of separate metal islands?
2. does every port still sit on metal, and on the same island as before?

Both are O(n^2) union-find checks on bounding boxes, which is accurate enough for
manhattan layouts made of rectangles and simple polygons.
"""
from __future__ import annotations

import json
from typing import Sequence

from .polygons import BBox, Point, Polygon, bbox


class _DSU:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))

    def find(self, i: int) -> int:
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def islands(polys: Sequence[Polygon], tol: float = 0.03) -> list[int]:
    """Return the island id of every polygon (touching polygons share an id)."""
    boxes = [bbox(p) for p in polys]
    dsu = _DSU(len(polys))
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            if boxes[i].overlaps(boxes[j], tol):
                dsu.union(i, j)
    return [dsu.find(i) for i in range(len(polys))]


def island_count(polys: Sequence[Polygon], tol: float = 0.03) -> int:
    return len(set(islands(polys, tol)))


def port_islands(polys: Sequence[Polygon], ports: dict[str, Point], tol: float = 0.05) -> dict[str, int | None]:
    """Map each port to the island it touches, or None when it hangs in the air."""
    ids = islands(polys)
    boxes: list[BBox] = [bbox(p) for p in polys]
    out: dict[str, int | None] = {}
    for name, (x, y) in ports.items():
        hit = None
        for i, bb in enumerate(boxes):
            if bb.contains(x, y, tol):
                hit = ids[i]
                break
        out[name] = hit
    return out


def check_edit(base: Sequence[Polygon], edited: Sequence[Polygon],
               ports: dict[str, Point], tol: float = 0.03) -> dict:
    """Gate an edit. Returns a dict with ok / reason fields; never raises."""
    if len(base) != len(edited):
        return {"ok": False, "reason": "polygon count changed", "base": len(base), "edited": len(edited)}
    n0, n1 = island_count(base, tol), island_count(edited, tol)
    if n0 != n1:
        return {"ok": False, "reason": "island count changed", "base": n0, "edited": n1}
    pi0, pi1 = port_islands(base, ports), port_islands(edited, ports)
    floating = [k for k in ports if pi1[k] is None]
    if floating:
        return {"ok": False, "reason": "port not on metal", "ports": floating}
    moved = [k for k in ports if pi0[k] != pi1[k]]
    if moved:
        return {"ok": False, "reason": "port changed island", "ports": moved,
                "base": {k: pi0[k] for k in moved}, "edited": {k: pi1[k] for k in moved}}
    return {"ok": True, "islands": n1, "ports": len(ports)}


def load_ports(path: str) -> dict[str, Point]:
    """Ports as {"P1": [x_mm, y_mm], ...}."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    return {k: (float(v[0]), float(v[1])) for k, v in raw.items()}