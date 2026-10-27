# -*- coding: utf-8 -*-
"""
ADS Live Server — 在 ADS 的 Python 控制台里运行。

作用：
    在 ADS 会话内启动一个 XML RPC 服务器。外部 Python（VS Code 终端）
    通过它调用本服务器的函数，让版图构建在 ADS 主线程中执行，
    从而 GUI 实时刷新 —— 实现"我在终端改，你在 ADS 里实时看"。

在 ADS 中的启动步骤：
    1. 打开 python_wrk workspace
    2. Tools -> Python Console（快捷键 Ctrl+Shift+P）
    3. 在控制台依次输入：
         exec(open(r'${EXTERNAL_DIR}', encoding='utf-8').read())
         start_server()
    4. 看到 "ADS Live Server listening on 127.0.0.1:8765" 即成功。
"""
import socketserver
import threading
from xmlrpc.server import SimpleXMLRPCServer

import _pde_app
from keysight.ads import ael
from keysight.ads import de
from keysight.ads.de import db_uu

PORT = 8765
LIB_NAME = "python_lib"

_layout = None      # 当前操作的 layout
_cell_name = "BT"   # 当前操作的 cell


def _run_main(fn):
    """在 ADS 主线程中执行，保证 GUI 实时刷新。"""
    return _pde_app.ui.execute_in_main_thread(fn)


def _view_all():
    try:
        ael.call.de_view_all()
    except Exception:
        pass


# ------------------------------------------------------------------
# 暴露给外部客户端的操作（均可由 XML RPC 调用）
# ------------------------------------------------------------------
def ping() -> str:
    return "OK"


def open_layout(cell_name: str = "BT") -> str:
    """打开（不存在则创建）指定 cell 的 layout 视图。"""

    def f():
        global _layout, _cell_name
        _cell_name = cell_name
        _layout = db_uu.create_layout(f"{LIB_NAME}:{cell_name}:layout")
        _view_all()
        return _layout.design_name

    return _run_main(f)


def clear_layout() -> str:
    """清空当前 layout。"""

    def f():
        _layout.clear_design()
        _view_all()
        return "cleared"

    return _run_main(f)


def add_polygon(points) -> str:
    """添加一个多边形（CONDUCTOR 层）。points = [[x,y], ...]"""

    def f():
        pts = [tuple(p) for p in points]
        _layout.add_polygon(db_uu.LayerId(1), pts)
        _view_all()
        return f"polygon added ({len(pts)} pts)"

    return _run_main(f)


def add_port(name: str, x: float, y: float) -> str:
    """在 (x, y) 处添加端口，端口连接标记放在 CONDUCTOR 层。"""

    def f():
        # 在 CONDUCTOR 层上添加一个端口点（pin），并关联网络/端子
        cond = db_uu.LayerId(1)
        dot = _layout.add_dot(cond, (x, y))
        dot.width = 0.3   # 端口标记尺寸 (mm)
        dot.height = 0.3
        net = _layout.find_or_add_net(name)
        term = _layout.add_term(net, name)
        _layout.add_pin(term, dot)
        _view_all()
        return f"port {name} added at ({x}, {y}) on CONDUCTOR"

    return _run_main(f)


def save_layout() -> str:
    """保存当前 layout。"""

    def f():
        _layout.save_design()
        return "saved"

    return _run_main(f)


def view_all() -> str:
    """缩放至全部图形。"""

    def f():
        _view_all()
        return "view_all"

    return _run_main(f)


def show_all_layers() -> str:
    """让 Layers 窗口中所有图层可见（解决 CONDUCTOR 层未显示、版图灰色的问题）。"""

    def f():
        from keysight.ads import ael

        ael.call.de_layer_prefs_all_visible(ael.call.de_get_current_design_context())
        try:
            ael.call.de_refresh_layers()
        except Exception:
            pass
        return "all layers visible"

    return _run_main(f)


