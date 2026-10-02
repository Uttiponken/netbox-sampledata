#!/usr/bin/env python3
"""
Layer 4: transport — everything between sites.

  providers, circuit types, circuits and their terminations
  -> the long-haul cables (Nordfiber's own backbone, the leased Polarlink
     pair, the two vendor spans to Helsinki), each with its fiber-plant
     record (netbox-fms) and its real-world route (netbox-pathways)
  -> circuit geometries for the leased circuits
  -> the few circuit terminations that are physically cabled

A leased dark-fiber circuit stays a commercial record with uncabled
terminations; the physical span is ONE direct Cable between the vendor's
two MeetMe panels (rear to rear). That is the same model as Nordfiber's own
backbone, so a trace follows the glass rather than the contract.

Requires layers 1-3. Safe to re-run.
"""

from cabling import CT, Cabler
from common import connect, ensure, linestring, report, route_km
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

    print("== Long-haul cables, fiber plant and routes ==")
    for key, a, b, note, fms_note in T.LONG_HAUL:
        route = T.ROUTES[key]
        km = route_km(route)
        # the leased Polarlink pair has no Tenant of its own; it is Nordfiber's cable
        own = key in ("bb1", "bb2", "bb3", "bb4")
        cable = cabler.connect(("rearport",) + a, ("rearport",) + b, note=note,
                               tenant="nordfiber-ab" if own else None, km=km)

        if not nb.plugins.fms.fiber_cables.get(cable_id=cable.id):
            fc = nb.plugins.fms.fiber_cables.create(cable=cable.id, fiber_cable_type=cable_type.id, notes=fms_note)
            report("fiber cable", fc, "created", cable.label)

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
    long_haul(nb, cabler)
    geometries(nb)
    cabled_terminations(cabler)
    cabler.summary()


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nLayer 4 (transport) complete.")
