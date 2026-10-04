#!/usr/bin/env python3
"""
Layer 4: transport — everything between sites.

  providers, circuit types, circuits and their terminations
  -> the long-haul cables (Nordfiber's own backbone, the leased Polarlink
     pair, the two vendor spans to Helsinki), each with its fiber-plant
     record (netbox-fms) and its real-world route (netbox-pathways)
  -> every strand landed on its panel port, and a fiber circuit (netbox-fms)
     for each trunk pair that is in use
  -> circuit geometries for the leased circuits
  -> the few circuit terminations that are physically cabled

A leased dark-fiber circuit stays a commercial record with uncabled
terminations; the physical span is ONE direct Cable between the vendor's
two MeetMe panels (rear to rear). That is the same model as Nordfiber's own
backbone, so a trace follows the glass rather than the contract.

Requires layers 1-3. Safe to re-run.
"""

from cabling import CT, Cabler
from common import api, connect, ensure, linestring, report, route_km
from data import optical as O
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


def long_haul(nb, cabler):
    print("== FMS cable type ==")
    spec = dict(T.FMS_CABLE_TYPE)
    mfr = nb.dcim.manufacturers.get(slug=spec.pop("manufacturer"))
    cable_type, st = ensure(nb.plugins.fms.cable_types, {"model": spec["model"]}, manufacturer=mfr.id, **spec)
    report("fms cable type", cable_type, st)
    if st == "created":
        for tube in T.FMS_BUFFER_TUBES:
            nb.plugins.fms.buffer_tube_templates.create(fiber_cable_type=cable_type.id, **tube)

    tenants = {t["code"]: nb.tenancy.tenants.get(slug=t["slug"]) for t in TENANTS}
    plant = {}
    print("== Long-haul cables, fiber plant and routes ==")
    for key, a, b, note, fms_note in T.LONG_HAUL:
        route = T.ROUTES[key]
        km = route_km(route)
        # the leased Polarlink pair has no Tenant of its own; it is Nordfiber's cable
        own = key in ("bb1", "bb2", "bb3", "bb4")
        cable = cabler.connect(("rearport",) + a, ("rearport",) + b, note=note,
                               tenant="nordfiber-ab" if own else None, km=km)

        detail = T.FIBER_DETAILS[key]
        installer = tenants.get(detail["installer"]) if detail["installer"] else None
        fc, st = ensure(nb.plugins.fms.fiber_cables, {"cable_id": cable.id}, cable=cable.id, fiber_cable_type=cable_type.id,
                        notes=fms_note, serial_number=detail["serial_number"], install_date=detail["install_date"],
                        installed_by=installer.id if installer else None, start_mark=0, end_mark=round(km * 1000))
        report("fiber cable", fc, st, cable.label)
        plant[key] = {"fiber_cable": fc, "a": a[0], "b": b[0], "km": km}

        label = f"{cable.label}-route"
        names = " -> ".join(n for n, _, _ in route)
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
    return plant


def _port_id(port):
    return port if isinstance(port, int) or port is None else port.id


def strand_ports(nb, plant):
    """Land every strand on its panel port: strands 2n-1 and 2n of a trunk are pair n, port n at both ends."""
    print("== Strands on panel ports ==")
    for key, info in plant.items():
        ports = {side: {fp.name: fp.id for fp in nb.dcim.front_ports.filter(device=info[side])} for side in ("a", "b")}
        updates = []
        for strand in nb.plugins.fms.fiber_strands.filter(fiber_cable_id=info["fiber_cable"].id, limit=0):
            pair = (strand.position + 1) // 2
            want = {"front_port_a": ports["a"][f"Port {pair}"], "front_port_b": ports["b"][f"Port {pair}"]}
            if (_port_id(strand.front_port_a), _port_id(strand.front_port_b)) != (want["front_port_a"], want["front_port_b"]):
                updates.append({"id": strand.id, **want})
        if updates:
            nb.plugins.fms.fiber_strands.update(updates)
        print(f"  [{'updated' if updates else 'exists '}] {key}: {len(updates)} of 48 strands landed on {info['a']} / {info['b']}")


def fiber_circuits(nb, plant):
    """One netbox-fms fiber circuit per trunk pair in use, two paths (the duplex pair's two strands), traced."""
    print("== FMS fiber circuits ==")
    tenant = nb.tenancy.tenants.get(slug=next(t["slug"] for t in TENANTS if t["code"] == "nordfiber"))
    for fc in T.FIBER_CIRCUITS:
        info = plant[fc["trunk"]]
        origin_dev, origin_port = O.LINE_PATCH[fc["wdms"][0]]
        origin = nb.dcim.front_ports.get(device=origin_dev, name=f"Port {origin_port}")
        circuit, st = ensure(nb.plugins.fms.fiber_circuits, {"cid": fc["cid"]}, name=fc["name"], cid=fc["cid"],
                             status="active", strand_count=2, tenant=tenant.id, description=fc["description"])
        report("fiber circuit", circuit, st, fc["cid"])
        loss = round(info["km"] * T.FIBER_CIRCUIT_LOSS_DB_PER_KM + T.FIBER_CIRCUIT_CONNECTOR_LOSS_DB, 2)
        for position in (1, 2):
            path, st = ensure(nb.plugins.fms.fiber_circuit_paths, {"circuit_id": circuit.id, "position": position},
                              once=("path",), circuit=circuit.id, position=position, origin=origin.id,
                              path=[{"type": "front_port", "id": origin.id}],     # a seed; the retrace below fills it in
                              wavelength_nm=T.FIBER_CIRCUIT_WAVELENGTH_NM, actual_loss_db=loss)
            report(f"  path {position}", path, st, f"{origin_dev} : Port {origin_port}, {loss:.2f} dB")
        api(f"/api/plugins/fms/fiber-circuits/{circuit.id}/retrace/", method="post")
        if not all(p.is_complete for p in nb.plugins.fms.fiber_circuit_paths.filter(circuit_id=circuit.id)):
            raise SystemExit(f"{fc['name']}: FMS did not trace a complete path")


def geometries(nb):
    print("== Circuit geometries ==")
    for c in T.CIRCUITS:
        if "geometry" not in c:
            continue
        route = T.ROUTES[c["geometry"]]
        circuit = nb.circuits.circuits.get(cid=c["cid"])
        names = " -> ".join(n for n, _, _ in route)
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
    cabler = Cabler(nb)
    plant = long_haul(nb, cabler)
    strand_ports(nb, plant)
    fiber_circuits(nb, plant)
    geometries(nb)
    cabled_terminations(cabler)
    cabler.summary()


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nLayer 4 (transport) complete.")
