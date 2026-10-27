# Pitfalls that cost the most time

A short list of failure modes seen while running this loop for real. Each one
looks like a solver bug until it does not.

## 1. The edit that never reached the file

**Symptom.** A new candidate evaluates to exactly the same numbers as the previous
one, to several decimal places.

**Cause.** The build script edited the in-memory polygon list and then wrote only
the port file - or wrote the polygons to a copy that the solver never read.
Because the ports moved, the solver output has a different hash and everything
*looks* like it ran.

**Detection.** Compare the geometry files byte-wise before trusting the run; a
changed solver output hash alone proves nothing.

```python
guard.assert_changed(base_polys, edited_polys, what="stub length")
guard.assert_differs("base.poly", "edited.poly")
```

## 2. The selector that matched nothing

**Symptom.** Same as above.

**Cause.** The pattern was written for one branch of the design family (for
example, a 3.4 mm stub) and applied to another branch where the stub is 3.0 mm.
The edit silently became a no-op.

**Detection.** Always assert that the edit returned a non-zero count; print the
number of touched polygons in the build log.

## 3. The cascade that opened a gap

**Symptom.** The solver exits after a few seconds, or the extracted circuit shows
an open circuit where there was a line.

**Cause.** Lengthening one segment of a chain requires moving everything
downstream by the same amount. If the downstream set is defined by a bounding-box
predicate that is slightly too broad (or too narrow), either unrelated polygons
move - usually including a port - or one polygon stays behind and a gap appears.

**Detection.** Island count and port-island map before and after. In one attempt a
port at x = 0 fell off the metal because an input tee had been shifted by mistake;
the port-map check caught it before the solver did.

## 4. The resolution that flattered the design

**Symptom.** Two sweeps of the same design disagree by several points.

**Cause.** A notch narrower than the sweep step. The coarse sweep reports the
neighbouring points.

**Detection.** Evaluate on at least 0.05 GHz, and plot the curve rather than
reporting only the minimum: the shape tells you whether the minimum is a plateau
or a spike.

## 5. The calibration that moved

**Symptom.** The same design and the same EM data give different efficiency in
two runs.

**Cause.** Harmonic order or oversampling changed between runs. A compressed
device needs enough harmonics to represent the rectified current; with too few,
the DC power is overestimated and the efficiency drops by up to a point.

**Detection.** Put the order and oversampling factor in the results metadata and
refuse to compare results recorded with different values.

## 6. The knob that was not a knob

**Symptom.** Hours of sweeps, no change.

**Cause.** The dimension belonged to a bias or sense branch that terminates in a
50 ohm port. Changing it by half a millimetre moved the efficiency by 0.02 points.

**Detection.** Before sweeping a family, change one member by 0.5 mm and measure.
If the response is flat, stop - the whole family is dead weight.