#!/usr/bin/env python3
"""
Phase 4: Circuits.

Creates, in NetBox's own dependency order:
  providers -> circuit types -> circuits -> circuit terminations
  -> (where applicable) a cable from the termination to a device interface

Two circuits (see config.py's Phase 4 comment block for the full story):
  - NF-BRG-0001: Nordfiber AB sells an EPL to Baltic Retail Group,
    Stockholm <-> Malmo. Both terminations are cabled to a router port.
  - PLT-100234: Nordfiber AB leases dark fiber from Polarlink Transit,
    Stockholm <-> Oslo. Terminations exist at the Site level only — no
    device interface yet, since dark fiber has no active gear on it until
    Phase 6 lights it.

Depends on Phase 1 (tenants/sites) and Phase 2 (devices/interfaces) for the
EPL circuit's cabled terminations. Safe to re-run.
"""

from common import connect, create_cable_if_needed, get_interface, get_or_create, report
from config import CIRCUIT_TYPES, CIRCUITS, PROVIDERS


def run(nb):
    print("== Providers ==")
    providers = {}
    for p in PROVIDERS:
        obj, created = get_or_create(nb.circuits.providers, {"slug": p["slug"]}, **p)
        report("provider", obj, created)
        providers[p["slug"]] = obj

    print("== Circuit types ==")
    circuit_types = {}
    for ct in CIRCUIT_TYPES:
        obj, created = get_or_create(nb.circuits.circuit_types, {"slug": ct["slug"]}, **ct)
        report("circuit type", obj, created)
        circuit_types[ct["slug"]] = obj

    sites = {s.slug: s for s in nb.dcim.sites.all()}
    tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
    devices = {d.name: d for d in nb.dcim.devices.all()}

    print("== Circuits ==")
    for c in CIRCUITS:
        circuit, created = get_or_create(
            nb.circuits.circuits,
            {"cid": c["cid"]},
            cid=c["cid"],
            provider=providers[c["provider_slug"]].id,
            type=circuit_types[c["type_slug"]].id,
            tenant=tenants[c["tenant_slug"]].id,
            status=c["status"],
            commit_rate=c["commit_rate"],
            description=c["description"],
        )
        report("circuit", circuit, created)

        print(f"   == Terminations for {c['cid']} ==")
        for t in c["terminations"]:
            site = sites[t["site_slug"]]
            term = nb.circuits.circuit_terminations.get(circuit_id=circuit.id, term_side=t["term_side"])
            if term is None:
                term = nb.circuits.circuit_terminations.create(
                    circuit=circuit.id,
                    term_side=t["term_side"],
                    termination_type="dcim.site",
                    termination_id=site.id,
                    port_speed=c["commit_rate"],
                )
                print(f"     [created] termination {t['term_side']}: {site.name} (id={term.id})")
            else:
                print(f"     [exists ] termination {t['term_side']}: {site.name} (id={term.id})")

            if t["device"] is None:
                continue  # dark fiber: no device interface to cable to yet

            iface = get_interface(nb, devices[t["device"]], t["iface"])
            create_cable_if_needed(
                nb,
                term, "circuits.circuittermination",
                iface, "dcim.interface",
                status="connected",
                label=t["cable_label"],
                comments=f"{c['cid']} ({t['term_side']}-side) demarc",
                # This is Nordfiber's own demarc-extension cable on their own
                # router; the customer relationship for what rides over it
                # is already captured on the Circuit object's own tenant.
                tenant=tenants["nordfiber-ab"].id,
            )


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 4 (Circuits) complete.")
