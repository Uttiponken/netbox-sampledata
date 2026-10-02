#!/usr/bin/env python3
"""
Phase 8: Baltic Retail Group backup path (added post-hoc, 2026-09-27).

A DWDM-based protect path for circuit NF-BRG-0001, routed Stockholm <->
Gothenburg <-> Malmo instead of a second direct fiber run. See config.py's
Phase 8 comment block for the full design rationale (terminal mux vs
ROADM, electrical regeneration at Gothenburg, router client handoff).

Creates, in dependency order:
  bb-cbl-00004 (Gothenburg <-> Malmo backbone fiber, FMS-decorated)
  -> second WDM channel-plan entry (grid_position 2) on the existing
     shared WDM profile -> 4 new WDM terminal devices (auto-instantiates
     WdmNodes + channels, including a NEW channel 2 slot on the two
     already-existing Stockholm/Oslo nodes too — harmless spare capacity)
  -> line ports -> line cross-connects to patch panels
  -> Gothenburg regeneration jumper (got-wdm-01 <-> got-wdm-02, client
     port to client port)
  -> client cross-connects to sto-rtr-01 / mma-rtr-01
  -> commercial circuit NF-BRG-0002 (uncabled terminations)
  -> two WdmCircuits, one per regenerated segment, each stitched using
     the wavelength_path_id read off a representative channel's own
     /trace/ action (grid_position alone can't disambiguate the two
     segments — see inline comment below).

Depends on Phase 4 (circuit types/providers), Phase 5 (FMS cable type,
patch panels), Phase 6 (WDM profile/device type/device role). Requires
netbox-fms and netbox-wdm. Safe to re-run.
"""

from common import (
    call_plugin_action,
    connect,
    create_cable_if_needed,
    create_device_type_from_yaml,
    create_fiber_cable_if_needed,
    fetch_devicetype_yaml,
    get_front_port,
    get_interface,
    get_or_create,
    get_rear_port,
    report,
)
from config import (
    BACKUP_CIRCUIT,
    BACKUP_WDM_CHANNEL_PLAN_ENTRY,
    BACKUP_WDM_CIRCUITS,
    BACKUP_WDM_CLIENT_CROSS_CONNECTS,
    BACKUP_WDM_NODES,
    FMS_CABLE_TYPE,
    FMS_DEVICE_TYPE_SOURCES,
    FMS_MANUFACTURERS,
    GOTHENBURG_REGEN_JUMPER,
    NEW_BACKBONE_FIBER_CABLE,
    WDM_DEVICE_ROLES,
    WDM_DEVICE_TYPE_SOURCES,
    WDM_MANUFACTURERS,
    WDM_PROFILE,
)


