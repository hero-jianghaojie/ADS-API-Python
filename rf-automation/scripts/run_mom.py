# -*- coding: utf-8 -*-
"""Run a Momentum EM simulation from the command line on any work directory.

`bin\\adsMomWrapper.bat` is the Momentum engine; a directory that already holds a
`proj.*` input set (proj_a / proj.ltd / proj.sub / proj.sti / proj.opt / proj.pin /
proj.prt) can be re-solved without the ADS GUI or the EM plugin.

Stale results are removed first, using a WHITELIST of inputs: anything not known
to be an input is deleted.  (A blacklist silently misses files; the whole point of
this step is that a leftover proj.sio or proj.cti makes a failed run look like a
successful one, or makes -3D reuse the previous answer.)

The edge mesh is switched ON by default (auto-determined width).  With sheet conductors it
puts a dense cell pattern along metal and slot edges and leaves the interior coarse, which is
where most of the current flows: on a 1.2 GHz notch stub it moved the notch by ~30 MHz and
changed S21 by up to 4.4 dB.  Use --edge-mesh off to reproduce the old, coarser runs.

Usage:
    python run_mom.py <workdir> [--mode full|solve|mesh|dataset] [--keep]
                     [--cpw N] [--edge-mesh auto|off|<width_mm>]
"""
import argparse
import os
import re
import subprocess
import sys
import time

ADS = r"${ADS_HOME}"

MODES = {
    "full": (["-O", "-3D"], "full flow: preprocess + mesh + S-params (re-meshes)"),
    "solve": (["-3D"], "solve only (reuse the existing mesh)"),
    "mesh": (["-O", "-M"], "stop after mesh generation"),
    "dataset": (["-CD"], "package the existing results into a dataset"),
}

INPUTS = {
    "proj_a", "proj.cfg", "proj.dbw", "proj.ltd", "proj.opt", "proj.opto",
    "proj.pin", "proj.prt", "proj.sti", "proj.sub", "proj.toi", "proj_t3D.opt",
    "momentum.cfg", "design.xml", "proj.json", "proj_ref.json", "hash.json",
    "adsMultiTechData.json", "exprDict.json", "varDict.json",
}


def env():
    e = dict(os.environ)
    e["HPEESOF_DIR"] = ADS
    e["SIMARCH"] = "win32_64"
    e["PATH"] = os.pathsep.join([os.path.join(ADS, "bin"),
                                 os.path.join(ADS, "bin", "win32_64"),
                                 e.get("PATH", "")])
    return e


def set_edge_mesh(text, mode):
    """Rewrite the edge-mesh setting of a `proj.opt`.

    The preprocessor writes `EDGEMESH_BORDERWIDTH OFF;` (and the solver later resolves it to
    `edgemesh_borderwidth 0 METRE;`); both mean no edge mesh.  `edgemesh_borderwidth AUTO;`
    turns it on with an auto-determined width and `<value> METRE` sets the width explicitly --
    those two literals come straight out of the strings inside MomEngine.exe.
    """
    m = str(mode).strip().lower()
    if m in ("off", "none", "false", "0"):
        repl = "edgemesh_borderwidth 0 METRE;"
    elif m in ("auto", "on", "true"):
        repl = "edgemesh_borderwidth AUTO;"
    else:
        repl = "edgemesh_borderwidth %s METRE;" % mode

    setting = re.compile(r"(?im)^[ \t]*EDGEMESH_BORDERWIDTH[^\n;]*;")
    if setting.search(text):
        return setting.sub(lambda _m: repl, text, count=1)
    # the setting is absent (a work directory that was never patched): put it next to the density
    anchor = re.compile(r"(?im)^[ \t]*NO_CELLS_PER_WAVELENGTH[^\n;]*;")
    if anchor.search(text):
        return anchor.sub(lambda mo: mo.group(0) + "\n" + repl, text, count=1)
    return repl + "\n" + text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir")
    ap.add_argument("--mode", default="full", choices=sorted(MODES))
    ap.add_argument("--keep", action="store_true", help="do not delete stale results")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--cpw", type=int, default=None,
                    help="cells per wavelength: RFPro's preset uses 40, the work directories "
                         "that came out of an older run carry 20.  Overrides proj.opt.")
    ap.add_argument("--edge-mesh", default="auto", metavar="MODE",
                    help="'auto' (default) = edge mesh on with an auto-determined width, "
                         "'off' = disabled, or an explicit width in mm")
    args = ap.parse_args()

    exe = os.path.join(ADS, "bin", "adsMomWrapper.bat")
    if not os.path.isfile(exe):
        print("FAIL: adsMomWrapper not found at", exe)
        return 2
    wd = os.path.abspath(args.workdir)
    for f in ("proj_a", "proj.opt", "proj.ltd", "proj.sub", "proj.sti", "proj.pin", "proj.prt"):
        if not os.path.isfile(os.path.join(wd, f)):
            print(f"FAIL: missing input file {f} in {wd}")
            return 3

    if not args.keep:
        gone = []
        for name in sorted(os.listdir(wd)):
            p = os.path.join(wd, name)
            if os.path.isfile(p) and name not in INPUTS:
                os.remove(p)
                gone.append(name)
        print(f"removed {len(gone)} stale file(s): {', '.join(gone) if gone else '-'}")

    opt = os.path.join(wd, "proj.opt")
    text = open(opt, encoding="utf-8", errors="replace").read()
    new = text
    if args.cpw is not None:
        new = re.sub(r"no_cells_per_wavelength\s+\d+",
                     "no_cells_per_wavelength %d" % args.cpw, new)
        new = re.sub(r"NO_CELLS_PER_WAVELENGTH\s+\d+",
                     "NO_CELLS_PER_WAVELENGTH %d" % args.cpw, new)
    new = set_edge_mesh(new, args.edge_mesh)
    if new != text:
        open(opt, "w", encoding="utf-8").write(new)
        print("proj.opt patched: cpw=%s  edge-mesh=%s" % (args.cpw, args.edge_mesh))

    cmd = [exe] + MODES[args.mode][0] + ["proj", "proj"]
    print(f"adsMomWrapper {' '.join(MODES[args.mode][0])} proj proj   (cwd={wd})")
    t0 = time.time()
    r = subprocess.run(cmd, cwd=wd, env=env(), capture_output=True, text=True,
                       errors="replace", timeout=args.timeout)
    dt = time.time() - t0
    print(f"exit code = {r.returncode}, elapsed {dt:.1f} s")

    out = (r.stdout or "") + (r.stderr or "")
    interesting = [ln for ln in out.splitlines()
                   if any(k in ln.lower() for k in
                          ("error", "invalid", "fail", "warning", "finished", "not fully"))]
    for ln in interesting[-15:]:
        print("   ", ln.strip())

    for f in ("proj.cti", "proj.sio"):
        p = os.path.join(wd, f)
        print(f"{f}: {os.path.getsize(p)} B" if os.path.isfile(p) else f"{f}: not produced")
    return 0 if r.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
