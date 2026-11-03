# Roadmap

What is done, in progress and planned for the Nordfiber AB dataset. The scope (the physical and inventory layers and a
thin slice above them) is in `README.md`, the reasons behind it in `DESIGN.md`, the details of each release in
`CHANGELOG.md`. The NetBox stack the dataset is loaded into
([netbox-docker](https://github.com/Uttiponken/netbox-docker)) has a roadmap of its own.

## Done

Released `v0.1.0` to `v0.8.3` (2026-10-03 to 2026-11-03). Every release builds from an empty NetBox in one run and
passes `verify.py`. The milestones:

- **0.2.0** The build rewritten as seven layered, reconciling scripts.
- **0.5.0** FMS strands landed on panel ports, and a fiber circuit per trunk pair in use.
- **0.6.0** Stockholm in three zones with a metro ring; every plugin optional, so the dataset loads on a NetBox
  without plugins.
- **0.7.0** Loads into NetBox 4.7.3 (netbox-fms 0.6, netbox-pathways 0.3).
- **0.8.0** The North - West cable rerouted over Mälaren, the Helsinki route over Norrtälje, Åland and Turku.
- **0.8.1** The southern Baltic backup route (`BFN-DF-0001`) leg by leg over Nynäshamn, Gotland, Ventspils, Riga and
  Tallinn, as in `Baltic Route.md`.
- **0.8.2** Builds on netbox-wdm 0.2.2 and 0.3.0 (0.3.0 renamed the grid keys; the loader writes the key the installed
  version knows). Released together with netbox-docker v1.2.0, which moves to netbox-wdm 0.3.0.
- **0.8.3** Follows netbox-docker v1.3.0 (netbox-fms 0.8.0, netbox-notices 1.4.0, netbox-pathways 0.4.0): on
  netbox-pathways 0.4.0 and later an innerduct's owner is written with the innerduct; the data is unchanged.

0.8.0 also builds on netbox-docker v1.1.0 (with netbox-dns, netbox-notices, netbox-cable-labels and
netbox-topology-views added): 70 checks passed, 0 failed, and a second run changed nothing (2026-10-28). 0.8.2 builds
unchanged on netbox-docker v1.3.0 (netbox-fms 0.8.0, netbox-notices 1.4.0, netbox-pathways 0.4.0; 2026-11-02).

## In progress

Nothing at the moment. The in-place upgrade of a 0.8.0 database, open since 0.8.1, was done on 2026-11-02: the
development NetBox, built with 0.8.0, upgraded to netbox-docker v1.3.0, then `build.py` of 0.8.2 added the
leg-by-leg Baltic route (23 changes), a second run changed nothing, and `verify.py` passed 70 checks.

## Planned, when the stack changes

- **netbox-routing instead of netbox-bgp.** netbox-docker will replace netbox-bgp with netbox-routing once
  netbox-routing has a stable release; the two cannot run together. The dataset's BGP part is then rebuilt for
  netbox-routing: today `06_services.py` creates the peer group `NORDFIBER-IBGP` and a full iBGP mesh of 21 sessions
  among the seven core routers (`ROUTER_ORDER` in `data/services.py`) with netbox-bgp, and `verify.py` checks the
  mesh. That becomes netbox-routing's BGP objects, behind a `have("routing")` gate in `common.py` with a matching
  `verify.py` group, and `INFRASTRUCTURE.md`, `README.md` and a dated section in `DESIGN.md` follow.
  To decide then: keep the netbox-bgp path for NetBox installations that still have it, or drop it.
- **netbox-secrets back.** No change to the data: once netbox-docker carries a release for NetBox 4.7, running
  `build.py` again adds the encrypted login per router, and `verify.py` checks it again.

## To decide

- **The plugins added in netbox-docker v1.1.0, and FMS fiber faults.** The dataset uses none of them;
  netbox-topology-views needs no data of its own (it draws the existing cables), and `README.md` says so. Whether the
  dataset should show netbox-dns or netbox-notices (for example DNS records for the management and loopback
  addresses, or maintenance notices for the leased circuits), or a fiber fault with netbox-fms 0.7 and later (it would
  break the circuit on the faulted cable), is open; nothing is planned.

## Kept in reserve

From `DESIGN.md`; to be taken up only if a reason appears.

- **"NetBox can automate itself"**: a chapter with NetBox Custom Scripts, which run inside NetBox with the ORM, next to
  the REST API build.
- **Wireless links**: only for a real reason, such as microwave backhaul as a fiber backup between two nearby PoPs.
