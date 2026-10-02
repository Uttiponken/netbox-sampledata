#!/usr/bin/env python3
"""
Phase 19: Helsinki MeetMe room + lighting the two leased dark fiber pairs
(added post-hoc, 2026-10-01).

Fixes a gap found by the user while reviewing live data (Helsinki never
got a MeetMe room, unlike every other site) and lights the two dark fiber
circuits from Phase 17 (NSN-DF-0001, BFN-DF-0001) end to end. See
config.py's Phase 19 comment for the full confirmed design, including the
exact 8-segment trunk/jumper chain per circuit and the judgment call to
hand off each wavelength straight to a router port rather than through
the Phase 10 DCP-2/DCP-110 client shelf (that shelf is for external
customer demarc; these are Nordfiber's own internal backbone links).

Creates, in dependency order:
  2 fiber-vendor Tenants (Nordic Subsea Networks AB, Baltic Fibre Networks
  OU — previously Provider-only, same gap as Vastkust in Phase 13)
  -> Helsinki MeetMe Location + rack + 3 panels (Nordfiber's own + one per
     vendor) -> 2 new vendor panels in Stockholm's EXISTING MeetMe room
  -> 4 new WDM terminal devices (2 at Stockholm, 2 at Helsinki; reuses the
     existing WDM profile/device type/role, so each auto-gains all 40
     channels per Phase 14) -> Line ports
  -> per circuit: the full physical chain from muxponder to muxponder,
     then a direct client handoff to each end's router.

Depends on Phase 6 (WDM profile/device type), Phase 11/12 (MeetMe
pattern), Phase 13 (Suppliers tenant group), Phase 17 (the 2 dark fiber
circuits + Helsinki site). Safe to re-run.
"""

from common import (
    connect,
    create_cable_if_needed,
    get_front_port,
    get_interface,
    get_or_create,
    get_rear_port,
    report,
)
from config import (
    FIBER_VENDOR_TENANTS,
    HELSINKI_LIGHTING_CHAINS,
    HELSINKI_LIGHTING_WDM_NODES,
    HELSINKI_MEETME_LOCATION,
    HELSINKI_MEETME_PANELS,
    HELSINKI_MEETME_RACK,
    STOCKHOLM_MEETME_VENDOR_PANELS,
)


