#!/usr/bin/env python3
"""
Phase 13: Vastkust Bredband AB's own MeetMe panel (added post-hoc,
2026-09-27).

Applies the exact same cable-splitting method used in Phase 12 to
`got-cbl-00007` (Phase 9's Internet-transit circuit demarc): instead of
the circuit termination cabling straight to got-rtr-01, Vastkust Bredband
AB (Nordfiber's own upstream Internet provider) gets its own dedicated
panel in the Gothenburg MeetMe room, cross-connected through Nordfiber's
existing MeetMe panel and patch panel — the same demarc pattern every
other party at this site already uses. See config.py's Phase 13 comment
block for the exact port/label plan.

Depends on Phase 5 (patch panel device type, got-patch-01), Phase 9
(circuit VKB-INET-0001), Phase 12 (got-mmr-nordfiber-01). Safe to re-run.
"""

from common import (
    connect,
    create_cable_if_needed,
    create_device_type_from_yaml,
    disconnect_direct_cable_if_present,
    fetch_devicetype_yaml,
    get_front_port,
    get_interface,
    get_or_create,
    get_rear_port,
    report,
)
from config import (
    FMS_DEVICE_TYPE_SOURCES,
    FMS_MANUFACTURERS,
    VASTKUST_MEETME_PANEL,
    VASTKUST_MEETME_RETROFIT,
    VASTKUST_TENANT,
    VASTKUST_TENANT_GROUP,
)


def run(nb):
    print("== Vastkust Bredband AB as a Tenant too (Suppliers group) ==")
    obj, created = get_or_create(nb.tenancy.tenant_groups, {"slug": VASTKUST_TENANT_GROUP["slug"]}, **VASTKUST_TENANT_GROUP)
    report("tenant group", obj, created)
    tg_fields = dict(VASTKUST_TENANT)
    group_slug = tg_fields.pop("group_slug")
    group = nb.tenancy.tenant_groups.get(slug=group_slug)
    vastkust_tenant, created = get_or_create(
        nb.tenancy.tenants, {"slug": tg_fields["slug"]}, group=group.id, **tg_fields
    )
    report("tenant", vastkust_tenant, created)

    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    racks = {r.name: r for r in nb.dcim.racks.all()}
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}

    print("== Patch panel device type (reused from Phase 5) ==")
    manufacturers = {}
    for m in FMS_MANUFACTURERS:
        obj, created = get_or_create(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        manufacturers[m["name"]] = obj
    panel_type = None
    for mfr_name, path in FMS_DEVICE_TYPE_SOURCES:
        yaml_data = fetch_devicetype_yaml(path)
        panel_type = create_device_type_from_yaml(nb, manufacturers, yaml_data)
    panel_role = nb.dcim.device_roles.get(slug="patch-panel")

    print("== Vastkust Bredband AB's own MeetMe panel ==")
    p = VASTKUST_MEETME_PANEL
    rack = racks[p["rack"]]
    vastkust_panel, created = get_or_create(
        nb.dcim.devices, {"name": p["name"]},
        name=p["name"], device_type=panel_type.id, role=panel_role.id,
        site=rack.site.id, location=locations[p["location_slug"]].id, rack=rack.id,
        position=p["position"], face="front", tenant=tenants[p["tenant_slug"]].id, status="active",
    )
    report("device", vastkust_panel, created)

    print("== Split got-cbl-00007 into the full MeetMe chain ==")
    r = VASTKUST_MEETME_RETROFIT
    circuit = nb.circuits.circuits.get(cid=r["circuit_cid"])
    term = nb.circuits.circuit_terminations.get(circuit_id=circuit.id, term_side=r["circuit_term_side"])
    nordfiber_device = nb.dcim.devices.get(name=r["nordfiber_device"])
    nordfiber_iface = get_interface(nb, nordfiber_device, r["nordfiber_iface"])

    disconnect_direct_cable_if_present(
        nb, term, "circuits.circuittermination", nordfiber_iface, "dcim.interface",
    )

    vastkust_rear = get_rear_port(nb, vastkust_panel, r["vastkust_port"])
    create_cable_if_needed(
        nb,
        term, "circuits.circuittermination",
        vastkust_rear, "dcim.rearport",
        status="connected",
        label=r["cables"]["circuit_to_vastkust_panel"],
        comments=f"{r['circuit_cid']} ({r['circuit_term_side']}-side) <-> {r['vastkust_panel']} (Vastkust's own incoming fiber)",
        tenant=tenants["vastkust-bredband-ab"].id,
    )

    vastkust_front = get_front_port(nb, vastkust_panel, r["vastkust_port"])
    nordfiber_mmr_panel = nb.dcim.devices.get(name=r["nordfiber_mmr_panel"])
    nordfiber_mmr_front = get_front_port(nb, nordfiber_mmr_panel, r["nordfiber_mmr_port"])
    create_cable_if_needed(
        nb,
        vastkust_front, "dcim.frontport",
        nordfiber_mmr_front, "dcim.frontport",
        status="connected",
        label=r["cables"]["vastkust_panel_to_nordfiber_mmr"],
        comments=f"{r['vastkust_panel']} <-> {r['nordfiber_mmr_panel']} (cross-connect jumper, MeetMe room)",
        tenant=tenants["nordfiber-ab"].id,
    )

    nordfiber_mmr_rear = get_rear_port(nb, nordfiber_mmr_panel, r["nordfiber_mmr_port"])
    nordfiber_patch = nb.dcim.devices.get(name=r["nordfiber_patch_panel"])
    nordfiber_patch_rear = get_rear_port(nb, nordfiber_patch, r["nordfiber_patch_port"])
    create_cable_if_needed(
        nb,
        nordfiber_mmr_rear, "dcim.rearport",
        nordfiber_patch_rear, "dcim.rearport",
        status="connected",
        label=r["cables"]["nordfiber_mmr_to_patch"],
        comments=f"{r['nordfiber_mmr_panel']} <-> {r['nordfiber_patch_panel']} (trunk, MeetMe room to telecom room)",
        tenant=tenants["nordfiber-ab"].id,
    )

    nordfiber_patch_front = get_front_port(nb, nordfiber_patch, r["nordfiber_patch_port"])
    create_cable_if_needed(
        nb,
        nordfiber_patch_front, "dcim.frontport",
        nordfiber_iface, "dcim.interface",
        status="connected",
        label=r["cables"]["patch_to_router"],
        comments=f"{r['nordfiber_patch_panel']} <-> {r['nordfiber_device']} {r['nordfiber_iface']} (in-rack jumper)",
        tenant=tenants["nordfiber-ab"].id,
    )


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 13 (Vastkust Bredband AB MeetMe panel) complete.")
