# Changelog

Releases are tagged `vX.Y.Z`. Every release builds from an empty NetBox in one run and passes `verify.py`.

## Unreleased

Built from an empty NetBox on 4.7.3 (netbox-fms 0.6.0, netbox-pathways 0.3.0, netbox-wdm 0.2.2; netbox-secrets is not installed, so its login step is skipped): `verify.py` passes (70 checks). After the dev NetBox moved to 4.7.4, a second `build.py` changes nothing and `verify.py` still passes. The in-place upgrade of a 0.8.0 database has not been rehearsed (see `docs/DESIGN.md`, 2026-10-28).

- **The Stockholm East - Helsinki backup route (`bb-cbl-00006`, `BFN-DF-0001`) follows the southern Baltic route of
  `docs/Baltic Route.md`.** From Nacka by road past Handen to Västerhaninge, along the railway to Nynäshamn, under the
  sea to Fårösund, across Gotland by road to Ljugarn, under the sea to Ventspils, along the A10 past Pūre to Riga, the
  A2/A3 to Valmiera and Valga, roads 6 and 49 to Viljandi and Imavere, road 2 to Tallinn, under the sea to the Vuosaari
  harbour and by road into Helsinki: 1154.3 km in 15 legs, 393.3 km of it subsea (was one straight line of 905 km over
  Visby). Each land leg is a direct-buried pathway and each sea crossing a submarine pathway, owned by Baltic Fibre
  Networks, with one cable segment per leg; the circuit geometry carries the whole route. The dataset now has 84 cable
  segments (13 submarine, 30 direct buried). The bare-fiber loss of `NF-FC-0005` is 243.9 dB (was 191.6).
- **Tools.** `tools/derive_longhaul.py` derives both Helsinki routes (`python tools/derive_longhaul.py bfn` derives one
  and keeps the other), with a railway corridor (Overpass, `railway=rail`) as a new kind of section and a dry reference
  point and grid step per sea crossing. `tools/waterpath.py`: a coastline vertex lying exactly on a grid row could make
  the row lose a crossing and invert from there on (it cut the Vuosaari harbour off the open sea); fixed.
  `OVERPASS_URL` selects another Overpass instance when the main one does not answer.
- **Upgrading an existing NetBox.** `04_transport.py` replaces `bb-cbl-00006-route` with the 15 legs, as it did for
  `bb-cbl-00005` in 0.8.0. `verify.py` is unchanged: its route checks already follow the legs of a route laid leg by leg.

## 0.8.0

Two routes changed; the rest of the dataset is as in 0.7.0. Built from an empty NetBox on 4.7.3 (netbox-fms 0.6.0, netbox-pathways 0.3.0; netbox-secrets has no 4.7 release, so its login step is skipped): `verify.py` passes (70 checks), a second `build.py` changes nothing, an existing 0.7.0 database is brought up to date in place the same way (13 objects removed, the rest reconciled), and the print plugin's acceptance tests pass (199 checks). Not rebuilt on NetBox 4.6.

- **The Stockholm North - West ring cable no longer runs alongside the West - East cable.** `bb-cbl-00008` used to
  leave Ekerö for the E4/E20 and share that corridor with `bb-cbl-00010` for its last 16.8 km (different ducts, same
  road). It now follows Ekerö's south coast to Sjöängen, crosses the open water of Mälaren (7.5 km, a submarine
  pathway routed along the shore, 6 times shorter than the 39 km detour by road) and lands at Vattubrinken, from where
  local roads lead into the Södertälje entrance from the north-west. 57.2 km (was 50.5), owners Sollentuna,
  Stockholm, Ekerö and Södertälje (Botkyrka and Salem no longer own ducts on this cable). The ring now has 41
  conduits with innerducts and 4 submarine pathways (was 42 and 3).
- **The Stockholm North - Helsinki route (`bb-cbl-00005`, `NSN-DF-0001`) no longer goes over Vaasa.** It runs up road
  265 and the E18 to Norrtälje, over Väddö to Grisslehamn, by sea to Eckerö, over Åland to Mariehamn and Hummelvik, by
  sea to Kumlinge and through the open water between the islands to Korpo, then Pargas, Turku, the E18 to Salo, along
  the power line corridor towards Espoo and by road into Helsinki: 591.7 km in 19 legs (was one straight line of 849
  km). Each land leg is a direct-buried pathway and each sea crossing a submarine pathway, owned by Nordic Subsea
  Networks, with one cable segment per leg. The circuit geometry carries the whole route.
