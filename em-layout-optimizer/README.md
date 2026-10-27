# em-layout-optimizer

A small, tool-agnostic toolkit for **optimising the physical layout of RF/microwave boards from EM simulation results**:
edit polygons, keep the topology valid, run the solver, evaluate the circuit, plot the whole band, repeat.

It grew out of a real design loop for a coupled-line band-pass matching network, where the useful lessons were
mostly about *process* rather than about the circuit:

- a 0.1 GHz sweep can hide a 5-point notch, so every candidate has to be evaluated on a fine grid;
- moving one polygon usually breaks the topology, so every edit needs a connectivity gate;
- some "knobs" are physically dead (bias branches) and only the RF path matters;
- the harmonic-balance order changes efficiency by up to a point, so the calibration must be fixed and stated.

This repository packages those lessons as reusable code plus a methodology write-up.

## What is in the box

| Module | Purpose |
| --- | --- |
| `emlayout.polygons` | read / write a plain polygon list, rectangle & vertex edits, translate a group |
| `emlayout.connectivity` | island count, port-on-metal test, port-map comparison between two layouts |
| `emlayout.guard` | assertion helpers so a silent "nothing changed" edit cannot reach the solver |
| `emlayout.plotting` | dual-axis DE / Pout plots from a results JSON (PNG + SVG, English labels) |
| `scripts/run_batch.py` | run an external EM command over a list of candidates, in parallel |

Everything is plain Python 3.9+, `numpy` + `matplotlib` only. No vendor API is imported at package level;
vendor-specific adapters live behind optional modules and are loaded only when a project uses them.

## Quick start

```bash
pip install -r requirements.txt

# 1) check that two layouts differ AND keep the same connectivity
python -m emlayout.connectivity base.poly edited.poly --ports ports.json

# 2) plot a whole band from saved results (never re-runs the solver)
python scripts/plot_results.py examples/demo_results.json --out figs/demo
```

## The loop it supports

```
 choose knob  ->  edit polygons  ->  GUARD (did it change? islands? ports?)
      ^                                                   |
      |                                                   v
      +---- rank & pick  <---- plot whole band  <---- evaluate circuit
                                   ^                     |
                                   |                     v
                            results.json  <------  EM solver run
```

Details, including the four failure modes that cost the most time, are in
[`docs/methodology.md`](docs/methodology.md) and [`docs/pitfalls.md`](docs/pitfalls.md).
中文版见 [`docs/zh/methodology.md`](docs/zh/methodology.md)。

## Design principles

1. **Polygon level, not parameter level.** Generated layouts from a schematic-driven flow can stay valid;
   a hand-tuned one usually cannot, so this toolkit edits polygons directly and only commits an edit that
   passes the connectivity gate.
2. **Measure before you trust.** Every edit is compared against the base file; a run that did not change the
   geometry is aborted instead of being paid for.
3. **Save everything.** Each candidate keeps its geometry, its solver output and a JSON of the extracted
   metrics, so plots and reports are regenerated without re-simulating.
4. **State the calibration.** Band, resolution, drive level, bias and harmonic order are recorded with every
   result, because the same design moves by a point when any of them changes.

## Licence

MIT, see [LICENSE](LICENSE).