#!/usr/bin/env python3
"""
Layer 2 — hardware: everything that sits in a rack, at its FINAL name and slot.

  manufacturers + real device/module types (live from the community library)
  -> the netbox-wdm profile and its full 40-channel plan (must exist BEFORE
     the muxponders, so each muxponder gets all 40 channels when created)
  -> device roles, rack roles, racks
  -> every device (Nordfiber's core racks, MeetMe panels, colo customers'
     switches/panels/servers, the Gothenburg IDF and Erik's desk) with a
     serial and — for Nordfiber-owned devices — an asset tag
  -> DCP-110 modules in the DCP-2 shelves
  -> contact assignments that point at racks and devices

Racks and devices come from layout.py, so every site of the same kind is
alike by construction. Rack placement is only applied at creation; this
script never silently moves anything on a re-run.
"""

import re

import naming
from common import (
    api, assign_contact, connect, create_device_type_from_yaml, create_module_type_from_yaml, ensure,
    fetch_devicetype_yaml, fetch_moduletype_yaml, get_or_create, have, report, skip, version_at_least,
)
from data import hardware as H
from data.organization import CONTACT_ASSIGNMENTS, SITES, TENANTS
from layout import inventory, site_by_code

WDM_PROFILE = {"node_type": "terminal_mux", "fiber_type": "single_fiber"}


def wdm_grid():
    """The 100 GHz C-band grid key; netbox-wdm 0.3.0 renamed it and migrates the rows it already holds."""
    return "dwdm_c_100ghz" if version_at_least("wdm", 0, 3) else "dwdm_100ghz"


SITE_CODE = {naming.site_slug(s): s["code"].upper() for s in SITES}


class Identity:
    """Serials <MFR>-<SITE>-<nnnn> and asset tags NF-<SITE>-<nnnnn>; numbering continues after what exists, never renumbers."""

    def __init__(self, devices):
        self.serial, self.tag = {}, {}
        for d in devices:
            site = SITE_CODE[d.site.slug]
            mfr = naming.MANUFACTURER_CODES[d.device_type.manufacturer.slug]
            m = re.fullmatch(rf"{mfr}-{site}-(\d+)", d.serial or "")
            if m:
                self.serial[(mfr, site)] = max(self.serial.get((mfr, site), 1), int(m.group(1)) + 1)
            m = re.fullmatch(rf"NF-{site}-(\d+)", d.asset_tag or "")
            if m:
                self.tag[site] = max(self.tag.get(site, 1), int(m.group(1)) + 1)

    def next_serial(self, mfr_slug, site):
        mfr = naming.MANUFACTURER_CODES[mfr_slug]
        n = self.serial.get((mfr, site), 1)
        self.serial[(mfr, site)] = n + 1
        return f"{mfr}-{site}-{n:04d}"

    def next_tag(self, site):
        n = self.tag.get(site, 1)
        self.tag[site] = n + 1
        return f"NF-{site}-{n:05d}"


def wdm_nodes(nb, wdm_type, devices):
    """
    netbox-wdm makes a WdmNode only when a Device is CREATED while its profile exists. If the plugin was added after
    the devices (a build that ran without it), the nodes are missing; make them here so a later run completes the
    optical layer.
    """
    print("== WDM nodes ==")
    for dev in devices.values():
        if dev.device_type.id != wdm_type.id:
            continue
        if nb.plugins.wdm.wdm_nodes.get(device_id=dev.id):
            continue
        node = nb.plugins.wdm.wdm_nodes.create(device=dev.id, node_type=WDM_PROFILE["node_type"], grid=wdm_grid())
        report("wdm node", node, "created", dev.name)


