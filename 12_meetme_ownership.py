#!/usr/bin/env python3
"""
Phase 12: MeetMe room ownership + empty-room racks (added post-hoc,
2026-09-27).

Two corrections to Phase 11's MeetMe room model — see config.py's Phase 12
comment block for the full confirmed design:

  1. Malmo and Oslo's MeetMe rooms (Locations only, since Phase 11) get
     real racks now. Stockholm's rack is re-tenanted to Nordfiber itself
     (it's their own datacenter, not a colocation PoP) rather than
     Skagerrak. Malmo gets its OWN new facility-operator tenant, Oresund
     Exchange AB, distinct from Skagerrak (which operates Gothenburg AND
     Oslo).
  2. Every MeetMe room gets a Nordfiber-owned demarc panel, inserted into
     the existing tenant cross-connect chains from Phase 11 (a proper
     front-to-front cross-connect jumper, then a rear-to-rear trunk back
     to sto-patch-01/got-patch-01) — Nordfiber is a facility customer at
     every PoP too, same as Polaris/Vasthamnen.

Also adds Contacts for both facility operators, assigned at the site, rack,
and device level wherever they're active.

Depends on Phase 5 (patch panel device type), Phase 11 (MeetMe Locations,
tenant cross-connect chains). Safe to re-run.
"""

from common import (
    connect,
    create_cable_if_needed,
    create_device_type_from_yaml,
    disconnect_direct_cable_if_present,
    fetch_devicetype_yaml,
    get_front_port,
    get_or_create,
    get_rear_port,
    report,
)
from config import (
    FMS_DEVICE_TYPE_SOURCES,
    FMS_MANUFACTURERS,
    MEETME_FACILITY_CONTACTS,
    MEETME_NEW_RACKS,
    MEETME_PANELS,
    MEETME_RETROFITS,
    MEETME_TENANT_2,
)


