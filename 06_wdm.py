#!/usr/bin/env python3
"""
Phase 6: WDM.

Lights the Stockholm <-> Oslo leased dark fiber (bb-cbl-003, Phase 5) with
a real SmartOptics muxponder at each end, and reserves ITU channel 21 for
Fjord Media Networks' wavelength service.

Order matters here more than in earlier phases: the WDM profile and its
channel-plan entry must exist BEFORE the devices are created, because
creating a device of a profiled device type auto-instantiates a matching
WdmNode, which in turn auto-instantiates WdmChannels from the profile's
channel-plan (verified empirically — see docs/DESIGN.md). Create the
devices too early and no channels appear.

Depends on Phase 1 (sites/tenants), Phase 2 (racks), Phase 4 (circuit
PLT-100234, referenced only in description text), Phase 5 (patch panels
and their front ports, first used here). Requires the netbox-wdm plugin.
Safe to re-run.
"""

from common import call_plugin_action, connect, create_cable_if_needed, create_device_type_from_yaml, fetch_devicetype_yaml, get_or_create, report
from config import (
    WDM_CHANNEL_PLAN,
    WDM_CIRCUIT,
    WDM_CLIENT_CROSS_CONNECTS,
    WDM_DEVICE_ROLES,
    WDM_DEVICE_TYPE_SOURCES,
    WDM_MANUFACTURERS,
    WDM_NODES,
    WDM_PROFILE,
)


