#!/usr/bin/env python3
"""
Layer 1 — organization: who and where.

Tenant groups and tenants (Nordfiber, customers, facility operators,
suppliers), regions, site groups, sites (generated from the DC/PoP profiles),
one Location per room, contact groups/roles/contacts, and the contact
assignments that point at sites and tenants. (Assignments to racks and
devices are made in layer 2, once those exist.)

Safe to re-run: every object is created or reconciled by ensure().
"""

from collections import Counter

import naming
from common import assign_contact, connect, ensure, report
from data.organization import (
    CONTACT_ASSIGNMENTS, CONTACT_GROUPS, CONTACT_ROLES, CONTACTS, REGIONS, SITE_GROUPS, SITES, TENANT_GROUPS, TENANTS,
)
from layout import rooms_for


def run(nb):
    print("== Tenant groups / tenants ==")
    groups = {}
    for g in TENANT_GROUPS:
        obj, st = ensure(nb.tenancy.tenant_groups, {"slug": g["slug"]}, **g)
        report("tenant group", obj, st)
        groups[g["slug"]] = obj
    tenants = {}
    for t in TENANTS:
        obj, st = ensure(nb.tenancy.tenants, {"slug": t["slug"]}, name=t["name"], slug=t["slug"],
                         group=groups[t["group"]].id, description=t["description"])
        report("tenant", obj, st)
        tenants[t["code"]] = obj

    print("== Regions / site groups ==")
    regions = {}
    for r in REGIONS:
        obj, st = ensure(nb.dcim.regions, {"slug": r["slug"]}, name=r["name"], slug=r["slug"],
                         parent=regions[r["parent"]].id if r["parent"] else None)
        report("region", obj, st)
        regions[r["slug"]] = obj
    site_groups = {}
    for g in SITE_GROUPS:
        obj, st = ensure(nb.dcim.site_groups, {"slug": g["slug"]}, **g)
        report("site group", obj, st)
        site_groups[g["slug"]] = obj

    print("== Sites and rooms ==")
    sites = {}
    for s in SITES:
        group = "data-centers" if s["kind"] == "dc" else "points-of-presence"
        obj, st = ensure(
            nb.dcim.sites, {"slug": naming.site_slug(s)},
            name=s["name"], slug=naming.site_slug(s), status="active", region=regions[s["region"]].id,
            group=site_groups[group].id, tenant=tenants["nordfiber"].id, facility=s["facility"],
            physical_address=s["address"], time_zone=s["tz"], latitude=s["lat"], longitude=s["lon"],
            description=s["description"],
        )
        report("site", obj, st)
        sites[s["code"]] = obj
        for room in rooms_for(s):
            name, _ = naming.ROOMS[room]
            loc, st = ensure(nb.dcim.locations, {"slug": naming.room_slug(s, room)},
                             name=name, slug=naming.room_slug(s, room), site=obj.id)
            report("room", loc, st, s["code"])

    print("== Contacts ==")
    cgroups = {}
    for g in CONTACT_GROUPS:
        obj, st = ensure(nb.tenancy.contact_groups, {"slug": g["slug"]}, **g)
        report("contact group", obj, st)
        cgroups[g["slug"]] = obj
    croles = {}
    for r in CONTACT_ROLES:
        obj, st = ensure(nb.tenancy.contact_roles, {"slug": r["slug"]}, **r)
        report("contact role", obj, st)
        croles[r["slug"]] = obj
    contacts = {}
    for c in CONTACTS:
        obj, st = ensure(nb.tenancy.contacts, {"name": c["name"]}, name=c["name"], groups=[cgroups[c["group"]].id],
                         title=c["title"], email=c["email"], phone=c["phone"])
        report("contact", obj, st)
        contacts[c["name"]] = obj

    counts = Counter()
    for a in CONTACT_ASSIGNMENTS:
        if a["kind"] == "site":
            ot, oid = "dcim.site", sites[a["ref"]].id
        elif a["kind"] == "tenant":
            ot, oid = "tenancy.tenant", tenants[a["ref"]].id
        else:
            continue  # rack/device assignments are made in layer 2
        counts[assign_contact(nb, contacts[a["contact"]], croles[a["role"]], ot, oid)] += 1
    print(f"  contact assignments (sites/tenants): {dict(counts)}")


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nLayer 1 (organization) complete.")
