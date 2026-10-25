#!/usr/bin/env python3
"""
Layer 4a: the metro plant — structures, ducts and water crossings of the Stockholm ring (netbox-pathways).

  structures (datacenter entrances, handholes, manholes, vaults), each owned by the municipality whose ground it
  stands in -> per leg of each ring link: a duct bank with our conduit and innerduct (the lead-in at a datacenter),
  or a conduit with our innerduct (a municipal duct), or a submarine pathway (a water crossing, Nordfiber's own)

This is the part of the dataset you can look at on the pathways map before any cable is laid: it needs only
layer 1 (sites and tenants), and netbox-pathways (without the plugin the layer is skipped). The cables follow in layer 4 (04_transport.py), which routes each of them through the
innermost pathway of every leg, in order. Safe to re-run.

    python plant.py
"""

from common import connect, ensure, have, report, skip, version_at_least
from data import metro as M
from data.organization import TENANTS



# netbox-pathways 0.3.0 moved a structure's map point from `location` to `geometry` (`location` became a link to a
# NetBox Location) and made an innerduct's colour a hex code (the migration turned "orange" into ff9800). Both are
# decided when the plugin has been detected (connect()), not when this module is imported.
def _point_field():
    return "geometry" if version_at_least("pathways", 0, 3) else "location"


def _innerduct_color():
    color = M.INNERDUCT["color"]
    return {"orange": "ff9800"}.get(color, color) if version_at_least("pathways", 0, 3) else color


def point(lon, lat):
    return f"POINT ({lon} {lat})"


def line(path):
    return "LINESTRING (" + ", ".join(f"{lon} {lat}" for lon, lat in path) + ")"


def _geom_matches(current, wanted):
    """`current` is a GeoJSON geometry from the API (or None), `wanted` a list of (lon, lat)."""
    return current is not None and [list(c) for c in current.coordinates] == [list(w) for w in wanted]


def _tenants(nb):
    return {t["code"]: nb.tenancy.tenants.get(slug=t["slug"]) for t in TENANTS}


def structures(nb, tenants, sites):
    print("== Structures ==")
    made = {}
    entrance_sites = {name: code for code, links in M.ENTRANCES.items() for name in links.values()}
    field = _point_field()
    for name, (stype, lon, lat, owner, _link) in M.structures().items():
        site = sites[entrance_sites[name]] if name in entrance_sites else None
        obj, st = ensure(nb.plugins.pathways.structures, {"name": name}, once=(field,),
                         name=name, structure_type=stype, status="active", **{field: point(lon, lat)},
                         tenant=tenants[owner].id, site=site.id if site else None)
        # the API returns the point as GeoJSON, so it is compared apart (and a moved structure is moved)
        current = getattr(obj, field)
        if current is None or [round(c, 5) for c in current.coordinates] != [round(lon, 5), round(lat, 5)]:
            obj.update({field: point(lon, lat)})
            st = "updated"
        report("structure", obj, st, f"{stype}, {M.short(owner)}")
        made[name] = obj
    return made


def _pathway(endpoint, label, path, kind_fields, **fields):
    """Create or reconcile a pathway of any kind; the geometry is compared apart because the API returns GeoJSON."""
    obj, st = ensure(endpoint, {"label": label}, once=("path",), label=label, path=line(path), **fields, **kind_fields)
    if not _geom_matches(obj.path, path):
        obj.update({"path": line(path)})
        st = "updated"
    return obj, st


