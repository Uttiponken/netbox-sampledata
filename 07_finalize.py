#!/usr/bin/env python3
"""
Layer 7: finalize.

netbox-wdm re-runs path discovery whenever ANY cable touching WDM topology is
saved and spawns duplicates instead of recognizing existing paths (an upstream
bug; with 40 channels per node it grows to hundreds of rows). The paths that
matter are the ones attached to a WdmCircuit; every other row is derived
data. This layer deletes the rest, then re-checks that the attached ones
still stitch complete. Must run last: any later cable save can regrow them,
just run it again. Without netbox-wdm there is nothing to prune and only the
totals are printed.

Safe to re-run.
"""

from common import api, connect, have, skip


def prune_wavelength_paths(nb):
    attached = set()
    for wc in nb.plugins.wdm.wdm_circuits.all():
        for p in wc.wavelength_paths or []:
            attached.add(p if isinstance(p, int) else p.id)
    if not attached:
        raise SystemExit("No WdmCircuit has an attached wavelength path; refusing to prune everything")

    paths = list(nb.plugins.wdm.wdm_wavelength_paths.all())
    stale = [p for p in paths if p.id not in attached]
    print(f"== Wavelength paths: {len(paths)} total, {len(attached)} attached, {len(stale)} stale ==")
    if stale:
        nb.plugins.wdm.wdm_wavelength_paths.delete(stale)
        print(f"  [deleted] {len(stale)} stale paths")

    print("== Re-stitching attached circuits ==")
    for wc in nb.plugins.wdm.wdm_circuits.all():
        res = api(f"/api/plugins/wdm/wdm-circuits/{wc.id}/stitch/")
        states = [(p["is_complete"], p["is_active"]) for p in res["paths"]]
        print(f"  {wc.name}: {states}")
        if not states or not all(c and a for c, a in states):
            raise SystemExit(f"{wc.name} no longer stitches complete after pruning")


def run(nb):
    if have("wdm"):
        prune_wavelength_paths(nb)
    else:
        skip("wdm", "pruning and re-stitching the wavelength paths")

    print("== Totals ==")
    for label, endpoint in [("sites", nb.dcim.sites), ("racks", nb.dcim.racks), ("devices", nb.dcim.devices),
                            ("cables", nb.dcim.cables), ("circuits", nb.circuits.circuits),
                            ("ip addresses", nb.ipam.ip_addresses)]:
        print(f"  {label}: {endpoint.count()}")


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nLayer 7 (finalize) complete.")
