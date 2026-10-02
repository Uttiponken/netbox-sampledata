#!/usr/bin/env python3
"""
Phase 5: FMS (fiber physical plant).

Creates, in dependency order:
  manufacturers -> patch panel device type (fetched from the real
  devicetype-library, incl. front/rear port templates) -> device role ->
  4 patch panel devices (one per site) -> FMS cable type -> buffer tube
  templates -> 3 backbone fiber cables (dcim.Cable between two patch
  panels' rear ports, decorated with fms.FiberCable metadata, which
  auto-instantiates real BufferTube + FiberStrand objects from the cable
  type's templates)

Depends on Phase 1 (sites/tenants/locations) and Phase 2 (racks). Requires
the netbox-fms plugin. Safe to re-run.
"""

from common import (
    connect,
    create_cable_if_needed,
    create_device_type_from_yaml,
    create_fiber_cable_if_needed,
    fetch_devicetype_yaml,
    get_or_create,
    get_rear_port,
    report,
)
from config import (
    BACKBONE_FIBER_CABLES,
    FMS_BUFFER_TUBE_TEMPLATES,
    FMS_CABLE_TYPE,
    FMS_DEVICE_ROLES,
    FMS_DEVICE_TYPE_SOURCES,
    FMS_MANUFACTURERS,
    PATCH_PANELS,
)


def run(nb):
    print("== Manufacturers ==")
    manufacturers = {}
    for m in FMS_MANUFACTURERS:
        obj, created = get_or_create(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        report("manufacturer", obj, created)
        manufacturers[m["name"]] = obj

    print("== Patch panel device type (fetched from the real devicetype-library) ==")
    device_types = {}
    for mfr_name, path in FMS_DEVICE_TYPE_SOURCES:
        yaml_data = fetch_devicetype_yaml(path)
        dt = create_device_type_from_yaml(nb, manufacturers, yaml_data)
        device_types[dt.slug] = dt

    print("== Device roles ==")
    device_roles = {}
    for r in FMS_DEVICE_ROLES:
        obj, created = get_or_create(nb.dcim.device_roles, {"slug": r["slug"]}, **r)
        report("device role", obj, created)
        device_roles[r["slug"]] = obj

    sites = {s.slug: s for s in nb.dcim.sites.all()}
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}
    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    racks = {r.name: r for r in nb.dcim.racks.all()}
    patch_panel_type = device_types["generic-lc-24-port-fiber-patch-panel"]

    print("== Patch panel devices ==")
    devices = {}
    for p in PATCH_PANELS:
        obj, created = get_or_create(
            nb.dcim.devices,
            {"name": p["name"]},
            name=p["name"],
            device_type=patch_panel_type.id,
            role=device_roles["patch-panel"].id,
            site=sites[p["site_slug"]].id,
            location=locations[p["location_slug"]].id,
            rack=racks[p["rack_name"]].id,
            position=p["position"],
            face="front",
            tenant=tenants[p["tenant_slug"]].id,
            status="active",
        )
        report("device", obj, created)
        devices[p["name"]] = obj

    print("== FMS cable type ==")
    ct_fields = dict(FMS_CABLE_TYPE)
    mfr_name = ct_fields.pop("manufacturer_name")
    cable_type, created = get_or_create(
        nb.plugins.fms.cable_types,
        {"model": ct_fields["model"]},
        manufacturer=manufacturers[mfr_name].id,
        **ct_fields,
    )
    report("fms cable type", cable_type, created)

    print("== Buffer tube templates ==")
    if created:
        for btt in FMS_BUFFER_TUBE_TEMPLATES:
            nb.plugins.fms.buffer_tube_templates.create(fiber_cable_type=cable_type.id, **btt)
        print(f"  + {len(FMS_BUFFER_TUBE_TEMPLATES)} buffer tube templates")
    else:
        print("  [exists ] (skipped — cable type already existed)")

    print("== Backbone fiber cables ==")
    for fc in BACKBONE_FIBER_CABLES:
        a_dev = devices.get(fc["a_device"]) or nb.dcim.devices.get(name=fc["a_device"])
        b_dev = devices.get(fc["b_device"]) or nb.dcim.devices.get(name=fc["b_device"])
        a_port = get_rear_port(nb, a_dev, fc["a_port"])
        b_port = get_rear_port(nb, b_dev, fc["b_port"])

        dcim_cable, _ = create_cable_if_needed(
            nb,
            a_port, "dcim.rearport",
            b_port, "dcim.rearport",
            status="connected",
            label=fc["label"],
            comments=fc["comments"],
            tenant=tenants[fc["tenant_slug"]].id,
        )
        create_fiber_cable_if_needed(
            nb,
            dcim_cable,
            cable_type,
            notes=fc["fms_notes"],
        )


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 5 (FMS) complete.")