def run(nb):
    sites = {s.slug: s for s in nb.dcim.sites.all()}
    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}
    racks = {r.name: r for r in nb.dcim.racks.all()}

    print("== Backbone fiber: Gothenburg <-> Malmo (bb-cbl-00004) ==")
    fms_manufacturers = {}
    for m in FMS_MANUFACTURERS:
        obj, created = get_or_create(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        fms_manufacturers[m["name"]] = obj
    ct_fields = dict(FMS_CABLE_TYPE)
    mfr_name = ct_fields.pop("manufacturer_name")
    cable_type, _ = get_or_create(
        nb.plugins.fms.cable_types,
        {"model": ct_fields["model"]},
        manufacturer=fms_manufacturers[mfr_name].id,
        **ct_fields,
    )

    fc = NEW_BACKBONE_FIBER_CABLE
    a_dev = nb.dcim.devices.get(name=fc["a_device"])
    b_dev = nb.dcim.devices.get(name=fc["b_device"])
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
    create_fiber_cable_if_needed(nb, dcim_cable, cable_type, notes=fc["fms_notes"])

    print("== WDM manufacturer / device type / profile (re-established, already exist) ==")
    wdm_manufacturers = {}
    for m in WDM_MANUFACTURERS:
        obj, created = get_or_create(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        wdm_manufacturers[m["name"]] = obj
    device_type = None
    for mfr_name, path in WDM_DEVICE_TYPE_SOURCES:
        yaml_data = fetch_devicetype_yaml(path)
        device_type = create_device_type_from_yaml(nb, wdm_manufacturers, yaml_data)
    profile, _ = get_or_create(
        nb.plugins.wdm.wdm_profiles,
        {"device_type_id": device_type.id},
        device_type=device_type.id,
        **WDM_PROFILE,
    )

    print("== Second WDM channel-plan entry (grid_position 2) ==")
    entry = BACKUP_WDM_CHANNEL_PLAN_ENTRY
    front_port_template = nb.dcim.front_port_templates.get(
        devicetype_id=device_type.id, name=entry["front_port_name"]
    )
    existing = nb.plugins.wdm.wdm_channel_plans.get(profile_id=profile.id, grid_position=entry["grid_position"])
    if existing:
        report("channel plan entry", existing, False)
    else:
        obj = nb.plugins.wdm.wdm_channel_plans.create(
            profile=profile.id,
            grid_position=entry["grid_position"],
            # Unlike WdmChannel, a WdmChannelPlan's wavelength_nm is NOT
            # overridden by the plugin — it's stored as given, and the DB
            # enforces uniqueness on (profile, wavelength_nm), not
            # (profile, grid_position). The existing grid_position=1 entry
            # already occupies the 1550.0 placeholder, so this one needs
            # its own distinct placeholder value.
            wavelength_nm=1550.0 + entry["grid_position"],
            label="placeholder",
            mux_front_port_template=front_port_template.id,
            demux_front_port_template=front_port_template.id,
        )
        report("channel plan entry", obj, True)

    device_roles = {}
    for r in WDM_DEVICE_ROLES:
        obj, created = get_or_create(nb.dcim.device_roles, {"slug": r["slug"]}, **r)
        device_roles[r["slug"]] = obj

    print("== Backup WDM terminal devices ==")
    devices = {}
    for n in BACKUP_WDM_NODES:
        obj, created = get_or_create(
            nb.dcim.devices,
            {"name": n["name"]},
            name=n["name"],
            device_type=device_type.id,
            role=device_roles["wdm-terminal"].id,
            site=sites[n["site_slug"]].id,
            location=locations[n["location_slug"]].id,
            rack=racks[n["rack_name"]].id,
            position=n["position"],
            face="front",
            tenant=tenants[n["tenant_slug"]].id,
            status="active",
        )
        report("device", obj, created)
        devices[n["name"]] = obj

    print("== Line ports ==")
    for n in BACKUP_WDM_NODES:
        device = devices[n["name"]]
        wdm_node = nb.plugins.wdm.wdm_nodes.get(device_id=device.id)
        line_rear_port = nb.dcim.rear_ports.get(device_id=device.id, name="Line")
        existing = nb.plugins.wdm.wdm_line_ports.get(wdm_node_id=wdm_node.id, rear_port_id=line_rear_port.id)
        if existing:
            report("line port", existing, False)
        else:
            obj = nb.plugins.wdm.wdm_line_ports.create(
                wdm_node=wdm_node.id,
                rear_port=line_rear_port.id,
                direction="common",
                role="bidi",
            )
            report("line port", obj, True)

    print("== Physical cross-connect: WDM Line port <-> patch panel front port ==")
    for n in BACKUP_WDM_NODES:
        device = devices[n["name"]]
        line_rear_port = nb.dcim.rear_ports.get(device_id=device.id, name="Line")
        patch_panel = nb.dcim.devices.get(name=n["patch_panel"])
        front_port = nb.dcim.front_ports.get(device_id=patch_panel.id, name=n["patch_panel_front_port"])
        create_cable_if_needed(
            nb,
            front_port, "dcim.frontport",
            line_rear_port, "dcim.rearport",
            status="connected",
            label=f"{n['name']}-line",
            comments=f"{n['name']} Line <-> {n['patch_panel']} {n['patch_panel_front_port']} (WDM cross-connect)",
            tenant=tenants["nordfiber-ab"].id,
        )

    print("== Gothenburg regeneration jumper ==")
    j = GOTHENBURG_REGEN_JUMPER
    a_port = get_front_port(nb, devices[j["a_device"]], j["a_front_port"])
    b_port = get_front_port(nb, devices[j["b_device"]], j["b_front_port"])
    create_cable_if_needed(
        nb,
        a_port, "dcim.frontport",
        b_port, "dcim.frontport",
        status="connected",
        label=j["label"],
        comments=j["comments"],
        tenant=tenants[j["tenant_slug"]].id,
    )

    print("== Client cross-connects to routers ==")
    for cc in BACKUP_WDM_CLIENT_CROSS_CONNECTS:
        wdm_front_port = get_front_port(nb, devices[cc["wdm_node"]], cc["wdm_front_port"])
        router = nb.dcim.devices.get(name=cc["router"])
        router_iface = get_interface(nb, router, cc["router_iface"])
        create_cable_if_needed(
            nb,
            wdm_front_port, "dcim.frontport",
            router_iface, "dcim.interface",
            status="connected",
            label=cc["label"],
            comments=(
                f"{cc['wdm_node']} channel {cc['wdm_front_port']} <-> {cc['router']} "
                f"{cc['router_iface']} (backup-path client handoff)"
            ),
            tenant=tenants["nordfiber-ab"].id,
        )

    print("== Commercial circuit NF-BRG-0002 (uncabled terminations) ==")
    provider = nb.circuits.providers.get(slug=BACKUP_CIRCUIT["provider_slug"])
    circuit_type = nb.circuits.circuit_types.get(slug=BACKUP_CIRCUIT["type_slug"])
    circuit, created = get_or_create(
        nb.circuits.circuits,
        {"cid": BACKUP_CIRCUIT["cid"]},
        cid=BACKUP_CIRCUIT["cid"],
        provider=provider.id,
        type=circuit_type.id,
        tenant=tenants[BACKUP_CIRCUIT["tenant_slug"]].id,
        status=BACKUP_CIRCUIT["status"],
        commit_rate=BACKUP_CIRCUIT["commit_rate"],
        description=BACKUP_CIRCUIT["description"],
    )
    report("circuit", circuit, created)
    for t in BACKUP_CIRCUIT["terminations"]:
        site = sites[t["site_slug"]]
        term = nb.circuits.circuit_terminations.get(circuit_id=circuit.id, term_side=t["term_side"])
        if term is None:
            term = nb.circuits.circuit_terminations.create(
                circuit=circuit.id,
                term_side=t["term_side"],
                termination_type="dcim.site",
                termination_id=site.id,
                port_speed=BACKUP_CIRCUIT["commit_rate"],
            )
            print(f"  [created] termination {t['term_side']}: {site.name} (id={term.id})")
        else:
            print(f"  [exists ] termination {t['term_side']}: {site.name} (id={term.id})")

    print("== Backup WdmCircuits (one per regenerated segment) ==")
    for wc in BACKUP_WDM_CIRCUITS:
        circuit, created = get_or_create(
            nb.plugins.wdm.wdm_circuits,
            {"name": wc["name"]},
            name=wc["name"],
            tenant=tenants[wc["tenant_slug"]].id,
            status=wc["status"],
            description=wc["description"],
        )
        report("wdm circuit", circuit, created)

        # Both segments share grid_position 2, so a plain
        # wdm-wavelength-paths lookup can't tell them apart (the object
        # itself carries no node/device reference — see docs/DESIGN.md).
        # Instead, trace the specific channel belonging to this segment's
        # first device: /trace/ returns the exact wavelength_path_id for
        # the path that channel is actually part of.
        anchor_device_name = wc["segment_devices"][0]
        anchor_device = devices[anchor_device_name]
        anchor_node = nb.plugins.wdm.wdm_nodes.get(device_id=anchor_device.id)
        anchor_channel = nb.plugins.wdm.wdm_channels.get(
            wdm_node_id=anchor_node.id, grid_position=entry["grid_position"]
        )
        trace = call_plugin_action(f"/api/plugins/wdm/wdm-channels/{anchor_channel.id}/trace/")
        path_id = trace["wavelength_path_id"]
        traced_nodes = {el["node_name"] for el in trace["elements"]}
        expected_nodes = set(wc["segment_devices"])
        if traced_nodes != expected_nodes:
            raise SystemExit(
                f"Trace from {anchor_device_name}'s channel {anchor_channel.id} covers "
                f"{traced_nodes}, expected exactly {expected_nodes} for {wc['name']!r} — "
                "physical wiring for this segment looks incomplete or crossed."
            )

        existing_path_ids = [p if isinstance(p, int) else p.id for p in (circuit.wavelength_paths or [])]
        if path_id not in existing_path_ids:
            circuit.wavelength_paths = existing_path_ids + [path_id]
            circuit.save()
            print(f"  attached wavelength path id={path_id} to circuit")
        else:
            print(f"  wavelength path id={path_id} already attached")

        stitched = call_plugin_action(f"/api/plugins/wdm/wdm-circuits/{circuit.id}/stitch/")
        print(f"  stitch result: {stitched}")


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 8 (Baltic Retail Group backup path) complete.")
