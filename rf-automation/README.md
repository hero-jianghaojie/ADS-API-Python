# ads-rf-automation

> Scriptable **Keysight ADS** automation for RF power-amplifier / filter design:
> dump & patch netlists, run simulations headlessly, optimise against explicit
> physical objectives, verify three ways, and write results back **safely**.
> 用 Python 脚本把 **ADS 单元 → 网表 → 仿真 → 优化 → 验证 → 写回** 这条闭环自动化。

**Language / 语言**: 文档主体为中文，代码与注释为英文。 (Docs are mainly Chinese; code and comments are English.)

---

## Why this repo exists / 这个仓库解决什么

Driving ADS by hand does not scale, and naive scripting fails in *specific, repeatable* ways.
This repo packages the working method **and** the failure modes we actually hit, so the next
person (or agent) does not rediscover them:

- Two distinct Python environments are required (**bridge** vs **simulation**) — the bridge
  can read/modify designs but **cannot run simulations**.
- Simulated results depend on the analysis口径 (`FundOversample`, sweep coverage, Pin …);
  an evaluator that silently reads a frequency **outside the sweep** returns plausible garbage.
- Optimisers happily **trade away an already-met spec** unless it is enforced as a
  **rejection-based hard floor**.

## The three rules / 三条铁律

1. **Bridge dumps, simulation runs elsewhere.** `pb.py` drives the ADS GUI (netlist in/out);
   `hpeesofsim` must be called with ADS's own Python.
2. **Assert sweep coverage.** Before reading any quantity (band, 2nd harmonic, stopband),
   assert `min ≤ f ≤ max` in the netlist sweep — out-of-range lookups do **not** error,
   they clamp to the sweep edge.
3. **Hard floors, not penalties.** Enforce already-met specs as feasibility rejections and
   optimise only the failing one; print the violation counts each evaluation to prove it.

## Repository layout / 目录

```
README.md
docs/                    中文方法文档（01 环境 → 09 现状，建议按序读）
  00_README_handover.md  交接包入口
  01_environment.md      环境与路径（**先读这个**）
  02_driving_ads.md      如何驱动 ADS（能力边界/导网表/打补丁/写回）
  03_simulation.md       仿真口径与评估器
  04_optimization.md     优化方法（硬地板/分阶段/身份比对）
  05_em_cosim.md         EM 与联合仿真（Momentum / ModelReuse）
  06_figures.md          出图规范
  07_domain_impedance_space.md  领域约定与 CCF/target-space 阻抗空间
  08_pitfalls.md         ★ 26 条踩坑教训（症状→原因→对策）
  09_project_status.md   项目现状与未决问题（模板）
docs/reference/          更长的专题笔记（全景总览、EM 可行性结论、自动寻优笔记…）
scripts/                 config.py + 评估器/优化器/EM 驱动/绘图
examples/                最小可运行示例（导网表 / 打补丁并仿真）
env.example              复制成 env.local 后填写本机路径（env.local 不入库）
```

## Quick start / 快速开始

```bash
git clone <your-fork-url> && cd ads-rf-automation
cp env.example env.local        # 填 ADS_HOME / BRIDGE_PY / WORKSPACE
python scripts/config.py        # 打印解析后的路径，确认无误
```

1. **Start the live bridge inside ADS** (Scripting console):
   ```python
   exec(open(r"<repo>/scripts/ads_live_server.py").read())
   ```
2. **Dump a cell** (bridge python):
   ```bash
   %BRIDGE_PY% pb.py examples/dump_netlist.py
   ```
3. **Patch + simulate** (ADS python):
   ```bash
   %ADS_PY% examples/patch_and_sim.py <work>/sim/usr/PA1.net vals.json
   ```
4. **Optimise**: start from `scripts/pyopt_pa1_po39.py` (PA) or
   `scripts/pyopt_fomn_s2b.py` (output match), swapping in your own
   evaluator settings and bounds.

## Paths / 关于路径占位

All scripts use environment variables (see `scripts/config.py`). Copies inside this repo may
still show placeholders such as `${ADS_HOME}`, `${WORKSPACE}`, `${SCRATCH}`, `${PAPER_DIR}`
where the author's absolute paths used to be — replace them via `config.py` / `env.local`
or with your own paths. **The documents in `docs/` were written against the author's machine
and are kept verbatim for context; treat their absolute paths as examples.**

## Units & naming / 单位与命名约定

