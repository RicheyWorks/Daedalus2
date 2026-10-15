#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the portable AUD1 checks; optionally verify fixtures against the unchanged Java renderer."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def compiler_environment(compiler, environment):
    if Path(compiler).name.lower() not in ("cl", "cl.exe"):
        return environment
    compiler_path = Path(compiler).resolve()
    vc = next((parent for parent in compiler_path.parents if parent.name == "VC"), None)
    if not vc:
        return environment  # An existing Developer Command Prompt may already supply INCLUDE/LIB.
    script = vc / "Auxiliary" / "Build" / "vcvars64.bat"
    if not script.is_file():
        return environment
    # vcvars is a batch file; use cmd for this read-only environment capture, with a verified VS path.
    command = 'call "{}" >nul && set'.format(script)
    output = subprocess.check_output(command, shell=True, executable=os.environ.get("COMSPEC", "cmd.exe"), text=True)
    configured = dict(environment)
    for line in output.splitlines():
        if "=" in line and not line.startswith("="):
            key, value = line.split("=", 1)
            configured[key] = value
    return configured


def find_compiler(requested):
    if requested:
        found = shutil.which(requested)
        if found:
            return found
        raise RuntimeError("requested C++ compiler not found: " + requested)
    for candidate in (os.environ.get("CXX", ""), "clang++", "g++", "cl"):
        if candidate and shutil.which(candidate):
            return shutil.which(candidate)
    if os.name == "nt":
        base = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft Visual Studio"
        candidates = sorted(base.glob("*/*/VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe"))
        if candidates:
            return str(candidates[-1])
    raise RuntimeError("C++17 compiler not found; pass --compiler or run in a compiler developer shell")


def verify_java(repo, fixtures, build):
    javac, java = shutil.which("javac"), shutil.which("java")
    if not javac or not java:
        raise RuntimeError("--verify-java needs existing javac/java")
    classes, generated = build / "java-classes", build / "java-fixtures"
    classes.mkdir()
    audio = repo / "daedalus-core/src/main/java/com/daedalus/world/audio"
    sources = [audio / (name + ".java") for name in ("Genome", "Species", "CallSpec", "Rng", "CallSynth")]
    sources.append(Path(__file__).with_name("GenerateJavaParity.java"))
    subprocess.run([javac, "-d", str(classes)] + [str(source) for source in sources], check=True)
    subprocess.run([java, "-cp", str(classes), "GenerateJavaParity", str(generated)], check=True)
    expected = sorted(path.name for path in fixtures.glob("*.pcm")) + sorted(path.name for path in fixtures.glob("*.txt"))
    if sorted(expected) != sorted(path.name for path in generated.iterdir()):
        raise RuntimeError("Java-generated fixture roster differs")
    for name in expected:
        if (fixtures / name).read_bytes() != (generated / name).read_bytes():
            raise RuntimeError("committed fixture differs from existing Java source: " + name)
    print("All PCM/seed/RNG metadata fixtures reproduce byte-for-byte from existing Java sources.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler")
    parser.add_argument("--sanitize", action="store_true", help="GNU/Clang ASan+UBSan (not MSVC)")
    parser.add_argument("--verify-java", action="store_true", help="regenerate into TEMP and compare; never overwrite repo fixtures")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[4]
    fixtures = Path(__file__).with_name("fixtures").resolve()
    contract = repo / "docs/contracts/aud-v1/forest-canid.aud"
    if contract.is_file() and contract.read_bytes() != (fixtures / "forest-canid.aud").read_bytes():
        raise RuntimeError("native AUD fixture differs from current Java contract fixture")
    compiler = find_compiler(args.compiler)
    environment = compiler_environment(compiler, os.environ)
    with tempfile.TemporaryDirectory(prefix="codex-aud1-native-") as directory:
        build = Path(directory)
        build.resolve().relative_to(Path(tempfile.gettempdir()).resolve())
        if args.verify_java:
            verify_java(repo, fixtures, build)
        executable = build / ("audio_core_test.exe" if os.name == "nt" else "audio_core_test")
        source = Path(__file__).with_name("audio_core_test.cpp").resolve()
        include = repo / "engines/unreal/DaedalusLink/Source/DaedalusLink/Public"
        if Path(compiler).name.lower() in ("cl", "cl.exe"):
            if args.sanitize:
                raise RuntimeError("--sanitize uses GNU/Clang ASan+UBSan; select that compiler")
            command = [compiler, "/nologo", "/std:c++17", "/EHsc", "/permissive-", "/W4", "/WX", "/O2", "/I" + str(include), str(source), "/Fe:" + str(executable), "/Fo:" + str(build / "audio_core_test.obj")]
        else:
            command = [compiler, "-std=c++17", "-O1", "-g", "-Wall", "-Wextra", "-Werror", "-I", str(include), str(source), "-o", str(executable)]
            if args.sanitize:
                command.extend(["-fsanitize=address,undefined", "-fno-omit-frame-pointer"])
        print("Building audio core with " + compiler, flush=True)
        subprocess.run(command, cwd=repo, env=environment, check=True)
        subprocess.run([str(executable), str(fixtures)], cwd=repo, env=environment, check=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        sys.exit(1)
