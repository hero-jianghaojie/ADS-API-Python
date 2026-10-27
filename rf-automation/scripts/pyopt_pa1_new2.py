# -*- coding: utf-8 -*-
"""PA1 (modified schematic, Gap1 EXCLUDED) pattern search: 29 vars, hard Pmin>=38."""
import json, os, subprocess, sys, time, warnings
NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
warnings.filterwarnings("ignore")
import numpy as np
PY = r"${ADS_PY}"; EV = r"<REPO_PARENT>/_lbq2/eval_var.py"; NET = "PA1_new2.net"
TMP = r"<REPO_PARENT>/_lbq2/psnew2"; os.makedirs(TMP, exist_ok=True)
names = ["O_TL20_W","O_TL20_L","O_TL21_W","O_TL21_L","O_TL22_W","O_TL22_L","O_TL24_W","O_TL24_L","O_TL25_W","O_TL25_L","O_TL147_L","O_TL23_W","O_TL23_L","FEED_W","FEED_L","IN_BR_L","RSTUB_W","RSTUB_L","FLT_L1","FLT_L2","FLT_L3","FLT_STUB_W","STUB_D2","w_line5","l_b1","l_b2","B2_L","B3_L","B4_L"]
lb = np.array([0.3,0.2,0.3,0.2,0.3,0.2,0.3,0.5,0.3,0.5,3.1,0.3,0.2,0.3,0.2,1,0.15,0.5,2,1,0.1,0.15,0,0.3,1,0.5,0.5,0.5,0.5])
ub = np.array([3.5,15,3.5,15,3.5,10,3.5,20,3.5,15,30,3.5,10,3.5,10,20,2.5,12,25,15,4,2.5,4,8,20,20,15,15,20])
x = np.array([0.9,4.5,2.7,5.1,2,2.3,1.3,8,1.3,1.9,10,2.7,2.3,1.5,1.1,1.8,0.3,6.2,7.8,1,0.4,0.4,0,1.6,8.5,8.5,3,3,5])
env = dict(os.environ); env.update({"PYTHONIOENCODING":"utf-8","HB_ORDER":"3","HB_MAX":"4","STRIP_ANNOT":"1","ROUND1":"1",
                                    "EV_BAND_LO":"1.5","EV_BAND_HI":"2.5","EV_NPTS":"21"})
N=[0]
def cost(v, tag):
    N[0]+=1
    i=os.path.join(TMP,tag+"_i.json"); o=os.path.join(TMP,tag+"_o.json")
    json.dump({k:float(y) for k,y in zip(names,v)}, open(i,"w"))
    try:
        subprocess.run([PY,EV,i,o,NET], env=env, timeout=900, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WIN)
        r=json.load(open(o))
    except Exception: return None
    if not r.get("ok"): return None
    de=np.array(r["de"],float); p=np.array(r["p"],float)
    if p.min() < 38.0: return None
    d1=np.maximum(0.0,60.0-de)
    return dict(c=float(d1.mean())+1.0*float(d1.max())+0.05*float((de<60).sum())-0.05*float(de.mean()),
                dm=float(de.mean()), dn=float(de.min()), pm=float(p.min()), ns=int((de<60).sum()))
cur=cost(x,"s")
if cur is None: print("[FATAL] start failed", flush=True); sys.exit(1)
best,bx=cur["c"],x.copy()
print("[start] cost=%.3f DEmean=%.2f DEmin=%.2f below60=%d Pmin=%.2f" % (best,cur["dm"],cur["dn"],cur["ns"],cur["pm"]), flush=True)
t0=time.time(); step=(ub-lb)*0.10; sweep=0
while sweep<10 and time.time()-t0<2400:
    sweep+=1; improved=False
    order=list(range(len(names))); np.random.default_rng(4242+sweep).shuffle(order)
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
                    print("[S%02d %-12s %+d x=%.1f] cost=%.3f DEmean=%.2f DEmin=%.2f below60=%d Pmin=%.2f (n=%d %.0fs)" %
                          (sweep,names[i2],sign,v[i2],best,r["dm"],r["dn"],r["ns"],r["pm"],N[0],time.time()-t0), flush=True)
                    mult*=2.0
                else: break
    step*=0.5
    print("[sweep %d done] best=%.3f n=%d %.0fs" % (sweep,best,N[0],time.time()-t0), flush=True)
    if not improved and step.max()<0.003: break
out={k:float(y) for k,y in zip(names,bx)}
json.dump(out, open(r"<REPO_PARENT>/_lbq2/py_best_pa1_new2.json","w"), indent=1)
print("[DONE] cost=%.3f after %d evals (%.0fs)" % (best,N[0],time.time()-t0), flush=True)
print("OK")
