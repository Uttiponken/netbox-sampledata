#!/usr/bin/env python3
"""
Layer 6: services — management addressing, loopbacks and iBGP, device
credentials, spare assets.

  OOB management prefix per site; every managed device gets its management
  address (assigned to the management interface and set as primary IPv4)
  -> loopback + iBGP full mesh (netbox-bgp) on each site's router 01
  -> one encrypted login secret per router 01 (netbox-secrets)
  -> cold spares depot (netbox-inventory)

Requires layers 1-2. Safe to re-run.
"""

import itertools

import layout
from common import api, connect, ensure, get_secrets_session_key, report
from data import services as S
from data.organization import SITES, TENANTS
from naming import room_slug, site_slug


def addressing(nb):
    tenants = {t["code"]: nb.tenancy.tenants.get(slug=t["slug"]) for t in TENANTS}
    role, st = ensure(nb.ipam.roles, {"slug": "management"}, name="Management", slug="management", weight=100)
    report("ipam role", role, st)

    print("== Management prefixes ==")
    for s in SITES:
        site = nb.dcim.sites.get(slug=site_slug(s))
        obj, st = ensure(nb.ipam.prefixes, {"prefix": f"10.0.{s['mgmt']}.0/24"}, prefix=f"10.0.{s['mgmt']}.0/24",
                         scope_type="dcim.site", scope_id=site.id, tenant=tenants["nordfiber"].id, role=role.id,
                         status="active", description=f"Out-of-band management network, {s['name']}")
        report("prefix", obj, st)

    print("== Management addresses ==")
    code_of = {t["code"]: t["code"] for t in TENANTS}
    _, devices = layout.inventory()
    for d in devices:
        if not d["mgmt_ip"]:
            continue
        device = nb.dcim.devices.get(name=d["name"])
        iface = nb.dcim.interfaces.get(device_id=device.id, name=d["mgmt_iface"])
        ip, st = ensure(nb.ipam.ip_addresses, {"address": d["mgmt_ip"]}, address=d["mgmt_ip"], status="active",
                        tenant=tenants[code_of[d["tenant"]]].id, assigned_object_type="dcim.interface",
                        assigned_object_id=iface.id)
        report("mgmt IP", ip, st, d["name"])
        if not device.primary_ip4 or device.primary_ip4.id != ip.id:
            device.primary_ip4 = ip.id
            device.save()


def bgp(nb):
    tenants = {t["code"]: nb.tenancy.tenants.get(slug=t["slug"]) for t in TENANTS}
    print("== BGP ==")
    rir, st = ensure(nb.ipam.rirs, {"slug": "private-use"}, name="Private Use (RFC 6996)", slug="private-use", is_private=True)
    asn, st = ensure(nb.ipam.asns, {"asn": S.BGP_ASN}, asn=S.BGP_ASN, rir=rir.id, description="Nordfiber AB",
                     tenant=tenants["nordfiber"].id)
    report("asn", asn, st)
    group, st = ensure(nb.plugins.bgp.peer_group, {"name": S.PEER_GROUP["name"]}, local_as=asn.id, remote_as=asn.id,
                       **S.PEER_GROUP)
    report("peer group", group, st)

    loop = {}
    for n, code in enumerate(S.ROUTER_ORDER, start=1):
        dev = nb.dcim.devices.get(name=f"{code}-rtr-01")
        iface, st = ensure(nb.dcim.interfaces, {"device_id": dev.id, "name": "lo0"}, device=dev.id, name="lo0", type="virtual")
        ip, st = ensure(nb.ipam.ip_addresses, {"address": f"10.255.0.{n}/32"}, address=f"10.255.0.{n}/32", status="active",
                        assigned_object_type="dcim.interface", assigned_object_id=iface.id)
        report("loopback", ip, st, dev.name)
        loop[code] = (dev, ip)

    for a, b in itertools.combinations(S.ROUTER_ORDER, 2):
        name = f"{a}-rtr-01_{b}-rtr-01"
        obj, st = ensure(nb.plugins.bgp.session, {"name": name}, name=name, device=loop[a][0].id,
                         local_address=loop[a][1].id, remote_address=loop[b][1].id, local_as=asn.id, remote_as=asn.id,
                         peer_group=group.id, status="active")
        report("bgp session", obj, st)


def secrets(nb):
    print("== Secrets ==")
    key = get_secrets_session_key(nb)
    role, st = ensure(nb.plugins.secrets.secret_roles, {"slug": S.SECRET_ROLE["slug"]}, **S.SECRET_ROLE)
    for code in S.ROUTER_ORDER:
        dev = nb.dcim.devices.get(name=f"{code}-rtr-01")
        if nb.plugins.secrets.secrets.get(assigned_object_type="dcim.device", assigned_object_id=dev.id, name="local-admin"):
            print(f"  [exists ] secret: {dev.name}/local-admin")
            continue
        api("/api/plugins/secrets/secrets/", method="post", extra_headers={"X-Session-Key": key},
            json={"assigned_object_type": "dcim.device", "assigned_object_id": dev.id, "role": role.id,
                  "name": "local-admin", "plaintext": S.PASSWORDS[code]})
        print(f"  [created] secret: {dev.name}/local-admin (value encrypted, not printed)")


def inventory(nb):
    print("== Spare assets ==")
    tenant = nb.tenancy.tenants.get(slug="nordfiber-ab")
    sto = next(s for s in SITES if s["code"] == "sto")
    location = nb.dcim.locations.get(slug=room_slug(sto, "tr"))
    role, st = ensure(nb.plugins.inventory.asset_roles, {"slug": S.ASSET_ROLE["slug"]}, **S.ASSET_ROLE)
    for a in S.SPARE_ASSETS:
        dt = nb.dcim.device_types.get(slug=a["type"])
        obj, st = ensure(nb.plugins.inventory.assets, {"serial": a["serial"]}, name=a["name"], serial=a["serial"],
                         status="stored", role=role.id, device_type=dt.id, tenant=tenant.id, storage_location=location.id)
        report("asset", obj, st)


def run(nb):
    addressing(nb)
    bgp(nb)
    secrets(nb)
    inventory(nb)


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nLayer 6 (services) complete.")
