# MATLAB 帮 ADS 做优化 —— 使用方法（本工程实测版）

> 适用环境：MATLAB **R2025a**（\`<MATLAB_HOME>\`）+ ADS **2025 Update 2**（\`D:\Program Files\Keysight\ADS2025_Update2\`，ADS 版本号 620）
> 本文所有结论都是本工程 2026-10-10 / 10-11 实测得到，未实测的会明确标注。

---

## 0. 能用什么（实测许可证与函数）

| 项目 | 结果 |
|---|---|
| \`license('test','GADS_Toolbox')\` | **1**（= Global Optimization Toolbox：ga / patternsearch / bayesopt / surrogateopt / gamultiobj / particleswarm） |
| \`license('test','Optimization_Toolbox')\` | 1（fmincon 等局部优化） |
| \`license('test','Statistics_Toolbox')\` | 1（fitrgp / fitrensemble：高斯过程、集成代理） |
| \`license('test','Distrib_Computing_Toolbox')\` | **1**（= Parallel Computing Toolbox，**8 workers**） |
| \`license('test','Deep_Learning_Toolbox')\` | 0（不可用） |
| 核数 | \`feature('numcores')\` = **8**（8 物理核） |

> ⚠️ 查询许可证名要用对字符串：\`'Global_Optimization_Toolbox'\` 与 \`'Parallel_Computing_Toolbox'\` 查出来是 **0**，那是名字不对；正确名是 \`'GADS_Toolbox'\` 与 \`'Distrib_Computing_Toolbox'\`。

---

## 1. 两种接线方式（先决定谁做主）

| | **A. ADS → MATLAB**（ADS 当主循环，MATLAB 当大脑） | **B. MATLAB → ADS**（MATLAB 当主循环，ADS 当评估器） |
|---|---|---|
| 适合 | 循环已经写在 Python 里（本工程的 hpeesofsim / Momentum 批跑），只把"下一个采样点"交给 MATLAB | 循环写在 MATLAB，评估走 Python/ADS |
| 建立 | ADS 自带 Python 里已装 \`matlab.engine\` | \`pyenv\` 指向 ADS 自带 Python 3.12 |
| 代价 | 冷启 MATLAB ~70 s，之后每次 \`eng.eval\` ~0.03 s | 冷启 MATLAB ~40 s，之后每次 py 调用 ~10 ms |
| 已验证 | ✅ \`autoADS\_matlab_bridge.py\` | ✅ \`scripts\demo_bayesopt_ads.m\`、\`scripts\demo_surrogateopt_lbq1.m\` |

**A 的最小骨架**
\`\`\`python
# 在 ADS 自带 Python 里跑（HPEESOF_DIR 已设）
import matlab.engine
eng = matlab.engine.start_matlab("-nojvm -nodisplay -r ''")   # ~70 s
eng.workspace["ads_score"] = my_python_objective              # 注册 Python 回调
eng.eval("h = @(x) ads_score(x);", nargout=0)
best = eng.patternsearch("h", 5.0, [], [], [], [], 3.0, 6.0)  # MATLAB 决定下一个点
\`\`\`

**B 的最小骨架**
\`\`\`matlab
ads_dir = 'D:\Program Files\Keysight\ADS2025_Update2';
pyenv('Version', fullfile(ads_dir,'tools','python','python.exe'), 'ExecutionMode','OutOfProcess');
setenv('HPEESOF_DIR', ads_dir);                       % 必须在 import keysight 之前
sys = py.importlib.import_module('sys');
sys.path.insert(int64(0), 'e:\AI\autoADS');           % 放目标模块的目录
M = py.importlib.import_module('my_objective');       % 暴露 score_vec(x)/VARS/LB/UB/X0
lb = cellfun(@double, cell(M.LB))';  ub = cellfun(@double, cell(M.UB))';
x0 = cellfun(@double, cell(M.X0))';
f  = @(x) double(M.score_vec(py.list(num2cell(x(:)'))));    % 目标：float -> float
\`\`\`

---

## 2. 选哪个求解器（决策表）

| 场景 | 用谁 | 关键设置 | 本工程实测 |
|---|---|---|---|
| 单次评估很贵（EM 1–2 min、HB 4–6 s），维数 ≤ ~20，预算只有几十次 | **\`bayesopt\`** | \`'IsObjectiveDeterministic',true\`；\`'MaxObjectiveEvaluations'\` 按预算给 | 20 次真实 ADS 仿真把 lbq1 的 RMS 从 12.40 做到 **11.80** |
| 有边界约束、确定性、维数 10–60、肯花 100+ 次评估 | **\`surrogateopt\`** | **必须给 \`'InitialPoints'\`**；\`'MinSurrogatePoints' > nvars\` | 130 次把 12.40 做到 **11.51**（取整回 12.40，见 §5-7） |
| 目标便宜、多峰、想全局 | \`ga\` / \`particleswarm\` / \`simulannealbnd\` | 种群 × 代数 = 评估数，先算预算 | 未用 |
| 局部精修、目标非光滑 | \`patternsearch\` | 起点决定一切 | 用于桥接自检 |
| 已有大批历史数据（如 lbq1 的 **580 点**数据集） | \`fitrgp\` / \`fitrensemble\` 建**离线代理**，在代理上搜，少量真评估验证 | 代理外推要警惕 | 未用（推荐） |
| 多目标（DE↑ 同时 Pout 平坦） | \`gamultiobj\` / \`paretosearch\` | 产出 Pareto 前沿 | 未用 |
| 想一次跑多个候选 | \`parpool\`(8) + \`'UseParallel',true\` / \`parfeval\` | **EM/ Momentum 不能并行**（共享 substrate DB），HB/SP 可以 | 未用（推荐给 HB） |

**预算公式**：\`评估次数 ≈ 可接受的墙上时间 / 单次评估耗时\`
- SP 网表 ≈ 4 s → 30 min 可跑 ~450 次
- HB（FPA 器件台 2–5 GHz/100 MHz）≈ 2–4 min → 30 min 只能跑 ~10 次 ⇒ 必须用 \`bayesopt\` 或减少频点
- Momentum EM ≈ 1–2 min → 同上，且**串行**

---

## 3. 目标函数怎么写（本项目三档模板）

| 档 | 单次耗时 | 模板（已实测） | 目标怎么写 |
|---|---|---|---|
| **SP 网表** | ~4 s | \`autoADS\matlab_obj_lbq1.py\`、\`lbq1_graded.py\` | 改网表变量 → \`hpeesofsim.exe n.net\` → 读 \`.ds\` 取 S 参数 → 返回标量（如 \`RMS|Zin-ZL|\`） |
| **HB 器件台** | 2–4 min | \`autoADS\paper1_hb_run.py\`、\`fpa_lbq1_hb.py\` | 替换 VAR → HB → \`pa_metrics_de.read_metrics(ds)\` → 取 2.5–4.5 GHz 的 DE（min 或均值），Pout 做惩罚 |
| **Momentum EM** | 1–2 min | \`ads_tools\run_mom.py\` | 改 \`proj_a\`(+ \`proj.pin\`) → \`run_mom.py --mode full\` → 读 \`proj.sio\`（\`keysight.pwdatatools\`）→ 返回标量 |

**目标设计三条经验**
1. **约束用连续罚函数**，不要写成硬墙（否则贝叶斯/代理模型学不到梯度信息）；
2. **每次评估落日志**（\`eval_log.txt\`：参数 + 指标 + 代价），出图/复查全靠它；
3. 目标返回 **float**，Python 侧不要抛异常（失败要返回一个"很差的有限值"，否则优化器会中断）。

---

## 4. 标准工作流（照抄）

1. **写目标模块**（Python）：\`score_vec(x) -> float\`，并暴露 \`VARS / LB / UB / X0\`（\`describe()\` 返回 JSON 便于自检）
2. **先跑一次基线**：确认能出数、并**量出单次耗时**（决定预算）
3. **MATLAB 侧建句柄**（§1-B），选求解器（§2），给 \`InitialPoints\`
4. **运行**：\`bayesopt\`（≤20 维贵目标）或 \`surrogateopt\`（10–60 维）
5. **取解 → 真环境复核**（同评估器再跑一次）→ **按 1 位小数取整 → 再复核**
6. **写回 ADS**：先备份网表/变量表 → 写 VAR（纯数字）+ 实例表达式（**带单位后缀**）→ \`save_design()\` → **用 ADS 导出的网表复跑**确认一致
7. **出图归档**：收敛曲线 + 优化前后对比（英文标注、PNG + SVG）

---

## 5. 已验证的坑（照着躲）

1. **\`bayesopt\` 的目标函数收到的是 table**：写 \`@(x) ...x(1)...\` 会报"不支持使用一个下标"，要写 \`@(t) ...t.FEED_W_IN(1)...\`
2. **\`surrogateopt\` 的 \`MinSurrogatePoints\` 必须 > 变量个数**（14 维时给 12 直接被拒）
3. **贵目标必须给 \`InitialPoints\`**：14 维、150 次评估从零探索，连已知好点都追不上（256.6 vs 157.5）
4. **MATLAB 字符串反斜杠是转义符**：\`'e:\AI\autoADS\x.csv'\` 里的 \`\l\` 会警告/写不出去 → 用 \`fullfile\` 或双反斜杠
5. **\`pyenv\` 必须是 ADS 自带 Python 3.12 + \`OutOfProcess\`**，且先 \`setenv('HPEESOF_DIR', ...)\`（否则版本/DLL 冲突）
6. **写回 ADS 时实例表达式必须带单位**（\`FEED_W_IN mm\`）；VAR 里存纯数字即可
7. **1 位小数取整会吃掉小增益**：数学最优 11.51 Ω 取整后 12.40 Ω（< 0.1 mm 布局颗粒度）⇒ 汇报要说明"这是口径最优"
8. **\`pa_metrics_de.read_metrics\` 的 freq 列是 Hz**（画图前 /1e9）
9. **bridge 里用真实单元名**：磁盘目录名是 \`%\` 转义（\`%F%P%A1\` → \`FPA1\`）
10. **Momentum 不能并行**：所有 Momentum 任务共享 \`SPB_Data\substrates\0000.sdb\`，必须串行

---

## 6. 本工程现成资产（直接复用）

| 文件 | 作用 |
|---|---|
| \`autoADS\pb.py\` + \`ads_tools\ads_live_server.py\` | 把脚本送进正在运行的 ADS（XML-RPC 127.0.0.1:8765） |
| \`autoADS\_matlab_bridge.py\` | 路线 A 原型（ADS Python 起 headless MATLAB + 注册回调） |
| \`autoADS\matlab_obj_lbq1.py\` | 路线 B 的 **SP 目标模块**模板（3 变量版） |
| \`autoADS\lbq1_graded.py\` | 路线 B 的 **14 变量目标模块**模板（含 \`describe()/score_vec()\`） |
| \`autoADS\scripts\demo_bayesopt_ads.m\` | **bayesopt 驱动 ADS** 完整示例 |
| \`autoADS\scripts\demo_surrogateopt_lbq1.m\` | **surrogateopt 驱动 ADS** 完整示例（含 InitialPoints） |
| \`autoADS\scripts\probe_matlab_ads.m\` / \`probe_matlab_lic.m\` | 环境自检（pyenv/keysight 导入、许可证/核数） |
| \`autoADS\paper1_hb_run.py\` / \`fpa_lbq1_hb.py\` | HB 目标模板（器件测试台 + 参数替换） |
| \`autoADS\pa_metrics_de.py\` | 从 HB 数据集读 DE / PAE / Pout / 增益 |
| \`autoADS\plot_lbq1_graded.py\` / \`paper1_hb_plot.py\` | 收敛图 / 指标图模板（英文标注、PNG+SVG） |

---

## 7. 三种典型用法（对号入座）

**用法 1｜已有 Python 循环，给循环换个大脑（路线 A）**
\`\`\`
Python 循环跑 ADS 评估  →  eng.workspace["score"]=回调  →  MATLAB patternsearch/ga 决定下一点
\`\`\`
适合：hpeesofsim/EM 批处理已经写好，只想换优化算法。

**用法 2｜MATLAB 主控（路线 B，本文主力）**
\`\`\`
MATLAB(bayesopt/surrogateopt) → Python 目标模块(patch 网表 → 跑 ADS → 读结果) → 返回标量
\`\`\`
适合：目标昂贵（EM/HB）、要少评估、要出收敛图。

**用法 3｜离线代理（省最多时间）**
\`\`\`
已有 N 组历史 (参数, 指标) 数据 → fitrgp 建代理 → 在代理上 bayesopt/ga 搜索 → 只对 top-k 做真评估
\`\`\`
适合：像 lbq1 那种已经攒了几百组数据的场景。

---

## 8. 一句话总结

**MATLAB 的价值不在"会算"，而在"少算"**——把昂贵的 ADS 评估（EM/HB）用 \`bayesopt\`/\`surrogateopt\` 的少数次评估逼近最优；ADS 只当评估器，MATLAB 当优化器与分析器。**它替代不了结构创新**：换求解器救不了拓扑问题（lbq1 的四组宽度全部收敛到同一个值就是证据）。
