# Design notes and build log

This document records *why* the dataset and loader are built the way they
are, and a phase-by-phase log of what's been built and verified so far.
`README.md` is the quick-start; this is the rationale, kept up to date as
the project grows.

## Status

Standalone project as of 2026-09-26. Originally built inside
`netbox-docker/demo-data/` (the NetBox deployment this was first tested
against), then deliberately moved out to its own directory and its own git
repository, `netbox-sampledata`, so the dataset isn't coupled to any one
NetBox deployment — it's a client of the REST API of *any* reachable NetBox
instance, pointed at via `NETBOX_URL`/`NETBOX_TOKEN` in `.env`.

## The layered rewrite (2026-10-02)

The dataset was first built as 22 numbered "phase" scripts, each added when
a requirement appeared; later phases retrofitted earlier ones (deleting and
re-creating cables, moving devices), so the scripts could only be replayed
in order and no script described a final state. After an audit the build was
rewritten as seven layers that each describe the **final state directly**,
driven by plain-Python data modules, and replayed on an empty NetBox:

- `01_organization` · `02_hardware` · `03_cabling` · `04_transport` ·
  `05_optical` · `06_services` · `07_finalize`, plus `verify.py` and
  `build.py`. Data lives in `data/`, the naming convention in `naming.py`,
  site/rack/device generation in `layout.py`, cable rules in `cabling.py`.
- Sites are profiles (`dc` = redundant pair, `pop` = single pair with
  slots reserved) so every site of a kind is generated, not hand-written.
- The audit's findings were built in: uniform rack slots; every
  management port cabled to an OOB switch; cable type/colour/length/label
  and per-end labels (`label_a`/`label_b` custom fields) set at creation
  under the rules in `docs/INFRASTRUCTURE.md` §8; one naming scheme;
  redundant router/switch pairs at the datacenters; Helsinki brought to
  parity with the other sites (management addressing, loopback and iBGP,
  credential, contacts, DCP-2 shelf); a real west-coast route for
  `bb-cbl-00004` and routes plus fiber-plant records for the two leased
  Helsinki spans; geography for every long-haul cable.
- **Verification.** Before the rewrite the live state was dumped to
  `reference/state-before-refactor.json` (`tools/dump_state.py`). After the
  replay `tools/diff_state.py` (which applies the intended renames and
  ignores the redefined cable attributes) showed 97 of 106 cables
  identical and every remaining difference accounted for: renames, uniform
  slots, the new redundant equipment and its cabling, tenant rule changes
  on vendor jumpers, Helsinki parity, descriptions cleaned of "Phase N" and
  stale text, diacritics restored in names (Västkust, Öresund, Baltic Fibre
  Networks OÜ). Serials and asset tags are renumbered by the new creation
  order (deterministic, but not the old numbers).
- **Old scripts.** The 22 numbered scripts and `config.py` are removed; the
  state they produced is preserved in `reference/` and in git (commit
  `8f65e89`) and `archive/legacy-numbered-phases-2026-10-02.tar.gz`.

The phase log below is kept as the **history** of how the dataset and its
workarounds came about — the scripts it names no longer exist, and its
"Phase N" numbering is not used anywhere in the dataset itself. The
upstream-plugin findings it records (WDM channel plan before devices,
placeholder wavelengths, the duplicate-path bug, the `/trace/` limitation,
the front-port mapping fields, the secrets session key) are all still true
and are handled in the new layers.

## After the rewrite (2026-10-03)

Three changes made once the dataset was used to test the print plugin (`netbox-tracepath-plugin`). Each was rebuilt
from an empty NetBox and verified.

### 24-pair trunks (v0.3.0)

Requirement: every panel-to-panel rear connection is a 24-pair fiber trunk, not 24 discrete cables.

- A trunk is **one cable between two rear ports**, 24 pairs = 48 fibers, LC connectors. The panel is a custom
  device type (`TRUNK_PANEL` in `data/hardware.py`, the community library has none): 1U, 24 duplex LC front
  ports, ONE rear port `Trunk` with 24 positions, front port *n* mapped to position *n*.
- One panel per trunk (kept deliberately). Each core rack holds a panel for the MeetMe trunk and one per
  backbone trunk, at the same height at every site; the slot of the site itself stays free.
- Consequence: one cable carries many paths (pair x direction), so anything that traces a trunk has to ask
  which pair. The print plugin does.
- The facility owners' placeholder panels have no trunk; `verify.py` allows only those.

### Trunk colours (v0.4.0)

Rule in `cabling.py`: a 24-pair trunk is green inside a site and blue between sites, decided from the sites of
its two panels. Other fiber stays yellow, copper grey, DAC black. It is the plain NetBox cable colour; nothing
here is specific to the print plugin, which just draws the colour NetBox stores.

### Strands and fiber circuits (v0.5.0)

- **Strand landing.** netbox-fms stores `front_port_a` / `front_port_b` on every `FiberStrand`. A trunk
  panel's duplex LC port is one pair, so strands 2n-1 and 2n are landed on port n at both ends (FMS allows two
  strands on one port). Done with a bulk update in `04_transport.py`.
- **Circuits.** One `FiberCircuit` per trunk pair actually in use (`NF-FC-0001` to `-0005`, `FIBER_CIRCUITS` in
  `data/transport.py`), `strand_count=2` with two circuit paths that start at the same duplex port, because FMS
  models one strand per front port and a duplex port is two. Origin and destination are the line panel ports of
  the two muxponders (`LINE_PATCH`). FMS follows rear-port cables whether or not they have an FMS record and
  treats a front-to-front cable as a splice, so the two Helsinki circuits run through both MeetMe rooms and the
  leased trunk.
- **API quirks.** A circuit path cannot be created with an empty `path`, so it is seeded with its origin front
  port and the circuit's `retrace` action fills it in; the API returns origin and destination as plain ids.
- **netbox-fms 0.6 (NetBox 4.7).** Paths are no longer stored on the circuit: FMS derives a `FiberStrandPath` for
  every pair of front ports its strands connect (a background job after the strands are landed, so
  `04_transport.py` waits for it), and a circuit is assigned one of them with `POST fiber-circuits/<id>/assign/`.
  The assignment carries the wavelength and loss. A circuit therefore has ONE assigned path, the pair's two
  strands travel together, and `retrace` and the `FiberCircuitNode` are gone; the code keeps the older way for
  netbox-fms below 0.6 (`version_at_least("fms", 0, 6)` in `common.py`). `verify.py` checks the same facts
  either way: the circuit's ends, that the path is complete, and that it is the pair the plan names.
- **Loss and wavelength.** 1550 nm, and the loss of the bare fiber end to end (0.21 dB/km plus 1.5 dB of
  connectors), which comes to 55 to 192 dB. It is not a link budget; amplifiers are not modelled. The constants
  are in `data/transport.py`.
- **No circuit on `bb-cbl-00002`.** Stockholm-Malmö has no cabled path through it (`NF-BRG-0001` is cabled
  router to router), so no pair is in use.

## Stockholm as three availability zones (2026-10-24)

Requirement: split the Stockholm datacenter into three zones, AWS-style, tie them together with fiber in
municipal ducts, and move the long-haul terminations so each zone lands its own routes. Rebuilt from an empty
NetBox and verified (70 checks).

- **Sites.** `stn` (Sollentuna, North, HQ), `stw` (Södertälje, West), `ste` (Nacka, East), all full datacenters
  (router/switch pair, OOB, MeetMe room, DCP-2 shelf), in the region Greater Stockholm. The `city` of a site is the
  slug stem, so the three read `nordfiber-stockholm-north-dc` etc. and the room slugs follow. Management prefixes
  keep the five old sites' addresses and give West and East `10.0.6.0/24` and `10.0.7.0/24`.
- **Landing.** Gothenburg north, Oslo and NSN land in North; Malmö and a **new southern trunk to Gothenburg**
  (`bb-cbl-00007`) land in West; BFN lands in East. A tenant-owned Baltic Retail is in all three zones because its
  primary circuit now starts in West and its protect path in North.
- **Ring cables are a second trunk type.** 288 fibers = 24 tubes of 12 = 144 pairs (the largest ALTOS loose-tube
  count), on a 3U panel with 144 duplex LC ports behind one 144-position rear port (`TRUNK_PANEL_144`). The
  panel slots in the core rack were re-planned (`CORE_SLOTS`): one 1U slot per long-haul peer and three 3U slots
  for the zones, which moved everything below up by 8U at every site, so equipment still lines up between sites.
  The OOB port plan changed for the same reason (up to six WDM nodes, DCP-2 on 9, others from 10, second router
  and switch on 15/16).
- **Tubes carry their use.** FMS has no per-fiber status, so the tube *name* is the plan: `Tube 1 - WDM` ... `Tube 13
  - Nordfiber dark` ... `Tube 17 - leasable dark`. Reserved WDM pairs are only this label; the lit pair and the
  leased pair are fiber circuits (`NF-FC-0007` to `-0010`). A leased dark pair has bare panel ports at both ends,
  so NetBox has no cable path there and the print plugin says "nothing to print"; that is a plugin limit, not
  a data error.
- **Three parties per duct, kept apart.** The conduit belongs to the municipality (`Pathway.tenant`), the innerduct
  to the cable's owner, the cable to Nordfiber or to Stockholm Metro Fibre AB (the leased West - East cable, with
  a dark-fiber circuit `SMF-DF-0001` like the Helsinki vendor spans), the lessee is Nordfiber. The innerduct
  endpoint of netbox-pathways has no tenant field, so its owner is set through the base `pathways` endpoint.
- **Water crossings are `submarine` pathways** (the base `Pathway`, which accepts the type through the REST API;
  there is no dedicated model). Lengths are not computed by the plugin, `plant.py` sets them. The pathways map does
  not draw them.
- **Dispersion is a verified property.** Two entrances per zone, one per ring cable; `verify.py` fails if a duct or
  a structure outside the buildings is used by two cables. Shared *owners* are allowed and noted.
- **The geometry is derived, not typed** (`tools/derive_metro.py` -> `data/metro_geometry.py`, generated, ODbL):
  1. each land section is routed on the road network (OSRM), which is how the West - East link ends up on the
     E4/E20, road 75 and road 222; waypoints that pull the route off the motorway were tried and removed;
  2. the route is sampled every 700 m and each sample is placed in its municipality (Overpass `is_in`), which gives
     the real borders; runs longer than 4.5 km are split again; the first and last leg at a datacenter are the
     duct-bank lead-ins;
  3. a water crossing exists only where the road distance between two shore chambers is several times the straight
     line (6 to 9 times here), and the straight line between them is checked against OpenStreetMap's water areas;
  4. a station that landed on a road bridge is moved along the route to dry land.
  The first hand-typed guess had four structures in water and three ducts crossing lakes, which is why this is
  done with data. Python 3.9 from the Command Line Tools cannot make the TLS connection to Overpass, so the
  helper calls `curl`.
- **Ownership is invented.** The municipalities are real, which of them owns which duct is not; the descriptions
  say so.
- **Idempotent, proved.** A second `build.py` over the finished dataset changes nothing. Two small fixes were
  needed on the way: a moved structure is now reconciled (its location is compared apart, the API returns
  GeoJSON), and the innerduct owner is set through the base endpoint.
- **Reset script gotcha.** `tools/reset_netbox.sh` recreates only `demo-loader`: a personal superuser (for example
  `admin`) is gone after a reset and must be created again with `createsuperuser`.

## Plugins are optional (2026-10-24)

Requirement: the dataset must load into a vanilla NetBox with no plugins, and use whichever of the six plugins it
knows (pathways, fms, wdm, bgp, secrets, inventory) are installed. Until then the first plugin call (layer 2 creates
the WDM profile) stopped a build on a NetBox without netbox-wdm. The print plugin must stay independent of the dataset.

