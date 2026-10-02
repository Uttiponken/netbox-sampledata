#!/usr/bin/env python3
"""
Phase 16: Gothenburg PoP -> Datacenter (added post-hoc, 2026-09-30).

Reclassifies the Gothenburg site as a full Datacenter (name + SiteGroup)
and adds new growth capacity (a new Suite/Row with 2 empty racks) — real
datacenters carry spare white space, unlike a lean PoP. Deliberately does
NOT rename the site's slug or any got-*/gothenburg-pop-prefixed
Location/Rack/Device slug elsewhere in this dataset — see config.py's
Phase 16 comment for why.

get_or_create() never updates an existing object's fields (same gotcha as
Phases 12/15), so the Site's name/group are explicitly reconciled here
rather than left to SITES' own get_or_create in 01_organization.py, which
already ran once with the old values.

Depends on Phase 1 (the Gothenburg site itself). Safe to re-run.
"""

from common import connect, get_or_create, report
from config import GOTHENBURG_DC_LOCATIONS, GOTHENBURG_DC_RACKS, SITES

GOTHENBURG = next(s for s in SITES if s["slug"] == "nordfiber-gothenburg-pop")


def run(nb):
    print("== Reclassify Gothenburg as a Datacenter ==")
    site = nb.dcim.sites.get(slug=GOTHENBURG["slug"])
    site_group = nb.dcim.site_groups.get(slug=GOTHENBURG["group_slug"])
    changed = []
    if site.name != GOTHENBURG["name"]:
        site.name = GOTHENBURG["name"]
        changed.append("name")
    if site.group.id != site_group.id:
        site.group = site_group.id
        changed.append("group")
    if site.description != GOTHENBURG["description"]:
        site.description = GOTHENBURG["description"]
        changed.append("description")
    if changed:
        site.save()
        print(f"  [updated] site: {site.name} — {', '.join(changed)}")
    else:
        print(f"  [exists ] site: {site.name} (already a Datacenter)")

    print("== New Suite 200 / Row C ==")
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}
    for loc in GOTHENBURG_DC_LOCATIONS:
        fields = {"name": loc["name"], "slug": loc["slug"], "site": site.id}
        if loc["parent_slug"]:
            fields["parent"] = locations[loc["parent_slug"]].id
        obj, created = get_or_create(nb.dcim.locations, {"slug": loc["slug"]}, **fields)
        report("location", obj, created)
        locations[loc["slug"]] = obj

    print("== New growth-capacity racks (empty) ==")
    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    for r in GOTHENBURG_DC_RACKS:
        obj, created = get_or_create(
            nb.dcim.racks,
            {"name": r["name"], "site_id": site.id},
            name=r["name"],
            site=site.id,
            location=locations[r["location_slug"]].id,
            tenant=tenants[r["tenant_slug"]].id,
            status="active",
            width=19,
            u_height=42,
        )
        report("rack", obj, created)


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 16 (Gothenburg PoP -> Datacenter) complete.")
