# SPDX-License-Identifier: MIT
"""Process-held file exclusivity. A leftover file is not evidence of a live owner."""
from contextlib import contextmanager
import os
from pathlib import Path


class LocalOwnerBusy(RuntimeError):
    pass


@contextmanager
def exclusive_file(path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0,2)
        if stream.tell()==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as error:
            raise LocalOwnerBusy('Another local process owns '+str(path)) from error
        try:
            yield
        finally:
            if os.name=='nt':
                msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
