# 01 环境与路径（**最先读**：路径错，一切错）

## 1. ADS
- 安装：`D:\Program Files\Keysight\ADS2025_Update2`（2025 Update2）
- 仿真引擎：`...\bin\hpeesofsim.exe`（用 python 驱动，见 03）
- EM：`...\bin\adsMomWrapper.bat` → 内部调 `MomEngine.exe`（**这才是入口**）；
  ⚠ `...\bin\hpeesofemx.exe` **直接调用会挂起**，不要用它。
- 版本相关：**ADS 2025 Update2**。老脚本若用别的版本路径需改。

## 2. 两套 + 一套 Python（**关键**）
| 用途 | 解释器 | 说明 |
|---|---|---|
| **驱动 ADS GUI / 读改单元** | `<BRIDGE_PY>` | 配 `<REPO_PARENT>\pb.py <脚本.py>` 走**桥接**；**能导网表，不能跑仿真** |
| **跑仿真/读数据集/优化** | `D:\Program Files\Keysight\ADS2025_Update2\tools\python\python.exe` | 有 numpy/scipy/matplotlib/pypdf，**无** `skrf`；`numpy` **无** `np.trapezoid` |
| **出"出版风格"图（复用既有绘图脚本）** | `<a venv with scikit-rf>\Scripts\python.exe` | **有 `skrf` 2.1.0**（这类脚本通常需要 scikit-rf）|

⚠ **任何导入 matplotlib 的子进程都要传环境变量**：
`HOME=C:\Users\<你>`、`USERPROFILE=...`、`MPLCONFIGDIR=<可写目录>`
否则报 `RuntimeError: Could not determine home directory.`

## 3. 桥接（live bridge）
- 客户端：`<REPO_PARENT>\pb.py`（1.1 KB，把脚本发给本机 ADS 侧的监听服务执行）
- 服务端：`<REPO_PARENT>\ads_tools\ads_live_server.py`（**必须在 ADS 进程里跑**）
- 默认端口 `127.0.0.1:8765`；探测：`<REPO_PARENT>\ads_tools\check_live_server.py`
- 若"nothing listening"但 ADS 开着 ⇒ 见技能 `starting-ads-live-bridge`
- 桥接内可用：`from keysight.ads.de import db_uu as db` + `db_uu.DesignMode`；
  **常用**：`db.Design(lib, cell, view, DesignMode.READ_ONLY).generate_netlist()` → 返回**网表纯文本**；
  ⚠ 写回时用 `DesignMode.APPEND`（用 `WRITE` 会写成空 design）；
  ⚠ pcell/实例参数取值**必须传字符串**（值是带单位的表达式，如 `"18.6164 mm"`）。
- `db_uu` 没有列库/列单元的现成 API（`get_design_views` 返回 None）⇒ **看目录里的 `*.dds`/mtime** 更可靠。

## 4. 工作区与库（本项目实际用到的）
- 主工作区：`<WORKSPACE>`
- 其它工作区：`JHJ_CLASSF_Filter_wrk`、`JHJ_CLASSF_Filter_wrk_copy`、`scratch`、`Study_wrk`、`_geosearch`、`自建原理图模型`
- 主库：`ADS_Auto_lib`（单元：`PA1/PA2/PA3`、`FOMN`、`FPA3`、`LBQ11`、`BT2_V1`、`Y2_V1`、`HMN3P5ghZ`、`BIAS`、`DCIV`、备份 `PA1_preOpt`/`FOMN_preOpt`）
- 另一库：`JHJ_CLASSF_Filter_lib`（在某些 python 环境里会报 "Failed to get data for library"）
- 网表暂存：`work\ADS_Auto_wrk\sim\usr\<CELL>.net`（**我们的约定**：把 `generate_netlist()` 的结果写这里）
- 数据集：`work\ADS_Auto_wrk\data\*.ds`；EM 模型：`...\ADS_Auto_lib\<cell>\emModel\`（内含 `model.ndx`、`data.000.sio`、`emStateFile.xml`）

## 5. 时间与时区坑
- 脚本里 `new Date().toISOString()` / python 的 UTC 时间戳 **是 UTC**；本机是 **Asia/Shanghai (+8)**。
- 判断"文件是否被改"要 **UTC+8 后**与用户时钟比；工具里看到的时间戳若非标明 UTC，需先确认口径。

## 6. 已装技能（Claude/DSH 侧）
`starting-ads-live-bridge`（建桥）、`easyeda-agent`/`easyeda-api`（嘉立创，与本项目无关）。
