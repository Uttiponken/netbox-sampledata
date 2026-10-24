#!/usr/bin/env python3
"""
Derive the geometry of the Stockholm metro ring (data/metro_geometry.py) from OpenStreetMap.

A one-off helper, not part of the build: the build reads the file it writes. It exists so the geometry can be
reproduced and checked, and so nobody has to believe hand-typed coordinates.

  1. Each land section of a link is routed on the road network (OSRM demo server, read-only): the ducts follow the
     roads, so the West - East link follows the E4/E20 and road 222.
  2. The route is sampled every ~700 m and each sample is placed in its municipality (Overpass API, read-only).
  3. The route is cut into legs where the municipality changes, and any run longer than ~4.5 km is split again.
     The first and last leg at a datacenter are the duct-bank lead-ins.
  4. Water crossings are straight lines between two shore chambers and become submarine pathways.

The output is geometry only: the ownership and the ducts themselves are invented for the scenario. The road and
boundary data come from OpenStreetMap contributors (ODbL, https://www.openstreetmap.org/copyright).

    python tools/derive_metro.py            # writes data/metro_geometry.py and prints a report
"""

import io
import json
import math
import subprocess
import sys
import time

UA = "netbox-sampledata-geocheck/1.0 (educational dataset)"
OSRM = "https://router.project-osrm.org"
OVERPASS = "https://overpass-api.de/api/interpreter"
OUT = "data/metro_geometry.py"

SAMPLE_M = 700          # municipality sampling step along a route
MAX_LEG_M = 4500        # a run inside one municipality is split into legs no longer than this
LEAD_IN_M = 1200        # the duct bank at a datacenter
MIN_RUN_M = 1300        # a municipality run shorter than this between two runs of the same municipality is a flicker

# Entrances are fixed (the datacenters are fictional), everything else is snapped to roads.
ENTRANCES = {"STN-ENT-W": (17.9170, 59.4400), "STN-ENT-E": (17.9340, 59.4410),
             "STW-ENT-N": (17.6430, 59.1765), "STW-ENT-E": (17.6480, 59.1740),
             "STE-ENT-N": (18.1690, 59.3135), "STE-ENT-S": (18.1650, 59.3100)}

# A link is a chain: entrance, then alternating land sections and water crossings, then the other entrance.
#   ("shore", lon, lat): a shore chamber, snapped to the nearest road; a crossing runs between two of them
#   ("via", lon, lat):   a waypoint the road route must pass (to keep it on the intended road)
LINKS = {
    "nw": [("entrance", "STN-ENT-W"),
           ("shore", 17.8330, 59.3600),          # Hässelby strand
           ("shore", 17.7600, 59.3520),          # Färingsö: across Mälaren (by road it is 26 km away)
           ("entrance", "STW-ENT-N")],
    "ne": [("entrance", "STN-ENT-E"),
           ("shore", 18.1000, 59.4020),          # Djursholm, Danderyd
           ("shore", 18.1150, 59.3835),          # Lidingö, north coast
           ("shore", 18.2300, 59.3590),          # Lidingö, east end
           ("shore", 18.2380, 59.3270),          # Nacka, north coast: across the water from Lidingö
           ("via", 18.2540, 59.3070),            # Orminge, road 222
           ("entrance", "STE-ENT-N")],
    "we": [("entrance", "STW-ENT-E"),
           ("entrance", "STE-ENT-S")],     # no waypoints: the shortest road route is the E4/E20 and road 222
}


def run_curl(args):
    return subprocess.run(["curl", "-s", "--max-time", "90", "-A", UA] + args, capture_output=True)


def osrm(path):
    for t in range(5):
        try:
            d = json.loads(run_curl([OSRM + path]).stdout.decode("utf-8"))
            if d.get("code") == "Ok":
                return d
        except Exception:
            pass
        time.sleep(4 * (t + 1))
    raise SystemExit(f"OSRM failed: {path}")


def municipality(lon, lat):
    q = f"[out:json][timeout:25];is_in({lat},{lon})->.a;area.a[boundary=administrative][admin_level=7];out tags;"
    for t in range(6):
        try:
            d = json.loads(run_curl([OVERPASS, "-H", "Accept: */*", "--data-urlencode", "data=" + q]).stdout.decode("utf-8"))
            names = [e["tags"].get("name") for e in d["elements"] if e["tags"].get("name")]
            return names[0] if names else None
        except Exception:
            time.sleep(5 * (t + 1))
    return None


def km(a, b):
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[0] - a[0]) / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(h))


