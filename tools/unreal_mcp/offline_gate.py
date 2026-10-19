"""Run selected pure MCP unit tests with real sockets and Unreal imports blocked."""
import argparse
import importlib.abc
import io
import json
import re
import socket
import ssl
import sys
import time
import unittest
import urllib.request  # Load SSL classes before replacing socket constructors.
from pathlib import Path


class _NoUnreal(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "unreal" or fullname.startswith("unreal."):
            raise RuntimeError("offline gate forbids Unreal imports")
        return None


def _blocked(*args, **kwargs):
    raise RuntimeError("offline gate forbids real sockets")


def _peak_working_set():
    if sys.platform != "win32":
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform == "darwin" else value * 1024)
    import ctypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ("peak", "working", "ppq", "pq", "pnq", "nq", "page", "peak_page")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    if not query(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return None
    return int(counters.peak)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("tests", nargs="+")
    args = parser.parse_args(argv)
    if any(re.fullmatch(r"tools\.unreal_mcp\.test_[a-z0-9_]+", name) is None for name in args.tests):
        parser.error("only named tools.unreal_mcp.test_* modules are supported")
    if args.report.exists():
        parser.error("report already exists; preserve the prior run")
    sys.meta_path.insert(0, _NoUnreal())
    socket.socket = _blocked
    socket.create_connection = _blocked
    socket.socketpair = _blocked
    ssl.SSLSocket.connect = _blocked
    ssl.SSLSocket.connect_ex = _blocked
    started = time.perf_counter()
    output = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromNames(args.tests)
    result = unittest.TextTestRunner(stream=output, verbosity=1).run(suite)
    report = {"schema": "codex.offline-mcp-unit-gate.v1", "modules": args.tests,
              "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "elapsed_seconds": time.perf_counter() - started,
              "peak_working_set_bytes": _peak_working_set(), "socket_boundary": "blocked",
              "unreal_import_boundary": "blocked", "native_requests": 0,
              "success": result.wasSuccessful() and result.testsRun > 0 and not result.skipped,
              "output": output.getvalue()}
    with args.report.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
    print(json.dumps({key: value for key, value in report.items() if key != "output"}))
    if not report["success"]:
        print(output.getvalue())
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
