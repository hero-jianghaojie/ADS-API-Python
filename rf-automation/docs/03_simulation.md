# 03 仿真口径与评估器（`eval_*.py`）

## 1. 为什么必须"标准化口径"
同一网表，**不同分析设置会给出不同数**。已实测案例：
- **`FundOversample` 1（单元原设）vs 8（我们的标准）** ⇒ 2.40–2.50 GHz 处最大差 **8.96 个点**，把"DE 最差 60.26%（OS=8）"翻成 **59.64%（OS=1）** ⇒ **验收必须在同一 OS 下比**。
- **频率步长 0.05 vs 0.10 GHz** ⇒ 影响"最差点"落在哪个频点。
⇒ 结论：**所有结论都要写明"口径"**：频段 + 点数 + `Pin` + `FundOversample` + 器件/偏置 + 端口端接。

## 2. 调用 hpeesofsim（`ads_sim_helper.run_hpeesofsim`）
```python
from ads_sim_helper import run_hpeesofsim      # <REPO_PARENT>\ads_sim_helper.py
r = run_hpeesofsim(netlist_text, workdir, tag, timeout=900)
# r = {"ok": bool, "ds_path": "...", "err": ...}
```
- 用 **ADS 的 python** 跑（`...\tools\python\python.exe`），`cwd` 用工作区。
- `tag` 决定中间文件名 ⇒ **每次唯一**，否则并发/缓存会串。
- 读结果：`keysight.ads.dataset.open_dataset_for_reading(r["ds_path"])` → `d.get(name).to_dataframe()`

## 3. `eval_var.py`（PA 类评估器，本项目的"标准尺子"）
它把单元的嵌套扫描**统一成**：
- **HB**：`HB1_stim Start=1.5 Stop=2.5 Lin=21`（可由 env 改）
- **ParamSweep**：`ParamSweep1_stim Start=30 Lin=1`（即 **Pin 固定**）
- 强制 **`FundOversample=8`**、**`Pin=30`**、`MaxOrder=4`、`Order[1]=3`
**环境变量**（默认值刻意不改，避免影响旧结果）：
| env | 默认 | 含义 |
|---|---|---|
| `EV_BAND_LO`/`EV_BAND_HI`/`EV_NPTS` | 1.5/3.5/21 | 评估频段与点数 |
| `HB_ORDER`/`HB_MAX` | 3/4 | `Order[1]`/`MaxOrder` |
| `STRIP_ANNOT` | 1 | 去掉网表里的 `tune{}`/`notune{}` 注解 |
| `ROUND1` | 1 | 写回/补丁时取 1 位小数（用户硬性偏好）|

## 4. 数据集取数（**易错点**）
- **`Pdc` 必须取 `freq=0` 的 DC 行**；`Pdel` 取**基波行**（`freq≈RFfreq`）。
- 频率索引：`df.index.get_level_values("freq")`；比较/取点前**先排序并对齐**。
- **`argmin(|f - f_target|)` 的危险**：如果目标频率**超出网表扫频范围**，它会**静默返回扫频上沿**，出来的是**貌似合理的垃圾** ⇒ 评估器必须**先断言扫频覆盖**（`min≤band≤stop≤max`）。
  > 真实事故：打分副本只扫到 3.5 GHz，而"二次谐波"要看到 5 GHz、阻带要看到 8 GHz ⇒ 二次/阻带数全错。
- **口径一致性**：读到的 `S` 参数是**线性复数**；阻抗换算 `Z=Z0(1+Γ)/(1-Γ)`（`Z0` 取端口 `Z`，通常 50）。

## 5. DE（漏极效率）计算
```
Pout = 0.5 * Re(V_fund * conj(I_fund))          # 基波
Pdc  = Re(Vs_high * conj(Is_high) [+ Vs_low * conj(Is_low)])   # DC 行
DE   = Pout / Pdc
```
- 单电源（CGH40010F 这一档）取 `Vs_h` 一路；双电源（含栅）时按网表实际 Short 元素判定。
- `eval_var.py` 里有**回退公式**（找不到理想节点时用），实现行约在 61–62 / 106–109。

## 6. `eval_fomn.py`（阻抗空间评估器，与 07 配套）
- 读**打分专用副本**（由 env `FOMN_NET` 指定，默认 `FOMN_ccf.net`）⇒ **该副本的扫频必须覆盖 `[band, 2*band, stop]`**。
- 计算 `Zin`（器件侧端口）= `50(1+S11)/(1-S11)`；对**基波段**与**二次谐波段**分别算"到目标轨迹的**最小距离**"：
  ```
  d(p) = min_over_rho dist_seg(Z, re(rho), im_lo(rho), im_hi(rho))     # 并集(扇形/带)的精确距离
  d_eff = max(0, d - TOL)                                              # TOL = 允许区(等向膨胀)
  ```
- 归一化与权重：`d/ROPT`；`cost = w1*(mean+WMAX*max)d1 + w2*(...)d2 + wOUT*阻带罚 + 0.1*带内项`。
- **env**：`FOMN_BAND_LO/HI`、`FOMN_STOP_LO/HI`、`FOMN_ROPT`、`FOMN_ROPT_LO/HI`（把 `R_opt` 的不确定度并成**并集**）、`FOMN_TOL`、`FOMN_W1/W2/WMAX/WOUT`、`FOMN_NET`。
⚠ 并集采样**必须包含参考 `ROPT` 本身**，否则"并集"不是窄空间的超集，会出现"并集反而更远"的悖论。
