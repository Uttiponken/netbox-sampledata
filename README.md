# Nordfiber AB — NetBox demo dataset

An educational dataset for a fresh NetBox install: a fictional regional
fiber-optic network operator, **Nordfiber AB**, with two datacenters
(Stockholm, its HQ, and Gothenburg — upgraded from a PoP in Phase 16), a
third, smaller datacenter in Helsinki (Finland, Phase 17), and points of
presence in Malmö and Oslo (Norway — one cross-border site on purpose).
Three fictional customers colocate or lease services at different subsets
of these sites. The dataset is built in phases that mirror NetBox's own
object dependency order, so each phase is a complete, demoable stage on
its own — start with Phase 1 and grow from there.

**Standalone project.** This talks to NetBox purely over its REST API, so
it isn't coupled to any particular NetBox deployment or repo — point
`NETBOX_URL`/`NETBOX_TOKEN` (in `.env`) at any reachable NetBox instance.
It was developed and is regularly tested against a `netbox-docker`
deployment running locally, but that's just the test target, not a
dependency. See `docs/DESIGN.md` for the full rationale behind every
decision here (why the API and not the database, the token-format gotcha,
verification methodology, and a per-phase build log) — this README is just
the quick start. For what the finished topology actually looks like —
which sites connect to which over what technology — see
`docs/INFRASTRUCTURE.md`.

## Why the REST API, not the database

