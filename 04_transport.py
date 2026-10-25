#!/usr/bin/env python3
"""
Layer 4: transport — everything between sites.

  providers, circuit types, circuits and their terminations
  -> the metro plant (plant.py: structures, ducts, water crossings of the Stockholm ring)
  -> the long-haul cables (Nordfiber's own backbone, the leased Polarlink
     pair, the two vendor spans to Helsinki) and the three metro ring cables, each with
     its fiber-plant record (netbox-fms) and its real-world route (netbox-pathways)
  -> every strand landed on its panel port, and a fiber circuit (netbox-fms)
     for each trunk pair that is in use or leased
  -> circuit geometries for the leased circuits
  -> the few circuit terminations that are physically cabled

Providers, circuits, cables and demarcs are core NetBox and always loaded. The fiber plant (netbox-fms) and
the routes, ducts and geometries (netbox-pathways) are added only when those plugins are installed; run the
layer again after installing one and it fills in what is missing.

A leased dark-fiber circuit stays a commercial record with uncabled
terminations; the physical span is ONE direct Cable between the vendor's
two MeetMe panels (rear to rear). That is the same model as Nordfiber's own
backbone, so a trace follows the glass rather than the contract.

Requires layers 1-3. Safe to re-run.
"""

import time

import requests

import plant
from cabling import CT, Cabler
from common import api, connect, ensure, have, linestring, report, route_km, skip, version_at_least
from data import metro as M
from data import transport as T
from data.organization import SITES, TENANTS
from naming import site_slug


def circuits(nb):
    print("== Providers, circuit types ==")
    providers = {}
    for p in T.PROVIDERS:
        obj, st = ensure(nb.circuits.providers, {"slug": p["slug"]}, **p)
        report("provider", obj, st)
        providers[p["slug"]] = obj
    types = {}
    for t in T.CIRCUIT_TYPES:
        obj, st = ensure(nb.circuits.circuit_types, {"slug": t["slug"]}, **t)
        report("circuit type", obj, st)
        types[t["slug"]] = obj

    tenants = {t["code"]: nb.tenancy.tenants.get(slug=t["slug"]) for t in TENANTS}
    sites = {s["code"]: nb.dcim.sites.get(slug=site_slug(s)) for s in SITES}

    print("== Circuits ==")
    for c in T.CIRCUITS:
        circuit, st = ensure(
            nb.circuits.circuits, {"cid": c["cid"]}, cid=c["cid"], provider=providers[c["provider"]].id,
            type=types[c["type"]].id, tenant=tenants[c["tenant"]].id, status="active",
            commit_rate=c["rate"], description=c["description"])
        report("circuit", circuit, st)
        for side, code in c["sites"].items():
            term, st = ensure(
                nb.circuits.circuit_terminations, {"circuit_id": circuit.id, "term_side": side},
                once=("circuit", "term_side", "termination_type", "termination_id"),
                circuit=circuit.id, term_side=side, termination_type="dcim.site",
                termination_id=sites[code].id, port_speed=c["rate"])
            report(f"  termination {side}", term, st, sites[code].name)


def cable_types(nb):
    """The two FMS cable types: the 48-fiber trunk cable and the 288-fiber metro cable, each with its tube templates."""
    types = {}
    if not have("fms"):
        skip("fms", "fiber cable types")
        return types
    for fibers, base, tubes in ((48, T.FMS_CABLE_TYPE, T.FMS_BUFFER_TUBES), (288, T.FMS_CABLE_TYPE_288, T.FMS_BUFFER_TUBES_288)):
        spec = dict(base)
        mfr = nb.dcim.manufacturers.get(slug=spec.pop("manufacturer"))
        cable_type, st = ensure(nb.plugins.fms.cable_types, {"model": spec["model"]}, manufacturer=mfr.id, **spec)
        report("fms cable type", cable_type, st)
        if st == "created":
            for tube in tubes:
                nb.plugins.fms.buffer_tube_templates.create(fiber_cable_type=cable_type.id, **tube)
        types[fibers] = cable_type
    return types


def fiber_record(nb, cable, cable_type, key, km, notes, tenants):
    """The netbox-fms record of one cable: type, serial, installer and sheath marks."""
    detail = T.FIBER_DETAILS[key]
    installer = tenants.get(detail["installer"]) if detail["installer"] else None
    fc, st = ensure(nb.plugins.fms.fiber_cables, {"cable_id": cable.id}, cable=cable.id, fiber_cable_type=cable_type.id,
                    notes=notes, serial_number=detail["serial_number"], install_date=detail["install_date"],
                    installed_by=installer.id if installer else None, start_mark=0, end_mark=round(km * 1000))
    report("fiber cable", fc, st, cable.label)
    return fc


