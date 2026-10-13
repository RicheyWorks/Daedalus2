"""Run Java/C++ full-domain grid parity in an isolated temporary build directory."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--compiler',default='g++')
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args()
    compiler=shutil.which(args.compiler)
    javac=shutil.which('javac');java=shutil.which('java')
    if not all((compiler,javac,java)):parser.error('compiler and Java 21 must be on PATH')
    msvc=Path(compiler).stem.lower()=='cl'
    if msvc and args.sanitize:parser.error('use GCC/Clang for sanitizer checks')
    here=Path(__file__).resolve().parent
    repo=here.parents[2]
    with tempfile.TemporaryDirectory(prefix='daedalus-grid-') as tmp:
        work=Path(tmp);exe=work/('grid.exe' if msvc else 'grid')
        src=here/'land_grid_test.cpp'
        if msvc:
            command=[compiler,'/nologo','/std:c++17','/EHsc','/W4','/WX',str(src),'/Fe:'+str(exe)]
        else:
            command=[compiler,'-std=c++17','-Wall','-Wextra','-Werror','-O1',str(src),'-o',str(exe)]
            if args.sanitize:command+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        subprocess.run(command,cwd=work,check=True,timeout=120)
        with (work/'native.csv').open('w') as output:
            subprocess.run([str(exe)],stdout=output,check=True,timeout=60)
        subprocess.run([javac,'--release','21','-d',str(work),str(repo/'daedalus-core/src/main/java/com/daedalus/world/RealmLandGrid.java'),str(here/'LandGridParity.java')],check=True,timeout=60)
        subprocess.run([java,'-cp',str(work),'LandGridParity',str(work/'native.csv')],check=True,timeout=60)
        # Deliberately corrupt one native district row: prove mismatched output is refused.
        rows=(work/'native.csv').read_text().splitlines();parts=rows[4999].split(',');parts[3]='999';rows[4999]=','.join(parts)
        (work/'corrupt.csv').write_text('\n'.join(rows)+'\n')
        rejected=subprocess.run([java,'-cp',str(work),'LandGridParity',str(work/'corrupt.csv')],capture_output=True,text=True,timeout=60)
        if rejected.returncode==0 or 'AssertionError' not in rejected.stderr:
            raise RuntimeError('parity verifier did not reject the corrupted district')
        print('PASS: verifier rejects native district drift')

if __name__=='__main__':main()
