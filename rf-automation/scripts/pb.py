# -*- coding: utf-8 -*-
"""pb.py -- post a Python file to the ADS live bridge and print the result.

Usage:  python pb.py <file.py> [--tail N]

The file runs inside the ADS process (main thread), so it can use keysight.ads.de
and _pde_app.  Everything it prints comes back here.  This exists because stuffing
multi-line code through python -c on PowerShell mangles the quotes.
"""
import sys
import xmlrpc.client

PORT = 8765


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    tail = 0
    if "--tail" in sys.argv:
        tail = int(sys.argv[sys.argv.index("--tail") + 1])
    code = open(path, encoding="utf-8").read()
    srv = xmlrpc.client.ServerProxy("http://127.0.0.1:%d" % PORT, allow_none=True)
    out = srv.run_python(code)
    if out is None:
        print("<no result>")
        return 1
    if tail:
        lines = out.splitlines()
        out = "\n".join(lines[-tail:])
    print(out)
    return 0 if out.startswith("OK") else 1


if __name__ == "__main__":
    sys.exit(main())
