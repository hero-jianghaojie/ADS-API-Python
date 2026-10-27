---
name: ads-automation
description: "Keysight ADS（Advanced Design System）自动化总入口，Windows 本机环境。Use when a task touches ADS workspaces/schematics/layouts, Momentum or RFPro EM, EM-circuit co-simulation, parameter sweeps, optimization, or reading .ds/.sio datasets; also use when the user says ADS、Momentum、RFPro、hpeesofsim、keysight.ads、adsMomWrapper、版图 EM、联合仿真、滤波器/功放优化、bpf/BT/PA/FPA 单元。包含环境常量、三条执行通道、数据契约、必须遵守的不变量、坑速查与交付验收清单。"
---

# ADS 自动化（总入口）

工程根：`<REPO_PARENT>`（**不是**旧文档里的 `<MATLAB_ADS>`，该目录已不存在）。
ADS：`D:\Program Files\Keysight\ADS2025_Update2`。

## 0. 先做自检（10 秒）

```powershell
& '<BRIDGE_PY>' <REPO_PARENT>\ads_env_check.py
```

输出 `0 FAIL` 才继续；`HPEESOF_DIR` 与网桥 8765 的 WARN 按任务需要处理（见 §2/§3）。

## 1. 硬常量（唯一事实来源，别硬编码到别处）

| 项 | 值 |
|---|---|
| ADS 安装 | `D:\Program Files\Keysight\ADS2025_Update2` |
| ADS Python 3.12 | `...\tools\python\python.exe`（**只有它**有 `keysight.*`） |
| 系统 Python 3.10 | `<BRIDGE_PY>`（有 shapely/skrf，**没有** keysight） |
| 命令行 EM | `...\bin\adsMomWrapper.bat` |
| 电路仿真 | `...\bin\hpeesofsim.exe`（**必须经** `ads_sim_helper` 调用，直接调静默失败） |
| MATLAB | `<MATLAB_HOME>\bin\matlab.exe`（`-batch` 无头） |
| 网桥 | `http://127.0.0.1:8765`（XML-RPC，跑在 ADS 进程内） |
| 主工作区 | `<REPO_PARENT>\work\JHJ_CLASSF_Filter_wrk`（库 `JHJ_CLASSF_Filter_lib`） |
| 滤波器工作区 | `<REPO_PARENT>\work\Study_wrk`（库 `Study_lib`） |
| **自动化训练工作区** | `<WORKSPACE>`（库 `ADS_Auto_lib`，2026-10-05 建；工艺已配：85 图层 + `ads_standard_layers`/`ads_schematic_layers` 参考库；**已装 design kit**：`muRataLibWeb`(80 cell，村田电感电容) + `CGH40_r6`(9 cell，含 Cree 器件 `CGH40010F_r6_CGH40_r6`)，各带 `_tech`） |
| **布局单位** | **毫米 mm**（用户偏好，2026-10-05 明确要求；新建库用 `create_layout_tech_std_ads("mm", 1000)`，**不要** mil/micron） |

**两套 Python 不许混用**：几何/出图/搜索 → 系统 3.10；碰 ADS 对象/读数据集 → ADS 3.12。
**RFPro/EMPro 脚本必须包一层**：`%HPEESOF_DIR%\bin\adsEmproEnv.bat python xxx.py`。
**读 `.sio` 前必须** `$env:HPEESOF_DIR='D:\Program Files\Keysight\ADS2025_Update2'`。

### 新建库/工作区的配置（2026-10-05 实测，全走网桥 API）

