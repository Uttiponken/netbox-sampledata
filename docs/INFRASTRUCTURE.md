# Nordfiber AB — Physical Infrastructure

What the finished dataset looks like: what connects to what, over what, and
how it is named and cabled. This describes the build produced by
`build.py` (layers 1–7); `docs/DESIGN.md` has the rationale and history.

## TL;DR

- **5 sites, 18 racks, 85 devices, 142 cables, 6 circuits.** Three
  datacenters Nordfiber owns — **Stockholm** (HQ), **Gothenburg**,
  **Helsinki** — and two points of presence, **Malmö** and **Oslo** (the
  cross-border one).
- **Datacenters are built in redundant pairs** (router/switch 01 and 02 in
  the same rack, cross-connected); PoPs have a single pair with the slots
  for the second one kept free. Every site otherwise has the same
  equipment in the same rack slots.
- **Stockholm is the physical hub.** Three 24-pair fiber trunks radiate from it to
  Gothenburg, Malmö and Oslo (the Oslo trunk is leased glass, managed as
  Nordfiber's own cable); Gothenburg–Malmö has a fourth. Helsinki is
  reached over two independent leased 24-pair trunks from two vendors on
  geographically disjoint routes.
- **Every panel-to-panel connection is a 24-pair trunk**: one cable (48 fibers)
  between two patch panels, each with 24 duplex LC ports on the front and one
  rear port "Trunk" with 24 positions. There is one panel per trunk.
- **Everything between sites is dark fiber**; DWDM (SmartOptics
  DCP-M40-PAM4-ER muxponders, 40 channels each) lights the wavelengths that
  need bandwidth.
- **Every external party lands on its own demarc panel** in the site's
  MeetMe room; nothing external lands on Nordfiber's own rack gear.
- **Every cable has a type, colour, length, label and per-end labels**;
  every device a serial (Nordfiber's own also an asset tag); every
  management port is cabled to the site's OOB switch.
- **All six long-haul cables have a real-world route** (netbox-pathways) and
  a fiber-plant record (netbox-fms).

---

## 1. Naming convention

One scheme everywhere (it lives in `naming.py`):

| Thing | Pattern | Example |
|---|---|---|
| Site | `Nordfiber <City> DC` / `PoP` | Nordfiber Gothenburg DC |
| Room (one Location each) | Telecom Room, MeetMe Room, Colo Hall, IDF Floor 3, Office Floor 3 | |
| Rack | `<SITE>-<ROOM>-<NN>` | `STO-TR-01`, `GOT-MM-01`, `GOT-CH-02` |
| Nordfiber device | `<site>-<role>-<NN>` | `sto-rtr-01`, `hel-oob-01`, `got-wdm-02` |
| Tenant device | `<tenant>-<site>-<role>-<NN>` | `polaris-sto-sw-01` |
| MeetMe panel | `<site>-mmr-<party>-01` | `got-mmr-vastkust-01` |
| Telecom-room trunk panel | `<site>-patch-<to>-01`, `<to>` = `mmr` or the site the trunk goes to | `sto-patch-mmr-01`, `sto-patch-got-01` |
| Cable | `<site>-cbl-NNNNN` inside a site, `bb-cbl-NNNNN` between sites | `got-cbl-00011`, `bb-cbl-00005` |
| Serial | `<MFR>-<SITE>-<nnnn>` | `JNP-STO-0001` |
| Asset tag (Nordfiber's own) | `NF-<SITE>-<nnnnn>` | `NF-STO-00003` |

## 2. Sites and racks

| Site | Kind | Building / MeetMe room | Racks |
|---|---|---|---|
| Stockholm DC | Datacenter (HQ) | Nordfiber's own, including the MeetMe room | `STO-TR-01` core, `STO-MM-01` MeetMe, `STO-CH-01` Polaris colo, `STO-CH-02` Baltic Retail colo |
| Gothenburg DC | Datacenter | MeetMe room is space in a building run by Skagerrak Interconnect AB | `GOT-TR-01` core, `GOT-MM-01` MeetMe, `GOT-CH-01` Polaris, `GOT-CH-02` Västhamnen, `GOT-CH-03/04` empty growth racks, `GOT-IDF-01` floor 3 closet |
| Helsinki DC | Datacenter (smaller) | Nordfiber's own, including the MeetMe room | `HEL-TR-01`, `HEL-MM-01` |
| Malmö PoP | PoP | MeetMe room run by Öresund Exchange AB | `MMA-TR-01`, `MMA-MM-01`, `MMA-CH-01` Baltic Retail colo |
| Oslo PoP | PoP | MeetMe room run by Skagerrak Interconnect AB | `OSL-TR-01`, `OSL-MM-01` |

**Uniform slots** (NetBox position 42 is the top; 2U gaps between kinds of
equipment leave room to grow):

| Rack kind | Top to bottom |
|---|---|
| Core rack (`-TR-01`) | U42–38 trunk patch panels, by destination (U42 MeetMe room, U41 Stockholm, U40 Gothenburg, U39 Malmö, U38 Oslo; the site's own slot stays free) · U35 OOB switch · U32/31 router 01/02 · U30/29 switch 01/02 · U26 and down WDM terminals · U20 DCP-2 shelf (fixed, so it lines up everywhere) |
| Colo customer rack | U42 top-of-rack fiber panel · U39 tenant switch · U36 and down servers |
| MeetMe rack | U42 Nordfiber's panel · U41 the facility owner's own panel (where it isn't Nordfiber) · U38 and down external parties |
| IDF rack | U42 floor switch |

PoPs keep U31/U29 free: the same racks, with the second pair not yet
installed.

## 3. Long-haul fiber

Six 24-pair trunks, `bb-cbl-00001` to `-00006`, each ONE cable between two trunk panels. Each has an FMS fiber-cable record
(Corning ALTOS loose tube, 48 fibers = 24 pairs, DIN/IEC colours, with serial number, install date, installer and
route marks from 0 to the route length in metres) and a PostGIS route
(`DirectBuried` pathway + `CableSegment`). The cable's length is the route
length.

| Cable | Between | Route | Length |
|---|---|---|---|
| `bb-cbl-00001` | `sto-patch-got-01` – `got-patch-sto-01` | Västerås, Örebro, Karlstad, Trollhättan | 480 km |
| `bb-cbl-00002` | `sto-patch-mma-01` – `mma-patch-sto-01` | the E4: Linköping, Jönköping, Markaryd, Hässleholm, Lund | 553 km |
| `bb-cbl-00003` | `sto-patch-osl-01` – `osl-patch-sto-01` (**leased** from Polarlink Transit, `PLT-100234`) | Västerås, Örebro, Karlstad, Charlottenberg | 448 km |
| `bb-cbl-00004` | `got-patch-mma-01` – `mma-patch-got-01` | the west coast: Varberg, Halmstad, Helsingborg, Landskrona | 259 km |
| `bb-cbl-00005` | Stockholm – Helsinki, **NSN-DF-0001** (Nordic Subsea Networks), between the vendor's two MeetMe panels | Mariehamn (Åland), Vaasa | 850 km |
| `bb-cbl-00006` | Stockholm – Helsinki, **BFN-DF-0001** (Baltic Fibre Networks), between the vendor's two MeetMe panels | Visby (Gotland), Riga, Tallinn | 907 km |

A leased circuit (`PLT-100234`, `NSN-DF-0001`, `BFN-DF-0001`) is a
commercial record whose terminations stay **uncabled**; the glass is the
single direct Cable (a Cable is physical connectivity, a Circuit is the
contract, and the two are deliberately different objects). The three leased
circuits additionally carry the same route as a circuit geometry. Helsinki's
two routes are chosen for path diversity: one through Åland and Vaasa, one
through Gotland and the Baltics.

## 4. DWDM transport

Ten muxponders, all SmartOptics DCP-M40-PAM4-ER (a terminal mux, not a
ROADM), each with all 40 channels provisioned; only the listed ones are lit, and those are
marked Active (the rest stay Available).

| Node | Carries |
|---|---|
| `sto-wdm-01` ↔ `osl-wdm-01` | Fjord Media wavelength service, channel 1 (C21), Stockholm–Oslo |
| `sto-wdm-02` ↔ `got-wdm-01` | Baltic Retail protect path, segment 1, channel 2 (C22) |
| `got-wdm-02` ↔ `mma-wdm-01` | Baltic Retail protect path, segment 2, channel 2 |
| `sto-wdm-03` ↔ `hel-wdm-01` | Nordfiber's own link to Helsinki over NSN, channel 1 |
| `sto-wdm-04` ↔ `hel-wdm-02` | Nordfiber's own link to Helsinki over BFN, channel 1 |

- **Why Stockholm has four chassis**: a protect path on its primary's
  chassis would not protect against a chassis failure, so each service has
  its own hardware.
- **Why Gothenburg has two for one wavelength**: a terminal mux cannot pass
  a wavelength through a site, so Stockholm–Malmö via Gothenburg is two
  independent segments regenerated electrically (`got-wdm-01` and `-02`
  jumpered client to client). netbox-wdm correctly reports two complete
  paths, not one.
- **Client handoffs, two patterns**: services with an *external customer*
  (Fjord, Baltic Retail) go through a **DCP-2 shelf with a DCP-110 module**,
  which turns the colored 100G channel into a grey 10G port the customer is
  handed (`sto-dcp2-01`, `osl-dcp2-01`, `mma-dcp2-01`). Nordfiber's own
  Helsinki links skip the shelf and go straight to a 100G router port:
  NSN on router 01 (`et-0/0/2`) at both ends, BFN on router 02
  (`et-0/0/3`) at both ends, so the two routes land on different routers.
  Gothenburg's and Helsinki's shelves are installed, with their module, and
  cabled for management only: nothing is delivered there yet.
- **Baltic Retail's protect path** ends on Stockholm's router 02
  (`et-0/0/1`) and Malmö's router 01 (`et-0/0/1`); the primary
  (`NF-BRG-0001`) is on router 01 (`et-0/0/0`) at both ends.

**Upstream limitation, not a data error.** netbox-wdm's `/trace/` cannot
walk a front-port-to-front-port cable (the MeetMe jumpers), so the Helsinki
links are not traceable by the plugin. `verify.py` checks them by walking
the cable chain port by port instead. Separately, netbox-wdm re-discovers
wavelength paths on every cable save and creates duplicates; layer 7
deletes everything not attached to a WdmCircuit and must run last.

## 5. MeetMe rooms

Every site has a MeetMe room (a Location and a rack apart from the core
rack) where each external party has its own demarc panel.

| Site | Panels |
|---|---|
| Stockholm | Nordfiber, Polaris (colo), Nordic Subsea Networks, Baltic Fibre Networks, Baltic Retail (colo) |
| Gothenburg | Nordfiber, Skagerrak (owner), Polaris (colo), Västhamnen (colo), Västkust Bredband (Internet) |
| Helsinki | Nordfiber, Nordic Subsea Networks, Baltic Fibre Networks |
| Malmö | Nordfiber, Öresund (owner), Baltic Retail (colo) |
| Oslo | Nordfiber, Skagerrak (owner) |

Convention everywhere: **the REAR port "Trunk" is a 24-pair trunk, FRONT ports are jumpers.** A
trunk keeps the pair number: front port N at one end is front port N at the other (position N of the trunk), so
the MeetMe port of a party is also its port on `<site>-patch-mmr-01`. A colo tenant's path is

```
server -> tenant switch -> tenant ToR panel --[trunk]--> tenant's MeetMe panel
  --[jumper]--> Nordfiber's MeetMe panel --[trunk]--> <site>-patch-mmr-01 (telecom room)
  --[jumper]--> Nordfiber switch (sto-sw-01 / got-sw-01)
```

The leased Helsinki links use the same pattern end to end with the
muxponder at the inner end and the vendor's long-haul span in the middle.

## 6. Datacenter redundancy

Datacenters have router 01/02 and aggregation switch 01/02 in `-TR-01`,
all linked by DAC: each router to both switches, router to router, switch to
switch. The OOB switch uplinks to both routers (`Ethernet49` and `50`).
Single-homed by design (a documented simplification): tenants, the IDF and
the colo and MeetMe handoffs all land on switch 01; router/switch 02 carry
management addressing only and are not in the iBGP mesh.

## 7. Out-of-band management

Each site has a 48-port copper OOB switch (`<site>-oob-01`) with the same
port plan everywhere: Ethernet1 router 01, 2 switch 01, 3–6 WDM terminals,
7 DCP-2, 8 and up everything else in the building (IDF switch, tenant
switches and servers), 13/14 router/switch 02 at datacenters, and a DAC
uplink to the router on 49 (and 50). One management port per device is
cabled — including colo tenants' gear (Nordfiber provides OOB as a service)
and the Gothenburg IDF switch over a copper riser. The OOB switch's own
management port is reached through its uplink. Management addressing is
`10.0.<site>.0/24`: router 01 `.11`, switch 01 `.12`, IDF `.13`,
workstation `.14`, router 02 `.15`, switch 02 `.16`, servers `.21` up.

## 8. Cabling standards

Decided in one place (`cabling.py`) so every cable gets them at creation:

| | Rule |
|---|---|
| Type, colour | copper twisted pair: **Cat6 gray** (Cat6A for the workstation) · DAC between network devices in one rack: **passive DAC black** · anything with an LC end or a circuit termination: **single-mode OS2 yellow** |
| Length | same rack: **2 m**, or **3 m** if the equipment is more than 20U apart · same room, other rack: 5 m · other room in the building: 30 m · floor riser or office run: 40 m / 30 m · between sites: the route length in km · circuit demarc: none |
| Label | `<site>-cbl-NNNNN` / `bb-cbl-NNNNN`, in creation order, never reassigned |
| End labels | custom fields **`label_a`** and **`label_b`**: `<cable id> -> <far end>`, what to print at each end |
| Tenant | the external party's if exactly one end is theirs (it is their cross-connect), Nordfiber's otherwise; OOB cables are always Nordfiber's; a vendor span is the vendor's |

## 9. Commercial circuits

| Circuit | Purpose | Physical path | Rate |
|---|---|---|---|
| `NF-BRG-0001` | Baltic Retail, primary EPL; Baltic Retail has a server and switch in colo at each end (`baltic-retail-sto-srv-01`, `baltic-retail-mma-srv-01`) | direct, `bb-cbl-00002` | 10 Gbps |
| `NF-BRG-0002` | Baltic Retail, protect | DWDM via Gothenburg, regenerated | 10 Gbps |
| `PLT-100234` | Nordfiber's leased Stockholm–Oslo dark fiber (Polarlink) | `bb-cbl-00003`, lit as Fjord's service | — |
| `VKB-INET-0001` | Nordfiber's upstream Internet (Västkust Bredband), A side only | via Gothenburg's MeetMe room | 10 Gbps |
| `NSN-DF-0001` | leased dark fiber, Helsinki primary route | `bb-cbl-00005` | — |
| `BFN-DF-0001` | leased dark fiber, Helsinki backup route | `bb-cbl-00006` | — |

Fjord Media's wavelength service is a netbox-wdm `WdmCircuit` riding on the
`PLT-100234` lease; Baltic Retail's protect path is two `WdmCircuit`s, one
per regenerated segment.

## 10. Not covered

Power, serial console access, VLANs and service IP addressing, the OOB
network beyond management addresses, customer CPE. See `README.md`,
"Not modeled, on purpose".
