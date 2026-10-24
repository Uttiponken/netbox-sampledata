#!/usr/bin/env python3
"""
Run the whole build: layers 1-7 in order, then verify.py.

    python build.py            # build (or reconcile) everything, then verify
    python build.py 3 5        # only layers 3 to 5

Every layer is idempotent, so running this against a half-built or
already-built NetBox just fills in / corrects what differs.

The dataset loads into a vanilla NetBox and uses whichever of the six plugins
(pathways, fms, wdm, bgp, secrets, inventory) are installed. The plugin list
is printed first and the steps that were left out are summed up at the end.
Run it again after installing a plugin to add that plugin's part.
NETBOX_SKIP_PLUGINS=wdm,pathways switches plugins off on purpose.
"""

import glob
import subprocess
import sys

from common import connect, plugin_report

LAYERS = sorted(glob.glob("0[1-7]_*.py"))


def run(script, skipped):
    """Run one script, pass its output through, and remember the lines that say a plugin step was left out."""
    proc = subprocess.Popen([sys.executable, "-u", script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True, encoding="utf-8")
    for line in proc.stdout:
        sys.stdout.write(line)
        if line.startswith("  [skipped]") or line.startswith("  skip "):
            skipped.append(line.strip())
    return proc.wait()


def main(argv):
    first, last = (int(argv[0]), int(argv[1])) if len(argv) == 2 else (1, 7)
    connect()
    print("Plugins:")
    print("\n".join(plugin_report()))
    skipped = []
    for script in LAYERS:
        n = int(script[:2])
        if first <= n <= last:
            print(f"\n######## {script}")
            if run(script, skipped) != 0:
                sys.exit(f"{script} failed")
    code = 0
    if (first, last) == (1, 7):
        print("\n######## verify.py")
        code = run("verify.py", skipped)
    if skipped:
        print(f"\n{len(skipped)} plugin steps and checks were left out:")
        print("\n".join("  " + s for s in skipped))
        print("Install the plugin and run build.py again to add them.")
    sys.exit(code)


if __name__ == "__main__":
    main(sys.argv[1:])
