"""
The Stockholm metro ring: three cables between Nordfiber's three Stockholm datacenters (availability zones), run
through real ducts, structure by structure, in the territory of the municipalities along the way.

  link   from -> to                  cable                         owner of the cable
  nw     North (Sollentuna) -> West (Södertälje), via Hässelby, Färingsö and Ekerö
                                     288-fiber ALTOS, 144 pairs    Nordfiber
  ne     North (Sollentuna) -> East (Nacka), via Danderyd, Lidingö and Orminge
                                     288-fiber ALTOS, 144 pairs    Nordfiber
  we     West (Södertälje) -> East (Nacka), along the E4/E20 and road 222
                                     288-fiber ALTOS, 144 pairs    Stockholm Metro Fibre AB, leased whole

Three different parties are involved in every segment, and the dataset keeps them apart:
  * the DUCT is owned by the municipality it lies in (Pathway.tenant) and installed by a contractor (installed_by);
    the water crossings are Nordfiber's own submarine pathways;
  * the CABLE has its own owner (dcim.Cable.tenant): Nordfiber, or the telecom that leases its cable to Nordfiber;
  * the LESSEE is Nordfiber (a dark-fiber circuit, as with the vendor spans to Helsinki).

For redundancy the three links are routed as dispersed as possible: each datacenter has two separate building
entrances, one per link, and no structure or duct outside the buildings is shared between two links (verify.py checks
it). The geometry (stations, legs, the municipal borders where the owner changes) is derived from OpenStreetMap by
tools/derive_metro.py and stored in data/metro_geometry.py; the municipalities are real, but the ownership and the
ducts are invented for the scenario.

A leg is "bank" (a concrete-encased duct bank with our conduit and innerduct in it: the lead-in at a datacenter),
"duct" (a conduit with our innerduct in it) or "sub" (a submarine pathway, a water crossing). The cable runs through the
innermost pathway of each leg, the innerduct, or the submarine pathway itself.

Coordinates are (lon, lat).
"""

import math

from data.metro_geometry import GEOMETRY


def code(name):
    """'Södertälje' -> 'sodertalje': the party code of a municipality."""
    out = name.lower().replace("å", "a").replace("ä", "a").replace("ö", "o").replace(" ", "-")
    return {"danderyds": "danderyd", "salems": "salem", "sundbybergs": "sundbyberg", "stockholms": "stockholm",
            "nykvarns": "nykvarn", "jarfallas": "jarfalla", "upplands-bros": "upplands-bro"}.get(out, out)


# Static facts of each link. The stations, legs and roads come from the generated geometry.
_LINKS = [
    {"key": "nw", "name": "North - West", "a": "stn", "b": "stw", "cable_owner": "nordfiber", "circuit": None,
     "a_panel": "stn-patch-stw-01", "b_panel": "stw-patch-stn-01", "installed": "2025-02-10",
     "route": "Stockholm North (Sollentuna) - Stockholm West (Södertälje) via Hässelby, Färingsö and Ekerö"},
    {"key": "ne", "name": "North - East", "a": "stn", "b": "ste", "cable_owner": "nordfiber", "circuit": None,
     "a_panel": "stn-patch-ste-01", "b_panel": "ste-patch-stn-01", "installed": "2025-03-12",
     "route": "Stockholm North (Sollentuna) - Stockholm East (Nacka) via Danderyd, Lidingö and Orminge"},
    {"key": "we", "name": "West - East", "a": "stw", "b": "ste", "cable_owner": "smf", "circuit": "SMF-DF-0001",
     "a_panel": "stw-patch-ste-01", "b_panel": "ste-patch-stw-01", "installed": "2024-10-01",
     "route": "Stockholm West (Södertälje) - Stockholm East (Nacka) along the E4/E20 and road 222"},
]

_USE = ("Pair 1 lit with DWDM, pairs 2-72 reserved for WDM, pairs 73-96 Nordfiber dark fiber, pairs 97-144 "
        "leasable dark fiber")