def run(nb):
    print("== Manufacturers and device types ==")
    manufacturers = {}
    for m in H.MANUFACTURERS:
        obj, st = ensure(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        manufacturers[m["name"]] = obj
    types = {}
    for path in H.DEVICE_TYPE_SOURCES:
        dt = create_device_type_from_yaml(nb, manufacturers, fetch_devicetype_yaml(path))
        types[dt.slug] = dt
    for spec in H.CUSTOM_DEVICE_TYPES:
        dt = create_device_type_from_yaml(nb, manufacturers, spec)
        types[dt.slug] = dt
    module_types = {}
    for path in H.MODULE_TYPE_SOURCES:
        mt = create_module_type_from_yaml(nb, manufacturers, fetch_moduletype_yaml(path))
        module_types[mt.model] = mt

    print("== WDM profile + 40-channel plan ==")
    wdm_type = types[H.T_WDM]
    if have("wdm"):
        profile, st = ensure(nb.plugins.wdm.wdm_profiles, {"device_type_id": wdm_type.id}, device_type=wdm_type.id, grid=wdm_grid(), **WDM_PROFILE)
        report("wdm profile", profile, st)
        made = 0
        for n in range(1, 41):
            if nb.plugins.wdm.wdm_channel_plans.get(profile_id=profile.id, grid_position=n):
                continue
            fpt = nb.dcim.front_port_templates.get(devicetype_id=wdm_type.id, name=str(920 + n))
            # WdmChannelPlan keeps wavelength_nm as given and requires it unique per
            # profile (the derived WdmChannel gets the real ITU value), so use a
            # distinct placeholder per position.
            nb.plugins.wdm.wdm_channel_plans.create(
                profile=profile.id, grid_position=n, wavelength_nm=1550.0 + n, label="placeholder",
                mux_front_port_template=fpt.id, demux_front_port_template=fpt.id)
            made += 1
        print(f"  channel plan entries created: {made} (of 40)")
    else:
        skip("wdm", "WDM profile and 40-channel plan")

    print("== Roles ==")
    roles = {r["slug"]: ensure(nb.dcim.device_roles, {"slug": r["slug"]}, **r)[0] for r in H.DEVICE_ROLES}
    rack_roles = {r["slug"]: ensure(nb.dcim.rack_roles, {"slug": r["slug"]}, **r)[0] for r in H.RACK_ROLES}

    sites = {s.slug: s for s in nb.dcim.sites.all()}
    locations = {l.slug: l for l in nb.dcim.locations.all()}
    tenants = {t["code"]: nb.tenancy.tenants.get(slug=t["slug"]) for t in TENANTS}
    racks_spec, devices_spec = inventory()

    print("== Racks ==")
    racks = {}
    for r in racks_spec:
        site = site_by_code(r["site"])
        obj, st = ensure(
            nb.dcim.racks, {"name": r["name"], "site_id": sites[naming.site_slug(site)].id},
            name=r["name"], site=sites[naming.site_slug(site)].id, location=locations[naming.room_slug(site, r["room"])].id,
            tenant=tenants[r["tenant"]].id, role=rack_roles[r["role"]].id, status="active", width=19, u_height=42,
        )
        report("rack", obj, st)
        racks[r["name"]] = obj

    print("== Devices ==")
    identity = Identity(list(nb.dcim.devices.all()))
    devices = {}
    for d in devices_spec:
        site = site_by_code(d["site"])
        fields = dict(name=d["name"], device_type=types[d["type"]].id, role=roles[d["role"]].id,
                      site=sites[naming.site_slug(site)].id, location=locations[naming.room_slug(site, d["room"])].id,
                      tenant=tenants[d["tenant"]].id, status="active")
        if d["rack"]:
            fields.update(rack=racks[d["rack"]].id, position=d["position"], face="front")
        obj, st = ensure(nb.dcim.devices, {"name": d["name"]}, once=("rack", "position", "face", "location", "device_type"), **fields)
        missing = {}
        if not obj.serial:
            missing["serial"] = identity.next_serial(obj.device_type.manufacturer.slug, d["site"].upper())
        if not obj.asset_tag and d["tenant"] == "nordfiber":
            missing["asset_tag"] = identity.next_tag(d["site"].upper())
        if missing:
            obj.update(missing)
            st = st if st == "created" else "updated"
        report("device", obj, st, f"{d['rack'] or 'unracked'}" + (f" U{int(d['position'])}" if d["position"] else ""))
        devices[d["name"]] = obj

    if have("wdm"):
        wdm_nodes(nb, wdm_type, devices)

    print("== DCP-110 modules in the DCP-2 shelves ==")
    for code, bays in H.DCP2_MODULE_BAYS.items():
        shelf = devices[f"{code}-dcp2-01"]
        for bay_name in bays:
            bay = nb.dcim.module_bays.get(device_id=shelf.id, name=bay_name)
            if nb.dcim.modules.get(device_id=shelf.id, module_bay_id=bay.id):
                print(f"  [exists ] {shelf.name} {bay_name}")
                continue
            nb.dcim.modules.create(device=shelf.id, module_bay=bay.id, module_type=module_types["DCP-110"].id, status="active")
            print(f"  [created] {shelf.name} {bay_name}: DCP-110")

    print("== Contact assignments for racks and devices ==")
    croles = {r.slug: r for r in nb.tenancy.contact_roles.all()}
    contacts = {c.name: c for c in nb.tenancy.contacts.all()}
    for a in CONTACT_ASSIGNMENTS:
        if a["kind"] == "rack":
            ot, oid = "dcim.rack", racks[a["ref"]].id
        elif a["kind"] == "device":
            ot, oid = "dcim.device", devices[a["ref"]].id
        else:
            continue
        print(f"  [{assign_contact(nb, contacts[a['contact']], croles[a['role']], ot, oid):7}] {a['contact']} -> {a['ref']}")


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nLayer 2 (hardware) complete.")
