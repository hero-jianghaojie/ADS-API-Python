# MATLAB-ADS 联合仿真整理与可行性验证

> 日期：2026-08-15　|　环境：MATLAB R2025a + Keysight ADS 2025 Update 2（`D:\Program Files\Keysight\ADS2025_Update2`）
> 本文档整理 Matlab↔ADS 联合仿真的全部可行方案，并记录本机实测的可行性结果。

---

## 1. 方案总览

| 方案 | 原理 | 双向性 | 版本耦合 | 本机可行性 | 推荐度 |
|---|---|---|---|---|---|
| **A. MATLAB 直调 ADS Python API** | MATLAB 的 `py.` 桥接 → `keysight.ads.de` / `keysight.ads.dataset` | 双向（建网表+读数据） | 需匹配 Python 版本 | ✅ **已端到端验证** | ⭐⭐⭐ 首选 |
| **B. 文件交换（Touchstone/CSV）** | ADS 导出 `.s2p/.s4p/.csv/.ds`，MATLAB 读取处理 | 单向为主 | 无 | ✅ 天然可用 | ⭐⭐⭐ 最稳 |
| **C. ADS 原生 MATLAB 组件** | ADS 的 `%Matlab%Output` 与 `com_calc\Matlab` 脚本（通道分析/眼图/抖动） | MATLAB 作计算引擎 | 强 | ⚠️ 需特定仿真场景 | ⭐ 适用面窄 |
| **D. RPC/Socket 桥** | MATLAB 与 ADS 内 Python（`ads_live_server`）通过 XML-RPC/TCP 通信 | 双向 | 弱 | ✅ 已有 `ads_tools` 基础 | ⭐⭐ 与现有框架一致 |

**结论**：本机 **方案 A 已打通完整链路**（打开工作区→生成网表→读取 S 参数→MATLAB 处理），可作为标准工作流；方案 B 用于无 Python 桥接时的兜底；方案 D 可复用工作区现有 `ads_live_server.py`。

---

## 2. 方案 A：MATLAB 直调 ADS Python API（已验证 ✅）

### 2.1 原理

MATLAB（R2018b+）内置 Python 桥接 `py.`，可直接调用 ADS 自带的 Python 解释器及其 `keysight.ads` 包：

```
MATLAB (R2025a)
   └─ py. 桥接（OutOfProcess）
        └─ ADS Python 3.12.2 (tools\python\python.exe)
             ├─ keysight.ads.de       # 设计自动化：打开工作区/设计、生成网表、建图元
             └─ keysight.ads.dataset  # 读仿真数据集 .ds、S 参数等
```

### 2.2 关键配置（两个坑）

1. **必须用 `OutOfProcess` 模式**：
   ```matlab
   pyenv('Version', ADS_PY, 'ExecutionMode', 'OutOfProcess');
   ```
   MATLAB 默认 `InProcess` 会把 Python 原生 DLL 加载进 MATLAB 进程，与 ADS 的 `_pde` 扩展 DLL 冲突，报 `ImportError: Failed to load the _pde extension module`。切到 `OutOfProcess` 后 Python 独立进程运行，DLL 无冲突。

2. **必须设置 `HPEESOF_DIR`**（在 `import` 之前）：
   ```matlab
   setenv('HPEESOF_DIR', 'D:\Program Files\Keysight\ADS2025_Update2');
   ```
   `keysight.ads.de` 的 `_extension_setup.setup_environment()` 会据此把 ADS `bin` 加入 DLL 搜索路径。

3. **建议在未激活 venv 的终端运行**，否则 MATLAB 默认选中工作区 venv（Python 3.10）导致版本不匹配。显式 `pyenv('Version', ADS_PY)` 可强制切换。

### 2.3 标准化初始化（已封装 `ads_init.m`）

```matlab
% 一行初始化：返回 de / ds 两个句柄
[de, ds] = ads_init();   % 详见 ads_init.m
```

### 2.4 典型工作流（已端到端验证，见 test_e2e_ads.m）

