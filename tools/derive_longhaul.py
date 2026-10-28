#!/usr/bin/env python3
"""
Derive the geometry of the two leased Stockholm - Helsinki routes (data/longhaul_geometry.py) from OpenStreetMap.

A one-off helper, not part of the build: the build reads the file it writes. Like tools/derive_metro.py it exists so the
routes can be reproduced and checked, and so nobody has to believe hand-typed coordinates.

Route 1 (NSN-DF-0001, key "nsn") runs: Stockholm North - road 265 and E18 - Norrtälje - Väddö - Grisslehamn - (sea) -
Eckerö - Mariehamn - Vårdö - (sea) - Kumlinge - (sea) - Korpo - Pargas - Turku - E18 - Salo - (power line corridor) -
Espoo - roads - Helsinki.

Route 2 (BFN-DF-0001, key "bfn") runs: Stockholm East (Nacka) - Handen - Västerhaninge - (railway corridor) - Nynäshamn -
(sea) - Fårösund - roads over Gotland - Ljugarn - (sea) - Ventspils - major roads - Pūre - Riga - Valmiera - Valga -
Viljandi - Imavere - Tallinn - (sea) - Vuosaari harbour - roads - Helsinki.

  1. Land sections are routed on the road network (OSRM demo server, read-only), so the cable follows roads.
  2. Every ferry the road router uses (OSRM step mode "ferry") becomes a submarine leg: no road there.
     A crossing the road network does not know (Kumlinge - Korpo, 46 km through the archipelago; the three open-sea
     crossings of route 2) is routed through the water along the shoreline (tools/waterpath.py), so that the cable passes
     between the islands and not over them.
  3. Past Salo route 1 follows the high-voltage power line corridor (OpenStreetMap power=line, 110 kV and up, found
     with the Overpass API) as far as the outskirts of Helsinki, then roads again. From Västerhaninge to Nynäshamn route 2
     follows the railway (OpenStreetMap railway=rail, the Nynäs line). If Overpass is unavailable, or no connected line is
     found, the section falls back to roads and the report says so.
  4. The result is simplified (Ramer-Douglas-Peucker) and written with an ODbL attribution header.

The output is geometry only. The road, ferry, railway, power line and shoreline data come from OpenStreetMap contributors
(ODbL, https://www.openstreetmap.org/copyright); the cables, their ducts and their owners are invented for the scenario.

    python tools/derive_longhaul.py                 # derives both routes, writes data/longhaul_geometry.py, prints a report
    python tools/derive_longhaul.py bfn             # derives one route; the other is kept as it is in the file
    python tools/derive_longhaul.py --out FILE      # write somewhere else (review)
    python tools/derive_longhaul.py --no-power      # roads all the way from Salo (baseline for comparison)
    python tools/derive_longhaul.py --no-rail       # roads all the way from Västerhaninge (baseline for comparison)
"""

import ast
import heapq
import io
import json
import math
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))      # derive_metro.py and waterpath.py, also under python -I
import derive_metro as dm                      # run_curl, osrm, cumulative, rdp, km, at (shared helpers)
import waterpath                               # routes through the water along the OpenStreetMap shoreline

OUT = "data/longhaul_geometry.py"
FERRY_MIN_M = 300            # an OSRM ferry step shorter than this is a pontoon, not a crossing
LAND_EPS_M = 25              # simplification of land legs
SUB_EPS_M = 250              # simplification of submarine legs
POWER_MIN_V = 110000         # lines of this voltage and up
POWER_HANDOFF_KM = 22        # the corridor is left for roads this far (straight line) from the Helsinki datacenter
POWER_LINK_M = 450           # two line ends closer than this are treated as joined (a substation between them)
RAIL_LINK_M = 100            # two railway ends closer than this are treated as joined (a switch between them)
RAIL_MAX_OFF_KM = 2          # the railway must pass this close to both ends of its section

STN = (17.9200, 59.4405)                       # Stockholm North, the site point
HEL = (24.9384, 60.1699)                       # Helsinki, the site point
NORRTALJE = (18.7048, 59.7573)
ALMSTA = (18.8031, 59.9717)                    # Väddö: keeps the road leg on the island
GRISSLEHAMN = (18.8059, 60.0982)
MARIEHAMN = (19.9413, 60.1024)
HUMMELVIK = (20.4133, 60.2244)                 # Vårdö, the quay of the Kumlinge ferry
KUMLINGE = (20.7782, 60.2588)
KORPO = (21.5950, 60.1789)                     # Galtby, Korpo
TURKU = (22.2670, 60.4516)
SALO = (23.1333, 60.3833)

