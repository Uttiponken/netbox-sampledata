#!/usr/bin/env python3
"""
Phase 10: WDM client demarc shelf (added post-hoc, 2026-09-27).

Adds one SmartOptics DCP-2 chassis (+ a DCP-110 module) at every site with
WDM equipment, and retrofits the existing tenant handoffs (Fjord Media's
wavelength service, the Baltic Retail backup path) to land on a grey
10G client port on that shelf instead of directly on the muxponder's own
DWDM channel port. See config.py's Phase 10 comment block for the full
rationale, including why the DCP-1610 module was dropped and why
Gothenburg's shelf is installed but left uncabled.

Creates, in dependency order:
  DCP-2 device type (with module bays) + DCP-110 module type
  -> device role -> 4 chassis -> modules installed in their bays
     (auto-instantiates real "Line/{n}/1"..."Client/{n}/10" interfaces)
  -> per retrofit: delete the old direct muxponder<->client cable, then
     cable muxponder channel front port -> shelf Line port -> shelf
     Client port -> the same client interface as before.

Depends on Phase 6 (WDM profile/nodes) and Phase 8 (backup path WDM
nodes). Requires netbox-wdm only insofar as the channel front ports it
created are reused; this phase itself only uses core dcim (Module/
ModuleType). Safe to re-run.
"""

from common import (
    connect,
    create_cable_if_needed,
    create_device_type_from_yaml,
    create_module_type_from_yaml,
    disconnect_direct_cable_if_present,
    fetch_devicetype_yaml,
    fetch_moduletype_yaml,
    get_interface,
    get_module_bay,
    get_or_create,
    install_module_if_needed,
    report,
)
from config import (
    DCP2_CHASSIS,
    DCP2_DEVICE_ROLES,
    DCP2_DEVICE_TYPE_SOURCES,
    DCP2_MANUFACTURERS,
    DCP2_MODULE_TYPE_SOURCES,
    DCP2_MODULES,
    DCP2_RETROFITS,
)


def run(nb):
    print("== Manufacturers ==")
    manufacturers = {}
    for m in DCP2_MANUFACTURERS:
        obj, created = get_or_create(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        report("manufacturer", obj, created)
        manufacturers[m["name"]] = obj

    print("== DCP-2 chassis device type (incl. module bay templates) ==")
    device_type = None
    for mfr_name, path in DCP2_DEVICE_TYPE_SOURCES:
        yaml_data = fetch_devicetype_yaml(path)
        device_type = create_device_type_from_yaml(nb, manufacturers, yaml_data)

    print("== DCP-110 module type ==")
    module_type = None
    for mfr_name, path in DCP2_MODULE_TYPE_SOURCES:
        yaml_data = fetch_moduletype_yaml(path)
        module_type = create_module_type_from_yaml(nb, manufacturers, yaml_data)

    print("== Device role ==")
    device_roles = {}
    for r in DCP2_DEVICE_ROLES:
        obj, created = get_or_create(nb.dcim.device_roles, {"slug": r["slug"]}, **r)
        report("device role", obj, created)
        device_roles[r["slug"]] = obj

    sites = {s.slug: s for s in nb.dcim.sites.all()}
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}
    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    racks = {r.name: r for r in nb.dcim.racks.all()}

    print("== DCP-2 chassis devices ==")
    chassis = {}
    for c in DCP2_CHASSIS:
        obj, created = get_or_create(
            nb.dcim.devices,
            {"name": c["name"]},
            name=c["name"],
            device_type=device_type.id,
            role=device_roles["wdm-client-shelf"].id,
            site=sites[c["site_slug"]].id,
            location=locations[c["location_slug"]].id,
            rack=racks[c["rack_name"]].id,
            position=c["position"],
            face="front",
            tenant=tenants[c["tenant_slug"]].id,
            status="active",
        )
        report("device", obj, created)
        chassis[c["name"]] = obj

    print("== Modules installed (auto-instantiates Line/Client interfaces) ==")
    for m in DCP2_MODULES:
        device = chassis[m["chassis"]]
        bay = get_module_bay(nb, device, m["bay"])
        install_module_if_needed(nb, device, bay, module_type)

    print("== Retrofits: muxponder channel -> shelf Line -> shelf Client -> tenant ==")
    all_devices = {d.name: d for d in nb.dcim.devices.all()}
    for r in DCP2_RETROFITS:
        shelf = chassis[r["chassis"]]
        pos = r["module_position"]
        line_iface = get_interface(nb, shelf, f"Line/{pos}/1")
        client_shelf_iface = get_interface(nb, shelf, f"Client/{pos}/1")

        wdm_device = all_devices[r["wdm_node"]]
        channel_front_port = nb.dcim.front_ports.get(device_id=wdm_device.id, name=r["wdm_front_port"])

        client_device = all_devices[r["client_device"]]
        client_iface = get_interface(nb, client_device, r["client_iface"])

        disconnect_direct_cable_if_present(
            nb,
            channel_front_port, "dcim.frontport",
            client_iface, "dcim.interface",
        )

        create_cable_if_needed(
            nb,
            channel_front_port, "dcim.frontport",
            line_iface, "dcim.interface",
            status="connected",
            label=r["line_cable_label"],
            comments=f"{r['wdm_node']} channel {r['wdm_front_port']} <-> {r['chassis']} {line_iface.name} (DCP-110 line side)",
            tenant=tenants["nordfiber-ab"].id,
        )
        create_cable_if_needed(
            nb,
            client_shelf_iface, "dcim.interface",
            client_iface, "dcim.interface",
            status="connected",
            label=r["client_cable_label"],
            comments=(
                f"{r['chassis']} {client_shelf_iface.name} <-> {r['client_device']} {r['client_iface']} "
                "(grey client handoff via DCP-110)"
            ),
            tenant=tenants["nordfiber-ab"].id,
        )


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 10 (WDM client demarc shelf) complete.")