def long_haul(nb, cabler, types):
    tenants = {t["code"]: nb.tenancy.tenants.get(slug=t["slug"]) for t in TENANTS}
    plant_ = {}
    print("== Long-haul cables, fiber plant and routes ==")
    for key, a, b, note, fms_note in T.LONG_HAUL:
        route = T.ROUTES[key]
        km = route_km(route)
        # the leased Polarlink pair has no Tenant of its own; it is Nordfiber's cable
        cable = cabler.connect(("rearport",) + a, ("rearport",) + b, note=note,
                               tenant="nordfiber-ab" if key in T.NORDFIBER_CABLES else None, km=km)
        fc = fiber_record(nb, cable, types[48], key, km, fms_note, tenants) if types else None
        plant_[key] = {"fiber_cable": fc, "a": a[0], "b": b[0], "km": km, "strands": 48}
        if not have("pathways"):
            continue

        label = f"{cable.label}-route"
        names = " -> ".join(n for n, _, _ in route if n)
        comments = f"{names} ({km:.0f} km)"
        # `path` comes back as GeoJSON, so it can't go through ensure()'s plain comparison
        pathway, st = ensure(nb.plugins.pathways.direct_buried, {"label": label}, once=("path",), label=label,
                             path=linestring(route), comments=comments)
        if (pathway.path.coordinates if pathway.path else None) != [[lon, lat] for _, lon, lat in route]:
            pathway.update({"path": linestring(route)})
            st = "updated"
        report("pathway", pathway, st, label)
        if not nb.plugins.pathways.cable_segments.get(cable_id=cable.id, pathway_id=pathway.id):
            nb.plugins.pathways.cable_segments.create(cable=cable.id, pathway=pathway.id, sequence=1)
    if not types:
        skip("fms", "fiber cable records for the long-haul cables")
    if not have("pathways"):
        skip("pathways", "routes and cable segments for the long-haul cables")
    return plant_


def metro_cables(nb, cabler, types):
    """The three ring cables: 288-fiber cable between 144-pair panels, routed through the plant leg by leg."""
    tenants = {t["code"]: nb.tenancy.tenants.get(slug=t["slug"]) for t in TENANTS}
    plant_ = {}
    print("== Metro ring cables, fiber plant and routes ==")
    for l in M.LINKS:
        key = l["key"]
        km = M.cable_km(key)
        a, b = ("rearport", l["a_panel"], "Trunk"), ("rearport", l["b_panel"], "Trunk")
        owner = tenants[l["cable_owner"]]
        cable = cabler.connect(a, b, note=l["note"], tenant=owner.slug, km=km)
        fc = fiber_record(nb, cable, types[288], key, km, l["fms_note"], tenants) if types else None
        plant_[key] = {"fiber_cable": fc, "a": l["a_panel"], "b": l["b_panel"], "km": km, "strands": 288}

        if fc:
            # the tube name carries what the tube is for: WDM, Nordfiber's dark fiber, or leasable dark fiber
            for tube in nb.plugins.fms.buffer_tubes.filter(fiber_cable_id=fc.id):
                want = f"Tube {tube.position} - {T.tube_use(tube.position)}"
                if tube.name != want:
                    tube.update({"name": want})

        if have("pathways"):
            for seq, pathway in enumerate(plant.cable_route(nb, key), start=1):
                seg = nb.plugins.pathways.cable_segments.get(cable_id=cable.id, sequence=seq)
                if seg is None:
                    nb.plugins.pathways.cable_segments.create(cable=cable.id, pathway=pathway.id, sequence=seq)
                elif (seg.pathway.id if seg.pathway else None) != pathway.id:
                    seg.update({"pathway": pathway.id})
            report("route", cable, "exists", f"{len(M.legs(key))} segments, {km} km")
    if not types:
        skip("fms", "fiber cable records and tube names for the ring cables")
    if not have("pathways"):
        skip("pathways", "routes through the ducts for the ring cables")
    return plant_


def _port_id(port):
    return port if isinstance(port, int) or port is None else port.id