```python
import keysight.ads.de as de
from keysight.ads import ael
WS, LIB = r"<WORKSPACE>", "ADS_Auto_lib"
ws  = de.create_workspace(WS)            # 只建不打开
ws  = de.open_workspace(WS)              # 或 open_workspace(WS, force=True) 关掉旧的再开
lib = de.create_new_library(LIB, WS + "\\" + LIB)
lib.create_tech()                                        # 1) 建本库工艺
lib.create_layout_tech_std_ads("micron", 1000)           # 2) 标准版图层 + 单位（单位最终由参考库图决定）
ael.call.tech_open_technology(LIB, "a")                  # 3) 设参考库（示意图层必须）
ael.call.tech_set_libraries_used_by_technology(LIB, ael.call.list("ads_standard_layers", "ads_schematic_layers"))
ael.call.tech_save_technology(LIB)
```

- ⚠️ `lib.setup_schematic_tech(False|True)` 在**本机必崩**：`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xce`（ADS 内部 C++ 读某资源按 UTF-8 解），**别用**，用上面的 `tech_set_libraries_used_by_technology` 代替。
- ⚠️ `create_new_library` **不会**写 `<wrk>\lib.defs` → 库只在内存里，重开工作区就丢。必须自己补两行（与 ADS 约定一致）：
  ```
  DEFINE <lib> <lib>
  ASSIGN <lib> libMode shared
  ```
  然后 `de.open_workspace(WS, force=True)` 重载即可看到库带着工艺回来。
- ⚠️ `delete_cell` 报 `The cell has open cellviews` 时，`de_close_all()` **不管用**；实测**重开工作区**（`open_workspace(..., force=True)`）后即可删除。
- 技术类型：`ael.call.tech_get_library_technology_type(LIB)` → 1 = legacy（ADS 自带库 ads_standard_layers/ads_rflib 都是 1；与旧工程一致，保持不动）。
### 命名约定（用户约定，2026-10-05 实测）

- **工作区 Folder 可以用中文** —— 它只是 `workspace.ads` 里的虚拟组织容器（`<Folder Name="中文" />`），不参与网表；ADS 没有建/删 Folder 的 API，只能 GUI 里加。
- **库 / 单元 / 视图 / 网络 / 端口 / 变量 / 数据集名一律 ASCII**（`小写字母+数字+下划线`）：这些名字会进入网表、`proj.*`、`.ds` 文件名与 `%X` 转义逻辑，**中文名会在 hpeesofsim / Momentum 环节失败**。
- **工作区路径必须全 ASCII**（中文路径只能只读浏览、无法生成网表）；新工作区一律放 `<REPO_PARENT>\work\<ascii>_wrk`。

- **加 design kit（库）**：`ws.add_library(<lib_name>, <lib_dir>, LibraryMode.READ_ONLY)`，会自动写进 `<wrk>\lib.defs`（DEFINE/ASSIGN），**比重开工作区前手改文件稳**。库名/目录去 kit 自带的 `lib.defs` 里读。已装：`muRataLibWeb`（`D:\<external>\ADS\adsZIP\zipped\murata_lib_ads2011later_521e\murata_lib_ads2011later_521e`，80 cell）、`CGH40_r6`（`D:\<external>\ADS\adsZIP\zipped\CGH40_r6_converted`，9 cell，**含 `CGH40010F_r6_CGH40_r6`，用户要的就是这个**）。
- **移出（取消注册）一个 kit 的安全做法**：不要碰 `ws.remove_library`（怕误删 PDK），改为**手工删 `lib.defs` 与 `workspace.ads` 里对应行**再 `open_workspace(force=True)`；D 盘文件不动。2026-10-05 已用此法移出 `CGH40010F`/`CGH40010F_tech`。
- 同目录另有 `Cree_Wlfspd_ADS_v9p0`、`MRF8P9040N_Level2_Rev2_DK`、`tsmc18rfpdk` 等未装。

### 原理图 / 仿真自动化（2026-10-05 实测，样板 = `ADS_Auto_lib:dc_sweep`）