- **Tools.** `tools/derive_longhaul.py` derives the Helsinki route; `tools/waterpath.py` routes a crossing through
  the water along the OpenStreetMap shoreline (used for Sjöängen - Vattubrinken and Kumlinge - Korpo);
  `tools/derive_metro.py` can now route a crossing through the water and falls back to Nominatim when the Overpass
  API does not answer.
- **`verify.py`.** A new check: no two ring cables run within 300 m of each other for more than 0.5 km outside the
  2 km datacenter lead-ins (the structure-name check could not see a shared road). The route checks follow the legs of
  a route laid leg by leg.
- **Upgrading an existing NetBox.** `plant.retire()` removes the ring structures and pathways that the route no longer
  contains (after the cables have been routed through the new legs), and `04_transport.py` replaces
  `bb-cbl-00005-route` with its legs; an earlier build is reconciled in place.

## 0.7.0

Loads into NetBox 4.7.3 with the newest plugins as well; the data is unchanged and NetBox 4.6 with the older plugin
releases keeps working. Built from an empty NetBox on 4.7.3 (netbox-fms 0.6.0, netbox-pathways 0.3.0): `verify.py`
passes (69 of 70 checks, the netbox-secrets one is skipped), a second `build.py` changes nothing, and the print
plugin's acceptance tests pass.

- **netbox-fms 0.6.** Fiber circuits are assigned the path FMS derives between their two panel ports (one path per
  circuit, with the wavelength and loss on the assignment) instead of two traced paths. The build waits for the
  derived path to appear and for FMS to finish its analysis, and tries the assignment again if the API refuses it
  meanwhile. `verify.py` checks the circuit's ends and that the path is complete either way.
- **netbox-pathways 0.3.** A structure's point is written to `geometry` (it was `location`, now a link to a NetBox
  Location) and the innerduct colour is a hex code.
- `common.version_at_least()` decides this from the installed plugin version.
- netbox-secrets has no NetBox 4.7 release yet; the logins are skipped there, as with any missing plugin.

## 0.6.1

Documentation only; the data is unchanged (`verify.py` 70 checks, a second `build.py` changes nothing).

- `docs/INFRASTRUCTURE.md` now explains why the metro ring's submarine crossings and innerducts do not appear on the
  netbox-pathways map: the map has no layer for these base pathways, its search box skips them, and the **Map**
  button on their pages opens the map on the extent of the whole dataset instead of the stretch. The data and the
  plugin's `geo/pathways` API are complete. 45 of the ring's 52 cable segments lie in innerducts or submarine
  crossings.

## 0.6.0

Two changes: Stockholm becomes three availability zones with a metro ring through municipal ducts, and the plugins
become optional.

**Plugins are optional.** The dataset now loads into a vanilla NetBox with no plugins at all, and adds the layers of
whichever of netbox-pathways, -fms, -wdm, -bgp, -secrets and -inventory are installed. `build.py` lists the plugins it
found and sums up the steps it left out; `verify.py` skips the matching checks (39 of 70 run on a vanilla NetBox);
`NETBOX_SKIP_PLUGINS=wdm,pathways` switches plugins off on purpose; running `build.py` again after installing a
plugin adds its part. The acceptance tests of netbox-tracepath-plugin moved here from that plugin's repository
(`tests/tracepath/`) and skip themselves when the plugin is missing, so the plugin's repository no longer depends
on this dataset.

**Stockholm.** The data model is the same;
the dataset grows from 5 sites, 85 devices and 142 cables to **7 sites, 125 devices and 213 cables**.

- **Stockholm DC is split into three datacenters**, Nordfiber Stockholm **North** (Sollentuna, HQ), **West**
  (Södertälje) and **East** (Nacka), in the new region Greater Stockholm. Site codes `stn`, `stw`, `ste` replace
  `sto` in every name (`stn-rtr-01`, `STN-TR-01`, `polaris-stn-sw-01`, ...). Management prefixes `10.0.6.0/24` and
  `10.0.7.0/24` for West and East; the iBGP mesh grows to seven routers (21 sessions).