def show_layer(layer_name: str) -> str:
    """在 Layers 窗口中仅显示指定图层（如 "CONDUCTOR"）。"""

    def f():
        from keysight.ads import ael

        ael.call.de_layer_prefs_all_not_visible(ael.call.de_get_current_design_context())
        try:
            ael.call.de_layer_display(layer_name, 1)
        except Exception:
            # 某些版本命令不同，回退为全部可见
            ael.call.de_layer_prefs_all_visible(ael.call.de_get_current_design_context())
        try:
            ael.call.de_refresh_layers()
        except Exception:
            pass
        return f"layer {layer_name} shown"

    return _run_main(f)


def get_emsetup_info() -> str:
    """查询当前 layout 的 EM Setup 视图名和关联衬底。"""

    def f():
        try:
            from keysight.ads import emtools

            ems = emtools.find_emsetup_view_name((LIB_NAME, _cell_name, "layout"))
            sub = emtools.get_substrate_info((LIB_NAME, _cell_name, ems))
            return f"emsetup={ems}, substrate={sub}"
        except Exception as e:
            return f"error: {e}"

    return _run_main(f)


def run_em() -> str:
    """运行当前 emSetup 配置的 EM 仿真（同步，阻塞直到完成）。
    运行时会弹出 ADS 仿真进度窗口，可在 GUI 里实时查看。"""

    def f():
        from keysight.ads import ael

        ael.call.deem_run_em_setup(ael.call.de_get_current_design_context(), "emSetup")
        return "em simulation finished"

    return _run_main(f)


# ------------------------------------------------------------------
# 服务器生命周期
# ------------------------------------------------------------------
class _ThreadedXMLRPCServer(socketserver.ThreadingMixIn, SimpleXMLRPCServer):
    allow_reuse_address = True


_server = None


def run_python(code: str) -> str:
    """在 ADS 主线程执行一段 Python 代码，同步等待并返回输出/异常。

    说明：`execute_in_main_thread` 是异步提交（立即返回），所以这里用
    `threading.Event` 阻塞等待主线程执行完 worker 后再返回结果。
    """
    ev = threading.Event()
    result = {"value": None}

    def worker():
        import io, contextlib, traceback
        buf = io.StringIO()
        try:
            # stdout AND stderr: a posted script that calls traceback.print_exc()
            # writes to stderr, and without this the traceback is silently lost.
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                exec(code, globals())
            result["value"] = "OK\n" + buf.getvalue()
        except BaseException:
            # BaseException, not Exception: a SystemExit/KeyboardInterrupt raised by
            # the posted script used to escape the worker, leaving result as None and
            # making the bridge report "<no result>" instead of the real error.
            result["value"] = "ERROR\n" + traceback.format_exc() + buf.getvalue()
        finally:
            ev.set()

    _run_main(worker)          # 异步提交到 ADS 主线程
    ev.wait(timeout=60)        # 同步等待执行完成
    return result["value"]


def start_server() -> str:
    """在 ADS 中启动 XML RPC 服务器（线程方式，不阻塞控制台）。"""
    global _server
    if _server is not None:
        return "server already running"
    _server = _ThreadedXMLRPCServer(("127.0.0.1", PORT), logRequests=False, allow_none=True)
    for name in [
        "ping", "open_layout", "clear_layout", "add_polygon",
        "add_port", "save_layout", "view_all",
        "show_all_layers", "show_layer",
        "get_emsetup_info", "run_em", "run_python",
    ]:
        _server.register_function(globals()[name], name)
    t = threading.Thread(target=_server.serve_forever, daemon=True)
    t.start()
    return f"ADS Live Server listening on 127.0.0.1:{PORT}"


def stop_server() -> str:
    """停止 XML RPC 服务器。"""
    global _server
    if _server is not None:
        _server.shutdown()
        _server.server_close()
        _server = None
        return "server stopped"
    return "server not running"


if __name__ == "__main__":
    print("请在 ADS Python 控制台中运行 start_server() 启动 ADS Live Server。")