```python
from keysight.ads.de import db_uu
from keysight.ads.de.db_uu import DesignMode
d = db_uu.Design("ADS_Auto_lib", "dc_sweep", "schematic", DesignMode.APPEND)   # 新单元先 db_uu.create_schematic(...)
V1  = d.add_instance(("ads_sources", "V_DC", "symbol"),  (0.0, 0.0),   name="V1")
R1  = d.add_instance(("ads_rflib", "R", "symbol"),       (1.5, 0.0),   name="R1")
G1  = d.add_instance(("ads_rflib", "GROUND", "symbol"),  (2.0, -1.0),  name="G1")
DC1 = d.add_instance(("ads_simulation", "DC", "symbol"), (0.0, 2.0),   name="DC1")
VAR = d.add_var_instance((0.0, 3.5), name="VAR1"); VAR.vars["Vsweep"] = "1"
d.add_wire([(0,0),(0,0.5),(1.5,0.5),(1.5,0)], layer_id=d.default_wire_layer)   # 只为好看
# ★★ 电气连通 = 把同一个 Net 对象赋给多个 InstPin.net（add_wire 不建立连通！）
pins = {str(p): p for i in d.instances for p in i.inst_pins}
pins['<InstPin "R1.1">'].net = pins['<InstPin "V1.1">'].net
pins['<InstPin "V1.2">'].net = pins['<InstPin "G1.1">'].net      # gnd!
pins['<InstPin "R1.2">'].net = pins['<InstPin "G1.1">'].net
V1.parameters["Vdc"].value = "Vsweep"            # 源值写成变量
DC1.parameters["SweepVar"].value = '"Vsweep"'    # ★ 字符串参数要自带引号
for k, v in (("Start", "0"), ("Stop", "5"), ("Step", "0.1")):
    DC1.parameters[k].value = v
d.save_design(); nl = d.generate_netlist()
```

宿主侧跑仿真（纯 stdlib，系统 Python 即可）：

```python
import sys; sys.path.insert(0, r"<REPO_PARENT>")
from ads_sim_helper import run_hpeesofsim
r = run_hpeesofsim(nl, r"<WORKSPACE>", "dc_sweep")   # -> <wrk>\sim\<design>\<design>.ds
```

**★★ 正式连线（官方 AEL 路径，2026-10-05 实测）—— "把原理图连得好看"的正解**

```python
from keysight.ads import ael
ctx = ael.call.de_get_current_design_context()                      # 或 de_get_design_context_from_name("lib:cell:schematic")
lid = ael.call.db_get_layerid_for_schematic_wires(ctx)              # 原理图导线层 = LayerId 228
ael.call.de_set_route_around_annot(1)     # 走线绕开标注
ael.call.de_set_reroute_wires(1)          # 移动元件后只从端点重走线
for pts in [[(0.0,1.0),(1.5,1.0)],        # V1.+ -> R1.1
            [(2.5,1.0),(2.5,0.0),(1.5,0.0)],
            [(1.5,0.0),(0.0,0.0)],
            [(1.5,0.0),(1.5,-0.6)]]:      # 底轨 -> 地（竖直 stub，不横穿地符号）
    ael.call.de_connect()
    for x, y in pts:
        ael.call.de_add_wire(float(x), float(y))
    ael.call.de_end()
# 验证：每个 pin 返回 1 表示已接到导线
ael.call.db_is_inst_pin_connected_to_wire(pin)
```