def legs(nb, tenants, made):
    print("== Ducts and water crossings ==")
    installer = tenants["mkab"]
    for l in M.LINKS:
        cable_owner = tenants[l["cable_owner"]]
        for leg in M.legs(l["key"]):
            owner = tenants[leg["owner"]]
            a, b = made[leg["a"]], made[leg["b"]]
            common = dict(start_structure=a.id, end_structure=b.id, tenant=owner.id, installed_by=installer.id,
                          length=leg["metres"], installation_date=l["installed"])
            base, path = leg["label"], leg["path"]
            km = f"{leg['metres'] / 1000:.1f} km"
            who = f"{M.short(leg['owner'])}, {leg['a']} - {leg['b']}, {km}"
            if leg["kind"] == "sub":
                obj, st = _pathway(nb.plugins.pathways.pathways, f"{base} submarine crossing", path,
                                   {"pathway_type": "submarine"}, comments=f"Water crossing, {who}. Nordfiber's own pathway.",
                                   **common)
                report("submarine", obj, st, who)
                continue
            parent = None
            if leg["kind"] == "bank":
                bank, st = _pathway(nb.plugins.pathways.conduit_banks, f"{base} duct bank", path,
                                    {"configuration": M.BANK["configuration"], "total_conduits": M.BANK["total_conduits"],
                                     "encasement_type": M.BANK["encasement_type"]},
                                    comments=f"Concrete-encased 1x4 duct bank at the datacenter, {who}.", **common)
                report("duct bank", bank, st, who)
                parent, st = _pathway(nb.plugins.pathways.conduits, f"{base} conduit {M.BANK['conduit_position']}", path,
                                      {"material": M.BANK["material"], "inner_diameter": M.BANK["inner_diameter"],
                                       "outer_diameter": M.BANK["outer_diameter"], "conduit_bank": bank.id,
                                       "bank_position": M.BANK["conduit_position"]},
                                      comments=f"Nordfiber's conduit in the bank, {who}.", **common)
            else:
                parent, st = _pathway(nb.plugins.pathways.conduits, f"{base} conduit", path,
                                      {"material": M.DUCT["material"], "inner_diameter": M.DUCT["inner_diameter"],
                                       "outer_diameter": M.DUCT["outer_diameter"], "depth": M.DUCT["depth"]},
                                      comments=f"Municipal duct, {who}.", **common)
            report("conduit", parent, st, who)
            # The innerduct belongs to whoever owns the cable (inside a conduit the municipality owns). The innerduct
            # endpoint has no tenant field, so the owner is set on the base pathway.
            inner_fields = {k: v for k, v in common.items() if k != "tenant"}
            inner, st = _pathway(nb.plugins.pathways.innerducts, f"{base} innerduct", path,
                                 {"parent_conduit": parent.id, "size": M.INNERDUCT["size"], "color": _innerduct_color(),
                                  "position": M.INNERDUCT["position"]},
                                 comments=f"Innerduct that carries the metro cable, {who}.", **inner_fields)
            as_pathway = nb.plugins.pathways.pathways.get(inner.id)
            if (as_pathway.tenant.id if as_pathway.tenant else None) != cable_owner.id:
                as_pathway.update({"tenant": cable_owner.id})
                st = "updated" if st == "exists" else st
            report("innerduct", inner, st, f"{who}, owner {cable_owner.name}")


def cable_route(nb, key):
    """The pathways a ring cable runs through, in order: the innerduct of each leg, or the submarine pathway."""
    out = []
    for leg in M.legs(key):
        if leg["kind"] == "sub":
            obj = nb.plugins.pathways.pathways.get(label=f"{leg['label']} submarine crossing")
        else:
            obj = nb.plugins.pathways.innerducts.get(label=f"{leg['label']} innerduct")
        if obj is None:
            raise SystemExit(f"pathway for {leg['label']} is missing: run plant.py first")
        out.append(obj)
    return out


def run(nb):
    tenants = _tenants(nb)
    sites = {}
    for s in nb.dcim.sites.all():
        sites[s.slug] = s
    import naming
    from data.organization import SITES
    by_code = {s["code"]: sites[naming.site_slug(s)] for s in SITES}
    made = structures(nb, tenants, by_code)
    legs(nb, tenants, made)


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    if have("pathways"):
        run(nb)
    else:
        skip("pathways", "the metro plant")
    print("\nLayer 4a (metro plant) complete.")
