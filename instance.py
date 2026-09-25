"""Single-instance guard: stop the "5 windows" problem.

If you launch calibrate.py (or visualize.py) while one is already running,
the new copy prints a message and exits instead of stacking another window.

Uses a real OS file lock (msvcrt on Windows, fcntl on Unix), held open for
the life of the process — so the OS itself releases it if we crash. No PID
files, no stale locks, nothing to clean up.
"""
import os
import sys
import tempfile

_lock_fd = None  # kept open: closing it (or dying) releases the lock


def single_instance(name):
    global _lock_fd
    path = os.path.join(tempfile.gettempdir(), f"brawlbot-{name}.lock")
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        if os.fstat(fd).st_size == 0:
            os.write(fd, b"x")  # msvcrt needs at least 1 byte to lock
    except OSError:
        pass
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        print(f"'{name}' is already running. "
              f"Press ESC in its window to close it first.")
        sys.exit(1)
    _lock_fd = fd
