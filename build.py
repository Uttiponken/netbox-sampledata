#!/usr/bin/env python3
"""
Run the whole build: layers 1-7 in order, then verify.py.

    python build.py            # build (or reconcile) everything, then verify
    python build.py 3 5        # only layers 3 to 5

Every layer is idempotent, so running this against a half-built or
already-built NetBox just fills in / corrects what differs.
"""

import glob
import subprocess
import sys

LAYERS = sorted(glob.glob("0[1-7]_*.py"))


def main(argv):
    first, last = (int(argv[0]), int(argv[1])) if len(argv) == 2 else (1, 7)
    for script in LAYERS:
        n = int(script[:2])
        if first <= n <= last:
            print(f"\n######## {script}")
            if subprocess.call([sys.executable, script]) != 0:
                sys.exit(f"{script} failed")
    if (first, last) == (1, 7):
        print("\n######## verify.py")
        sys.exit(subprocess.call([sys.executable, "verify.py"]))


if __name__ == "__main__":
    main(sys.argv[1:])
