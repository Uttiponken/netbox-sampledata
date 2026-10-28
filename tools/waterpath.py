"""
A cable route through the water, derived from the OpenStreetMap shoreline (used by derive_metro.py and
derive_longhaul.py for their submarine crossings).

A straight line between two shore chambers is only honest when it stays in the water. This module finds a route that does:

  1. One Overpass query fetches the shoreline inside a box (natural=coastline, natural=water ways and relations), cached
     in a file so a re-run does not hit the shared server again.
  2. A grid of points is classified as water or land. Along a row of the grid the state changes at every shoreline
     crossing, so each row is classified from its two known ends: the state at the west end is found by counting the
     shoreline crossings on the straight line from there to a point known to be dry land.
  3. Dijkstra over the water points (8 neighbours, a step may not cross the shoreline) from the water point nearest to the
     start hint to the one nearest to the goal hint.
  4. The route is simplified by keeping a vertex only where a straight shortcut would touch the shore.

Roads and shores are OpenStreetMap contributors (ODbL, https://www.openstreetmap.org/copyright).
"""

import heapq
import io
import json
import math
import os
import time

import derive_metro as dm

QUERY = ('[out:json][timeout:180];(way["natural"="coastline"]({s},{w},{n},{e});way["natural"="water"]({s},{w},{n},{e});'
         'relation["natural"="water"]({s},{w},{n},{e}););out geom({s},{w},{n},{e});')
CELL = (0.02, 0.01)                      # spatial index cell (degrees lon, lat)


def shoreline(bbox, cache=None):
    """The shoreline polylines inside bbox = (south, west, north, east); from the cache file when there is one."""
    if cache and os.path.exists(cache):
        return json.load(io.open(cache, encoding="utf-8"))
    s, w, n, e = bbox
    data = None
    for t in range(10):
        r = dm.run_curl([dm.OVERPASS, "-H", "Accept: */*", "--data-urlencode",
                         "data=" + QUERY.format(s=s, w=w, n=n, e=e)]).stdout.decode("utf-8", "replace")
        try:
            data = json.loads(r)
            if "elements" in data:
                break
        except ValueError:
            pass
        print(f"   Overpass busy, waiting {min(30 * (t + 1), 240)} s ({t + 1}/10)")
        time.sleep(min(30 * (t + 1), 240))
    else:
        raise SystemExit("Overpass did not answer")
    lines = []
    for el in data["elements"]:
        geoms = [el["geometry"]] if el["type"] == "way" and "geometry" in el else [m["geometry"] for m in el.get("members", []) if m.get("geometry")]
        for g in geoms:
            run = []
            for p in g + [None]:                          # a null node lies outside the box: the line ends there
                if p:
                    run.append((round(p["lon"], 6), round(p["lat"], 6)))
                else:
                    if len(run) > 1:
                        lines.append(run)
                    run = []
    if cache:
        json.dump(lines, io.open(cache, "w", encoding="utf-8"))
    return lines


