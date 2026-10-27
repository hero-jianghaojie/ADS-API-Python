# -*- coding: utf-8 -*-
"""FOMN stage-2: drive the 2nd harmonic (3-5GHz) into the EXPANDED CCF space (R_opt fan, tol=0.15*Ropt).
   Hard guards: stopband <= -20 dB, fundamental distance small. Objective = 2nd-harmonic distance."""
import json, os, subprocess, sys, time, warnings
warnings.filterwarnings("ignore")
import numpy as np
NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
PY = r"${ADS_PY}"; EV = r"<REPO_PARENT>/_lbq2/eval_fomn.py"; NET = "FOMN_wide.net"
TMP = r"<REPO_PARENT>/_lbq2/fomn_s2"; os.makedirs(TMP, exist_ok=True)
ROPT = 30.0; TOL = 0.15*ROPT
D1_FLOOR = 8.0; STOP_FLOOR = -20.0
names = ["O_TL20_W","O_TL20_L","O_TL21_W","O_TL21_L","O_TL22_W","O_TL22_L","O_TL24_W","O_TL24_L","O_TL25_W","O_TL25_L","FLT_W","FLT_CL_S1","FLT_CL_S2","FLT_CL_L","FLT_L1","FLT_L2","FLT_L3","FLT_STUB_W","FEED_W","FEED_L","STUB_D2","IN_BR_L","RSTUB_W","RSTUB_L","OUT_W","OUT_L1","OUT_L2"]
lb = np.array([0.3,0.2,0.3,0.2,0.3,0.2,0.3,0.5,0.3,0.5,0.2,0.05,0.05,4,2,1,0.1,0.15,0.3,0.2,0,1,0.15,0.5,0.3,0.2,0.2])
ub = np.array([3.5,15,3.5,15,3.5,10,3.5,20,3.5,15,3,0.8,1,32,25,15,4,2.5,3.5,10,4,20,2.5,12,4,12,12])
x = np.array([1.6,6,3.2,6,2.2,0.8,1.2,8.4,1.1,1.3,0.4,0.1,0.1,19.7,10.2,5.4,0.1,0.4,1.7,0.9,0,6.8,0.4,4.2,1.6,3.3,4.3])
env = dict(os.environ); env.update({"PYTHONIOENCODING":"utf-8","FOMN_NET":NET,"FOMN_ROPT":"30",
  "FOMN_ROPT_LO":"26","FOMN_ROPT_HI":"40","FOMN_TOL":str(TOL),
  "FOMN_BAND_LO":"1.5","FOMN_BAND_HI":"2.5","FOMN_STOP_LO":"5.2","FOMN_STOP_HI":"8.0"})
N=[0]
def cost(v, tag):
    N[0]+=1
    i=os.path.join(TMP,tag+"_i.json"); o=os.path.join(TMP,tag+"_o.json")
    json.dump({k:float(y) for k,y in zip(names,v)}, open(i,"w"))
    try:
        subprocess.run([PY,EV,i,o,NET], env=env, timeout=900, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WIN, cwd=r"${REPO_PARENT}")
        r=json.load(open(o))
    except Exception: return None
    if not r or r.get("cost") is None: return None
    if r["stop_max"] > STOP_FLOOR: return None      # ★阻带硬地板
    if r["d1_mean"] > D1_FLOOR:   return None       # ★基波硬地板(已达标项不得被卖)
    return dict(c=r["cost"], d1m=r["d1_mean"], d1x=r["d1_max"], d2m=r["d2_mean"], d2x=r["d2_max"], st=r["stop_max"])
cur=cost(x,"s")
if cur is None: print("[FATAL] start infeasible/failed", flush=True); sys.exit(1)
best,bx=cur["c"],x.copy()
print("[start] cost=%.3f d1mean=%.2f d1max=%.2f d2mean=%.2f d2max=%.2f stop=%.1f (tol=%.1f)" %
      (best,cur["d1m"],cur["d1x"],cur["d2m"],cur["d2x"],cur["st"],TOL), flush=True)
t0=time.time(); step=(ub-lb)*0.10; sweep=0
while sweep<12 and time.time()-t0<2400:
    sweep+=1; improved=False
    order=list(range(len(names))); np.random.default_rng(20261+sweep).shuffle(order)
    for i2 in order:
        s=step[i2]
        if s < (ub[i2]-lb[i2])*0.004: continue
        for sign in (1,-1):
            mult=1.0
            while mult<=4.0:
                v=x.copy(); v[i2]=float(np.clip(x[i2]+sign*s*mult, lb[i2], ub[i2]))
                if abs(v[i2]-x[i2])<1e-6: break
                r=cost(v,"e")
                if r is not None and r["c"]<best-1e-5:
                    best,x,bx,improved=r["c"],v.copy(),v.copy(),True
                    print("[S%02d %-12s %+d x=%.1f] cost=%.3f d1mean=%.2f d1max=%.2f d2mean=%.2f d2max=%.2f stop=%.1f (n=%d %.0fs)" %
                          (sweep,names[i2],sign,v[i2],best,r["d1m"],r["d1x"],r["d2m"],r["d2x"],r["st"],N[0],time.time()-t0), flush=True)
                    mult*=2.0
                else: break
    step*=0.5
    print("[sweep %d done] best=%.3f n=%d %.0fs" % (sweep,best,N[0],time.time()-t0), flush=True)
    if not improved and step.max()<0.003: break
out={k:float(y) for k,y in zip(names,bx)}
json.dump(out, open(r"<REPO_PARENT>/_lbq2/py_best_fomn_s2.json","w"), indent=1)
print("[DONE] cost=%.3f after %d evals (%.0fs)" % (best,N[0],time.time()-t0), flush=True)
print("OK")