# Route 2 (Nominatim places; the towns are passed on the major roads, the harbours are where the cable goes to sea)
STE = (18.1660, 59.3125)                       # Stockholm East (Nacka), the site point
HANDEN = (18.15901, 59.16752)                  # road 73 where it passes Handen (the town point is 1 km west, off the road)
VASTERHANINGE = (18.10285, 59.12234)           # Västerhaninge station: the railway corridor begins here
NYNASHAMN = (17.95088, 58.90085)               # Nynäshamn station, at the harbour: the railway corridor ends here
FAROSUND = (19.05089, 57.86303)                # Fårösund, Gotland side of the sound
LJUGARN = (18.70688, 57.33377)
VENTSPILS = (21.5636, 57.39039)
PURE = (22.89593, 57.06237)
RIGA = (24.10518, 56.9494)
VALMIERA = (25.42617, 57.53891)
VALGA = (26.03156, 57.77703)
KARKSI_NUIA = (25.55133, 58.10167)             # keeps Valga - Viljandi on roads 6 and 49 (the router prefers 28 km of local roads)
VILJANDI = (25.58781, 58.36454)
IMAVERE = (25.79094, 58.73531)                 # Imavere, Järva county, on road 2 (Tallinn - Tartu)
TALLINN = (24.75727, 59.43724)
VUOSAARI = (25.17683, 60.21692)                # Vuosaaren satama, the Vuosaari harbour of Helsinki

