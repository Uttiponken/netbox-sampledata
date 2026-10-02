# Nordfiber AB — Physical Infrastructure

What connects to what, over what, between Nordfiber's own sites. This is a
snapshot of the live dataset as of 2026-10-02 (Phase 22) — see
`docs/DESIGN.md` for the phase-by-phase build log and every design
decision/bug behind how it got this way.

## TL;DR

- **5 sites**: two full datacenters Nordfiber owns outright — **Stockholm**
  (HQ) and **Gothenburg** (upgraded from a PoP, Phase 16) — a third,
  smaller owned datacenter in **Helsinki**, Finland (Phase 17–19), and two
  leaner points of presence, **Malmö** and **Oslo** (Norway — the one
  cross-border site).
- **Physical layer**: Stockholm is the hub. Three Nordfiber-owned fiber
  pairs radiate from it — to Gothenburg, to Malmö, and to Oslo (the Oslo
  pair is itself on *leased* glass from Polarlink Transit, but Nordfiber
  physically manages it as its own cable). A fourth Nordfiber-owned pair
  connects Gothenburg↔Malmö directly. Helsinki is reached by two
  *independent* leased dark fiber pairs from two different vendors, on
  two geographically disjoint routes, specifically for path diversity.
- **Transport**: everything between sites is dark fiber at the physical
  layer; DWDM (SmartOptics DCP‑M40‑PAM4‑ER muxponders, 40 channels each)
  lights specific wavelengths on top where a service actually needs
  inter-site bandwidth. Every muxponder in the fleet has its full
  40-channel capacity provisioned; only a handful of channels are
  actually lit.
- **Demarc architecture**: every site has its own MeetMe/cross-connect
  room. At Stockholm and Helsinki (Nordfiber's own buildings) Nordfiber
  owns that room; at Gothenburg and Oslo it's leased space inside a
  third-party facility (Skagerrak Interconnect AB); at Malmö, a *different*
  third-party operator (Oresund Exchange AB). Every external party
  (colo tenant, fiber vendor, the Internet upstream) gets its own demarc
  panel there — nothing lands directly on Nordfiber's own rack gear.
- **What's actually lit today**: Fjord Media Networks' wavelength service
  (Stockholm↔Oslo), Baltic Retail Group's protected EPL (Stockholm↔Malmö
  primary + a DWDM-regenerated backup via Gothenburg), and Nordfiber's own
  internal backbone link to Helsinki over both leased pairs.
- **Real geography**: the three long domestic cables (Stockholm to
  Gothenburg, Malmö and Oslo) and both Helsinki leased pairs have real PostGIS
  LineString routes via the netbox-pathways plugin, following the actual
  roads/towns each runs along. The short Gothenburg↔Malmö pair
  (`bb-cbl-00004`) does not have one yet.
- **Uniform racks, cabled management**: every site's core rack has the same
  top-down layout, and every device's management port is cabled to a
  per-site OOB switch (§7).

---

## 1. Sites

| Site | Role | Owner of the building | Region |
|---|---|---|---|
| Nordfiber Stockholm DC | Datacenter (HQ) | Nordfiber AB (owns outright) | Sweden |
| Nordfiber Gothenburg DC | Datacenter (upgraded from PoP, Phase 16) | Nordfiber AB owns its own suite; the **MeetMe room specifically** is leased space inside a building operated by **Skagerrak Interconnect AB** | Sweden |
| Nordfiber Malmö PoP | Point of presence | Nordfiber AB owns its own suite; MeetMe room is leased space operated by **Oresund Exchange AB** | Sweden |
| Nordfiber Oslo PoP | Point of presence (cross-border) | Nordfiber AB owns its own suite; MeetMe room is leased space operated by **Skagerrak Interconnect AB** (same operator as Gothenburg) | Norway |
| Nordfiber Helsinki DC | Datacenter (smaller footprint) | Nordfiber AB (owns outright, including its MeetMe room) | Finland |

Stockholm and Gothenburg are classified "Datacenter" (Nordfiber's own
facility, multiple suites, room to grow — Gothenburg specifically got a
second empty expansion row, Suite 200/Row C, in Phase 16). Malmö and Oslo
remain leaner single-suite PoPs. Helsinki is deliberately smaller than
Stockholm — one rack of core infrastructure plus a MeetMe room — but still
classified as a Datacenter since Nordfiber owns the space outright, unlike
the colocation arrangement at Gothenburg/Malmö/Oslo.

## 2. Domestic backbone fiber (Nordfiber-owned)

Four fiber pairs, all terminating on each site's own LC patch panel
(`<site>-patch-01`, a real 24-port Corning-compatible panel, Phase 5),
decorated as `fms.FiberCable` objects with real buffer-tube/strand
auto-instantiation:

| Cable | Route | Real-world path |
|---|---|---|
| `bb-cbl-00001` | Stockholm ↔ Gothenburg | Västerås → Örebro → Karlstad → Trollhättan (481km) |
| `bb-cbl-00002` | Stockholm ↔ Malmö | E4 via Linköping → Jönköping → Markaryd → Hässleholm → Lund (554km) |
| `bb-cbl-00003` | Stockholm ↔ Oslo | Västerås → Örebro → Karlstad → Charlottenberg → Oslo, the E18 corridor (449km). *Leased from Polarlink Transit* (circuit `PLT-100234`) — the physical glass Nordfiber manages as its own cable even though the underlying fiber is leased |
| `bb-cbl-00004` | Gothenburg ↔ Malmö | Direct pair, added in Phase 8 for the Baltic Retail Group backup path. No route geometry yet |

`bb-cbl-00003` is the one cable in this layer that's commercially a lease
rather than Nordfiber-owned glass — see §3 for how that distinction is
modeled (a Cable represents physical connectivity; a Circuit represents
the commercial relationship, and the two are deliberately *not* the same
object).

`bb-cbl-00001`, `-00002` and `-00003` have real PostGIS route geometry
(`netbox-pathways` `DirectBuried` pathways, one per cable, joined via
`CableSegment` — Phase 18). `bb-cbl-00003` was first built with the wrong
route (Gothenburg→E6→Oslo, contradicting a cable that physically runs
Stockholm↔Oslo) and was corrected on 2026-10-02. `bb-cbl-00004` has no
route yet, and the two Helsinki spans carry their geometry on the
*circuit* (`circuit-geometries`) rather than on the cable — an
inconsistency in how routes are attached, not yet resolved.

## 3. International leased fiber: Helsinki

Helsinki is reached over **two independent leased dark fiber pairs from
two different vendors**, deliberately routed through different countries
for genuine physical path diversity — confirmed design intent, not an
accident of two vendors happening to exist:

| Circuit | Vendor | Role | Route | Distance |
|---|---|---|---|---|
| `NSN-DF-0001` | Nordic Subsea Networks AB | **Primary** (shorter) | Stockholm → Mariehamn (Åland) → Vaasa → Helsinki | 852km |
| `BFN-DF-0001` | Baltic Fibre Networks OÜ | **Backup** (longer, more diverse) | Stockholm → Visby (Gotland) → Riga (Latvia) → Tallinn (Estonia) → Helsinki | 910km |

Both have real `circuit-geometries` LineString geometry (Phase 17),
verified at the PostGIS level (`ST_Length(path::geography)` matches the
table above).

**Physical modeling, confirmed against this dataset's own established
precedent** (`PLT-100234`/`bb-cbl-00003`): the commercial `Circuit` object
for each lease is a billing/contractual record only — both its
`CircuitTermination`s are deliberately left **uncabled**. The actual
physical fiber span is one direct `dcim.Cable` per circuit
(`nsn-cbl-00001`, `bfn-cbl-00001`), connecting the two vendors' own demarc
panels — one in Stockholm's MeetMe room, one in Helsinki's — exactly the
way `bb-cbl-00003` connects two patch panels for the Oslo lease. The first
build attempt got this backwards (cabled through the CircuitTermination
objects instead); caught by testing, not assumed correct — see
`docs/DESIGN.md` Phase 19 for the full story.

## 4. DWDM transport layer

Ten WDM terminal devices exist today, all the same real hardware
(SmartOptics DCP‑M40‑PAM4‑ER, a 40-channel terminal mux — not a ROADM, a
fact that matters below):

| Node | Site | Serves |
|---|---|---|
| `sto-wdm-01` | Stockholm | Fjord Media wavelength service (ch. 1, →Oslo) |
| `osl-wdm-01` | Oslo | Fjord Media wavelength service (ch. 1, →Stockholm) |
| `sto-wdm-02` | Stockholm | Baltic Retail backup, segment 1 (ch. 2, →Gothenburg) |
| `got-wdm-01` | Gothenburg | Baltic Retail backup, segment 1 (ch. 2, from Stockholm) |
| `got-wdm-02` | Gothenburg | Baltic Retail backup, segment 2 (ch. 2, →Malmö) |
| `mma-wdm-01` | Malmö | Baltic Retail backup, segment 2 (ch. 2, from Gothenburg) |
| `sto-wdm-03` | Stockholm | Nordfiber's own backbone link to Helsinki, primary route (ch. 1) |
| `hel-wdm-01` | Helsinki | Nordfiber's own backbone link to Stockholm, primary route (ch. 1) |
| `sto-wdm-04` | Stockholm | Nordfiber's own backbone link to Helsinki, backup route (ch. 1) |
| `hel-wdm-02` | Helsinki | Nordfiber's own backbone link to Stockholm, backup route (ch. 1) |

