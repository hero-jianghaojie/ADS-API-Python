# ADS Python 教程合集导读（9 集）

> 本文是个人学习笔记，整理自 B 站合集 [ADS Python Tutorial](https://www.bilibili.com/video/BV1cwgEzcEPG/)（UP 主：连接器技术汇，共 9 集，约 158 分钟）。
> 原始幻灯片与讲解的版权归 Keysight Technologies 及视频作者所有；本文只做要点归纳与 API 索引，未复制幻灯片图片。
> 整理方式：B 站公开 API 取元数据与视频流，ffmpeg 场景抽帧后逐帧阅读；合集无 CC 字幕，未逐句转写。

来源：B 站合集「ADS Python Tutorial」，UP 主「连接器技术汇」，共 9 集，总时长约 157 分钟。
整理方式：B 站 API 取元数据与视频流 → ffmpeg 场景抽帧 → 逐帧阅读幻灯片与代码画面。
局限：合集无 CC 字幕；本地语音识别模型下载受阻，**未逐句转写**，本文以幻灯片与画面中的代码为依据。

## 一、学习路径建议

1. 先看 00（Introduction）建立全局：DE/DDS 两个解释器、venv 与 wheels、2025 起原生 API 全貌。
2. 01 → 02 → 03 是递进的最小闭环：**建 workspace/库 → 建原理图与放器件 → 跑仿真、处理数据、画图**。
3. 04 补变量与 MeasEqn（做参数化与公式化测量的关键）。
4. 05 是综合应用：用 Python 合成滤波器（Chebyshev 低通）并自动生成原理图。
5. 06 参数扫描与多维数据绘图。
6. 07 PDK 与 DC-IV 特性；08 版图（layout）创建。

## 二、分集要点

### 00 Introduction to Python in ADS（12:10）
- DE 与 DDS 各自内嵌 Python 解释器，执行上下文独立；`keysight.ads.de.is_pde_app()` / `keysight.ads.dds.is_dds_app()` 判断环境。
- 外部 IDE（VS Code / Jupyter）无头自动化：直接 `import keysight.ads.de` 或 `keysight.ads.dds`；venv 的 Python 主次版本必须与 ADS 一致。
- 安装 wheels：`$HPEESOF_DIR/tools/python/wheelhouse` 下 `pip install -r venv_requirements.txt --find-links .`。
- 周边栈：EDA Toolbox、PW Data Tools、Nexus。
- ADS 2025+ 原生 API：workspace/library、schematic/layout/symbol、改设计、VARs/MeasEqn、菜单/Add-On/GUI、ANN 抽取、基板、数据显示。
- 版本策略：新 API 先入 experimental 库，成熟后进稳定库；稳定库按年随大版本更新。

### 01 Getting Started with Python Console（20:52）
- 演示在 ADS 内 Python 控制台与 VS Code 两侧同步写脚本。
- 关键调用：`de.create_workspace(path)`、`workspace.open()`（返回是否为新开）、`de.create_new_library(name, path)`、`workspace.open_library(name, path, de.LibraryMode.SHARED)`。
- 注意点：workspace 已打开时不要重复创建；库必须挂在已打开的 workspace 下。

### 02 Creating & Working with Schematics（22:23）
- 用 `db.create_schematic(...)` 建原理图；`design.add_instance("in1", "AMP", [x, y], "0")` 放器件；`design.add_pin(...)` 加端口。
- 演示了按器件引脚循环建 pin、按网表/连接关系布线（画面中可见 for 循环遍历 component.numpins）。
- 主题：从 Python 控制台创建原理图，并对原理图里的器件做放置与操作。

### 03 Simulation, Data Processing & Result Plots（20:03）
- 流程：建设计 → 放器件并设参数 → `netlist = design.generate_netlist()` → 仿真引擎 → 取 dataset → 用 matplotlib 画频响。
- 画面中可见 `ads.simulator_engine(...)`、dataset 读取、`pyplot` 绘图（滤波器 S21 曲线）。
- 主题：从控制台搭电路仿真、用 Dataset 模块处理结果、在 Python 里出图。

### 04 Working with VARs and MeasEqns（19:06）
- 变量：`design.add_var_instance(...)`（含表达式与单位，如 `[1000 2000] mH`）。
- 测量方程：`design.add_meas_eqn(...)` 把公式挂到设计上。
- 仿真后从 dataset 取数据、做 dB/群时延等后处理并绘图。

### 05 Using Python based Synthesis IPs（20:31）
- 用 EDA Toolbox 的合成函数（如 Chebyshev 低通 `lpf_design_ByChebyshev`）从指标算出微带线宽/线长。
- 再自动生成原理图（MLIN/MTEE/电容等），形成"指标 → 综合 → 原理图"的自动化链路。
- 后段出现 3D/EM 视图，示意版图或 EM 验证。

### 06 Parameter Sweep & Multi-Dimensional Data Plots（14:18）
- 在 Python 里设置参数扫描，跑多组仿真。
- 多维数据绘图：按扫描变量组织 dataset，画族曲线/二维图。

### 07 Working with PDKs and DC-IV Characteristics（14:42）
- 打开 PDK 库、取器件；用 `create_dciv_characteristic(...)` 生成 DC-IV 特性并 `plot_dciv_characteristic(...)`。
- 画面含版图视图（器件几何），说明 PDK 器件与版图、特性曲线的联动。

### 08 Getting Started with Layout Designs using Python（13:21）
- 建库后建 layer：`de.create_layer(lib, "cond", LayerMode.IMAGE, ...)`；建 layout：`db.create_layout(lib, name, view)`。
- 几何图元：`layout.add_rectangle(...)`、`add_polygon(...)`、`add_line(...)`、`add_text(...)`，最后 `layout.snap()`。
- 主题：用 Python 从零创建版图几何，并与 ADS 版图视图联动。

## 三、可复用 API 速查（按出现顺序）

| 类别 | 调用 | 出现集 |
|---|---|---|
| 环境判定 | keysight.ads.de.is_pde_app() / keysight.ads.dds.is_dds_app() | 00 |
| 工作区 | de.create_workspace(path)、workspace.open() | 01 |
| 库 | de.create_new_library(name, path)、workspace.open_library(name, path, LibraryMode.SHARED) | 01 |
| 原理图 | db.create_schematic(...)、design.add_instance(...)、design.add_pin(...) | 02 |
| 仿真 | design.generate_netlist()、ads.simulator_engine(...) | 03 |
| 数据 | dataset 读取、matplotlib pyplot | 03/04 |
| 变量/方程 | design.add_var_instance(...)、design.add_meas_eqn(...) | 04 |
| 合成 IP | edatoolbox 的滤波器综合函数 | 05 |
| 扫描 | 参数扫描 + 多维绘图 | 06 |
| PDK | 打开 PDK 库、create_dciv_characteristic / plot_dciv_characteristic | 07 |
| 版图 | de.create_layer(...)、db.create_layout(...)、add_rectangle/add_polygon/add_line/add_text、snap() | 08 |

> 表中函数名来自幻灯片与代码画面的可读部分；个别参数顺序在小字号画面中无法完全确认，实际使用时以 ADS Python API 文档为准。

## 四、与现有工作流的衔接

- 你现在的外部驱动方式（ads_live_server + XML-RPC）与视频里"headless + `import keysight.ads.de`"是同一目标的两条路径；后者依赖 ADS 自带 wheel 与 venv 版本对齐，前者不依赖，但需要自己维护 RPC 服务。
- 视频里的 `create_workspace / create_new_library / db.create_schematic / add_instance / generate_netlist` 正好覆盖你之前手工做的"建工程、克隆单元、改参数、跑 EM"的上游环节；版图部分（08）可与现有的版图几何脚本对照。

## 五、采集说明

- 每集通过 `x/web-interface/view` 取 cid，`x/player/playurl?fnval=16` 取流，ffmpeg 以 `select='gt(scene,0.06)'` 抽场景帧。
- 各集抽帧数：00=11、01=9、02=5、03=8、04=8、05=53、06=11、07=20、08=17。
- 02/05 等以操作演示为主的集，场景帧只能覆盖部分代码画面；要精确到每一行代码，需要逐句讲稿或更高帧率抽样。
