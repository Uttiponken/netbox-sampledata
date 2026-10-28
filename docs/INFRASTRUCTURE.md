# Nordfiber AB — Physical Infrastructure

What the finished dataset looks like: what connects to what, over what, and
how it is named and cabled. This describes the build produced by
`build.py` (layers 1–7, with the metro plant in `plant.py`); `docs/DESIGN.md` has the rationale and history.

This is the complete build, with all six optional plugins installed. On a NetBox without them the same sites,
racks, devices, cables, circuits and addresses load; what is missing per plugin (the duct plant and routes, the fiber
records, the WDM services, the iBGP sessions, the logins, the spare assets) is listed under "Plugins" in the README.

## TL;DR

- **7 sites, 24 racks, 125 devices, 213 cables, 7 circuits.** Five datacenters
  Nordfiber owns — **Stockholm North, West and East** (three availability
  zones, North is HQ), **Gothenburg** and **Helsinki** — and two points of
  presence, **Malmö** and **Oslo** (the cross-border one).
- **Datacenters are built in redundant pairs** (router/switch 01 and 02 in
  the same rack, cross-connected); PoPs have a single pair with the slots
  for the second one kept free. Every site otherwise has the same
  equipment in the same rack slots.
- **Stockholm is three datacenters tied together by a metro ring**: three
  288-fiber cables (144 pairs each) between the zones, run through real ducts
  owned by ten municipalities. Two of the cables are Nordfiber's own; the third
  is leased whole from another telecom. Each zone lands different long-haul
  routes (see section 4), so Gothenburg is reached by a northern and a
  southern trunk, Malmö and Oslo by one trunk each, and Helsinki by two
  independent leased trunks from two vendors on geographically disjoint routes.
- **Every panel-to-panel connection is a trunk**: one cable between two patch
  panels, each with duplex LC ports on the front and one rear port "Trunk"
  with one position per pair. Long-haul trunks are 24 pairs (48 fibers), the
  metro ring is 144 pairs (288 fibers). There is one panel per trunk.
- **Everything between sites is dark fiber**; DWDM (SmartOptics
  DCP-M40-PAM4-ER muxponders, 40 channels each) lights the wavelengths that
  need bandwidth.
- **Every external party lands on its own demarc panel** in the site's
  MeetMe room; nothing external lands on Nordfiber's own rack gear.