- **只有 \`de_connect() → de_add_wire(x,y)… → de_end()\` 会建立真正的电气连通**；Python 的 \`db_uu.add_wire()\` 只画图形、不连通（本项目实测的坑）。
- **布线规则（够用版）**：只用水平/垂直段；同一节点用一条"底轨"汇合；**地符号用短竖直 stub 吊在轨下面**，绝不让导线横穿地符号；元件标签会被导线压住时，把元件挪开而不是绕远。
- 引脚坐标先量：\`inst.inst_pins\` → \`pin.snap_point\`（单位 inch）；旋转用 \`add_instance(..., angle=270)\`（V_DC：angle 0/180 水平、90/270 竖直，pin1 总在原点、pin2 在 1 inch 处）。
- 相关官方帮助页（本地 7479 页，版本精确匹配）：\`ael\de_add_wire()\`、\`ael\de_connect()\`、\`ael\de_end()\`、\`ael\db_is_inst_pin_connected_to_wire()\`、\`ael\db_get_layerid_for_schematic_wires()\`、\`ael\de_set_route_around_annot()\`、\`ael\de_set_reroute_wires()\`。
- 截图核对：\`ads_tools/ads_win.py list\` 找到设计窗口 HWND → PowerShell \`System.Drawing\` 的 \`CopyFromScreen\` 抓那个矩形 → \`read_image\` 看效果（GUI 会即时刷新 API 的改动）。

**★★ 收尾规定动作：工作区 force-reload 后必须立刻开回设计窗口**

`de.open_workspace(WS, force=True)` 会关掉**所有**设计窗口，此后 ADS 的 "current window" = 主窗口（不含设计）。此时任何需要 "active window command name" 的 AEL/UI 动作都会弹：

```
ERROR: (deviewcb.ael line 1368, column 23 in de_get_active_window_command_name)
The specified window does not contain a design.
A schematic, symbol or layout window is must be specified.
```

（用户会在 GUI 里看到这个报错框；数据不会丢，但很扰人。）⇒ **reload 之后立刻**：

```python
ctx = ael.call.de_get_design_context_from_name("LIB:CELL:schematic")
ael.call.de_show_context_in_new_window(ctx)      # 把设计窗口开回来
```

- **★ 抽头（bias tee / 分叉）必须把线拆开**：实测 `db_is_inst_pin_connected_to_wire` 对"落在导线中段"的 pin 返回 0（netlist 里该 pin 自成孤网）。凡是 DC_Feed / 地 / 电阻要接到一条干线上的地方，**把干线在该点拆成两段**，让 pin 落在导线**端点**上。判断连通性一律用 `db_is_inst_pin_connected_to_wire(pin)==1` 逐个断言，再看 netlist 里两侧 pin 是否同网。

**★ 先开设计窗口，才能画 AEL 导线**：工作区刚 force-reload 后没有"当前窗口"，\`de_connect()\` 会报 \`Current window does not exist or does not have a design\`（GUI 里弹 \`deviewcb.ael ... The specified window does not contain a design\`）。先开窗：

```python
ctx = ael.call.de_get_design_context_from_name("LIB:CELL:schematic")
win = ael.call.de_show_context_in_new_window(ctx)            # 总是新开一个（重载工作区后用这个更稳）
# 或 ael.call.de_bring_context_to_top_or_open_new_window(ctx)  # 优先复用已有窗口
```

**DC IV 样板（CGH40010F_r6，2026-10-05 跑通）**

- 器件：\`("CGH40_r6", "CGH40010F_r6_CGH40_r6", "symbol")\`；引脚 1=Gate(原点) 2=Drain(+0.5,+0.5) 3=Source(+0.5,-0.5) 4=热(+0.5,0)；参数 \`tcase\`/\`crth\`。
- 拓扑：\`SRC1\`(V_DC, Vdc=VGS)→栅；\`SRC2\`(V_DC, Vdc=VDS)→漏；源→地；\`DC1\` 扫 VDS(0→28,步 1)；\`Sweep1\`(ParamSweep) 扫 VGS(-4→0,步 0.5)；\`VAR1\` 放 VGS/VDS。
- ★ ParamSweep 必须绑定分析实例：\`Sweep1.parameters["SimInstanceName"].value = ['"DC1"', "", "", "", "", ""]\` —— 它是 6 槽的 \`ParamRepeated\`，**值必须自带引号**；少了引号 → \`a quoted argument may be need\`，槽位不够 6 个 → \`zip() argument 2 is shorter\`，字符串被逐字符拆成 [1]=D [2]=C → \`Undefined parameter 'D'\`。
- 实测结果（261 点）：VGS=-4/-3.5 V 截止；VGS=0、VDS=28 V 时 ID≈1528 mA；曲线在 6–8 V 达峰后随 VDS 缓降（模型热效应）。脚本：\`_lbq2/_ads_build_iv4.py\`（建模）+ \`_lbq2/_run_iv_cgh.py\`（仿真）+ \`_lbq2/_read_iv_cgh.py\`（读数出图）。

**ADS 自带原理图模板（2026-10-05 挖到确切位置）**

- 模板库 = `D:\Program Files\Keysight\ADS2025_Update2\circuit\templates\library`（42 个 cell；目录名是 %X 转义，`%D%C_%F%E%T_%T` = `DC_FET_T`）。
- 用法：`ws.add_library("ads_templates", <上面路径>, LibraryMode.READ_ONLY)` 之后即可 `ws.design("ads_templates:DC_FET_T:schematic")` 读它 / 把里面的元件直接实例化进自己的设计。
- **`DC_FET_T` 只有 2 个实例**：`SIM1 = ads_simulation:DC_FET`（智能扫源，参数 VGS_start/stop/points + VDS_start/stop/points；2 个引脚：pin1=栅驱动、pin2=漏驱动）+ `disptemp1 = ads_simulation:DisplayTemplate`（`TemplateName=['"DC_FET_T"']`，放进设计后 ADS 自动出 IV 图）。器件源极接地即可；内部自带 I_Probe（数据列 `SIM1.IDS.i`，正向）与 `aele DC_power=IDS.i*VDS`。
- `FET_curve_tracer` 是老式 8 实例版：`IDS`(ads_rflib:I_Probe) / `SRC2`(Vdc=VGS) / `SRC1`(Vdc=VDS) / `G1` / `VAR1` / `Sweep1`(ParamSweep, SweepVar=VGS) / `DC1`(DC, SweepVar=VDS) / `disptemp1`。**旧 JHJ 工程的 IV 单元就是照它搭的**（数据集列 `SRC1.i/SRC2.i/IDS.i` 即证据）。
- 交叉验证：手搭版 vs `DC_FET_T` 版，同器件同偏置 **max |ΔID| = 0**（261 点）；差别只是列名与电流符号约定（`-SRC2.i` = `+SIM1.IDS.i`）。
- 坑：`de_place_design_template()` 经网桥调用报 `Insert template command is not active`（插入模板是交互命令）→ 走"注册模板库 + 直接实例化模板里的元件"这条路更稳。

**8 个坑（都实测过）**：

1. **`add_wire` 不建立电气连通** —— 线只是图形；连通必须靠"同一个 `Net` 赋给多个 `InstPin.net`"。
2. **字符串参数要自带引号**：`SweepVar.value='"Vsweep"'`；不带引号 → hpeesofsim 报 `Expected a quoted string for parameter 'SweepVar'`。
3. **不要扫源实例名**：`SweepVar="V1"` → `Cannot alter 'V1'. It is a dependent variable`；改成扫 **VAR 变量**。
4. **design 变只读**（`Attempt to save a read-only design`）：`de.open_workspace(WS, force=True)` 后取新句柄即可；桥的 `exec(code, globals())` 会跨脚本持有旧对象，也占住 design。
5. **别用 `lib.close()`**：之后 `ws.open_library(name)` 报 `Library path '' does not exist`，只能整工作区重载。
6. 元件名：`ads_sources:V_DC`(Vdc/Vac/SaveCurrent)、`ads_rflib:R`、`ads_rflib:GROUND`、`ads_simulation:DC`、`ads_datacmps:VAR`；`Cell` 取名字用 `.name`（`"V_DC" in lib.cells` 永远 False）。
7. 原理图单位是 **inch**（`d.unit_name=="in"`）；pin 坐标取 `InstPin.snap_point`。
8. **Folder 只能改 `workspace.ads`**：`<Folder Name="直流扫描"><Cell Name="lib:cell" /></Folder>`，再 `open_workspace(force=True)` 生效。

- **出图一律用 SVG（用户偏好，2026-10-06 明确要求）**：所有交付给用户的图（读数图、Smith 圆图、牵引汇总、报告图、版图/EM 结果图）存成 `*.svg` —— matplotlib 直接 `fig.savefig("xxx.svg")` 即可（扩展名决定格式）。注意 **SVG 中文字体会变方框**，图内标题/图例/刻度一律用 ASCII（或显式指定中文字体）；同时留一份 .png 无妨，但交付件必须是 .svg。

- **单位：一律毫米 mm（用户偏好，2026-10-05 明确要求）**。建库时就该用 `create_layout_tech_std_ads("mm", 1000)`（0.001 mm 分辨率）；已建的库改单位走 GUI 的 Technology Setup → Layout Units 页（程序化改会撞 `conflicts in the specified tech graph`）。后续交付尺寸、几何变量、`emit_geo` 参数一律按 mm 写。

## 2. 三条执行通道（先选通道，再写脚本）

| 通道 | 何时用 | 前置 | 入口 |
|---|---|---|---|
| **A. ADS 网桥（XML-RPC）** | 要**改/建** ADS 库单元、版图、原理图；要 GUI 实时显示 | ADS 开着 + 目标工作区已打开 + Console 里 `start_server()` | `ads_tools/ads_live_server.py` + `live_query.py` / `pb.py` |
| **B. 命令行 Momentum** | 批量 EM、参数扫描（**首选**） | 目录里有 `proj.opt/sti/sub/ltd/pin/prt`(+ `proj_a`) | `ads_tools/run_mom.py` 或 `run_em_cli.py` |
| **C. 无头 emSetup** | 要在 ADS 自己工作区留下 EM 结果、不想开窗口 | 单元已有 `emSetup` 视图 | `ael.de_get_design_context_from_name(...)` + `ael.deem_run_em_setup(ctx,'emSetup')` |

通道 A 启动（人只做一次，详见 skill `starting-ads-live-bridge`）：

```text
1. 启动 ADS（若未运行）
2. 人工打开目标 workspace（.wrk）
3. Tools → Python Console（Ctrl+Shift+P）
4. exec(open(r'<REPO_PARENT>\ads_tools\ads_live_server.py', encoding='utf-8').read()); start_server()
   成功标志：probe 返回 ping: OK / in_ads_gui True
