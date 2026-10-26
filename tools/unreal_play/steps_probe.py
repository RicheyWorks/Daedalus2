# SPDX-License-Identifier: MIT
"""Probe daedalus.steps: three trivial steps; prints the raw reply shape so the host tooling matches it."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "connectors", "claude-asset-pipeline"))
from asset_pipeline import wire  # noqa: E402

code = "def steps():\n    yield 'a'\n    yield 'b'\n    return {'x': 1}\n"
r = wire.call(wire.UNREAL, "daedalus.steps", code=code, label="probe", timeout=30)
print(type(r).__name__, repr(r)[:600])