def run(nb):
    print("== Manufacturers ==")
    manufacturers = {}
    for m in WDM_MANUFACTURERS:
        obj, created = get_or_create(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        report("manufacturer", obj, created)
        manufacturers[m["name"]] = obj

    print("== WDM terminal device type (fetched from the real devicetype-library) ==")
    device_type = None
    for mfr_name, path in WDM_DEVICE_TYPE_SOURCES:
        yaml_data = fetch_devicetype_yaml(path)
        device_type = create_device_type_from_yaml(nb, manufacturers, yaml_data)

    print("== WDM profile (ties the device type to a channel grid) ==")
    profile, created = get_or_create(
        nb.plugins.wdm.wdm_profiles,
        {"device_type_id": device_type.id},
        device_type=device_type.id,
        **WDM_PROFILE,
    )
    report("wdm profile", profile, created)

    print("== WDM channel plan ==")
    for entry in WDM_CHANNEL_PLAN:
        front_port_template = nb.dcim.front_port_templates.get(
            devicetype_id=device_type.id, name=entry["front_port_name"]
        )
        existing = nb.plugins.wdm.wdm_channel_plans.get(profile_id=profile.id, grid_position=entry["grid_position"])
        if existing:
            report("channel plan entry", existing, False)
            continue
        obj = nb.plugins.wdm.wdm_channel_plans.create(
            profile=profile.id,
            grid_position=entry["grid_position"],
            wavelength_nm=1550.0,  # placeholder — the plugin computes and overrides the real ITU value
            label="placeholder",  # ditto
            mux_front_port_template=front_port_template.id,
            demux_front_port_template=front_port_template.id,
        )
        report("channel plan entry", obj, True)

    print("== Device role ==")
    device_roles = {}
    for r in WDM_DEVICE_ROLES:
        obj, created = get_or_create(nb.dcim.device_roles, {"slug": r["slug"]}, **r)
        report("device role", obj, created)
        device_roles[r["slug"]] = obj

    sites = {s.slug: s for s in nb.dcim.sites.all()}
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}
    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    racks = {r.name: r for r in nb.dcim.racks.all()}

    print("== WDM terminal devices (auto-instantiates a WdmNode + channels each) ==")
    devices = {}
    for n in WDM_NODES:
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

    print("== Line ports (marks each node's Line rear port as the outside-facing port) ==")
    for n in WDM_NODES:
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
    for n in WDM_NODES:
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
            # Nordfiber's own shared WDM equipment — only 1 of the muxponder's
            # 40 channels is Fjord Media's; the other 39 are spare capacity
            # Nordfiber could sell to anyone, so this cable isn't Fjord's.
            tenant=tenants["nordfiber-ab"].id,
        )

    print("== Physical cross-connect: WDM client port <-> site switch ==")
    for cc in WDM_CLIENT_CROSS_CONNECTS:
        wdm_device = devices[cc["wdm_node"]]
        wdm_front_port = nb.dcim.front_ports.get(device_id=wdm_device.id, name=cc["wdm_front_port"])
        switch = nb.dcim.devices.get(name=cc["switch"])
        switch_iface = nb.dcim.interfaces.get(device_id=switch.id, name=cc["switch_iface"])
        create_cable_if_needed(
            nb,
            wdm_front_port, "dcim.frontport",
            switch_iface, "dcim.interface",
            status="connected",
            label=cc["label"],
            comments=(
                f"{cc['wdm_node']} channel {cc['wdm_front_port']} <-> {cc['switch']} "
                f"{cc['switch_iface']} (wavelength-service client handoff)"
            ),
            tenant=tenants["nordfiber-ab"].id,
        )

    print("== WDM circuit for Fjord Media Networks ==")
    circuit, created = get_or_create(
        nb.plugins.wdm.wdm_circuits,
        {"name": WDM_CIRCUIT["name"]},
        name=WDM_CIRCUIT["name"],
        tenant=tenants[WDM_CIRCUIT["tenant_slug"]].id,
        status=WDM_CIRCUIT["status"],
        description=WDM_CIRCUIT["description"],
    )
    report("wdm circuit", circuit, created)

    # WdmWavelengthPath objects are discovered/computed by the plugin
    # itself once both ends' channels are wired up (confirmed via each
    # channel's own /trace/ action) — but attaching one to a WdmCircuit is
    # a separate, manual step; the circuit doesn't auto-discover paths on
    # its own.
    #
    # netbox-wdm 0.2.2 re-runs this discovery whenever a cable anywhere in
    # the WDM topology is saved — including for an unrelated field change
    # (confirmed live: patching only the `tenant` field on the WDM
    # cross-connect cables spawned a SECOND WdmWavelengthPath for the same
    # grid_position, timestamped exactly at that save, alongside the
    # original — rather than recognizing the path already existed). So
    # `.get(grid_position=...)` isn't safe here; there may be more than
    # one candidate. Prefer whichever is already attached to this circuit
    # (stable across re-runs); only fall back to picking one when nothing
    # is attached yet, deterministically (lowest id = oldest = the one
    # originally verified), and warn if there's more than one to attach
    # from, since that itself is a symptom of this upstream quirk.
    existing_path_ids = [p if isinstance(p, int) else p.id for p in (circuit.wavelength_paths or [])]
    candidates = list(nb.plugins.wdm.wdm_wavelength_paths.filter(grid_position=WDM_CIRCUIT["grid_position"]))
    if not candidates:
        raise SystemExit(
            f"No WdmWavelengthPath found for grid_position={WDM_CIRCUIT['grid_position']} — "
            "the channels may not be physically complete yet."
        )
    attached = [p for p in candidates if p.id in existing_path_ids]
    if attached:
        path = attached[0]
    else:
        path = min(candidates, key=lambda p: p.id)
        if len(candidates) > 1:
            print(
                f"  WARNING: {len(candidates)} WdmWavelengthPath candidates for "
                f"grid_position={WDM_CIRCUIT['grid_position']} (ids={[p.id for p in candidates]}) — "
                f"known netbox-wdm 0.2.2 duplicate-discovery quirk (see docs/DESIGN.md). "
                f"Using id={path.id}; consider deleting the others manually."
            )
    if path.id not in existing_path_ids:
        circuit.wavelength_paths = existing_path_ids + [path.id]
        circuit.save()
        print(f"  attached wavelength path id={path.id} to circuit")
    else:
        print(f"  wavelength path id={path.id} already attached")

    print("== Stitching the end-to-end wavelength path ==")
    stitched = call_plugin_action(f"/api/plugins/wdm/wdm-circuits/{circuit.id}/stitch/")
    print(f"  stitch result: {stitched}")


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 6 (WDM) complete.")
