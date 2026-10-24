#!/usr/bin/env python3
"""
Dump the dataset's NetBox state to a deterministic JSON file, for comparing
two builds (e.g. before/after a refactor, or live vs. a clean replay).

    python tools/dump_state.py reference/state-before-refactor.json

Read-only. Everything is keyed by something stable (names, endpoint pairs)
rather than database ids, so two dumps from two different databases can be
diffed with tools/diff_state.py.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import connect, have  # noqa: E402


def val(x):
    """Unwrap a pynetbox choice/nested record to a plain comparable value."""
    if x is None:
        return None
    if hasattr(x, "value"):
        return x.value
    if hasattr(x, "slug"):
        return x.slug
    if hasattr(x, "name"):
        return x.name
    if hasattr(x, "cid"):
        return x.cid
    return x


def endpoint(t):
    ot = t.object_type
    o = t.object
    if ot == "circuits.circuittermination":
        return f"circuit:{o.circuit.cid}:{o.term_side}"
    return f"{ot.split('.')[1]}:{o.device.name}:{o.name}"


def run(nb):
    s = {}

    s["sites"] = {x.slug: dict(name=x.name, group=val(x.group), region=val(x.region), tenant=val(x.tenant),
                                description=x.description, facility=x.facility) for x in nb.dcim.sites.all()}
    s["locations"] = {x.slug: dict(name=x.name, site=val(x.site), parent=val(x.parent)) for x in nb.dcim.locations.all()}
    s["racks"] = {x.name: dict(site=val(x.site), location=val(x.location), tenant=val(x.tenant), u_height=x.u_height)
                  for x in nb.dcim.racks.all()}
    s["tenants"] = {x.slug: dict(name=x.name, group=val(x.group), description=x.description) for x in nb.tenancy.tenants.all()}
    s["providers"] = {x.slug: dict(name=x.name, description=x.description) for x in nb.circuits.providers.all()}

    s["devices"] = {}
    for d in nb.dcim.devices.all():
        s["devices"][d.name] = dict(
            type=val(d.device_type), role=val(d.role), site=val(d.site), location=val(d.location),
            rack=val(d.rack), position=d.position, face=val(d.face), tenant=val(d.tenant), status=val(d.status),
            serial=d.serial, asset_tag=d.asset_tag, primary_ip4=str(d.primary_ip4) if d.primary_ip4 else None,
        )

    s["cables"] = {}
    for c in nb.dcim.cables.all():
        ends = sorted(endpoint(t) for t in list(c.a_terminations) + list(c.b_terminations))
        key = " <> ".join(ends)
        s["cables"][key] = dict(
            label=c.label, type=val(c.type), color=c.color, length=c.length, length_unit=val(c.length_unit),
            tenant=val(c.tenant), status=val(c.status), description=c.description, comments=c.comments,
            custom_fields={k: v for k, v in (c.custom_fields or {}).items() if v},
        )

    s["circuits"] = {}
    for c in nb.circuits.circuits.all():
        terms = {t.term_side: dict(site=val(t.termination), port_speed=t.port_speed)
                 for t in nb.circuits.circuit_terminations.filter(circuit_id=c.id)}
        s["circuits"][c.cid] = dict(provider=val(c.provider), type=val(c.type), tenant=val(c.tenant),
                                    commit_rate=c.commit_rate, description=c.description, terminations=terms)

    s["ip_addresses"] = {str(i.address): dict(tenant=val(i.tenant),
                                              assigned=(f"{i.assigned_object.device.name}:{i.assigned_object.name}"
                                                        if i.assigned_object else None))
                         for i in nb.ipam.ip_addresses.all()}
    s["prefixes"] = {str(p.prefix): dict(description=p.description, tenant=val(p.tenant)) for p in nb.ipam.prefixes.all()}

    s["contacts"] = {c.name: dict(title=c.title) for c in nb.tenancy.contacts.all()}
    assignments = []
    for a in nb.tenancy.contact_assignments.all():
        assignments.append(f"{a.contact.name} | {val(a.role)} | {a.object_type} | {getattr(a.object, 'name', a.object_id)}")
    s["contact_assignments"] = sorted(assignments)

    s["modules"] = sorted(f"{m.device.name}:{m.module_bay.name}:{m.module_type.model}" for m in nb.dcim.modules.all())

    # plugins (a section is left out when its plugin is not installed)
    if have("wdm"):
        s["wdm"] = {
            "nodes": {},
            "circuits": {},
            "wavelength_path_rows": len(list(nb.plugins.wdm.wdm_wavelength_paths.all())),
        }
        for n in nb.plugins.wdm.wdm_nodes.all():
            dev = nb.dcim.devices.get(id=n.device.id if hasattr(n.device, "id") else n.device)
            s["wdm"]["nodes"][dev.name] = len(list(nb.plugins.wdm.wdm_channels.filter(wdm_node_id=n.id)))
        for c in nb.plugins.wdm.wdm_circuits.all():
            s["wdm"]["circuits"][c.name] = dict(tenant=val(c.tenant), status=val(c.status))

    if have("fms"):
        fms = []
        for fc in nb.plugins.fms.fiber_cables.all():
            cable = nb.dcim.cables.get(id=fc.cable.id if hasattr(fc.cable, "id") else fc.cable)
            fms.append(" <> ".join(sorted(endpoint(t) for t in list(cable.a_terminations) + list(cable.b_terminations))))
        s["fms_fiber_cables"] = sorted(fms)

    if have("pathways"):
        s["pathways"] = {p.label: dict(coordinates=p.path.coordinates if p.path else None, comments=p.comments)
                         for p in nb.plugins.pathways.direct_buried.all()}
        s["cable_segments"] = sorted(f"{x.cable.label} -> {x.pathway.label}" for x in nb.plugins.pathways.cable_segments.all())
        s["circuit_geometries"] = {}
        for g in nb.plugins.pathways.circuit_geometries.all():
            cid = g.circuit.cid if hasattr(g.circuit, "cid") else g.circuit
            s["circuit_geometries"][cid] = g.path.coordinates if g.path else None

    if have("bgp"):
        s["bgp_sessions"] = sorted(x.name for x in nb.plugins.bgp.session.all())
    if have("secrets"):
        s["secrets"] = sorted(f"{x.assigned_object.name}:{x.name}" for x in nb.plugins.secrets.secrets.all()
                              if getattr(x, "assigned_object", None))
    return s


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "state.json"
    nb = connect()
    data = run(nb)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True, ensure_ascii=False, default=str)
    print(f"wrote {out}: " + ", ".join(f"{k}={len(v)}" for k, v in data.items() if hasattr(v, "__len__")))