class Water:
    def __init__(self, lines, dry, bbox, dx=0.002, dy=0.001):
        self.segs, self.index = [], {}
        for pl in lines:
            for a, b in zip(pl, pl[1:]):
                i = len(self.segs)
                self.segs.append((a[0], a[1], b[0], b[1]))
                for cx in range(int(min(a[0], b[0]) / CELL[0]), int(max(a[0], b[0]) / CELL[0]) + 1):
                    for cy in range(int(min(a[1], b[1]) / CELL[1]), int(max(a[1], b[1]) / CELL[1]) + 1):
                        self.index.setdefault((cx, cy), []).append(i)
        self.dry = dry
        s, w, n, e = bbox
        self.dx, self.dy, self.w, self.s = dx, dy, w, s
        self.cols, self.rows = int((e - w) / dx) + 1, int((n - s) / dy) + 1
        self.water = self._classify()

    # -- geometry -------------------------------------------------------------------------------------------------
    @staticmethod
    def _cells(p, q):
        """Every index cell the segment p-q touches (exact, column by column)."""
        (x0, y0), (x1, y1) = (p, q) if p[0] <= q[0] else (q, p)
        out = set()
        for cx in range(int(x0 / CELL[0]), int(x1 / CELL[0]) + 1):
            xa, xb = max(x0, cx * CELL[0]), min(x1, (cx + 1) * CELL[0])
            if x1 == x0:
                ya, yb = sorted((y0, y1))
            else:
                ya, yb = sorted((y0 + (y1 - y0) * (xa - x0) / (x1 - x0), y0 + (y1 - y0) * (xb - x0) / (x1 - x0)))
            for cy in range(int(ya / CELL[1]), int(yb / CELL[1]) + 1):
                out.add((cx, cy))
        return out

    def crossings(self, p, q):
        """Number of shoreline segments crossed by the segment p-q (a shared vertex of two segments counts once)."""
        seen, n = set(), 0
        d1x, d1y = q[0] - p[0], q[1] - p[1]
        for c in self._cells(p, q):
            for i in self.index.get(c, ()):
                if i in seen:
                    continue
                seen.add(i)
                ax, ay, bx, by = self.segs[i]
                d2x, d2y = bx - ax, by - ay
                den = d1x * d2y - d1y * d2x
                if abs(den) < 1e-15:
                    continue
                t = ((ax - p[0]) * d2y - (ay - p[1]) * d2x) / den
                u = ((ax - p[0]) * d1y - (ay - p[1]) * d1x) / den
                if 0 <= t <= 1 and 0 <= u < 1:
                    n += 1
        return n

    def _classify(self):
        """Set of (col, row) grid points that are water, row by row."""
        by_row = {}
        for ax, ay, bx, by in self.segs:
            if ay == by:
                continue
            r0, r1 = sorted((ay, by))
            # one row of margin on each side: for a vertex on a row, (y - s) / dy can come out as 756.0000000000002, and ceil()
            # then skipped that row for the segment above the vertex while the half-open test skipped it for the one below; the
            # row lost a crossing and was classified the wrong way round from that vertex to its east end (Tallinn - Vuosaari)
            for r in range(max(0, math.ceil((r0 - self.s) / self.dy) - 1),
                           min(self.rows - 1, math.floor((r1 - self.s) / self.dy) + 1) + 1):
                y = self.s + r * self.dy
                if r0 <= y < r1:                                         # half-open, so a vertex on a row counts once
                    by_row.setdefault(r, []).append(ax + (bx - ax) * (y - ay) / (by - ay))
        water = set()
        for r in range(self.rows):
            y = self.s + r * self.dy
            west = (self.w, y)
            is_water = self.crossings(west, self.dry) % 2 == 1          # parity against the known dry point
            xs = sorted(by_row.get(r, []))
            k = 0
            for c in range(self.cols):
                x = self.w + c * self.dx
                while k < len(xs) and xs[k] < x:
                    is_water = not is_water
                    k += 1
                if is_water:
                    water.add((c, r))
        return self._despeckle(water)

    def _despeckle(self, water):
        """The row-by-row classification can get a row wrong where its line clips a vertex of the shore. Such an artefact is a run
        of one or two grid points in a column, with the same state above and below it and at least three points of that state
        on each side; it takes the state of its surroundings."""
        for c in range(self.cols):
            runs, r = [], 0                                           # (state, first row, length) of the column
            while r < self.rows:
                st, r0 = (c, r) in water, r
                while r < self.rows and ((c, r) in water) == st:
                    r += 1
                runs.append((st, r0, r - r0))
            for i in range(1, len(runs) - 1):
                st, r0, n = runs[i]
                if n <= 2 and runs[i - 1][0] == runs[i + 1][0] != st and runs[i - 1][2] >= 3 and runs[i + 1][2] >= 3:
                    for rr in range(r0, r0 + n):
                        water.symmetric_difference_update({(c, rr)})
        return water

    def point(self, node):
        return (self.w + node[0] * self.dx, self.s + node[1] * self.dy)

    def nearest(self, p):
        return min(self.water, key=lambda k: dm.km(self.point(k), p))

    # -- routing --------------------------------------------------------------------------------------------------
    def largest_body(self):
        """The biggest set of water points that touch each other (8 neighbours): the open water, not a pond or a lake."""
        left, best = set(self.water), set()
        while left:
            seed = left.pop()
            seen, stack = {seed}, [seed]
            while stack:
                u = stack.pop()
                pu = self.point(u)
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        v = (u[0] + di, u[1] + dj)
                        if v in left and not self.crossings(pu, self.point(v)):     # a step may not cross the shore
                            left.discard(v)
                            seen.add(v)
                            stack.append(v)
            if len(seen) > len(best):
                best = seen
        return best

    def route(self, start, goal):
        sea = self.largest_body()
        a = min(sea, key=lambda k: dm.km(self.point(k), start))
        b = min(sea, key=lambda k: dm.km(self.point(k), goal))
        print(f"   water: {len(sea)} points in the largest body; start {dm.km(self.point(a), start):.2f} km and goal "
              f"{dm.km(self.point(b), goal):.2f} km from their hints")
        dist, prev, heap = {a: 0.0}, {}, [(0.0, a)]
        while heap:
            d, u = heapq.heappop(heap)
            if u == b:
                break
            if d > dist.get(u, 1e18):
                continue
            pu = self.point(u)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if not (di or dj):
                        continue
                    v = (u[0] + di, u[1] + dj)
                    if v not in self.water:
                        continue
                    pv = self.point(v)
                    if self.crossings(pu, pv):
                        continue
                    nd = d + dm.km(pu, pv)
                    if nd < dist.get(v, 1e18):
                        dist[v], prev[v] = nd, u
                        heapq.heappush(heap, (nd, v))
        if b not in dist:
            raise SystemExit(f"no water route from {start} to {goal}")
        path = [b]
        while path[-1] != a:
            path.append(prev[path[-1]])
        pts = [self.point(k) for k in reversed(path)]
        out, i = [pts[0]], 0
        while i < len(pts) - 1:
            j = len(pts) - 1
            while j > i + 1 and self.crossings(pts[i], pts[j]):
                j -= 1
            out.append(pts[j])
            i = j
        return [(round(x, 5), round(y, 5)) for x, y in out]
