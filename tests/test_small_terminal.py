#!/usr/bin/env python3
import os
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import fcntl
import time


def run(binary, rows, cols, args, seconds):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    env = os.environ.copy()
    env["LC_ALL"] = "C.UTF-8"
    env["LANG"] = "C.UTF-8"
    env.pop("LINES", None)
    env.pop("COLUMNS", None)
    proc = subprocess.Popen(
        [binary, *args],
        stdin=slave,
        stdout=slave,
        stderr=subprocess.PIPE,
        env=env,
        close_fds=True,
    )
    os.close(slave)
    output = b""
    deadline = time.time() + seconds
    while time.time() < deadline and proc.poll() is None:
        ready, _, _ = select.select([master], [], [], 0.1)
        if ready:
            try:
                output += os.read(master, 65536)
            except OSError:
                break
    status = proc.poll()
    if status is None:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=1)
    else:
        proc.wait(timeout=1)
    os.close(master)
    return status, output


def main():
    binary = sys.argv[1] if len(sys.argv) > 1 else "./cmatrix"
    failures = []

    status, output = run(binary, 3, 40, [], 2.0)
    if status is not None and status < 0:
        failures.append(
            "3x40 terminal died with signal %d before the run ended" % (-status)
        )
    elif len(output) == 0:
        failures.append("3x40 terminal produced no output")

    status, output = run(binary, 24, 80, [], 0.6)
    if status is not None and status < 0:
        failures.append(
            "24x80 terminal died with signal %d" % (-status)
        )
    elif len(output) == 0:
        failures.append("24x80 terminal produced no output")

    status, _ = run(binary, 3, 40, ["-o"], 1.0)
    if status is not None and status < 0:
        failures.append(
            "3x40 old-style terminal died with signal %d" % (-status)
        )

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print("small-terminal checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
