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
import naming
from common import PLUGIN_STATE, api, connect, have, version_at_least
from data import cabling as C
from data import hardware as H
from data import metro as M
from data import optical as O
from data import services as S
from data import transport as T
from data.organization import SITES, TENANTS

FAILS = []
PASSED = 0
SKIPPED = []


def check(name, ok, detail=""):
    global PASSED
    if ok:
        PASSED += 1
        print(f"  ok    {name}")
    else:
        FAILS.append(name)
        print(f"  FAIL  {name}  {detail}")


def skip_checks(plugin, what):
    """A group of checks that needs a plugin the NetBox does not have (or that was switched off)."""
    SKIPPED.append(what)
    print(f"  skip  {what}: netbox-{plugin} {PLUGIN_STATE[plugin]}")


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
    core = ("patch-mmr-01", "oob-01", "rtr-01", "rtr-02", "sw-01", "sw-02", "dcp2-01")
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
        rear = [t.object for t in ends if t.object_type == "dcim.rearport"]
        trunk = len(rear) == 2 and all(r.name == "Trunk" for r in rear)
        # trunks are green inside a site and blue between sites; other fiber is yellow
        want = ("2196f3" if len(sites) > 1 else "4caf50") if trunk else colour.get(str(c.type))
        if str(c.type) not in colour or c.color != want:
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
    tenant_slug = {t["code"]: t["slug"] for t in TENANTS}
    ring_key = {}                       # cable label -> link key, for the metro ring's three cables
    for l in M.LINKS:
        rc = cabled(("rearport", l["a_panel"], "Trunk"), ("rearport", l["b_panel"], "Trunk"))
        if rc:
            ring_key[rc.label] = l["key"]
    ring_owner = {label: tenant_slug[M.link(key)["cable_owner"]] for label, key in ring_key.items()}
    wrong = []
    for c in cables:
        ends = list(c.a_terminations) + list(c.b_terminations)
        devs = [devices[t.object.device.name] for t in ends if t.object_type != "circuits.circuittermination"]
        if any(d.role.slug == "oob-switch" for d in devs):
            want = {"nordfiber-ab"}
        else:
            ext = {d.tenant.slug for d in devs if d.tenant and d.tenant.slug != "nordfiber-ab"}
            want = ext or {"nordfiber-ab"}
        if c.label in ring_owner:
            want = {ring_owner[c.label]}
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
    for wdm, (patch, port) in O.LINE_PATCH.items():
        if not cabled(("frontport", patch, f"Port {port}"), ("rearport", wdm, "Line")):
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
    for l in M.LINKS:
        if not cabled(("rearport", l["a_panel"], "Trunk"), ("rearport", l["b_panel"], "Trunk")):
            missing.append(f"{l['a_panel']} <> {l['b_panel']}")
    check("all planned cables present", not missing, str(missing))

    print("== Trunks ==")
    panels = [d for d in devices.values() if d.role.slug == "patch-panel"]
    check("every patch panel is a 24-pair panel, except the metro ring's 144-pair panels",
          all(d.device_type.slug == (H.T_PANEL_144 if (d.name.split("-")[0], d.name.split("-")[2]) in
                                    {(a, b) for a, b in H.RING_PAIRS} | {(b, a) for a, b in H.RING_PAIRS} else H.T_PANEL)
              for d in panels if "-patch-" in d.name),
          str([d.name for d in panels if "-patch-" in d.name]))
    trunk_ends, discrete = {}, []
    for c in cables:
        ends = list(c.a_terminations) + list(c.b_terminations)
        rear = [t.object for t in ends if t.object_type == "dcim.rearport"]
        if any(r.name == "Trunk" for r in rear):
            trunk_ends[c.label] = ([r.device.name for r in rear if r.name == "Trunk"],
                                   any(t.object_type == "circuits.circuittermination" for t in ends))
        discrete += [c.label for r in rear if r.name != "Trunk" and r.device.role.slug == "patch-panel"]
    check("every trunk is ONE cable between two panels (or a panel and a circuit demarc)",
          all(len(panels_) == 2 or (len(panels_) == 1 and circuit) for panels_, circuit in trunk_ends.values()), str(trunk_ends))
    # the facility owner's own panel in a MeetMe room is a placeholder: it carries nothing
    owner_panels = {f"{x['code']}-mmr-{x['mm_owner']}-01" for x in SITES if x["mm_owner"] != "nordfiber"}
    lone = [d.name for d in panels if d.name not in owner_panels
            and not any(d.name in panels_ for panels_, _c in trunk_ends.values())]
    check("no panel is left without its trunk (the facility owners' placeholders excepted)", not lone, str(lone))
    check("no panel has discrete one-pair rear cables any more", not discrete, str(discrete))
    ring_labels = set(ring_key)
    if have("fms"):
        check("long-haul and vendor trunks have 48-fiber FMS records, the metro ring cables 288-fiber",
              all(fc.fiber_cable_type.strand_count == (288 if fc.cable.label in ring_labels else 48)
                  for fc in nb.plugins.fms.fiber_cables.all()))
    else:
        skip_checks("fms", "FMS cable records")

    if have("fms"):
        print("== Fiber strands and circuits ==")
        badly_landed = []
        for s in nb.plugins.fms.fiber_strands.filter(limit=0):
            want = f"Port {(s.position + 1) // 2}"
            a, b = s.front_port_a, s.front_port_b
            if not (a and b and a.name == b.name == want and a.device.id != b.device.id):
                badly_landed.append(f"{s.fiber_cable}/{s.name}")
        check("every strand is landed on its pair's panel port at both ends (strands 2n-1, 2n -> Port n)",
              not badly_landed, str(badly_landed[:5]))
        fcs = {fc.cid: fc for fc in nb.plugins.fms.fiber_circuits.all()}
        check("one FMS fiber circuit per trunk pair in use or leased", set(fcs) == {c["cid"] for c in T.FIBER_CIRCUITS}, str(sorted(fcs)))
        for plan in T.FIBER_CIRCUITS:
            fc = fcs.get(plan["cid"])
            paths = list(nb.plugins.fms.fiber_circuit_paths.filter(circuit_id=fc.id)) if fc else []
            (o_dev, o_port), (d_dev, d_port) = T.circuit_ends(plan)
            want_ends = (o_dev, f"Port {o_port}", d_dev, f"Port {d_port}")
            if version_at_least("fms", 0, 6):
                # netbox-fms 0.6: the circuit is assigned the path it derived between the two panel ports
                def port(fp):
                    return fp.device.name, fp.name
                derived = [nb.plugins.fms.fiber_strand_paths.get(p.strand_path.id) for p in paths]
                got = {frozenset({port(sp.end_a_port), port(sp.end_b_port)}) for sp in derived}
                want = {frozenset({(o_dev, f"Port {o_port}"), (d_dev, f"Port {d_port}")})}
                check(f"{plan['cid']}: 2 strands, assigned path complete {want_ends[0]}:{want_ends[1]} -> {want_ends[2]}:{want_ends[3]}",
                      bool(fc) and fc.strand_count == 2 and len(paths) == 1
                      and all(sp.completeness == "terminated_terminated" for sp in derived)
                      and got == want, f"{got}")
                continue
            def port(pk):                                # the FMS serializer returns plain ids for these
                fp = nb.dcim.front_ports.get(pk)
                return fp.device.name, fp.name
            got = {port(p.origin) + port(p.destination) for p in paths if p.destination}
            check(f"{plan['cid']}: 2 strands, both paths complete {want_ends[0]}:{want_ends[1]} -> {want_ends[2]}:{want_ends[3]}",
                  bool(fc) and fc.strand_count == 2 and len(paths) == 2 and all(p.is_complete for p in paths)
                  and got == {want_ends}, f"{got}")
    else:
        skip_checks("fms", "fiber strands and circuits")

    print("== Physical paths, traced by NetBox ==")

    def trace_end(device, ifname):
        """Where NetBox's own trace from an interface ends: 'device:port' or 'circuit:CID:side'."""
        iface = nb.dcim.interfaces.get(device_id=devices[device].id, name=ifname)
        legs = api(f"/api/dcim/interfaces/{iface.id}/trace/")
        far = legs[-1][2] if legs else []
        if not far:
            return None
        end_ = far[0]
        if "circuit" in end_:
            return f"circuit:{end_['circuit']['cid']}:{end_['term_side']}"
        return f"{end_['device']['name']}:{end_['name']}"

    expected = [
        ("stn-dcp2-01", "Line/1/1", "osl-dcp2-01:Line/1/1"),                 # Fjord, through two trunks and two muxponders
        ("stn-dcp2-01", "Line/2/1", "mma-dcp2-01:Line/1/1"),                 # Baltic Retail protect, regenerated in Gothenburg
        ("stw-dcp2-01", "Line/1/1", "got-dcp2-01:Line/1/1"),                 # Baltic Retail secondary, the southern route
        ("stn-rtr-01", "et-0/0/2", "hel-rtr-01:et-0/0/2"),                   # Helsinki over NSN
        ("ste-rtr-02", "et-0/0/3", "hel-rtr-02:et-0/0/3"),                   # Helsinki over BFN
        ("stn-rtr-01", "et-0/0/3", "stw-rtr-01:et-0/0/2"),                   # the ring, North - West
        ("stn-rtr-02", "et-0/0/3", "ste-rtr-01:et-0/0/2"),                   # the ring, North - East
        ("stw-rtr-02", "et-0/0/3", "ste-rtr-01:et-0/0/3"),                   # the ring, West - East (leased)
        ("polaris-stn-sw-01", "Ethernet49", "stn-sw-01:Ethernet2"),
        ("baltic-retail-stn-sw-01", "Ethernet49", "stn-sw-01:Ethernet3"),
        ("baltic-retail-stw-sw-01", "Ethernet49", "stw-sw-01:Ethernet2"),
        ("baltic-retail-ste-sw-01", "Ethernet49", "ste-sw-01:Ethernet2"),
        ("polaris-got-sw-01", "Ethernet49", "got-sw-01:Ethernet2"),
        ("vasthamnen-got-sw-01", "Ethernet49", "got-sw-01:Ethernet3"),
        ("baltic-retail-mma-sw-01", "Ethernet49", "mma-sw-01:Ethernet2"),
        ("got-rtr-01", "xe-0/1/1", "circuit:VKB-INET-0001:A"),
        ("stw-rtr-01", "et-0/0/0", "mma-rtr-01:et-0/0/0"),                   # the Baltic Retail circuit
    ]
    for dev, port, want in expected:
        got = trace_end(dev, port)
        check(f"{dev}:{port} -> {want}", got == want, f"got {got}")

    if have("wdm"):
        print("== Optical services ==")
        for wc in nb.plugins.wdm.wdm_circuits.all():
            check(f"{wc.name} has an attached path", bool(wc.wavelength_paths))
        check(f"only the {len(O.WDM_CIRCUITS)} attached wavelength paths remain",
              nb.plugins.wdm.wdm_wavelength_paths.count() == len(O.WDM_CIRCUITS),
              str(nb.plugins.wdm.wdm_wavelength_paths.count()))
        muxponders = [d for d in devices.values() if d.role.slug == "wdm-terminal"]
        check("every muxponder has its 40 channels",
              all(nb.plugins.wdm.wdm_channels.count(wdm_node_id=nb.plugins.wdm.wdm_nodes.get(device_id=d.id).id) == 40
                  for d in muxponders))
    else:
        skip_checks("wdm", "optical services")

    print("== Geography ==")
    long_haul = [c for c in cables if c.label and c.label.startswith("bb-")]
    if have("fms"):
        check("every long-haul cable has an FMS record", nb.plugins.fms.fiber_cables.count() == len(long_haul),
              f"{nb.plugins.fms.fiber_cables.count()} vs {len(long_haul)}")
    else:
        skip_checks("fms", "FMS records of the long-haul cables")
    if have("pathways"):
        segs_by_cable = {}
        for seg in nb.plugins.pathways.cable_segments.all():
            segs_by_cable.setdefault(seg.cable.id, []).append(seg)
        check("every long-haul cable has a pathway segment, the ring cables one per leg",
              all(len(segs_by_cable.get(c.id, [])) == (len(M.legs(ring_key[c.label])) if c.label in ring_key else 1)
                  for c in long_haul))
        site_pos = {s.slug: (float(s.longitude), float(s.latitude)) for s in nb.dcim.sites.all() if s.latitude}
        seg_by_cable = {cid: segs[0] for cid, segs in segs_by_cable.items()}
        off = []
        for c in long_haul:
            seg = seg_by_cable.get(c.id)
            if not seg or c.label in ring_labels:
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
    else:
        skip_checks("pathways", "routes and geometries")

    if have("pathways"):
        print("== Stockholm metro plant ==")
        pw = nb.plugins.pathways
        structs = {x.name: x for x in pw.structures.all()}
        check("every structure of the plan exists, owned by its municipality (or Nordfiber)",
              set(structs) == set(M.structures()) and
              all(structs[n].tenant and structs[n].tenant.slug == tenant_slug[M.structures()[n][3]] for n in structs),
              str(set(structs) ^ set(M.structures())))
        entrance_site = {name: code for code, links in M.ENTRANCES.items() for name in links.values()}
        check("each datacenter has one entrance per ring link, on its own site",
              all(structs[n].site and structs[n].site.slug == next(naming.site_slug(s) for s in SITES if s["code"] == c)
                  for n, c in entrance_site.items()))
        used_structs, used_paths, bad = {}, {}, []
        base_by_id = {x.id: x for x in pw.pathways.all()}
        for l in M.LINKS:
            key = l["key"]
            cable = cabled(("rearport", l["a_panel"], "Trunk"), ("rearport", l["b_panel"], "Trunk"))
            segs = sorted(segs_by_cable.get(cable.id, []), key=lambda x: x.sequence) if cable else []
            legs_ = M.legs(key)
            if len(segs) != len(legs_):
                bad.append(f"{key}: {len(segs)} segments for {len(legs_)} legs")
                continue
            total = 0.0
            for n, (seg, leg) in enumerate(zip(segs, legs_), start=1):
                p = base_by_id[seg.pathway.id]
                total += float(p.length or 0)
                used_paths.setdefault(p.id, set()).add(key)
                for end_ in (p.start_structure, p.end_structure):
                    if end_:
                        used_structs.setdefault(end_.name, set()).add(key)
                if (p.start_structure.name, p.end_structure.name) != (leg["a"], leg["b"]):
                    bad.append(f"{key} leg {n}: {p.start_structure.name} -> {p.end_structure.name}")
                # the innermost pathway belongs to the cable's owner, the water crossing to Nordfiber; the conduit around
                # an innerduct belongs to the municipality
                want_owner = tenant_slug["nordfiber" if leg["kind"] == "sub" else l["cable_owner"]]
                if not p.tenant or p.tenant.slug != want_owner:
                    bad.append(f"{key} leg {n} owner")
                if leg["kind"] != "sub":
                    cond = nb.plugins.pathways.conduits.get(label=leg["label"] + (" conduit A1" if leg["kind"] == "bank" else " conduit"))
                    if not cond or not cond.tenant or cond.tenant.slug != tenant_slug[leg["owner"]]:
                        bad.append(f"{key} leg {n} conduit owner")
                want_type = "submarine" if leg["kind"] == "sub" else "innerduct"
                if str(p.pathway_type.value if hasattr(p.pathway_type, "value") else p.pathway_type) != want_type:
                    bad.append(f"{key} leg {n} type {p.pathway_type}")
            if abs(total - float(cable.length) * 1000) > 100:
                bad.append(f"{key}: ducts {total:.0f} m, cable {float(cable.length) * 1000:.0f} m")
            a_site, b_site = (next(naming.site_slug(s) for s in SITES if s["code"] == c) for c in (l["a"], l["b"]))
            if (structs[legs_[0]["a"]].site.slug, structs[legs_[-1]["b"]].site.slug) != (a_site, b_site):
                bad.append(f"{key}: ends are not the entrances of {l['a']} and {l['b']}")
        check("each ring cable runs through its legs in order, structure to structure, owner by owner, and the ducts add up to its length",
              not bad, str(bad))
        check("no duct and no structure outside the buildings is shared between two ring links (dispersed routing)",
              all(len(v) == 1 for v in used_paths.values()) and all(len(v) == 1 for v in used_structs.values()),
              str({k: v for k, v in list(used_paths.items()) + list(used_structs.items()) if len(v) > 1}))
        lease = next(l for l in M.LINKS if l["circuit"])
        lease_cable = cabled(("rearport", lease["a_panel"], "Trunk"), ("rearport", lease["b_panel"], "Trunk"))
        check("the West - East cable is owned by Stockholm Metro Fibre and leased whole (SMF-DF-0001, with a geometry)",
              lease_cable.tenant.slug == "stockholm-metro-fibre-ab" and bool(nb.circuits.circuits.get(cid=lease["circuit"]))
              and bool(nb.plugins.pathways.circuit_geometries.get(circuit_id=nb.circuits.circuits.get(cid=lease["circuit"]).id)))
    else:
        skip_checks("pathways", "the Stockholm metro plant")
    if have("fms"):
        tube_names = []
        for key in (l["key"] for l in M.LINKS):
            l = M.link(key)
            fcab = next((fc for fc in nb.plugins.fms.fiber_cables.all() if fc.cable.label ==
                         cabled(("rearport", l["a_panel"], "Trunk"), ("rearport", l["b_panel"], "Trunk")).label), None)
            names = sorted(t.name for t in nb.plugins.fms.buffer_tubes.filter(fiber_cable_id=fcab.id)) if fcab else []
            tube_names.append(len(names) == 24 and all(n.startswith("Tube ") and " - " in n for n in names))
        check("each ring cable has 24 tubes named after their use (WDM, Nordfiber dark, leasable dark)", all(tube_names))
    else:
        skip_checks("fms", "ring cable tube names")

    print("== Services ==")
    routers = len(S.ROUTER_ORDER)
    if have("bgp"):
        check("iBGP full mesh", nb.plugins.bgp.session.count() == routers * (routers - 1) // 2, str(nb.plugins.bgp.session.count()))
    else:
        skip_checks("bgp", "iBGP full mesh")
    if have("secrets"):
        check("one secret per router 01", nb.plugins.secrets.secrets.count() == routers)
    else:
        skip_checks("secrets", "one secret per router 01")
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

    extra = f", {len(SKIPPED)} groups of plugin checks skipped" if SKIPPED else ""
    print(f"\n{PASSED} checks passed, {len(FAILS)} failed{extra}")
    return not FAILS


if __name__ == "__main__":
    nb = connect()
    sys.exit(0 if run(nb) else 1)
