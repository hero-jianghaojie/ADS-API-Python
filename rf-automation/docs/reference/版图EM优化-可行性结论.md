# 版图（EM）优化到 60% —— 可行性结论与路径

> 目标：用 **EM 联合仿真**作为评估器，把 3.0–4.0 GHz 窗内每点 DE 优化到 ≥60%。
> 结论：**评分环节已可脚本化；生成环（几何重生成）不可脚本化，是硬墙。**
> 2026-09-14

---

## 一、当前基线（实测）

| 评估方式 | 3.0–4.0 GHz 最差 DE | 均值 | ≥60% 达标 |
|---|---|---|---|
| 理想微带（MLIN 等标称模型） | **60.4419%** @3.20 | 62.34% | ✅ 21/21 |
| **EM 联合仿真（版图）** | **49.3947%** @4.00 | 58.06% | ✗ **8/21** |

逐点（EM 联仿）：

| GHz | 3.0 | 3.1 | 3.2 | 3.3 | 3.4 | 3.5 | 3.6 | 3.7 | 3.8 | 3.9 | 4.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DE% | 65.7 | 63.0 | **55.8** | **53.6** | **57.3** | 69.3 | **57.1** | **58.6** | **54.8** | **50.6** | **49.4** |

**即：版图比理想模型差约 11 个点（最差点），需要真正的"以 EM 为评估器"的再优化。**

评分脚本：`opt_em_cosim.py`（用法见文末）

---

## 二、⚠️ 硬墙：EM 输入文件（几何）无法脚本重生成

要把版图优化做成闭环，每次改几何都要重新生成 EM 的几何输入：

```
改微带尺寸 → 重新生成 proj_a/proj.pin → 跑 Momentum → 电路+EM 联仿 → 算 DE
                 ^^^^^^^^^^^^^^^^^^^
                 这一步过不去
```

### 证据链（都已实测）

1. **`proj_a` 是纯文本几何**，可直接读：
   ```
   UNITS MM,1000;
   EDIT proj;
   ADD P1 :W0.000000  0.000,-1.619 17.616,-1.619 17.616,1.619 0.000,1.619;
   ```
   （第一条 = `TL122`，半宽 1.619 = `IN_W4`/2、长 17.616 = `IN_L3`）

2. **版图 pcell 参数可以脚本改**：
   `instance.parameters["L"].value = "18.6164 mm"` 写入并回读成功（注意**必须传字符串**，
   因为值是带单位的表达式；用 `DesignMode.APPEND` 打开，`WRITE` 会变成空 design）。

3. **AEL 里确实有几何重生成函数**：
   `deem_run_create_preprocessed_geometry(context, "emSetup")`

4. **但它调不下去** —— 迭代式追依赖，最终卡在 DLL：
   ```
   deem_run_create_preprocessed_geometry
     -> deemif_newMap                     (在 atf 里，可加载)
     -> dex_em_egsWrite_geometry          ← 只在 bin\pde_private.dll 里
   ```
   实测：
   - 加载顺序必须是 `deempublic.atf` → `deemif.atf`（反了就互相覆盖词表）
   - 该顺序下 `deemif_newMap` / `deem_run_create_preprocessed_geometry` / `deem_run_em_setup`
     都是"可调用"（`type="function"`）
   - 但**一调就报** `Cannot call the undefined function: "dex_em_egsWrite_geometry"`
   - 全安装搜索：`dex_em_egsWrite_geometry` 只出现在 `bin\pde_private.dll` 和
     `de\ael\deemif.atf`（仅是前向声明）
   - `config\emsetup.cfg` 印证：*"code is in pde/mom/Em_egsWrite.cxx"* —— 编在 DE 里，**没有独立 exe**

5. **同族的其它插件函数也是同样情况**（都解析不出来）：
   `dex_em_simulate_from_layout`（`deem_run_em_setup` 依赖）、`emSetupView_isEmSetupView`

6. **没有可用的旁路**：
   - `deboot_em_ui_files.atf` / `deemconvert.atf`（含 `emSetupView_pluginLoaded` 引导标志）
     加载后**无改善**
   - `ads.exe` 里出现的 `aelshell` 只是历史字符串，**没有 aelshell.exe**
   - 只有 `aelcomp.exe`（AEL 编译器），不是运行时 shell

**⇒ 只要几何变了，就必须在 ADS GUI 里重新生成 EM 输入文件。**

---

## 三、能脚本化的部分 vs 必须 GUI 的部分

