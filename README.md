# ADS 自动化工具箱（ADS Automation）

射频/微波设计里，把 **Keysight ADS** 用 Python 与 MATLAB 驱动起来的一套工具、脚本与笔记。
目标只有一个：把重复操作变成可复现的脚本，并且把踩过的坑写进仓库。

## 模块总览

| 目录 | 做什么 | 原仓库 |
|---|---|---|
| [`docs/`](docs/) | ADS Python 教程合集（9 集）导读、API 速查 | — |
| [`matlab-bridge/`](matlab-bridge/) | MATLAB ↔ ADS 联合仿真桥：`ads_init`、`open_workspace`、`generate_netlist`、读 dataset | [ADS-Matlab](https://github.com/hero-jianghaojie/ADS-Matlab) |
| [`rf-automation/`](rf-automation/) | ADS 自动化闭环：网表 dump/patch → 无头仿真 → 优化 → 三重验证 → 安全写回 | [ads-rf-automation](https://github.com/hero-jianghaojie/ads-rf-automation) |
| [`em-layout-optimizer/`](em-layout-optimizer/) | 基于 EM 仿真结果的版图多边形优化工具包（连通性门禁、全带评估） | [em-layout-optimizer](https://github.com/hero-jianghaojie/em-layout-optimizer) |
| `ADS的python指令/`、`ads_tools/`、`CGH40_r6_converted/` | 早期整理的 ADS Python 指令、工具与示例 | 本仓库历史 |

## 从哪开始

1. 想先弄懂 ADS 的 Python 接口：看 [`docs/ADS-Python教程合集导读.md`](docs/ADS-Python教程合集导读.md)。
2. 想在 MATLAB 里调 ADS：看 [`matlab-bridge/`](matlab-bridge/) 的 README，三步跑通。
3. 想做「仿真 → 优化 → 写回」闭环：看 [`rf-automation/`](rf-automation/)。
4. 想优化版图几何：看 [`em-layout-optimizer/`](em-layout-optimizer/)。

## 迁移说明

2026-10-27 把三个同主题仓库并入本仓库，代码与文档保持原样（各自保留 README 与 LICENSE），来源 commit：

- `matlab-bridge` ← ADS-Matlab @ `aa04cdf`
- `rf-automation` ← ads-rf-automation @ `e57d6e0`
- `em-layout-optimizer` ← em-layout-optimizer @ `0cd4efb`

原仓库已归档（archived，只读，可随时 unarchive 恢复），作为历史与备份；日常维护集中在主仓。
