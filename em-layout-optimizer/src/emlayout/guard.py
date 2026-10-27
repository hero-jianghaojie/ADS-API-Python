"""Guards that stop a no-op edit from being paid for in simulation time.

Two failures happened often enough to become code:

* an edit script that matched zero polygons and silently wrote the base file back;
* an edit that moved only the ports, leaving the metal untouched.

Both produce a screenshot that "looks fine" and a result that is identical to the
previous candidate. `assert_changed` catches them before the solver starts.
"""
from __future__ import annotations

import hashlib


def digest(obj) -> str:
    """Stable hash of a polygon list or of a results dict."""
    text = repr(obj)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def assert_changed(before, after, *, what: str = "layout", min_changed: int = 1) -> int:
    """Return the number of changed entries, raising when nothing moved."""
    if len(before) != len(after):
        raise AssertionError(f"{what}: length changed unexpectedly ({len(before)} -> {len(after)})")
    changed = sum(1 for a, b in zip(before, after) if a != b)
    if changed < min_changed:
        raise AssertionError(
            f"{what}: edit changed nothing - the selector matched no polygon. "
            "Check the pattern against the actual geometry before simulating."
        )
    return changed


def assert_differs(file_a: str, file_b: str) -> None:
    """Compare two written files byte-wise; cheap and impossible to fool."""
    with open(file_a, "rb") as fa, open(file_b, "rb") as fb:
        if fa.read() == fb.read():
            raise AssertionError(f"{file_a} and {file_b} are identical - the edit did not reach disk")