# A chain per route. kind: "road" (routed; ferries inside it become submarine legs), "water" (a crossing routed through
# the water between its two hints; the sections around it end and begin at its shore chambers), "power" and "rail"
# (corridors). Every section becomes at least one leg, so a section boundary is a named joint of the route.
# A water crossing: (bbox south, west, north, east), a point known to be dry land (the parity reference of the grid), and
# the grid step (lon, lat) in degrees; open sea needs no fine grid, an archipelago does.
ROUTES = {
    "nsn": {
        "title": "Stockholm North - Helsinki (NSN-DF-0001)", "start": STN, "end": HEL,
        "chain": [
            ("road", "Stockholm North - Norrtälje", [STN, NORRTALJE]),
            ("road", "Norrtälje - Väddö - Grisslehamn", [NORRTALJE, ALMSTA, GRISSLEHAMN]),
            ("road", "Grisslehamn - Eckerö - Mariehamn", [GRISSLEHAMN, MARIEHAMN]),
            ("road", "Mariehamn - Vårdö", [MARIEHAMN, HUMMELVIK]),
            ("road", "Hummelvik - Kumlinge", [HUMMELVIK, KUMLINGE]),     # the ferry, then the road on Kumlinge to the shore chamber
            ("water", "Kumlinge - Korpo", [KUMLINGE, KORPO]),         # through the water between the islands to the Korpo chamber
            ("road", "Korpo - Pargas - Turku", [KORPO, TURKU]),
            ("road", "Turku - Salo", [TURKU, SALO]),
            ("power", "Salo - Espoo", [SALO, HEL]),
        ],
        "water": {"Kumlinge - Korpo": ((60.10, 20.70, 60.34, 21.66), KUMLINGE, (0.002, 0.001))},
        # name: (point, radius in km within which a leg end is called by that name)
        "known": {"Stockholm North": (STN, 2.5), "Norrtälje": (NORRTALJE, 2.5), "Älmsta (Väddö)": (ALMSTA, 2.5),
                  "Grisslehamn": (GRISSLEHAMN, 2.5), "Mariehamn": (MARIEHAMN, 2.5), "Hummelvik (Vårdö)": (HUMMELVIK, 2.5),
                  "Kumlinge": (KUMLINGE, 5.5), "Korpo": (KORPO, 2.5), "Turku": (TURKU, 2.5), "Salo": (SALO, 2.5),
                  "Helsinki": (HEL, 2.5)},
    },
    "bfn": {
        "title": "Stockholm East - Helsinki (BFN-DF-0001)", "start": STE, "end": HEL,
        "chain": [
            ("road", "Stockholm East - Handen", [STE, HANDEN]),
            ("road", "Handen - Västerhaninge", [HANDEN, VASTERHANINGE]),
            ("rail", "Västerhaninge - Nynäshamn", [VASTERHANINGE, NYNASHAMN]),   # along the Nynäs line to the harbour
            ("water", "Nynäshamn - Fårösund", [NYNASHAMN, FAROSUND]),
            ("road", "Fårösund - Ljugarn", [FAROSUND, LJUGARN]),               # across Gotland
            ("water", "Ljugarn - Ventspils", [LJUGARN, VENTSPILS]),
            ("road", "Ventspils - Pūre", [VENTSPILS, PURE]),                   # the A10
            ("road", "Pūre - Riga", [PURE, RIGA]),
            ("road", "Riga - Valmiera", [RIGA, VALMIERA]),
            ("road", "Valmiera - Valga", [VALMIERA, VALGA]),
            ("road", "Valga - Viljandi", [VALGA, KARKSI_NUIA, VILJANDI]),     # roads 6 and 49
            ("road", "Viljandi - Imavere", [VILJANDI, IMAVERE]),
            ("road", "Imavere - Tallinn", [IMAVERE, TALLINN]),                 # road 2
            ("water", "Tallinn - Vuosaari", [TALLINN, VUOSAARI]),
            ("road", "Vuosaari - Helsinki", [VUOSAARI, HEL]),
        ],
        "water": {
            # dry references: inland north Gotland (a point in Nynäshamn lay in a bay), inland Gotland west of Ljugarn,
            # central Tallinn; each checked to be an odd number of shore crossings away from the open sea
            "Nynäshamn - Fårösund": ((57.80, 17.85, 58.96, 19.40), (18.9000, 57.8600), (0.004, 0.002)),
            "Ljugarn - Ventspils": ((57.15, 18.55, 57.60, 21.75), (18.6900, 57.3350), (0.004, 0.002)),
            "Tallinn - Vuosaari": ((59.38, 24.55, 60.26, 25.40), (24.7450, 59.4300), (0.002, 0.001)),   # archipelago: fine grid
        },
        "rail": {"Västerhaninge - Nynäshamn": (58.86, 17.88, 59.15, 18.14)},
        "known": {"Stockholm East": (STE, 2.5), "Handen": (HANDEN, 2.5), "Västerhaninge": (VASTERHANINGE, 2.5),
                  "Nynäshamn": (NYNASHAMN, 2.5), "Fårösund": (FAROSUND, 2.5), "Ljugarn": (LJUGARN, 2.5),
                  "Ventspils": (VENTSPILS, 4.0), "Pūre": (PURE, 2.5), "Riga": (RIGA, 3.0), "Valmiera": (VALMIERA, 3.0),
                  "Valga": (VALGA, 3.0), "Viljandi": (VILJANDI, 3.0), "Imavere": (IMAVERE, 2.5), "Tallinn": (TALLINN, 3.0),
                  "Vuosaari": (VUOSAARI, 2.5), "Helsinki": (HEL, 2.5)},
    },
}


def km(a, b):
    return dm.km(a, b)


def length_m(points):
    return dm.cumulative(points)[-1]


def dedupe(points):
    out = []
    for p in points:
        p = (round(p[0], 5), round(p[1], 5))
        if not out or out[-1] != p:
            out.append(p)
    return out


# ---- names of the leg ends (Nominatim reverse geocoding, one request per second) ---------------------------------

_LABELS = {}


def place_label(p, known):
    """The name of the place at a point: a known waypoint of the route, else hamlet, village, town, island or municipality
    (Nominatim, zoom 14)."""
    for name, (q, radius) in known.items():
        if km(p, q) < radius:
            return name
    key = (round(p[0], 3), round(p[1], 3))
    if key in _LABELS:
        return _LABELS[key]
    url = ("https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=14&addressdetails=1"
           f"&lat={p[1]}&lon={p[0]}&accept-language=sv")
    name = None
    for t in range(3):
        try:
            a = json.loads(dm.run_curl([url]).stdout.decode("utf-8")).get("address", {})
            for field in ("hamlet", "village", "suburb", "neighbourhood", "town", "city", "island", "municipality", "county"):
                if a.get(field):
                    name = a[field].replace(" kommun", "").replace(" stad", "")
                    break
            break
        except Exception:
            time.sleep(3 * (t + 1))
    time.sleep(1.3)
    _LABELS[key] = name or "?"
    return _LABELS[key]


