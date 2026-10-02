#!/usr/bin/env python3
"""
Phase 1: Organization.

Creates, in NetBox's own dependency order:
  tenant groups -> tenants -> regions -> site groups -> sites -> locations
  -> contact groups -> contact roles -> contacts -> contact assignments

Safe to re-run: every object is looked up by its slug (or, for contacts,
name) before being created.
"""

from common import connect, get_or_create, report
from config import (
    CONTACT_ASSIGNMENTS,
    CONTACT_GROUPS,
    CONTACT_ROLES,
    CONTACTS,
    LOCATIONS,
    REGIONS,
    SITE_GROUPS,
    SITES,
    TENANT_GROUPS,
    TENANTS,
)


def run(nb):
    print("== Tenant groups ==")
    tenant_groups = {}
    for tg in TENANT_GROUPS:
        obj, created = get_or_create(nb.tenancy.tenant_groups, {"slug": tg["slug"]}, **tg)
        report("tenant group", obj, created)
        tenant_groups[tg["slug"]] = obj

    print("== Tenants ==")
    tenants = {}
    for t in TENANTS:
        obj, created = get_or_create(
            nb.tenancy.tenants,
            {"slug": t["slug"]},
            name=t["name"],
            slug=t["slug"],
            group=tenant_groups[t["group_slug"]].id,
            description=t["description"],
        )
        report("tenant", obj, created)
        tenants[t["slug"]] = obj

    print("== Regions ==")
    regions = {}
    for r in REGIONS:
        fields = {"name": r["name"], "slug": r["slug"]}
        if r["parent_slug"]:
            fields["parent"] = regions[r["parent_slug"]].id
        obj, created = get_or_create(nb.dcim.regions, {"slug": r["slug"]}, **fields)
        report("region", obj, created)
        regions[r["slug"]] = obj

    print("== Site groups ==")
    site_groups = {}
    for sg in SITE_GROUPS:
        obj, created = get_or_create(nb.dcim.site_groups, {"slug": sg["slug"]}, **sg)
        report("site group", obj, created)
        site_groups[sg["slug"]] = obj

    print("== Sites ==")
    sites = {}
    for s in SITES:
        obj, created = get_or_create(
            nb.dcim.sites,
            {"slug": s["slug"]},
            name=s["name"],
            slug=s["slug"],
            status=s["status"],
            region=regions[s["region_slug"]].id,
            group=site_groups[s["group_slug"]].id,
            tenant=tenants[s["tenant_slug"]].id,
            facility=s["facility"],
            physical_address=s["physical_address"],
            time_zone=s["time_zone"],
            latitude=s["latitude"],
            longitude=s["longitude"],
            description=s["description"],
        )
        report("site", obj, created)
        sites[s["slug"]] = obj

    print("== Locations ==")
    locations = {}
    for loc in LOCATIONS:
        fields = {
            "name": loc["name"],
            "slug": loc["slug"],
            "site": sites[loc["site_slug"]].id,
        }
        if loc["parent_slug"]:
            fields["parent"] = locations[loc["parent_slug"]].id
        obj, created = get_or_create(nb.dcim.locations, {"slug": loc["slug"]}, **fields)
        report("location", obj, created)
        locations[loc["slug"]] = obj

    print("== Contact groups ==")
    contact_groups = {}
    for cg in CONTACT_GROUPS:
        obj, created = get_or_create(nb.tenancy.contact_groups, {"slug": cg["slug"]}, **cg)
        report("contact group", obj, created)
        contact_groups[cg["slug"]] = obj

    print("== Contact roles ==")
    contact_roles = {}
    for cr in CONTACT_ROLES:
        obj, created = get_or_create(nb.tenancy.contact_roles, {"slug": cr["slug"]}, **cr)
        report("contact role", obj, created)
        contact_roles[cr["slug"]] = obj

    print("== Contacts ==")
    contacts = {}
    for c in CONTACTS:
        obj, created = get_or_create(
            nb.tenancy.contacts,
            {"name": c["name"]},
            name=c["name"],
            groups=[contact_groups[c["group_slug"]].id],
            title=c["title"],
            email=c["email"],
            phone=c["phone"],
        )
        report("contact", obj, created)
        contacts[c["name"]] = obj

    print("== Contact assignments ==")
    for ca in CONTACT_ASSIGNMENTS:
        if ca["object_type"] == "dcim.site":
            object_id = sites[ca["site_slug"]].id
        elif ca["object_type"] == "tenancy.tenant":
            object_id = tenants[ca["tenant_slug"]].id
        else:
            raise ValueError(f"Unhandled object_type in config: {ca['object_type']}")

        existing = nb.tenancy.contact_assignments.filter(
            contact_id=contacts[ca["contact"]].id,
            object_type=ca["object_type"],
            object_id=object_id,
        )
        existing = list(existing)
        if existing:
            report("contact assignment", existing[0], False)
            continue
        obj = nb.tenancy.contact_assignments.create(
            object_type=ca["object_type"],
            object_id=object_id,
            contact=contacts[ca["contact"]].id,
            role=contact_roles[ca["role_slug"]].id,
        )
        report("contact assignment", obj, True)


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 1 (Organization) complete.")
