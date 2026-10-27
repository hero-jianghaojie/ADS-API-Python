# -*- coding: utf-8 -*-
"""
ads_env_check.py — ADS 自动化环境自检（只读，不改任何状态）

用法（任意 Python 3.8+ 均可运行，只用标准库）：
    python ads_env_check.py
    python ads_env_check.py --json          # 机器可读
    "${ADS_PY}" ads_env_check.py

检查项：
  1) ADS 安装（ads.exe / hpeesofsim.exe / adsMomWrapper.bat / tools\python）
  2) 两套 Python（系统 3.10 / ADS 3.12）及关键包
  3) ADS 进程与 GUI 窗口、XMLRPC 桥（127.0.0.1:8765）
  4) 工作区目录与 .cdslck 写锁
  5) MATLAB（可选）
退出码：无 FAIL 为 0，否则 1。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import socket
import subprocess
import sys

PROJECT_ROOT = r"${REPO_PARENT}"
WORK_ROOT = os.path.join(PROJECT_ROOT, "work")

ADS_CANDIDATES = [
    os.environ.get("HPEESOF_DIR") or "",
    r"${ADS_HOME}",
    r"<ADS_HOME>",
]
SYS_PY_CANDIDATES = [
    r"${BRIDGE_PY}",
    sys.executable,
]
MATLAB_CANDIDATES = [r"<MATLAB_HOME>\bin\matlab.exe"]

SYS_PACKAGES = ["numpy", "scipy", "pandas", "matplotlib", "shapely", "skrf",
                "win32com", "psutil", "pywinauto", "optuna", "h5py", "sklearn"]
ADS_PACKAGES = ["numpy", "scipy", "pandas", "matplotlib", "keysight.ads",
                "keysight.pwdatatools", "keysight.edatoolbox", "empro"]

RESULTS: list[tuple[str, str, str]] = []   # (level, item, detail)


def rec(level: str, item: str, detail: str = "") -> None:
    RESULTS.append((level, item, detail))
    if not ARGS.json:
        mark = {"PASS": "[ OK ]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[level]
        print(f"{mark} {item}" + (f"  -- {detail}" if detail else ""), flush=True)


def find_first(paths, kind="file"):
    for p in paths:
        if not p:
            continue
        if (os.path.isfile(p) if kind == "file" else os.path.isdir(p)):
            return p
    return None


def has_module(exe: str, module: str) -> bool | None:
    """用子进程探测 exe 里是否能 import 指定模块；exe 不可用时返回 None。"""
    if not exe or not os.path.isfile(exe):
        return None
    code = ("import importlib.util as u,sys;"
            "sys.exit(0 if u.find_spec(%r) else 3)" % module)
    try:
        r = subprocess.run([exe, "-c", code], capture_output=True, timeout=90)
        if r.returncode == 0:
            return True
        if r.returncode == 3:
            return False
        return None
    except Exception:
        return None


def py_version(exe: str) -> str:
    try:
        r = subprocess.run([exe, "-c", "import sys;print(sys.version.split()[0])"],
                           capture_output=True, text=True, timeout=60)
        return r.stdout.strip() or "?"
    except Exception:
        return "?"


def port_open(port: int = 8765, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except Exception:
        return False


def tasklist(image: str) -> bool:
    try:
        r = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image}"],
                           capture_output=True, text=True, timeout=30)
        return image.lower() in r.stdout.lower()
    except Exception:
        return False


def main() -> int:
    print("=" * 78)
    print("ADS 自动化环境自检  |  工程根目录:", PROJECT_ROOT)
    print("=" * 78)

    # 1) ADS 安装
    ads = find_first(ADS_CANDIDATES, "dir")
    if ads:
        rec("PASS", "ADS 安装目录", ads)
        rec("PASS" if os.path.isfile(os.path.join(ads, "bin", "ads.exe")) else "FAIL",
            "ads.exe", os.path.join(ads, "bin", "ads.exe"))
        rec("PASS" if os.path.isfile(os.path.join(ads, "bin", "hpeesofsim.exe")) else "FAIL",
            "hpeesofsim.exe", os.path.join(ads, "bin", "hpeesofsim.exe"))
        rec("PASS" if os.path.isfile(os.path.join(ads, "bin", "adsMomWrapper.bat")) else "WARN",
            "adsMomWrapper.bat", os.path.join(ads, "bin", "adsMomWrapper.bat"))
        ads_py = os.path.join(ads, "tools", "python", "python.exe")
        rec("PASS" if os.path.isfile(ads_py) else "FAIL", "ADS 自带 Python",
            f"{ads_py}  ({py_version(ads_py)})")
    else:
        ads_py = None
        rec("FAIL", "ADS 安装目录", "未找到；请设置 HPEESOF_DIR")
    if os.environ.get("HPEESOF_DIR"):
        rec("PASS", "环境变量 HPEESOF_DIR", os.environ["HPEESOF_DIR"])
    else:
        rec("WARN", "环境变量 HPEESOF_DIR",
            "当前会话未设置（读 .sio / MATLAB 桥 / headers 需要）")

    # 2) 两套 Python
    sys_py = find_first(SYS_PY_CANDIDATES, "file")
    if sys_py:
        rec("PASS", "系统 Python", f"{sys_py}  ({py_version(sys_py)})")
        missing = [m for m in SYS_PACKAGES if has_module(sys_py, m) is False]
        rec("PASS" if not missing else "WARN", "系统 Python 包",
            "全部就绪" if not missing else "缺少: " + ", ".join(missing))
    else:
        rec("WARN", "系统 Python", "未找到 (${BRIDGE_PY})")
    if ads_py and os.path.isfile(ads_py):
        missing = [m for m in ADS_PACKAGES if has_module(ads_py, m) is False]
        rec("PASS" if not missing else "WARN", "ADS Python 包",
            "全部就绪" if not missing else "缺少: " + ", ".join(missing))

    # 3) 运行态：进程 / 桥
    ads_running = tasklist("ads.exe")
    rec("PASS" if ads_running else "WARN", "ADS 进程 ads.exe",
        "运行中" if ads_running else "未运行（需要 GUI 时先启动 ADS）")
    bridge = port_open()
    rec("PASS" if bridge else "WARN", "XMLRPC 桥 127.0.0.1:8765",
        "可连接" if bridge else "未监听（在 ADS Python Console 里 start_server() 后才有）")
    if ads_running and not bridge:
        rec("WARN", "桥未启动", "在 ADS Tools→Python Console 中执行 "
            "exec(open(r'%s\\ads_tools\\ads_live_server.py',encoding='utf-8').read()); start_server()"
            % PROJECT_ROOT)

    # 4) 工作区
    if os.path.isdir(WORK_ROOT):
        workspaces = sorted(d for d in os.listdir(WORK_ROOT)
                            if os.path.isdir(os.path.join(WORK_ROOT, d)))
        rec("PASS", "工作区目录 (%d)" % len(workspaces), ", ".join(workspaces) or "(空)")
        locks = []
        for w in workspaces:
            lk = os.path.join(WORK_ROOT, w, ".cdslck")
            if os.path.exists(lk):
                locks.append(w)
        rec("WARN" if locks else "PASS", "工作区写锁 .cdslck",
            ("被占用: " + ", ".join(locks)) if locks else "无残留锁")
    else:
        rec("WARN", "工作区目录", WORK_ROOT + " 不存在")

    # 5) MATLAB（可选）
    mat = find_first(MATLAB_CANDIDATES, "file")
    rec("PASS" if mat else "WARN", "MATLAB", mat or "未找到（原理图级优化需要）")

    fails = [r for r in RESULTS if r[0] == "FAIL"]
    warns = [r for r in RESULTS if r[0] == "WARN"]
    print("-" * 78)
    print(f"汇总: {len(RESULTS) - len(fails) - len(warns)} OK / {len(warns)} WARN / {len(fails)} FAIL")
    if ARGS.json:
        print(json.dumps({"results": RESULTS,
                          "ok": len(RESULTS) - len(fails) - len(warns),
                          "warn": len(warns), "fail": len(fails)},
                         ensure_ascii=False, indent=1))
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ARGS = ap.parse_args()
    sys.exit(main())
