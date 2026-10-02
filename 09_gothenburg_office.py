#!/usr/bin/env python3
"""
Phase 9: Erik Lindqvist's workplace + a Gothenburg Internet circuit
(added post-hoc, 2026-09-27).

Gives Erik Lindqvist (already a Contact, NOC Engineer, Phase 1) an actual
physical desk at the Gothenburg PoP: a desktop PC on an office floor, wired
through a TP outlet to an IDF switch on the same floor, which has its own
fiber uplink down to the core switch in the ground-floor telecom room. Also
adds a standalone Internet transit circuit at the same site — a regional
ISP the size of Nordfiber still has to buy its own upstream somewhere. See
config.py's Phase 9 comment block for the confirmed design assumptions
(same site/new Locations, shared mgmt prefix, single-sided circuit).

Creates, in dependency order:
  2 new Locations + 1 rack -> 2 new device types (fetched from the real
  devicetype-library) -> 2 device roles -> 2 devices -> mgmt IPs -> 2
  cables (TP outlet run, fiber uplink) -> a device-level contact
  assignment for Erik -> an Internet Access circuit type/provider/circuit,
  cabled to got-rtr-01.

Depends on Phase 1 (Erik's Contact, the Gothenburg site) and Phase 2
(got-sw-01, got-rtr-01). Safe to re-run.
"""

from common import (
    connect,
    create_cable_if_needed,
    create_device_type_from_yaml,
    fetch_devicetype_yaml,
    get_interface,
    get_or_create,
    report,
)
from config import (
    GOTHENBURG_INTERNET_CIRCUIT,
    GOTHENBURG_INTERNET_CIRCUIT_TYPE,
    GOTHENBURG_INTERNET_PROVIDER,
    GOTHENBURG_OFFICE_CABLES,
    GOTHENBURG_OFFICE_CONTACT_ASSIGNMENT,
    GOTHENBURG_OFFICE_DEVICE_ROLES,
    GOTHENBURG_OFFICE_DEVICE_TYPE_SOURCES,
    GOTHENBURG_OFFICE_DEVICES,
    GOTHENBURG_OFFICE_LOCATIONS,
    GOTHENBURG_OFFICE_RACKS,
    MANUFACTURERS,
)


