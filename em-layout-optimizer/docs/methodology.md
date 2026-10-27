# Methodology: polygon-level layout optimisation against an EM solver

This note describes a complete optimisation loop that only needs three things:
an EM solver that can be driven from a command line, a way to edit the layout as
polygons, and a fixed evaluation harness. It is written tool-agnostically; the
companion code in `src/emlayout` implements the pieces that are easy to get wrong.

## 1. Choose the representation

There are two ways to change a layout:

| Route | When it works | When it fails |
| --- | --- | --- |
| Edit generator parameters, regenerate the layout | the whole layout is generated from a schematic and the generator is trustworthy | the layout is hand-tuned, or the generator produces different artwork than the one that was measured |
| Edit polygons directly | always, and preserves whatever the layout currently is | needs a connectivity gate, because a single edge change can open a gap |

A hand-tuned board is usually in the second row: regenerating it moves every
vertex and the measured response changes for reasons unrelated to the knob being
studied. Editing polygons keeps the comparison controlled, at the price of doing
connectivity bookkeeping (section 3).

## 2. Define the camera before touching anything

Every candidate must be scored with the same instrument. Write the calibration
down once and never change it silently:

```
band           1.6 - 2.6 GHz, 0.05 GHz step
drive          Pin = 30 dBm, fixed
bias           fixed DC values, recorded
harmonic order 5, oversampling >= 2 x order
terminations   50 ohm everywhere else
outputs        efficiency, output power, DC power, all saved
```

Two calibration details are worth calling out because they cost whole days:

- **Resolution.** A 0.1 GHz grid can step straight over a notch that is narrower
  than 0.1 GHz. In the case that motivated this toolkit, a 0.1 GHz sweep reported
  58.2 percent where a 0.05 GHz sweep found 53.2 percent 50 MHz away.
- **Harmonic order.** Truncating the expansion too early under-resolves the
  rectified DC current of a compressed device, which biases the efficiency low by
  roughly half a point to a full point. The order and the oversampling factor are
  part of the calibration, not a detail.

## 3. Gate every edit

A polygon edit is only admissible when all of the following hold:

1. **it changed something** (the selector matched at least one polygon, and the
   file on disk differs from the base file);
2. **the island count is unchanged** - a width change on one segment of a stepped
   chain opens a gap at the step, which the solver reports as an open circuit or
   refuses outright;
3. **every port still sits on metal, on the same island as before**.

```python
from emlayout import polygons, connectivity, guard

base = polygons.load("base.poly")
edited = polygons.apply(base, polygons.select(base, lambda b: b.w < 1.0),
                        lambda p: polygons.stretch_edge(p, "right", 0.2))
guard.assert_changed(base, edited)                      # gate 1
ports = connectivity.load_ports("ports.json")
assert connectivity.check_edit(base, edited, ports)["ok"]  # gates 2 and 3
```

## 4. Pick knobs by sensitivity, not by intuition

Not every dimension is a control. Ranking knobs by a one-off measurement saves
most of the simulation budget:

| Knob class | Typical effect | Reason |
| --- | --- | --- |
| open stubs on the RF path | **large** | they move a resonance, and a resonance can be several points deep |
| lengths in a cascaded RF chain | medium | they change the electrical phase of the whole downstream section |
| stubs on bias or sense branches | ~zero | the branch ends at a port terminated in 50 ohm, so it never loads the RF path |

A practical screening loop: pick one representative from each class, change it by
0.5 mm, and keep only the classes that move the metric by more than the
measurement repeatability.

## 5. Move resonances, do not hide them

If a dip is caused by a stub, its depth and position are set by the stub length:

```
stub 3.2 mm  ->  dip at 2.15 GHz, 53.5 %
stub 3.8 mm  ->  dip moved out of band, band minimum becomes 58.4 %
stub 4.4 mm  ->  dip reappears at 2.10 GHz, deeper
```

Two traps follow. First, a fine grid that happens to straddle the dip reports a
better minimum than the design really has - always state the grid. Second, if the
layout has no lossy element, the only way to remove a dip completely is to push
the resonance outside the band, which may simply create another one elsewhere.

## 6. Record, then plot, then decide

Each candidate keeps:

- the polygon file that was simulated,
- the solver output,
- a JSON of extracted metrics: `{name: [[f_GHz, pout_dBm, eff_pct], ...]}`.

Plots are regenerated from that JSON, never by re-running the solver, so a change
of axis or a different target line costs seconds. The decision is then made on the
whole band, not on the best point:

```bash
python scripts/plot_results.py results.json --f-lo 1.6 --f-hi 2.6 --target 60
```

## 7. When to stop

A useful stopping rule is: stop when the remaining shortfall is smaller than the
arithmetic uncertainty of the calibration (grid resolution, solver mesh, harmonic
order). Chasing the last few tenths of a point through geometry alone usually
produces designs that are impossible to manufacture - in the case behind this
toolkit, moving a coupling gap by 0.01 mm cost 7.6 points, which set the
manufacturing tolerance far tighter than the optimisation step.