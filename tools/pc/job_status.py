# SPDX-License-Identifier: MIT
"""Read one PC job's recorded state and bounded log tail, without waiting.

    python tools/pc/job_status.py --id job-1014-024500 --lines 40

The job's existing .exit, .started and .log files are evidence, not a process
probe. A recorded exit code does not establish that the producer recorded it
correctly, or that the job's acceptance checks passed. This observer neither
starts a job nor retries one whose outcome is uncertain.
"""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import stat

MAX_LINES = 200
MAX_TAIL_BYTES = 128 * 1024
MAX_MARKER_BYTES = 256
_JOB_ID = re.compile(r"job-[A-Za-z0-9][A-Za-z0-9_-]{0,119}", re.ASCII)
_EXIT = re.compile(r"done (-?[0-9]+)", re.ASCII | re.IGNORECASE)
_STARTED = re.compile(r"pid=([0-9]+)", re.ASCII | re.IGNORECASE)


@contextmanager
def _open_regular(path):
    # Nonblocking open also lets a POSIX FIFO be rejected without waiting for a
    # writer. fstat checks the opened file, avoiding a stat/open replacement race.
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("artifact is not a regular file")
        with os.fdopen(fd, "rb", buffering=0, closefd=False) as source:
            yield source
    finally:
        os.close(fd)


def _marker(path):
    """Read at most one small marker; distinguish absence from unreadability."""
    try:
        with _open_regular(path) as source:
            data = source.read(MAX_MARKER_BYTES + 1)
    except FileNotFoundError:
        return None
    if len(data) > MAX_MARKER_BYTES:
        raise ValueError("marker exceeds %d bytes" % MAX_MARKER_BYTES)
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    text = data.decode(encoding)
    # The legacy producer writes .exit directly. A digit prefix such as 'done 2'
    # must not become completed before the producer finishes 'done 23\r\n'.
    if not text.endswith("\n"):
        raise ValueError("marker is not line-terminated; publication may be incomplete")
    return text.strip()


def _tail(path, lines):
    """Capture a bounded suffix; never emit a fragment of its first line."""
    try:
        with _open_regular(path) as source:
            source.seek(0, os.SEEK_END)
            size = source.tell()
            start = max(0, size - MAX_TAIL_BYTES)
            # One preceding byte tells whether the suffix starts at a line boundary.
            if start:
                source.seek(start - 1)
                boundary = source.read(1) == b"\n"
            else:
                boundary = True
            source.seek(start)
            data = source.read(min(size, MAX_TAIL_BYTES))
    except FileNotFoundError:
        return None, False
    if not boundary:
        first_newline = data.find(b"\n")
        data = data[first_newline + 1:] if first_newline >= 0 else b""
    rows = data.decode("utf-8-sig", errors="replace").splitlines()
    truncated = bool(start or len(rows) > lines)
    return rows[-lines:], truncated


def snapshot(job_id, jobs_dir, *, lines=40):
    """One read-only snapshot of this ID; no latest-job selection or polling."""
    if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
        raise ValueError("id must be a PC job ID (job-... without path separators)")
    if type(lines) is not int or not 1 <= lines <= MAX_LINES:
        raise ValueError("lines must be an integer from 1 to %d" % MAX_LINES)
    jobs_dir = Path(jobs_dir)
    report = {
        "schema": "pc-job-status/v1", "job_id": job_id, "state": "unknown",
        "exit_code": None, "terminal": False, "evidence": None,
        "launch_pid": None, "process_verified": False,
        "tail": [], "tail_truncated": False, "errors": [],
    }
    marker_invalid = False
    try:
        marker = _marker(jobs_dir / (job_id + ".exit"))
        if marker is not None:
            match = _EXIT.fullmatch(marker)
            if not match:
                raise ValueError("expected a complete 'done <exit code>' marker")
            code = int(match.group(1))
            if not -2147483648 <= code <= 4294967295:
                raise ValueError("exit code is outside the Windows 32-bit range")
            report.update(state="completed", exit_code=code, terminal=True, evidence="exit_marker")
    except (OSError, ValueError, UnicodeError) as error:
        marker_invalid = True
        report["errors"].append("exit: %s" % error)

    # A launch receipt is useful before cmd creates the log, but never proves the
    # process is still running. A malformed terminal marker must not fall back.
    if not report["terminal"] and not marker_invalid:
        try:
            started = _marker(jobs_dir / (job_id + ".started"))
            if started is not None:
                match = _STARTED.fullmatch(started)
                if not match or not 1 <= int(match.group(1)) <= 4294967295:
                    raise ValueError("expected a complete 'pid=<positive 32-bit PID>' receipt")
                report.update(state="incomplete", evidence="launch_receipt", launch_pid=int(match.group(1)))
        except (OSError, ValueError, UnicodeError) as error:
            marker_invalid = True
            report["errors"].append("started: %s" % error)
    try:
        tail, truncated = _tail(jobs_dir / (job_id + ".log"), lines)
        if tail is not None:
            report.update(tail=tail, tail_truncated=truncated)
            if not report["terminal"] and not marker_invalid and report["evidence"] is None:
                report.update(state="incomplete", evidence="log")
    except OSError as error:
        report["errors"].append("log: %s" % error)
    if report["evidence"] is None and not report["errors"]:
        report["errors"].append("no job log, launch receipt or exit marker found; launch outcome is unknown")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="exact ID returned by pc-job.ps1 -Start")
    parser.add_argument("--lines", type=int, default=40, help="last 1..200 lines (default 40)")
    parser.add_argument("--jobs-dir", type=Path, help="artifact directory (default LOCALAPPDATA/Daedalus/jobs)")
    args = parser.parse_args(argv)
    jobs_dir = args.jobs_dir
    if jobs_dir is None:
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            parser.error("LOCALAPPDATA is unavailable; supply --jobs-dir")
        jobs_dir = Path(local) / "Daedalus" / "jobs"
    try:
        report = snapshot(args.id, jobs_dir, lines=args.lines)
    except (TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=True, separators=(",", ":")))
    # This is the observer's status. The recorded job code remains in the JSON.
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
