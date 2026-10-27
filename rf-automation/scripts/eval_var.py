import os
# -*- coding: utf-8 -*-
"""FPA_V3 评估器：输入 JSON(变量值) -> 生成网表 -> hpeesofsim -> 输出指标 JSON。
用法: python eval_fpav3.py in.json out.json"""
import json, os, re, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np
sys.path.insert(0, r"${REPO_PARENT}")
from ads_sim_helper import run_hpeesofsim
from keysight.ads import dataset

WRK = r"${WORKSPACE}"
OUT = os.path.join(WRK, "sim", "usr")
SRC = sys.argv[3] if len(sys.argv) > 3 else "ADS_Auto_lib_FPA_V3.net"
BASE = open(os.path.join(OUT, SRC), encoding="utf-8").read()
# HB 阶数：默认只算到 3 次谐波（实际中更高次影响很小，且收敛更快）；可用 HB_ORDER/HB_MAX 覆盖做对照
HB_ORDER = int(os.environ.get("HB_ORDER", "3"))
HB_MAX = int(os.environ.get("HB_MAX", "4"))
BASE = re.sub(r"MaxOrder=\d+", "MaxOrder=%d" % HB_MAX, BASE, count=1)
BASE = re.sub(r"Order\[1\]=\d+", "Order[1]=%d" % HB_ORDER, BASE, count=1)
if "FundOversample=" in BASE:
    BASE = re.sub(r"FundOversample=\d+", "FundOversample=8", BASE, count=1)
else:
    BASE = re.sub(r"(HB:\w+[^\n]*)", r"\1 FundOversample=8", BASE, count=1)
B_LO = float(os.environ.get("EV_BAND_LO", "1.5"))
B_HI = float(os.environ.get("EV_BAND_HI", "3.5"))
B_N  = int(os.environ.get("EV_NPTS", "21"))
if re.search(r"(?m)^freq_low=", BASE):
    BASE = re.sub(r"(?m)^freq_low=[-\d.]+", "freq_low=%g" % B_LO, BASE, count=1)
    BASE = re.sub(r"(?m)^freq_high=[-\d.]+", "freq_high=%g" % B_HI, BASE, count=1)

# 判断是否需要标准化：HB 的扫频计划若"不"引用 freq_low（即用字面量）⇒ 说明是嵌套/非标准口径 ⇒ 标准化
_needs_std = (not re.search(r"Start=freq_low", BASE)) and (re.search(r"(?m)^HB:\w+", BASE) is not None)
if _needs_std:
    # 嵌套扫频的单元（外层 ParamSweep 调 HB，HB 自己又扫 Pin）：统一为标准 PA 口径
    # 只留一处扫频率：HB1 扫 RFfreq(1.5-3.5GHz/21点)，外层退化为扫 Pin 单点
    BASE = BASE.replace('SimInstanceName[1]="HB1" StatusLevel=2 SweepVar="RFfreq"', 'SimInstanceName[1]="HB1" StatusLevel=2 SweepVar="Pin"')
    BASE = BASE.replace('SweepVar="Pin" SweepPlan="HB1_stim"', 'SweepVar="RFfreq" SweepPlan="HB1_stim"')
    BASE = re.sub(r"(?m)^SweepPlan:\s*HB1_stim[^\n]*", "SweepPlan: HB1_stim Start=%g GHz Stop=%g GHz Lin=%d" % (B_LO, B_HI, B_N), BASE)
    BASE = re.sub(r"(?m)^SweepPlan:\s*ParamSweep1_stim[^\n]*", "SweepPlan: ParamSweep1_stim Start=30 Stop=30 Lin=1", BASE)
    # 若输出计划里没有 Deff/Pdel_dBm（V11 缺），按 V4 的表达式补一条（改用它自己的节点名 Vs_h/Vs_l）
    if re.search(r"(?m)^Pin=", BASE):
        BASE = re.sub(r"(?m)^Pin=.*$", "Pin=30", BASE, count=1)
    else:
        BASE += "\nPin=30\n"