- **The long-haul cables moved to the zones.** North lands the northern Gothenburg trunk, Oslo and Helsinki over NSN;
  West lands Malmö; East lands Helsinki over BFN. **New southern trunk to Gothenburg** (`bb-cbl-00007`, Stockholm
  West, 24 pairs, pair 1 lit, `NF-FC-0006`) with a third Gothenburg muxponder.
- **The metro ring**: three 288-fiber ALTOS cables (24 tubes of 12, 144 pairs) between the zones, on new 144-pair
  trunk panels. Tubes 1-12 are WDM (pair 1 lit, `NF-FC-0007` to `-0009`), tubes 13-16 Nordfiber's dark fiber, tubes
  17-24 leasable dark fiber; pair 97 of the North - East cable is leased to Baltic Retail Group (`NF-FC-0010`). The
  West - East cable is owned by the new supplier **Stockholm Metro Fibre AB** and leased whole as `SMF-DF-0001`.
- **Real ducts.** Each ring cable runs through its legs structure by structure (netbox-pathways): 48 structures,
  6 duct banks, 42 conduits with innerducts and 3 submarine crossings, 52 cable segments. The ducts belong to **ten
  municipalities** (new tenant group), the innerducts to the cable owner, the water crossings to Nordfiber. The
  legs follow public roads (E4/E20, road 222, ...) and change owner at the real municipal borders; the geometry is
  derived from OpenStreetMap by `tools/derive_metro.py` (ODbL). Each zone has two separate building entrances and
  no duct or structure is shared between two ring cables.
- **Baltic Retail Group** now has colo in all three zones: the primary circuit starts in West, the protect path in
  North, and a **secondary wavelength** runs over the southern route to Gothenburg (a fourth WDM circuit).
- New: `plant.py` (the metro plant, runnable on its own after layer 1) and `data/metro.py`, `data/metro_geometry.py`,
  `data/municipalities.py`. OOB port plan: WDM nodes on 3-8, DCP-2 on 9, others from 10, second router and switch on
  15/16. Rack slots: the core rack has room for three 3U ring panels.
- `verify.py`: 70 checks, including the ring: structures and owners, the legs in order and adding up to the cable's
  length, dispersed routing, the lease, and the tube names.
- The plugin's live tests follow the new names; the leased dark pair `NF-FC-0010` is the one circuit it cannot print
  (see its roadmap).

## 0.5.3

- Documentation only: the print plugin this dataset is used with was renamed from netbox-trace-print to
  **netbox-tracepath-plugin** (0.7.0); the README and the design notes use the new name and the new repository
  address. The data is unchanged. Entries below this one use the old name.

## 0.5.2

- An **Authors** section in the README: co-authored by JP and Claude (Claude Sonnet 5.5), the companies are
  fictional, and the hardware sources are named (NetBox Community Device Type Library, the generic patch panel
  defined here, Corning's ALTOS cable family, real places for the geography).
- The README says how the dataset relates to the plugin releases. The data is unchanged.

## 0.5.1

- Documentation only: design notes for the trunks, colours, strands and fiber circuits, a releases section and the
  link to netbox-trace-print. The data is unchanged.

## 0.5.0

- **Strands on panel ports.** Strands 2n-1 and 2n of every 48-fiber trunk are landed on port n of the panel at
  each end (netbox-fms), so the tube, fiber and colour of a pair can be read off.
- **FMS fiber circuits** `NF-FC-0001` to `-0005` (2 strands, two paths from one duplex port, 1550 nm, with
  end-to-end loss), one per trunk pair in use, each from the line panel port of one muxponder to the other's.
- `verify.py`: 52 checks.

## 0.4.0

- Trunk cables are **green** inside a site and **blue** between sites.

## 0.3.0

- **24-pair trunks.** Every panel-to-panel rear connection is one 24-pair (48-fiber) cable between two trunk
  panels (24 duplex LC front ports, one 24-position rear port), no longer 24 discrete cables.
- Baltic Retail Group has servers at both ends of `NF-BRG-0001`.
- Fuller fiber-plant records: serial number, install date, installer and route marks.

## 0.2.0

- The build rewritten as seven layered, reconciling scripts (`01_organization` to `07_finalize`, plus
  `verify.py` and `build.py`) that describe the final state directly and can be replayed on an empty NetBox.

## 0.1.0

- The baseline: 22 numbered phase scripts, kept in git and in `archive/` as history.