def strand_ports(nb, plant_):
    """Land every strand on its panel port: strands 2n-1 and 2n of a trunk are pair n, port n at both ends."""
    print("== Strands on panel ports ==")
    if not have("fms"):
        skip("fms", "landing strands on panel ports")
        return
    for key, info in plant_.items():
        ports = {side: {fp.name: fp.id for fp in nb.dcim.front_ports.filter(device=info[side])} for side in ("a", "b")}
        updates = []
        for strand in nb.plugins.fms.fiber_strands.filter(fiber_cable_id=info["fiber_cable"].id, limit=0):
            pair = (strand.position + 1) // 2
            want = {"front_port_a": ports["a"][f"Port {pair}"], "front_port_b": ports["b"][f"Port {pair}"]}
            if (_port_id(strand.front_port_a), _port_id(strand.front_port_b)) != (want["front_port_a"], want["front_port_b"]):
                updates.append({"id": strand.id, **want})
        if updates:
            nb.plugins.fms.fiber_strands.update(updates)
        print(f"  [{'updated' if updates else 'exists '}] {key}: {len(updates)} of {info['strands']} strands landed on "
              f"{info['a']} / {info['b']}")


def fiber_circuits(nb, plant_):
    """One netbox-fms fiber circuit per trunk pair in use or leased, between the two panel ports of the pair.

    netbox-fms 0.6 derives the fiber paths itself from the strands landed on the ports, so the circuit is assigned
    the path between its end ports. Earlier releases stored two traced paths (the duplex pair's two strands)."""
    print("== FMS fiber circuits ==")
    if not have("fms"):
        skip("fms", "fiber circuits")
        return
    tenants = {t["code"]: nb.tenancy.tenants.get(slug=t["slug"]) for t in TENANTS}
    derived = version_at_least("fms", 0, 6)
    for fc in T.FIBER_CIRCUITS:
        info = plant_[fc["trunk"]]
        (origin_dev, origin_port), far = T.circuit_ends(fc)
        origin = nb.dcim.front_ports.get(device=origin_dev, name=f"Port {origin_port}")
        tenant = tenants[fc.get("tenant", "nordfiber")]
        circuit, st = ensure(nb.plugins.fms.fiber_circuits, {"cid": fc["cid"]}, name=fc["name"], cid=fc["cid"],
                             status="active", strand_count=2, tenant=tenant.id, description=fc["description"])
        report("fiber circuit", circuit, st, fc["cid"])
        loss = round(info["km"] * T.FIBER_CIRCUIT_LOSS_DB_PER_KM + T.FIBER_CIRCUIT_CONNECTOR_LOSS_DB, 2)
        if derived:
            end = nb.dcim.front_ports.get(device=far[0], name=f"Port {far[1]}")
            _assign_derived_path(nb, circuit, fc, origin, end, loss)
            continue
        for position in (1, 2):
            path, st = ensure(nb.plugins.fms.fiber_circuit_paths, {"circuit_id": circuit.id, "position": position},
                              once=("path",), circuit=circuit.id, position=position, origin=origin.id,
                              path=[{"type": "front_port", "id": origin.id}],     # a seed; the retrace below fills it in
                              wavelength_nm=T.FIBER_CIRCUIT_WAVELENGTH_NM, actual_loss_db=loss)
            report(f"  path {position}", path, st, f"{origin_dev} : Port {origin_port}, {loss:.2f} dB")
        api(f"/api/plugins/fms/fiber-circuits/{circuit.id}/retrace/", method="post")
        if not all(p.is_complete for p in nb.plugins.fms.fiber_circuit_paths.filter(circuit_id=circuit.id)):
            raise SystemExit(f"{fc['name']}: FMS did not trace a complete path")


def _derived_paths(nb, a, b):
    """The fiber paths netbox-fms has derived between two front ports, whichever end is listed first."""
    found = list(nb.plugins.fms.fiber_strand_paths.filter(end_a_port_id=a.id, end_b_port_id=b.id))
    return found + list(nb.plugins.fms.fiber_strand_paths.filter(end_a_port_id=b.id, end_b_port_id=a.id))


def _wait_for_analysis(nb, wait_seconds):
    """Wait until netbox-fms has worked off its path analysis queue (the plant changes of the strand landings).

    Assigning a path while the analysis is still replacing paths failed once on an empty NetBox (HTTP 500)."""
    deadline, quiet = time.time() + wait_seconds, 0
    while time.time() < deadline:
        quiet = quiet + 1 if nb.plugins.fms.path_analysis_queue.count() == 0 else 0
        if quiet >= 2:
            return
        time.sleep(3)


