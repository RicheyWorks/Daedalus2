"""Exercise real separate-JVM restarts and the OS directory writer lock."""
import argparse
import json
import queue
import subprocess
import threading
import time
from pathlib import Path


def check(java, classpath, probe, directory):
    directory = directory.resolve()
    if directory.exists():
        raise ValueError('Probe directory must be fresh; existing stores are never reset')
    command = [str(java), '--class-path', str(classpath), str(probe)]
    start = time.monotonic()

    def run(mode, marker):
        result = subprocess.run(command + [mode, str(directory)], capture_output=True,
                                text=True, timeout=30, check=True)
        if marker not in result.stdout:
            raise RuntimeError(f'Missing {marker}: {result.stdout} {result.stderr}')

    run('write', 'OCEAN_PROCESS_WRITE_PASS')
    run('read', 'OCEAN_PROCESS_RESTART_PASS')
    holder = subprocess.Popen(command + ['hold', str(directory)], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    ready = queue.Queue()
    threading.Thread(target=lambda: ready.put(holder.stdout.readline()), daemon=True).start()
    try:
        line = ready.get(timeout=20)
        if 'OCEAN_LOCK_READY' not in line:
            raise RuntimeError(f'Lock holder failed: {line}')
        run('locked', 'OCEAN_OS_LOCK_REFUSED')
        holder.communicate('\n', timeout=10)
        if holder.returncode != 0:
            raise RuntimeError('Lock holder failed on release')
    finally:
        if holder.poll() is None:
            holder.kill()
            holder.communicate(timeout=10)
    run('read', 'OCEAN_PROCESS_RESTART_PASS')
    return {'separate_jvm_edit_and_empty_restart': True, 'os_writer_lock_refused': True,
            'lock_release_reopen': True, 'owned_holder_stopped': holder.poll() is not None,
            'elapsed_seconds': round(time.monotonic() - start, 3),
            'scope': 'Java source launch, edit/save, process restart, writer exclusion and reopen',
            'store_bytes': sum(p.stat().st_size for p in directory.iterdir() if p.is_file()),
            'realm_registration_verified': False, 'unreal_play_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--java', required=True, type=Path)
    parser.add_argument('--classpath', required=True, type=Path)
    parser.add_argument('--probe', required=True, type=Path)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Proof output must be fresh')
    result = check(args.java, args.classpath.resolve(), args.probe.resolve(), args.directory)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
