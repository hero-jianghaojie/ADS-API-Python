# 02 如何操作 ADS（可脚本化边界 + 具体招式）

## 1. 能力边界（**先记住这张表**）
| 动作 | 能否脚本化 | 做法 |
|---|---|---|
| 读单元 → 导出网表 | ✅ | 桥接 + `Design(...).generate_netlist()` |
| 批量拿变量当前值 | ✅ | 从导出网表里 `^VAR=数值$` 正则抓 |
| 改单元里的变量值 | ✅ | 桥接 + 写回（见 §3），或**只用于仿真的文本补丁**（不改单元）|
| 跑 SP/HB 等电路仿真 | ✅ | **ADS 的 python** 调 `hpeesofsim`（见 03）|
| 跑 Momentum EM | ⚠ 部分 | `adsMomWrapper -3D`（≈196 s/次，18 端口 0–10 GHz/0.1 GHz）；**打包数据集** `-CD` |
| **重生成 EM 的几何输入**（`proj_a`/`proj.pin`）| ❌ | **只能在 ADS GUI 里点**（插件函数 `dex_em_egsWrite_geometry` 只在 `bin\pde_private.dll`，AEL 调不到）|
| 版图自动分割进联合仿真(emCosim) | ❌ | 同属插件（`dex_em_simulate_from_layout`）|
| 读写数据集(.ds) | ✅ | `keysight.ads.dataset.open_dataset_for_reading` → `to_dataframe()` |
| 出图 | ✅ | matplotlib（英文标注 ⇒ 默认字体无 CJK）|

## 2. 导出网表（最常用的第一步）
```python
# <REPO_PARENT>/_dump_xxx.py  -> 用 pb.py 跑
from keysight.ads.de import db_uu as db
from keysight.ads.de.db_uu import DesignMode
nl = db.Design("ADS_Auto_lib","PA1","schematic",DesignMode.READ_ONLY).generate_netlist()
open(r"<WORKSPACE>\sim\usr\PA1_x.net","w",encoding="utf-8").write(nl)
```
运行：`"<BRIDGE_PY>" pb.py _dump_xxx.py`（cwd=`<REPO_PARENT>`）

## 3. "文本补丁"改参数（**比写回单元安全、必用**）
网表是纯文本，变量形如 `^O_TL20_L=7$`。**逐变量精确替换**（注意只替换**第一个**匹配，且用行首锚定）：
```python
import re
t = open(net, encoding="utf-8").read()
for k, v in vals.items():
    t = re.sub(r"(?m)^" + re.escape(k) + r"=[-\d.eE+]+", "%s=%.4f" % (k, float(v)), t, count=1)
```
⚠ 若某变量在网表里**出现多次**（多 VAR 块）⇒ 说明**写回必须"按名字路由"到含该变量的那个 VAR 块**（见 04 §4）。

## 4. 结构侦察（判断"用户改了什么"）
- **元件计数差分**能立刻看出**拓扑改动**：`^([A-Za-z0-9_]+):([A-Za-z0-9_]+)` 统计前缀（如 `MLIN2`/`MTEE_ADS`/`MRSTUB`/`MSTEP`/`MCROSO`/`MLOC2`）⇒ 数量变了就是**重构**，不只是调尺寸。
- **行数**几乎不变的改动 ⇒ 一定是**参数或结构替换**，要用元件计数才看得见。
- **端口/分析**：抓 `Port:`（`Num=`、`Z=`、`P[1]=`）、`HB:`（`FundOversample=`、`MaxOrder=`、`Order[1]=`）、`S_Param:`、`SweepPlan:`。

## 5. 写回单元（**只在整体更优时才做**）
- 必须：**备份原单元**（本项目惯例 `<CELL>_preOpt`）→ **按名字路由**改 → 重新导出**逐字节核对**（除优化集外必须与原值一致）→ 复测。
- 写回后**必须做"三处吻合验证"**：① 补丁网表结果 ② 写后单元导出结果 ③ 独立复测脚本结果 —— 三者一致才算成功。
- ⚠ 历史事故：早期"写到第一个 VAR 实例"导致 `Expression 'OUT_W' is already defined`（hpeesofsim 拒绝展开）⇒ **必须按名字路由**。

## 6. 清理与并发
- **同一时刻只跑一个仿真**；诊断用的网表/设计名**必须唯一**。
- 杀进程：按命令行匹配 PID，杀完`Get-Process hpeesofsim`确认 `all clear`。
- Windows 下 **必须抑制控制台窗口**：Python `subprocess` 加 `creationflags=CREATE_NO_WINDOW (0x08000000)`；Node 端 `windowsHide:true`。
- `run_code` 里 `detached` 起的进程**活不过这一步** ⇒ 要长跑就用**后台 job**（`run_in_background`）。
- PowerShell 重定向日志（`Tee-Object`）**是 UTF-16** ⇒ 读时用 `utf16le`（或先检查 `\u0000` 密度再决定）。