- **Detection** (`common.detect_plugins`). `/api/status/` lists the installed plugins; a plugin counts as usable
  only if its REST root (`/api/plugins/<name>/`) also answers, so an installed plugin with a changed or broken API is
  skipped with a reason instead of failing the build. `NETBOX_SKIP_PLUGINS=wdm,pathways` switches plugins off on purpose;
  an unknown name stops the run (a typo must not look like success). `have(name)` asks, `skip(name, what)` prints
  `[skipped] what: netbox-x is not installed`.
- **What stays core.** Organization, hardware, all cabling, providers and circuits, the long-haul and ring cables
  themselves (length, tenant, notes), circuit demarcs, prefixes, addresses, the ASN and the loopbacks. These are the
  same objects with or without plugins, so `verify.py`'s 39 core checks (including the physical traces walked by
  NetBox itself, through the muxponders and the MeetMe jumpers) run on a vanilla NetBox.
- **What a plugin adds.** pathways: structures, ducts, crossings, cable segments, circuit geometries. fms: cable
  records, tubes, strands landed on ports, fiber circuits. wdm: profile and channel plan, nodes, line ports, the
  wavelength services, channel status, path pruning. bgp: peer group and sessions. secrets, inventory: one step each.
- **Mixed steps were split, not duplicated.** `04_transport.py` created a core cable and its FMS record and pathway in
  one loop; the loop now creates the cable always and the records only `if types` / `if have("pathways")`, so the
  story of a cable is still told in one place. `06_services.py::bgp` makes the ASN and loopbacks always and the
  sessions only with netbox-bgp. `build.py` streams every layer, collects the `[skipped]` lines and sums them up.
- **Adding a plugin later works for all six**, including the awkward one. netbox-wdm creates a node only when a device is
  created while its profile exists, so on devices that existed before the plugin the nodes are missing; layer 2 now
  creates them (`wdm_nodes()`), and the channels follow from the node.
- **Verified** against throwaway NetBox instances (the dev data was not touched): a plugin-free NetBox (build 39/0,
  second build changes nothing); the same NetBox with only the print plugin added (its acceptance tests run, the ones that
  need fms/wdm skip themselves); on a plugin-enabled NetBox from empty: everything switched off (39/0), then everything
  but WDM (64/0), then everything (70/0, 18 nodes created late, 4 wavelength services stitched), then again (nothing
  changes); a clean build with all plugins; and the dev NetBox re-run (70/0, nothing changes).
- **Rejected.** A second, smaller "core" dataset (two things to keep in step); one script per plugin (the cables and
  their records belong together); refusing to run without the plugins (the point of the change).
- **The print plugin's tests moved here** (`tests/tracepath/`), because the dataset knows its own names and the plugin
  must not. The plugin got a small test of its own that seeds a network and needs no data. The dependency now points one
  way: this repository may mention and test the plugin; the plugin's repository does not mention this one.

## Goal

An educational dataset for a fresh NetBox install, built in stages that
mirror NetBox's own object dependency order, so each stage is a complete,
demoable checkpoint — not one giant all-or-nothing dump. The scenario is a
fictional regional fiber-optic operator ("Nordfiber AB") chosen specifically
to give natural, realistic reasons to exercise NetBox's less-obvious
features later: multi-tenant colocation, cross-border sites, leased
circuits, owned dark fiber, and lit wavelength services — i.e., things that
justify the FMS and WDM plugins already installed on the target deployment,
not just core DCIM.

## Why the REST API, not the database, not Django fixtures

Three options were considered:

1. **Direct SQL / `loaddata` fixtures.** Rejected. Bypasses NetBox's model
   validation, cable-path tracing, computed/cached fields, and the
   changelog. You can produce rows that satisfy foreign-key constraints but
   are wrong by NetBox's own business rules — invisible until something
   downstream (a report, a cable trace, a plugin) breaks on them. Fixtures
   are also tied to a specific schema/PK layout and don't survive a NetBox
   upgrade.
2. **NetBox "Custom Scripts"** (server-side, run from the NetBox UI, using
   the Django ORM directly). Considered and set aside for the *base* load —
   they're faster and transactional, but they live inside NetBox and are
   less portable/inspectable as standalone teaching material sitting in its
   own repo. Kept in reserve as a possible later chapter ("NetBox can
   automate itself").
3. **REST API via `pynetbox`.** Chosen. Same validation and side effects a
   real API client gets, fully portable/inspectable as plain Python,
   and — importantly for an *educational* dataset — the API is one of
   NetBox's headline features, so the loading mechanism itself is part of
   the lesson.

## Idempotency strategy

Every layer script is safe to re-run, and *reconciling*. `common.ensure()`
looks an object up by its natural key (slug, name, cid, ...), creates it if
missing, and otherwise **updates any declared field that has drifted**.
Fields that can only be decided at creation time (rack placement, which
would otherwise shuffle a hand-adjusted rack) are passed in `once=` and are
never touched again. Cables go through `Cabler.connect()`, which does the
same for cable attributes and refuses, loudly, to touch a port that is
already cabled to something other than what the plan says.

The earlier phase scripts used a create-only `get_or_create()`. That was the
root cause of several bugs (editing the data never reached an object that
already existed; a retrofit script could silently reconcile the wrong
cable), and is what the layered rewrite below fixed. The NetBox instance is
still the only state: there is no "has this run" bookkeeping.

## The NetBox 4.5+ API token format (a real gotcha, documented in full)

This cost real debugging time and is worth recording precisely so it isn't
rediscovered the hard way again.

**What changed:** starting in NetBox 4.5, `Token` objects default to a "v2"
format. A v2 token is stored as a salted HMAC digest — the plaintext secret
exists only in memory at the moment `Token.save()` runs and is **never**
retrievable from the database afterward. The model has three relevant
fields:

- `key` — a 12-character public identifier, stored in the clear, safe to
  query later (`Token.objects.get(...).key` always works).
- `token` (a Python property backed by an in-memory `_token` attribute) —
  the plaintext secret, populated only immediately after
  `Token(...).save()`, `None` on any subsequently-fetched instance.
- `plaintext` — a DB column that exists only for **legacy v1** tokens; blank
  for v2.

The credential a client actually needs is `nbt_<key>.<secret>` — the
literal prefix `nbt_` (from `users.constants.TOKEN_PREFIX`), then the
`key`, a literal dot, then the `token` secret captured at creation time.

**The failure mode encountered:** creating a token via
`Token.objects.create(user=u)` and printing `t.key` gave a plausible-looking
12-character string, which was mistaken for the full credential. Using just
that value produced `403 Invalid v1 token` — NetBox's
`TokenAuthentication.authenticate()` infers v1-vs-v2 from whether the
*value itself* starts with `nbt_`, not from which HTTP scheme keyword
(`Token` vs `Bearer`) is sent. A bare 12-char key doesn't have the prefix,
so it was parsed as a (nonexistent) v1 plaintext token and rejected.

**The fix:** capture `t.key` and `t.token` together, immediately after
`t.save()`, and assemble `nbt_<key>.<token>` as the credential. `pynetbox`
needs no special configuration for this — pass the assembled string as its
ordinary `token=` argument; NetBox's server-side parser does the rest
regardless of header keyword.

**Correct creation snippet** (also in `README.md`):

```python
from django.contrib.auth import get_user_model
from users.models import Token
U = get_user_model()
u, _ = U.objects.get_or_create(username='demo-loader', defaults={'is_superuser': True, 'is_active': True})
Token.objects.filter(user=u).delete()
t = Token(user=u, description='demo-data loader scripts')
t.save()
print('nbt_' + t.key + '.' + t.token)   # capture NOW — unrecoverable after this line
```

## Verification methodology

Beyond "the script exited 0," each phase is checked at the relational
level, not just object-existence:

- **Idempotency**: re-run immediately after a fresh load; expect 100%
  `[exists]`, 0 `[created]`.
- **Hierarchy correctness**: for any parent/child structure (Regions,
  Locations), fetch with `?depth=1` (or expand the nested `parent` object)
  and confirm the resolved parent name matches what `config.py` specified —
  don't just trust that the create call didn't error.
- **Cross-object correctness**: for generic-relation objects (Contact
  Assignments), confirm the assigned object's *name*, not just its ID,
  resolves correctly — an off-by-one in `object_id` construction would
  still "succeed" as a valid API call while pointing at the wrong object.

Phase 1's spot checks (recorded 2026-09-26):

```
Nordics -> parent: None
Norway  -> parent: Nordics
Sweden  -> parent: Nordics

Nordfiber Stockholm DC / Suite 100     -> parent: None
Nordfiber Stockholm DC / Row A         -> parent: Suite 100
Nordfiber Stockholm DC / Row B         -> parent: Suite 100
Nordfiber Gothenburg PoP / Telecom Room -> parent: None
Nordfiber Malmö PoP / Telecom Room      -> parent: None
Nordfiber Oslo PoP / Telecom Room       -> parent: None
```

## Phase log

### Phase 1 — Organization (done, 2026-09-26)

Tenant groups, tenants, regions, site groups, sites, locations, contact
groups/roles, contacts, contact assignments. 39 objects. See "Scenario
reference" in `README.md` for the tenant/site list.

Design choice worth noting: a NetBox **Site** has exactly one `tenant`
field — it cannot itself "belong to" multiple tenants. The "sites with one
or multiple tenants" requirement is instead realized at the **Rack/Device**
level in Phase 2: the Site's own tenant is always Nordfiber AB (it's their
building), while individual colocated racks within that site carry the
*customer's* tenant. That's the standard NetBox modeling pattern for a
carrier-neutral or multi-tenant PoP, and it's what makes Stockholm and
Gothenburg end up "multi-tenant" and Oslo "single-tenant" once Phase 2 adds
racks.

### Phase 2 — Infrastructure (done, 2026-09-26)

Manufacturers, device types, device roles, racks, devices, mgmt IPAM
role/prefixes/IP addresses. 11 devices across 6 racks. See `README.md`
"Scenario reference" for the equipment list.

**Equipment decisions** (made with the user before building, not
unilaterally): real vendor hardware rather than fictitious placeholders,
specifically because NetBox's community
[devicetype-library](https://github.com/netbox-community/devicetype-library)
makes real definitions a live fetch rather than manual typing, and because
realistic interface names/optics matter once the FMS/WDM phases start
caring about which specific transceiver sits in which port.

- **Juniper MX204** — edge/core router, standardized across all four sites
  (realistic: a regional carrier running one routing platform, not a
  different box per site). 1U, real spec: `fxp0` mgmt + 4×100GbE QSFP28 +
  8×10GbE SFP+ (13 interfaces).
- **Arista DCS-7050SX3-48YC8-F** — aggregation switch, all four sites. 1U,
  `Management1` mgmt + 48×25G SFP28 + 8×100G QSFP28 (57 interfaces).
- **Dell PowerEdge R650** — generic colocated compute representing
  **Polaris Cloud Services**' equipment, not Nordfiber's own. 1U, 2×1GbE
  data + `iDRAC9` BMC (3 interfaces).
- Optical transport (SmartOptics DCP platform) was deliberately deferred to
  Phases 5–6 rather than added here — it's only thematically motivated once
  FMS/WDM exist to use it. SmartOptics was specifically checked against the
  devicetype-library before committing to it (real entries exist: DCP-2
  chassis, DCP-M40-PAM4-ER transponders, H-MD mux/demux modules) — chosen
  over Ciena partly because it's a Norwegian vendor, fitting the Nordic
  scenario.

**Mechanism**: `common.fetch_devicetype_yaml(path)` pulls the definition
live from the devicetype-library's raw GitHub content (e.g.
`fetch_devicetype_yaml("Juniper/MX204")`) rather than vendoring a copy —
the same file a real user would get from the library's own import tooling.
`common.create_device_type_from_yaml()` translates it into a `DeviceType`
plus its `interface-templates`. This means every device's interface list
in this dataset is authoritative real hardware spec, not approximated.