STRIP_ANNOT = os.environ.get("STRIP_ANNOT", "1") == "1"
ROUND1 = int(os.environ.get("ROUND1", "1"))  # 变量按 0.1 粒度取整后再仿真（与写回一致）
if STRIP_ANNOT:
    BASE = re.sub(r"(tune|notune)\{[^}]*\}", "", BASE)

def net(vals):
    t = BASE
    for k, v in vals.items():
        if ROUND1:
            v = round(float(v), ROUND1)
        t = re.sub(r"(?m)^" + re.escape(k) + r"=[-\d.eE+]+", "%s=%.6g" % (k, v), t, count=1)
    return t


def _compute_from_raw(df, cols):
    """当数据集缺 Deff/Pdel_dBm 时，用 Vload/Iload.i 与 Vs_h/Is_high.i 自算 DE/Pout。
    约定: Pout = 0.5*Re(V*conj(I)) (取模), Pdc = 28V * |Idc|; DE = Pout/Pdc*100"""
    import numpy as _np
    need = {"Vload", "Iload.i", "Vs_h", "Is_high.i"}
    if not need.issubset(set(cols)):
        return None
    lv = df.index.names
    if "harmindex" not in lv or "RFfreq" not in lv:
        return None
    try:
        V = _np.asarray(df["Vload"].values, dtype=complex)
        I = _np.asarray(df["Iload.i"].values, dtype=complex)
        Vs = _np.asarray(df["Vs_h"].values, dtype=complex)
        Is = _np.asarray(df["Is_high.i"].values, dtype=complex)
        _has_low = ("Vs_l" in cols) and ("Is_low.i" in cols)
        if _has_low:
            Vsl = _np.asarray(df["Vs_l"].values, dtype=complex)
            Isl = _np.asarray(df["Is_low.i"].values, dtype=complex)
        fr = _np.asarray(df.index.get_level_values("RFfreq").astype(float))
        hi = _np.asarray(df.index.get_level_values("harmindex").astype(int))
        pin = None
        if "Pin" in lv:
            pin = _np.asarray(df.index.get_level_values("Pin").astype(float))
            _uv = _np.unique(pin)
            if _uv.size > 1:
                pin = _np.where(_np.abs(pin - 30.0) == _np.abs(_uv - 30.0).min(), 30.0, _np.nan)
        out_f, out_de, out_p = [], [], []
        _seen = set()
        for ff in _np.unique(fr):
            if ff in _seen:
                continue
            for pp in [30.0]:
                sel = (fr == ff)
                if pin is not None:
                    sel &= _np.isfinite(pin)
                if not sel.any():
                    continue
                _seen.add(ff)
                idx = _np.where(sel)[0]
                h = hi[idx]
                dc = idx[h == 0]
                f1 = idx[h == 1]
                if dc.size == 0 or f1.size == 0:
                    continue
                if _has_low:
                    pdc = float(_np.real(Vs[dc[0]] * _np.conj(Is[dc[0]]) + Vsl[dc[0]] * _np.conj(Isl[dc[0]])))
                else:
                    pdc = float(_np.real(Vs[dc[0]] * _np.conj(Is[dc[0]])))
                pdel = 0.5 * float(_np.real(V[f1[0]] * _np.conj(I[f1[0]])))
                if pdc <= 1e-9:
                    continue
                out_f.append(ff / 1e9)
                out_de.append(100.0 * pdel / pdc)
                out_p.append(10.0 * _np.log10(max(pdel, 1e-12) * 1000.0))
        if len(out_f) < 5:
            return None
        return (_np.asarray(out_f), _np.asarray(out_de), _np.asarray(out_p))
    except Exception:
        return None

