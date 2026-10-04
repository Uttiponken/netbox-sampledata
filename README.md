# Nordfiber AB — NetBox sample dataset

An educational dataset for a fresh NetBox install: a fictional Nordic
fiber-optic network operator, **Nordfiber AB**, with three datacenters
(Stockholm, Gothenburg, Helsinki) and two points of presence (Malmö, Oslo),
colocation customers, leased dark fiber, a DWDM transport layer with lit
wavelength services, and everything from the building's racks and cables up
to management addressing, iBGP and encrypted device credentials.

The scope is the **physical and inventory layers**: organization, sites and
racks, devices, cabling, circuits, fiber plant, optical transport. Above
that only a thin slice (management IPs, loopbacks, iBGP, credentials) is
modeled; VPNs, VLAN plans, service IPs and the like are out of scope, as is
power.

**Standalone project.** Everything is loaded over NetBox's REST API
([pynetbox](https://github.com/netbox-community/pynetbox)); point
`NETBOX_URL`/`NETBOX_TOKEN` (in `.env`) at any reachable NetBox. It is
developed against a local `netbox-docker` deployment with the plugins
`netbox-bgp`, `-fms`, `-inventory`, `-otp`, `-secrets`, `-wdm`, `-floorplan`
and `-pathways` (the last needs PostGIS). `docs/INFRASTRUCTURE.md` describes
what the finished dataset looks like; `docs/DESIGN.md` records why it is
built the way it is, and the history of how it got here.

## Layout

The build is seven layers, each a script that depends only on the ones
before it, plus an invariant check:

| Script | Layer |
|---|---|
| `01_organization.py` | Tenant groups, tenants, regions, site groups, sites, one Location per room, contacts and their assignments |
| `02_hardware.py` | Manufacturers, device and module types (fetched live from the NetBox community library), the WDM profile and its 40-channel plan, roles, racks, devices (placed in uniform rack slots, with serials and asset tags), DCP-110 modules |
| `03_cabling.py` | Cabling inside each building: core interconnects (full redundancy mesh at datacenters), out-of-band management, MeetMe-room jumpers and trunks, colo customers' chains, the Gothenburg office floor |
| `04_transport.py` | Providers, circuits, the long-haul cables (own backbone, the leased Oslo pair, the two leased spans to Helsinki) with their fiber plant (netbox-fms: cable records, every strand landed on its panel port, a fiber circuit for each trunk pair in use) and routes (netbox-pathways), circuit geometries, cabled circuit demarcs |
| `05_optical.py` | WDM line ports and cabling, DCP-2 client shelves, backbone handoffs, regeneration jumper, the three wavelength services (netbox-wdm) |
| `06_services.py` | Management prefixes and addresses, loopbacks and iBGP full mesh (netbox-bgp), device credentials (netbox-secrets), spare assets (netbox-inventory) |
| `07_finalize.py` | Prunes the duplicate wavelength paths netbox-wdm generates, re-checks stitching, prints totals |
| `verify.py` | Read-only invariants: sites look alike, cables carry full attributes, planned connections exist, paths are continuous, routes match their cables, no stale text. Exits non-zero on failure |
| `build.py` | Runs 01–07 then `verify.py` |

Supporting code: `common.py` (API helpers, `ensure()`), `cabling.py` (the one
place cables are made), `naming.py` (the naming convention), `layout.py`
(site profiles → racks and devices), and `data/` (the scenario itself as
plain Python: `organization`, `hardware`, `cabling`, `transport`, `optical`,
`services`). `tools/` has `reset_netbox.sh` (wipe a local netbox-docker),
`dump_state.py` and `diff_state.py` (compare two builds).

**To change the scenario, edit `data/`**, not the scripts. Adding a site is
one entry in `data/organization.py`; its racks and devices follow from the
site profile in `layout.py`, its cabling from `data/cabling.py`.

Every layer is idempotent and reconciling: re-running creates what is
missing and corrects what has drifted (`ensure()` in `common.py`), and a
second run of a finished build changes nothing. Layers must be run in order
on an empty NetBox the first time; after that any layer can be re-run alone.

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Create an API token for a dedicated service account (superuser) and put it
in `.env` as `NETBOX_TOKEN`. **NetBox 4.5+ tokens are hashed**: the full
`nbt_<key>.<secret>` value exists only at creation and can never be read
back, so copy it when you create it. For a local netbox-docker,
`tools/reset_netbox.sh` does this for you (see below).

```
NETBOX_URL=http://localhost:8000
NETBOX_TOKEN=nbt_<key>.<secret>
```

## Running

```bash
./.venv/bin/python build.py        # everything, then verify
./.venv/bin/python build.py 3 5    # only layers 3 to 5
./.venv/bin/python verify.py       # just the checks
```

A full build against an empty NetBox takes a few minutes (mostly cable
creation through the API).

**Secrets key.** `06_services.py` generates an RSA keypair for
netbox-secrets and keeps the private half in `.secrets_userkey.pem`
(gitignored, like `.env`). It exists in full only once; losing it makes the
stored secrets permanently undecryptable. The device passwords in
`data/services.py` are obvious placeholders.

## Resetting

```bash
tools/reset_netbox.sh [path-to-netbox-docker]
```

**Destructive**: removes the Postgres volume of the local netbox-docker
(PostGIS overlay), recreates the database and the `postgis` extension,
boots NetBox, creates the `demo-loader` superuser and API token (written to
`.env`, never printed) and deletes the now-invalid secrets key. Then run
`build.py`.

## Comparing two builds

```bash
./.venv/bin/python tools/dump_state.py /tmp/state.json
./.venv/bin/python tools/diff_state.py reference/state-before-refactor.json /tmp/state.json
```

`reference/state-before-refactor.json` is the state of the dataset before
the layered rewrite; `diff_state.py` applies the intended renames and shows
what is left. The remaining differences are all deliberate (see
`docs/DESIGN.md`, "The layered rewrite").

## Tenants

- **Nordfiber AB** (Internal) — owns the sites and core infrastructure.
- **Baltic Retail Group** (Customers) — an EPL Stockholm–Malmö with a
  protect path via Gothenburg, and a colocated server and switch at each end.
- **Polaris Cloud Services** (Customers) — colo at Stockholm and Gothenburg.
- **Västhamnen Logistics** (Customers) — colo at Gothenburg.
- **Fjord Media Networks** (Customers) — a wavelength service Stockholm–Oslo.
- **Skagerrak Interconnect AB**, **Öresund Exchange AB** (Facility
  Operators) — run the MeetMe rooms at Gothenburg/Oslo and Malmö.
- **Västkust Bredband AB**, **Nordic Subsea Networks AB**, **Baltic Fibre
  Networks OÜ** (Suppliers) — Nordfiber's Internet upstream and the two
  vendors of the leased fiber to Helsinki; tenants as well as providers so
  they can own demarc panels.

## Releases

Tagged `v0.1.0` to `v0.5.0`, listed in `CHANGELOG.md`. Every release builds from an empty NetBox in one run and
passes `verify.py`.

## Used to test netbox-trace-print

The dataset is the test data of the print plugin
([netbox-trace-print](https://github.com/Uttiponken/netbox-trace-print)), which prints cable traces as PDF:
long multi-site paths, 24-pair trunks, WDM services, fiber circuits and the colo tenants' chains. The
plugin's tests and sample printouts (0.5.0 and later) use dataset release 0.5.x; `docs/TESTING.md` in the plugin
repository explains how to build the data and run the tests against it.

## Not modeled, on purpose

Wireless links (no radio equipment in the scenario), customer CPE routers,
a second wavelength customer at Oslo, a DCP-110 shelf in front of the
Helsinki backbone wavelengths, a topology diagram plugin (none targets NetBox
4.6 yet), power, and anything above management addressing and iBGP.

## Authors

Co-authored by JP and Claude (Anthropic's AI assistant, model **Claude Sonnet 5.5**, `claude-sonnet-5-5`, used
through Claude Code): the scenario, the loader scripts, the checks and the documentation were developed together
in pair-programming sessions. Every commit made with Claude's help carries a `Co-Authored-By: Claude Sonnet 5.5`
line, so the model behind any change can be read from the history and compared with later ones.

**Fictional companies, real hardware.** Nordfiber AB and every customer, partner, provider, contact and circuit in
the dataset are invented; any resemblance to real companies or people is coincidental. The equipment is real
hardware, taken from these sources:

- **NetBox Community Device Type Library**
  ([netbox-community/devicetype-library](https://github.com/netbox-community/devicetype-library)): Juniper MX204,
  Arista DCS-7050SX3-48YC8-F and DCS-7010T-48, Dell PowerEdge R650 and OptiPlex SFF 7050, Smartoptics
  DCP-M40-PAM4-ER and DCP-2, and the Smartoptics DCP-110 module. They are fetched live from the library when
  `02_hardware.py` runs, never typed by hand, so the interfaces are the real ones.
- **Defined in this dataset**, because the library has no such model: a generic 1U LC patch panel with 24 duplex
  ports behind one 24-position rear port (the end of a 24-pair trunk), in `data/hardware.py`.
- **Corning's ALTOS loose-tube cable family** (a real product line,
  [corning.com](https://www.corning.com)) is the model for the fiber cable type: 48 fibers in four 12-fiber tubes
  with the DIN/IEC 60304 fiber colour code. The figures are chosen for the scenario; use Corning's datasheets
  for the real specification.
- **Real places** (Stockholm, Gothenburg, Malmö, Oslo, Helsinki and the towns along the long-haul routes) give the
  sites and the route geometry their coordinates; the cables, buildings and routes themselves are fictional.
