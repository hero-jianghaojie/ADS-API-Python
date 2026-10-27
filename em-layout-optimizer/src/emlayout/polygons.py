"""Polygon-level editing helpers.

A layout is a flat list of polygons, each a list of (x, y) points in millimetres,
stored either as JSON or as a simple text file:

    # comment
    POLY  x0,y0  x1,y1  x2,y2  x3,y3

Edits are expressed as functions of the point list so they can be chained and
unit-tested; nothing here knows about any vendor file format.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

Point = tuple[float, float]
Polygon = list[Point]


@dataclass(frozen=True)
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    @property
    def h(self) -> float:
        return self.y1 - self.y0

    def contains(self, x: float, y: float, tol: float = 0.05) -> bool:
        return (self.x0 - tol <= x <= self.x1 + tol) and (self.y0 - tol <= y <= self.y1 + tol)

    def overlaps(self, other: "BBox", tol: float = 0.03) -> bool:
        return (min(self.x1, other.x1) - max(self.x0, other.x0) > -tol
                and min(self.y1, other.y1) - max(self.y0, other.y0) > -tol)


def bbox(poly: Sequence[Point]) -> BBox:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return BBox(min(xs), min(ys), max(xs), max(ys))


def load(path: str) -> list[Polygon]:
    """Load polygons from .json or the simple .poly text format."""
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return [[tuple(map(float, p)) for p in poly] for poly in data["polygons"]]
    polys: list[Polygon] = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.split("#", 1)[0].strip()
            if not line.upper().startswith("POLY"):
                continue
            pts: Polygon = []
            for tok in line[4:].split():
                x, y = tok.split(",")
                pts.append((float(x), float(y)))
            if len(pts) >= 3:
                polys.append(pts)
    return polys


def save(path: str, polys: Iterable[Polygon]) -> None:
    """Write polygons back in the same format that was read."""
    polys = list(polys)
    if path.lower().endswith(".json"):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"units": "mm", "polygons": [[list(p) for p in poly] for poly in polys]}, fh, indent=1)
        return
    with open(path, "w", encoding="utf-8") as fh:
        for poly in polys:
            fh.write("POLY  " + "  ".join(f"{x:.4f},{y:.4f}" for x, y in poly) + "\n")


def translate(poly: Polygon, dx: float = 0.0, dy: float = 0.0) -> Polygon:
    return [(x + dx, y + dy) for x, y in poly]


def stretch_edge(poly: Polygon, edge: str, delta: float) -> Polygon:
    """Move one edge of an axis-aligned polygon by delta (mm).

    edge is one of "left", "right", "bottom", "top"; the opposite edge stays put.
    """
    bb = bbox(poly)
    out: Polygon = []
    for x, y in poly:
        if edge == "left" and abs(x - bb.x0) < 1e-6:
            x += delta
        elif edge == "right" and abs(x - bb.x1) < 1e-6:
            x += delta
        elif edge == "bottom" and abs(y - bb.y0) < 1e-6:
            y += delta
        elif edge == "top" and abs(y - bb.y1) < 1e-6:
            y += delta
        out.append((x, y))
    return out


def select(polys: Sequence[Polygon], pred: Callable[[BBox], bool]) -> list[int]:
    """Indices of polygons whose bounding box satisfies pred."""
    return [i for i, poly in enumerate(polys) if pred(bbox(poly))]


def apply(polys: Sequence[Polygon], indices: Iterable[int],
          fn: Callable[[Polygon], Polygon]) -> list[Polygon]:
    """Return a new list where only the given indices are transformed."""
    keep = set(indices)
    return [fn(list(poly)) if i in keep else list(poly) for i, poly in enumerate(polys)]


def shift_group(polys: Sequence[Polygon], indices: Iterable[int],
                dy: float, anchor: str = "top") -> list[Polygon]:
    """Translate a set of polygons together, keeping them connected to the rest.

    This is the operation behind "make this line 0.5 mm longer": the segment that
    grows keeps one edge fixed, and every polygon downstream of it moves by the
    same amount, so the cascade stays physically joined.
    """
    return apply(polys, indices, lambda p: translate(p, 0.0, dy))


def summary(polys: Sequence[Polygon]) -> dict:
    n_rect = sum(1 for p in polys if len(p) == 4)
    xs = [bbox(p).x0 for p in polys] + [bbox(p).x1 for p in polys]
    ys = [bbox(p).y0 for p in polys] + [bbox(p).y1 for p in polys]
    return {
        "count": len(polys),
        "rectangles": n_rect,
        "polygons": len(polys) - n_rect,
        "bbox_mm": [min(xs), min(ys), max(xs), max(ys)],
    }