def evaluate(vals, tag=None):
    if tag is None:
        import time as _t
        tag = "v3_%d_%d" % (os.getpid(), int(_t.time()*1000) % 1000000)
    r = run_hpeesofsim(net(vals), WRK, tag, timeout=900)
    if not r.get("ok"):
        if os.environ.get("DEBUG_SIM") == "1":
            import sys as _s
            print("[DEBUG] sim fail; r keys=%s" % list(r.keys()), file=_s.stderr)
            for _k in ("err", "stderr", "stdout", "stdout_tail", "rc", "sim_dir", "log", "msg"):
                _v = r.get(_k)
                if _v:
                    print("[DEBUG] %s=%s" % (_k, str(_v)[-900:]), file=_s.stderr)
        return dict(ok=False, err="sim fail")
    d = dataset.open_dataset_for_reading(r["ds_path"])
    P = D = None
    for k in d.keys():
        try:
            df = d.get(k).to_dataframe()
        except Exception:
            continue
        cols = [str(c) for c in df.columns]
        fq = None
        for nm in ("RFfreq", "freq", "RFfreq_Hz"):
            try:
                fq = np.asarray(df.index.get_level_values(nm).astype(float)) / 1000.0
                break
            except Exception:
                continue
        if fq is None:
            continue
        if "Deff" in cols and D is None:
            D = (fq, np.asarray(df["Deff"].values, float))
        if "Pdel_dBm" in cols and P is None:
            P = (fq, np.asarray(df["Pdel_dBm"].values, float))
    RAWD = None
    for k in d.keys():
        try:
            df2 = d.get(k).to_dataframe()
        except Exception:
            continue
        r2 = _compute_from_raw(df2, [str(c) for c in df2.columns])
        if r2 is not None:
            RAWD = r2
            break
    if (D is None or P is None) and RAWD is not None:
        fR, deR, pR = RAWD
        bandR = (fR >= B_LO) & (fR <= B_HI)
        if bandR.sum() >= 5 and np.isfinite(deR[bandR]).all() and np.isfinite(pR[bandR]).all():
            return dict(ok=True, de_mean=float(deR[bandR].mean()), de_min=float(deR[bandR].min()),
                        p_mean=float(pR[bandR].mean()), p_min=float(pR[bandR].min()),
                        npts=int(bandR.sum()), fmin=float(fR[bandR][0]), fmax=float(fR[bandR][-1]),
                        de=list(map(float, deR[bandR])), p=list(map(float, pR[bandR])), f=list(map(float, fR[bandR])),
                        note="self-computed from Vload/Iload.i")
    if D is None or P is None:
        return dict(ok=False, err="no HB data")
    fD, vD = D
    fP, vP = P
    band = (fD >= B_LO) & (fD <= B_HI)
    if band.sum() < 5:
        return dict(ok=False, err="band<5pts")
    de = vD[band]; po = vP[band]
    if not (np.isfinite(de).all() and np.isfinite(po).all()):
        return dict(ok=False, err="nan")
    return dict(ok=True, de_mean=float(de.mean()), de_min=float(de.min()),
                p_mean=float(po.mean()), p_min=float(po.min()),
                npts=int(band.sum()), fmin=float(fD[band][0]), fmax=float(fD[band][-1]),
                de=list(map(float, de)), p=list(map(float, po)), f=list(map(float, fD[band])))




if __name__ == "__main__":
    inp, outp = sys.argv[1], sys.argv[2]
    srcref = sys.argv[3] if len(sys.argv) > 3 else "ADS_Auto_lib_FPA_V3.net"
    tag = os.path.basename(srcref).replace(".net", "")
    vals = json.load(open(inp, encoding="utf-8"))
    res = evaluate(vals, tag)
    cost = None
    if res.get("ok"):
        cost = -(res["de_mean"] + 0.5 * res["de_min"]) + 8.0 * max(0.0, 38.0 - res["p_min"])
        res["cost"] = cost
    json.dump(res, open(outp, "w"), indent=1)
    print(json.dumps({k: res.get(k) for k in ("ok","err","de_mean","de_min","p_mean","p_min","cost","npts")}))