**Tenancy realized**: per the Phase 1 design note above, sites keep a
single owning tenant (always Nordfiber AB — they own the building), while
individual **racks** carry the tenant that actually uses them:

| Site | Racks | Tenant split |
|---|---|---|
| Stockholm DC | STO-RACK-A1 (Nordfiber core), STO-RACK-B1 (Polaris colo) | multi-tenant |
| Gothenburg PoP | GOT-RACK-1 (Nordfiber core), GOT-RACK-2 (Polaris colo) | multi-tenant |
| Malmö PoP | MMA-RACK-1 (Nordfiber core only) | single-tenant |
| Oslo PoP | OSL-RACK-1 (Nordfiber core only) | single-tenant |

Devices inherit their rack's tenant. IP addresses go one step further:
mgmt IPs for Polaris's servers are tagged tenant=Polaris even though the
*prefix* they're drawn from is tenant=Nordfiber (Nordfiber operates the
shared OOB/remote-hands network as a service to colo customers — realistic
DC practice, and a good demonstration that NetBox tracks tenancy
independently at every object level, not just inherited blindly downward).

**Verification performed** (not just "script exited 0"):

```
sto-rtr-01 interface_count: 13 (expect 13, matches MX204 template)
sto-sw-01 interface_count: 57 (expect 57, matches Arista template)
polaris-sto-srv-01 interface_count: 3 (expect 3, matches R650 template)
sto-rtr-01 primary_ip4: 10.0.1.11/24 (matches assigned mgmt IP)
polaris-sto-srv-01 tenant: Polaris Cloud Services (rack tenant inherited correctly)

Rack tenant split:
  Stockholm DC   / STO-RACK-A1 -> Nordfiber AB       Stockholm DC   / STO-RACK-B1 -> Polaris Cloud Services
  Gothenburg PoP / GOT-RACK-1  -> Nordfiber AB       Gothenburg PoP / GOT-RACK-2  -> Polaris Cloud Services
  Malmö PoP      / MMA-RACK-1  -> Nordfiber AB
  Oslo PoP       / OSL-RACK-1  -> Nordfiber AB
```

Interface counts matching the real device-type templates exactly confirms
NetBox's component-template auto-instantiation worked (interfaces are
never created directly by this script — creating a `Device` triggers
NetBox to instantiate one `Interface` per `InterfaceTemplate` on its
`DeviceType` server-side). Re-run immediately after: 0 created, everything
`[exists]`.

