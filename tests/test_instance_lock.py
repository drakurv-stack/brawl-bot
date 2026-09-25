"""Regression test: the Windows positional-lock bug.

msvcrt.locking(fd, LK_NBLCK, 1) locks 1 byte starting at the CURRENT file
position (unlike fcntl.flock, which locks the whole file). The lock-file
creator ends at position 1 (after writing the seed byte); later openers
start at position 0. Without an explicit seek to 0 before locking, each
process locks a different byte, the locks never conflict, and the
single-instance guard silently does nothing on Windows.

We emulate msvcrt's positional semantics with fcntl.lockf (also
position-relative) and prove: no seek -> no conflict (bug); seek -> conflict.
Run:  python tests/test_instance_lock.py
"""
import fcntl
import os
import subprocess
import sys
import tempfile
import time

WORKER = """
import fcntl, os, sys, time
path, seek = sys.argv[1], sys.argv[2] == "seek"
fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
if os.fstat(fd).st_size == 0:
    os.write(fd, b"x")
if seek:
    os.lseek(fd, 0, os.SEEK_SET)
pos = os.lseek(fd, 0, os.SEEK_CUR)  # where msvcrt.locking() would lock
try:
    fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, pos, os.SEEK_SET)
except OSError:
    print("REFUSED", flush=True)
    sys.exit(1)
print("ACQUIRED", flush=True)
time.sleep(30)
"""


def try_second(path, seek):
    """Returns (exit_code, first_stdout_line) of a second worker.

    The holder keeps its lock (sleeping); the second worker prints one line
    (ACQUIRED/REFUSED) immediately after its non-blocking lock attempt.
    """
    mode = "seek" if seek else "noseek"
    holder = subprocess.Popen(
        [sys.executable, "-c", WORKER, path, mode],
        stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == "ACQUIRED", "holder failed"
    time.sleep(0.5)
    second = subprocess.Popen(
        [sys.executable, "-c", WORKER, path, mode],
        stdout=subprocess.PIPE, text=True)
    try:
        outcome = second.stdout.readline().strip()
    finally:
        if second.poll() is None:  # still alive -> it ACQUIRED and is sleeping
            second.kill()
    code = second.wait()
    holder.kill()
    holder.wait()
    return code, outcome


def main():
    ok = True

    with tempfile.TemporaryDirectory() as d:
        code, out = try_second(os.path.join(d, "bug.lock"), seek=False)
        # Buggy behavior: second process locks a DIFFERENT byte -> no conflict
        bug_reproduced = (out == "ACQUIRED")
        print(f"{'OK ' if bug_reproduced else 'FAIL'} no-seek: "
              f"second instance {out} (bug mechanism reproduced)")
        ok &= bug_reproduced

    with tempfile.TemporaryDirectory() as d:
        code, out = try_second(os.path.join(d, "fix.lock"), seek=True)
        # Fixed behavior: both lock byte 0 -> second is refused.
        # (Outcome string is the assertion; exit code is racy because the
        # parent may SIGKILL the worker mid-shutdown.)
        fixed = (out == "REFUSED")
        print(f"{'OK ' if fixed else 'FAIL'} with-seek: "
              f"second instance {out} (guard fires)")
        ok &= fixed

    print("ALL TESTS PASSED" if ok else "TESTS FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
