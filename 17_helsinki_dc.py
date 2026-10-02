#!/usr/bin/env python3
"""
Phase 17: Helsinki DC + dual leased dark fiber to Stockholm
(added post-hoc, 2026-09-30).

A third, smaller Nordfiber-owned datacenter in Finland, built the same way
as Malmo/Oslo (one rack, one router, one switch, one patch panel), reached
from Stockholm over two independently-routed leased dark fiber pairs from
two different vendors: one primary (shorter route, via Mariehamn/Vaasa),
one backup (longer, more diverse route, via Gotland/Riga/Tallinn). Both
circuits are dark — uncabled at both ends, exactly like the existing
Stockholm<->Oslo lease (PLT-100234) — lighting them is a future phase.

The real route geography is recorded via the newly-adopted netbox-pathways
plugin: one `circuit-geometries` object per circuit, a real multi-point
LineString threading through each route's actual waypoints. See
config.py's Phase 17 comment for the full confirmed design.

Depends on Phase 1 (tenants, Nordics region), Phase 2 (device types/roles
already fetched), Phase 4 (dark-fiber circuit type), Phase 5 (patch panel
device type). Requires netbox-pathways (adopted separately on the
netbox-docker deployment). Safe to re-run.
"""

from common import connect, create_device_type_from_yaml, fetch_devicetype_yaml, get_interface, get_or_create, report, create_cable_if_needed
from config import (
    FMS_HELSINKI_PATCH_PANEL,
    HELSINKI_DEVICES,
    HELSINKI_FIBER_CIRCUITS,
    HELSINKI_FIBER_PROVIDERS,
    HELSINKI_LOCATIONS,
    HELSINKI_MGMT_PREFIX,
    HELSINKI_RACKS,
    HELSINKI_REGION,
    HELSINKI_SITE,
    HELSINKI_UPLINK_CABLE,
)


