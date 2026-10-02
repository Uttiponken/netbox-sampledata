#!/usr/bin/env python3
"""
Phase 18: real route geography for the domestic backbone fiber
(added post-hoc, 2026-09-30).

Gives the 3 original backbone cables (Phase 5) real geographic routes,
using netbox-pathways — but via a different mechanism than Phase 17's
Helsinki circuits, since these are physical dcim.Cables, not
circuits.Circuit objects. Each cable gets its own DirectBuried pathway
(a real multi-point LineString, fiber genuinely buried alongside a road
corridor) plus a CableSegment joining that pathway to the actual cable.
Confirmed empirically before building: creating a CableSegment correctly
bumps the pathway's own `cables_routed` counter.

See config.py's Phase 18 comment for the exact routes as given by the
user (bb-cbl-00001 via Vasteras/Orebro/Karlstad/Trollhattan, bb-cbl-00002
via the E4 through Linkoping/Jonkoping/Markaryd/Hassleholm/Lund,
bb-cbl-00003 along the E6 via Uddevalla/Stromstad).

Depends on Phase 5 (the 3 backbone cables already exist). Requires
netbox-pathways. Safe to re-run — and, unlike Phase 5-13's cable
helpers, a route CAN legitimately change after the fact (confirmed:
swapping Tanumshede for Trollhattan on bb-cbl-00001), so an existing
pathway's `path`/`comments` are explicitly reconciled against config.py
rather than left untouched once created.
"""

from common import connect, report
from config import BACKBONE_CABLE_ROUTES


def run(nb):
    for route in BACKBONE_CABLE_ROUTES:
        print(f"== {route['cable_label']} ==")
        cable = nb.dcim.cables.get(label=route["cable_label"])

        expected_coords = [[lon, lat] for _name, lon, lat in route["waypoints"]]
        wkt_points = ", ".join(f"{lon} {lat}" for lon, lat in expected_coords)
        path_wkt = f"LINESTRING ({wkt_points})"

        pathway = nb.plugins.pathways.direct_buried.get(label=route["pathway_label"])
        if pathway is None:
            pathway = nb.plugins.pathways.direct_buried.create(
                label=route["pathway_label"],
                path=path_wkt,
                comments=route["comments"],
            )
            report("pathway", pathway, True)
        else:
            changed = []
            current_coords = pathway.path.coordinates if pathway.path else None
            if current_coords != expected_coords:
                pathway.path = path_wkt
                changed.append("path")
            if pathway.comments != route["comments"]:
                pathway.comments = route["comments"]
                changed.append("comments")
            if changed:
                pathway.save()
                print(f"  [updated] pathway: {pathway.label} (id={pathway.id}) — {', '.join(changed)}")
            else:
                report("pathway", pathway, False)

        existing_segment = nb.plugins.pathways.cable_segments.get(cable_id=cable.id, pathway_id=pathway.id)
        if existing_segment:
            report("cable segment", existing_segment, False)
        else:
            segment = nb.plugins.pathways.cable_segments.create(
                cable=cable.id, pathway=pathway.id, sequence=1,
            )
            report("cable segment", segment, True)


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 18 (backbone fiber route geography) complete.")
