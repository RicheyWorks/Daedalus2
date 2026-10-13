"""Compile policy checks and prove key regressions are detected; no Unreal required.

Run in an MSVC developer shell with --compiler cl, or use g++/clang++.
All build and mutation files live in a temporary directory.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', default='g++')
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    compiler = shutil.which(args.compiler)
    if not compiler:
        parser.error('compiler not found; MSVC requires its developer shell')
    msvc = Path(compiler).stem.lower() == 'cl'
    if msvc and args.sanitize:
        parser.error('sanitizer option is for GCC/Clang')
    here = Path(__file__).resolve().parent
    source = (here / 'dungeon_core_test.cpp').read_text()
    header = (here.parent / 'DaedalusLink/Source/DaedalusLink/Public/DaedalusDungeonCore.h').read_text()
    source = source.replace('../DaedalusLink/Source/DaedalusLink/Public/DaedalusDungeonCore.h', 'DaedalusDungeonCore.h')
    mutants = [
        ('uncertain replay', '!Uncertain && !Pending', '!Pending', 'uncertain action not retried'),
        ('stale acceptance', 'if(!Pending || Id!=Pending) return false;', 'if(!Pending) return false;', 'stale response refused'),
        ('read unlocks mutation', 'Last=Value;HasLast=true;', 'Uncertain=false;Last=Value;HasLast=true;', 'read cannot clear uncertain mutation'),
    ]
    with tempfile.TemporaryDirectory(prefix='daedalus-dungeon-') as tmp:
        root = Path(tmp)
        (root / 'test.cpp').write_text(source)
        for name, content, expected in [('baseline', header, None)] + [
            (name, header.replace(old, new), expected) for name, old, new, expected in mutants
        ]:
            (root / 'DaedalusDungeonCore.h').write_text(content)
            exe = root / ('test.exe' if msvc else 'test')
            if msvc:
                command = [compiler, '/nologo', '/std:c++17', '/EHsc', '/W4', '/WX', '/O2', 'test.cpp', '/Fe:'+str(exe)]
            else:
                command = [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-O1', 'test.cpp', '-o', str(exe)]
                if args.sanitize:
                    command += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
            subprocess.run(command, cwd=root, check=True, timeout=120)
            result = subprocess.run([str(exe)], cwd=root, text=True, capture_output=True, timeout=30)
            if expected is None:
                if result.returncode != 0:
                    raise RuntimeError(result.stdout + result.stderr)
                print(result.stdout.strip(), flush=True)
            elif result.returncode == 0 or ('FAIL '+expected) not in result.stderr:
                raise RuntimeError(f'{name}: expected assertion not detected: {result.stdout} {result.stderr}')
            else:
                print('Detected regression: '+name, flush=True)
    print('Baseline and 3 mutation checks passed', flush=True)

if __name__ == '__main__':
    main()