def run(nb):
    sites = {s.slug: s for s in nb.dcim.sites.all()}
    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}

    print("== Manufacturers (Arista, Dell already exist) ==")
    manufacturers = {}
    for m in MANUFACTURERS:
        obj, created = get_or_create(nb.dcim.manufacturers, {"slug": m["slug"]}, **m)
        manufacturers[m["name"]] = obj

    print("== Office + IDF Locations ==")
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}
    for loc in GOTHENBURG_OFFICE_LOCATIONS:
        fields = {"name": loc["name"], "slug": loc["slug"], "site": sites[loc["site_slug"]].id}
        if loc["parent_slug"]:
            fields["parent"] = locations[loc["parent_slug"]].id
        obj, created = get_or_create(nb.dcim.locations, {"slug": loc["slug"]}, **fields)
        report("location", obj, created)
        locations[loc["slug"]] = obj

    print("== IDF rack ==")
    racks = {r.name: r for r in nb.dcim.racks.all()}
    for r in GOTHENBURG_OFFICE_RACKS:
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

    print("== Device types (fetched from the real devicetype-library) ==")
    device_types = {}
    for mfr_name, path in GOTHENBURG_OFFICE_DEVICE_TYPE_SOURCES:
        yaml_data = fetch_devicetype_yaml(path)
        dt = create_device_type_from_yaml(nb, manufacturers, yaml_data)
        device_types[dt.slug] = dt

    print("== Device roles ==")
    device_roles = {}
    for r in GOTHENBURG_OFFICE_DEVICE_ROLES:
        obj, created = get_or_create(nb.dcim.device_roles, {"slug": r["slug"]}, **r)
        report("device role", obj, created)
        device_roles[r["slug"]] = obj

    print("== Devices (IDF switch + Erik's workstation) ==")
    devices = {}
    for d in GOTHENBURG_OFFICE_DEVICES:
        fields = {
            "name": d["name"],
            "device_type": device_types[d["device_type_slug"]].id,
            "role": device_roles[d["role_slug"]].id,
            "site": sites[d["site_slug"]].id,
            "location": locations[d["location_slug"]].id,
            "tenant": tenants[d["tenant_slug"]].id,
            "status": "active",
        }
        # Only the switch is rack-mounted — Erik's desktop sits on/under his desk.
        if "rack_name" in d:
            fields["rack"] = racks[d["rack_name"]].id
            fields["position"] = d["position"]
            fields["face"] = "front"
        obj, created = get_or_create(nb.dcim.devices, {"name": d["name"]}, **fields)
        report("device", obj, created)
        devices[d["name"]] = obj

    print("== Management IP addresses (assigned + set as primary IPv4) ==")
    for d in GOTHENBURG_OFFICE_DEVICES:
        device = devices[d["name"]]
        iface = nb.dcim.interfaces.get(device_id=device.id, name=d["mgmt_interface"])
        if iface is None:
            raise SystemExit(f"Interface {d['mgmt_interface']!r} not found on device {d['name']!r}")
        ip, created = get_or_create(
            nb.ipam.ip_addresses,
            {"address": d["mgmt_ip"]},
            address=d["mgmt_ip"],
            tenant=tenants[d["ip_tenant_slug"]].id,
            status="active",
            assigned_object_type="dcim.interface",
            assigned_object_id=iface.id,
        )
        report("mgmt IP", ip, created)
        if str(device.primary_ip4) != d["mgmt_ip"]:
            device.primary_ip4 = ip.id
            device.save()
            print(f"           set as primary IPv4 for {d['name']}")

    print("== Cabling: TP outlet run + fiber uplink ==")
    for c in GOTHENBURG_OFFICE_CABLES:
        a_dev = devices.get(c["a_device"]) or nb.dcim.devices.get(name=c["a_device"])
        b_dev = devices.get(c["b_device"]) or nb.dcim.devices.get(name=c["b_device"])
        a_iface = get_interface(nb, a_dev, c["a_iface"])
        b_iface = get_interface(nb, b_dev, c["b_iface"])
        create_cable_if_needed(
            nb,
            a_iface, "dcim.interface",
            b_iface, "dcim.interface",
            status="connected",
            label=c["label"],
            type=c["type"],
            comments=c["comments"],
            tenant=tenants[c["tenant_slug"]].id,
        )

    print("== Erik's device-level contact assignment ==")
    ca = GOTHENBURG_OFFICE_CONTACT_ASSIGNMENT
    contact = nb.tenancy.contacts.get(name=ca["contact"])
    contact_role = nb.tenancy.contact_roles.get(slug=ca["role_slug"])
    device = devices[ca["device_name"]]
    existing = list(nb.tenancy.contact_assignments.filter(
        contact_id=contact.id, object_type="dcim.device", object_id=device.id,
    ))
    if existing:
        report("contact assignment", existing[0], False)
    else:
        obj = nb.tenancy.contact_assignments.create(
            contact=contact.id,
            role=contact_role.id,
            object_type="dcim.device",
            object_id=device.id,
        )
        report("contact assignment", obj, True)

    print("== Internet provider + circuit type ==")
    provider, created = get_or_create(
        nb.circuits.providers, {"slug": GOTHENBURG_INTERNET_PROVIDER["slug"]}, **GOTHENBURG_INTERNET_PROVIDER
    )
    report("provider", provider, created)
    circuit_type, created = get_or_create(
        nb.circuits.circuit_types, {"slug": GOTHENBURG_INTERNET_CIRCUIT_TYPE["slug"]}, **GOTHENBURG_INTERNET_CIRCUIT_TYPE
    )
    report("circuit type", circuit_type, created)

    print("== Internet circuit (single-sided: provider network isn't ours to document) ==")
    ic = GOTHENBURG_INTERNET_CIRCUIT
    circuit, created = get_or_create(
        nb.circuits.circuits,
        {"cid": ic["cid"]},
        cid=ic["cid"],
        provider=provider.id,
        type=circuit_type.id,
        tenant=tenants[ic["tenant_slug"]].id,
        status=ic["status"],
        commit_rate=ic["commit_rate"],
        description=ic["description"],
    )
    report("circuit", circuit, created)

    site = sites[ic["site_slug"]]
    term = nb.circuits.circuit_terminations.get(circuit_id=circuit.id, term_side="A")
    if term is None:
        term = nb.circuits.circuit_terminations.create(
            circuit=circuit.id,
            term_side="A",
            termination_type="dcim.site",
            termination_id=site.id,
            port_speed=ic["commit_rate"],
        )
        print(f"  [created] termination A: {site.name} (id={term.id})")
    else:
        print(f"  [exists ] termination A: {site.name} (id={term.id})")

    router = nb.dcim.devices.get(name=ic["device"])
    router_iface = get_interface(nb, router, ic["iface"])
    create_cable_if_needed(
        nb,
        term, "circuits.circuittermination",
        router_iface, "dcim.interface",
        status="connected",
        label=ic["cable_label"],
        comments=f"{ic['cid']} (A-side) demarc",
        tenant=tenants["nordfiber-ab"].id,
    )


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 9 (Gothenburg office + Internet circuit) complete.")