def name_legs(legs, known):
    for leg in legs:
        a, b = place_label(leg[2][0], known), place_label(leg[2][-1], known)
        corridor = next((c for c in ("power line corridor", "railway corridor") if c in leg[1]), None)
        tag = " (subsea)" if leg[0] == "sub" else (f" ({corridor})" if corridor else "")
        leg[1] = f"{a} - {b}{tag}" if a != b else (f"{a} (local road)" if leg[0] == "land" else f"{a}{tag}")


# ---- roads (OSRM) ---------------------------------------------------------------------------------------------

def road_runs(waypoints):
    """Route the waypoints and return runs [(kind, name, points)], kind 'land' or 'sub' (OSRM ferry steps), plus road refs."""
    coords = ";".join(f"{x},{y}" for x, y in waypoints)
    d = dm.osrm(f"/route/v1/driving/{coords}?overview=false&geometries=geojson&steps=true")
    time.sleep(0.8)
    runs, refs = [], []
    for leg in d["routes"][0]["legs"]:
        for s in leg["steps"]:
            pts = [tuple(c) for c in s["geometry"]["coordinates"]]
            if len(pts) < 2:
                continue
            ferry = s.get("mode") == "ferry" and s["distance"] >= FERRY_MIN_M
            kind = "sub" if ferry else "land"
            name = s.get("name") or ""
            ref = s.get("ref") or name
            if kind == "land" and ref and s["distance"] > 2000 and (not refs or refs[-1] != ref):
                refs.append(ref)
            if runs and runs[-1][0] == kind and kind == "land":
                runs[-1][2].extend(pts)
            elif runs and runs[-1][0] == kind == "sub" and name == runs[-1][1]:
                runs[-1][2].extend(pts)
            else:
                runs.append([kind, name, list(pts)])
    return [(k, n, dedupe(p)) for k, n, p in runs], refs


# ---- power lines (Overpass) -----------------------------------------------------------------------------------

def overpass(query, tries=8):
    """One Overpass query with a patient back-off; None if the server never answers."""
    for t in range(tries):
        r = dm.run_curl([dm.OVERPASS, "-H", "Accept: */*", "--data-urlencode", "data=" + query]).stdout.decode("utf-8", "replace")
        try:
            d = json.loads(r)
            if "elements" in d:
                return d
        except Exception:
            pass
        wait = min(30 * (t + 1), 240)
        print(f"   Overpass busy, waiting {wait} s ({t + 1}/{tries})")
        time.sleep(wait)
    return None


def power_corridor(start, target_km_from_hel):
    """Follow power lines from near `start` towards Helsinki; return (points, note) or (None, reason)."""
    s, w, n, e = 60.10, 22.95, 60.50, 24.95
    q = (f'[out:json][timeout:120];way["power"="line"]["voltage"~"^[0-9]+$"]({s},{w},{n},{e});'
         'out tags geom;')
    cache = sys.argv[sys.argv.index("--power-cache") + 1] if "--power-cache" in sys.argv else None
    d = None
    if cache:
        try:
            d = json.load(io.open(cache, encoding="utf-8"))
            print(f"   power lines read from {cache}")
        except (OSError, ValueError):
            d = None
    if d is None:
        d = overpass(q)
        if d is not None and cache:
            json.dump(d, io.open(cache, "w", encoding="utf-8"))
    if d is None:
        return None, "Overpass did not answer"
    ways = []
    for el in d["elements"]:
        try:
            v = max(int(x) for x in el["tags"]["voltage"].replace(",", ";").split(";") if x.strip().isdigit())
        except Exception:
            continue
        if v < POWER_MIN_V or "geometry" not in el:
            continue
        ways.append((v, [(round(g["lon"], 5), round(g["lat"], 5)) for g in el["geometry"]]))
    if not ways:
        return None, "no power lines of 110 kV or more in the area"
    print(f"   {len(ways)} power line ways of {POWER_MIN_V // 1000} kV and up in the area")
    # graph: nodes are coordinates; weight favours the higher voltages a little
    adj = line_graph([(1.0 if v >= 400000 else (1.1 if v >= 220000 else 1.25), pts) for v, pts in ways], POWER_LINK_M)
    a = nearest_node(adj, start)
    a_km = km(a, start)
    if a_km > 8:
        return None, f"the nearest power line is {a_km:.0f} km from Salo"
    # Dijkstra from a; stop at the first node within the handoff distance of Helsinki
    path = shortest(adj, a, lambda u: km(u, HEL) <= target_km_from_hel)
    if path is None:
        return None, "the power lines near Salo do not connect to the Helsinki area"
    return path, f"{len(ways)} line ways, {length_m(path) / 1000:.0f} km of corridor, starts {a_km:.1f} km from Salo"