def run(nb):
    print("== Finland region ==")
    parent = nb.dcim.regions.get(slug=HELSINKI_REGION["parent_slug"])
    region, created = get_or_create(
        nb.dcim.regions, {"slug": HELSINKI_REGION["slug"]},
        name=HELSINKI_REGION["name"], slug=HELSINKI_REGION["slug"], parent=parent.id,
    )
    report("region", region, created)

    print("== Helsinki site ==")
    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    site_group = nb.dcim.site_groups.get(slug=HELSINKI_SITE["group_slug"])
    site_fields = dict(HELSINKI_SITE)
    site_fields.pop("region_slug")
    site_fields.pop("group_slug")
    site, created = get_or_create(
        nb.dcim.sites, {"slug": HELSINKI_SITE["slug"]},
        region=region.id, group=site_group.id, tenant=tenants[HELSINKI_SITE["tenant_slug"]].id,
        **{k: v for k, v in site_fields.items() if k != "tenant_slug"},
    )
    report("site", site, created)

    print("== Telecom Room ==")
    locations = {}
    for loc in HELSINKI_LOCATIONS:
        obj, created = get_or_create(
            nb.dcim.locations, {"slug": loc["slug"]},
            name=loc["name"], slug=loc["slug"], site=site.id,
        )
        report("location", obj, created)
        locations[loc["slug"]] = obj

    print("== HEL-RACK-1 ==")
    racks = {}
    for r in HELSINKI_RACKS:
        obj, created = get_or_create(
            nb.dcim.racks, {"name": r["name"], "site_id": site.id},
            name=r["name"], site=site.id, location=locations[r["location_slug"]].id,
            tenant=tenants[r["tenant_slug"]].id, status="active", width=19, u_height=42,
        )
        report("rack", obj, created)
        racks[r["name"]] = obj

    print("== Devices (router + switch, reusing existing device types) ==")
    device_types = {dt.slug: dt for dt in nb.dcim.device_types.all()}
    device_roles = {dr.slug: dr for dr in nb.dcim.device_roles.all()}
    devices = {}
    for d in HELSINKI_DEVICES:
        obj, created = get_or_create(
            nb.dcim.devices, {"name": d["name"]},
            name=d["name"], device_type=device_types[d["device_type_slug"]].id,
            role=device_roles[d["role_slug"]].id, site=site.id, location=locations[d["location_slug"]].id,
            rack=racks[d["rack_name"]].id, position=d["position"], face="front",
            tenant=tenants[d["tenant_slug"]].id, status="active",
        )
        report("device", obj, created)
        devices[d["name"]] = obj

    print("== Management prefix + IPs ==")
    ipam_role = nb.ipam.roles.get(slug="management")
    p = HELSINKI_MGMT_PREFIX
    prefix, created = get_or_create(
        nb.ipam.prefixes, {"prefix": p["prefix"]},
        prefix=p["prefix"], scope_type="dcim.site", scope_id=site.id,
        tenant=tenants[p["tenant_slug"]].id, role=ipam_role.id, status="active",
        description=f"Out-of-band management network, {site.name}",
    )
    report("prefix", prefix, created)

    for d in HELSINKI_DEVICES:
        device = devices[d["name"]]
        iface = get_interface(nb, device, d["mgmt_interface"])
        ip, created = get_or_create(
            nb.ipam.ip_addresses, {"address": d["mgmt_ip"]},
            address=d["mgmt_ip"], tenant=tenants[d["ip_tenant_slug"]].id, status="active",
            assigned_object_type="dcim.interface", assigned_object_id=iface.id,
        )
        report("mgmt IP", ip, created)
        if str(device.primary_ip4) != d["mgmt_ip"]:
            device.primary_ip4 = ip.id
            device.save()
            print(f"           set as primary IPv4 for {d['name']}")

    print("== Uplink cable ==")
    c = HELSINKI_UPLINK_CABLE
    a_iface = get_interface(nb, devices[c["a_device"]], c["a_iface"])
    b_iface = get_interface(nb, devices[c["b_device"]], c["b_iface"])
    create_cable_if_needed(
        nb, a_iface, "dcim.interface", b_iface, "dcim.interface",
        status="connected", label=c["label"], comments=c["comments"], tenant=tenants[c["tenant_slug"]].id,
    )

    print("== FMS patch panel ==")
    panel_type = device_types["generic-lc-24-port-fiber-patch-panel"]
    panel_role = device_roles["patch-panel"]
    p = FMS_HELSINKI_PATCH_PANEL
    obj, created = get_or_create(
        nb.dcim.devices, {"name": p["name"]},
        name=p["name"], device_type=panel_type.id, role=panel_role.id, site=site.id,
        location=locations[p["location_slug"]].id, rack=racks[p["rack_name"]].id,
        position=p["position"], face="front", tenant=tenants[p["tenant_slug"]].id, status="active",
    )
    report("device", obj, created)

    print("== Dark fiber providers ==")
    providers = {}
    for pr in HELSINKI_FIBER_PROVIDERS:
        obj, created = get_or_create(nb.circuits.providers, {"slug": pr["slug"]}, **pr)
        report("provider", obj, created)
        providers[pr["slug"]] = obj

    print("== Dark fiber circuits (uncabled, both ends) + pathway geometries ==")
    sites = {s.slug: s for s in nb.dcim.sites.all()}
    circuit_type = nb.circuits.circuit_types.get(slug="dark-fiber")
    for fc in HELSINKI_FIBER_CIRCUITS:
        circuit, created = get_or_create(
            nb.circuits.circuits, {"cid": fc["cid"]},
            cid=fc["cid"], provider=providers[fc["provider_slug"]].id, type=circuit_type.id,
            tenant=tenants[fc["tenant_slug"]].id, status=fc["status"], commit_rate=fc["commit_rate"],
            description=fc["description"],
        )
        report("circuit", circuit, created)

        for t in fc["terminations"]:
            term_site = sites[t["site_slug"]]
            term = nb.circuits.circuit_terminations.get(circuit_id=circuit.id, term_side=t["term_side"])
            if term is None:
                term = nb.circuits.circuit_terminations.create(
                    circuit=circuit.id, term_side=t["term_side"],
                    termination_type="dcim.site", termination_id=term_site.id,
                    port_speed=fc["commit_rate"],
                )
                print(f"  [created] termination {t['term_side']}: {term_site.name} (id={term.id})")
            else:
                print(f"  [exists ] termination {t['term_side']}: {term_site.name} (id={term.id})")

        wkt_points = ", ".join(f"{lon} {lat}" for _name, lon, lat in fc["route_waypoints"])
        path_wkt = f"LINESTRING ({wkt_points})"
        existing_geom = nb.plugins.pathways.circuit_geometries.get(circuit_id=circuit.id)
        if existing_geom:
            report("circuit geometry", existing_geom, False)
        else:
            waypoint_names = " -> ".join(name for name, _lon, _lat in fc["route_waypoints"])
            geom = nb.plugins.pathways.circuit_geometries.create(
                circuit=circuit.id,
                path=path_wkt,
                comments=f"Route ({fc['role']}): {waypoint_names}",
            )
            report("circuit geometry", geom, True)


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 17 (Helsinki DC + dual leased dark fiber) complete.")