- **Every cable has a type, colour, length, label and per-end labels**;
  every device a serial (Nordfiber's own also an asset tag); every
  management port is cabled to the site's OOB switch.
- **All ten long-haul and ring cables have a real-world route** (netbox-pathways)
  and a fiber-plant record (netbox-fms).

---

## 1. Naming convention

One scheme everywhere (it lives in `naming.py`):

| Thing | Pattern | Example |
|---|---|---|
| Site | `Nordfiber <City> DC` / `PoP`; Stockholm is `Nordfiber Stockholm North/West/East DC` | Nordfiber Gothenburg DC |
| Room (one Location each) | Telecom Room, MeetMe Room, Colo Hall, IDF Floor 3, Office Floor 3 | |
| Rack | `<SITE>-<ROOM>-<NN>` | `STN-TR-01`, `GOT-MM-01`, `GOT-CH-02` |
| Nordfiber device | `<site>-<role>-<NN>` | `stn-rtr-01`, `hel-oob-01`, `got-wdm-02` |
| Tenant device | `<tenant>-<site>-<role>-<NN>` | `polaris-stn-sw-01` |
| MeetMe panel | `<site>-mmr-<party>-01` | `got-mmr-vastkust-01` |
| Telecom-room trunk panel | `<site>-patch-<to>-01`, `<to>` = `mmr` or the site the trunk goes to | `stn-patch-mmr-01`, `stn-patch-got-01`, `stn-patch-stw-01` |
| Cable | `<site>-cbl-NNNNN` inside a site, `bb-cbl-NNNNN` between sites | `got-cbl-00011`, `bb-cbl-00005` |
| Serial | `<MFR>-<SITE>-<nnnn>` | `JNP-STN-0001` |
| Asset tag (Nordfiber's own) | `NF-<SITE>-<nnnnn>` | `NF-STN-00003` |

Site codes: `stn` `stw` `ste` (Stockholm North, West, East), `got`, `mma`, `osl`, `hel`.

## 2. Sites and racks

| Site | Kind | Building / MeetMe room | Racks |
|---|---|---|---|
| Stockholm North DC (Sollentuna) | Datacenter (HQ) | Nordfiber's own, including the MeetMe room | `STN-TR-01` core, `STN-MM-01` MeetMe, `STN-CH-01` Polaris colo, `STN-CH-02` Baltic Retail colo |
| Stockholm West DC (Södertälje) | Datacenter | Nordfiber's own | `STW-TR-01`, `STW-MM-01`, `STW-CH-01` Baltic Retail colo |
| Stockholm East DC (Nacka) | Datacenter | Nordfiber's own | `STE-TR-01`, `STE-MM-01`, `STE-CH-01` Baltic Retail colo |
| Gothenburg DC | Datacenter | MeetMe room is space in a building run by Skagerrak Interconnect AB | `GOT-TR-01` core, `GOT-MM-01` MeetMe, `GOT-CH-01` Polaris, `GOT-CH-02` Västhamnen, `GOT-CH-03/04` empty growth racks, `GOT-IDF-01` floor 3 closet |
| Helsinki DC | Datacenter (smaller) | Nordfiber's own, including the MeetMe room | `HEL-TR-01`, `HEL-MM-01` |
| Malmö PoP | PoP | MeetMe room run by Öresund Exchange AB | `MMA-TR-01`, `MMA-MM-01`, `MMA-CH-01` Baltic Retail colo |
| Oslo PoP | PoP | MeetMe room run by Skagerrak Interconnect AB | `OSL-TR-01`, `OSL-MM-01` |

The three Stockholm sites form the region **Greater Stockholm**. Their
addresses and coordinates are invented.

**Uniform slots** (NetBox position 42 is the top; 2U gaps between kinds of
equipment leave room to grow):

| Rack kind | Top to bottom |
|---|---|
| Core rack (`-TR-01`) | U42 MeetMe-room trunk panel · U41 Gothenburg · U40 Malmö · U39 Oslo (1U panels, by destination) · U36–38 Stockholm North · U33–35 Stockholm West · U30–32 Stockholm East (3U ring panels; the site's own slot stays free) · U27 OOB switch · U24/23 router 01/02 · U22/21 switch 01/02 · U18 and down WDM terminals · U12 DCP-2 shelf (fixed, so it lines up everywhere) |
| Colo customer rack | U42 top-of-rack fiber panel · U39 tenant switch · U36 and down servers |
| MeetMe rack | U42 Nordfiber's panel · U41 the facility owner's own panel (where it isn't Nordfiber) · U38 and down external parties |
| IDF rack | U42 floor switch |

PoPs keep U23/U21 free: the same racks, with the second pair not yet
installed.

## 3. Long-haul fiber

Seven 24-pair trunks, `bb-cbl-00001` to `-00007`, each ONE cable between two trunk panels. Each has an FMS fiber-cable record
(Corning ALTOS loose tube, 48 fibers = 24 pairs, DIN/IEC colours, with serial number, install date, installer and
route marks from 0 to the route length in metres) and a PostGIS route
(`DirectBuried` pathway + `CableSegment`). The cable's length is the route
length.

| Cable | Between | Route | Length |
|---|---|---|---|
| `bb-cbl-00001` | `stn-patch-got-01` – `got-patch-stn-01` (the **northern** route to Gothenburg) | Västerås, Örebro, Karlstad, Trollhättan | 468 km |
| `bb-cbl-00002` | `stw-patch-mma-01` – `mma-patch-stw-01` | the E4: Linköping, Jönköping, Markaryd, Hässleholm, Lund | 523 km |
| `bb-cbl-00003` | `stn-patch-osl-01` – `osl-patch-stn-01` (**leased** from Polarlink Transit, `PLT-100234`) | Västerås, Örebro, Karlstad, Charlottenberg | 436 km |
| `bb-cbl-00004` | `got-patch-mma-01` – `mma-patch-got-01` | the west coast: Varberg, Halmstad, Helsingborg, Landskrona | 258 km |
| `bb-cbl-00005` | Stockholm North – Helsinki, **NSN-DF-0001** (Nordic Subsea Networks), between the vendor's two MeetMe panels | Norrtälje, Grisslehamn, Åland (Mariehamn, Kumlinge), Korpo, Turku, Salo: roads, six sea crossings and a power line corridor, 19 legs (below) | 592 km |
| `bb-cbl-00006` | Stockholm East – Helsinki, **BFN-DF-0001** (Baltic Fibre Networks), between the vendor's two MeetMe panels | Handen, Västerhaninge, the railway to Nynäshamn, Gotland (Fårösund, Ljugarn), Ventspils, Pūre, Riga, Valmiera, Valga, Viljandi, Imavere, Tallinn, Vuosaari: roads, a railway corridor and three sea crossings, 15 legs (below) | 1154 km |
| `bb-cbl-00007` | `stw-patch-got-01` – `got-patch-stw-01` (the **southern** route to Gothenburg) | Nyköping, Norrköping, Linköping, Jönköping, Borås | 389 km |

The northern and southern Gothenburg trunks are the same kind of cable and
are lit the same way (pair 1, DWDM); the southern one shares the E4 corridor
with the Malmö trunk between Södertälje and Jönköping, as the two northern
trunks (Gothenburg and Oslo) share the corridor to Karlstad. Five of these routes are
straight lines between towns; the two routes to Helsinki and the metro ring below follow roads, shores, a railway and power lines.

**The Helsinki route over NSN (`bb-cbl-00005`).** The leased pair runs from Stockholm North up road 265 and the E18 to
Norrtälje, over Väddö (roads 76 and 283) to Grisslehamn, across the sea to Eckerö on Åland, over the Åland roads to
Mariehamn and Hummelvik, by sea to Kumlinge and, through the open water between the islands of the archipelago, to
Korpo, then along road 180 to Pargas and Turku, along the E18 to Salo, and from there along the 110 kV and 400 kV power
line corridor to the outskirts of Espoo and by road into Helsinki. It replaces the old route over Vaasa, which was a
straight line of 849 km. The cable is laid leg by leg: a direct-buried pathway for each land leg, a submarine pathway
for each sea crossing (every ferry line, the small cable ferries included, becomes a crossing; where no ferry exists the crossing is routed
through the water along the shore, so it never cuts across an island), all owned by Nordic Subsea Networks, with one cable
segment per leg. The circuit `NSN-DF-0001` carries the whole route as its geometry.

| Leg | From – to | Laid as | Length |
|---|---|---|---|
| 1 | Stockholm North - Norrtälje | direct buried | 63.7 km |
| 2 | Norrtälje - Grisslehamn | direct buried | 45.8 km |
| 3 | Grisslehamn (local road) | direct buried | 1.5 km |
| 4 | Grisslehamn - Berghamn | submarine | 42.9 km |
| 5 | Berghamn - Mariehamn | direct buried | 33.6 km |
| 6 | Mariehamn - Sund | direct buried | 33.6 km |
| 7 | Sund - Vårdö | submarine | 0.4 km |
| 8 | Vårdö - Hummelvik (Vårdö) | direct buried | 11.2 km |
| 9 | Hummelvik (Vårdö) - Kumlinge | submarine | 26.4 km |
| 10 | Kumlinge (local road) | direct buried | 5.9 km |
| 11 | Kumlinge - Korpo | submarine | 50.8 km |
| 12 | Korpo - Österretais | direct buried | 6.8 km |
| 13 | Österretais - Nagu | submarine | 0.8 km |
| 14 | Nagu (local road) | direct buried | 27.3 km |
| 15 | Nagu - Pargas | submarine | 1.6 km |
| 16 | Pargas - Turku | direct buried | 40.1 km |
| 17 | Turku - Salo | direct buried | 58.0 km |
| 18 | Salo - Esbogård | direct buried, along the 110 kV+ power line corridor | 113.6 km |
| 19 | Esbogård - Helsinki | direct buried | 27.6 km |
| | **Total** | 13 land legs, 6 submarine | **591.7 km** (122.9 km subsea) |

The geometry is derived by `tools/derive_longhaul.py` (roads and ferries from OpenStreetMap through OSRM, the power lines
from OpenStreetMap through the Overpass API, the water route of the Kumlinge – Korpo crossing with `tools/waterpath.py`)
and stored in `data/longhaul_geometry.py`. The corridor makes a small dogleg through the Ingå substation, where the two
real lines meet. Who owns what is invented.

**The Helsinki route over BFN (`bb-cbl-00006`), the southern Baltic route.** The leased pair runs from Stockholm East
(Nacka) by roads 222, 75 and 73 past Handen to Västerhaninge, then along the railway (the Nynäs line) to Nynäshamn
station at the harbour, under the sea to Fårösund on Gotland, by roads 148, 147, 146 and 143 across Gotland to Ljugarn,
under the sea to Ventspils, along the A10 past Pūre to Riga, along the A2 and A3 to Valmiera and Valga, along roads 6
and 49 (by Karksi-Nuia) to Viljandi, along road 49 to Imavere and road 2 to Tallinn, under the sea to the Vuosaari
harbour (Vuosaaren satama) and by road into Helsinki. It replaces the old route, a straight line of 905 km through Visby,
Riga and Tallinn. It is laid like the NSN route: a direct-buried pathway for each land leg and a submarine pathway for
each sea crossing, all owned by Baltic Fibre Networks, with one cable segment per leg. The circuit `BFN-DF-0001`
carries the whole route as its geometry. At 1154 km it is almost twice the length of the NSN route, which keeps it the
longer, geographically diverse backup.

| Leg | From – to | Laid as | Length |
|---|---|---|---|
| 1 | Stockholm East - Handen | direct buried | 20.9 km |
| 2 | Handen - Västerhaninge | direct buried | 7.6 km |
| 3 | Västerhaninge - Nynäshamn | direct buried, along the railway | 32.3 km |
| 4 | Nynäshamn - Fårösund | submarine | 132.8 km |
| 5 | Fårösund - Ljugarn | direct buried | 79.8 km |
| 6 | Ljugarn - Ventspils | submarine | 170.3 km |
| 7 | Ventspils - Pūre | direct buried | 105.8 km |
| 8 | Pūre - Riga | direct buried | 86.1 km |
| 9 | Riga - Valmiera | direct buried | 108.7 km |
| 10 | Valmiera - Valga | direct buried | 49.4 km |
| 11 | Valga - Viljandi | direct buried | 92.9 km |
| 12 | Viljandi - Imavere | direct buried | 51.2 km |
| 13 | Imavere - Tallinn | direct buried | 108.4 km |
| 14 | Tallinn - Vuosaari | submarine | 90.3 km |
| 15 | Vuosaari - Helsinki | direct buried | 17.9 km |
| | **Total** | 12 land legs, 3 submarine | **1154.3 km** (393.3 km subsea) |

The same tool derives it: the roads through OSRM, the railway from OpenStreetMap through the Overpass API, and the three
sea crossings with `tools/waterpath.py` (each one leaves its harbour through the water and stays off every island; the
Nynäshamn crossing enters the Fårösund strait from the north). Two waypoints keep the route on the major roads: Handen is
joined where road 73 passes it, and Valga - Viljandi goes by Karksi-Nuia (roads 6 and 49, 93 km) where the router would
take 28 km of local roads (79 km). Who owns what is invented.

**Strands and fiber circuits.** A trunk panel's duplex LC port *n* carries pair *n*, so strands 2*n*-1 and 2*n* of the
cable (netbox-fms `FiberStrand`) are landed on port *n* of the panel at each end; the strand records give the tube and
fiber and the colour to look for (DIN/IEC 60304). Each trunk pair that is in use has a **fiber circuit** (2 strands,
two circuit paths from the same duplex port, wavelength 1550 nm, with the end-to-end loss of the bare fiber at
0.21 dB/km plus 1.5 dB of connectors), all pair 1 unless noted:

| Circuit | Runs |
|---|---|
| `NF-FC-0001` | Stockholm North – Gothenburg |
| `NF-FC-0002` | Stockholm North – Oslo |
| `NF-FC-0003` | Gothenburg – Malmö |
| `NF-FC-0004` | Stockholm North – Helsinki over NSN |
| `NF-FC-0005` | Stockholm East – Helsinki over BFN |
| `NF-FC-0006` | Stockholm West – Gothenburg (southern route) |
| `NF-FC-0007` / `-0008` / `-0009` | the three ring cables, North–West, North–East, West–East |
| `NF-FC-0010` | pair 97 of the North–East ring cable, a **dark pair leased to Baltic Retail Group** |

A circuit runs from the line panel port of one muxponder to that of the other (`LINE_PATCH`); netbox-fms follows the
glass from there, so the two Helsinki circuits run through both MeetMe rooms and the leased trunk. The Stockholm West –
Malmö trunk has no pair in use and so no circuit.

A leased circuit (`PLT-100234`, `NSN-DF-0001`, `BFN-DF-0001`, `SMF-DF-0001`) is a
commercial record whose terminations stay **uncabled**; the glass is the
single direct Cable (a Cable is physical connectivity, a Circuit is the
contract, and the two are deliberately different objects). The leased
circuits additionally carry the same route as a circuit geometry. Helsinki's
two routes are chosen for path diversity: one through Åland and Turku, one
through Gotland and the Baltics.

## 4. The Stockholm metro ring

Stockholm is three datacenters, one per availability zone. Each lands its own
long-haul routes, and the zones are tied together by three metro cables:

| Zone | Lands |
|---|---|
| North (Sollentuna) | Gothenburg north `bb-cbl-00001`, Oslo `-00003`, Helsinki over NSN `-00005`, and two ring cables |
| West (Södertälje) | Malmö `bb-cbl-00002`, Gothenburg south `-00007`, and two ring cables |
| East (Nacka) | Helsinki over BFN `bb-cbl-00006`, and two ring cables |

| Cable | Between | Owner of the cable | Length | Route |
|---|---|---|---|---|
| `bb-cbl-00008` | North – West | Nordfiber AB | 57.2 km | Sollentuna, Hässelby, **water crossing of Mälaren**, Färingsö, Ekerö (along its south coast to Sjöängen), **water crossing of the Mälaren bay (7.5 km)**, Vattubrinken, Södertälje (arriving from the north-west, away from the E4/E20) |
| `bb-cbl-00009` | North – East | Nordfiber AB | 40.6 km | Sollentuna, Danderyd, **water crossing**, Lidingö, **water crossing**, Orminge on road 222, Nacka |
| `bb-cbl-00010` | West – East | **Stockholm Metro Fibre AB**, leased whole as `SMF-DF-0001` | 38.6 km | E4/E20, road 75 and road 222: Södertälje, Salem, Botkyrka, Huddinge, Stockholm, Nacka |

All three are Corning ALTOS loose-tube cable of the largest count: **288 fibers, 24 tubes of 12 = 144 pairs**, ending on
**144-pair trunk panels** (3U, `LC-144`). A tube's name says what it is for:

| Tubes | Pairs | Use |
|---|---|---|
| 1–12 | 1–72 | **WDM**: pair 1 is lit (a muxponder at each end, a fiber circuit), pairs 2–72 are reserved |
| 13–16 | 73–96 | Nordfiber's own **dark fiber** |
| 17–24 | 97–144 | **dark fiber to lease out**; pair 97 on the North–East cable is leased to Baltic Retail Group (`NF-FC-0010`) |

**Who owns what.** Three different parties are involved in every segment and
the dataset keeps them apart: the **duct** belongs to the municipality it lies
in, the **cable** to whoever owns it (Nordfiber, or Stockholm Metro Fibre on
the leased West–East cable), and the **lessee** is Nordfiber (a dark-fiber
circuit, like the Helsinki vendor spans). The cable runs through an **innerduct**
that belongs to the cable's owner, inside a conduit that belongs to the
municipality.

**Real ducts, structure by structure.** Each cable is routed through its ducts leg by leg
(netbox-pathways): 48 structures (building entrances, manholes, handholes, vaults at the municipal
borders), 6 concrete duct banks (the lead-ins at the datacenters), 41 conduits each with an innerduct, and
4 submarine pathways (the water crossings, which are Nordfiber's own). That is 45 cable segments. The
legs follow public roads and change owner where the real municipal border is; the municipalities are
**Sollentuna, Danderyd, Lidingö, Nacka, Stockholm, Ekerö, Botkyrka, Salem, Huddinge and Södertälje**
(tenant group "Municipalities").

| Cable | Owners along the route (km of duct) |
|---|---|
| North – West | Sollentuna 2.1 → Stockholm 10.3 → water 4.2 → Ekerö 22.4 → water 7.8 → Södertälje 10.3 |
| North – East | Sollentuna 5.6 → Danderyd 7.2 → water 2.2 → Lidingö 11.8 → water 3.5 → Nacka 10.3 |
| West – East | Södertälje 7.0 → Salem 4.9 → Botkyrka 6.3 → Huddinge 6.3 → Stockholm 10.5 → Nacka 3.7 |

**Dispersed routing.** Each datacenter has two separate building entrances, one per ring cable, and no duct and
no structure outside the buildings is shared between two cables (`verify.py` checks it). The cables do
share owners (Stockholms stad owns ducts on two of them), which is an organisational dependency, not a
physical one. The check is also made by distance: no two ring cables may run within 300 m of each other for more than
0.5 km outside the 2 km lead-ins at a datacenter. The North – West cable used to share the E4/E20 corridor with the West – East
cable for its last 16.8 km (different ducts, same road), which a check on structure names cannot see; it now leaves Ekerö
across the open water of Mälaren and reaches Södertälje from the north-west.

The geometry (stations, legs, borders) is derived from OpenStreetMap by `tools/derive_metro.py` (the crossing between Sjöängen
and Vattubrinken with `tools/waterpath.py`, which routes it through the water along the shore) and stored in
`data/metro_geometry.py`. The municipalities and the roads are real; the ownership, the ducts and every
coordinate to the metre are invented for the scenario.
Road and boundary data: © OpenStreetMap contributors, ODbL (https://www.openstreetmap.org/copyright).
The netbox-pathways map does not draw submarine pathways, so the water crossings show as gaps there. The data is
complete (each crossing has its geometry, and the plugin's `geo/pathways` API returns it): the map only has layers
for conduit banks, conduits, aerial spans, direct-buried pathways and circuits, its search box asks only those, and
the **Map** button on a crossing's page (`?select=submarine-<id>`) finds nothing to centre on, so the map falls back
to its default view (the extent of the whole dataset, not the crossing).

The 41 innerducts have the same limitation, because they are base pathways too. They are not drawn, the search box
skips them, and the **Map** button on an innerduct's page (`?select=innerduct-<id>`) also opens the map on the whole
dataset instead of the stretch. Each innerduct has exactly the line of its parent conduit, so the route is visible
through the conduit, but the innerduct itself (its owner, its colour, the cable inside it) cannot be selected on the
map. This matters: of the dataset's 84 cable segments, 41 lie in innerducts (the ring) and 13 in submarine crossings (4 in the ring,
6 on the NSN route and 3 on the BFN route to Helsinki), and only the 30 direct-buried ones (five long-haul routes, 13 land legs of
the NSN route and 12 of the BFN route) are on a pathway type the map draws. The circuit geometries of `NSN-DF-0001` and
`BFN-DF-0001` do show the whole Helsinki routes. The data is as netbox-pathways models it
(a cable segment on an innerduct inside a conduit); nothing is missing from the dataset.

## 5. DWDM transport

Eighteen muxponders, all SmartOptics DCP-M40-PAM4-ER (a terminal mux, not a
ROADM), each with all 40 channels provisioned; only the listed ones are lit, and those are
marked Active (the rest stay Available).

| Node | Carries |
|---|---|
| `stn-wdm-01` ↔ `osl-wdm-01` | Fjord Media wavelength service, channel 1 (C21), Stockholm North–Oslo |
| `stn-wdm-02` ↔ `got-wdm-01` | Baltic Retail protect path, segment 1 (northern route), channel 2 (C22) |
| `got-wdm-02` ↔ `mma-wdm-01` | Baltic Retail protect path, segment 2, channel 2 |
| `stw-wdm-01` ↔ `got-wdm-03` | Baltic Retail **secondary** wavelength over the southern route, channel 2; it ends in Gothenburg |
| `stn-wdm-03` ↔ `hel-wdm-01` | Nordfiber's own link to Helsinki over NSN, channel 1 |
| `ste-wdm-01` ↔ `hel-wdm-02` | Nordfiber's own link to Helsinki over BFN, channel 1 |
| `stn-wdm-04` ↔ `stw-wdm-02` | Nordfiber's own, ring North–West, channel 1 |
| `stn-wdm-05` ↔ `ste-wdm-02` | Nordfiber's own, ring North–East, channel 1 |
| `stw-wdm-03` ↔ `ste-wdm-03` | Nordfiber's own, ring West–East (leased cable), channel 1 |

- **Why Stockholm North has five chassis**: a protect path on its primary's
  chassis would not protect against a chassis failure, so each service has
  its own hardware. Stockholm West and East have three each, Gothenburg three.
- **Why Gothenburg has two for one wavelength**: a terminal mux cannot pass
  a wavelength through a site, so Stockholm North–Malmö via Gothenburg is two
  independent segments regenerated electrically (`got-wdm-01` and `-02`
  jumpered client to client). netbox-wdm correctly reports two complete
  paths, not one. The secondary wavelength over the southern route is not
  continued to Malmö: the Gothenburg–Malmö leg would be shared with the protect path.
- **Client handoffs, two patterns**: services with an *external customer*
  (Fjord, Baltic Retail) go through a **DCP-2 shelf with a DCP-110 module**,
  which turns the colored 100G channel into a grey 10G port the customer is
  handed (`stn-dcp2-01`, `stw-dcp2-01`, `osl-dcp2-01`, `mma-dcp2-01`). Nordfiber's
  own links skip the shelf and go straight to a 100G router port: NSN on router 01
  (`et-0/0/2`) at both ends, BFN on router 02 (`et-0/0/3`) at both ends, so the two
  routes to Helsinki land on different routers; the ring cables use `et-0/0/2` and
  `et-0/0/3` of router 01 and 02 as listed in `data/optical.py`.
  Gothenburg's, Helsinki's and Stockholm East's shelves are installed, with their module,
  and cabled for management only: nothing is delivered there yet (Gothenburg's carries
  the end of the secondary wavelength on the line side, nothing on the client side).
- **Baltic Retail** has three services: the primary `NF-BRG-0001` from Stockholm West
  (`stw-rtr-01`, `et-0/0/0`) straight to Malmö; the protect path `NF-BRG-0002` from
  Stockholm North (`stn-rtr-02`, `et-0/0/1`) via Gothenburg to Malmö (`mma-rtr-01`,
  `et-0/0/1`); and the secondary wavelength from Stockholm West (`stw-rtr-02`, `et-0/0/1`)
  to Gothenburg. That is why Baltic Retail has colo in all three Stockholm zones.

**Upstream limitation, not a data error.** netbox-wdm's `/trace/` cannot
walk a front-port-to-front-port cable (the MeetMe jumpers), so the Helsinki
links are not traceable by the plugin. `verify.py` checks them by walking
the cable chain port by port instead. Separately, netbox-wdm re-discovers
wavelength paths on every cable save and creates duplicates; layer 7
deletes everything not attached to a WdmCircuit and must run last.

## 6. MeetMe rooms

Every site has a MeetMe room (a Location and a rack apart from the core
rack) where each external party has its own demarc panel.

| Site | Panels |
|---|---|
| Stockholm North | Nordfiber, Polaris (colo), Nordic Subsea Networks, Baltic Retail (colo) |
| Stockholm West | Nordfiber, Baltic Retail (colo) |
| Stockholm East | Nordfiber, Baltic Fibre Networks, Baltic Retail (colo) |
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
  --[jumper]--> Nordfiber switch (stn-sw-01 / got-sw-01)
```

The leased Helsinki links use the same pattern end to end with the
muxponder at the inner end and the vendor's long-haul span in the middle.

## 7. Datacenter redundancy

Datacenters have router 01/02 and aggregation switch 01/02 in `-TR-01`,
all linked by DAC: each router to both switches, router to router, switch to
switch. The OOB switch uplinks to both routers (`Ethernet49` and `50`).
Single-homed by design (a documented simplification): tenants, the IDF and
the colo and MeetMe handoffs all land on switch 01; router/switch 02 carry
management addressing only and are not in the iBGP mesh (seven routers, 21 sessions).

## 8. Out-of-band management

Each site has a 48-port copper OOB switch (`<site>-oob-01`) with the same
port plan everywhere: Ethernet1 router 01, 2 switch 01, 3–8 WDM terminals,
9 DCP-2, 10 and up everything else in the building (IDF switch, tenant
switches and servers), 15/16 router/switch 02 at datacenters, and a DAC
uplink to the router on 49 (and 50). One management port per device is
cabled — including colo tenants' gear (Nordfiber provides OOB as a service)
and the Gothenburg IDF switch over a copper riser. The OOB switch's own
management port is reached through its uplink. Management addressing is
`10.0.<site>.0/24` (Stockholm North 1, Gothenburg 2, Malmö 3, Oslo 4, Helsinki 5,
Stockholm West 6, Stockholm East 7): router 01 `.11`, switch 01 `.12`, IDF `.13`,
workstation `.14`, router 02 `.15`, switch 02 `.16`, servers `.21` up.

## 9. Cabling standards

Decided in one place (`cabling.py`) so every cable gets them at creation:

| | Rule |
|---|---|
| Type, colour | copper twisted pair: **Cat6 gray** (Cat6A for the workstation) · DAC between network devices in one rack: **passive DAC black** · a trunk between two patch panels: **single-mode OS2 green**, or **blue** when the panels are at different sites · any other cable with an LC end or a circuit termination: **single-mode OS2 yellow** |
| Length | same rack: **2 m**, or **3 m** if the equipment is more than 20U apart · same room, other rack: 5 m · other room in the building: 30 m · floor riser or office run: 40 m / 30 m · between sites: the route length in km · circuit demarc: none |
| Label | `<site>-cbl-NNNNN` / `bb-cbl-NNNNN`, in creation order, never reassigned |
| End labels | custom fields **`label_a`** and **`label_b`**: `<cable id> -> <far end>`, what to print at each end |
| Tenant | the external party's if exactly one end is theirs (it is their cross-connect), Nordfiber's otherwise; OOB cables are always Nordfiber's; a vendor span is the vendor's; a leased metro cable is its owner's |

## 10. Commercial circuits

| Circuit | Purpose | Physical path | Rate |
|---|---|---|---|
| `NF-BRG-0001` | Baltic Retail, primary EPL, Stockholm West – Malmö; Baltic Retail has a server and switch in colo at each end (`baltic-retail-stw-srv-01`, `baltic-retail-mma-srv-01`) | direct, `bb-cbl-00002` | 10 Gbps |
| `NF-BRG-0002` | Baltic Retail, protect, from Stockholm North | DWDM via Gothenburg, regenerated | 10 Gbps |
| `PLT-100234` | Nordfiber's leased Stockholm North–Oslo dark fiber (Polarlink) | `bb-cbl-00003`, lit as Fjord's service | — |
| `VKB-INET-0001` | Nordfiber's upstream Internet (Västkust Bredband), A side only | via Gothenburg's MeetMe room | 10 Gbps |
| `NSN-DF-0001` | leased dark fiber, Helsinki primary route, to Stockholm North | `bb-cbl-00005` | — |
| `BFN-DF-0001` | leased dark fiber, Helsinki backup route, to Stockholm East | `bb-cbl-00006` | — |
| `SMF-DF-0001` | leased dark fiber, the whole 288-fiber cable between Stockholm West and East (Stockholm Metro Fibre) | `bb-cbl-00010` | — |

Fjord Media's wavelength service is a netbox-wdm `WdmCircuit` riding on the
`PLT-100234` lease; Baltic Retail's protect path is two `WdmCircuit`s, one
per regenerated segment, and its secondary wavelength a fourth.

## 11. Not covered

Power, serial console access, VLANs and service IP addressing, the OOB
network beyond management addresses, customer CPE. See `README.md`,
"Not modeled, on purpose".