def line_graph(ways, link_m):
    """A graph over the vertices of some line ways [(weight factor, points)]: each way is a chain of edges weighted by
    length times its factor, and two way ends closer than link_m are joined (a substation or a switch between them)."""
    adj, endpoints = {}, []

    def edge(a, b, wgt):
        adj.setdefault(a, []).append((b, wgt))
        adj.setdefault(b, []).append((a, wgt))

    for factor, pts in ways:
        for a, b in zip(pts, pts[1:]):
            if a != b:
                edge(a, b, km(a, b) * factor)
        endpoints += [pts[0], pts[-1]]
    cell = {}
    for p in set(endpoints):
        cell.setdefault((round(p[0] * 120), round(p[1] * 240)), []).append(p)
    for (cx, cy), plist in cell.items():
        near = [q2 for dx in (-1, 0, 1) for dy in (-1, 0, 1) for q2 in cell.get((cx + dx, cy + dy), [])]
        for p in plist:
            for q2 in near:
                if p < q2 and km(p, q2) * 1000 < link_m:
                    edge(p, q2, km(p, q2))
    return adj


def nearest_node(adj, p):
    return min(adj, key=lambda q2: km(p, q2))


def shortest(adj, a, is_goal):
    """Dijkstra from node a to the first node for which is_goal() holds; the path as a list of nodes, or None."""
    dist, prev, heap, goal = {a: 0.0}, {}, [(0.0, a)], None
    while heap:
        dd, u = heapq.heappop(heap)
        if dd > dist.get(u, 1e18):
            continue
        if is_goal(u):
            goal = u
            break
        for v2, wgt in adj[u]:
            nd = dd + wgt
            if nd < dist.get(v2, 1e18):
                dist[v2] = nd
                prev[v2] = u
                heapq.heappush(heap, (nd, v2))
    if goal is None:
        return None
    path = [goal]
    while path[-1] != a:
        path.append(prev[path[-1]])
    path.reverse()
    return path


def rail_corridor(route_key, name, start, end, bbox):
    """Follow the railway (OpenStreetMap railway=rail, main and branch lines, no sidings or yards) from near `start` to near
    `end`; return (points, note) or (None, reason). The ways come from one Overpass query, cached in tools/.cache."""
    s, w, n, e = bbox
    q = (f'[out:json][timeout:120];way["railway"="rail"][!"service"]({s},{w},{n},{e});'
         'out tags geom;')
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache",
                         f"rail-{route_key}-" + name.lower().replace(" - ", "-") + ".json")
    d = None
    if os.path.exists(cache):
        d = json.load(io.open(cache, encoding="utf-8"))
        print(f"   railway read from {cache}")
    else:
        d = overpass(q)
        if d is not None:
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            json.dump(d, io.open(cache, "w", encoding="utf-8"))
    if d is None:
        return None, "Overpass did not answer"
    ways = [(1.0, [(round(g["lon"], 5), round(g["lat"], 5)) for g in el["geometry"]])
            for el in d["elements"] if "geometry" in el]
    if not ways:
        return None, "no railway in the area"
    adj = line_graph(ways, RAIL_LINK_M)
    a, b = nearest_node(adj, start), nearest_node(adj, end)
    if km(a, start) > RAIL_MAX_OFF_KM or km(b, end) > RAIL_MAX_OFF_KM:
        return None, f"the railway passes {km(a, start):.1f} km and {km(b, end):.1f} km from the ends"
    path = shortest(adj, a, lambda u: u == b)
    if path is None:
        return None, "the railway does not connect the two ends"
    return path, (f"{len(ways)} railway ways, {length_m(path) / 1000:.1f} km of corridor, "
                  f"{km(a, start) * 1000:.0f} m and {km(b, end) * 1000:.0f} m from the ends")


# ---- assemble ---------------------------------------------------------------------------------------------------

