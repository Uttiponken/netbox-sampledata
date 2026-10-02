#!/usr/bin/env python3
"""
Phase 3: Connections.

Creates cables between existing devices' existing interfaces:
  - router <-> switch uplink, one per Nordfiber site
  - colo server <-> site switch cross-connect, one per colocated server

Depends on Phase 2 (02_infrastructure.py) — devices and their interfaces
must already exist. Wireless links were considered and deliberately left
out: there's no radio equipment in the scenario yet, and adding some just
to populate this phase would be padding rather than a real story (see
docs/DESIGN.md).

Safe to re-run: a cable is skipped if either endpoint interface already has
one attached (see common.create_cable_if_needed).
"""

from common import connect, create_cable_if_needed, get_interface
from config import CABLES


def run(nb):
    print("== Cables ==")
    devices = {d.name: d for d in nb.dcim.devices.all()}
    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    missing = {c["a_device"] for c in CABLES} | {c["b_device"] for c in CABLES}
    missing -= set(devices)
    if missing:
        raise SystemExit(f"Missing devices (did 02_infrastructure.py run?): {missing}")

    for c in CABLES:
        iface_a = get_interface(nb, devices[c["a_device"]], c["a_iface"])
        iface_b = get_interface(nb, devices[c["b_device"]], c["b_iface"])
        create_cable_if_needed(
            nb,
            iface_a, "dcim.interface",
            iface_b, "dcim.interface",
            status="connected",
            label=c["label"],
            comments=c["comments"],
            tenant=tenants[c["tenant_slug"]].id,
        )


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 3 (Connections) complete.")
