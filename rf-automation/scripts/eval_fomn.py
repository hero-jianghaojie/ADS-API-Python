# -*- coding: utf-8 -*-
"""FOMN CCF evaluator: score = fundamental + 2nd-harmonic distance to the continuous class-F
impedance space + out-of-band (3.5-7 GHz) suppression; tiny in-band term to stay a real filter.
Device side = Term1 (user), port2 terminated 50 ohm, Zin = 50(1+S11)/(1-S11)."""
import json, os, re, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np
sys.path.insert(0, r"${REPO_PARENT}")
from ads_sim_helper import run_hpeesofsim
from keysight.ads import dataset
WRK = r"${WORKSPACE}"
BASE = open(os.path.join(WRK, "sim", "usr", os.environ.get("FOMN_NET", "FOMN_ccf.net")), encoding="utf-8").read()
ROPT = float(os.environ.get("FOMN_ROPT", "30"))
BAND = (float(os.environ.get("FOMN_BAND_LO", "1.5")), float(os.environ.get("FOMN_BAND_HI", "3.5")))
STOP = (float(os.environ.get("FOMN_STOP_LO", "3.5")), float(os.environ.get("FOMN_STOP_HI", "7.0")))
# CCF 段（归一化 -> ohm）
# ★拓展空间: 把 R_opt 的不确定度并入 ⇒ 空间 = 一族 CCF 轨迹的并(基波扇形/二次带); 距离 = 对 rho 取最小(并集精确距离)
ROPT_LO = float(os.environ.get("FOMN_ROPT_LO", str(ROPT)))
ROPT_HI = float(os.environ.get("FOMN_ROPT_HI", str(ROPT)))
TOL = float(os.environ.get("FOMN_TOL", "0"))          # 容差(ohm): 距离小于 tol 视为已在空间内
_RHOS = np.unique(np.concatenate([[ROPT], np.linspace(min(ROPT_LO, ROPT_HI), max(ROPT_LO, ROPT_HI), 26)]))  # ★并入 ROPT 自身, 保证并集是窄空间的超集
Z1S = [(2.312*p, -2.002*p, 0.0) for p in _RHOS]
Z2S = [(0.0, 0.0, 3.181*p) for p in _RHOS]
def dist_space(z, segs, tol=0.0):
    d = min(dist_seg(z, re_, lo, hi) for (re_, lo, hi) in segs)
    return max(0.0, d - tol)
def net(vals):
    t = BASE
    for k, v in vals.items():
        t = re.sub(r"(?m)^" + k + r"=[-\d.eE+]+", "%s=%.4f" % (k, round(float(v), 1)), t, count=1)
    return t
def dist_seg(z, re_, im_lo, im_hi):
    return float(np.hypot(z.real-re_, z.imag - min(max(z.imag, im_lo), im_hi)))
def evaluate(vals, tag):
    r = run_hpeesofsim(net(vals), WRK, tag, timeout=900)
    if not r.get("ok"): return None
    d = dataset.open_dataset_for_reading(r["ds_path"])
    for k in d.keys():
        try: df = d.get(k).to_dataframe()
        except Exception: continue
        if "S[1,1]" not in [str(c) for c in df.columns]: continue
        f = np.asarray(df.index.get_level_values("freq").astype(float))/1e9
        s11 = np.asarray(df["S[1,1]"].values, complex); s21 = np.asarray(df["S[2,1]"].values, complex)
        Zin = 50.0*(1+s11)/(1-s11)
        d1 = []; d2 = []
        for f0 in np.arange(BAND[0], BAND[1]+1e-9, 0.1):
            i1 = int(np.argmin(np.abs(f-f0))); i2 = int(np.argmin(np.abs(f-2*f0)))
            d1.append(dist_space(Zin[i1], Z1S, TOL))
            d2.append(dist_space(Zin[i2], Z2S, TOL))
        st = (f > STOP[0]) & (f <= STOP[1])
        s21db = 20*np.log10(np.maximum(np.abs(s21), 1e-12))
        band = (f >= BAND[0]) & (f <= BAND[1])
        stop_max = float(s21db[st].max()); stop_mean = float(s21db[st].mean())
        pen_stop = max(0.0, stop_max + 20.0)              # 目标 <= -20 dB
        inband_def = max(0.0, float((-1.0) - np.mean(s21db[band])))   # 用均值,避免被带边深零点绑架
        stage = int(os.environ.get("FOMN_STAGE", "0"))
        wmax = float(os.environ.get("FOMN_WMAX", "0.5"))
        w2 = float(os.environ.get("FOMN_W2", "1.0"))                 # 2 次谐波权重(Stage1 设 0)
        w1 = float(os.environ.get("FOMN_W1", "1.0"))                 # 基波权重
        wout = float(os.environ.get("FOMN_WOUT", "8.0"))             # 带外权重(最差项为主)
        p1 = w1*(np.mean(d1)/ROPT + wmax*np.max(d1)/ROPT)
        p2 = w2*(np.mean(d2)/ROPT + wmax*np.max(d2)/ROPT)
        stop_t = float(os.environ.get("FOMN_STOP_T", "-15"))
        pen_stop_max = max(0.0, stop_max - stop_t)                   # 目标 <= stop_t dB(最差项)
        cost = p1 + p2 + wout*(pen_stop_max/20.0) + 0.1*inband_def
        return dict(cost=float(cost), d1_mean=float(np.mean(d1)), d1_max=float(np.max(d1)),
                    d2_mean=float(np.mean(d2)), d2_max=float(np.max(d2)),
                    stop_max=stop_max, stop_mean=stop_mean,
                    f=[float(x) for x in f], zin=[[float(z.real), float(z.imag)] for z in Zin],
                    s21db=[float(x) for x in s21db])
    return None
if __name__ == "__main__":
    v = json.load(open(sys.argv[1], encoding="utf-8"))
    r = evaluate(v, "ccfchk")
    if r: json.dump(r, open(sys.argv[2], "w"))
    print(json.dumps({k: r[k] for k in ("cost","d1_mean","d1_max","d2_mean","d2_max","stop_max")} if r else {"ok": False}))