**API detail worth recording**: `ipam/prefixes` no longer takes a direct
`site` field in this NetBox version — it uses a generic `scope_type` +
`scope_id` pair (`"dcim.site"` + the site's ID) instead, generalizing a
prefix's scope beyond just sites. Caught by checking the endpoint's live
`OPTIONS` schema before writing the create call, same discipline as every
other endpoint in this project — assuming the older `site=` field still
existed here would have failed loudly, but it's exactly the kind of
"differs subtly between versions" trap this whole project exists to avoid.

#### Addendum, 2026-09-27: fourth customer tenant added to Gothenburg

User request: add another tenant colocating in Gothenburg. Added **Västhamnen
Logistics** (a fictional port-logistics/container-tracking operator —
Gothenburg is Sweden's largest port, so this is thematically grounded rather
than an arbitrary filler tenant), colocating one Dell PowerEdge R650 in a
new rack, **GOT-RACK-3**.

This was a deliberate test of the dataset's own "start small, grow it"
design: only `config.py` was edited (one tenant, one contact, one contact
assignment, one rack, one device, one mgmt IP) — no changes to either
script. Re-running both phase scripts in order created exactly the 3 new
Phase 1 objects and exactly the 3 new Phase 2 objects, and nothing else;
every pre-existing object still reported `[exists]`. That's the idempotency
strategy (§ above) working as intended under a real incremental edit, not
just a clean re-run of unchanged data.

Gothenburg PoP is now the dataset's richest multi-tenancy example: one
Nordfiber core rack plus two independent customer colo racks (Polaris,
Västhamnen), verified via the rack-tenant listing:

```
GOT-RACK-1 -> Nordfiber AB
GOT-RACK-2 -> Polaris Cloud Services
GOT-RACK-3 -> Västhamnen Logistics
```

### Phase 3 — Connections (done, 2026-09-27)

8 cables: 4 router↔switch uplinks (one per Nordfiber site, on the router's
`xe-0/1/0` — a 10GbE port deliberately chosen over its 100GbE `et-0/0/x`
ports, which are reserved for Phase 4's inter-site circuits) and 4 colo
server↔switch cross-connects (each colocated server's data port patched
into the *same* switch Nordfiber operates in that rack).

**Wireless links deliberately left out of this phase.** They were in the
original phase plan ("Cables, wireless links"), but there's no radio
equipment anywhere in the scenario — adding some purely to populate this
phase would be inventing a story rather than telling one. Worth revisiting
later only if a real reason appears (e.g. microwave backhaul as a fiber
backup between two nearby PoPs).

**Idempotency approach differs from Phases 1–2**: cables have no natural
slug/name to look up by. Instead, `common.create_cable_if_needed()` checks
whether either endpoint interface already has a `.cable` attached — an
interface can only ever terminate one cable, so this is a reliable
existence check without needing to enumerate existing cables and compare
endpoints.

**Known, disclosed simplification**: the switch's data ports are optical
(25G SFP28 / 100G QSFP28); the servers' data port is 1000BASE-T copper.
Real hardware would need a 1000BASE-T SFP in the switch (or a media
converter) to make this link physically real. NetBox's Cable model doesn't
validate physical media compatibility, so nothing broke — but it's
recorded here as a corner cut for dataset simplicity, not something to
mistake for an oversight later.

**Verification performed**: beyond the idempotent re-run (8/8 `[exists]`,
0 created), checked cable terminations resolve to the intended device/port
pairs from the cable side, and confirmed NetBox's cable-path tracing
resolves correctly from the *interface* side too:

```
sto-rtr-01:xe-0/1/0 -> cable id=1 -> connected_endpoints: ['sto-sw-01:Ethernet1']
                                     connected_endpoints_reachable: True
```

`connected_endpoints_reachable: True` is exactly the computed/traced
behavior that a direct-database-write approach (rejected at the very start
of this project — see "Why the REST API, not the database" above) would
have silently left broken. Worth noting as the point where that original
decision actually paid off, not just a theoretical concern.

#### Addendum, 2026-09-27: cable labeling scheme

User feedback: the original cables carried a descriptive string (e.g.
"Polaris cross-connect") in the `label` field, with nothing distinguishing
a physical cable ID from a human description. Reworked to a proper
site-scoped numbering scheme.

**Scheme chosen: `<site>-cbl-<NNN>`** (e.g. `sto-cbl-001`), sequential per
site, 3-digit zero-padded, reusing the `sto`/`got`/`mma`/`osl` prefixes
already established in device names rather than inventing a second
site-code convention. Site-scoped restart (each site's numbering starts
fresh at 001) means the label alone tells you which site's cable plan it
belongs to; 3-digit padding avoids a `cbl-9`-vs-`cbl-10` sort problem once a
site accumulates more than 9 cables, which Phase 4+ (circuits, fiber runs)
will do quickly. The old descriptive string moved to NetBox's `comments`
field on the same Cable object — `label` and `comments` are two distinct
NetBox Cable fields, not one field wearing two hats.

This required a real capability the codebase didn't have yet:
`common.create_cable_if_needed()` previously only checked whether a cable
existed and skipped everything else (matching the create-only idempotency
used for identity-bearing objects like sites/tenants throughout this
project). Cable *metadata* isn't identity, though — a label is exactly the
kind of field expected to get refined after the fact. The helper now
diffs `label`/`comments`/`status` on an existing cable against the desired
values and `PATCH`es only what's actually changed, reporting `[updated]`
distinctly from `[exists]`/`[created]`. Running the updated script against
the 8 already-existing cables produced 8 `[updated]` (label + comments both
changed on every one, as expected); running it again immediately after
produced 8 `[exists]`, confirming the new reconciliation logic is itself
idempotent, not just the original create-if-missing check.

### Phase 4 — Circuits (done, 2026-09-27)

2 providers, 2 circuit types, 2 circuits, 4 terminations, 2 cables.

**The two circuits tell deliberately different stories**, chosen with the
user before building rather than arbitrarily:

- **`NF-BRG-0001`** — Nordfiber AB *sells* an Ethernet Private Line to
  Baltic Retail Group, Stockholm ↔ Malmö, 1 Gbps commit rate. Provider =
  a new **Provider** object named "Nordfiber AB" — deliberately distinct
  from the *Tenant* object of the same name from Phase 1. NetBox tracks
  "who owns this infrastructure" (Tenant) and "who sells this circuit
  service" (Provider) as separate concerns, and a real company is very
  often both at once. Both terminations are cabled to a router's `et-0/0/x`
  port (the 100GbE ports reserved back in Phase 3 specifically for this).
- **`PLT-100234`** — Nordfiber AB *buys* (leases) dark fiber from a new
  fictional wholesale provider, **Polarlink Transit**, for the Stockholm ↔
  Oslo cross-border segment — realistic: regional carriers essentially
  never own fiber across a national border outright, they lease dark
  strands from a transit wholesaler and light them with their own
  equipment. Tenant on this circuit is Nordfiber AB itself (they're the
  *customer* here). Deliberately **not** cabled to any device interface —
  dark fiber has no active gear on it. It becomes a real physical fiber
  asset in Phase 5 (FMS) and gets lit by Nordfiber's own SmartOptics WDM
  gear in Phase 6, which is what Fjord Media Networks' wavelength service
  (per their Phase 1 tenant description) will actually ride over. This is
  the connective tissue between Phases 4, 5, and 6 — not three unrelated
  demos.

**Mechanism generalized from Phase 3**: `common.create_cable_if_needed()`
previously assumed both cable ends were device interfaces. A circuit
termination is a different NetBox object type (`circuits.circuittermination`)
that also happens to expose `.cable`, so the function was generalized to
take an explicit object-type string per end and dispatch to the right
endpoint for the existence-check refetch — rather than writing a
circuit-specific copy of the same logic. Re-verified Phase 3 still produces
8/8 `[exists]` after this refactor before building on top of it.

**Verification performed**, again going past "the script exited 0":

```
NF-BRG-0001  provider=Nordfiber AB       tenant=Baltic Retail Group    type=EPL         commit_rate=1000000
PLT-100234   provider=Polarlink Transit  tenant=Nordfiber AB           type=Dark Fiber  commit_rate=None

PLT-100234 terminations: cable=None on both A and Z sides (correct — no device connection yet)

Cable-path trace from sto-rtr-01:et-0/0/0:
  cable -> circuit termination A (NF-BRG-0001) -> circuit -> termination Z -> cable -> mma-rtr-01:et-0/0/0
  connected_endpoints: ['mma-rtr-01:et-0/0/0']
  connected_endpoints_reachable: True
```

The last part is the significant one: NetBox's cable-path tracer followed
the connection **through** the circuit object itself, from one router's
physical interface across two cables and a commercial circuit construct to
the *other* router's physical interface, and correctly reports them as
reachable from each other. That's a materially more sophisticated computed
result than Phase 3's plain interface-to-interface trace, and it's exactly
the kind of cross-object computed behavior that would be extremely easy to
get subtly wrong (or simply not get at all) with a direct-database-write
approach — the strongest validation yet of that original Phase 1 decision.

### Phase 5 — FMS (done, 2026-09-27)

netbox-fms is a materially richer plugin than anything used so far — its
own API root (`/api/plugins/fms/`) exposes 19 endpoints (cable types,
buffer tubes, ribbons, splice plans/projects, fiber circuits and their own
node/path routing...). Before designing anything, the actual live schema
was explored via `OPTIONS` on the endpoints this phase needed, and three
things were verified empirically with throwaway test objects (created,
inspected, deleted) rather than assumed from the plugin's README:

1. **`fms.FiberCable` decorates an existing `dcim.Cable`** — it has a
   required `cable` field and no endpoints/site fields of its own. FMS
   describes what's *inside* a cable (strand structure); it doesn't
   replace NetBox core's own physical-connection model. This meant a real
   `dcim.Cable` had to exist first, which meant something had to be at
   each end of that cable — which is what drove the patch panel decision
   below, not an incidental extra.
2. **Front port ↔ rear port mapping isn't inferred by the REST API.** The
   devicetype-library YAML for simple 1:1 LC patch panels omits an
   explicit mapping (its name-matching convention is only interpreted by
   NetBox's own *UI* import form). Calling the plain REST API directly
   requires posting `rear_ports: [{"rear_port": <id>, "position": 1}]` on
   each front-port-template explicitly — confirmed by creating one via a
   throwaway device type and reading back what NetBox actually stored.
   `common.create_device_type_from_yaml()` was extended to create rear
   ports first (they need to exist before front ports can reference them)
   and pair them up by list position.
3. **Buffer tubes and strands auto-instantiate**, exactly as advertised:
   creating an `fms.FiberCable` against a cable type with buffer-tube
   templates immediately produces real `BufferTube` + `FiberStrand`
   objects — no separate strand-creation calls needed. Verified with a
   throwaway 4-strand cable type (produced exactly 1 tube + 4
   correctly-EIA/598-colored strands), matching the plugin's own claimed
   feature before it was relied on for the real dataset.

**What was built**: a real generic 24-port LC fiber patch panel (device
type fetched from the devicetype-library, one per site, in the Nordfiber
rack), a **Corning ALTOS** 24-strand loose-tube cable type (real product
line; **DIN/IEC 60304** color scheme chosen over the more US-centric
EIA/598 for Nordic-region authenticity, consistent with Phase 2's
SmartOptics choice), 2 buffer tube templates (12 strands each), and 3
backbone fiber cables terminated on the patch panels' rear ports:

- `bb-cbl-001`: Stockholm ↔ Gothenburg (Nordfiber-owned)
- `bb-cbl-002`: Stockholm ↔ Malmö (Nordfiber-owned — the physical path
  underneath Baltic Retail Group's EPL circuit `NF-BRG-0001` from Phase 4)
- `bb-cbl-003`: Stockholm ↔ Oslo (the physical realization of the dark
  fiber Nordfiber leases from Polarlink Transit under circuit
  `PLT-100234`, Phase 4 — deliberately left unlit)

**Cable label scheme extended again**: backbone runs cross two sites, so
they get a `bb-cbl-NNN` namespace rather than being shoehorned into either
site's `<site>-cbl-NNN` sequence from Phase 3.

**Deliberately deferred, not forgotten**: patch panel *front* ports are
left uncabled in this phase. Real outside-plant fiber lands on a demarc
(the rear port); a technician cross-connects the front port to whatever
active equipment needs that strand. Nothing needs that cross-connect yet —
Phase 4's circuit-termination cables were already simplified straight to
the routers (a pre-existing, disclosed simplification, not retrofitted
here) and Phase 6's WDM transponders will be the first real, well-motivated
consumer of a front-port patch cord.

**Verification performed**:

```
3 fiber cables, each: 2 buffer tubes ("Tube 1", "Tube 2"), 24 strands total
Strand colors: ff0000, 00ff00, 0000ff, ... (DIN/IEC red-green-blue order —
  confirmed DIFFERENT from the EIA/598 blue-orange-green order seen in the
  earlier throwaway test, proving color_scheme is actually respected, not
  defaulted)
sto-patch-01: front_port_count=24, rear_port_count=24
sto-patch-01 rear port "Port 1": cable=bb-cbl-001 (correct attachment;
  connected_endpoints=None is CORRECT here too — that trace runs through
  the paired front port, which is intentionally uncabled in this phase)
```

Re-run immediately after: 0 created, everything `[exists]` — including the
device type's port templates and the auto-instantiated strands, none of
which get double-created on a second pass.

### Phase 6 — WDM (done, 2026-09-27)

Lights the Stockholm ↔ Oslo leased dark fiber (`bb-cbl-003` / circuit
`PLT-100234`) with a real SmartOptics muxponder at each end, and delivers
a genuinely stitched, verified-complete wavelength service for Fjord Media
Networks. This phase surfaced the most, and most consequential, real bugs
of the whole project so far — one in this dataset's own shared code, one
in the plugin itself — both found the same way as everything else here:
by testing against the live system rather than trusting documentation.

**Device chosen**: SmartOptics **DCP-M40-PAM4-ER**, a real 1U 40-channel
muxponder. Its 40 front ports are individually named by real ITU 100GHz
grid frequency (`921`–`960` = ITU channels 21–60) and all fan into one
combined `Line` rear port — confirmed by inspecting the device type's own
`port-mappings` block in its devicetype-library YAML, which explicitly
lists `front_port`/`rear_port`/`rear_port_position` for all 40 ports (a
genuinely different shape from the simple 1:1 same-name pairing the
Phase 5 patch panel used).

**Bug #1 — in `common.create_device_type_from_yaml()`, this dataset's own
code.** NetBox's front-port-to-rear-port mapping object has *two* separate
position fields: `position` (the front port's own internal position — 1
for a plain simplex LC connector) and `rear_port_position` (which of the
rear port's N slots this mapping occupies). The first implementation
conflated them — passing the mapping's `rear_port_position` value into the
`position` field and never setting `rear_port_position` at all, which
silently defaults to 1. Every front port beyond the first therefore tried
to occupy rear-port slot 1 a second time, failing with `The fields
rear_port, rear_port_position must make a unique set`. Diagnosed by
comparing the OPTIONS-derived field list (which didn't distinguish the two
clearly) against the full OpenAPI schema's `FrontPortTemplateMappingRequest`
definition, which does. Fixed in the shared helper, so any future
multi-position device type (an MPO breakout panel, say) benefits too — not
just this one device.

**Bug #2 — in netbox-wdm 0.2.2 itself, upstream.** `POST
.../wdm-nodes/{id}/sync-ports/?dry_run=false` (the action that's supposed
to confirm a node's `port_sync_valid` flag) throws a server-side
`AttributeError: 'Func' object has no attribute '_meta'` on this NetBox
version (4.6.10) — reproducible, not a fluke. 0.2.2 is currently the only
published release, so there's no newer version to move to. Investigated
rather than worked around: querying an individual channel's own `/trace/`
action showed `is_complete: true, is_active: true, is_valid: true` despite
`port_sync_valid` staying `false` — meaning this flag is a separate
drift-detection health-check, not a gate on actual path validity. The
wavelength service works correctly; only that one confirmation action is
broken. Documented here rather than patched around, consistent with this
project's rule of not reaching into a plugin's internals to force a fix.

**Discovery — grid_position is an index into a real ITU table, not a free
value.** Creating a `wdm-channel-plans` entry with `grid_position=1` and
arbitrary `wavelength_nm`/`label` values produced an auto-instantiated
channel labeled **`C21` at 1560.61nm** — the plugin computed and overrode
both values from its own built-in ITU-T grid table for `dwdm_100ghz`,
ignoring what was supplied. `grid_position=1` corresponds to the device's
own front port `921` (= ITU channel 21) — confirmed by cross-referencing
the device type's real port names, not assumed. `config.py`'s
`WDM_CHANNEL_PLAN` now only supplies `grid_position` and a front-port
reference; the placeholder `wavelength_nm`/`label` values passed at create
time are never actually used, which is called out explicitly in code
comments so it isn't mistaken for a bug later.

**Discovery — a WdmCircuit doesn't auto-discover its wavelength path.**
`WdmWavelengthPath` objects ARE auto-computed once both ends' channels are
physically wired (visible per-channel via `/trace/` before any circuit
exists at all) — but attaching one to a `WdmCircuit` is a separate, manual
step via the circuit's `wavelength_paths` field. Calling the circuit's
`/stitch/` action before doing that returns `paths: []`, which reads like
failure but isn't — it's just reporting the circuit's (empty)
associations. Fixed by looking up the path by `grid_position` and PATCHing
it onto the circuit before stitching.

**Physical path completed end-to-end**: each WDM node's `Line` rear port
was cross-connected to the FRONT port on that site's patch panel which
passes through to the rear port already cabled to the outside fiber in
Phase 5 — the first real use of those front ports, left deliberately
uncabled since Phase 5 specifically for this. Full chain: `sto-wdm-01
Line` → cable → `sto-patch-01` front `Port 3` → (patch panel pass-through)
→ `sto-patch-01` rear `Port 3` → `bb-cbl-003` (outside fiber) →
`osl-patch-01` rear `Port 1` → (pass-through) → `osl-patch-01` front
`Port 1` → cable → `osl-wdm-01 Line`.

**Verification performed** — the `stitch` result is the real end-to-end
proof, not a per-object existence check:

```
stitch result: service "Fjord Media Networks - Wavelength Service", status active
  path: wavelength_nm=1560.61, is_complete=True, is_active=True
    sto-wdm-01 channel C21 (front port 921) -> osl-wdm-01 channel C21 (front port 921)
```

`is_complete: True` / `is_active: True` on a freshly-stitched path is a
materially stronger claim than anything checked in earlier phases: it
means the plugin's own path-finding engine walked the full physical chain
above — two devices, two channels, two cross-connect cables, and the
Phase 5 backbone fiber in between — and confirmed it end-to-end. Re-run
three times total while fixing the two bugs above; the final clean run
reports 0 created / all `[exists]` except the (also now-idempotent)
wavelength-path attach step, and `stitch` returns the identical complete
path every time.

### Phase 7 — BGP, Secrets, Inventory (done, 2026-09-27)

The last of the originally planned 7 phases. Three unrelated plugins in one
script since each is small alone: a full iBGP mesh (netbox-bgp), genuinely
encrypted per-device credentials (netbox-secrets), and a small cold-spares
depot (netbox-inventory).

**BGP**: one private-use ASN (65001 — Nordfiber doesn't need a real public
one for internal iBGP), a loopback interface + `/32` IP on each of the 4
core routers (standard ISP practice: peering on loopbacks survives any
single physical link flapping, unlike peering on a physical interface's
own address), one peer-group, and a full 6-session iBGP mesh. **Disclosed
simplification**: one `Session` object per router *pair*, not one per
router's own view of each peer (which would be 12, documenting both
sides) — kept to 6 for this phase's scope.

**A real, non-obvious requirement caught immediately**: `ipam.asn`'s `rir`
field isn't marked required in the endpoint's `OPTIONS` response but *is*
enforced at creation — the same class of surprise as `role` on
`tenancy.contacts` back in Phase 1's design, and `role` on
`secrets.secrets` hit again in this very phase (see below). A `Private Use
(RFC 6996)` RIR (`is_private: true`) was created rather than reusing a real
one, since 65001 is a real private-use ASN, not a placeholder pretending to
be a real allocation.

**Secrets — the real cryptographic workflow, not a toy version of it**.
netbox-secrets doesn't encrypt with a single static site key — it encrypts
with an RSA keypair activated per NetBox user, and every write needs a
short-lived "session key" obtained by submitting your *private* key to
unlock your copy of the site's master key. This was worked out empirically
against the live API (generate a keypair → activate a `UserKey` → exchange
the private key for a session key → pass it as `X-Session-Key` on the
write), the same way as every other new plugin surface in this project.
Two things mattered enough to get their own handling:

1. **The private key is exactly as ephemeral as the Phase 1 API token** —
   it exists in full only once, in the `generate-rsa-key-pair` response.
   Unlike the API token (which is only needed once, at `.env` setup time),
   this key is needed on *every* future run that writes a secret. It's
   persisted to `.secrets_userkey.pem` (gitignored, chmod 600) the first
   time, and reused thereafter — `common.get_secrets_session_key()` checks
   for the file before ever generating a new keypair, and refuses to
   proceed (rather than guess) if a `UserKey` already exists for
   `demo-loader` but the local file is missing, since there would be no
   way to recover the matching private key.
2. **`role` is required on `secrets.secrets`** despite not being marked so
   in `OPTIONS` — caught immediately by the first real write attempt
   (`{'role': ['This field cannot be null.']}`), fixed by creating a
   `Device Login` secret role first. This is the second time in this
   project a field silently required at the model level wasn't flagged as
   required in `OPTIONS` (the other being `ipam.asn.rir`, this same phase)
   — worth remembering as a general pattern for future NetBox plugin work:
   don't fully trust `OPTIONS` to enumerate every required field; a first
   real write attempt tells the truth fast, and cheaply.

**Values are obvious placeholders** (`Nf-Sto-Rtr-D3mo!` etc.), never real
credentials — noted directly in `config.py` alongside them, since a
teaching dataset with unrealistic-looking secrets is safer than one that
could be mistaken for real ones.

**Inventory**: one `Spare Chassis` asset role and three `stored` spare
assets at the Stockholm hub — one each of the Juniper router, Arista
switch, and SmartOptics muxponder in active use elsewhere in the dataset,
matching the real practice of stocking a cold spare for anything whose
failure would take a whole site offline.

**Verification performed** — the secrets check is the most rigorous of any
phase, since "it exists" is a much weaker claim than "it actually encrypts
and decrypts correctly":

```
BGP: 6/6 sessions, each showing the correct loopback pair and AS65001 on both sides

Secrets round-trip proof:
  GET secret (no X-Session-Key header)  -> plaintext: None       (correctly hidden)
  GET secret (with X-Session-Key header) -> plaintext: "Nf-Sto-Rtr-D3mo!"  (correctly decrypted)

Inventory: 3/3 spare assets, status=stored, correct device_type/role/location
```

Re-run twice after the fixes above: 0 created both times, all `[exists]`
— including the secrets step reporting "(reusing existing keypair from
.secrets_userkey.pem)" rather than generating a new one, confirming the
persistence mechanism itself is what makes the whole phase idempotent, not
just the individual object checks.

---

### Addendum, 2026-09-27: cable tenancy, and a missing link found while fixing it

User feedback, reviewing the data directly: cables were missing tenant
information, and something seemed missing in the connections. Both turned
out real, and fixing the first led straight to finding the second.

**1. Every cable in the dataset was missing its `tenant` field.**
`dcim.Cable` has had a `tenant` field the whole time (visible in the very
first `OPTIONS` dump back in Phase 3) — it was simply never populated in
any of the 15 cables created across Phases 3–6. Fixed by establishing an
explicit rule, applied consistently: **a cable's tenant reflects who
owns/operates the physical cable itself, not who commercially benefits
from what rides over it.** Concretely:

- Nordfiber-to-Nordfiber links (router↔switch uplinks, the backbone fiber,
  WDM cross-connects, circuit demarc-extension cables) → `Nordfiber AB`,
  even where a customer's circuit or service rides over them — that
  commercial relationship already lives on the Circuit/WdmCircuit object,
  not the physical cable.
- A cross-connect landing on a **customer's own colocated device**
  (Polaris's or Västhamnen's servers) → that customer's tenant, matching
  how the device/rack was already tenanted in Phase 2.
- The leased Stockholm↔Oslo backbone fiber (`bb-cbl-003`) → `Nordfiber AB`,
  consistent with circuit `PLT-100234` also being tenanted to Nordfiber as
  the paying customer of that lease, not to the lessor.

**Required a real fix to the shared idempotency helper first.**
`common.create_cable_if_needed()`'s field-reconciliation logic only
unwrapped choice fields (via `.value`, e.g. `status`) — a nested-object
field like `tenant` has an `.id` instead, no `.value`, so the old code
compared a whole Record object to a plain integer, which is never equal.
Left as-is, every future run would have reported `[updated]` on every
cable forever, never settling to `[exists]`. Fixed to unwrap either shape.
Applying the tenant field to all 15 existing cables (re-running Phases
3–6) confirmed the fix: 15 `[updated]` the first time, then 0 on immediate
re-run.

**2. That re-run surfaced a second, unrelated netbox-wdm bug.** Saving the
two WDM cross-connect cables (only to set `tenant` — nothing WDM-related)
caused netbox-wdm to re-run its path-discovery logic and spawn a **second**
`WdmWavelengthPath` for the same `grid_position`, rather than recognizing
the existing one. `06_wdm.py`'s wavelength-path lookup used a plain
`.get(grid_position=...)`, which raises on more than one match — so this
one-line unrelated edit crashed a completely different part of the script.
Fixed properly, not just patched around: `06_wdm.py` now prefers whichever
path is already attached to the circuit (stable across re-runs), falls
back to the lowest `id` (oldest, originally-verified) only when nothing is
attached yet, and prints a warning naming this exact upstream quirk if
more than one candidate ever appears again. The stray duplicate was
deleted by hand once, and two full re-runs afterward confirmed the fix
holds — no further duplicates, path count stays at 1.

**3. Fixing #2 uncovered a real, previously-informal piece of the
topology.** Two cables existed in NetBox with no label and no tenant —
not test leftovers, but a **genuine, correct connection** made during
Phase 6's own development and never formalized in `config.py`: each WDM
node's client-facing channel port (front port `921`, ITU channel 21)
cross-connected to that site's own switch, on a spare 100GbE port
(`Ethernet49/1` — untouched until now). This is the piece that makes the
wavelength service carry real switch traffic rather than just existing as
lit glass between two idle transponder ports; it's also exactly what had
already flipped `mux_connected`/`demux_connected` to `true` in the Phase 6
stitch output, a detail that went unremarked on at the time. Formalized as
`WDM_CLIENT_CROSS_CONNECTS` in `config.py` and a proper creation/
reconciliation step in `06_wdm.py`, tenanted to Nordfiber AB (shared
transport plumbing — only 1 of the muxponder's 40 channels is Fjord
Media's).

**End state, verified**: 17 cables total (15 original + 2 newly
formalized), zero missing a tenant, exactly 1 `WdmWavelengthPath` (no
duplicate), `stitch` still reports `is_complete: true` / `is_active: true`
with both ends now showing `mux_connected: true, demux_connected: true`.
Two full re-runs of the affected phases afterward: 0 created, 0 updated,
0 warnings.

---

### Phase 8 — Baltic Retail Group backup path (done, 2026-09-27)

A DWDM-based protect path for circuit `NF-BRG-0001`, routed Stockholm ↔
Gothenburg ↔ Malmö instead of a second direct fiber run. User-requested,
plan presented and confirmed before implementation (including one
clarifying question: client handoff lands on the routers, a spare 100GbE
port, matching the primary circuit's own termination — confirmed rather
than assumed, since Fjord Media's WDM handoff went to a switch instead, a
different but equally reasonable choice for a different circuit).

**The core technical fact that shaped everything else**: the WDM hardware
in this dataset (SmartOptics DCP-M40-PAM4-ER) is a terminal mux, not a
ROADM — it can terminate a wavelength, not pass one through a site
optically. A genuine multi-hop path therefore needs two independent lit
segments with **electrical regeneration** at Gothenburg: two muxponders,
back to back, jumpered client-port to client-port, rather than one
continuous wavelength end to end. This has a real, confirmed-not-assumed
modeling consequence: `/stitch/` reports **two** separate complete paths
(Stockholm↔Gothenburg, Gothenburg↔Malmö), not one Stockholm↔Malmö path —
correct for regenerated transport, not a bug.

Built: `bb-cbl-00004` (new Gothenburg↔Malmö backbone fiber, FMS-decorated,
mirroring Phase 5's pattern exactly); a second WDM channel-plan entry
(grid_position 2, ITU channel 22) added to the *existing* shared WDM
profile; 4 new WDM terminal devices (`sto-wdm-02`, `got-wdm-01`,
`got-wdm-02`, `mma-wdm-01`); line cross-connects to each site's patch
panel; a client-port-to-client-port jumper between `got-wdm-01` and
`got-wdm-02` (the regeneration point); client cross-connects to
`sto-rtr-01`/`mma-rtr-01`; commercial circuit `NF-BRG-0002` with **both**
terminations deliberately left uncabled (same pattern as `PLT-100234`,
Phase 4) — the router ports are already physically used by the WDM client
cross-connects, so a second direct cable to the same port is both
impossible and redundant; and two `WdmCircuit`s, one per regenerated
segment.

**A real bug hit and fixed**: `WdmChannelPlan` (unlike `WdmChannel`) does
NOT have its `wavelength_nm` overridden by the plugin — it's stored
exactly as given, and the database enforces uniqueness on
`(profile, wavelength_nm)`, not `(profile, grid_position)`. The existing
grid_position-1 entry already occupied the `1550.0` placeholder used in
Phase 6, so creating a second entry with the same placeholder failed with
a 400. Fixed by giving each entry a distinct placeholder
(`1550.0 + grid_position`).

**A second real problem, solved cleanly**: both new segments share
`grid_position` 2, and `WdmWavelengthPath` carries no node/device
reference at all — a plain `.filter(grid_position=2)` returns candidates
from *both* segments with no way to tell them apart. Solved by tracing a
representative device's own channel via its `/trace/` action, which
returns the exact `wavelength_path_id` for the path that channel is
actually part of, plus the full list of node names in that path — used to
assert the trace covers exactly the expected two devices before trusting
it, rather than just taking the first result.

**A design decision surfaced late, and fixed properly rather than left
implicit**: `sto-wdm-02` is a genuinely separate physical chassis from the
already-existing `sto-wdm-01`, even though `sto-wdm-01` has 39 unused
channels that could technically have hosted grid_position 2 instead. This
wasn't explicitly decided at the time — it was caught when the user asked
directly why a second chassis was created at Stockholm and Malmö. Re-
examined and confirmed with the user rather than just asserted: a protect
path sharing its primary's physical muxponder would defeat the point of
protection (a chassis/card/software failure on `sto-wdm-01` takes out the
backup too, not just a fiber cut) — real path protection wants independent
hardware, not just an independent wavelength on the same box. Documented
inline in `config.py` next to `BACKUP_WDM_NODES` so it's no longer an
unstated assumption. (Malmö's `mma-wdm-01` isn't actually "secondary" to
anything — Malmö had zero WDM equipment before this phase.)

**Verified**: both new `WdmCircuit`s stitch `is_complete: true,
is_active: true`; two full re-runs of `08_baltic_retail_backup.py`: 0
created on the second.

### Phase 9 — Erik Lindqvist's workplace + a Gothenburg Internet circuit (done, 2026-09-27)

Two independent, user-requested additions, planned and confirmed before
implementation (two `AskUserQuestion` rounds: office-as-new-Location vs.
new-Site, and reusing the Gothenburg mgmt prefix vs. a separate office
VLAN — both resolved toward the simpler option).

Erik Lindqvist already existed as a Contact (NOC Engineer, assigned to all
4 sites, Phase 1) — this phase gives him an actual physical desk: two new
Locations under the *existing* `nordfiber-gothenburg-pop` site (Office
Floor 3, IDF Floor 3 — one building, office floor above the ground-floor
telecom room, not a separate site elsewhere in the city); a small IDF
rack; a real Arista DCS-7010T-48 (48×1000BASE-T copper + 4×10G SFP+
uplinks — the first copper-only switch device type in this dataset) as the
distribution switch; a real Dell OptiPlex SFF 7050 as his workstation
(deliberately **not** rack-mounted — a desk PC, unlike everything else in
this dataset); a Cat6a cable standing in for the TP outlet + horizontal
run (the same simplification already used for fiber patch-panel front
ports — NetBox has no separate "wall jack" object); a fiber cable for the
inter-floor riser uplink to `got-sw-01`; both new devices on the existing
Gothenburg mgmt prefix (`10.0.2.0/24`) rather than a new office VLAN,
since nothing else in this dataset enforces inter-VLAN routing policy
anyway; and a device-level contact assignment giving Erik his own
workstation in addition to his existing site-level assignments.

Also added: a standalone Internet Access circuit type + a new fictional
provider (Vastkust Bredband AB) + one circuit (`VKB-INET-0001`) at the
Gothenburg PoP, terminated **only** on the A-side — a regional ISP the
size of Nordfiber still buys its own upstream transit somewhere, and the
provider's own network beyond the demarc isn't Nordfiber's to document. A
single-sided `CircuitTermination` is valid in NetBox; this is the first
one in the dataset with no Z-side at all (`PLT-100234`, Phase 4, has both
sides present but uncabled — a different case).

**One real snag**: the planned uplink port `got-sw-01:Ethernet2` turned
out to already be in use (`got-cbl-00002`, a Phase 3 colo cross-connect) —
caught immediately by a 400 "Duplicate termination" error, not silently
overwritten. Moved to `Ethernet4`, confirmed free by checking every
interface's `.cable` state directly before re-running.

**Verified**: two full re-runs of `09_gothenburg_office.py`: 0 created on
the second.

### Phase 10 — WDM client demarc shelf (done, 2026-09-27)

User-requested: a SmartOptics DCP-2 chassis at every site with WDM
equipment, so a tenant is handed a plain grey 1310/1550nm optic on a
dedicated demarc shelf instead of patching directly into the DWDM
muxponder's own channel port. This phase went through more back-and-forth
than any other before anything was built, and it's a good example of why —
two real hardware mismatches surfaced that would have produced a
physically-nonsensical model if built on the first ask:

1. The user's original request named two modules for the chassis: a
   DCP-1610 and a DCP-110. Both are real, and both exist in the
   devicetype-library's `module-types/` tree (a separate tree from
   `device-types/` — the first attempt to fetch one 404'd until
   `common.py` grew a second fetch function, `fetch_moduletype_yaml`, for
   it). But the DCP-1610's "Line" ports are only 10G each, while this
   dataset's existing muxponder (DCP-M40-PAM4-ER) puts a full **100G**
   signal on every DWDM channel — there's no way to plug a 10G port into a
   100G one. Surfaced directly to the user rather than guessed around;
   confirmed answer: drop the DCP-1610 for now (no matching lower-rate DWDM
   layer exists in this dataset to justify it), keep only the DCP-110
   (100G Line QSFP28 + 10×10G SFP+ Client — its Line side matches a
   channel port exactly).
2. Whether to retrofit the *existing* tenant handoffs (Fjord Media's
   wavelength service, Baltic Retail's backup-path router handoffs)
   through the new shelf, or leave them as direct colored cross-connects
   and only use the shelf for future tenants — confirmed: retrofit them,
   so every tenant handoff is grey-optic and consistent.

Built: DCP-2 chassis device type (the first in this dataset with
**module bays**, requiring `create_device_type_from_yaml` to grow support
for `module-bays` → `ModuleBayTemplate`); a DCP-110 **module type**
(`create_module_type_from_yaml`, new — module types have no `slug` field,
looked up by `(manufacturer, model)` instead); one chassis per site with
WDM equipment (`sto-dcp2-01`, `got-dcp2-01`, `mma-dcp2-01`,
`osl-dcp2-01`); a DCP-110 module installed in each (two in Stockholm's,
one per existing WDM node there — confirmed empirically that NetBox
substitutes the module bay's own `position` value for the literal
`"{module}"` placeholder in the module type's interface-template names,
producing real interfaces like `Line/1/1`/`Client/2/1`); and, for every
site with an actual live tenant channel, a retrofit: delete the old direct
muxponder-channel-to-client cable, then cable channel front port → shelf
Line port → shelf Client port → the same client interface as before
(same label, since it's still the same logical handoff).

**Gothenburg is the one site with nothing to retrofit**: `got-wdm-01`'s
and `got-wdm-02`'s only channel is already fully consumed by the Phase 8
regeneration jumper between them, not a tenant handoff — no free channel
exists there to plug the DCP-110 into yet. Its chassis and module are
still created (so the infrastructure is consistent everywhere), just left
uncabled, with the reason recorded in `config.py` rather than left as a
silent gap.

**Retrofit safety**: a new `disconnect_direct_cable_if_present()` helper
was added rather than reusing `create_cable_if_needed()` for the removal
— that function only ever adds or reconciles a cable's fields, it never
re-terminates one, so the pre-existing direct cable had to be deleted
before the two new intermediate cables could be created. The helper
checks that **both** endpoints resolve to the *same* cable before
deleting, which is what makes it safe to call on every re-run: once the
retrofit has happened, the muxponder channel port and the original client
interface are each on their own, different cable (one to the shelf's Line
port, one to its Client port), so nothing gets deleted the second time.

**Verified**: idempotency (0 created/deleted on re-run) and, more
importantly, that the retrofit didn't silently break anything already
working — re-ran `/stitch/` on all three `WdmCircuit`s (Fjord Media's
service, both Baltic Retail Group backup segments) afterward and confirmed
all three still report `is_complete: true, is_active: true`.

---

### Phase 11 — colo tenant fiber cross-connects via a MeetMe room (done, 2026-09-27)

Re-architects how the two colo tenants (Polaris Cloud Services, Vasthamnen
Logistics — Baltic Retail Group and Fjord Media Networks are service
customers, not colocated, and are unaffected) reach Nordfiber's network:

```
OLD: tenant server --------------------------------------------> Nordfiber's switch
NEW: tenant server -> tenant's OWN switch -> tenant's ToR panel -> [trunk] ->
     tenant's dedicated panel in a MeetMe room -> [trunk] ->
     Nordfiber's EXISTING patch panel -> [jumper] -> Nordfiber's switch
```

This went through two full rounds of user confirmation before anything was
built — the topology itself (3 questions: dedicated-panel-per-tenant vs.
shared panel, reuse Nordfiber's existing patch panels vs. a new dedicated
one, MeetMe Locations everywhere vs. only where a tenant exists today —
all resolved toward the option that reuses existing infrastructure), and
then a **correction that arrived after the topology was already
confirmed**: the MeetMe room does not belong to Nordfiber. It's a
third-party carrier-neutral facility — Nordfiber is a customer of it for
cross-connect services, exactly like Polaris and Vasthamnen are. This
didn't change any cabling already agreed on, but it did change *tenancy*:
a new fictional facility-operator tenant, **Skagerrak Interconnect AB**
(its own new TenantGroup, "Facility Operators"), now owns the two MeetMe
racks (`STO-RACK-MMR1`, `GOT-RACK-MMR1`) instead of `nordfiber-ab` — even
though the MeetMe Location itself still sits under Nordfiber's existing
Site (a shared interconnection floor in the same building, a common real
carrier-hotel arrangement). Each party's own panel inside that shared rack
still carries *its own* tenant, unaffected by the correction.

Built: MeetMe Locations at all 4 sites (Malmo/Oslo stay empty — no colo
tenant there yet); 2 MeetMe racks; per tenant-rack (3 total: Polaris at
Stockholm, Polaris at Gothenburg, Vasthamnen at Gothenburg) a tenant-owned
Arista DCS-7010T-48 switch + a ToR patch panel, both reusing device types
already fetched in earlier phases (Phase 9's switch, Phase 5's patch
panel) rather than fetching new ones; a dedicated demarc panel per tenant
in the MeetMe room; a retrofit of each existing server↔Nordfiber-switch
cable onto the tenant's own switch instead; and the 4-hop passive fiber
chain (switch uplink → ToR panel → MeetMe panel → one of
`sto-patch-01`/`got-patch-01`'s spare ports → Nordfiber's switch,
reusing `disconnect_direct_cable_if_present` from Phase 10 for the
retrofit).

**A real, forced consequence, not an open choice**: both Stockholm Polaris
servers now aggregate through *one* tenant switch with *one* fiber uplink,
so Nordfiber only needs one port on `sto-sw-01` for Polaris instead of
two — the second port is simply freed, not replaced with anything.

**Verified two ways**: idempotency (0 created/deleted on re-run of
`11_colo_crossconnects.py`), and — more meaningfully — NetBox's own
interface `.trace()` from each tenant switch's uplink port. This is the
first phase verified this way: the trace followed the full passive chain
automatically through both patch panels' front↔rear pass-through (a real
NetBox cable-trace behavior, distinct from an active device like a switch,
which correctly does NOT pass a trace through from one port to another)
and landed exactly on the expected Nordfiber switch port, for all 3
tenant-rack chains.

---

### Phase 12 — MeetMe room ownership + empty-room racks (done, 2026-09-27)

Two corrections to Phase 11's MeetMe room model, both raised by the user
*after* Phase 11 was already built and verified — a good example of why
"present before acting" doesn't stop applying once a phase ships; a
follow-up correction deserves the same confirm-before-building treatment
as the original request:

1. **Room ownership follows a DC-vs-PoP pattern.** Stockholm is Nordfiber's
   own datacenter, so its MeetMe rack is re-tenanted to `nordfiber-ab`
   (Phase 11 had wrongly tenanted it to Skagerrak). Gothenburg and Oslo
   are PoPs inside the *same* third-party facility, Skagerrak Interconnect
   AB. Malmo is a PoP inside a *different* facility, so it gets its own
   new facility-operator tenant, **Oresund Exchange AB** — confirmed
   explicitly by the user ("the owner of these meetme rooms are the
   providers housing Nordfiber as customers"), not assumed to be a single
   company operating every PoP.
2. **Nordfiber gets its own demarc panel in every MeetMe room**, inserted
   into the existing Phase 11 cross-connect chains rather than replacing
   anything: the tenant's MeetMe panel now jumpers to Nordfiber's MeetMe
   panel (front-to-front, both physically in the MeetMe room), which then
   trunks back to `sto-patch-01`/`got-patch-01` (rear-to-rear). Nordfiber
   is a facility customer at every PoP too, exactly like Polaris and
   Vasthamnen — it needed its own panel there, not just a pass-through.
   Where Nordfiber already owns the room (Stockholm), one panel does
   double duty as both "the room owner's panel" and "Nordfiber's demarc";
   a separate facility-operator panel there would be a pointless
   duplicate. Gothenburg/Malmo/Oslo each get two panels: the facility
   operator's own (uncabled — their own administrative presence, no
   traffic modeled through it) and Nordfiber's (cabled wherever a tenant
   already exists).

This also fixed a front/rear inconsistency left over from Phase 11: REAR
now consistently means "trunk" and FRONT means "jumper/cross-connect"
everywhere in the chain. Phase 11 had gone straight from a MeetMe-room
panel's FRONT port to a telecom-room panel's REAR port in one hop — Phase
12 splits that into a proper front-to-front jumper (within the MeetMe
room) followed by a proper rear-to-rear trunk (back to Nordfiber's
equipment room).

**A real gotcha, not a bug**: `get_or_create()` never updates an existing
object's fields — editing `MEETME_RACKS`' tenant in `config.py` alone
would NOT have fixed Stockholm's already-created rack in NetBox; it would
just keep reporting `[exists]` forever with the wrong tenant still live.
Required an explicit compare-and-`.save()` step in
`12_meetme_ownership.py`, the same pattern already used for
`device.primary_ip4` in Phases 2 and 9.

**Verified**: idempotency (0 created/updated/deleted on re-run), plus a
full `.trace()` from `polaris-sto-sw-01`'s uplink port confirming the new
5-hop path (ToR panel → tenant's MeetMe panel → **Nordfiber's new MeetMe
panel** → `sto-patch-01` → `sto-sw-01`) resolves correctly end to end.
Also confirmed `dcim.rack` works as a `ContactAssignment` object type
(untested until now in this dataset) — both facility operators' contacts
are assigned at the site, rack, *and* device level.

---

### Phase 13 — Vastkust Bredband AB's own MeetMe panel (done, 2026-09-27)

A direct, user-requested application of Phase 12's exact splitting method
to one more cable: `got-cbl-00007` (Phase 9's Internet-transit circuit
demarc, a single direct cable from the circuit termination straight to
`got-rtr-01`). Vastkust Bredband AB — Nordfiber's own upstream Internet
provider — gets its own dedicated panel in the Gothenburg MeetMe room,
cross-connected through Nordfiber's existing MeetMe panel and
`got-patch-01`, exactly like every other party at that site.

**One real modeling gap surfaced immediately**: Vastkust Bredband AB had
only ever existed as a `circuits.Provider` (since Phase 9) — but a
`Device`'s `tenant` field is a `tenancy.Tenant`, a completely different
model, so giving them an owned panel required a matching `Tenant` record
too. Solved the same way Nordfiber AB itself already works in this
dataset: the same real-world company is modeled as BOTH a Provider (the
commercial circuit relationship) AND a Tenant (device/asset ownership),
same slug, two different NetBox models for two different purposes. A new
TenantGroup, "Suppliers", was added for it — Vastkust is the opposite
commercial direction from "Customers" (Nordfiber buys transit from them,
not the other way around) and isn't a facility operator either, so
neither existing group fit.

**Labeling**: same rule as Phase 12 — the segment touching the *unchanged*
endpoint (the CircuitTermination) keeps the old label
(`got-cbl-00007`); the three newly-inserted segments each get a new one.

**Verified**: idempotency (0 created/deleted on re-run), and full
continuity confirmed by reading all 4 cables' terminations directly (the
`.trace()` convenience method pynetbox exposes on interfaces/front-rear
ports isn't available on `circuits.CircuitTermination` in this NetBox
version — 404 on the API's own `/trace/` action for that endpoint. Not a
bug: manually verifying the port-by-port equality — `got-cbl-00007`'s B
side is `got-cbl-00018`'s A side is `got-cbl-00019`'s A side is
`got-cbl-00020`'s A side — plus every panel's front/rear pair sharing the
same port number, gives the identical guarantee).

---

### Addendum, 2026-09-27: full purge-and-reload test, and a real data-corruption bug it caught

User-requested: wipe the NetBox database entirely and reload the full
13-phase sequence from scratch, specifically to catch any errors
accumulated across all the incremental add/remove/update work above.

**The literal request succeeded cleanly on the first try**: `docker
compose down`, removed the `netbox-docker_netbox-postgres` volume,
`docker compose up -d --wait` (fresh schema via NetBox's own migrations),
a new API token, a new `.secrets_userkey.pem` (the old one is invalidated
by a DB wipe — documented in README's own "Resetting" section), then
`01_organization.py` through `13_vastkust_meetme.py` in order. Zero
errors, zero warnings, every phase's own idempotency check (re-running
that same script immediately after it built) came back clean.

**A follow-up stress test — re-running the entire 01→13 sequence a SECOND
time against the already-fully-built dataset — caught a real, previously
latent bug.** `03_connections.py`'s second run threw a confusing
"duplicate termination" 400 error, but the line right before it was worse:
`[updated] cable: sto-sw-01:Ethernet2 <-> polaris-sto-srv-01:Gig-E 1 (id=44)
— label, comments, tenant`. Cable 44 is NOT that cable — it's
`sto-patch-01:Port 4 <-> sto-sw-01:Ethernet2`, the MeetMe-chain trunk
Phase 11 had already retrofitted onto that same switch interface.
`common.create_cable_if_needed()` decided "the interface already has a
cable, so this must be it" and silently overwrote a live, correct cable's
label/comments/tenant with the wrong values, before crashing on the second
endpoint (the server, now legitimately cabled to its own tenant switch
instead).

**Root cause**: the function only ever checked `a_obj.cable` for
*existence*, never verified the existing cable's far end actually matched
`b_obj`. That assumption held for 12 phases straight because nothing had
ever re-run an EARLIER script after a LATER retrofit phase changed what
its interface pointed to — this dataset's first genuine "run everything
twice" test found the gap immediately.

**Fixed in `common.py`**: a new `_verify_cable_far_end()` check runs
before any reconciliation — it confirms the existing cable's other
termination is actually `b_obj` (matching object type AND id) before
treating it as a match. If it isn't, the function now raises a clear,
actionable `SystemExit` naming the actual cable/label found and explaining
why (a later retrofit), instead of silently corrupting data. Re-verified
with a full clean rewipe + rebuild afterward: identical clean first pass
(0 errors), and the second full-sequence stress test now fails LOUDLY and
SAFELY at exactly the 5 phases that get retrofitted downstream —
`03_connections.py` (retrofitted by Phase 11), `06_wdm.py` and
`08_baltic_retail_backup.py` (retrofitted by Phase 10),
`09_gothenburg_office.py` (retrofitted by Phase 13), and
`11_colo_crossconnects.py` (retrofitted by Phase 12) — each stopping
*before* mutating anything, confirmed by reading the output: no
`[updated]` line ever precedes the error. `04`, `05`, `07`, `10`, `12`,
and `13` have nothing downstream retrofitting them, so they stay fully
idempotent even on a second full pass.

**This is a real, permanent constraint of this dataset worth knowing**:
run phases 01 through 13 in order from a clean/empty database. Re-running
an individual earlier phase script in isolation, after a later phase has
already retrofitted its cabling, is not supported — and now fails safely
with a clear message instead of corrupting data, rather than being
silently "fixed" by trying to make every retrofitted phase aware of every
possible downstream retrofit (a much larger, more fragile change that
wasn't needed to satisfy the actual request).

**Final verification on the live rebuilt database**: all 3 `WdmCircuit`s
still stitch `is_complete: true, is_active: true`; the full 5-hop Polaris
Stockholm cross-connect traces correctly end to end; 45 devices, 50
cables, all 8 tenants present (Nordfiber AB, Baltic Retail Group, Polaris
Cloud Services, Vasthamnen Logistics, Fjord Media Networks, Skagerrak
Interconnect AB, Oresund Exchange AB, Vastkust Bredband AB).

---

### Phase 14 — full 40-channel WDM plan (done, 2026-09-27)

User-requested: populate every available channel on each WDM terminal
mux, not just the 2 that happen to be lit (Fjord Media on grid_position 1,
Baltic Retail's backup on grid_position 2). The muxponder device type
genuinely has 40 channel front ports (confirmed live: `921` through
`960`), so this gives all 6 existing WDM nodes their real, full capacity.

**A real, wrong assumption from Phase 8 got caught and corrected here.**
Phase 8's own comment claimed "adding this to the existing profile means
sto-wdm-01/osl-wdm-01 also gain an unused channel-2 slot" — reasonable-
sounding, but never actually verified at the time, and wrong: adding
grid_position 3-40 to the shared `WdmProfile` did NOT retroactively give
any pre-existing node a matching `WdmChannel`. Confirmed directly: right
after adding all 38 new channel-plan entries, every node still showed only
its original 1-2 channels. The real behavior — a node's `WdmChannel`s are
built once, at DEVICE CREATION time, from whatever channel-plan entries
exist on the profile *at that moment* — there's no live signal that
ripples a later profile change out to already-existing nodes.

**Fixed by creating the missing `WdmChannel` objects directly**, one POST
per (node, grid_position) pair, each pointing at that node's own
already-instantiated front port (e.g. `"923"` for grid_position 3, not a
device-type template). Confirmed this still gets the plugin's real
computed ITU wavelength/label, identical to a channel created via normal
device creation (spot-checked: posting grid_position 2 with no
`wavelength_nm` came back `"C22 (1559.79nm)"`, matching the value already
seen elsewhere for that same grid_position). ~230 individual creates
across 6 nodes.

**Verified**: every node now has exactly 40 `WdmChannel`s (240 total,
confirmed by direct count); idempotent (0 created on re-run); the 3
already-lit `WdmCircuit`s (Fjord Media, both Baltic Retail Group backup
segments) all still stitch `is_complete: true, is_active: true` —
populating 38 additional unlit channels per node didn't disturb any
existing service.

---

### Phase 15 — Baltic Retail Group capacity upgrade, 1 Gbps -> 10 Gbps (done, 2026-09-30)

User-requested. Upgraded both `NF-BRG-0001` (primary) and `NF-BRG-0002`
(backup) so the backup still fully covers the primary. No physical
rewiring: checked live first that both circuits already land on 100GE
QSFP28 ports (`et-0/0/0`/`et-0/0/1` on the Juniper MX204s) regardless of
the configured commit rate. Two fields needed reconciling per circuit —
`Circuit.commit_rate` AND each `CircuitTermination.port_speed`, set
independently at creation time in Phases 4/8 — both fixed explicitly
(`get_or_create()` still never updates existing objects). Verified
idempotent.

### Phase 16 — Gothenburg PoP -> Datacenter (done, 2026-09-30)

User-requested, confirmed to include real new capacity, not just a
classification change. Site renamed to "Nordfiber Gothenburg DC",
SiteGroup -> Data Centers — but the site's slug
(`nordfiber-gothenburg-pop`) and every `got-*`/`gothenburg-pop`-prefixed
Location/Rack/Device slug elsewhere in this dataset were deliberately left
unchanged, to avoid an invasive, purely-cosmetic rename touching 9+
phases' worth of config for no functional gain. New growth capacity
added: a "Suite 200" / "Row C" Location with 2 new empty racks — real
datacenters carry spare white space, unlike a lean PoP; left unpopulated
since no new tenant or service was requested. Same `get_or_create()` field
gotcha as Phase 15 — the Site's name/group/description needed an explicit
compare-and-save, since `01_organization.py`'s own `SITES` loop already
ran once with the old values.

### Phase 17 — Helsinki DC + dual leased dark fiber to Stockholm (done, 2026-09-30)

User-requested: a third, smaller Nordfiber-owned datacenter (Finland — a
new Region, alongside Sweden/Norway), built the same way as Malmo/Oslo
(one rack, router, switch, patch panel), reached from Stockholm over two
independently-routed leased dark fiber pairs from two different vendors.
Four points were confirmed with the user before building any of it: dark
fiber lit later (not part of this phase) vs. already-lit; primary+backup
vs. active/active; real geographic route data vs. text description; and
that two new fictional providers were needed (**Nordic Subsea Networks
AB**, the shorter Mariehamn/Vaasa route, designated primary; **Baltic
Fibre Networks OU**, the longer Gotland/Riga/Tallinn route, designated
backup).

Both circuits are uncabled at both ends, exactly like the existing
`PLT-100234` (Stockholm<->Oslo) — no new NetBox Sites were created at the
route waypoints either, since Nordfiber has no actual equipment at
Mariehamn, Vaasa, Gotland, Riga, or Tallinn, just transit fiber passing
through.

**The real route geography uses the netbox-pathways plugin adopted
earlier this session** — specifically its `circuit-geometries` endpoint,
which attaches a real multi-point LineString directly to a `Circuit`
object. This is the right-sized fit for "here is the actual route": it
gives genuine, queryable geographic data without building out full
conduit/duct-bank physical plant (`pathways`/`structures`/`direct-buried`
etc.), which nothing here called for. Verified at the PostGIS level, not
just via the API: `ST_AsText`/`ST_SRID` confirm real `LINESTRING` geometry
at SRID 4326 for both routes, and `ST_Length(path::geography)` gives
genuinely plausible real-world distances — 851.7km for the primary route,
909.6km for the backup — which correctly makes the backup the longer,
more diverse path, exactly as designated.

---

### Phase 18 — real route geography for the domestic backbone fiber (done, 2026-09-30)

User-requested, immediate follow-up to Phase 17: give the 3 ORIGINAL
backbone cables (Phase 5) the same real-route treatment, now that the
pattern exists. These are physical `dcim.Cable`s (FMS `FiberCable`s), not
`circuits.Circuit` objects, so Phase 17's `circuit-geometries` shortcut
doesn't apply — this needed a different part of netbox-pathways, verified
empirically with a throwaway pilot object before building anything real:

- A route's geometry lives on its own object — a `DirectBuried` pathway
  here (fiber genuinely buried alongside a road corridor, the realistic
  choice over `aerial-spans`/`conduit-banks`), which carries the `path`
  LineString directly, same shape as `Pathway` itself (confirmed:
  `pathway_type` comes back read-only, auto-set to `direct_buried`).
- A separate `CableSegment` join object is what actually links that route
  to a real `Cable` — confirmed live that creating one bumps the
  pathway's own `cables_routed` counter from 0 to 1, and that
  `cable-segments`' `pathway` field accepts a `DirectBuried` object's ID
  directly (shared ID space via multi-table inheritance under one
  `Pathway` base, not a separate lookup).

Routes exactly as given by the user: `bb-cbl-00001` (Stockholm<->
Gothenburg) via Vasteras/Orebro/Karlstad/Tanumshede — followed as
specified even though it's not the shortest real route (that would go via
Orebro/Skovde) — `bb-cbl-00002` (Stockholm<->Malmo) via the E4 through
Linkoping/Jonkoping/Markaryd/Hassleholm/Lund, and `bb-cbl-00003`
(Gothenburg<->Oslo) along the E6. That last one had no named waypoints in
the request ("along the E6 road"), so Uddevalla and Stromstad — the two
real, well-known towns the E6 actually passes through on the Swedish
side — were added for a route of comparable fidelity to the other two,
rather than a bare 2-point line.

**Verified at the PostGIS level**: all 3 pathways are real `LINESTRING`
geometry at SRID 4326, each correctly joined to its own cable via
`CableSegment`, with plausible real-world lengths (`bb-cbl-00001`:
536.9km; `bb-cbl-00002`: 554.2km; `bb-cbl-00003`: 262.3km) — consistent
with `bb-cbl-00001`'s longer, non-direct routing. Idempotent (0 created on
re-run).

**Addendum, 2026-09-30: route edit, and a reconciliation gap it caught.**
User-requested: swap Tanumshede for Trollhattan on `bb-cbl-00001`. The
script as originally written only checked whether a pathway with the
right label *existed* — like `get_or_create()` everywhere else in this
project, it never re-checked an existing one's fields, so simply editing
`config.py`'s waypoints would have done nothing to the live pathway.
Unlike most objects in this dataset, though, a route genuinely CAN change
after the fact (an editorial correction, not a topology change), so
`18_backbone_pathways.py` was fixed to explicitly reconcile an existing
pathway's `path` and `comments` against config — comparing
`pathway.path.coordinates` (pynetbox unwraps the nested GeoJSON cleanly
to a plain list of `[lon, lat]` pairs, confirmed live) against the
expected coordinate list, and only re-saving `path`/`comments` when they
actually differ. Re-ran cleanly: only `bb-cbl-00001`'s pathway updated
(`path, comments`), the other two correctly reported `[exists]`. New
route length via Trollhattan: 481.3km, down from 536.9km — shorter and
more direct, matching that Trollhattan sits much closer to the
Stockholm-Gothenburg corridor than Tanumshede did.

---

### Phase 19 — Helsinki MeetMe room + lighting the two leased dark fiber pairs (done, 2026-10-01)

Two real gaps the user found while reviewing live data: Helsinki never
got a MeetMe room (every other site has one since Phase 11/12, but
Helsinki didn't exist yet then), and the two dark fiber circuits from
Phase 17 were still dark, as planned, but never actually lit. Both fixed
here, plus a genuinely new upstream limitation found along the way.

**Confirmed with the user before building**: Helsinki's MeetMe room is
Nordfiber-owned (like Stockholm — it's Nordfiber's own datacenter, not a
colocation PoP), and — since a leased fiber pair has two physical ends —
each vendor (Nordic Subsea Networks AB, Baltic Fibre Networks OU) gets its
own demarc panel at BOTH Stockholm and Helsinki, not just Helsinki as
first described. Same gap as Vastkust Bredband AB in Phase 13: both
vendors only existed as `circuits.Provider` records, so each needed a
matching `tenancy.Tenant` too, to own a `Device`.

**A real architectural bug caught by testing, not assumed correct**: the
first build attempt cabled the leased fiber straight through the Circuit's
own `CircuitTermination` objects (`CircuitTermination <-> vendor panel`).
Running the WDM channel's own `/trace/` action came back completely
empty, which led to checking the established precedent directly:
`PLT-100234`'s both terminations have `cable=None`, and the dark fiber it
represents is physically modeled as `bb-cbl-00003` — one direct
`dcim.Cable` connecting the two patch panels' rear ports, with NO
involvement of the CircuitTermination objects in the physical cable graph
at all. A commercial Circuit in this dataset is a billing/contractual
record, deliberately kept separate from physical connectivity. Fixed to
match: the CircuitTerminations stay uncabled, and the real long-haul span
is one direct `dcim.Cable` between the two vendor panels
(`nsn-cbl-00001`, `bfn-cbl-00001`), tenanted to the vendor, matching how
`bb-cbl-00003` itself is modeled.

**A second, genuinely new upstream limitation, found verifying the fix**:
even with the physical model corrected to match precedent, `/trace/` on
`sto-wdm-03`/`sto-wdm-04`'s channel 1 still comes back completely empty —
`is_complete: false`, `elements: []`, `wavelength_path_id: null`. Checked
at the SQL level to rule out the already-known duplicate-path bug: zero
rows in `netbox_wdm_wdmwavelengthpathchannel` reference either new
channel at all — not a duplicate, nothing. Meanwhile the physical cabling
was verified 100% correct and continuous by hand, port by port, across
all 7 segments. The one genuinely novel thing about this topology vs.
every other lit path in this dataset: it's the first Line-side physical
path to route through a front-port-to-front-port cable (the two
MeetMe-room "jumper" hops) — every prior lit path (Oslo, the Baltic
Retail backup) uses exactly one intermediate patch panel per hop, relying
on that panel's own built-in front↔rear template mapping to pass through,
never a direct front-to-front cable between two *different* panels. Best
explanation: netbox-wdm's path walker assumes that single-panel-
passthrough shape and doesn't know how to continue past a front port
that's cabled directly rather than via its own device's rear-port
mapping. Not treated as a reason to re-architect the physical model —
the cabling already matches this dataset's own established MeetMe-room
conventions exactly, and is objectively correct — this is a plugin
display/computation limitation, same category as the already-documented
`sync-ports` 500 error and the duplicate-wavelength-path bug. Verified
via manual cable-chain inspection instead (confirmed port-by-port
continuity for both circuits' full 7-segment chains).

**Design decision, flagged rather than assumed**: each new wavelength's
client handoff goes straight from the muxponder's channel port to a spare
100GE port on the local router (`sto-rtr-01`/`hel-rtr-01`), NOT through
the Phase 10 DCP-2/DCP-110 client shelf — that shelf exists specifically
to hand a grey optic to an *external* customer; these two links are
Nordfiber's own internal backbone connectivity between its own routers,
so no customer-facing demarc applies. Not confirmed with the user; easy
to add a DCP-110 hop later if wanted.

**Verified**: idempotent (0 created on re-run); all 20 new cables'
continuity confirmed by direct port-by-port inspection; the 3
pre-existing `WdmCircuit`s (Fjord Media, both Baltic Retail Group backup
segments) all still stitch `is_complete: true, is_active: true` — the new
topology caused zero regression to what already worked.

---

### Addendum, 2026-10-02: `bb-cbl-00003` route corrected, and a data audit

The user asked for an honest audit of the live data for consistency. It was
done against the live instance (not from memory) and found, among other
things, a mistake of mine: `bb-cbl-00003` is physically Stockholm<->Oslo
(`sto-patch-01` to `osl-patch-01`), but in Phase 18 it was given a
Gothenburg->E6->Oslo geometry because that is what the request said, and
the contradiction wasn't flagged. It is now Stockholm -> Vasteras -> Orebro
-> Karlstad -> Charlottenberg -> Oslo (the E18 corridor, 449.2km, verified
at the PostGIS level), as the user then specified. The audit also found
errors in `docs/INFRASTRUCTURE.md` (claimed all four backbone cables had
route geometry, `bb-cbl-00004` has none; said six WDM devices above a table
of ten) — fixed. Audit findings the user has not yet decided on (cable
type/length/color, Helsinki parity, redundant routers, Gothenburg customer
racks in the Telecom Room, naming/FMS/pathway inconsistencies, stale text)
are deliberately untouched. Power modeling was ruled out of scope.

### Phase 20 — uniform rack layout + out-of-band management (done, 2026-10-02)

Every rack of the same kind now has the same top-down layout (core racks:
patch panel U42, OOB switch U39, router/switch U36/35, WDM from U32, DCP-2
at a fixed U28; customer racks: ToR panel, tenant switch, servers; MeetMe
racks: Nordfiber's panel, the owner's panel, then external parties), with
2U gaps between kinds of equipment. Moves are done in two passes (park in
free low slots, then final slot) so a move never collides with a device
that hasn't moved yet. The audit had found 48 management-only interfaces,
none cabled, and no OOB hardware; added one 48-port copper OOB switch per
site (Arista DCS-7010T-48, already in the dataset, new "OOB Switch" role)
with the same port plan everywhere, one management port per device cabled
(Cat6, 32 devices, including colo tenants' gear — Phase 2's premise is that
Nordfiber provides OOB to colo tenants — and the Gothenburg IDF switch over
a riser), plus a 10GE DAC uplink to each site router. Scope calls flagged
rather than asked: DCP-2 chassis have five management ports, only
`if-1/eth1` is cabled (not the craft port); each OOB switch's own
`Management1` is left uncabled; serial console is not modeled. Cable labels
continue each site's numbering (earlier gaps not back-filled). Verified:
idempotent, all 32 devices with a management port cabled, all 3 WDM
circuits still stitch complete. Device moves and OOB cabling did not
regrow the wavelength-path table (stayed at 240 until Phase 22).

### Phase 21 — asset identity (done, 2026-10-02)

All devices lacked serials and asset tags. Serial `<MFR>-<SITE>-<nnnn>` on
every device; asset tag `NF-<SITE>-<nnnnn>` only on Nordfiber-owned devices
(41 of 62) — a colo tenant's server or a vendor's panel isn't Nordfiber's
asset. Numbering continues from the highest existing value, so a later
device never renumbers an old one. Linking installed gear to
netbox-inventory assets was left out (the plugin only models spares here).
Verified: no duplicates, idempotent.

### Phase 22 — wavelength path prune (done, 2026-10-02)

netbox-wdm's duplicate-path bug (Phase 6) had been multiplied by Phase 14,
which gave every node 40 channels: 240 `WdmWavelengthPath` rows, 3 of them
real (attached to a `WdmCircuit`). Deleted the 237 unattached ones —
plugin-derived rows, not source data — and re-verified all three circuits
still stitch complete/active. The script refuses to run if no circuit has
an attached path, and re-checks stitching after deleting. It must run last:
any later cable save on WDM topology can regrow the rows; re-run it.

---

## Status

Built by the layered scripts (`build.py`): 5 sites, 18 racks, 85 devices,
142 cables, 6 circuits, 5 fiber circuits, 3 wavelength services, with
`verify.py` (52 checks) passing on a fresh replay. See `README.md` for usage and `docs/INFRASTRUCTURE.md` for the
finished dataset. What was deliberately left out is listed in `README.md`
under "Not modeled, on purpose".
