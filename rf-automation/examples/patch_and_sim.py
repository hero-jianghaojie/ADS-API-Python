# -*- coding: utf-8 -*-
"""Example: patch variables in a netlist and simulate it with hpeesofsim.

    <ADS_PY> examples/patch_and_sim.py PA1.net vals.json

Note the two-rule discipline:
  * only the FIRST '^VAR=...' occurrence is replaced (route by name in real write-backs);
  * assert the sweep covers everything you intend to read afterwards.
"""
import json, os, re, sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from ads_sim_helper import run_hpeesofsim          # noqa: E402
from config import WORKSPACE                        # noqa: E402

net_file, vals_file = sys.argv[1], sys.argv[2]
text = open(net_file, encoding="utf-8").read()
for k, v in json.load(open(vals_file, encoding="utf-8")).items():
    text = re.sub(r"(?m)^" + re.escape(k) + r"=[-\d.eE+]+", "%s=%.4f" % (k, float(v)), text, count=1)

# guard: the sweep must cover the band you will read
lo = float(os.environ.get("BAND_LO", "1.5")); hi = float(os.environ.get("BAND_HI", "2.5"))
m = re.search(r"SweepPlan:\s*SP1_stim[^\n]*Start=([\d.]+)\s*GHz[^\n]*Stop=([\d.]+)\s*GHz", text)
if not m:
    print("WARN: could not find SP1_stim sweep range")
elif not (float(m.group(1)) <= lo and hi <= float(m.group(2))):
    print("WARN: sweep %s-%s does not cover %s-%s GHz --- values outside are MEANINGLESS" %
          (m.group(1), m.group(2), lo, hi))

r = run_hpeesofsim(text, WORKSPACE, "example", timeout=900)
print("ok=%s ds=%s err=%s" % (r.get("ok"), r.get("ds_path"), r.get("err")))
