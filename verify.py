#!/usr/bin/env python3
"""
Read-only invariant check of the built dataset. Exits non-zero on any failure.

    python verify.py

It checks the things the audit found wrong by hand, so they cannot silently
regress: every site looks like its siblings, every cable carries its full set
of attributes, every planned connection exists, physical paths are continuous
(walked cable by cable, since netbox-wdm cannot trace the Helsinki links),
route geometry agrees with the cable it belongs to, and no stale text
survived.
"""

import math
import re
import sys

import layout
from common import connect
from data import cabling as C
from data import hardware as H
from data import optical as O
from data import transport as T
from data.organization import SITES

FAILS = []
PASSED = 0


def check(name, ok, detail=""):
    global PASSED
    if ok:
        PASSED += 1
        print(f"  ok    {name}")
    else:
        FAILS.append(name)
        print(f"  FAIL  {name}  {detail}")


def end(t):
    """Printable, comparable name of a cable termination: 'device:port' or 'circuit:CID:side'."""
    o = t.object
    if t.object_type == "circuits.circuittermination":
        return f"circuit:{o.circuit.cid}:{o.term_side}"
    return f"{o.device.name}:{o.name}"


def haversine_km(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(a))


def run(nb):
    racks_plan, devices_plan = layout.inventory()
    devices = {d.name: d for d in nb.dcim.devices.all()}
    racks = {r.name: r for r in nb.dcim.racks.all()}
    cables = list(nb.dcim.cables.all())
    by_pair = {}
    for c in cables:
        ends = sorted(end(t) for t in list(c.a_terminations) + list(c.b_terminations))
        by_pair[tuple(ends)] = c

    def cabled(a, b):
        """The cable joining two (kind, device, port) endpoints, if any."""
        ea = f"{a[1]}:{a[2]}" if a[0] != "ct" else f"circuit:{a[1]}:{a[2]}"
        eb = f"{b[1]}:{b[2]}" if b[0] != "ct" else f"circuit:{b[1]}:{b[2]}"
        return by_pair.get(tuple(sorted([ea, eb])))

    print("== Inventory matches the layout ==")
    check("racks", set(racks) == {r["name"] for r in racks_plan},
          f"extra={set(racks) - {r['name'] for r in racks_plan}} missing={ {r['name'] for r in racks_plan} - set(racks)}")
    check("devices", set(devices) == {d["name"] for d in devices_plan},
          f"extra={set(devices) - {d['name'] for d in devices_plan}} missing={ {d['name'] for d in devices_plan} - set(devices)}")
    misplaced = [d["name"] for d in devices_plan if d["name"] in devices and
                 (devices[d["name"]].rack.name if devices[d["name"]].rack else None) != d["rack"]
                 or (d["position"] is not None and d["name"] in devices and devices[d["name"]].position != d["position"])]
    check("every device in its planned rack and U", not misplaced, str(misplaced))
    core = ("patch-01", "oob-01", "rtr-01", "rtr-02", "sw-01", "sw-02", "dcp2-01")
    for kind in ("dc", "pop"):
        shapes = {tuple(sorted(n.split("-", 1)[1] for n in devices if n.startswith(s["code"] + "-")
                               and n.split("-", 1)[1] in core))
                  for s in SITES if s["kind"] == kind}
        check(f"all {kind.upper()}s have the same core equipment", len(shapes) == 1, str(shapes))

    print("== Identity ==")
    check("every device has a serial", all(d.serial for d in devices.values()),
          str([n for n, d in devices.items() if not d.serial]))
    owned = [d for d in devices.values() if d.tenant and d.tenant.slug == "nordfiber-ab"]
    check("every Nordfiber device has an asset tag", all(d.asset_tag for d in owned),
          str([d.name for d in owned if not d.asset_tag]))

    print("== Cable attributes ==")
    colour = {"smf-os2": "ffeb3b", "cat6": "9e9e9e", "cat6a": "9e9e9e", "dac-passive": "111111"}
    bad = {"label": [], "ends": [], "type": [], "length": [], "tenant": [], "bb": []}
    for c in cables:
        ends = [t for t in list(c.a_terminations) + list(c.b_terminations)]
        sites = {t.object.device.site.slug for t in ends if t.object_type != "circuits.circuittermination"}
        has_ct = any(t.object_type == "circuits.circuittermination" for t in ends)
        if not re.fullmatch(r"(bb|[a-z]{3})-cbl-\d{5}", c.label or ""):
            bad["label"].append(c.id)
        elif c.label.startswith("bb-") != (len(sites) > 1):
            bad["bb"].append(c.label)
        cf = c.custom_fields or {}
        if not (cf.get("label_a") or "").startswith(f"{c.label} ->") or not (cf.get("label_b") or "").startswith(f"{c.label} ->"):
            bad["ends"].append(c.label)
        if str(c.type) not in colour or c.color != colour[str(c.type)]:
            bad["type"].append(c.label)
        if not has_ct and not c.length:
            bad["length"].append(c.label)
        if not c.tenant:
            bad["tenant"].append(c.label)
    check("labels follow <site>-cbl-NNNNN / bb-cbl-NNNNN, bb- exactly for inter-site cables", not bad["label"] and not bad["bb"], str(bad["label"] + bad["bb"]))
    check("every cable has both end labels", not bad["ends"], str(bad["ends"]))
    check("cable type and colour agree", not bad["type"], str(bad["type"]))
    check("every cable has a length (circuit demarcs excepted)", not bad["length"], str(bad["length"]))
    check("every cable has a tenant", not bad["tenant"], str(bad["tenant"]))
    labels = [c.label for c in cables]
    check("cable labels are unique", len(labels) == len(set(labels)))

    print("== Cable tenancy ==")
    wrong = []
    for c in cables:
        ends = list(c.a_terminations) + list(c.b_terminations)
        devs = [devices[t.object.device.name] for t in ends if t.object_type != "circuits.circuittermination"]
        if any(d.role.slug == "oob-switch" for d in devs):
            want = {"nordfiber-ab"}
        else:
            ext = {d.tenant.slug for d in devs if d.tenant and d.tenant.slug != "nordfiber-ab"}
            want = ext or {"nordfiber-ab"}
        if c.tenant.slug not in want:
            wrong.append(f"{c.label}={c.tenant.slug}")
    check("external party wins; OOB and own kit are Nordfiber's", not wrong, str(wrong))

    print("== Every management port is cabled ==")
    open_mgmt = []
    for d in devices_plan:
        if d["role"] == "oob-switch" or not d["mgmt_iface"] or d["role"] in ("patch-panel", "workstation"):
            continue
        iface = nb.dcim.interfaces.get(device_id=devices[d["name"]].id, name=d["mgmt_iface"])
        if not iface.cable:
            open_mgmt.append(d["name"])
    check("management ports", not open_mgmt, str(open_mgmt))

    print("== Every planned connection exists ==")
    missing = []
    for s in SITES:
        for plan in (C.core_pair(s), C.meetme(s), C.colo(s), C.office(s), C.oob(s)):
            missing += [f"{a[1]}:{a[2]}<>{b[1]}:{b[2]}" for a, b, _ in plan if not cabled(a, b)]
    for wdm, port in O.LINE_PATCH_PORT.items():
        if not cabled(("frontport", f"{wdm.split('-')[0]}-patch-01", f"Port {port}"), ("rearport", wdm, "Line")):
            missing.append(f"{wdm} line")
    for wdm, ch, shelf, line in O.SHELF_LINE:
        if not cabled(("frontport", wdm, ch), ("interface", shelf, line)):
            missing.append(f"{wdm}:{ch} -> {shelf}")
    for shelf, client, far in O.SHELF_CLIENT:
        if not cabled(("interface", shelf, client), far):
            missing.append(f"{shelf}:{client}")
    for wdm, ch, rtr, iface in O.DIRECT_HANDOFF:
        if not cabled(("frontport", wdm, ch), ("interface", rtr, iface)):
            missing.append(f"{wdm} -> {rtr}")
    a, ach, b, bch = O.REGEN_JUMPER
    if not cabled(("frontport", a, ach), ("frontport", b, bch)):
        missing.append("regen jumper")
    for _, a, b, _, _ in T.LONG_HAUL:
        if not cabled(("rearport",) + a, ("rearport",) + b):
            missing.append(f"{a[0]} <> {b[0]}")
    check("all planned cables present", not missing, str(missing))

    print("== Physical paths, walked cable by cable ==")

    def walk(device, kind, name):
        """Follow cables through passive panels (front N <-> rear N) to the first non-panel end."""
        ep = {"interface": nb.dcim.interfaces, "frontport": nb.dcim.front_ports, "rearport": nb.dcim.rear_ports}
        cur = ep[kind].get(device_id=devices[device].id, name=name)
        for _ in range(40):
            if not cur.cable:
                return None
            cable = nb.dcim.cables.get(id=cur.cable.id)
            here = {(t.object_type, t.object.id) for t in (list(cable.a_terminations) + list(cable.b_terminations))
                    if t.object.id == cur.id and t.object_type == f"dcim.{kind}"}
            far = next(t for t in list(cable.a_terminations) + list(cable.b_terminations)
                       if not (t.object.id == cur.id and t.object_type == f"dcim.{kind}"))
            if far.object_type == "circuits.circuittermination":
                return f"circuit:{far.object.circuit.cid}:{far.object.term_side}"
            fdev = devices[far.object.device.name]
            fkind = far.object_type.split(".")[1]
            if fdev.role.slug != "patch-panel":
                return f"{fdev.name}:{far.object.name}"
            other = {"frontport": ("rearport", nb.dcim.rear_ports), "rearport": ("frontport", nb.dcim.front_ports)}[fkind]
            cur = other[1].get(device_id=fdev.id, name=far.object.name)
            kind = other[0]
        return "loop"

    expected = [
        ("sto-wdm-01", "rearport", "Line", "osl-wdm-01:Line"),
        ("sto-wdm-02", "rearport", "Line", "got-wdm-01:Line"),
        ("got-wdm-02", "rearport", "Line", "mma-wdm-01:Line"),
        ("sto-wdm-03", "rearport", "Line", "hel-wdm-01:Line"),
        ("sto-wdm-04", "rearport", "Line", "hel-wdm-02:Line"),
        ("polaris-sto-sw-01", "interface", "Ethernet49", "sto-sw-01:Ethernet2"),
        ("polaris-got-sw-01", "interface", "Ethernet49", "got-sw-01:Ethernet2"),
        ("vasthamnen-got-sw-01", "interface", "Ethernet49", "got-sw-01:Ethernet3"),
        ("got-rtr-01", "interface", "xe-0/1/1", "circuit:VKB-INET-0001:A"),
    ]
    for dev, kind, port, want in expected:
        got = walk(dev, kind, port)
        check(f"{dev}:{port} -> {want}", got == want, f"got {got}")

    print("== Optical services ==")
    for wc in nb.plugins.wdm.wdm_circuits.all():
        check(f"{wc.name} has an attached path", bool(wc.wavelength_paths))
    check("only the 3 attached wavelength paths remain", nb.plugins.wdm.wdm_wavelength_paths.count() == 3,
          str(nb.plugins.wdm.wdm_wavelength_paths.count()))
    muxponders = [d for d in devices.values() if d.role.slug == "wdm-terminal"]
    check("every muxponder has its 40 channels",
          all(nb.plugins.wdm.wdm_channels.count(wdm_node_id=nb.plugins.wdm.wdm_nodes.get(device_id=d.id).id) == 40
              for d in muxponders))

    print("== Geography ==")
    long_haul = [c for c in cables if c.label and c.label.startswith("bb-")]
    check("every long-haul cable has an FMS record", nb.plugins.fms.fiber_cables.count() == len(long_haul),
          f"{nb.plugins.fms.fiber_cables.count()} vs {len(long_haul)}")
    check("every long-haul cable has a pathway segment", nb.plugins.pathways.cable_segments.count() == len(long_haul))
    site_pos = {s.slug: (float(s.longitude), float(s.latitude)) for s in nb.dcim.sites.all() if s.latitude}
    seg_by_cable = {}
    for seg in nb.plugins.pathways.cable_segments.all():
        seg_by_cable[seg.cable.id] = seg
    off = []
    for c in long_haul:
        seg = seg_by_cable.get(c.id)
        if not seg:
            continue
        coords = nb.plugins.pathways.direct_buried.get(id=seg.pathway.id).path.coordinates
        ends_sites = [site_pos[t.object.device.site.slug] for t in list(c.a_terminations) + list(c.b_terminations)]
        pairs = [(coords[0], ends_sites[0], coords[-1], ends_sites[1]), (coords[0], ends_sites[1], coords[-1], ends_sites[0])]
        ok = any(haversine_km(*p[0], *p[1]) < 15 and haversine_km(*p[2], *p[3]) < 15 for p in pairs)
        if not ok:
            off.append(c.label)
        km = c.length
        route_len = sum(haversine_km(*coords[i], *coords[i + 1]) for i in range(len(coords) - 1))
        if abs(float(km) - route_len) > 1:
            off.append(f"{c.label} length")
    check("route geometry starts and ends at the cable's own sites, length matches", not off, str(off))
    geoms = nb.plugins.pathways.circuit_geometries.count()
    check("leased circuits have geometries", geoms == sum(1 for c in T.CIRCUITS if "geometry" in c), str(geoms))

    print("== Services ==")
    check("iBGP full mesh", nb.plugins.bgp.session.count() == 10, str(nb.plugins.bgp.session.count()))
    check("one secret per router 01", nb.plugins.secrets.secrets.count() == 5)
    check("every managed device has a primary IPv4",
          all(devices[d["name"]].primary_ip4 for d in devices_plan if d["mgmt_ip"]))

    print("== Text hygiene ==")
    stale = []
    pat = re.compile(r"\bPhase \d|\bpost-hoc\b|Gothenburg PoP|\bTODO\b", re.I)
    for label, objs in (("site", nb.dcim.sites.all()), ("rack", nb.dcim.racks.all()), ("device", nb.dcim.devices.all()),
                        ("circuit", nb.circuits.circuits.all()), ("cable", cables), ("prefix", nb.ipam.prefixes.all()),
                        ("tenant", nb.tenancy.tenants.all()), ("provider", nb.circuits.providers.all())):
        for o in objs:
            for field in ("description", "comments"):
                if pat.search(getattr(o, field, "") or ""):
                    stale.append(f"{label} {getattr(o, 'name', None) or getattr(o, 'label', None) or getattr(o, 'cid', o.id)}")
    check("no leftover phase/PoP/TODO wording", not stale, str(stale))

    print(f"\n{PASSED} checks passed, {len(FAILS)} failed")
    return not FAILS


if __name__ == "__main__":
    nb = connect()
    sys.exit(0 if run(nb) else 1)