```matlab
[de, ds] = ads_init();                                   % 1) 初始化桥
ws = de.open_workspace('D:\AppGallery\codex\ADS\python_wrk');  % 2) 打开工作区
d  = ws.design('python_lib:py_ms_lpf:schematic');        % 3) 打开设计
nl = d.generate_netlist();                               % 4) 驱动 ADS 生成网表
dset = ds.open_dataset_for_reading('....\py_ms_lpf.ds'); % 5) 读仿真结果
vb = dset.get('SP1.SP');
df = vb.to_dataframe();
freq = double(df.index.to_numpy());                      % 频率 (Hz)
s21   = double(df.get('S[2,1]').to_numpy());             % 复数 S21
% —— 之后全部是纯 MATLAB 处理 ——
s21dB = 20*log10(abs(s21));
plot(freq/1e9, s21dB); grid on;
```

### 2.5 本机实测结果（2026-08-15）

```
[1] import keysight.ads.de / dataset      → OK
[2] open_workspace(python_wrk)            → OK（加载 CGH40_r6、muRataLibWeb 设计套件）
[3] library_names                         → OK（26 个库）
[4] design('python_lib:py_ms_lpf:schematic').generate_netlist() → OK（3289 字符）
[5] open_dataset_for_reading(py_ms_lpf.ds) → OK（500 点，0.01–5 GHz）
[6] MATLAB 计算 S21/S11(dB)               → OK（f=1GHz: S21=-0.24dB, S11=-17.4dB）
```

---

## 3. 方案 B：文件交换（最稳兜底，无需版本匹配）

**原理**：ADS 仿真后导出标准数据文件，MATLAB 读取；或 MATLAB 生成参数文件，ADS 读取后仿真。

- **ADS → MATLAB**：Touchstone `.s2p/.s4p`（`sp` 数据）或 `.csv` / `.ds`。
  - MATLAB 读 Touchstone：`RF Toolbox` 的 `sparameters('file.s2p')`；或 `readtable` 读 CSV。
  - 读 `.ds`：需要 `keysight.ads.dataset`（即方案 A）或 ADS 导出 CSV。
- **MATLAB → ADS**：MATLAB 把优化参数写入文本/CSV → ADS（Python 脚本或设计变量）读取 → 仿真 → 再导出。

**优点**：零版本耦合、最稳定。**缺点**：无法实时双向交互，需手动/定时触发。

---

## 4. 方案 C：ADS 原生 MATLAB 组件（适用面窄）

ADS 自带 MATLAB 相关资源（本机已确认存在）：

- `oalibs\rf\ads_simulation\%Matlab%Output` — 系统架构(RFA)/数据流仿真中的 MATLAB 输出端口。
- `lib\com_calc\Matlab\v1.54|v1.65\*.m` — 通道分析类计算脚本（`save_Jitter.m`、`save_PDF.m`、`save_Eye*.m`、`com_ieee...` 等），ADS 调用 MATLAB 做后处理。

**适用**：SerDes/通道仿真、眼图、抖动、误码率等把 MATLAB 当作计算引擎的场景。**不适用**：常规射频功放 S 参数联合仿真。

---

## 5. 方案 D：RPC/Socket 桥（复用现有 ads_tools）

工作区已有成熟架构：ADS 内运行 `ads_live_server.py`（XML-RPC，端口 8765），外部驱动。
MATLAB 可用 `webread`/`java.net.Socket` 或 MATLAB 内置 `xmlrpc`（需第三方）调用同一 RPC 服务：

```
MATLAB --(HTTP/XML-RPC)--> ADS 内 Python(keysight.ads.de) --> ADS
```

- 优点：与现有 `ads_tools`（`ads_live_client.py`、`start_live_server.py`）完全一致，MATLAB 侧无 Python 版本问题。
- 现状：`ads_tools` 的 live server 已实现打开版图、加图元等；可扩展 `simulate`/`read_dataset` 两个 RPC 方法即可闭环。

---

## 6. 目录结构（Matlab_ADS）