Every phase script talks to NetBox exclusively through its REST API (via
[pynetbox](https://github.com/netbox-community/pynetbox), the official SDK).
Loading data by writing directly to the Postgres database was considered and
rejected: it bypasses NetBox's validation, cable-path tracing, computed
fields, and changelog — you'd get rows that look right in `psql` but behave
wrong (or not at all) in the UI. The API path is slower to write but is
exactly what a real integration would do, which is also the point of a
*teaching* dataset. See `docs/DESIGN.md` for the two alternatives that were
considered and rejected, and why.

## Phases

All 7 originally planned phases are complete as of 2026-09-27, plus 15
more user-requested phases built since (a DWDM backup path with
electrical regeneration, a NOC engineer's physical workplace plus a
standalone Internet circuit, a WDM client demarc shelf, a colo
cross-connect re-architecture through a MeetMe room, a follow-up
correction giving that room proper third-party ownership at every PoP,
the same MeetMe demarc pattern applied to Nordfiber's own upstream
Internet provider, every WDM node's full 40-channel capacity, a 10x
capacity upgrade for Baltic Retail Group, Gothenburg's promotion to a
full Datacenter, a third datacenter in Helsinki reached over two
geographically-diverse leased dark fiber pairs with real PostGIS route
data, the same real route geography for the original domestic backbone
fiber, and that Helsinki link fully lit end to end through its own new
MeetMe room, a uniform rack layout with cabled out-of-band management, asset identity, and a prune of spurious wavelength paths) — the dataset is a fully functional, end-to-end
demonstration from organizational structure down to a genuinely lit, stitched wavelength
service and encrypted device credentials. See `docs/DESIGN.md` for the
full build log, every real bug hit along the way, and how each was
diagnosed. It's still built to grow further — nothing about the phased,
config-driven design stops here (see "Possible future extensions" below).

Every cable also carries a `tenant` (added after review — see the
2026-09-27 addendum in `docs/DESIGN.md`): Nordfiber-to-Nordfiber links are
tenanted to Nordfiber AB even where a customer's service rides over them,
while a cross-connect landing on a customer's own colocated device is
tenanted to that customer.

| Script | Layer | Depends on |
|---|---|---|
| `01_organization.py` | Tenant groups, tenants, regions, site groups, sites, locations, contact groups/roles, contacts, contact assignments | — |
| `02_infrastructure.py` | Manufacturers, real device types (fetched from the NetBox devicetype-library), device roles, racks, devices, mgmt IPAM role/prefixes/IPs — customer tenants assigned per-rack here, making Stockholm and Gothenburg multi-tenant and Malmö/Oslo single-tenant | Phase 1 |
| `03_connections.py` | Cables: router↔switch uplink per site, colo server↔switch cross-connects (wireless links deliberately deferred — no radio equipment in the scenario yet) | Phase 2 |
| `04_circuits.py` | Providers, circuit types, 2 circuits + terminations: Nordfiber→Baltic Retail EPL (Stockholm↔Malmö, cabled to routers) and Nordfiber's leased dark fiber from Polarlink Transit (Stockholm↔Oslo, left unterminated to any device — lit in Phase 6) | Phase 3 |
| `05_fms.py` | LC patch panel at each site (real device type), FMS cable type (Corning ALTOS, DIN/IEC colors), 3 backbone fiber cables with auto-instantiated buffer tubes/strands: Stockholm↔Gothenburg + Stockholm↔Malmö (Nordfiber-owned) and Stockholm↔Oslo (the physical realization of the leased dark fiber circuit from Phase 4) | Phase 3, netbox-fms plugin |
| `06_wdm.py` | Real SmartOptics muxponder at each end of the Oslo link, ITU channel plan, client-facing cross-connect to each site's switch, and a stitched, verified-complete end-to-end wavelength path for Fjord Media Networks' service | Phase 5, netbox-wdm plugin |
| `07_bgp_secrets_inventory.py` | Loopback IPs + full iBGP mesh on Nordfiber's private ASN, genuinely encrypted per-router credentials (round-trip verified), a small cold-spares inventory | Phase 2, netbox-bgp/netbox-secrets/netbox-inventory plugins |
| `08_baltic_retail_backup.py` | A DWDM-based backup/protect path for `NF-BRG-0001`, Stockholm↔Gothenburg↔Malmö, with electrical regeneration at Gothenburg (2 new muxponders, back to back) since the WDM hardware is a terminal mux, not a ROADM | Phase 4, Phase 5, Phase 6, netbox-wdm |
| `09_gothenburg_office.py` | Erik Lindqvist's physical workplace at the Gothenburg PoP (desk, TP outlet, IDF switch, fiber uplink) + a standalone Internet Access circuit for Nordfiber's own upstream transit | Phase 1, Phase 2 |
| `10_dwdm_client_shelf.py` | A SmartOptics DCP-2 + DCP-110 client demarc shelf at every site with WDM equipment, retrofitting Fjord Media's and Baltic Retail's tenant handoffs onto grey 10G ports instead of the muxponder's own colored channel port | Phase 6, Phase 8 |
| `11_colo_crossconnects.py` | Re-architects colo tenant connectivity: each tenant gets its own switch + ToR fiber panel + a dedicated demarc panel in a MeetMe room (a third-party carrier-neutral facility, not Nordfiber's own), cross-connected via Nordfiber's existing patch panels instead of a direct server-to-Nordfiber-switch cable | Phase 2, Phase 5, Phase 9 |
| `12_meetme_ownership.py` | Corrects MeetMe room ownership (Stockholm is Nordfiber's own; Malmo's is a second, different facility operator) and gives Nordfiber its own demarc panel in every MeetMe room, inserted into each tenant cross-connect chain; adds contacts for both facility operators at the site, rack, and device level | Phase 11 |
| `13_vastkust_meetme.py` | Applies the same MeetMe demarc pattern to Nordfiber's own upstream Internet provider (Vastkust Bredband AB): its own panel in the Gothenburg MeetMe room, cross-connected through Nordfiber's existing panels instead of cabling straight to the router | Phase 9, Phase 12 |
| `14_wdm_full_channel_plan.py` | Populates all 40 real channels on every WDM terminal mux (only 2 were lit before), each with the plugin's own computed ITU wavelength/label | Phase 6, Phase 8 |
| `15_baltic_retail_10g.py` | Upgrades Baltic Retail Group's leased line (primary + backup) from 1 Gbps to 10 Gbps commit rate | Phase 4, Phase 8 |
| `16_gothenburg_dc_upgrade.py` | Reclassifies Gothenburg as a full Datacenter (name + SiteGroup) and adds new growth capacity (a Suite/Row with 2 empty racks) | Phase 1 |
| `17_helsinki_dc.py` | A third, smaller datacenter in Helsinki, reached from Stockholm over two independently-routed leased dark fiber pairs from two different vendors, with real route geography via netbox-pathways | Phase 1, Phase 2, Phase 4, Phase 5, netbox-pathways |
| `18_backbone_pathways.py` | Real PostGIS route geography (DirectBuried pathway + CableSegment) for the 3 original domestic backbone cables, following the actual roads/towns each one runs along | Phase 5, netbox-pathways |
| `19_helsinki_dwdm_lighting.py` | Adds Helsinki's missing MeetMe room and lights both leased dark fiber pairs end to end (new WDM muxponders at both ends, demarc panels for both vendors at both ends, direct router handoff) | Phase 6, Phase 11, Phase 12, Phase 13, Phase 17 |
| `20_rack_layout_and_oob.py` | Re-seats every rack to one uniform layout (2U gaps between kinds of gear) and adds a per-site OOB switch with every device's management port cabled to it | All device phases |
| `21_asset_identity.py` | Serials on every device; asset tags on Nordfiber-owned devices | All device phases |
| `22_prune_wdm_paths.py` | Deletes spurious wavelength paths created by netbox-wdm's duplicate-path bug (must run last) | Phase 6, Phase 8, Phase 19 |

Each script is safe to re-run: everything is looked up by slug (or name,
for contacts) before being created, so running `01_organization.py` twice
reports 39 "exists" and creates nothing new. Run phases in order — later
scripts assume earlier ones already ran.

## Setup

```bash
cd demo-data
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Create an API token for these scripts (a dedicated service account is
better practice than reusing your own login):

```bash
cd ..   # netbox-docker/
docker compose exec -T netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py shell -c "
from django.contrib.auth import get_user_model
from users.models import Token
U = get_user_model()
u, _ = U.objects.get_or_create(username='demo-loader', defaults={'is_superuser': True, 'is_active': True})
Token.objects.filter(user=u).delete()
t = Token(user=u, description='demo-data loader scripts')
t.save()
print('nbt_' + t.key + '.' + t.token)
"
```

**Important — NetBox 4.5+ token format:** paste the full printed value
(`nbt_<key>.<secret>`) into `.env` as `NETBOX_TOKEN`. NetBox now stores API
tokens as a salted HMAC digest (a "v2" token) rather than plaintext — the
plaintext `.token` value only exists in memory at creation time and is
**never** retrievable again afterward (querying an existing `Token` object's
`.token` field later returns `None` — don't try to fetch it after the fact,
generate a new one instead). This is a genuine, fairly new NetBox security
feature, not a bug — worth knowing about since NetBox's own REST API docs
still show both v1 (`Authorization: Token <plaintext>`, deprecated, removed
in NetBox v5.0) and v2 (`Authorization: Bearer <key>.<secret>`) forms.
pynetbox doesn't need a separate "v2 mode" flag — NetBox infers the version
from whether the credential itself starts with the `nbt_` prefix, regardless
of which header keyword (`Token` or `Bearer`) is sent, so passing the full
`nbt_<key>.<secret>` string as pynetbox's `token=` argument works correctly.

Edit `.env`:

```
NETBOX_URL=http://localhost:8000
NETBOX_TOKEN=nbt_<key>.<secret>
```

## Running

```bash
./.venv/bin/python 01_organization.py
```

Run phases in order — `02` through `22` each depend on earlier ones having
already run.

## A second secret file, starting at Phase 7

`07_bgp_secrets_inventory.py` generates an RSA keypair to write real
encrypted secrets via netbox-secrets, and saves the private key to
`.secrets_userkey.pem` (gitignored, alongside `.env`) because — like the
Phase 1 API token — it only ever exists in full once, at generation time;
there's no "fetch it again later." Losing this file after Phase 7 has run
doesn't break anything else in the dataset, but it does mean the secrets
already stored become permanently undecryptable (real netbox-secrets
behavior, not a quirk of this script) — back it up if that data matters to
you, same as you would for `.env`.

## Resetting

There's no delete script (deleting in the right reverse-dependency order is
its own small project). For now, the fastest reset is to wipe the target
NetBox database and re-migrate — this also naturally invalidates
`.secrets_userkey.pem`, so delete that file too when you do a full reset,
otherwise a future Phase 7 run will find no matching UserKey in the fresh
database and correctly refuse to guess. If your target is a `netbox-docker`
deployment, its own `docs/OPERATIONS.md` §5.5 covers the restore procedure,
or you can just tear down and rebuild that stack per its §3 if you don't
need to keep anything else in it. This full purge-and-reload path is
tested end to end (see the 2026-09-27 addendum in `docs/DESIGN.md`).

**One real constraint worth knowing**: run `01` through `13` in order from
a clean/empty database. Phases 10, 11, 12, and 13 retrofit cables that
earlier phases (3, 6, 8, 9) originally created — re-running one of those
earlier scripts in isolation, after its retrofit has already happened,
isn't supported. It fails loudly and safely with a clear error (fixed
2026-09-27 — it used to silently mislabel the wrong cable first) rather
than corrupting anything, but it won't succeed. If you need to redo an
earlier phase's data, reset the whole database and replay the full
sequence instead.

## Scenario reference

See `config.py` for the full data — it's the single source of truth each
script reads from, so extending the dataset (add a fifth site, add a fourth
customer) means editing `config.py`, not the scripts themselves. Tenants:

- **Nordfiber AB** (Internal) — owns all sites and core infrastructure.
- **Baltic Retail Group** (Customers) — leases WAN between Stockholm ⟷ Malmö.
- **Polaris Cloud Services** (Customers) — colocates at Stockholm DC + Gothenburg.
- **Västhamnen Logistics** (Customers) — colocates edge-compute at Gothenburg for Port of Gothenburg container-tracking telemetry.
- **Fjord Media Networks** (Customers) — leases a wavelength service, Oslo ⟷ Stockholm.
- **Skagerrak Interconnect AB** (Facility Operators) — fictional carrier-neutral operator of the MeetMe/cross-connect rooms at Gothenburg and Oslo; Nordfiber and its colo tenants are all customers of this facility, not owners of it.
- **Oresund Exchange AB** (Facility Operators) — a second, different fictional facility operator, at Malmö only (Phase 12) — not every PoP shares the same landlord.
- **Vastkust Bredband AB** (Suppliers) — Nordfiber's own upstream Internet transit provider (a `circuits.Provider` since Phase 9); also modeled as a Tenant since Phase 13, so its own MeetMe-room panel at Gothenburg can be owned by it.

Two more `circuits.Provider`-only entities (no matching Tenant — they own no equipment in this dataset), added in Phase 17: **Nordic Subsea Networks AB** and **Baltic Fibre Networks OU**, the two different vendors leasing Nordfiber's dark fiber to Helsinki.

Gothenburg (now a Datacenter, not a PoP, since Phase 16) is a three-tenant site (Nordfiber's own core rack plus
two separate customer colo racks — Polaris and Västhamnen), the richest
multi-tenancy example in the dataset. Since Phase 11/12, those two colo
tenants no longer cable straight into Nordfiber's switch — each has its
own switch and patch panel, cross-connected via a MeetMe room panel that
belongs to the local facility operator, then jumpered to Nordfiber's own
MeetMe-room panel. MeetMe room ownership follows a DC-vs-PoP split:
Stockholm's is Nordfiber's own (it's their datacenter), Gothenburg's and
Oslo's belong to Skagerrak, and Malmö's belongs to Oresund Exchange.

## Possible future extensions

Not planned or scheduled — just the honest list of things that came up
during the original 7 phases and were deliberately deferred rather than
built, each with a reason:

- **Wireless links** (originally in the Phase 3 plan) — no radio equipment
  exists in the scenario to justify them. Would need a real reason (e.g. a
  microwave backhaul backup between two nearby PoPs) before adding fictional
  gear just to fill the gap.
- **Baltic Retail Group's own CPE router** — their EPL circuit currently
  terminates straight into Nordfiber's own router interface; a fully
  accurate model would give the customer their own edge device on each end.
- **A second WDM customer at Oslo** — every muxponder now has all 40
  channels populated (Phase 14), but Oslo's still only has 1 actually
  cabled/lit. Adding a second customer's wavelength there would exercise
  more of the netbox-wdm data model (a second `WdmCircuit`, channel reuse
  checks) without new infrastructure.
- **DCP-110 client shelf for the Helsinki wavelengths** — Phase 19's two
  new lit channels hand off straight to a router port; routing them
  through the Phase 10 DCP-2/DCP-110 shelf instead would be more
  consistent with the other customer-facing wavelengths, if these links
  are ever meant to also serve external customers rather than staying
  Nordfiber's own internal backbone capacity. Not confirmed either way.
- **netbox-topology-views** — a generic L1 diagram plugin; skipped because
  no release currently targets NetBox 4.6.x specifically (see the same
  §10 discussion).
- **A `00_reset.py` script** — deleting everything in correct
  reverse-dependency order, so this whole dataset can be torn down and
  rebuilt without wiping the entire NetBox database.
