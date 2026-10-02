#!/usr/bin/env python3
"""
Phase 22: prune spurious wavelength paths (added post-hoc, 2026-10-02).

netbox-wdm re-runs path discovery whenever ANY cable touching WDM topology
is saved and spawns duplicates instead of recognizing existing paths (the
upstream bug already documented in Phase 6). Phase 14 gave every node all
40 channels, which multiplied it: the audit found 240 WdmWavelengthPath
rows, 3 of them real (the ones attached to a WdmCircuit).

Deletes every wavelength path that no WdmCircuit references. These are
plugin-derived rows, not source data. Must run LAST — any later cable save
on WDM topology can regrow them; just re-run this script. Safe to re-run.
"""

from common import call_plugin_action, connect


def run(nb):
    attached = set()
    for wc in nb.plugins.wdm.wdm_circuits.all():
        for p in wc.wavelength_paths or []:
            attached.add(p if isinstance(p, int) else p.id)
    if not attached:
        raise SystemExit("No WdmCircuit has an attached wavelength path — refusing to prune everything")

    all_paths = list(nb.plugins.wdm.wdm_wavelength_paths.all())
    stale = [p for p in all_paths if p.id not in attached]
    print(f"== Wavelength paths: {len(all_paths)} total, {len(attached)} attached to a WdmCircuit, {len(stale)} stale ==")
    if stale:
        nb.plugins.wdm.wdm_wavelength_paths.delete(stale)
        print(f"  [deleted] {len(stale)} stale wavelength paths")

    print("== Re-checking attached circuits still stitch ==")
    for wc in nb.plugins.wdm.wdm_circuits.all():
        res = call_plugin_action(f"/api/plugins/wdm/wdm-circuits/{wc.id}/stitch/")
        states = [(p["is_complete"], p["is_active"]) for p in res["paths"]]
        print(f"  {wc.name}: {states}")
        if not states or not all(c and a for c, a in states):
            raise SystemExit(f"{wc.name} no longer stitches complete after pruning")


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 22 (wavelength path prune) complete.")
