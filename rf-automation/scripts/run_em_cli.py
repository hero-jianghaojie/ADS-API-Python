"""命令行运行 ADS Momentum EM 仿真（无需 GUI、无需 EM 插件）。

背景（已实测验证）：
  ADS 的 EM setup 在 <wrk>/simulation/<lib>/<cell>/<layout>/<emSetup>_MoM/ 下
  **已经存有一整套 Momentum 输入文件**（proj.prt/pin/opt/ltd/sti/cfg/mmd/msh/sub...），
  而 `bin\\adsMomWrapper.bat` 就是 Momentum 的命令行引擎。
  => 只要这些输入文件存在，就能完全脱离 GUI/插件跑 EM 仿真。

  命令行接口（官方文档 em\\Running_a_Momentum_simulation_from_Command_Line）：
     adsMomWrapper -O -3D proj proj          全流程（含重新划网格）→ S 参数
     adsMomWrapper -3D     proj proj         只跑求解（复用已有网格）
     adsMomWrapper -CD     proj proj         从已有结果生成数据集
     附加： --objMode=RF|MW   --dsName=名  --dsDir=目录

实测数据（BT20_opt2_final，0-10GHz/0.1GHz，101 点）：
   - 全流程 -O -3D：179 s
   - 只求解 -3D   ：173 s（复用时 2.5 s）
   - 与 emModel 原数据的带内(2.5-4.5GHz)最大绝对偏差 1.8e-05
   ⚠️ -O 会**重新生成网格**，结果会有约 4e-04 量级的差异；要严格复现请只用 -3D。

用法：
    <任意 python> run_em_cli.py --list
    <任意 python> run_em_cli.py --cell BT20_opt2_final --mode solve
    <任意 python> run_em_cli.py --cell BT20_opt2_final --mode full --scratch
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import time

ADS = r"${ADS_HOME}"
WRK = r"<MATLAB_ADS>\work\JHJ_CLASSF_Filter_wrk"
LIB = "JHJ_CLASSF_Filter_lib"

MODES = {
    # 名称: (引擎参数, 说明)
    "full": (["-O", "-3D"], "全流程：预处理+网格+S参数（会重新划网格）"),
    "solve": (["-3D"], "只跑 S 参数求解（复用已有网格，最快且可复现）"),
    "mesh": (["-O", "-M"], "只到网格生成为止"),
    "dataset": (["-CD"], "从已有结果生成数据集"),
}

# -3D 只写 proj.sio（proj.opt 里 SPARAM_OUTPUTFORMAT SMATRIXIO），
# **不生成 ADS 数据集**；要 .ds 需再跑一次 -CD。这些是"结果文件"，--force 时删掉以强制重算。
RESULT_FILES = ("proj.sio", "proj.sta", "proj.sam", "proj.qas")


def find_simdir(cell, view="layout"):
    """找该单元 EM setup 的 Momentum 仿真目录（含 proj.opt）。"""
    pat = os.path.join(WRK, "simulation", LIB, cell, view, "*", "proj.opt")
    hits = sorted(glob.glob(pat))
    return [os.path.dirname(h) for h in hits]


def env():
    e = dict(os.environ)
    e["HPEESOF_DIR"] = ADS
    e["SIMARCH"] = "win32_64"
    e["PATH"] = os.pathsep.join([os.path.join(ADS, "bin"),
                                 os.path.join(ADS, "bin", "win32_64"),
                                 e.get("PATH", "")])
    return e


def run(cell, mode, scratch, dsname, extra, force=False):
    dirs = find_simdir(cell)
    if not dirs:
        print("!! 找不到 %s 的 Momentum 仿真目录（需要先有 EM setup 并生成过输入文件）" % cell)
        print("   期望路径形如: %s" % os.path.join(
            WRK, "simulation", LIB, cell, "layout", "<emSetup>_MoM", "proj.opt"))
        return 2

    simdir = dirs[0]
    print("仿真目录: %s" % simdir)
    need = ["proj.opt", "proj.ltd", "proj.prt", "proj.pin"]
    miss = [f for f in need if not os.path.exists(os.path.join(simdir, f))]
    if miss:
        print("!! 缺少输入文件: %s" % miss)
        return 3

    workdir = simdir
    if scratch:
        workdir = os.path.join(WRK, "_emcli_" + cell)
        if os.path.isdir(workdir):
            shutil.rmtree(workdir)
        shutil.copytree(simdir, workdir)
        print("已复制到 scratch: %s" % workdir)

    # ⚠️ 必须在**复制之后**删结果，否则会被下一次复制还原
    #    （--scratch 每次都会重新复制整个目录）
    if force:
        n = 0
        for f in list(RESULT_FILES) + glob.glob("*.ds"):
            p = os.path.join(workdir, f)
            if os.path.isfile(p):
                os.remove(p)
                n += 1
        print("--force：已删除 %d 个旧结果文件，将强制重算" % n)

    args = list(MODES[mode][0])
    if mode in ("full", "solve", "dataset"):
        # 把数据集写到工作区外，避免覆盖既有 data/*.ds
        dsdir = workdir if scratch else os.path.join(WRK, "_emcli_out")
        os.makedirs(dsdir, exist_ok=True)
        args += ["--dsName=%s" % dsname, "--dsDir=%s" % dsdir]
    args += extra
    args += ["proj", "proj"]

    exe = os.path.join(ADS, "bin", "adsMomWrapper.bat")
    print("命令: adsMomWrapper %s   (cwd=%s)" % (" ".join(args), workdir))
    print("模式: %s" % MODES[mode][1])
    t0 = time.time()
    r = subprocess.run([exe] + args, cwd=workdir, env=env(),
                       capture_output=True, text=True, errors="replace")
    dt = time.time() - t0
    print("\n退出码 = %d，耗时 %.1f 秒" % (r.returncode, dt))
    tail = (r.stdout or "").strip().splitlines()
    print("--- 输出末尾 ---")
    for ln in tail[-12:]:
        print("   %s" % ln)

    got = glob.glob(os.path.join(workdir, "proj.sio"))
    print("\nproj.sio: %s" % ("已生成 %d B" % os.path.getsize(got[0]) if got else "未生成"))
    return 0 if r.returncode == 0 else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell")
    ap.add_argument("--mode", default="solve", choices=sorted(MODES))
    ap.add_argument("--scratch", action="store_true",
                    help="复制到 _emcli_<cell> 再跑（不碰原仿真目录）")
    ap.add_argument("--force", action="store_true",
                    help="删除旧结果强制重算（不做的话有结果就直接复用，秒回）")
    ap.add_argument("--dsname", default="EMCLI")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("extra", nargs="*")
    a = ap.parse_args(argv[1:])

    if a.list or not a.cell:
        print("工作区: %s" % WRK)
        base = os.path.join(WRK, "simulation", LIB)
        if not os.path.isdir(base):
            print("  (没有 simulation 目录)")
            return 1
        for cell in sorted(os.listdir(base)):
            ds = find_simdir(cell)
            if ds:
                print("  %-24s %d 个 EM 仿真目录" % (cell, len(ds)))
                for d in ds:
                    n = len([f for f in os.listdir(d)])
                    print("      %s  (%d 个文件)" % (os.path.basename(d), n))
        print("\n可用模式:")
        for k in sorted(MODES):
            print("   %-9s %s" % (k, MODES[k][1]))
        print("\n例: python run_em_cli.py --cell BT20_opt2_final --mode solve --scratch")
        return 0

    return run(a.cell, a.mode, a.scratch, a.dsname, a.extra, force=a.force)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
