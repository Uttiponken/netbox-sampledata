#!/usr/bin/env python3
"""
Phase 2: Infrastructure.

Creates, in NetBox's own dependency order:
  manufacturers -> device types (+ interface templates, fetched live from
  the real NetBox devicetype-library) -> device roles -> racks -> devices
  (interfaces auto-instantiate from the device type's templates) -> mgmt
  IPAM roles/prefixes -> mgmt IP addresses, assigned to each device's mgmt
  interface and set as its primary IPv4.

Depends on Phase 1 (01_organization.py) having already run — this script
looks up tenants/sites/locations by slug and expects them to exist.

Safe to re-run, same as Phase 1: everything is looked up before creation.
"""

from common import connect, create_device_type_from_yaml, fetch_devicetype_yaml, get_or_create, report
from config import (
    DEVICE_ROLES,
    DEVICE_TYPE_SOURCES,
    DEVICES,
    IPAM_ROLES,
    MANUFACTURERS,
    MGMT_PREFIXES,
    RACKS,
)


def run(nb):
    print("== Manufacturers ==")
    manufacturers = {}
    for m in MANUFACTURERS:
        obj, created = get_or_create(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        report("manufacturer", obj, created)
        manufacturers[m["name"]] = obj

    print("== Device types (fetched from the real devicetype-library) ==")
    device_types = {}
    for mfr_name, path in DEVICE_TYPE_SOURCES:
        yaml_data = fetch_devicetype_yaml(path)
        dt = create_device_type_from_yaml(nb, manufacturers, yaml_data)
        device_types[dt.slug] = dt

    print("== Device roles ==")
    device_roles = {}
    for r in DEVICE_ROLES:
        obj, created = get_or_create(nb.dcim.device_roles, {"slug": r["slug"]}, **r)
        report("device role", obj, created)
        device_roles[r["slug"]] = obj

    # Sites/locations/tenants come from Phase 1 — fetched, not recreated.
    sites = {s.slug: s for s in nb.dcim.sites.all()}
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}
    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    missing = [s for s in {r["site_slug"] for r in RACKS} if s not in sites]
    if missing:
        raise SystemExit(f"Missing sites (did 01_organization.py run?): {missing}")

    print("== Racks ==")
    racks = {}
    for r in RACKS:
        obj, created = get_or_create(
            nb.dcim.racks,
            {"name": r["name"], "site_id": sites[r["site_slug"]].id},
            name=r["name"],
            site=sites[r["site_slug"]].id,
            location=locations[r["location_slug"]].id,
            tenant=tenants[r["tenant_slug"]].id,
            status="active",
            width=19,
            u_height=42,
        )
        report("rack", obj, created)
        racks[r["name"]] = obj

    print("== Devices ==")
    devices = {}
    for d in DEVICES:
        obj, created = get_or_create(
            nb.dcim.devices,
            {"name": d["name"]},
            name=d["name"],
            device_type=device_types[d["device_type_slug"]].id,
            role=device_roles[d["role_slug"]].id,
            site=sites[d["site_slug"]].id,
            location=locations[d["location_slug"]].id,
            rack=racks[d["rack_name"]].id,
            position=d["position"],
            face="front",
            tenant=tenants[d["tenant_slug"]].id,
            status="active",
        )
        report("device", obj, created)
        devices[d["name"]] = obj

    print("== IPAM roles ==")
    ipam_roles = {}
    for r in IPAM_ROLES:
        obj, created = get_or_create(nb.ipam.roles, {"slug": r["slug"]}, **r)
        report("ipam role", obj, created)
        ipam_roles[r["slug"]] = obj

    print("== Management prefixes ==")
    for p in MGMT_PREFIXES:
        site = sites[p["site_slug"]]
        obj, created = get_or_create(
            nb.ipam.prefixes,
            {"prefix": p["prefix"]},
            prefix=p["prefix"],
            scope_type="dcim.site",
            scope_id=site.id,
            tenant=tenants[p["tenant_slug"]].id,
            role=ipam_roles["management"].id,
            status="active",
            description=f"Out-of-band management network, {site.name}",
        )
        report("prefix", obj, created)

    print("== Management IP addresses (assigned + set as primary IPv4) ==")
    for d in DEVICES:
        device = devices[d["name"]]
        iface = nb.dcim.interfaces.get(device_id=device.id, name=d["mgmt_interface"])
        if iface is None:
            raise SystemExit(
                f"Interface {d['mgmt_interface']!r} not found on device {d['name']!r} — "
                "did its device type's interface templates get created correctly?"
            )

        ip, created = get_or_create(
            nb.ipam.ip_addresses,
            {"address": d["mgmt_ip"]},
            address=d["mgmt_ip"],
            tenant=tenants[d["ip_tenant_slug"]].id,
            status="active",
            assigned_object_type="dcim.interface",
            assigned_object_id=iface.id,
        )
        report("mgmt IP", ip, created)

        if str(device.primary_ip4) != d["mgmt_ip"]:
            device.primary_ip4 = ip.id
            device.save()
            print(f"           set as primary IPv4 for {d['name']}")


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 2 (Infrastructure) complete.")