```

通道 B 常用：

```powershell
python <REPO_PARENT>\ads_tools\run_mom.py <含 proj.* 的目录> --mode full|mesh|solve --cpw 20 --edge-mesh auto
& 'D:\Program Files\Keysight\ADS2025_Update2\tools\python\python.exe' <REPO_PARENT>\run_em_cli.py --list
```

- `-O -3D` = 重划网格 + 求解；**只要复现就用 `-3D`**（`-O` 会让结果差 ~4e-4）。
- 跑前删 `proj.sio`/`proj.log`，否则永远复用旧结果；改频段必须 `-O -DB`。
- **两个 EM 扫描不能并行**（共享基板 DB）。
- `proj.opt` 第一行 `simulationMode`：`1`=Microwave(全波) / `2`=RF(忽略辐射)。**模式是耗时主因（≈4.6×）**，RF 偏保守可快速迭代，**定稿判定必须用 MW**。
- `edgemesh_borderwidth AUTO` **必须开**（关掉会把插损算高、陷波偏移）。

## 3. 数据契约

```python
from pa_metrics_de import read_metrics          # 电路/HB 指标
m = read_metrics(ds_path)
# 键: freq, de, pae, pout_w, pout_dbm, gain_db, ls_gain_db, pdc, pin_w
# DE = Pout/Pdc —— 报 DE 必须同时看 Pout 有没有塌
```

- HB 频率取 varblock 的 `freq` 列（**绝对 Hz**）；**不要**用 `RFfreq`（单位 MHz）。
- 数据集 `freq` 是 DataFrame 的 **index，不是列**；取列用 `df.get('S[2,1]')`。
- `db()` 参数是 `(re, im)` 元组，**不是复数**。
- Citifile 是**阵列主序**；官方 API 自动处理，手写解析用 `max|S| ≤ 1.001` 判据（`duplexer_perf.choose_layout`）。
- 复现性判据用**绝对偏差**（`|ΔS|`），相对误差在 |S|≈0 处会虚假放大。
- 交付/对比必须**同一步长**（0.1 GHz 复验；0.5 GHz 会把最差 DE 高估最多 3.7 点）。

## 4. 不变量（违反任何一条，结果不可信）

1. **评估不收敛 = 失败**，不许把算不出的点剔除后宣称达标（NaN 过滤曾造出假达标）。
2. **Pin 固定 30 dBm**；饱和点达标不代表标称点达标。
3. **基板不可换、EM 频段不可收窄**（MaxOrder=4 需要 ~4×f0 终端）。
4. **复验必须从磁盘上的交付单元自己重测**（跨网表答案不同）。
5. 带 pin 的矩形：**pin 所在轴的最小/最大边锁死，另一轴锁中心**，否则 Momentum 报 `This setup is invalid`。
6. **不带 pin 的死端枝节**改长度不需要动端口。
7. 改**已加载** emSetup 视图的磁盘文件会被会话缓存静默回退 → 只能在 GUI 改、或改生成的 `proj.opt/sti`、或**预置新视图**。
8. `PartNumber` 按元件系列索引，混用系列会取到不存在零件（会存成 NULL → 完全不出数据）。

## 5. 高频坑速查

| 症状 | 原因 / 做法 |
|---|---|
| `ModuleNotFoundError: shapely` / `No module named 'keysight'` | 用错解释器（§1） |
| `Failed to load the _pde extension module` | MATLAB 侧必须 `pyenv(...,'ExecutionMode','OutOfProcess')`；且 `HPEESOF_DIR` 要在 import 前设 |
| `KeyError: HPEESOF_DIR` 读 `.sio` | 先设环境变量 |
| `import empro` 失败 | 用 `adsEmproEnv.bat` 包一层 |
| `adsMomWrapper` 架构报错 | 设 `SIMARCH=win32_64` |
| hpeesofsim 无输出/静默失败 | 别直接调，走 `ads_sim_helper` |
| `A workspace already open` / 写不进 | 清 `.cdslck`（`ads_clear_locks.m` / 手工确认 PID 已死） |
| 中文路径 netlist 失败 | 工作区路径必须 ASCII（`C:\adswork`），中文路径只能只读浏览 |
| ADS 目录名看不懂 | `%X` = 每个大写字母与 `#` 逐字节转义（`BT_TRY`→`%B%T_%T%R%Y`，`emSetup`→`em%Setup`） |
| 圆弧被压成折线 | 别用 `simplify()`；用 `drop_collinear()`，腐蚀只做一次 |
| 建了 N 块存下去只剩 M 块 | 同网络相邻多边形被合并；用**面积**核对，别用块数 |
| RFPro 无头只入队 `Queued` | 派发只能 GUI 按 Run；批量走通道 B |
| 数据集互相覆盖 | 不同配置用不同 `DS_NAME` |
| 用 `ads_auto_setup.py` / `start_live_server_only.py` 起桥，行为诡异 | 它们的 `SERVER_SCRIPT` 指向 **旧副本**（`<external>\ADS\ads_tools\ads_live_server.py`）。统一用 `ads_tools/ads_live_server.py`（现行版） |
| 从 autoADS 跑 `export_s_params.py` 报 ImportError | 它依赖已不存在的 `E:\AI\ADS\src`；只有从旧 `<external>\ADS\ads_tools` 才成立 |
| 照抄 `scripts/*.py/.m` 里的路径 | `scripts/` 27 个文件（全仓共 33 个）硬编码已失效的 `<MATLAB_ADS>`；范例请用 §7 的 8 个文件 |
| 以为 `add_match_stub.py` 能加支节 | 它是**占位实现**，实际合并走 `merge_shapes.py` |