Every one of these nodes has all **40 channels** provisioned (Phase 14) —
only the ones listed above are actually cabled through to a client. The
rest is real spare capacity, not a cosmetic placeholder: each unused
channel has its own correctly-computed ITU wavelength and its own channel
front port, ready to be cross-connected the day a new service needs one.

**Why Stockholm has four separate WDM chassis instead of one with four
lit channels**: a protect/backup path sharing its primary's physical
muxponder would defeat the point of protection — a single chassis
failure would take out both. `sto-wdm-01`/`sto-wdm-02` (Oslo service +
Baltic Retail backup) and `sto-wdm-03`/`sto-wdm-04` (the two independent
Helsinki routes) are each on their own hardware for exactly this reason.

**Why Gothenburg has two WDM nodes just to relay one wavelength**: the
muxponder is a terminal mux, not a ROADM — it can terminate a wavelength,
not pass one through a site optically. Relaying Stockholm→Malmö via
Gothenburg means terminating the first segment's wavelength electrically
and regenerating it into a second, independent wavelength for the second
segment: `got-wdm-01` and `got-wdm-02`, client-port to client-port
jumpered (`got-cbl-00004`). `/stitch/` correctly reports this as **two**
separate complete paths, not one continuous Stockholm↔Malmö path — that's
the accurate representation of regenerated transport, not a bug.

**Client handoffs — two different patterns, by design**: wavelength
services with an *external* customer at the end (Fjord Media, Baltic
Retail) hand off through a SmartOptics DCP‑2 chassis + DCP‑110 module
(Phase 10) at each site — this converts the muxponder's own channel port
into a plain grey 10G port for the customer, rather than making them
patch directly into colored DWDM optics. Nordfiber's own internal
backbone link to Helsinki skips that shelf and hands off straight to a
spare 100GE port on the local router (`sto-rtr-01`/`hel-rtr-01`) — no
external customer demarc is needed for Nordfiber's own infrastructure
traffic. (Flagged in `docs/DESIGN.md` as a judgment call, not separately
confirmed — trivial to add a DCP-110 hop later if these links are ever
meant to also serve an external customer.)