LINKS = []
for _l in _LINKS:
    _g = GEOMETRY[_l["key"]]
    _l = dict(_l)
    _l["stations"] = [(n, t, lon, lat, code(o)) for n, t, lon, lat, o in _g["stations"]]
    _l["legs"] = [(kind, code(owner)) for kind, owner, _via in _g["legs"]]
    _l["via"] = [[tuple(p) for p in via] for _kind, _owner, via in _g["legs"]]
    _l["roads"] = _g["roads"]
    _owners = sorted({o for k, o in _l["legs"] if k != "sub"})
    _subs = sum(1 for k, _o in _l["legs"] if k == "sub")
    _ducts = f"in the ducts of {len(_owners)} municipalities" + (f" and {_subs} water crossing{'s' if _subs > 1 else ''}" if _subs else "")
    _own = "Nordfiber-owned" if _l["cable_owner"] == "nordfiber" else "leased"
    if _l["circuit"]:
        _l["note"] = f"{_l['circuit']}: leased 288-fiber metro cable (Stockholm Metro Fibre AB), {_l['route']}, {_ducts}"
        _l["fms_note"] = (f"Owned by Stockholm Metro Fibre AB and leased whole to Nordfiber AB under {_l['circuit']}. "
                          f"Side of the Stockholm metro ring, 144 pairs (288 fibers). {_USE}.")
    else:
        _l["note"] = f"{_own} 288-fiber metro cable, {_l['route']}, {_ducts}"
        _l["fms_note"] = f"Owned by Nordfiber AB. Side of the Stockholm metro ring, 144 pairs (288 fibers). {_USE}" + (
            " (pair 97 is leased to Baltic Retail Group)." if _l["key"] == "ne" else ".")
    LINKS.append(_l)

# Our duct and cable sizes. The cable is about 18 mm across; the innerduct leaves room to pull a second one later.
BANK = {"configuration": "1x4", "total_conduits": 4, "encasement_type": "concrete", "conduit_position": "A1",
        "material": "pvc", "inner_diameter": 100.0, "outer_diameter": 110.0}
DUCT = {"material": "hdpe", "inner_diameter": 100.0, "outer_diameter": 110.0, "depth": 1.2}
INNERDUCT = {"size": "40/33 mm", "color": "orange", "position": "1"}

def short(owner):
    """How the owner of a leg reads in a label: the municipality's short name."""
    if owner == "nordfiber":
        return "Nordfiber"
    from data.municipalities import NAMES
    return NAMES[owner][2]


def km_between(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(a))


def link(key):
    return next(l for l in LINKS if l["key"] == key)


def legs(key):
    """The legs of a link, in cable order: label, kind, owner, the two stations, the path and its length in metres."""
    l = link(key)
    out = []
    for n, ((kind, owner), via, a, b) in enumerate(zip(l["legs"], l["via"], l["stations"], l["stations"][1:]), start=1):
        path = [(a[2], a[3])] + via + [(b[2], b[3])]
        metres = sum(km_between(*p, *q) for p, q in zip(path, path[1:])) * 1000
        out.append({
            "n": n, "kind": kind, "owner": owner, "a": a[0], "b": b[0], "metres": round(metres, 1), "path": path,
            "label": f"{key.upper()}-{n:02d} {short(owner)}",
        })
    return out


def structures():
    """Every structure of every link: name -> (type, lon, lat, owner, the link's key)."""
    out = {}
    for l in LINKS:
        for name, stype, lon, lat, owner in l["stations"]:
            out[name] = (stype, lon, lat, owner, l["key"])
    return out


def cable_km(key):
    return round(sum(leg["metres"] for leg in legs(key)) / 1000, 1)


def municipalities():
    """The municipality codes that own ducts anywhere on the ring."""
    return sorted({o for l in LINKS for k, o in l["legs"] if k != "sub"} |
                  {o for l in LINKS for _n, _t, _x, _y, o in l["stations"] if o != "nordfiber"})


def _route(key):
    """Every point of the link's path as (name, lon, lat); points between stations have an empty name."""
    out = [(link(key)["stations"][0][0], *link(key)["stations"][0][2:4])]
    for leg, l_ in zip(legs(key), link(key)["stations"][1:]):
        out += [("", lon, lat) for lon, lat in leg["path"][1:-1]]
        out.append((leg["b"], l_[2], l_[3]))
    return out


# The route of each link as (name, lon, lat) waypoints, for the leased circuit's geometry.
ROUTES = {l["key"]: _route(l["key"]) for l in LINKS}

# The entrances of each datacenter, one per link.
ENTRANCES = {"stn": {"nw": "STN-ENT-W", "ne": "STN-ENT-E"},
             "stw": {"nw": "STW-ENT-N", "we": "STW-ENT-E"},
             "ste": {"ne": "STE-ENT-N", "we": "STE-ENT-S"}}
