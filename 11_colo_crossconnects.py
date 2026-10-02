#!/usr/bin/env python3
"""
Phase 11: colo tenant fiber cross-connects via a MeetMe room
(added post-hoc, 2026-09-27).

Re-architects how the two colo tenants (Polaris Cloud Services, Vasthamnen
Logistics) reach Nordfiber's network: instead of a server cabled straight
to Nordfiber's own switch, each tenant now has its own switch, its own
top-of-rack (ToR) fiber patch panel, and its own dedicated demarc panel in
a MeetMe/cross-connect room — which belongs to a third-party facility
operator, NOT Nordfiber. See config.py's Phase 11 comment block for the
full confirmed design (including the ownership correction that came in
after the topology itself was already confirmed).

Creates, in dependency order:
  Facility Operators tenant group + Skagerrak Interconnect AB tenant
  -> MeetMe Locations at all 4 sites -> 2 MeetMe racks (Stockholm,
     Gothenburg only — tenanted to the facility operator, not Nordfiber)
  -> per colo tenant-rack: a tenant-owned switch + ToR panel (in their
     existing colo rack) + a dedicated panel in the MeetMe room
  -> per server: retrofit its cable off Nordfiber's switch onto the
     tenant's own switch
  -> the 4-hop fiber chain: switch -> ToR panel -> [trunk] -> MeetMe panel
     -> [trunk] -> Nordfiber's EXISTING patch panel -> [jumper] ->
     Nordfiber's switch (reusing sto-patch-01/got-patch-01, not a new
     dedicated Nordfiber panel).

Depends on Phase 1 (tenants), Phase 2 (colo servers/racks), Phase 5 (patch
panel device type, sto-patch-01/got-patch-01), Phase 9 (Arista access
switch device type). Safe to re-run.
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
    COLO_CROSSCONNECTS,
    FMS_DEVICE_TYPE_SOURCES,
    FMS_MANUFACTURERS,
    GOTHENBURG_OFFICE_DEVICE_TYPE_SOURCES,
    MANUFACTURERS,
    MEETME_LOCATIONS,
    MEETME_RACKS,
    MEETME_TENANT,
    MEETME_TENANT_GROUPS,
)


def run(nb):
    sites = {s.slug: s for s in nb.dcim.sites.all()}

    print("== Facility Operators tenant group + Skagerrak Interconnect AB ==")
    for tg in MEETME_TENANT_GROUPS:
        obj, created = get_or_create(nb.tenancy.tenant_groups, {"slug": tg["slug"]}, **tg)
        report("tenant group", obj, created)
    tg_fields = dict(MEETME_TENANT)
    group_slug = tg_fields.pop("group_slug")
    group = nb.tenancy.tenant_groups.get(slug=group_slug)
    facility_tenant, created = get_or_create(
        nb.tenancy.tenants, {"slug": tg_fields["slug"]}, group=group.id, **tg_fields
    )
    report("tenant", facility_tenant, created)

    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}

    print("== MeetMe Locations (all 4 sites) ==")
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}
    for loc in MEETME_LOCATIONS:
        fields = {"name": loc["name"], "slug": loc["slug"], "site": sites[loc["site_slug"]].id}
        if loc["parent_slug"]:
            fields["parent"] = locations[loc["parent_slug"]].id
        obj, created = get_or_create(nb.dcim.locations, {"slug": loc["slug"]}, **fields)
        report("location", obj, created)
        locations[loc["slug"]] = obj

    print("== MeetMe racks (Stockholm + Gothenburg only, tenanted to the facility operator) ==")
    racks = {r.name: r for r in nb.dcim.racks.all()}
    for r in MEETME_RACKS:
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

    print("== Device types (reused: Arista access switch, Generic LC patch panel) ==")
    manufacturers = {}
    for m in MANUFACTURERS + FMS_MANUFACTURERS:
        obj, created = get_or_create(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        manufacturers[m["name"]] = obj
    device_types = {}
    for mfr_name, path in GOTHENBURG_OFFICE_DEVICE_TYPE_SOURCES + FMS_DEVICE_TYPE_SOURCES:
        yaml_data = fetch_devicetype_yaml(path)
        dt = create_device_type_from_yaml(nb, manufacturers, yaml_data)
        device_types[dt.slug] = dt
    switch_type = device_types["arista-dcs-7010t-48"]
    panel_type = device_types["generic-lc-24-port-fiber-patch-panel"]

    device_roles = {dr.slug: dr for dr in nb.dcim.device_roles.all()}

    all_devices = {d.name: d for d in nb.dcim.devices.all()}

    print("== Tenant switches, ToR panels, and MeetMe-room panels ==")
    for cc in COLO_CROSSCONNECTS:
        tenant = tenants[cc["tenant_slug"]]
        colo_rack = racks[cc["colo_rack"]]
        site = colo_rack.site

        obj, created = get_or_create(
            nb.dcim.devices, {"name": cc["switch_name"]},
            name=cc["switch_name"], device_type=switch_type.id, role=device_roles["access-switch"].id,
            site=site.id, location=colo_rack.location.id, rack=colo_rack.id,
            position=cc["switch_position"], face="front", tenant=tenant.id, status="active",
        )
        report("device", obj, created)
        all_devices[cc["switch_name"]] = obj

        obj, created = get_or_create(
            nb.dcim.devices, {"name": cc["tor_panel_name"]},
            name=cc["tor_panel_name"], device_type=panel_type.id, role=device_roles["patch-panel"].id,
            site=site.id, location=colo_rack.location.id, rack=colo_rack.id,
            position=cc["tor_panel_position"], face="front", tenant=tenant.id, status="active",
        )
        report("device", obj, created)
        all_devices[cc["tor_panel_name"]] = obj

        mmr_rack = racks[cc["mmr_rack"]]
        obj, created = get_or_create(
            nb.dcim.devices, {"name": cc["mmr_panel_name"]},
            name=cc["mmr_panel_name"], device_type=panel_type.id, role=device_roles["patch-panel"].id,
            site=mmr_rack.site.id, location=locations[cc["mmr_location_slug"]].id, rack=mmr_rack.id,
            position=cc["mmr_panel_position"], face="front", tenant=tenant.id, status="active",
        )
        report("device", obj, created)
        all_devices[cc["mmr_panel_name"]] = obj

    print("== Retrofit: server cables move from Nordfiber's switch to the tenant's own switch ==")
    for cc in COLO_CROSSCONNECTS:
        tenant = tenants[cc["tenant_slug"]]
        tenant_switch = all_devices[cc["switch_name"]]
        for s in cc["servers"]:
            server = all_devices[s["device"]]
            server_iface = get_interface(nb, server, s["iface"])
            old_switch = all_devices[s["old_nordfiber_switch"]]
            old_switch_iface = get_interface(nb, old_switch, s["old_nordfiber_iface"])
            disconnect_direct_cable_if_present(
                nb, server_iface, "dcim.interface", old_switch_iface, "dcim.interface",
            )
            new_switch_iface = get_interface(nb, tenant_switch, s["switch_iface"])
            create_cable_if_needed(
                nb,
                server_iface, "dcim.interface",
                new_switch_iface, "dcim.interface",
                status="connected",
                label=s["cable_label"],
                comments=f"{s['device']} <-> {cc['switch_name']} (tenant-owned access switch)",
                tenant=tenant.id,
            )

    print("== The 4-hop fiber chain: switch -> ToR -> MeetMe panel -> Nordfiber's patch panel -> Nordfiber's switch ==")
    for cc in COLO_CROSSCONNECTS:
        tenant = tenants[cc["tenant_slug"]]
        nordfiber_tenant = tenants["nordfiber-ab"]
        tenant_switch = all_devices[cc["switch_name"]]
        tor_panel = all_devices[cc["tor_panel_name"]]
        mmr_panel = all_devices[cc["mmr_panel_name"]]
        nordfiber_patch = all_devices[cc["nordfiber_patch_panel"]]
        nordfiber_switch = all_devices[cc["nordfiber_switch"]]

        uplink_iface = get_interface(nb, tenant_switch, cc["switch_uplink_iface"])
        tor_front = get_front_port(nb, tor_panel, cc["tor_port"])
        create_cable_if_needed(
            nb,
            uplink_iface, "dcim.interface",
            tor_front, "dcim.frontport",
            status="connected",
            label=cc["cables"]["switch_to_tor"],
            comments=f"{cc['switch_name']} uplink <-> {cc['tor_panel_name']} {cc['tor_port']} (in-rack)",
            tenant=tenant.id,
        )

        tor_rear = get_rear_port(nb, tor_panel, cc["tor_port"])
        mmr_rear = get_rear_port(nb, mmr_panel, cc["mmr_port"])
        create_cable_if_needed(
            nb,
            tor_rear, "dcim.rearport",
            mmr_rear, "dcim.rearport",
            status="connected",
            label=cc["cables"]["tor_to_mmr"],
            comments=f"{cc['tor_panel_name']} <-> {cc['mmr_panel_name']} (trunk to MeetMe room)",
            tenant=tenant.id,
        )

        mmr_front = get_front_port(nb, mmr_panel, cc["mmr_port"])
        nordfiber_patch_rear = get_rear_port(nb, nordfiber_patch, cc["nordfiber_patch_port"])
        create_cable_if_needed(
            nb,
            mmr_front, "dcim.frontport",
            nordfiber_patch_rear, "dcim.rearport",
            status="connected",
            label=cc["cables"]["mmr_to_nordfiber_patch"],
            comments=(
                f"{cc['mmr_panel_name']} <-> {cc['nordfiber_patch_panel']} "
                f"({cc['tenant_slug']}'s cross-connect into Nordfiber's network)"
            ),
            tenant=nordfiber_tenant.id,
        )

        nordfiber_patch_front = get_front_port(nb, nordfiber_patch, cc["nordfiber_patch_port"])
        nordfiber_switch_iface = get_interface(nb, nordfiber_switch, cc["nordfiber_switch_iface"])
        create_cable_if_needed(
            nb,
            nordfiber_patch_front, "dcim.frontport",
            nordfiber_switch_iface, "dcim.interface",
            status="connected",
            label=cc["cables"]["nordfiber_patch_to_switch"],
            comments=f"{cc['nordfiber_patch_panel']} <-> {cc['nordfiber_switch']} {cc['nordfiber_switch_iface']} (in-rack jumper)",
            tenant=nordfiber_tenant.id,
        )


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 11 (colo tenant cross-connects) complete.")
