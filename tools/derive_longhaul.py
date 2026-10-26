#!/usr/bin/env python3
"""
Derive the geometry of the Stockholm North - Helsinki leased route (data/longhaul_geometry.py) from OpenStreetMap.

A one-off helper, not part of the build: the build reads the file it writes. Like tools/derive_metro.py it exists so the
route can be reproduced and checked, and so nobody has to believe hand-typed coordinates.

The route (NSN-DF-0001, "route 1") runs: Stockholm North - road 265 and E18 - Norrtälje - Väddö - Grisslehamn - (sea) -
Eckerö - Mariehamn - Vårdö - (sea) - Kumlinge - (sea) - Korpo - Pargas - Turku - E18 - Salo - (power line corridor) -
Espoo - roads - Helsinki.

  1. Land sections are routed on the road network (OSRM demo server, read-only), so the cable follows roads.
  2. Every ferry the road router uses (OSRM step mode "ferry") becomes a submarine leg: no road there.
     A crossing the road network does not know (Kumlinge - Korpo, 46 km through the archipelago) is routed through the water
     along the shoreline (tools/waterpath.py), so that the cable passes between the islands and not over them.
  3. Past Salo the route follows the high-voltage power line corridor (OpenStreetMap power=line, 110 kV and up, found
     with the Overpass API) as far as the outskirts of Helsinki, then roads again. If Overpass is unavailable, or no
     connected line is found, the section falls back to roads and the report says so.
  4. The result is simplified (Ramer-Douglas-Peucker) and written with an ODbL attribution header.

The output is geometry only. The road, ferry and power line data come from OpenStreetMap contributors (ODbL,
https://www.openstreetmap.org/copyright); the cable, its ducts and its owner are invented for the scenario.

    python tools/derive_longhaul.py                 # writes data/longhaul_geometry.py and prints a report
    python tools/derive_longhaul.py --out FILE      # write somewhere else (review)
    python tools/derive_longhaul.py --no-power      # roads all the way from Salo (baseline for comparison)
"""

import heapq
import io
import json
import math
import os
import sys
import time
import urllib.parse

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import derive_metro as dm                      # run_curl, osrm, cumulative, rdp, km, at (shared helpers)
import waterpath                               # routes through the water along the OpenStreetMap shoreline

OUT = "data/longhaul_geometry.py"
FERRY_MIN_M = 300            # an OSRM ferry step shorter than this is a pontoon, not a crossing
LAND_EPS_M = 25              # simplification of land legs
SUB_EPS_M = 250              # simplification of submarine legs
POWER_MIN_V = 110000         # lines of this voltage and up
POWER_HANDOFF_KM = 22        # the corridor is left for roads this far (straight line) from the Helsinki datacenter
POWER_LINK_M = 450           # two line ends closer than this are treated as joined (a substation between them)

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

# The chain. kind: "road" (routed; ferries inside it become submarine legs), "water" (a crossing routed through the water
# between its two hints; the road sections around it end and begin at its shore chambers), "power" (corridor).
WATER_BBOX = {"Kumlinge - Korpo": (60.10, 20.70, 60.34, 21.66)}
CHAIN = [
    ("road", "Stockholm North - Norrtälje", [STN, NORRTALJE]),
    ("road", "Norrtälje - Väddö - Grisslehamn", [NORRTALJE, ALMSTA, GRISSLEHAMN]),
    ("road", "Grisslehamn - Eckerö - Mariehamn", [GRISSLEHAMN, MARIEHAMN]),
    ("road", "Mariehamn - Vårdö", [MARIEHAMN, HUMMELVIK]),
    ("road", "Hummelvik - Kumlinge", [HUMMELVIK, KUMLINGE]),       # the ferry, then the road on Kumlinge to the shore chamber
    ("water", "Kumlinge - Korpo", [KUMLINGE, KORPO]),           # through the water between the islands to the Korpo chamber
    ("road", "Korpo - Pargas - Turku", [KORPO, TURKU]),
    ("road", "Turku - Salo", [TURKU, SALO]),
    ("power", "Salo - Espoo", [SALO, HEL]),
]


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


KNOWN = {"Stockholm North": STN, "Norrtälje": NORRTALJE, "Älmsta (Väddö)": ALMSTA, "Grisslehamn": GRISSLEHAMN,
         "Mariehamn": MARIEHAMN, "Hummelvik (Vårdö)": HUMMELVIK, "Kumlinge": KUMLINGE, "Korpo": KORPO, "Turku": TURKU,
         "Salo": SALO, "Helsinki": HEL}


def place_label(p):
    """The name of the place at a point: a known waypoint, else hamlet, village, town, island or municipality (Nominatim, zoom 14)."""
    for name, q in KNOWN.items():
        if km(p, q) < (5.5 if name == "Kumlinge" else 2.5):
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