def run(nb):
    print("== Fiber vendor tenants ==")
    for t in FIBER_VENDOR_TENANTS:
        fields = dict(t)
        group_slug = fields.pop("group_slug")
        group = nb.tenancy.tenant_groups.get(slug=group_slug)
        obj, created = get_or_create(nb.tenancy.tenants, {"slug": fields["slug"]}, group=group.id, **fields)
        report("tenant", obj, created)

    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    sites = {s.slug: s for s in nb.dcim.sites.all()}

    print("== Helsinki MeetMe Location + rack ==")
    loc = HELSINKI_MEETME_LOCATION
    location, created = get_or_create(
        nb.dcim.locations, {"slug": loc["slug"]},
        name=loc["name"], slug=loc["slug"], site=sites[loc["site_slug"]].id,
    )
    report("location", location, created)

    r = HELSINKI_MEETME_RACK
    hel_mmr_rack, created = get_or_create(
        nb.dcim.racks, {"name": r["name"], "site_id": sites[r["site_slug"]].id},
        name=r["name"], site=sites[r["site_slug"]].id, location=location.id,
        tenant=tenants[r["tenant_slug"]].id, status="active", width=19, u_height=42,
    )
    report("rack", hel_mmr_rack, created)

    print("== Patch panel device type / role (reused from Phase 5) ==")
    panel_type = nb.dcim.device_types.get(slug="generic-lc-24-port-fiber-patch-panel")
    panel_role = nb.dcim.device_roles.get(slug="patch-panel")

    all_devices = {d.name: d for d in nb.dcim.devices.all()}

    print("== Helsinki MeetMe panels ==")
    for p in HELSINKI_MEETME_PANELS:
        obj, created = get_or_create(
            nb.dcim.devices, {"name": p["name"]},
            name=p["name"], device_type=panel_type.id, role=panel_role.id,
            site=sites["nordfiber-helsinki-dc"].id, location=location.id, rack=hel_mmr_rack.id,
            position=p["position"], face="front", tenant=tenants[p["tenant_slug"]].id, status="active",
        )
        report("device", obj, created)
        all_devices[p["name"]] = obj

    print("== Stockholm MeetMe vendor panels (existing room/rack) ==")
    sto_mmr_rack = nb.dcim.racks.get(name="STO-RACK-MMR1")
    sto_mmr_location = nb.dcim.locations.get(slug="stockholm-meetme-room")
    for p in STOCKHOLM_MEETME_VENDOR_PANELS:
        obj, created = get_or_create(
            nb.dcim.devices, {"name": p["name"]},
            name=p["name"], device_type=panel_type.id, role=panel_role.id,
            site=sites["nordfiber-stockholm-dc"].id, location=sto_mmr_location.id, rack=sto_mmr_rack.id,
            position=p["position"], face="front", tenant=tenants[p["tenant_slug"]].id, status="active",
        )
        report("device", obj, created)
        all_devices[p["name"]] = obj

    print("== New WDM terminal devices (reusing existing profile/device type/role) ==")
    wdm_device_type = nb.dcim.device_types.get(slug="smartoptics-dcp-m40-pam4-er")
    wdm_role = nb.dcim.device_roles.get(slug="wdm-terminal")
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}
    racks = {r.name: r for r in nb.dcim.racks.all()}
    for n in HELSINKI_LIGHTING_WDM_NODES:
        obj, created = get_or_create(
            nb.dcim.devices, {"name": n["name"]},
            name=n["name"], device_type=wdm_device_type.id, role=wdm_role.id,
            site=sites[n["site_slug"]].id, location=locations[n["location_slug"]].id,
            rack=racks[n["rack_name"]].id, position=n["position"], face="front",
            tenant=tenants[n["tenant_slug"]].id, status="active",
        )
        report("device", obj, created)
        all_devices[n["name"]] = obj

    print("== Line ports ==")
    for n in HELSINKI_LIGHTING_WDM_NODES:
        device = all_devices[n["name"]]
        wdm_node = nb.plugins.wdm.wdm_nodes.get(device_id=device.id)
        line_rear_port = get_rear_port(nb, device, "Line")
        existing = nb.plugins.wdm.wdm_line_ports.get(wdm_node_id=wdm_node.id, rear_port_id=line_rear_port.id)
        if existing:
            report("line port", existing, False)
        else:
            obj = nb.plugins.wdm.wdm_line_ports.create(
                wdm_node=wdm_node.id, rear_port=line_rear_port.id, direction="common", role="bidi",
            )
            report("line port", obj, True)

    print("== Lighting chains ==")
    nordfiber_tenant = tenants["nordfiber-ab"]
    sto_patch = all_devices.get("sto-patch-01") or nb.dcim.devices.get(name="sto-patch-01")
    hel_patch = all_devices.get("hel-patch-01") or nb.dcim.devices.get(name="hel-patch-01")
    sto_mmr_nordfiber = all_devices.get("sto-mmr-nordfiber-01") or nb.dcim.devices.get(name="sto-mmr-nordfiber-01")
    hel_mmr_nordfiber = all_devices["hel-mmr-nordfiber-01"]
    sto_rtr = all_devices.get("sto-rtr-01") or nb.dcim.devices.get(name="sto-rtr-01")
    hel_rtr = all_devices.get("hel-rtr-01") or nb.dcim.devices.get(name="hel-rtr-01")

    for chain in HELSINKI_LIGHTING_CHAINS:
        print(f"  -- {chain['circuit_cid']} --")
        vendor_tenant = tenants[chain["vendor_tenant_slug"]]
        sto_wdm = all_devices[chain["sto_wdm_node"]]
        hel_wdm = all_devices[chain["hel_wdm_node"]]
        sto_vendor_panel = all_devices[chain["sto_mmr_vendor_panel"]]
        hel_vendor_panel = all_devices[chain["hel_mmr_vendor_panel"]]
        cables = chain["cables"]

        # 1. sto-patch-01 (front) <-> sto-wdm:Line (rear) — WDM cross-connect
        sto_patch_front = get_front_port(nb, sto_patch, chain["sto_patch_port"])
        sto_wdm_line_rear = get_rear_port(nb, sto_wdm, "Line")
        create_cable_if_needed(
            nb, sto_patch_front, "dcim.frontport", sto_wdm_line_rear, "dcim.rearport",
            status="connected", label=cables["sto_patch_to_wdm"],
            comments=f"{chain['sto_wdm_node']} Line <-> sto-patch-01 {chain['sto_patch_port']} (WDM cross-connect)",
            tenant=nordfiber_tenant.id,
        )

        # 2. sto-patch-01 (rear) <-> sto-mmr-nordfiber-01 (rear) — trunk
        sto_patch_rear = get_rear_port(nb, sto_patch, chain["sto_patch_port"])
        sto_mmr_nf_rear = get_rear_port(nb, sto_mmr_nordfiber, chain["sto_mmr_nordfiber_port"])
        create_cable_if_needed(
            nb, sto_patch_rear, "dcim.rearport", sto_mmr_nf_rear, "dcim.rearport",
            status="connected", label=cables["sto_patch_to_mmr_nordfiber"],
            comments="sto-patch-01 <-> sto-mmr-nordfiber-01 (trunk, telecom room to MeetMe room)",
            tenant=nordfiber_tenant.id,
        )

        # 3. sto-mmr-nordfiber-01 (front) <-> sto-mmr-<vendor>-01 (front) — jumper
        sto_mmr_nf_front = get_front_port(nb, sto_mmr_nordfiber, chain["sto_mmr_nordfiber_port"])
        sto_vendor_front = get_front_port(nb, sto_vendor_panel, chain["sto_mmr_vendor_port"])
        create_cable_if_needed(
            nb, sto_mmr_nf_front, "dcim.frontport", sto_vendor_front, "dcim.frontport",
            status="connected", label=cables["sto_mmr_nordfiber_to_vendor"],
            comments=f"sto-mmr-nordfiber-01 <-> {chain['sto_mmr_vendor_panel']} (cross-connect jumper, MeetMe room)",
            tenant=nordfiber_tenant.id,
        )

        # 4. The leased fiber span itself: sto-mmr-<vendor>-01 (rear) <->
        # hel-mmr-<vendor>-01 (rear), a real direct Cable spanning both
        # cities — same pattern as bb-cbl-00001/2/3 modeling Nordfiber's
        # own backbone fiber. The Circuit's own CircuitTerminations stay
        # UNCABLED (matching PLT-100234); they're a billing record, not
        # part of the physical cable graph.
        sto_vendor_rear = get_rear_port(nb, sto_vendor_panel, chain["sto_mmr_vendor_port"])
        hel_vendor_rear = get_rear_port(nb, hel_vendor_panel, chain["hel_mmr_vendor_port"])
        create_cable_if_needed(
            nb, sto_vendor_rear, "dcim.rearport", hel_vendor_rear, "dcim.rearport",
            status="connected", label=cables["vendor_span"], type="smf-os2",
            comments=f"{chain['circuit_cid']}: leased fiber span, {chain['sto_mmr_vendor_panel']} <-> {chain['hel_mmr_vendor_panel']}",
            tenant=vendor_tenant.id,
        )

        # 6. hel-mmr-<vendor>-01 (front) <-> hel-mmr-nordfiber-01 (front) — jumper
        hel_vendor_front = get_front_port(nb, hel_vendor_panel, chain["hel_mmr_vendor_port"])
        hel_mmr_nf_front = get_front_port(nb, hel_mmr_nordfiber, chain["hel_mmr_nordfiber_port"])
        create_cable_if_needed(
            nb, hel_vendor_front, "dcim.frontport", hel_mmr_nf_front, "dcim.frontport",
            status="connected", label=cables["hel_mmr_vendor_to_nordfiber"],
            comments=f"{chain['hel_mmr_vendor_panel']} <-> hel-mmr-nordfiber-01 (cross-connect jumper, MeetMe room)",
            tenant=nordfiber_tenant.id,
        )

        # 7. hel-mmr-nordfiber-01 (rear) <-> hel-patch-01 (rear) — trunk
        hel_mmr_nf_rear = get_rear_port(nb, hel_mmr_nordfiber, chain["hel_mmr_nordfiber_port"])
        hel_patch_rear = get_rear_port(nb, hel_patch, chain["hel_patch_port"])
        create_cable_if_needed(
            nb, hel_mmr_nf_rear, "dcim.rearport", hel_patch_rear, "dcim.rearport",
            status="connected", label=cables["hel_mmr_nordfiber_to_patch"],
            comments="hel-mmr-nordfiber-01 <-> hel-patch-01 (trunk, MeetMe room to telecom room)",
            tenant=nordfiber_tenant.id,
        )

        # 8. hel-patch-01 (front) <-> hel-wdm:Line (rear) — WDM cross-connect
        hel_patch_front = get_front_port(nb, hel_patch, chain["hel_patch_port"])
        hel_wdm_line_rear = get_rear_port(nb, hel_wdm, "Line")
        create_cable_if_needed(
            nb, hel_patch_front, "dcim.frontport", hel_wdm_line_rear, "dcim.rearport",
            status="connected", label=cables["hel_patch_to_wdm"],
            comments=f"{chain['hel_wdm_node']} Line <-> hel-patch-01 {chain['hel_patch_port']} (WDM cross-connect)",
            tenant=nordfiber_tenant.id,
        )

        # Client handoffs: each muxponder's lit channel straight to a router port.
        sto_wdm_client_port = get_front_port(nb, sto_wdm, chain["channel_front_port"])
        sto_rtr_iface = get_interface(nb, sto_rtr, chain["sto_router_iface"])
        create_cable_if_needed(
            nb, sto_wdm_client_port, "dcim.frontport", sto_rtr_iface, "dcim.interface",
            status="connected", label=cables["sto_wdm_client"],
            comments=f"{chain['sto_wdm_node']} channel {chain['channel_front_port']} <-> sto-rtr-01 {chain['sto_router_iface']} (internal backbone handoff)",
            tenant=nordfiber_tenant.id,
        )

        hel_wdm_client_port = get_front_port(nb, hel_wdm, chain["channel_front_port"])
        hel_rtr_iface = get_interface(nb, hel_rtr, chain["hel_router_iface"])
        create_cable_if_needed(
            nb, hel_wdm_client_port, "dcim.frontport", hel_rtr_iface, "dcim.interface",
            status="connected", label=cables["hel_wdm_client"],
            comments=f"{chain['hel_wdm_node']} channel {chain['channel_front_port']} <-> hel-rtr-01 {chain['hel_router_iface']} (internal backbone handoff)",
            tenant=nordfiber_tenant.id,
        )


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 19 (Helsinki MeetMe room + DWDM lighting) complete.")
