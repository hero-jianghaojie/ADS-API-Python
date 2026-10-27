#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Central configuration for ads-rf-automation.

ALL machine-specific paths come from environment variables so the repo runs on any
machine. Copy env.example -> env.local (gitignored) or export these directly.

    ADS_HOME   ADS installation root              (default: see below)
    ADS_PY     Python shipped with ADS           (<ADS_HOME>/tools/python/python.exe)
    BRIDGE_PY  Python that can drive the ADS GUI (used with pb.py)
    WORKSPACE  ADS workspace directory           (contains <lib>/ and data/)
    LIB        default library name              (default: ADS_Auto_lib)
    HOME_DIR   used for matplotlib HOME/USERPROFILE
    MPLDIR     matplotlib config dir (must be writable)
"""
import os

ADS_HOME  = os.environ.get("ADS_HOME",  r"<ADS_HOME>")
ADS_PY    = os.environ.get("ADS_PY",    os.path.join(ADS_HOME, "tools", "python", "python.exe"))
BRIDGE_PY = os.environ.get("BRIDGE_PY", r"<BRIDGE_PY>")
WORKSPACE = os.environ.get("WORKSPACE", os.path.join(os.path.expanduser("~"), "ads_work"))
LIB       = os.environ.get("LIB",       "ADS_Auto_lib")
HOME_DIR  = os.environ.get("HOME",      os.path.expanduser("~"))
MPLDIR    = os.environ.get("MPLCONFIGDIR", os.path.join(os.path.expanduser("~"), ".mplcfg"))
BRIDGE_HOST = os.environ.get("BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", "8765"))

HPEESOFSIM = os.path.join(ADS_HOME, "bin", "hpeesofsim.exe")
MOM_WRAPPER = os.path.join(ADS_HOME, "bin", "adsMomWrapper.bat")
SIM_USR = os.path.join(WORKSPACE, "sim", "usr")
DATA_DIR = os.path.join(WORKSPACE, "data")

def child_env(extra=None):
    """Env for any child process that imports matplotlib (avoids
    'Could not determine home directory')."""
    e = dict(os.environ)
    e.setdefault("HOME", HOME_DIR)
    e.setdefault("USERPROFILE", HOME_DIR)
    e.setdefault("MPLCONFIGDIR", MPLDIR)
    if extra:
        e.update(extra)
    return e

if __name__ == "__main__":
    for k in ("ADS_HOME","ADS_PY","BRIDGE_PY","WORKSPACE","LIB","HPEESOFSIM","MOM_WRAPPER"):
        print("%-12s %s" % (k, globals()[k]))
