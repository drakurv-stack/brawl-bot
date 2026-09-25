"""Single-instance guard: stop the "5 windows" problem.

If you launch calibrate.py (or visualize.py) while one is already running,
the new copy prints a message and exits instead of stacking another window.
Stale locks from crashed runs are detected via PID and taken over.
"""
import atexit
import os
import sys
import tempfile


def single_instance(name):
    path = os.path.join(tempfile.gettempdir(), f"brawlbot-{name}.lock")
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w") as f:
            f.write(str(os.getpid()))
    except FileExistsError:
        try:
            with open(path) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)  # raises OSError if that process is gone
            print(f"'{name}' is already running (pid {pid}). "
                  f"Press ESC in its window to close it first.")
            sys.exit(1)
        except (ValueError, OSError):
            pass  # stale lock from a dead process: take over
        with open(path, "w") as f:
            f.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(path) and os.remove(path))