```
Matlab_ADS/
├── README.md                    # 本文档（方案整理 + 可行性结论）
├── 使用步骤.md                  # 逐步操作手册（环境/启动/用法/排错）
├── ads_init.m                   # [可用] 初始化 MATLAB-Python-ADS 桥（方案 A）
├── read_ads_dataset.m           # [可用] 把 .ds 数据集读成 MATLAB 结构体
├── ads_set_param.m              # [可用] 设置设计实例参数（改原理图）
├── ads_run_sim.m                # [可用] 生成网表 + 跑 hpeesofsim + 读回
├── ads_sim_helper.py            # [可用] 仿真引擎（搭建 hpeesofsim 完整环境）
├── ads_lpf_cost.m               # [可用] 低通滤波器代价函数（供 fminsearch）
├── demo_optimize.m              # [可用] 自动调参闭环示例（fc→2GHz 优化）
├── test_matlab_python_ads.m     # [通过] 桥接可行性冒烟测试
├── test_e2e_ads.m               # [通过] 端到端：打开工作区+建网表+读 S 参数
├── demo_plot_s21.m              # [通过] 读 S 参数并绘图示例
└── test_pde_real_error.m        # 诊断用（InProcess DLL 冲突复现）
```

## 7. 自动优化闭环（已打通 ✅）

新增"MATLAB 自动设参 → 仿真 → 读回 → 迭代"完整闭环，实测通过（见 `demo_optimize.m`）：

```matlab
[de, ds] = ads_init();                          % 1 初始化桥
ws = de.open_workspace('...\python_wrk');
d  = ws.design('python_lib:py_ms_lpf:schematic');
ads_set_param(d, {'TL2','L','5.087563 mm'});    % 2 自动设参（改原理图）
out = ads_run_sim(d, wrk, 'py_ms_lpf');         % 3 自动仿真 + 读回
% 4 用 fminsearch 迭代：ads_lpf_cost -> ads_run_sim -> 更新参数
xopt = fminsearch(@(x) ads_lpf_cost(d,wrk,x,2.0), x0, opts);
```

**实测结果（2026-08-15）**：优化 LPF 截止频率，`1.892 GHz → 1.998 GHz`（目标 2.0 GHz），代价 0.225 → 0.000。

**cell_1 带通滤波器优化（`demo_optimize_cell1.m`）**：2.5GHz 平行耦合线带通，优化 VAR1 的 W1/S1/L1/L2/L3，
通带均值 S21 `-6.10 → -0.31 dB`、S11 `-5.63 → -23.70 dB`，代价 18.38 → 3.77，生成 `optimize_cell1_result.png`。

> **保存到原理图**：脚本用 `de.db.DesignMode.APPEND` 打开设计，优化完调用 `d.save_design()` 落盘。
> 注意 `READ_ONLY` 无法保存、`WRITE` 打开为空，只有 **`APPEND`** 才能编辑+保存已有设计（2026-08-15 实测）。

> 关键：`hpeesofsim` 需要 ADS **全部组件子目录**在 PATH 里才能启动
> （否则报 0xC0000135 DLL 缺失）。已封装进 `ads_sim_helper.py`，MATLAB 侧无需处理。

## 8. 运行方式

在 **未激活 venv** 的 PowerShell 中（重要，避免 MATLAB 选中 venv Python）：

```powershell
cd d:\AppGallery\codex\Matlab_ADS
& "d:\Program Files\MATLAB\R2025a\bin\matlab.exe" -batch "test_e2e_ads"
```

或打开 MATLAB GUI 后：

```matlab
cd d:\AppGallery\codex\Matlab_ADS
test_e2e_ads
```

> 说明：在任意目录运行后，ADS 自动化进程会在该目录生成 `de_sim.cfg` / `hpeesofsim.cfg`
> （ADS 默认工程配置，无害，可忽略；不要把它当成工作区）。

## 9. 下一步建议

1. 封装 `ads_sim_run(cellref, ...)`：MATLAB 里一键「建网表→跑 hpeesofsim→读结果」的完整闭环。
2. 把优化循环放到 MATLAB（参数 → ADS 仿真 → 读 S 参数 → 代价函数 → 参数更新），替代当前 `optimizer/` 的纯 Python 实现。
3. 如需实时双向，为 `ads_live_server.py` 增加 `simulate` / `read_dataset` RPC，供 MATLAB 调用。