def _assign_derived_path(nb, circuit, fc, a, b, loss, wait_seconds=180):
    """Assign the derived path between ports a and b to the circuit (netbox-fms 0.6), with its optical figures.

    The analysis runs as a background job after strands are landed, so the path can appear some seconds later."""
    _wait_for_analysis(nb, wait_seconds)
    deadline = time.time() + wait_seconds
    state = "exists"
    for attempt in range(1, 6):
        paths = _derived_paths(nb, a, b)
        while not any(p.completeness == "terminated_terminated" for p in paths) and time.time() < deadline:
            time.sleep(3)
            paths = _derived_paths(nb, a, b)
        complete = [p for p in paths if p.completeness == "terminated_terminated"]
        if not complete:
            raise SystemExit(f"{fc['name']}: netbox-fms has derived no complete fiber path from {a.device.name} {a.name} "
                             f"to {b.device.name} {b.name} after {wait_seconds} s (is the NetBox worker running?)")
        wanted = {complete[0].id}
        assigned = list(nb.plugins.fms.fiber_circuit_paths.filter(circuit_id=circuit.id))
        for stale in [x for x in assigned if x.strand_path.id not in wanted]:
            stale.delete()
            assigned.remove(stale)
        if assigned:
            break
        try:
            api(f"/api/plugins/fms/fiber-circuits/{circuit.id}/assign/", method="post",
                json={"strand_paths": sorted(wanted)})
        except requests.HTTPError as e:
            # the paths can still be replaced by a running analysis: look again after a pause
            print(f"  [retry  ] assign for {fc['cid']} answered HTTP {e.response.status_code} (attempt {attempt}): "
                  f"{e.response.text[:200]!r}")
            if attempt == 5:
                raise
            time.sleep(10)
            _wait_for_analysis(nb, wait_seconds)
            continue
        assigned = list(nb.plugins.fms.fiber_circuit_paths.filter(circuit_id=circuit.id))
        state = "created"
        break
    for x in assigned:
        change = {}
        if x.wavelength_nm != T.FIBER_CIRCUIT_WAVELENGTH_NM:
            change["wavelength_nm"] = T.FIBER_CIRCUIT_WAVELENGTH_NM
        if x.actual_loss_db is None or abs(float(x.actual_loss_db) - loss) > 1e-6:
            change["actual_loss_db"] = loss
        if change:
            x.update(change)
            state = "updated" if state == "exists" else state
        report("  path", x, state, f"{a.device.name} : {a.name} -> {b.device.name} : {b.name}, {loss:.2f} dB")


def geometries(nb):
    print("== Circuit geometries ==")
    if not have("pathways"):
        skip("pathways", "circuit geometries for the leased circuits")
        return
    for c in T.CIRCUITS:
        if "geometry" not in c:
            continue
        route = T.ROUTES[c["geometry"]]
        circuit = nb.circuits.circuits.get(cid=c["cid"])
        names = " -> ".join(n for n, _, _ in route if n)
        geom = nb.plugins.pathways.circuit_geometries.get(circuit_id=circuit.id)
        if geom is None:
            geom = nb.plugins.pathways.circuit_geometries.create(circuit=circuit.id, path=linestring(route), comments=names)
            report("circuit geometry", geom, "created", c["cid"])
        else:
            changed = {}
            if (geom.path.coordinates if geom.path else None) != [[lon, lat] for _, lon, lat in route]:
                changed["path"] = linestring(route)
            if geom.comments != names:
                changed["comments"] = names
            if changed:
                geom.update(changed)
            report("circuit geometry", geom, "updated" if changed else "exists", c["cid"])


def cabled_terminations(cabler):
    print("== Cabled circuit terminations ==")
    for cid, side, far, note in T.CABLED_TERMINATIONS:
        cabler.connect(CT(cid, side), far, note=f"{cid} ({side}): {note}")


def run(nb):
    circuits(nb)
    if have("pathways"):
        plant.run(nb)
    else:
        skip("pathways", "the metro plant (structures, ducts, water crossings)")
    cabler = Cabler(nb)
    types = cable_types(nb)
    plant_ = long_haul(nb, cabler, types)
    plant_.update(metro_cables(nb, cabler, types))
    strand_ports(nb, plant_)
    fiber_circuits(nb, plant_)
    geometries(nb)
    cabled_terminations(cabler)
    cabler.summary()


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nLayer 4 (transport) complete.")
