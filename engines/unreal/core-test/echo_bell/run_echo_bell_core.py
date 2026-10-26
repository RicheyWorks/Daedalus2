#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile and run the Echo Bell C++ core against the Java-generated fixture.
usage: python engines/unreal/core-test/echo_bell/run_echo_bell_core.py [--compiler g++|clang++|cl.exe] [--sanitize]"""
import argparse, os, subprocess, sys, tempfile
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
fixture = os.path.join(root, "docs", "contracts", "echo-bell-v1", "peals.ebg")
ap = argparse.ArgumentParser(); ap.add_argument("--compiler", default="g++"); ap.add_argument("--sanitize", action="store_true")
a = ap.parse_args()
with tempfile.TemporaryDirectory() as t:
    exe = os.path.join(t, "echo_bell_test" + (".exe" if os.name == "nt" else ""))
    src = os.path.join(here, "echo_bell_test.cpp")
    if os.path.basename(a.compiler).lower().startswith("cl"):
        cmd = [a.compiler, "/nologo", "/std:c++17", "/W4", "/WX", "/EHsc", src, "/Fe" + exe, "/Fo" + t + os.sep]
    else:
        cmd = [a.compiler, "-std=c++17", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-Wconversion", "-Wshadow", src, "-o", exe]
        if a.sanitize: cmd += ["-fsanitize=address,undefined", "-fno-sanitize-recover=all", "-g"]
    subprocess.run(cmd, check=True)
    sys.exit(subprocess.run([exe, fixture]).returncode)
