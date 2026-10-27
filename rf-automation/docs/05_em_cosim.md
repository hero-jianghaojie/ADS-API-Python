# 05 EM 与联合仿真（Momentum / cosim）

## 1. 结构：ADS 的"EM 联合仿真"长什么样
典型 testbench（本项目 `Y2_V1`）：
```
define <CELL> ( P1..PN ref=0 )
em_data_name="<lib>:<cell>:emModel"
MomCmpt:em_data P1..PN name=em_data_name
    modelFile=".../<lib>/<cell>/emModel/model.ndx"
    ModelType="MOMMW"   ModelReuse=1   EnforcePassivity=-1
<CELL>:X1 ...          ← 层级实例化 EM 块
+ 器件(如 CGH40010F_r6) + 偏置 + Port + HB/S_Param
```
**关键**：`ModelReuse=1` ⇒ **复用已存的 EM 模型，不会自己重跑 Momentum** ⇒ 所以**电路侧仿真很便宜**（cosim ≈ **4 s**），
但 ⇒ **EM 数据绑定"上次 Momentum 跑时的几何"** ⇒ **改了版图尺寸，EM 数据就失效**。

## 2. 能力边界（**必背**）
| 环节 | 脚本化 | 代价/做法 |
|---|---|---|
| 改版图/pcell 参数 | ✅ | 桥接写回；**值必须传字符串**（带单位）、`DesignMode.APPEND` |
| **重生成 EM 几何输入**（`proj_a`/`proj.pin`）| ❌ | **必须 GUI**：插件函数 `deem_run_create_preprocessed_geometry` 最终要 `dex_em_egsWrite_geometry`，而它只在 `bin\pde_private.dll`（AEL 调不到，无 `aelshell.exe`）|
| 跑 EM | ✅ | `...\bin\adsMomWrapper.bat -3D / -O -3D`（≈**196 s**，18 端口 0–10 GHz/0.1 GHz）|
| 打包数据集 | ✅ | `adsMomWrapper -CD` |
| 电路 + EM 联仿 | ✅ | `hpeesofsim`（≈4 s）|
| 算指标/评分 | ✅ | `opt_em_cosim.py` |
| 版图协仿自动分割(emCosim) | ❌ | 同属插件（`dex_em_simulate_from_layout`）|

**EM 引擎入口**：`adsMomWrapper.bat` → 内部解析后调 **`MomEngine.exe`**；
⚠ `bin\hpeesofemx.exe` **不要直接调**（会挂起）。

## 3. 两条可行路径（**官方推荐 A**）
### 路径 A（推荐）：EM 修正模型 + 快速优化
1. 在参考几何上量一次 **`corr(f) = DE_EM(f) − DE_ideal(f)`**；
2. 用**快速理想模型**把代价改成 `DE_ideal(f;p) + corr(f)` 优化（~2 s/次，纯脚本）；
3. **GUI 里刷新一次几何**（改变量 → 重新生成 EM 输入）——**这是唯一的 GUI 动作**；
4. 用真 EM 复验（2）的结果；若未达标 ⇒ 用新结果更新 `corr(f)` 回（2）；
⇒ **2–3 轮通常收敛**，每轮只需用户点 1 次 GUI。
### 路径 B：缩小 EM 区块
只 EM 仿真**最关键的耦合/间隙结构**，其余微带保留为**理想可调模型** ⇒ 扩大可调域。

## 4. 已知量级（引用时必须带"配置"）
| 场景 | 理想模型 | EM 联合仿真 | 版图惩罚 |
|---|---|---|---|
| 文献报告的一例（3.0–4.0 GHz）| 60.44% | 49.39% | **≈11 个点** |
| 本项目 `Y2_V1`（1.5–2.5 GHz）| ≈60.3% | **DE 均 53.27 / 最差 23.80%** | **更大**（2.1 GHz 以上断崖）|
⚠ 早期"负载牵引 58.3% / 偏置 56.6%"的上限是**特定配置**下的，已被后续设计超过 ⇒ **引用上限必须说明配置**。

## 5. EM 产物与数据
- 模型目录：`work\<wrk>\<lib>\<cell>\emModel\`（`model.ndx`、`data.000.sio`、`emStateFile.xml`、`eesof_em_model.file`）
- Windows 路径里会出现带 `%` 的转义形式（如 `%B%T2_%V1\em%Model`）——**桥接/网表里这样写是正常的**。
- Momentum 工程产物长这样：`proj_a`（**纯文本几何**，可直接读/`UNITS MM,1000`）、`proj.pin`、`proj.gdf`、`proj.msh`、`momentum.cfg`。
- 历史脚本：`ads_tools/run_mom.py`、`run_em_cli.py`、`em_opt_pa30v1.py`、`fpa1_em_loop.py`、`bt_v8_regen_em.py`、`bpf2_layout_opt.py`（可参考，本项目已跑通过无头 EM）。