| 环节 | 脚本化 | 说明 |
|---|---|---|
| 改进度/变量值 | ✅ | Python `keysight.ads.de`（pcell 参数传字符串） |
| **重生成 EM 几何输入（proj_a 等）** | ❌ | **需 DE 插件，必须 GUI** |
| 跑 EM 仿真 | ✅ | `adsMomWrapper -3D / -O -3D`（196 s，18 端口 0–10 GHz/0.1 GHz） |
| 打包数据集 | ✅ | `adsMomWrapper -CD` |
| 电路 + EM 联仿 | ✅ | `hpeesofsim`（~4 s） |
| 算窗内 DE 并评分 | ✅ | `opt_em_cosim.py` |
| 版图协仿（自动分割 emCosim） | ❌ | 同属插件（`dex_em_simulate_from_layout`） |

---

## 四、两条可行路径

### 路径 A（推荐，最省 GUI 操作）：EM 修正模型 + 快速优化

思路：EM 与理想模型的差值 `corr(f) = DE_EM(f) − DE_ideal(f)` 主要由**版图寄生效应**造成，
在参数小范围变化时可作**一阶近似为只随频率变化**。

1. 在参考解上量一次 `corr(f)`（已有：见第一节两张表）
2. 把代价函数改成 `DE_ideal(f; p) + corr(f)`，用**快速理想仿真（~2 s/次）**优化
   → 纯脚本、可用现有 `pa20_*` 工具链
3. **GUI 里刷新一次几何**（改变量 → 重新生成 EM 输入文件）
4. 用 `opt_em_cosim.py` **真 EM 复验**；若仍不到 60%，用新结果更新 `corr(f)` 再回到第 2 步
   （每次迭代只需 1 次 GUI 操作，2–3 轮通常收敛）

优点：脚本承担几乎所有计算量；GUI 只做"重新生成 EM 输入文件"这一个动作。

### 路径 B：扩大可调域（改设计方法）

把 EM 区块**缩小**（只 EM 仿真最关键的耦合线/间隙结构），其余微带保留为**理想可调模型**。
这样优化变量就都落在脚本可调的域里，闭环完全自动化。

代价：EM 精度下降（但可用路径 A 的修正量来标定误差）。

---

## 五、GUI 里那一步怎么做（唯一的手动环节）

1. 在 ADS 里打开目标单元的 `layout`
2. `EM > Simulation Setup` 打开 EM Setup 窗口
3. **`Generate` 下拉选 `EM Simulation Input Files`**（或 `EM Simulation/Model`）
4. 点 **`Go`**
   → 写出新的 `proj.*` 到
   `<wrk>/simulation/<lib>/<cell>/<layout>/<emSetup>_MoM/`
5. 之后全部交给脚本

> 前提：版图里的微带 pcell 参数是**变量表达式**（如 `W=IN_W4  L=IN_L3`），
> 所以改**原理图变量值**即可让版图跟着变，不必手工改版图。

---

## 六、已交付工具

### `opt_em_cosim.py` —— EM 联仿评估器（评分环节）

```powershell
$ADS = 'D:\Program Files\Keysight\ADS2025_Update2\tools\python\python.exe'

# 给当前版图评分（默认读 <wrk>/sim/<cell>_cosim/*.ds）
& $ADS opt_em_cosim.py --cell PA30_free --center 3.5 --window 1.0 --target 60

# 记入日志，便于跟踪多轮迭代
& $ADS opt_em_cosim.py --cell PA30_free --log logs/em_score.csv
```

输出：窗内最差 DE / 均值 / 达标点数，并逐点列出未达标频率。

### 相关的现成工具
| 脚本 | 作用 |
|---|---|
| `cosim_pa30free.py` | 构建并运行 EM 联仿（含理想微带白名单自检） |
| `run_em_cli.py` | 命令行跑 EM：`--mode solve\|full\|mesh\|dataset`、`--force` |
| `cmp_ds.py` | 两个数据集 S 参数数值对比（绝对偏差 + 加权 dB） |
| `find_ael_order.py` | 解析 AEL 词表加载顺序（本次调查产物） |

---

## 七、当前待办

- [x] 量化版图基线（最差 49.39% @4.0 GHz，8/21 达标）
- [x] 确认几何重生成的脚本化边界（硬墙已定位到 `pde_private.dll`）
- [x] 交付 EM 联仿评分工具
- [ ] 建立 `corr(f)` 修正模型并接入 `pa20_*` 代价函数（路径 A 第 2 步）
- [ ] GUI 刷新几何 → 真 EM 复验
