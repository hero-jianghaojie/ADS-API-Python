## ads-rf-automation v0.1.0

Scriptable **Keysight ADS** automation for RF power-amplifier / filter design:
dump & patch netlists, run simulations headlessly, optimise against explicit physical
objectives, verify three ways, and write results back safely.

### Highlights
- **Live ADS bridge** (`pb.py` + `scripts/ads_live_server.py`) — read designs and export netlists.
- **Simulation helper** (`scripts/ads_sim_helper.py`) with unique run tags for `hpeesofsim`.
- **Evaluators**: PA metrics (`eval_var.py`) and impedance-space distance (`eval_fomn.py`).
- **Optimisers**: pattern search with **rejection-based hard floors** (never trade away an
  already-met spec) — `pyopt_pa1_po39.py`, `pyopt_fomn_s2b.py`.
- **EM co-simulation notes**: `ModelReuse=1` semantics and the GUI-only geometry-regeneration wall.
- **Documentation set** (`docs/00`–`09`): environment, driving ADS, simulation口径, optimisation,
  EM co-simulation, figures, domain/CCF notes, **26 verified pitfalls**, project-status template.
- **Minimal examples** with a sweep-coverage guard.

### The three rules
1. The bridge dumps; a different process (ADS's own Python) simulates.
2. Assert sweep coverage — an out-of-range lookup clamps silently and returns plausible garbage.
3. Hard floors, not penalties — enforce already-met specs as rejections.

### Requirements
Keysight ADS (developed on 2025 Update 2) on Windows; two Python environments (bridge + ADS-bundled).

### Licence
MIT (code). Documentation as-is.