def name_legs(legs):
    for leg in legs:
        a, b = place_label(leg[2][0]), place_label(leg[2][-1])
        tag = " (subsea)" if leg[0] == "sub" else (" (power line corridor)" if "power line corridor" in leg[1] else "")
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
    adj, endpoints = {}, []

    def edge(a, b, wgt):
        adj.setdefault(a, []).append((b, wgt))
        adj.setdefault(b, []).append((a, wgt))

    for v, pts in ways:
        factor = 1.0 if v >= 400000 else (1.1 if v >= 220000 else 1.25)
        for a, b in zip(pts, pts[1:]):
            if a != b:
                edge(a, b, km(a, b) * factor)
        endpoints += [pts[0], pts[-1]]
    # join line ends that lie close together (the line continues through a substation)
    cell = {}
    for p in set(endpoints):
        cell.setdefault((round(p[0] * 120), round(p[1] * 240)), []).append(p)
    for (cx, cy), plist in cell.items():
        near = [q2 for dx in (-1, 0, 1) for dy in (-1, 0, 1) for q2 in cell.get((cx + dx, cy + dy), [])]
        for p in plist:
            for q2 in near:
                if p < q2 and km(p, q2) * 1000 < POWER_LINK_M:
                    edge(p, q2, km(p, q2))
    nodes = list(adj)

    def nearest(p):
        return min(nodes, key=lambda q2: km(p, q2))

    a = nearest(start)
    a_km = km(a, start)
    if a_km > 8:
        return None, f"the nearest power line is {a_km:.0f} km from Salo"
    # Dijkstra from a; stop at the first node within the handoff distance of Helsinki
    dist, prev, heap, goal = {a: 0.0}, {}, [(0.0, a)], None
    while heap:
        dd, u = heapq.heappop(heap)
        if dd > dist.get(u, 1e18):
            continue
        if km(u, HEL) <= target_km_from_hel:
            goal = u
            break
        for v2, wgt in adj[u]:
            nd = dd + wgt
            if nd < dist.get(v2, 1e18):
                dist[v2] = nd
                prev[v2] = u
                heapq.heappush(heap, (nd, v2))
    if goal is None:
        return None, "the power lines near Salo do not connect to the Helsinki area"
    path = [goal]
    while path[-1] != a:
        path.append(prev[path[-1]])
    path.reverse()
    return path, f"{len(ways)} line ways, {length_m(path) / 1000:.0f} km of corridor, starts {a_km:.1f} km from Salo"


# ---- assemble ---------------------------------------------------------------------------------------------------

def resolve_water(chain):
    """Replace every ("water", ...) section by its explicit submarine leg and move the neighbouring road sections to its chambers."""
    chain = [list(sec) for sec in chain]
    for i, sec in enumerate(chain):
        if sec[0] != "water":
            continue
        _kind, name, (a, b) = sec
        bbox = WATER_BBOX[name]
        cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "shore-nsn-" + name.lower().replace(" - ", "-") + ".json")
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        water = waterpath.Water(waterpath.shoreline(bbox, cache), a, bbox)
        route = water.route(a, b)
        rs, ds = dm.snap(*route[0])
        rg, dg = dm.snap(*route[-1])
        length = sum(km(p, q) for p, q in zip(route, route[1:]))
        print(f"== {name}: water route {length:.1f} km in {len(route)} points (straight line {km(a, b):.1f} km); chambers "
              f"{rs} ({ds:.0f} m from the water) and {rg} ({dg:.0f} m)")
        chain[i - 1][2][-1] = rs                       # the road before ends at the shore chamber
        chain[i + 1][2][0] = rg                        # the road after begins at the other one
        chain[i] = ["sub", name, [rs] + route + [rg]]
    return chain


def build(use_power):
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


    for si, (kind, name, wps) in enumerate(resolve_water(CHAIN)):
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
    name_legs(legs)
    legs = [leg[:3] for leg in legs]
    return legs, roads, notes


def write(legs, roads, notes, out):
    lines = ['"""',
             "Geometry of the leased Stockholm North - Helsinki route (NSN-DF-0001), derived by tools/derive_longhaul.py.",
             "",
             "Generated, do not edit by hand. The roads, ferries and power lines come from OpenStreetMap",
             "(c) OpenStreetMap contributors, ODbL (https://www.openstreetmap.org/copyright). The cable, its ducts and",
             "its owner are invented for the scenario.",
             "",
             "legs: (kind, name, points as (lon, lat)); kind is 'land' (direct buried) or 'sub' (submarine)",
             '"""', "", "GEOMETRY = {", '    "nsn": {', '        "legs": [']
    for kind, name, pts in legs:
        lines.append(f"            ({kind!r}, {name!r}, {[tuple(p) for p in pts]!r}),")
    lines += ["        ],", f'        "roads": {roads!r},', f'        "notes": {notes!r},', "    },", "}"]
    io.open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def report(legs):
    total = 0.0
    print("\nleg table")
    for i, (kind, name, pts) in enumerate(legs, 1):
        m = length_m(pts)
        total += m
        print(f"  {i:2} {kind:4} {m / 1000:7.1f} km  {len(pts):4} points  {name}")
    land = sum(length_m(p) for k, _n, p in legs if k == "land")
    sub = sum(length_m(p) for k, _n, p in legs if k == "sub")
    print(f"  total {total / 1000:.1f} km (land {land / 1000:.1f}, subsea {sub / 1000:.1f}); straight line "
          f"{km(STN, HEL):.0f} km, so the route is {total / 1000 / km(STN, HEL):.2f}x the straight line")


def main():
    out = OUT
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    legs, roads, notes = build("--no-power" not in sys.argv)
    report(legs)
    write(legs, roads, notes, out)
    print("written", out)


if __name__ == "__main__":
    main()
