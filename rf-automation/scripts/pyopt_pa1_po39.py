# -*- coding: utf-8 -*-
"""PA1: hard specs DE>=60% (all 21 pts) AND Pout>=39 dBm (all 21 pts); objective = maximise mean DE."""
import json, os, subprocess, sys, time, warnings
warnings.filterwarnings("ignore")
import numpy as np
NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
PY = r"${ADS_PY}"; EV = r"<REPO_PARENT>/_lbq2/eval_var.py"; NET = "PA1_de62.net"
TMP = r"<REPO_PARENT>/_lbq2/po39"; os.makedirs(TMP, exist_ok=True)
DE_MIN, PO_MIN = 60.0, 39.0
names = ["O_TL20_W","O_TL20_L","O_TL21_W","O_TL21_L","O_TL22_W","O_TL22_L","O_TL24_W","O_TL24_L","O_TL25_W","O_TL25_L","O_TL147_L","O_TL23_W","O_TL23_L","FEED_W","FEED_L","IN_BR_L","RSTUB_W","RSTUB_L","FLT_L1","FLT_L2","FLT_L3","FLT_STUB_W","STUB_D2","w_line5","l_b1","l_b2","B2_L","B3_L","B4_L"]
lb = np.array([0.3,0.2,0.3,0.2,0.3,0.2,0.3,0.5,0.3,0.5,3.1,0.3,0.2,0.3,0.2,1,0.15,0.5,2,1,0.1,0.15,0,0.3,1,0.5,0.5,0.5,0.5])
ub = np.array([3.5,15,3.5,15,3.5,10,3.5,20,3.5,15,30,3.5,10,3.5,10,20,2.5,12,25,15,4,2.5,4,8,20,20,15,15,20])
x = np.array([0.9,4.6,2.7,5,3.2,0.2,1.3,7.9,1.3,1.9,10.2,1.8,1.4,1.5,0.3,3.1,0.2,7.8,7.8,1,0.4,0.3,0,2,11.6,5,0.5,0.5,0.5])
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
    if de.min() < DE_MIN:            # ★硬地板: DE 任一点低于 60% 即不可行
        return None
    dp=np.maximum(0.0, PO_MIN-p)
    # 双硬指标: 缺额高权重(先补违规) + 达标后最大化平均 DE
    nde=int((de<DE_MIN).sum()); npo=int((p<PO_MIN).sum())
    c = 30.0*dp.max() + 15.0*dp.mean() + 5.0*npo - 0.05*de.mean()
    return dict(c=c, dm=float(de.mean()), dn=float(de.min()), pm=float(p.min()), pma=float(p.mean()),
                nde=int((de<DE_MIN).sum()), npo=int((p<PO_MIN).sum()))
cur=cost(x,"s")
if cur is None: print("[FATAL] start failed", flush=True); sys.exit(1)
best,bx=cur["c"],x.copy()
print("[start] cost=%.3f DEmean=%.2f DEmin=%.2f Pmean=%.2f Pmin=%.2f (need DE>=60, Pout>=39) | 违规 DE %d 点 / Pout %d 点" %
      (best,cur["dm"],cur["dn"],cur["pma"],cur["pm"],cur["nde"],cur["npo"]), flush=True)
t0=time.time(); step=(ub-lb)*0.08; sweep=0
while sweep<12 and time.time()-t0<3000:
    sweep+=1; improved=False
    order=list(range(len(names))); np.random.default_rng(555+sweep).shuffle(order)
    for i2 in order:
        s=step[i2]
        if s < (ub[i2]-lb[i2])*0.003: continue
        for sign in (1,-1):
            mult=1.0
            while mult<=4.0:
                v=x.copy(); v[i2]=float(np.clip(x[i2]+sign*s*mult, lb[i2], ub[i2]))
                if abs(v[i2]-x[i2])<1e-6: break
                r=cost(v,"e")
                if r is not None and r["c"]<best-1e-5:
                    best,x,bx,improved=r["c"],v.copy(),v.copy(),True
                    print("[S%02d %-12s %+d x=%.1f] cost=%.3f DEmean=%.2f DEmin=%.2f Pmin=%.2f 违规(DE/Pout)=%d/%d (n=%d %.0fs)" %
                          (sweep,names[i2],sign,v[i2],best,r["dm"],r["dn"],r["pm"],r["nde"],r["npo"],N[0],time.time()-t0), flush=True)
                    mult*=2.0
                else: break
    step*=0.5
    print("[sweep %d done] best=%.3f n=%d %.0fs" % (sweep,best,N[0],time.time()-t0), flush=True)
    if not improved and step.max()<0.002: break
out={k:float(y) for k,y in zip(names,bx)}
json.dump(out, open(r"<REPO_PARENT>/_lbq2/py_best_pa1_po39.json","w"), indent=1)
print("[DONE] cost=%.3f after %d evals (%.0fs)" % (best,N[0],time.time()-t0), flush=True)
print("OK")