def resolve_water(key):
    """Replace every ("water", ...) section by its explicit submarine leg and move the neighbouring sections to its chambers."""
    spec = ROUTES[key]
    chain = [[sec[0], sec[1], list(sec[2])] for sec in spec["chain"]]
    for i, sec in enumerate(chain):
        if sec[0] != "water":
            continue
        _kind, name, (a, b) = sec
        bbox, dry, (dx, dy) = spec["water"][name]
        cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache",
                             f"shore-{key}-" + name.lower().replace(" - ", "-") + ".json")
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        water = waterpath.Water(waterpath.shoreline(bbox, cache), dry, bbox, dx, dy)
        route = water.route(a, b)
        rs, ds = dm.snap(*route[0])
        rg, dg = dm.snap(*route[-1])
        length = sum(km(p, q) for p, q in zip(route, route[1:]))
        print(f"== {name}: water route {length:.1f} km in {len(route)} points (straight line {km(a, b):.1f} km); chambers "
              f"{rs} ({ds:.0f} m from the water) and {rg} ({dg:.0f} m)")
        chain[i - 1][2][-1] = rs                       # the section before ends at the shore chamber
        chain[i + 1][2][0] = rg                        # the section after begins at the other one
        chain[i] = ["sub", name, [rs] + route + [rg]]
    return chain


def build(key, use_power, use_rail):
    spec = ROUTES[key]
    legs, roads, notes = [], [], []

    section = [0]
    exact = set()                                               # indices of the legs routed through the water

    def add(kind, name, pts):
        if length_m(pts) < 30:
            return                                              # a zero-length sliver at a quay
        if legs and legs[-1][0] == kind == "land" and legs[-1][3] == section[0]:
            legs[-1][2].extend(pts[1:])                         # contiguous land runs of one section are one leg
        else:
            legs.append([kind, name, list(pts), section[0]])


    for si, (kind, name, wps) in enumerate(resolve_water(key)):
        section[0] = si
        print(f"== {name}")
        if kind == "sub":
            pts = list(wps) if len(wps) > 2 else [wps[0] or legs[-1][2][-1], wps[1]]
            add("sub", name + " (subsea)", pts)
            if len(wps) > 2:
                exact.add(len(legs) - 1)
            print(f"   explicit crossing, {sum(km(a, b) for a, b in zip(pts, pts[1:])):.1f} km")
        elif kind in ("road", "ferry"):
            runs, refs = road_runs(wps)
            if kind == "ferry":                                  # drop the road after the last crossing
                while runs and runs[-1][0] == "land":
                    runs.pop()
            roads += [r for r in refs if r not in roads]
            for k, n, pts in runs:
                label = name if k == "land" else (n or name) + " (subsea)"
                add(k, label, pts)
                print(f"   {k:4} {length_m(pts) / 1000:6.1f} km  {label}")
            print(f"   roads: {', '.join(refs)}")
        elif kind == "rail":
            prev_end, goal = legs[-1][2][-1], wps[-1]               # goal: the shore chamber, when a crossing follows
            pts, note = ((None, "skipped (--no-rail)") if not use_rail else
                         rail_corridor(key, name, wps[0], goal, spec["rail"][name]))
            if pts is None:
                print(f"   no railway corridor: {note}; roads instead")
                notes.append(f"{name} follows roads: {note}")
                runs, refs = road_runs([prev_end, goal])
                roads += [r for r in refs if r not in roads]
                for k, n, rp in runs:
                    add(k, name if k == "land" else (n or name) + " (subsea)", rp)
                    print(f"   {k:4} {length_m(rp) / 1000:6.1f} km")
            else:
                print(f"   railway corridor: {note}")
                notes.append(f"{name} follows the railway corridor: {note}")
                add("land", f"{name} (railway corridor)", dedupe([prev_end] + pts + [goal]))
        else:  # power
            prev_end = legs[-1][2][-1]
            pts, note = (None, "skipped (--no-power)") if not use_power else power_corridor(wps[0], POWER_HANDOFF_KM)
            if pts is None:
                print(f"   no power line corridor: {note}; roads from Salo instead")
                notes.append(f"Salo - Helsinki follows roads: {note}")
                runs, refs = road_runs([prev_end, HEL])
                roads += [r for r in refs if r not in roads]
                for k, n, rp in runs:
                    add(k, "Salo - Helsinki" if k == "land" else (n or name) + " (subsea)", rp)
                    print(f"   {k:4} {length_m(rp) / 1000:6.1f} km")
            else:
                print(f"   power line corridor: {note}")
                notes.append(f"Salo - Espoo follows the power line corridor: {note}")
                link = [prev_end, pts[0]]
                add("land", "Salo - Espoo (power line corridor)", dedupe(link + pts))
                section[0] += 0.5                                 # the road tail is a leg of its own
                runs, refs = road_runs([pts[-1], HEL])
                roads += [r for r in refs if r not in roads]
                for k, n, rp in runs:
                    add(k, "Espoo - Helsinki" if k == "land" else (n or name) + " (subsea)", rp)
                    print(f"   {k:4} {length_m(rp) / 1000:6.1f} km  roads {', '.join(refs)}")
    # simplify and snap the joints so that every leg starts where the previous one ends
    for i, leg in enumerate(legs):
        if i in exact:
            leg[2] = dedupe(leg[2])                              # a water route keeps every vertex: they keep the cable off the shore
        else:
            leg[2] = dedupe(dm.rdp(leg[2], SUB_EPS_M if leg[0] == "sub" else LAND_EPS_M))
    for a, b in zip(legs, legs[1:]):
        b[2][0] = a[2][-1]
    name_legs(legs, spec["known"])
    legs = [leg[:3] for leg in legs]
    return legs, roads, notes


