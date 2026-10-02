#!/usr/bin/env python3
"""
Phase 14: full 40-channel WDM plan (added post-hoc, 2026-09-27).

Populates grid_position 3 through 40 on the shared WDM profile — only 1
(Fjord Media, Phase 6) and 2 (Baltic Retail backup, Phase 8) existed
before this. The muxponder device type genuinely has 40 channel front
ports ("921" through "960"), so this gives every existing WDM node its
full, real capacity.

IMPORTANT correction vs. Phase 6/8's own assumption: adding a
channel-plan entry to the profile does NOT retroactively instantiate a
WdmChannel on nodes that already exist — that only happens at DEVICE
CREATION time, built from whatever channel-plan entries exist on the
profile at that moment (confirmed empirically here: after adding
grid_position 3-40 to the profile, every pre-existing node still showed
only its original 1-2 channels). So this phase does two things: adds the
remaining channel-plan entries (metadata NetBox needs to compute each
channel's real ITU wavelength), AND explicitly creates the missing
WdmChannel on every EXISTING node for every grid_position it doesn't
already have — each one pointing at that node's own already-instantiated
front port (e.g. "923" for grid_position 3), not a device-type template.
Posting a WdmChannel this way still gets the real computed ITU
wavelength/label (confirmed: grid_position 2 posted with no wavelength_nm
came back as "C22 (1559.79nm)", identical to one created via normal
device creation) — this phase does not create or cable any new node, it
just fills in the rest of the channel plan as unlit spare capacity,
identical in kind to how channels 1/2 already sit unused on every node
except the one pair each is actually cabled to.

Depends on Phase 6 (WDM profile/device type already exist). Safe to
re-run.
"""

from common import connect, fetch_devicetype_yaml, create_device_type_from_yaml, get_or_create, report
from config import WDM_DEVICE_TYPE_SOURCES, WDM_MANUFACTURERS, WDM_PROFILE, WDM_REMAINING_CHANNEL_PLAN


def run(nb):
    print("== WDM manufacturer / device type / profile (re-established, already exist) ==")
    manufacturers = {}
    for m in WDM_MANUFACTURERS:
        obj, created = get_or_create(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        manufacturers[m["name"]] = obj
    device_type = None
    for mfr_name, path in WDM_DEVICE_TYPE_SOURCES:
        yaml_data = fetch_devicetype_yaml(path)
        device_type = create_device_type_from_yaml(nb, manufacturers, yaml_data)
    profile, _ = get_or_create(
        nb.plugins.wdm.wdm_profiles,
        {"device_type_id": device_type.id},
        device_type=device_type.id,
        **WDM_PROFILE,
    )

    print("== Remaining channel-plan entries (grid_position 3-40) ==")
    for entry in WDM_REMAINING_CHANNEL_PLAN:
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
            wavelength_nm=entry["wavelength_nm"],
            label="placeholder",
            mux_front_port_template=front_port_template.id,
            demux_front_port_template=front_port_template.id,
        )
        report("channel plan entry", obj, True)

    print("== Filling in the missing WdmChannel on every EXISTING node ==")
    all_grid_positions = [1, 2] + [e["grid_position"] for e in WDM_REMAINING_CHANNEL_PLAN]
    for node in nb.plugins.wdm.wdm_nodes.all():
        device_id = node.device.id if hasattr(node.device, "id") else node.device
        device = nb.dcim.devices.get(id=device_id)
        if device.device_type.id != device_type.id:
            continue  # not one of our muxponders
        existing_positions = {c.grid_position for c in nb.plugins.wdm.wdm_channels.filter(wdm_node_id=node.id)}
        for gp in all_grid_positions:
            if gp in existing_positions:
                continue
            front_port_name = str(920 + gp)
            fp = nb.dcim.front_ports.get(device_id=device.id, name=front_port_name)
            chan = nb.plugins.wdm.wdm_channels.create(
                wdm_node=node.id,
                grid_position=gp,
                mux_front_port=fp.id,
                demux_front_port=fp.id,
            )
            print(f"  [created] channel: {device.name} grid_position={gp} ({chan.label}, {chan.wavelength_nm}nm)")


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 14 (full 40-channel WDM plan) complete.")