def cumulative(points):
    out, total = [0.0], 0.0
    for a, b in zip(points, points[1:]):
        total += km(a, b) * 1000
        out.append(total)
    return out


def at(points, cum, d):
    """The point at distance d metres along a polyline."""
    if d <= 0:
        return points[0]
    if d >= cum[-1]:
        return points[-1]
    i = max(j for j in range(len(cum)) if cum[j] <= d)
    f = (d - cum[i]) / ((cum[i + 1] - cum[i]) or 1)
    return (points[i][0] + f * (points[i + 1][0] - points[i][0]), points[i][1] + f * (points[i + 1][1] - points[i][1]))


def rdp(points, eps_m):
    if len(points) < 3:
        return points
    lat0 = math.radians(points[0][1])
    xy = [(p[0] * 111320 * math.cos(lat0), p[1] * 110540) for p in points]

    def dist(i, a, b):
        (x, y), (x1, y1), (x2, y2) = xy[i], xy[a], xy[b]
        dx, dy = x2 - x1, y2 - y1
        if dx == dy == 0:
            return math.hypot(x - x1, y - y1)
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))

    keep, stack = {0, len(points) - 1}, [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        far, fi = 0, None
        for i in range(a + 1, b):
            d = dist(i, a, b)
            if d > far:
                far, fi = d, i
        if fi is not None and far > eps_m:
            keep.add(fi)
            stack += [(a, fi), (fi, b)]
    return [points[i] for i in sorted(keep)]


def snap(lon, lat):
    d = osrm(f"/nearest/v1/driving/{lon},{lat}?number=1")
    time.sleep(0.7)
    wp = d["waypoints"][0]
    return (round(wp["location"][0], 5), round(wp["location"][1], 5)), wp["distance"]


def route(waypoints):
    coords = ";".join(f"{x},{y}" for x, y in waypoints)
    d = osrm(f"/route/v1/driving/{coords}?overview=full&geometries=geojson&steps=true")
    time.sleep(0.7)
    r = d["routes"][0]
    pts = [tuple(c) for c in r["geometry"]["coordinates"]]
    refs = []
    for leg in r["legs"]:
        for s in leg["steps"]:
            ref = s.get("ref") or s.get("name")
            if ref and (not refs or refs[-1] != ref) and s["distance"] > 600:
                refs.append(ref)
    return pts, refs


def short(name):
    """'Stockholms kommun' -> 'Stockholm' etc.: the key used for a municipality in the data."""
    base = name.replace(" kommun", "").replace(" stad", "")
    return {"Stockholms": "Stockholm", "Södertälje": "Södertälje"}.get(base, base)


def sections(key):
    """The chain of a link as a list of ('land', [waypoints]) and ('sub', a, b), with snapped shore points."""
    chain = LINKS[key]
    out, current = [], []
    first = True
    pending_sub = False
    shores = [i for i, c in enumerate(chain) if c[0] == "shore"]
    for i, c in enumerate(chain):
        if c[0] == "entrance":
            current.append(ENTRANCES[c[1]])
            if not first:
                out.append(("land", current))
                current = []
            first = False
        elif c[0] == "via":
            current.append((c[1], c[2]))
        elif c[0] == "shore":
            p, dist = snap(c[1], c[2])
            print(f"   {key} shore ({c[1]},{c[2]}) -> {p}  ({dist:.0f} m to the road)")
            k = shores.index(i)
            # a water crossing joins the (2m+1)-th and (2m+2)-th shore chamber of the chain in this scenario
            if k % 2 == 0:                       # first shore of a pair: the land section ends here
                current.append(p)
                out.append(("land", current))
                current = []
                pending_sub = p
            else:                                # second shore: the crossing runs from the previous one, land continues
                out.append(("sub", pending_sub, p))
                current = [p]
    return out


def segment(key, secs):
    """Cut the sections into legs and stations."""
    stations, legs, roads = [], [], []     # stations: [name, type, lon, lat, owner]; legs: [kind, owner, via]
    muni_seen = {}
    n = 0

    def add_station(name, stype, p, owner):
        stations.append([name, stype, round(p[0], 5), round(p[1], 5), owner])

    first_name = LINKS[key][0][1]
    last_name = LINKS[key][-1][1]
    add_station(first_name, "building_entrance", ENTRANCES[first_name], "nordfiber")
    for si, sec in enumerate(secs):
        if sec[0] == "sub":
            a, b = sec[1], sec[2]
            n += 1
            stations[-1][1] = "manhole" if stations[-1][1] != "building_entrance" else stations[-1][1]
            stations[-1][4] = "nordfiber"
            add_station(f"{key.upper()}-{n:02d}-SUB", "manhole", b, "nordfiber")
            legs.append(["sub", "nordfiber", []])
            continue
        waypoints = sec[1]
        pts, refs = route(waypoints)
        pts = [waypoints[0]] + pts[1:-1] + [waypoints[-1]]
        cum = cumulative(pts)
        total = cum[-1]
        print(f"   {key} land section {si}: {total / 1000:.1f} km by road, via {', '.join(refs)}")
        roads += [r for r in refs if r not in roads]
        # municipality of each sample
        samples = []
        d = 0.0
        while d < total:
            p = at(pts, cum, d + SAMPLE_M / 2 if d + SAMPLE_M / 2 < total else total)
            samples.append((d, municipality(*p)))
            time.sleep(0.9)
            d += SAMPLE_M
        runs = []                                   # [muni, start_d, end_d]
        for d, m in samples:
            if runs and runs[-1][0] == m:
                runs[-1][2] = min(d + SAMPLE_M, total)
            else:
                runs.append([m, d, min(d + SAMPLE_M, total)])
        # absorb flickers: a short run between two runs of the same municipality (or at either end) joins its neighbour
        changed = True
        while changed and len(runs) > 1:
            changed = False
            for i, r in enumerate(runs):
                length = r[2] - r[1]
                if length < MIN_RUN_M and len(runs) > 1:
                    if 0 < i < len(runs) - 1 and runs[i - 1][0] == runs[i + 1][0]:
                        runs[i - 1][2] = runs[i + 1][2]
                        del runs[i:i + 2]
                    elif i == 0 and length < MIN_RUN_M / 2:
                        runs[1][1] = r[1]
                        del runs[0]
                    elif i == len(runs) - 1 and length < MIN_RUN_M / 2:
                        runs[-2][2] = r[2]
                        del runs[-1]
                    else:
                        continue
                    changed = True
                    break
        # cuts: municipality borders, long runs split, lead-ins at a datacenter
        cuts = []                                    # (distance, owner_of_leg_ending_here)
        first_land = si == 0
        last_land = si == len(secs) - 1
        legs_here = []                               # (start, end, owner)
        for m, a, b in runs:
            owner = short(m) if m else "unknown"
            pieces = max(1, math.ceil((b - a) / MAX_LEG_M))
            step = (b - a) / pieces
            for k in range(pieces):
                legs_here.append([a + k * step, a + (k + 1) * step, owner])
        legs_here[0][0], legs_here[-1][1] = 0.0, total
        if first_land and legs_here[0][1] - legs_here[0][0] > LEAD_IN_M * 1.5:
            a, b, o = legs_here[0]
            legs_here[0:1] = [[a, a + LEAD_IN_M, o], [a + LEAD_IN_M, b, o]]
        if last_land and legs_here[-1][1] - legs_here[-1][0] > LEAD_IN_M * 1.5:
            a, b, o = legs_here[-1]
            legs_here[-1:] = [[a, b - LEAD_IN_M, o], [b - LEAD_IN_M, b, o]]
        for li, (a, b, owner) in enumerate(legs_here):
            kind = "duct"
            if (first_land and li == 0) or (last_land and li == len(legs_here) - 1):
                kind = "bank"
            inner = [pts[i] for i in range(len(pts)) if a < cum[i] < b]
            via = [(round(x, 5), round(y, 5)) for x, y in rdp([at(pts, cum, a)] + inner + [at(pts, cum, b)], 20)[1:-1]]
            legs.append([kind, owner, via])
            last = li == len(legs_here) - 1 and si == len(secs) - 1
            n += 1
            if last:
                add_station(last_name, "building_entrance", ENTRANCES[last_name], "nordfiber")
            else:
                end = at(pts, cum, b)
                border = li < len(legs_here) - 1 and legs_here[li + 1][2] != owner
                end_of_land = li == len(legs_here) - 1                  # a shore chamber, the next leg is a crossing
                stype = "manhole" if (end_of_land or li == 0) else ("vault" if border else "handhole")
                add_station(f"{key.upper()}-{n:02d}-{owner[:3].upper()}", stype, end,
                            "nordfiber" if end_of_land else owner)
    return stations, legs, roads


def in_water(lon, lat):
    """True if OpenStreetMap maps the point as a lake, bay or sea area (a road bridge counts as water)."""
    q = (f"[out:json][timeout:25];is_in({lat},{lon})->.a;"
         "(area.a[natural~\"^(water|bay|strait)$\"];area.a[place~\"^(sea|ocean)$\"];);out tags;")
    for t in range(6):
        try:
            d = json.loads(run_curl([OVERPASS, "-H", "Accept: */*", "--data-urlencode", "data=" + q]).stdout.decode("utf-8"))
            return bool(d["elements"])
        except Exception:
            time.sleep(5 * (t + 1))
    raise SystemExit("Overpass did not answer")


def snap_to_land(key, stations, legs):
    """A station between two land legs that fell on a road bridge is moved along the route to the nearest dry land."""
    for i in range(1, len(stations) - 1):
        name, stype, lon, lat, owner = stations[i]
        if stype == "building_entrance" or legs[i - 1][0] == "sub" or legs[i][0] == "sub":
            continue
        time.sleep(0.8)
        if not in_water(lon, lat):
            continue
        prev, nxt = tuple(stations[i - 1][2:4]), tuple(stations[i + 1][2:4])
        before = [tuple(v) for v in legs[i - 1][2]]
        after = [tuple(v) for v in legs[i][2]]
        full = [prev] + before + [(lon, lat)] + after + [nxt]
        cum = cumulative(full)
        here = cum[len(before) + 1]
        found = None
        for off in range(150, 1651, 150):
            for sign in (-1, 1):
                d = here + sign * off
                if d < 200 or d > cum[-1] - 200:      # keep clear of the neighbouring stations
                    continue
                p = at(full, cum, d)
                time.sleep(0.8)
                if not in_water(*p):
                    found = (d, p)
                    break
            if found:
                break
        if not found:
            print(f"   {key}: {name} is on water and no dry land within 1.6 km; left as is")
            continue
        d, p = found
        stations[i][2:4] = [round(p[0], 5), round(p[1], 5)]
        legs[i - 1][2] = [(round(full[k][0], 5), round(full[k][1], 5)) for k in range(1, len(full) - 1) if cum[k] < d]
        legs[i][2] = [(round(full[k][0], 5), round(full[k][1], 5)) for k in range(1, len(full) - 1) if cum[k] > d]
        print(f"   {key}: {name} was on a bridge over water; moved {abs(d - here):.0f} m along the route to {tuple(stations[i][2:4])}")


def write(result, corridors):
    lines = ['"""',
             "Geometry of the Stockholm metro ring: stations and legs, derived by tools/derive_metro.py.",
             "",
             "Generated, do not edit by hand. The ducts follow the road network and the legs change owner at the real",
             "municipal borders; both come from OpenStreetMap (c) OpenStreetMap contributors, ODbL",
             "(https://www.openstreetmap.org/copyright). The ownership and the ducts are invented for the scenario.",
             "",
             "stations: (name, structure type, lon, lat, owner)   legs: (kind, owner, via points)",
             '"""', "", "GEOMETRY = {"]
    for key, (stations, legs) in result.items():
        lines.append(f'    "{key}": {{')
        lines.append('        "stations": [')
        for s in stations:
            lines.append(f"            ({s[0]!r}, {s[1]!r}, {s[2]}, {s[3]}, {s[4]!r}),")
        lines.append("        ],")
        lines.append('        "legs": [')
        for k, o, via in legs:
            lines.append(f"            ({k!r}, {o!r}, {[tuple(v) for v in via]!r}),")
        lines.append("        ],")
        lines.append(f'        "roads": {corridors[key]!r},')
        lines.append("    },")
    lines.append("}")
    io.open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    snap_only = "--snap-only" in sys.argv
    keys = [a for a in sys.argv[1:] if not a.startswith("--")] or list(LINKS)
    result, corridors = {}, {}
    try:
        ns = {}
        exec(io.open(OUT, encoding="utf-8").read(), ns)
        for key, g in ns["GEOMETRY"].items():
            result[key] = ([list(s) for s in g["stations"]], [list(l) for l in g["legs"]])
            corridors[key] = g["roads"]
    except FileNotFoundError:
        pass
    for key in keys:
        if not snap_only:
            print(f"== {key}")
            secs = sections(key)
            stations, legs, roads = segment(key, secs)
            result[key] = (stations, legs)
            corridors[key] = roads
            print(f"   {key}: {len(stations)} stations, {len(legs)} legs, owners {sorted({l[1] for l in legs})}")
        print(f"== snapping {key} to dry land")
        snap_to_land(key, *result[key])
    result = {k: result[k] for k in LINKS if k in result}
    write(result, corridors)
    print("written", OUT)


if __name__ == "__main__":
    main()