def read(path):
    """The GEOMETRY of an existing generated file ({} if there is none), read as data, not executed."""
    if not os.path.exists(path):
        return {}
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "GEOMETRY" for t in node.targets):
            return ast.literal_eval(node.value)
    return {}


def write(geometry, out):
    lines = ['"""',
             "Geometry of the two leased Stockholm - Helsinki routes, derived by tools/derive_longhaul.py:",
             "nsn is NSN-DF-0001 (Stockholm North over Åland and Turku), bfn is BFN-DF-0001 (Stockholm East over Gotland",
             "and the Baltics).",
             "",
             "Generated, do not edit by hand. The roads, ferries, railways, power lines and shorelines come from OpenStreetMap",
             "(c) OpenStreetMap contributors, ODbL (https://www.openstreetmap.org/copyright). The cables, their ducts and",
             "their owners are invented for the scenario.",
             "",
             "legs: (kind, name, points as (lon, lat)); kind is 'land' (direct buried) or 'sub' (submarine)",
             '"""', "", "GEOMETRY = {"]
    for key in [k for k in ROUTES if k in geometry] + [k for k in geometry if k not in ROUTES]:
        g = geometry[key]
        lines += [f"    {key!r}: {{".replace("'", '"'), '        "legs": [']
        for kind, name, pts in g["legs"]:
            lines.append(f"            ({kind!r}, {name!r}, {[tuple(p) for p in pts]!r}),")
        lines += ["        ],", f'        "roads": {g["roads"]!r},', f'        "notes": {g["notes"]!r},', "    },"]
    lines.append("}")
    io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def report(key, legs):
    spec = ROUTES[key]
    total = 0.0
    print(f"\nleg table, {spec['title']}")
    for i, (kind, name, pts) in enumerate(legs, 1):
        m = length_m(pts)
        total += m
        print(f"  {i:2} {kind:4} {m / 1000:7.1f} km  {len(pts):4} points  {name}")
    land = sum(length_m(p) for k, _n, p in legs if k == "land")
    sub = sum(length_m(p) for k, _n, p in legs if k == "sub")
    line = km(spec["start"], spec["end"])
    print(f"  total {total / 1000:.1f} km (land {land / 1000:.1f}, subsea {sub / 1000:.1f}); straight line "
          f"{line:.0f} km, so the route is {total / 1000 / line:.2f}x the straight line")


def main():
    out = OUT
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    keys = [a for a in sys.argv[1:] if a in ROUTES] or list(ROUTES)
    geometry = read(OUT)                     # the routes not derived in this run are kept as they are
    for key in keys:
        legs, roads, notes = build(key, "--no-power" not in sys.argv, "--no-rail" not in sys.argv)
        report(key, legs)
        geometry[key] = {"legs": legs, "roads": roads, "notes": notes}
    write(geometry, out)
    print("written", out, "(derived: " + ", ".join(keys) + ")")


if __name__ == "__main__":
    main()