def run(nb):
    sites = {s.slug: s for s in nb.dcim.sites.all()}
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}

    print("== Correct Stockholm's MeetMe rack to Nordfiber ownership ==")
    sto_rack = nb.dcim.racks.get(name="STO-RACK-MMR1")
    nordfiber_tenant = nb.tenancy.tenants.get(slug="nordfiber-ab")
    if sto_rack.tenant.id != nordfiber_tenant.id:
        sto_rack.tenant = nordfiber_tenant.id
        sto_rack.save()
        print(f"  [updated] rack: STO-RACK-MMR1 tenant -> {nordfiber_tenant.name}")
    else:
        print(f"  [exists ] rack: STO-RACK-MMR1 tenant already {nordfiber_tenant.name}")

    print("== Oresund Exchange AB (new facility-operator tenant) ==")
    tg_fields = dict(MEETME_TENANT_2)
    group_slug = tg_fields.pop("group_slug")
    group = nb.tenancy.tenant_groups.get(slug=group_slug)
    oresund_tenant, created = get_or_create(
        nb.tenancy.tenants, {"slug": tg_fields["slug"]}, group=group.id, **tg_fields
    )
    report("tenant", oresund_tenant, created)

    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}

    print("== New MeetMe racks (Malmo, Oslo) ==")
    racks = {r.name: r for r in nb.dcim.racks.all()}
    for r in MEETME_NEW_RACKS:
        obj, created = get_or_create(
            nb.dcim.racks,
            {"name": r["name"], "site_id": sites[r["site_slug"]].id},
            name=r["name"],
            site=sites[r["site_slug"]].id,
            location=locations[r["location_slug"]].id,
            tenant=tenants[r["tenant_slug"]].id,
            status="active",
            width=19,
            u_height=42,
        )
        report("rack", obj, created)
        racks[r["name"]] = obj

    print("== Patch panel device type (reused from Phase 5) ==")
    manufacturers = {}
    for m in FMS_MANUFACTURERS:
        obj, created = get_or_create(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        manufacturers[m["name"]] = obj
    panel_type = None
    for mfr_name, path in FMS_DEVICE_TYPE_SOURCES:
        yaml_data = fetch_devicetype_yaml(path)
        panel_type = create_device_type_from_yaml(nb, manufacturers, yaml_data)
    panel_role = nb.dcim.device_roles.get(slug="patch-panel")

    print("== MeetMe-room panels (one Nordfiber demarc + one facility-owner's per non-Nordfiber-owned room) ==")
    all_devices = {d.name: d for d in nb.dcim.devices.all()}
    for p in MEETME_PANELS:
        rack = racks[p["rack"]]
        obj, created = get_or_create(
            nb.dcim.devices, {"name": p["name"]},
            name=p["name"], device_type=panel_type.id, role=panel_role.id,
            site=rack.site.id, location=locations[p["location_slug"]].id, rack=rack.id,
            position=p["position"], face="front", tenant=tenants[p["tenant_slug"]].id, status="active",
        )
        report("device", obj, created)
        all_devices[p["name"]] = obj

    print("== Retrofit: insert Nordfiber's MeetMe panel into each existing cross-connect chain ==")
    for r in MEETME_RETROFITS:
        tenant = tenants[r["tenant_slug"]]
        nordfiber_tenant = tenants["nordfiber-ab"]

        tenant_panel = all_devices[r["tenant_mmr_panel"]]
        nordfiber_mmr_panel = all_devices[r["nordfiber_mmr_panel"]]
        nordfiber_patch = all_devices[r["nordfiber_patch_panel"]]

        tenant_front = get_front_port(nb, tenant_panel, r["tenant_mmr_port"])
        old_patch_rear = get_rear_port(nb, nordfiber_patch, r["nordfiber_patch_port"])
        disconnect_direct_cable_if_present(
            nb, tenant_front, "dcim.frontport", old_patch_rear, "dcim.rearport",
        )

        nordfiber_mmr_front = get_front_port(nb, nordfiber_mmr_panel, r["nordfiber_mmr_port"])
        create_cable_if_needed(
            nb,
            tenant_front, "dcim.frontport",
            nordfiber_mmr_front, "dcim.frontport",
            status="connected",
            label=r["jumper_cable_label"],
            comments=f"{r['tenant_mmr_panel']} <-> {r['nordfiber_mmr_panel']} (cross-connect jumper, MeetMe room)",
            tenant=tenant.id,
        )

        nordfiber_mmr_rear = get_rear_port(nb, nordfiber_mmr_panel, r["nordfiber_mmr_port"])
        create_cable_if_needed(
            nb,
            nordfiber_mmr_rear, "dcim.rearport",
            old_patch_rear, "dcim.rearport",
            status="connected",
            label=r["trunk_cable_label"],
            comments=f"{r['nordfiber_mmr_panel']} <-> {r['nordfiber_patch_panel']} (trunk, MeetMe room to telecom room)",
            tenant=nordfiber_tenant.id,
        )

    print("== Facility operator contacts, assigned at site/rack/device level ==")
    contact_groups = {cg.slug: cg for cg in nb.tenancy.contact_groups.all()}
    contact_role = nb.tenancy.contact_roles.get(slug="technical-contact")
    for c in MEETME_FACILITY_CONTACTS:
        fields = dict(c)
        site_slugs = fields.pop("site_slugs")
        rack_names = fields.pop("racks")
        device_names = fields.pop("devices")
        fields.pop("tenant_slug")
        group_slug = fields.pop("group_slug")
        contact, created = get_or_create(
            nb.tenancy.contacts, {"name": fields["name"]},
            groups=[contact_groups[group_slug].id], **fields,
        )
        report("contact", contact, created)

        def assign(object_type, object_id, label):
            existing = list(nb.tenancy.contact_assignments.filter(
                contact_id=contact.id, object_type=object_type, object_id=object_id,
            ))
            if existing:
                report("contact assignment", existing[0], False)
            else:
                obj = nb.tenancy.contact_assignments.create(
                    contact=contact.id, role=contact_role.id,
                    object_type=object_type, object_id=object_id,
                )
                report("contact assignment", obj, True)

        for site_slug in site_slugs:
            assign("dcim.site", sites[site_slug].id, site_slug)
        for rack_name in rack_names:
            assign("dcim.rack", racks[rack_name].id, rack_name)
        for device_name in device_names:
            assign("dcim.device", all_devices[device_name].id, device_name)


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 12 (MeetMe room ownership) complete.")
