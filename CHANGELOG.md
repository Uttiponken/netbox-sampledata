# Changelog

Releases are tagged `vX.Y.Z`. Every release builds from an empty NetBox in one run and passes `verify.py`.

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