**A known upstream limitation, not a data error**: netbox-wdm's own
`/trace/` action returns empty for the two new Helsinki channels
(`sto-wdm-03`/`sto-wdm-04`, channel 1), even though the physical cabling
was verified completely correct and continuous by hand, port by port,
across all 7 segments per circuit. This is the first lit path in the
dataset to route through a front-port-to-front-port cable (the MeetMe
room's cross-connect jumpers, §5) rather than a single patch panel's
built-in front↔rear mapping — netbox-wdm's path walker appears not to
support that shape. See `docs/DESIGN.md` Phase 19 for the full
investigation (including SQL-level confirmation that this isn't the
already-known duplicate-path bug). Verify these two paths by reading the
cable chain directly rather than trusting the plugin's own trace result. Separately, netbox-wdm's duplicate-path bug had grown the wavelength-path table to 240 rows (3 real); Phase 22 prunes every path not attached to a `WdmCircuit`, and must be re-run after any later cable change on WDM topology.

## 5. MeetMe / cross-connect rooms

Every site has a dedicated MeetMe room — a Location and rack physically
separate from the site's own telecom-room equipment — where every
external party gets its own demarc panel. Nobody external lands directly
on Nordfiber's own rack gear.

| Site | Room owner | Panels present |
|---|---|---|
| Stockholm | **Nordfiber AB** | Nordfiber's own (`sto-mmr-nordfiber-01`), Polaris Cloud Services (colo), Nordic Subsea Networks AB, Baltic Fibre Networks OÜ |
| Gothenburg | **Skagerrak Interconnect AB** | Nordfiber's own, Skagerrak's own, Polaris Cloud Services (colo), Västhamnen Logistics (colo), Vastkust Bredband AB (Internet transit) |
| Malmö | **Oresund Exchange AB** | Nordfiber's own, Oresund's own |
| Oslo | **Skagerrak Interconnect AB** | Nordfiber's own, Skagerrak's own |
| Helsinki | **Nordfiber AB** | Nordfiber's own, Nordic Subsea Networks AB, Baltic Fibre Networks OÜ |

The room-ownership split follows a simple rule: Stockholm and Helsinki are
buildings Nordfiber owns outright, so Nordfiber owns the MeetMe room
itself. Gothenburg and Oslo happen to colocate in buildings run by the
same third-party operator (Skagerrak); Malmö's building has a different
landlord (Oresund Exchange) — not every PoP shares one.

**Cross-connect physical pattern** (confirmed by this dataset's own
convention, applied consistently everywhere a party crosses from their
own equipment into Nordfiber's network): REAR ports carry trunk runs
(between rooms, or the actual leased fiber spans in §3), FRONT ports
carry jumpers (the working-side patch within a room). A typical colo
tenant's path, for example:

```
tenant server -> tenant's own switch -> tenant's ToR panel (in their own rack)
  --[trunk]--> tenant's MeetMe panel
  --[jumper]--> Nordfiber's MeetMe panel
  --[trunk]--> Nordfiber's own patch panel (telecom room)
  --[jumper]--> Nordfiber's switch/router
```

The two Helsinki WDM links (§4) use the identical pattern end to end,
just with a muxponder instead of a router/switch at the inner end, and
the vendor's own long-haul fiber span (§3) standing in for the
tenant-side "trunk" leg.

## 6. Commercial circuits riding on this infrastructure

| Circuit | Customer / purpose | Physical path | Commit rate |
|---|---|---|---|
| `NF-BRG-0001` | Baltic Retail Group — primary EPL | Direct, Stockholm↔Malmö (`bb-cbl-00002`) | 10 Gbps |
| `NF-BRG-0002` | Baltic Retail Group — backup/protect | DWDM via Gothenburg, regenerated (§4) | 10 Gbps |
| `PLT-100234` | Nordfiber's own leased dark fiber (Polarlink Transit) | Stockholm↔Oslo, lit as Fjord Media's service | — (dark fiber lease) |
| `VKB-INET-0001` | Nordfiber's own upstream Internet transit (Vastkust Bredband AB) | Single-sided (A-side only — the provider's own network isn't Nordfiber's to document), via Gothenburg's MeetMe room | 10 Gbps |
| `NSN-DF-0001` | Nordfiber's own leased dark fiber (Nordic Subsea Networks AB) | Stockholm↔Helsinki, primary route, lit for internal backbone use | — (dark fiber lease) |
| `BFN-DF-0001` | Nordfiber's own leased dark fiber (Baltic Fibre Networks OÜ) | Stockholm↔Helsinki, backup route, lit for internal backbone use | — (dark fiber lease) |

Fjord Media Networks' own wavelength service is modeled as a
`netbox-wdm` `WdmCircuit` (not a `circuits.Circuit`) riding on top of the
`PLT-100234` dark fiber lease — the commercial relationship with Fjord
Media and the physical/commercial lease from Polarlink are two separate
objects, same separation of concerns as everywhere else in this document.

## 7. Rack layout and out-of-band management

**Uniform rack layout (Phase 20).** The same kind of device sits at the same
height at every site, with 2U gaps between kinds of equipment so more can be
added later (NetBox position 42 is the top):

| Rack kind | Top to bottom |
|---|---|
| Core rack (`<SITE>-RACK-A1/1`) | U42 fiber patch panel · U39 OOB switch · U36 router, U35 switch · U32 and down WDM terminals · U28 DCP-2 shelf (fixed, so it lines up everywhere) |
| Colo customer rack | U42 top-of-rack fiber panel · U39 tenant switch · U36 and down servers |
| MeetMe rack | U42 Nordfiber's panel · U41 the facility owner's own panel (where it isn't Nordfiber) · U38 and down external parties |

**Out-of-band management (Phase 20).** Each site has one 48-port copper OOB
switch (`<site>-oob-01`, Arista DCS-7010T-48) in the core rack, with the same
port plan everywhere: Ethernet1 router, 2 switch, 3–6 WDM terminals, 7 DCP-2,
8 and up everything else. One management port per device is cabled to it
(Cat6): 32 devices in all, including the colo tenants' servers and switches —
Nordfiber provides OOB access to colo tenants as a service — and the
Gothenburg IDF switch over a copper riser. Each OOB switch has a 10GE DAC
uplink to its site router (`xe-0/1/2`). Each OOB switch's *own* management
port is deliberately left uncabled; it is reached through that uplink.
Serial console access, power, and IP addressing of the OOB network are not
modeled.

**Asset identity (Phase 21).** Every device has a serial (`<MFR>-<SITE>-<nnnn>`);
Nordfiber-owned devices also have an asset tag (`NF-<SITE>-<nnnnn>`).
Tenant- and vendor-owned gear carries a serial but no Nordfiber tag.

## 8. What's deliberately not covered here

This document is about physical inter-site infrastructure specifically.
It does not cover: the full per-device inventory (see `README.md`'s
phase table and `docs/DESIGN.md` for that level of detail), the iBGP
mesh and IP addressing plan (Phase 7), encrypted device credentials
(Phase 7), or inventory/spares (Phase 7). See `README.md`'s "Possible
future extensions" for what's intentionally not built yet, including a
second WDM customer at Oslo and whether the Helsinki links should ever
grow a DCP-110 customer-facing shelf.
