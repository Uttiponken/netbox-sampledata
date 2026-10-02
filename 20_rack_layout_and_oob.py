#!/usr/bin/env python3
"""
Phase 20: uniform rack layout + out-of-band (OOB) management cabling
(added post-hoc, 2026-10-02).

1. Re-seats every device in every rack per config.RACK_LAYOUT, so the same
   kind of device sits at the same height at every site, with 2U gaps
   between kinds of equipment. Moves are done in two passes (first into
   free low slots, then to the final slot) so a move never collides with a
   device that hasn't moved yet.
2. Adds one 48-port copper OOB switch per site (core rack, U39), then
   cables ONE management port per device to it, plus a 10GE uplink from
   the OOB switch to the site's core router.

See config.py's Phase 20 comment for the layout and the scope decisions
(one mgmt port per device, colo tenants' gear included, IDF over a riser,
OOB switch's own Management1 deliberately uncabled).

Depends on every earlier phase that creates racked devices (2, 5, 6, 8, 9,
10, 11, 12, 13, 17, 19). Safe to re-run.
"""

from common import connect, create_cable_if_needed, get_interface, get_or_create, report
from config import (
    OOB_DEVICE_ROLE,
    OOB_MGMT_IFACE,
    OOB_SITES,
    OOB_UPLINK_OOB_IFACE,
    OOB_UPLINK_ROUTER_IFACE,
    RACK_LAYOUT,
)


def realign(nb):
    print("== Rack layout ==")
    devices = {d.name: d for d in nb.dcim.devices.all()}
    for rack_name, layout in RACK_LAYOUT.items():
        if len(set(layout.values())) != len(layout):
            raise SystemExit(f"RACK_LAYOUT for {rack_name} has two devices in one slot")
        rack = nb.dcim.racks.get(name=rack_name)
        moving = []
        for name, target in layout.items():
            dev = devices[name]
            if dev.rack is None or dev.rack.id != rack.id:
                raise SystemExit(f"{name} is not in {rack_name}")
            if int(dev.position) != target:
                moving.append((dev, target))
        if not moving:
            print(f"  [exists ] {rack_name}: already laid out")
            continue
        # Pass 1: park in free low slots (every layout slot is >= 28, and the
        # low slots are empty in every rack).
        for temp, (dev, _target) in enumerate(moving, start=1):
            dev.position = temp
            dev.save()
        # Pass 2: final slots.
        for dev, target in moving:
            dev.position = target
            dev.save()
            print(f"  [moved  ] {rack_name}: {dev.name} -> U{target}")


def run(nb):
    realign(nb)

    print("== OOB switch role / device type ==")
    role, created = get_or_create(nb.dcim.device_roles, {"slug": OOB_DEVICE_ROLE["slug"]}, **OOB_DEVICE_ROLE)
    report("device role", role, created)
    switch_type = nb.dcim.device_types.get(slug="arista-dcs-7010t-48")

    sites = {s.slug: s for s in nb.dcim.sites.all()}
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}
    racks = {r.name: r for r in nb.dcim.racks.all()}
    nordfiber = nb.tenancy.tenants.get(slug="nordfiber-ab")

    print("== OOB switches ==")
    oob = {}
    for s in OOB_SITES:
        obj, created = get_or_create(
            nb.dcim.devices, {"name": s["name"]},
            name=s["name"], device_type=switch_type.id, role=role.id,
            site=sites[s["site_slug"]].id, location=locations[s["location_slug"]].id,
            rack=racks[s["rack_name"]].id, position=s["position"], face="front",
            tenant=nordfiber.id, status="active",
        )
        report("device", obj, created)
        oob[s["name"]] = obj

    print("== OOB cabling ==")
    for s in OOB_SITES:
        switch = oob[s["name"]]
        print(f"  -- {s['name']} --")
        for p in s["ports"]:
            dev = nb.dcim.devices.get(name=p["device"])
            mgmt = get_interface(nb, dev, OOB_MGMT_IFACE[dev.device_type.slug])
            port = get_interface(nb, switch, f"Ethernet{p['port']}")
            create_cable_if_needed(
                nb, port, "dcim.interface", mgmt, "dcim.interface",
                status="connected", label=p["label"], type="cat6",
                comments=f"OOB management: {dev.name} {mgmt.name} <-> {s['name']} Ethernet{p['port']}",
                tenant=nordfiber.id,
            )
        router = nb.dcim.devices.get(name=s["router"])
        create_cable_if_needed(
            nb,
            get_interface(nb, switch, OOB_UPLINK_OOB_IFACE), "dcim.interface",
            get_interface(nb, router, OOB_UPLINK_ROUTER_IFACE), "dcim.interface",
            status="connected", label=s["uplink_label"], type="dac-passive",
            comments=f"{s['name']} OOB uplink <-> {s['router']} {OOB_UPLINK_ROUTER_IFACE}",
            tenant=nordfiber.id,
        )


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 20 (rack layout + OOB management) complete.")
