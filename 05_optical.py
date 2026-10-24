#!/usr/bin/env python3
"""
Layer 5: optical — WDM line ports and cabling, client demarc shelves,
backbone handoffs, and the wavelength services (netbox-wdm WdmCircuits).

  WdmLinePort per node -> patch panel <-> Line cables -> channel <-> DCP-2
  line ports -> DCP-2 client <-> tenant equipment -> direct router handoffs
  -> Gothenburg regeneration jumper -> WdmCircuits (path attached, stitched)

netbox-wdm re-discovers wavelength paths whenever a cable in the topology is
saved and creates duplicates; layer 7 prunes them. Its /trace/ also cannot
walk the front-to-front MeetMe jumpers, so the Helsinki links are not
traceable by the plugin — verify.py checks them by walking the cables.

The cabling is core NetBox and always loaded; the WDM line ports, wavelength services and channel status
need netbox-wdm and are skipped without it.

Requires layers 1-4. Safe to re-run.
"""

from cabling import F, I, R, Cabler
from common import api, connect, ensure, have, report, skip
from data import optical as O
from data.organization import TENANTS


def line_ports(nb):
    print("== WDM line ports ==")
    for name in O.LINE_PATCH:
        dev = nb.dcim.devices.get(name=name)
        node = nb.plugins.wdm.wdm_nodes.get(device_id=dev.id)
        rear = nb.dcim.rear_ports.get(device_id=dev.id, name="Line")
        lp = nb.plugins.wdm.wdm_line_ports.get(wdm_node_id=node.id, rear_port_id=rear.id)
        if lp is None:
            lp = nb.plugins.wdm.wdm_line_ports.create(wdm_node=node.id, rear_port=rear.id, direction="common", role="bidi")
            report("line port", lp, "created", name)
        else:
            report("line port", lp, "exists", name)


def cabling(nb, cabler):
    print("== Patch panel <-> Line ==")
    for wdm, (patch, port) in O.LINE_PATCH.items():
        cabler.connect(F(patch, f"Port {port}"), R(wdm, "Line"), note=f"{wdm} line to {patch}")
    print("== Muxponder channel <-> DCP-2 line ==")
    for wdm, ch, shelf, line in O.SHELF_LINE:
        cabler.connect(F(wdm, ch), I(shelf, line), note=f"{wdm} channel {ch} to {shelf} DCP-110 line side")
    print("== DCP-2 client <-> tenant equipment ==")
    for shelf, client, far in O.SHELF_CLIENT:
        cabler.connect(I(shelf, client), far, note=f"{shelf} grey client handoff")
    print("== Direct backbone handoffs ==")
    for wdm, ch, rtr, iface in O.DIRECT_HANDOFF:
        cabler.connect(F(wdm, ch), I(rtr, iface), note=f"{wdm} channel {ch} to router (backbone link)")
    print("== Regeneration jumper ==")
    a, ach, b, bch = O.REGEN_JUMPER
    cabler.connect(F(a, ach), F(b, bch), note="regeneration: Stockholm-facing (north route) to Malmö-facing muxponder")


def wdm_circuits(nb):
    print("== WDM circuits ==")
    tenants = {t["code"]: nb.tenancy.tenants.get(slug=t["slug"]) for t in TENANTS}
    for wc in O.WDM_CIRCUITS:
        circuit, st = ensure(nb.plugins.wdm.wdm_circuits, {"name": wc["name"]}, name=wc["name"],
                             tenant=tenants[wc["tenant"]].id, status="active", description=wc["description"])
        report("wdm circuit", circuit, st)

        anchor = nb.dcim.devices.get(name=wc["nodes"][0])
        node = nb.plugins.wdm.wdm_nodes.get(device_id=anchor.id)
        channel = nb.plugins.wdm.wdm_channels.get(wdm_node_id=node.id, grid_position=wc["channel"])
        trace = api(f"/api/plugins/wdm/wdm-channels/{channel.id}/trace/")
        traced = {el["node_name"] for el in trace["elements"]}
        if traced != set(wc["nodes"]) or not trace["wavelength_path_id"]:
            raise SystemExit(f"{wc['name']}: trace from {wc['nodes'][0]} covers {traced}, expected {set(wc['nodes'])}")
        path_id = trace["wavelength_path_id"]

        attached = [p if isinstance(p, int) else p.id for p in (circuit.wavelength_paths or [])]
        if path_id not in attached:
            circuit.wavelength_paths = attached + [path_id]
            circuit.save()
            print(f"  attached wavelength path {path_id}")
        res = api(f"/api/plugins/wdm/wdm-circuits/{circuit.id}/stitch/")
        states = [(p["is_complete"], p["is_active"]) for p in res["paths"]]
        print(f"  stitch: {states}")
        if not states or not all(c and a for c, a in states):
            raise SystemExit(f"{wc['name']} does not stitch complete")


def activate_channels(nb):
    """A channel whose client port is cabled (or jumpered) is in service: mark it Active, not Available."""
    print("== Channel status ==")
    used = {(w, int(ch) - 920) for w, ch, _s, _l in O.SHELF_LINE}
    used |= {(w, int(ch) - 920) for w, ch, _r, _i in O.DIRECT_HANDOFF}
    used |= {(O.REGEN_JUMPER[0], int(O.REGEN_JUMPER[1]) - 920), (O.REGEN_JUMPER[2], int(O.REGEN_JUMPER[3]) - 920)}
    for name, position in sorted(used):
        node = nb.plugins.wdm.wdm_nodes.get(device_id=nb.dcim.devices.get(name=name).id)
        channel = nb.plugins.wdm.wdm_channels.get(wdm_node_id=node.id, grid_position=position)
        if str(channel.status.value if hasattr(channel.status, "value") else channel.status) != "active":
            channel.update({"status": "active"})
            print(f"  [updated] {name} channel {position}: active")
        else:
            print(f"  [exists ] {name} channel {position}: active")


def run(nb):
    wdm = have("wdm")
    if wdm:
        line_ports(nb)
    else:
        skip("wdm", "WDM line ports")
    cabler = Cabler(nb)
    cabling(nb, cabler)
    cabler.summary()
    if wdm:
        wdm_circuits(nb)
        activate_channels(nb)
    else:
        skip("wdm", "wavelength services (WDM circuits) and channel status")


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nLayer 5 (optical) complete.")