## 6. 能力边界（只能 GUI 的部分）

| 能力 | 可脚本化 | 备注 |
|---|---|---|
| 无头电路仿真 HB/SP/DC | ✅ | `hpeesofsim` + cfg |
| 读数据集、改变量、克隆单元、建/改版图图元 | ✅ | 通道 A / 直连 API |
| 跑 EM（Momentum） | ✅ | 通道 B/C |
| 从原理图生成版图 | ❌ | 无 API |
| 生成 EM Setup 输入文件 | ❌ | 依赖 `dex_em_writeSimulationFiles`（`pde_private.dll`，独立进程不可用） |
| EM Component → Create EM Model | ❌ | 纯 GUI（可用 pywinauto 兜底尝试） |

## 7. 工程资产索引

- 全景：`docs/AI_联合仿真优化全流程.md`（AI 入口）、`INDEX.md`、`_交接包/README.md`
- 知识底座（本次整理）：`docs/_ai_digest/01_文档结论摘要.md`、`02_工具链清单.md`、`03_ADS_Python_API速查.md`
- 工具：`ads_tools/`（网桥、run_mom、读数据、版图几何）、`scripts/`、`ads_sim_helper.py`、`run_em_cli.py`
- 几何闭环（老脚本已归档，勿按老名调用）：`fit_geom_model.py / pin_anchor.py / emit_geo.py / geom_audit.py / eval_geo.py / sample_geo.py / deliver_geo.py` 已移入 `_archive_old_cells/`；**现行继任者是根目录的 `pa30v1_geo.py`**（几何模型，68/68 往返验证）。闭环本身仍是：几何模型 → 生成 `proj_a` → `run_em_cli.py` → 联仿 → 交付 → 复验。
- **可当范本的 8 个文件**（代码层无失效旧路径）：`ads_tools/ads_live_server.py`、`ads_tools/live_query.py`、`ads_tools/run_mom.py`、`ads_tools/splice_notch.py`、`ads_tools/merge_shapes.py`、`ads_tools/duplexer_perf.py`、`pa30v1_geo.py`、`em_opt_pa30v1.py`
- 自检：`ads_env_check.py`
- 窗口工具（GUI 兜底）：`ads_tools/ads_win.py list|focus|close --title <子串>` —— 纯 ctypes 枚举/置前/WM_CLOSE（等价点右上角 X）；桥挂了 ./get started 挡路时用它
- 桥探测器：`ads_tools/probe_live.py`（ping + is_pde_app + active_workspace + PID 归属）；`pb.py <file.py>` 把脚本投进 ADS 进程执行

## 8. 交付前验收清单

1. `ads_env_check.py` 无 FAIL。
2. 评估用**交付单元自己的网表**从磁盘重算；步长与判定一致。
3. 不收敛点**保留并计失败**，报告里显式列出。
4. 报 DE 时同时给 Pout/PAE/增益；报抑制时给出频段与最差点频率。
5. 复验用绝对偏差对比；任何"改了设置"的动作都要说明是否落在 `proj.opt/proj.sti`。
6. 结论若靠间接证据（包围盒、阈值扫描、面积差）得出，用**直接证据**（逐点几何/实跑）复核一遍。

## 9. 参考

- ADS Python API：`D:\Program Files\Keysight\ADS2025_Update2\tools\python\...\keysight\`；本地帮助检索 `read_adshelp.py --list=<关键字>`（7479 页官方帮助，版本精确匹配）。
- 官方示例：`E:\AI\ads_examples\`（LNAEmCktCosim / Pin_Handling_For_EmCosim / RF_Board / Coupled_Stubs_tune）。
- 团队记忆：`memoir_read`（本项目已有 70+ 条 ADS 工作记录与经验教训）。
