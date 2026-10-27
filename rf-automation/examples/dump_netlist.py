# -*- coding: utf-8 -*-
"""Example: dump an ADS cell's netlist through the live bridge.

Run with the BRIDGE python (see docs/01):
    python pb.py examples/dump_netlist.py
Requires an ADS GUI with the live server running (ads_tools/ads_live_server.py).
"""
import os, sys
from keysight.ads.de import db_uu as db
from keysight.ads.de.db_uu import DesignMode

LIB  = os.environ.get("LIB", "ADS_Auto_lib")
CELL = os.environ.get("CELL", "PA1")
VIEW = os.environ.get("VIEW", "schematic")
OUT  = os.environ.get("OUT", os.path.join(os.environ.get("WORKSPACE", "."), "sim", "usr"))

nl = db.Design(LIB, CELL, VIEW, DesignMode.READ_ONLY).generate_netlist()
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, "%s.net" % CELL)
open(path, "w", encoding="utf-8").write(nl)
print("wrote %s (%d lines)" % (path, len(nl.splitlines())))