- Layout units: **millimetres (mm)**.
- Library / cell / view / net / port / variable / dataset names: **ASCII, lower_snake_case**.
  Workspace *folders* may be non-ASCII, but **paths must stay ASCII** (non-ASCII breaks
  `hpeesofsim`/`Momentum` netlisting).
- Optimised values are written back with **one decimal place**, preserving `tune{}`/`notune{}`.

## Status / 状态

A working internal toolkit, extracted from a live research project. The pipeline is exercised
daily, but APIs of the private ADS python packages (`keysight.ads.de`, `keysight.ads.dataset`)
are **undocumented and version-specific** — pin your ADS version (see `docs/01`).

## Licence / 内容归属

MIT for the code (see `LICENSE` — replace the placeholder copyright). Documents under
`docs/` and `docs/reference/` include notes derived from the author's own research
(including notes extracted from the author's own research material (reviewed and removed before publishing)). **Review and remove anything
you do not want to publish before making this repository public.**

---

# English

## What this is

A small, working toolkit for driving **Keysight ADS** from Python: dump and patch netlists,
run simulations headlessly, optimise against an explicit physical objective, verify the result
three ways, and write it back into the design **safely**. Extracted from a real RF
power-amplifier / filter research workflow (mm-wave-free, 1.5–5 GHz class).

## Requirements

- **Keysight ADS** (developed on 2025 Update 2) and its bundled Python.
- A **second** Python that can start inside the ADS process for the live bridge.
- Windows (paths use `\`); Linux/macOS untested.

## The three rules

1. **The bridge dumps; a different process simulates.** `pb.py` talks to the ADS GUI.
   `hpeesofsim` must run under **ADS's own Python**.
2. **Assert sweep coverage.** An out-of-range frequency lookup does **not** raise — it clamps
   to the sweep edge and returns plausible garbage. Always assert `min ≤ f ≤ max`.
3. **Hard floors, not penalties.** Enforce already-met specs as feasibility **rejections**;
   optimise only the failing metric, and print the violation counts every evaluation.

## Install

```bash
git clone https://github.com/<you>/ads-rf-automation.git
cd ads-rf-automation
cp env.example env.local          # set ADS_HOME / BRIDGE_PY / WORKSPACE
python scripts/config.py          # prints the resolved paths
```

## Usage

```bash
# 1. inside ADS: start the bridge
python -c "exec(open('scripts/ads_live_server.py').read())"

# 2. dump a cell (bridge python)
%BRIDGE_PY% pb.py examples/dump_netlist.py

# 3. patch + simulate (ADS python)
%ADS_PY% examples/patch_and_sim.py <work>/sim/usr/PA1.net vals.json

# 4. optimise
%ADS_PY% scripts/pyopt_pa1_po39.py
```

## Design principles baked in

- **Explicit physical objective** measured from the simulator, never a proxy.
- **Pattern search** (per-variable line search, monotone acceptance, step halving) — it beat
  random search in practice (139 evaluations produced gains where 160 random ones produced none).
- **Every conclusion carries its configuration**: band, number of points, drive level,
  oversampling, terminations. Two runs of the same netlist differ by up to 8.96 points of
  drain efficiency when `FundOversample` is 1 vs 8.
- **One decimal place** on optimised values; keep `tune{}`/`notune{}` annotations.
- **Never auto-write a mixed result**: if one metric improves and another regresses, present both.

## Repository layout

| Path | Contents |
|---|---|
| `docs/` | Method notes (environment → operation → simulation → optimisation → EM → figures) |
| `docs/reference/` | Longer topic notes |
| `scripts/` | Evaluators, optimisers, EM drivers, plotting helpers, `config.py` |
| `examples/` | Minimal runnable examples |

## Notes and limitations

- ADS's Python APIs (`keysight.ads.de`, `keysight.ads.dataset`) are **undocumented and tied to
  the ADS version** — pin yours.
- The walkthrough documents were written against the author's machine; **any absolute path
  shown in `docs/` is an example** — configure real paths through `config.py` / `env.local`.
- Layout/EM work has a hard boundary: **regenerating the EM geometry input cannot be scripted**
  (it lives in an ADS plugin) — one GUI action per EM iteration is unavoidable. See `docs/05`.

## Licence

MIT for the code — see `LICENSE` (replace the placeholder copyright). Documentation is
provided as-is; verify anything before relying on it.
