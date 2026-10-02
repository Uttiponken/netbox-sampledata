#!/usr/bin/env python3
"""
Phase 7: BGP, Secrets, Inventory. The last of the originally planned phases.

Three independent, unrelated plugins covered in one script since each is
small on its own:

  BGP:       loopback interfaces + IPs on the 4 core routers, one private
             ASN for Nordfiber, a full iBGP mesh peer-group and 6 sessions.
  Secrets:   an RSA keypair (generated once, reused thereafter — see
             common.get_secrets_session_key), a secret role, and one
             "local admin" credential secret per core router.
  Inventory: a small cold-spares depot at the Stockholm hub — one spare of
             each major chassis type in use.

Depends on Phase 1 (tenants) and Phase 2 (the 4 core routers and their
interfaces). Safe to re-run.
"""

from common import (
    call_plugin_action,
    connect,
    get_or_create,
    get_secrets_session_key,
    report,
)
from config import (
    ASSET_ROLES,
    BGP_ASN,
    BGP_PEER_GROUP,
    BGP_SESSIONS,
    DEVICE_SECRETS,
    LOOPBACKS,
    RIR_PRIVATE_USE,
    SECRET_ROLE,
    SPARE_ASSETS,
)


def run_bgp(nb, devices, tenants):
    print("== BGP: RIR (private-use, for our internal ASN) ==")
    rir, created = get_or_create(nb.ipam.rirs, {"slug": RIR_PRIVATE_USE["slug"]}, **RIR_PRIVATE_USE)
    report("rir", rir, created)

    print("== BGP: ASN ==")
    asn, created = get_or_create(
        nb.ipam.asns,
        {"asn": BGP_ASN["asn"]},
        asn=BGP_ASN["asn"],
        rir=rir.id,
        description=BGP_ASN["description"],
        tenant=tenants[BGP_ASN["tenant_slug"]].id,
    )
    report("asn", asn, created)

    print("== BGP: loopback interfaces + IPs ==")
    loopback_ips = {}
    for lb in LOOPBACKS:
        device = devices[lb["device"]]
        iface, created = get_or_create(
            nb.dcim.interfaces,
            {"device_id": device.id, "name": "lo0"},
            device=device.id,
            name="lo0",
            type="virtual",
        )
        report("loopback interface", iface, created)

        ip, created = get_or_create(
            nb.ipam.ip_addresses,
            {"address": lb["ip"]},
            address=lb["ip"],
            status="active",
            assigned_object_type="dcim.interface",
            assigned_object_id=iface.id,
        )
        report("loopback IP", ip, created)
        loopback_ips[lb["device"]] = ip

    print("== BGP: peer group ==")
    peer_group, created = get_or_create(
        nb.plugins.bgp.peer_group,
        {"name": BGP_PEER_GROUP["name"]},
        name=BGP_PEER_GROUP["name"],
        description=BGP_PEER_GROUP["description"],
        local_as=asn.id,
        remote_as=asn.id,
    )
    report("bgp peer group", peer_group, created)

    print("== BGP: iBGP mesh sessions ==")
    for s in BGP_SESSIONS:
        device = devices[s["device"]]
        local_ip = loopback_ips[s["device"]]
        # remote_ip belongs to whichever device owns that loopback address
        remote_device_name = next(lb["device"] for lb in LOOPBACKS if lb["ip"] == s["remote_ip"])
        remote_ip = loopback_ips[remote_device_name]

        existing = nb.plugins.bgp.session.get(name=s["name"])
        if existing:
            report("bgp session", existing, False)
            continue
        obj = nb.plugins.bgp.session.create(
            name=s["name"],
            device=device.id,
            local_address=local_ip.id,
            remote_address=remote_ip.id,
            local_as=asn.id,
            remote_as=asn.id,
            peer_group=peer_group.id,
            status="active",
        )
        report("bgp session", obj, True)


def run_secrets(nb, devices):
    print("== Secrets: RSA keypair + session key ==")
    session_key = get_secrets_session_key(nb)

    print("== Secrets: role ==")
    role, created = get_or_create(nb.plugins.secrets.secret_roles, {"slug": SECRET_ROLE["slug"]}, **SECRET_ROLE)
    report("secret role", role, created)

    print("== Secrets: device credentials ==")
    for s in DEVICE_SECRETS:
        device = devices[s["device"]]
        existing = nb.plugins.secrets.secrets.get(
            assigned_object_type="dcim.device", assigned_object_id=device.id, name=s["name"]
        )
        if existing:
            report("secret", existing, False)
            continue
        result = call_plugin_action(
            "/api/plugins/secrets/secrets/",
            method="post",
            json={
                "assigned_object_type": "dcim.device",
                "assigned_object_id": device.id,
                "role": role.id,
                "name": s["name"],
                "plaintext": s["plaintext"],
            },
            extra_headers={"X-Session-Key": session_key},
        )
        print(f"  [created] secret: {s['device']}/{s['name']} (id={result['id']}) — value encrypted, not re-printed")


def run_inventory(nb, tenants, locations):
    print("== Inventory: asset roles ==")
    asset_roles = {}
    for r in ASSET_ROLES:
        obj, created = get_or_create(nb.plugins.inventory.asset_roles, {"slug": r["slug"]}, **r)
        report("asset role", obj, created)
        asset_roles[r["slug"]] = obj

    device_types = {dt.slug: dt for dt in nb.dcim.device_types.all()}

    print("== Inventory: spare assets ==")
    for a in SPARE_ASSETS:
        obj, created = get_or_create(
            nb.plugins.inventory.assets,
            {"serial": a["serial"]},
            name=a["name"],
            serial=a["serial"],
            status="stored",
            role=asset_roles["spare-chassis"].id,
            device_type=device_types[a["device_type_slug"]].id,
            tenant=tenants["nordfiber-ab"].id,
            storage_location=locations["stockholm-suite-100-row-a"].id,
        )
        report("asset", obj, created)


def run(nb):
    devices = {d.name: d for d in nb.dcim.devices.all()}
    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    locations = {loc.slug: loc for loc in nb.dcim.locations.all()}

    run_bgp(nb, devices, tenants)
    run_secrets(nb, devices)
    run_inventory(nb, tenants, locations)


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 7 (BGP, Secrets, Inventory) complete.")
