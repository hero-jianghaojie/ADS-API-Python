# -*- coding: utf-8 -*-
"""ADS 仿真助手：MATLAB 通过 py. 桥接调用。

职责：
  - 搭建 hpeesofsim 所需的完整 ADS 环境（组件子目录 DLL 依赖）
  - 写网表文件、运行 hpeesofsim、返回新生成的 .ds 路径

用法（在 MATLAB 中，先 ads_init() 建桥）：
    py.sys.path.insert(int64(0), 'd:\\AppGallery\\codex\\Matlab_ADS');
    r = py.ads_sim_helper.run_hpeesofsim(nl, wrk, design_name);
    if py.getattr(r, 'ok') ... end
"""
import os
import subprocess

ADS = r"D:\Program Files\Keysight\ADS2025_Update2"


def _ads_env():
    """构造 hpeesofsim 可运行的环境（必须包含全部组件子目录 DLL）。"""
    env = dict(os.environ)
    env["HPEESOF_DIR"] = ADS
    env["SIMARCH"] = "win32_64"
    env["COMPL_DIR"] = ADS
    env["QT_PLUGIN_PATH"] = os.path.join(ADS, "bin", "plugins", "qt")
    extra = []
    for root, dirs, files in os.walk(ADS):
        d = os.path.basename(root)
        if d == "win32_64" and "\\bin\\" in root + "\\":
            extra.append(root)
        elif d == "bin" and root != os.path.join(ADS, "bin"):
            extra.append(root)
    extra += [os.path.join(ADS, "bin"),
              os.path.join(ADS, "bin", "win32_64"),
              os.path.join(ADS, "lib", "win32_64"),
              os.path.join(ADS, "circuit", "lib.win32_64"),
              os.path.join(ADS, "adsptolemy", "lib.win32_64")]
    env["PATH"] = ";".join(extra + [env.get("PATH", "")])
    return env


def run_hpeesofsim(netlist_text, wrk, design_name, timeout=600):
    """写网表并运行 hpeesofsim。

    Args:
        netlist_text: 网表字符串（de 的 generate_netlist() 返回）
        wrk: ADS 工作区目录
        design_name: 设计名（如 'py_ms_lpf'），用于网表文件名与 .ds 定位
        timeout: 仿真超时秒数

    Returns:
        dict: {ok, ds_path, rc, stdout_tail, stderr}
    """
    os.makedirs(os.path.join(wrk, "networks"), exist_ok=True)
    netfile = os.path.join(wrk, "networks", design_name + ".net")
    with open(netfile, "w") as f:
        f.write(netlist_text)

    exe = os.path.join(ADS, "bin", "hpeesofsim.exe")
    try:
        r = subprocess.run([exe, netfile], cwd=wrk, env=_ads_env(),
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "ds_path": None, "rc": -99,
                "stdout_tail": "TIMEOUT", "stderr": ""}

    # 定位新 .ds（cwd 下 <design>.ds 或 data/<design>.ds）
    cand = [os.path.join(wrk, design_name + ".ds"),
            os.path.join(wrk, "data", design_name + ".ds")]
    ds_path = next((p for p in cand if os.path.exists(p)), None)

    return {
        "ok": r.returncode == 0 and ds_path is not None,
        "ds_path": ds_path,
        "rc": r.returncode,
        "stdout_tail": r.stdout[-800:],
        "stderr": r.stderr[-400:],
    }


def set_var_eqn(design, var_name, names, values):
    """更新设计里的 Var Eqn 复合参数（如 VAR1）的若干变量值。

    Args:
        design: de 打开的 Design 对象
        var_name: Var Eqn 实例名，如 'VAR1'
        names: 要更新的变量名列表，如 ['W1','S1','L1']
        values: 对应的字符串/数值列表（会转成 str 写回）

    Returns:
        bool: True 成功

    说明：只改指定变量，其它项（含表达式如 L4='L1+L2+W2'）原样保留。
    """
    inst = design.find_instance(var_name)
    pp = inst.parameters["Variable Value"]
    cur = [[str(n), str(v)] for n, v in pp.value]
    d = dict(cur)
    for n, v in zip(names, values):
        d[str(n)] = str(v)
    new_val = [[n, d[n]] for n, _ in cur]
    pp.value = new_val
    inst.update_item_annotation()
    return True
