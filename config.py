"""
Nordfiber AB demo dataset — scenario data.

Nordfiber AB is a fictional regional fiber-optic network operator with its
core/HQ in Stockholm and points of presence in Gothenburg, Malmö, and Oslo
(Norway) — giving one cross-border site on purpose, since that's what
justifies an international leased/dark-fiber/wavelength circuit in later
phases. Three fictional customers colocate or lease services at different
subsets of these sites, so some sites end up single-tenant (just Nordfiber's
own infrastructure) and some end up multi-tenant (Nordfiber's core gear plus
a customer's colocated racks) — that split happens in 02_infrastructure.py,
once racks exist to actually assign a tenant to.

All contact emails use the .example TLD (RFC 2606, reserved for
documentation) — never a real domain.
"""

TENANT_GROUPS = [
    {"name": "Internal", "slug": "internal"},
    {"name": "Customers", "slug": "customers"},
]

TENANTS = [
    {
        "name": "Nordfiber AB",
        "slug": "nordfiber-ab",
        "group_slug": "internal",
        "description": "Regional fiber-optic network operator headquartered in Stockholm. Owns all sites and core infrastructure in this dataset.",
    },
    {
        "name": "Baltic Retail Group",
        "slug": "baltic-retail-group",
        "group_slug": "customers",
        "description": "Nordic retail chain. Leases inter-site WAN connectivity between its Stockholm and Malmö distribution centers.",
    },
    {
        "name": "Polaris Cloud Services",
        "slug": "polaris-cloud-services",
        "group_slug": "customers",
        "description": "Cloud hosting provider. Colocates compute racks at the Stockholm DC and Gothenburg PoP.",
    },
    {
        "name": "Västhamnen Logistics",
        "slug": "vasthamnen-logistics",
        "group_slug": "customers",
        "description": "Port logistics and container-tracking operator. Colocates edge-compute servers at the Gothenburg PoP for real-time IoT telemetry from Port of Gothenburg operations.",
    },
    {
        "name": "Fjord Media Networks",
        "slug": "fjord-media-networks",
        "group_slug": "customers",
        "description": "Broadcast/media company. Leases a high-bandwidth wavelength service between Oslo and Stockholm.",
    },
]

# Regions: parent listed before children. `parent_slug: None` = top-level.
REGIONS = [
    {"name": "Nordics", "slug": "nordics", "parent_slug": None},
    {"name": "Sweden", "slug": "sweden", "parent_slug": "nordics"},
    {"name": "Norway", "slug": "norway", "parent_slug": "nordics"},
]

SITE_GROUPS = [
    {"name": "Data Centers", "slug": "data-centers"},
    {"name": "Points of Presence", "slug": "points-of-presence"},
]

SITES = [
    {
        "name": "Nordfiber Stockholm DC",
        "slug": "nordfiber-stockholm-dc",
        "status": "active",
        "region_slug": "sweden",
        "group_slug": "data-centers",
        "tenant_slug": "nordfiber-ab",
        "facility": "STO1",
        "physical_address": "Kungsholms Strand 39, 112 27 Stockholm, Sweden",
        "time_zone": "Europe/Stockholm",
        "latitude": 59.3293,
        "longitude": 18.0686,
        "description": "Primary data center and network core (HQ).",
    },
    {
        # Upgraded to a Datacenter, Phase 16 (2026-09-30) — name and
        # group_slug changed, but the slug ("...-gothenburg-pop") and every
        # got-*/gothenburg-pop-prefixed Location/Rack/Device slug elsewhere
        # in this file are DELIBERATELY left unchanged: renaming those too
        # would touch nearly every phase's config for no functional gain.
        "name": "Nordfiber Gothenburg DC",
        "slug": "nordfiber-gothenburg-pop",
        "status": "active",
        "region_slug": "sweden",
        "group_slug": "data-centers",
        "tenant_slug": "nordfiber-ab",
        "facility": "GOT1",
        "physical_address": "Lindholmspiren 5, 417 56 Göteborg, Sweden",
        "time_zone": "Europe/Stockholm",
        "latitude": 57.7089,
        "longitude": 11.9746,
        "description": "Second full datacenter (upgraded from a west coast point of presence, Phase 16).",
    },
    {
        "name": "Nordfiber Malmö PoP",
        "slug": "nordfiber-malmo-pop",
        "status": "active",
        "region_slug": "sweden",
        "group_slug": "points-of-presence",
        "tenant_slug": "nordfiber-ab",
        "facility": "MMA1",
        "physical_address": "Hyllie Boulevard 21, 215 32 Malmö, Sweden",
        "time_zone": "Europe/Stockholm",
        "latitude": 55.5636,
        "longitude": 12.9819,
        "description": "Southern point of presence, near the Öresund Bridge crossing to Denmark.",
    },
    {
        "name": "Nordfiber Oslo PoP",
        "slug": "nordfiber-oslo-pop",
        "status": "active",
        "region_slug": "norway",
        "group_slug": "points-of-presence",
        "tenant_slug": "nordfiber-ab",
        "facility": "OSL1",
        "physical_address": "Nydalsveien 28, 0484 Oslo, Norway",
        "time_zone": "Europe/Oslo",
        "latitude": 59.9139,
        "longitude": 10.7522,
        "description": "Cross-border point of presence into Norway.",
    },
]

# Locations: parent listed before children within the same site.
# `parent_slug: None` = top-level location within that site.
LOCATIONS = [
    {"name": "Suite 100", "slug": "stockholm-suite-100", "site_slug": "nordfiber-stockholm-dc", "parent_slug": None},
    {"name": "Row A", "slug": "stockholm-suite-100-row-a", "site_slug": "nordfiber-stockholm-dc", "parent_slug": "stockholm-suite-100"},
    {"name": "Row B", "slug": "stockholm-suite-100-row-b", "site_slug": "nordfiber-stockholm-dc", "parent_slug": "stockholm-suite-100"},
    {"name": "Telecom Room", "slug": "gothenburg-telecom-room", "site_slug": "nordfiber-gothenburg-pop", "parent_slug": None},
    {"name": "Telecom Room", "slug": "malmo-telecom-room", "site_slug": "nordfiber-malmo-pop", "parent_slug": None},
    {"name": "Telecom Room", "slug": "oslo-telecom-room", "site_slug": "nordfiber-oslo-pop", "parent_slug": None},
]

CONTACT_GROUPS = [
    {"name": "Network Operations", "slug": "network-operations"},
    {"name": "Customer Contacts", "slug": "customer-contacts"},
]

CONTACT_ROLES = [
    {"name": "NOC Engineer", "slug": "noc-engineer"},
    {"name": "Site Technician", "slug": "site-technician"},
    {"name": "Technical Contact", "slug": "technical-contact"},
]

CONTACTS = [
    {
        "name": "Erik Lindqvist",
        "group_slug": "network-operations",
        "title": "NOC Engineer",
        "email": "erik.lindqvist@nordfiber.example",
        "phone": "+46 70 123 45 67",
    },
    {
        "name": "Astrid Nilsen",
        "group_slug": "network-operations",
        "title": "Field Technician, Oslo",
        "email": "astrid.nilsen@nordfiber.example",
        "phone": "+47 400 12 345",
    },
    {
        "name": "Maria Svensson",
        "group_slug": "customer-contacts",
        "title": "IT Infrastructure Manager, Baltic Retail Group",
        "email": "maria.svensson@balticretail.example",
        "phone": "+46 70 555 11 22",
    },
    {
        "name": "Johan Eriksson",
        "group_slug": "customer-contacts",
        "title": "Head of Platform Engineering, Polaris Cloud Services",
        "email": "johan.eriksson@polariscloud.example",
        "phone": "+46 70 555 33 44",
    },
    {
        "name": "Lena Björk",
        "group_slug": "customer-contacts",
        "title": "Systems Engineer, Västhamnen Logistics",
        "email": "lena.bjork@vasthamnen.example",
        "phone": "+46 70 555 66 77",
    },
    {
        "name": "Ingrid Haugen",
        "group_slug": "customer-contacts",
        "title": "Broadcast Engineering Lead, Fjord Media Networks",
        "email": "ingrid.haugen@fjordmedia.example",
        "phone": "+47 400 99 887",
    },
]

# Contact assignments: (contact_name, role_slug, object_type, lookup for the
# assigned object). object_type is the NetBox "app_label.model" string used
# by its generic-relation ContactAssignment endpoint.
CONTACT_ASSIGNMENTS = [
    {"contact": "Erik Lindqvist", "role_slug": "noc-engineer", "object_type": "dcim.site", "site_slug": "nordfiber-stockholm-dc"},
    {"contact": "Erik Lindqvist", "role_slug": "noc-engineer", "object_type": "dcim.site", "site_slug": "nordfiber-gothenburg-pop"},
    {"contact": "Erik Lindqvist", "role_slug": "noc-engineer", "object_type": "dcim.site", "site_slug": "nordfiber-malmo-pop"},
    {"contact": "Erik Lindqvist", "role_slug": "noc-engineer", "object_type": "dcim.site", "site_slug": "nordfiber-oslo-pop"},
    {"contact": "Astrid Nilsen", "role_slug": "site-technician", "object_type": "dcim.site", "site_slug": "nordfiber-oslo-pop"},
    {"contact": "Maria Svensson", "role_slug": "technical-contact", "object_type": "tenancy.tenant", "tenant_slug": "baltic-retail-group"},
    {"contact": "Johan Eriksson", "role_slug": "technical-contact", "object_type": "tenancy.tenant", "tenant_slug": "polaris-cloud-services"},
    {"contact": "Lena Björk", "role_slug": "technical-contact", "object_type": "tenancy.tenant", "tenant_slug": "vasthamnen-logistics"},
    {"contact": "Ingrid Haugen", "role_slug": "technical-contact", "object_type": "tenancy.tenant", "tenant_slug": "fjord-media-networks"},
]

# ---------------------------------------------------------------------------
# Phase 2: Infrastructure
# ---------------------------------------------------------------------------
# Real vendor equipment, chosen deliberately:
#   - Juniper MX204: edge/core router, standardized across all four sites
#     (realistic for a regional carrier running one routing platform).
#   - Arista DCS-7050SX3-48YC8-F: aggregation switch, all four sites.
#   - Dell PowerEdge R650: generic colocated compute, representing
#     Polaris Cloud Services' equipment (not Nordfiber's own).
# Definitions are fetched live from the NetBox community devicetype-library
# (see common.fetch_devicetype_yaml) rather than hand-typed, so the actual
# interface lists are exactly what the real hardware has.

MANUFACTURERS = [
    {"name": "Juniper", "slug": "juniper"},
    {"name": "Arista", "slug": "arista"},
    {"name": "Dell", "slug": "dell"},
]

# (manufacturer key into MANUFACTURERS, devicetype-library path)
DEVICE_TYPE_SOURCES = [
    ("Juniper", "Juniper/MX204"),
    ("Arista", "Arista/DCS-7050SX3-48YC8-F"),
    ("Dell", "Dell/PowerEdge-R650"),
]

DEVICE_ROLES = [
    {"name": "Core Router", "slug": "core-router", "color": "2196f3"},
    {"name": "Aggregation Switch", "slug": "aggregation-switch", "color": "4caf50"},
    {"name": "Server", "slug": "server", "color": "9e9e9e"},
]

IPAM_ROLES = [
    {"name": "Management", "slug": "management", "weight": 100},
]

# Per-site out-of-band management /24, owned/operated by Nordfiber even in
# racks colocated to a customer (common real-world DC practice: the
# operator provides shared OOB/remote-hands access as a service).
MGMT_PREFIXES = [
    {"prefix": "10.0.1.0/24", "site_slug": "nordfiber-stockholm-dc", "tenant_slug": "nordfiber-ab"},
    {"prefix": "10.0.2.0/24", "site_slug": "nordfiber-gothenburg-pop", "tenant_slug": "nordfiber-ab"},
    {"prefix": "10.0.3.0/24", "site_slug": "nordfiber-malmo-pop", "tenant_slug": "nordfiber-ab"},
    {"prefix": "10.0.4.0/24", "site_slug": "nordfiber-oslo-pop", "tenant_slug": "nordfiber-ab"},
]

RACKS = [
    {"name": "STO-RACK-A1", "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-a", "tenant_slug": "nordfiber-ab"},
    {"name": "STO-RACK-B1", "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-b", "tenant_slug": "polaris-cloud-services"},
    {"name": "GOT-RACK-1", "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-telecom-room", "tenant_slug": "nordfiber-ab"},
    {"name": "GOT-RACK-2", "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-telecom-room", "tenant_slug": "polaris-cloud-services"},
    {"name": "GOT-RACK-3", "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-telecom-room", "tenant_slug": "vasthamnen-logistics"},
    {"name": "MMA-RACK-1", "site_slug": "nordfiber-malmo-pop", "location_slug": "malmo-telecom-room", "tenant_slug": "nordfiber-ab"},
    {"name": "OSL-RACK-1", "site_slug": "nordfiber-oslo-pop", "location_slug": "oslo-telecom-room", "tenant_slug": "nordfiber-ab"},
]

# mgmt_ip is None for devices that don't get a primary IP in this phase
# (none currently — every device here gets an OOB mgmt IP).
DEVICES = [
    {
        "name": "sto-rtr-01", "device_type_slug": "juniper-mx204", "role_slug": "core-router",
        "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-a",
        "rack_name": "STO-RACK-A1", "position": 42, "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "fxp0", "mgmt_ip": "10.0.1.11/24", "ip_tenant_slug": "nordfiber-ab",
    },
    {
        "name": "sto-sw-01", "device_type_slug": "arista-dcs-7050sx3-48yc8-f", "role_slug": "aggregation-switch",
        "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-a",
        "rack_name": "STO-RACK-A1", "position": 41, "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "Management1", "mgmt_ip": "10.0.1.12/24", "ip_tenant_slug": "nordfiber-ab",
    },
    {
        "name": "got-rtr-01", "device_type_slug": "juniper-mx204", "role_slug": "core-router",
        "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-telecom-room",
        "rack_name": "GOT-RACK-1", "position": 42, "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "fxp0", "mgmt_ip": "10.0.2.11/24", "ip_tenant_slug": "nordfiber-ab",
    },
    {
        "name": "got-sw-01", "device_type_slug": "arista-dcs-7050sx3-48yc8-f", "role_slug": "aggregation-switch",
        "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-telecom-room",
        "rack_name": "GOT-RACK-1", "position": 41, "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "Management1", "mgmt_ip": "10.0.2.12/24", "ip_tenant_slug": "nordfiber-ab",
    },
    {
        "name": "mma-rtr-01", "device_type_slug": "juniper-mx204", "role_slug": "core-router",
        "site_slug": "nordfiber-malmo-pop", "location_slug": "malmo-telecom-room",
        "rack_name": "MMA-RACK-1", "position": 42, "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "fxp0", "mgmt_ip": "10.0.3.11/24", "ip_tenant_slug": "nordfiber-ab",
    },
    {
        "name": "mma-sw-01", "device_type_slug": "arista-dcs-7050sx3-48yc8-f", "role_slug": "aggregation-switch",
        "site_slug": "nordfiber-malmo-pop", "location_slug": "malmo-telecom-room",
        "rack_name": "MMA-RACK-1", "position": 41, "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "Management1", "mgmt_ip": "10.0.3.12/24", "ip_tenant_slug": "nordfiber-ab",
    },
    {
        "name": "osl-rtr-01", "device_type_slug": "juniper-mx204", "role_slug": "core-router",
        "site_slug": "nordfiber-oslo-pop", "location_slug": "oslo-telecom-room",
        "rack_name": "OSL-RACK-1", "position": 42, "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "fxp0", "mgmt_ip": "10.0.4.11/24", "ip_tenant_slug": "nordfiber-ab",
    },
    {
        "name": "osl-sw-01", "device_type_slug": "arista-dcs-7050sx3-48yc8-f", "role_slug": "aggregation-switch",
        "site_slug": "nordfiber-oslo-pop", "location_slug": "oslo-telecom-room",
        "rack_name": "OSL-RACK-1", "position": 41, "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "Management1", "mgmt_ip": "10.0.4.12/24", "ip_tenant_slug": "nordfiber-ab",
    },
    # Polaris Cloud Services colocated compute. Site's owning tenant stays
    # Nordfiber AB; the rack, the devices, AND the mgmt IP are tenanted to
    # Polaris — the standard NetBox pattern for "who actually owns this
    # thing" at successively finer grain than the site itself.
    {
        "name": "polaris-sto-srv-01", "device_type_slug": "dell-poweredge-r650", "role_slug": "server",
        "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-b",
        "rack_name": "STO-RACK-B1", "position": 42, "tenant_slug": "polaris-cloud-services",
        "mgmt_interface": "iDRAC9", "mgmt_ip": "10.0.1.21/24", "ip_tenant_slug": "polaris-cloud-services",
    },
    {
        "name": "polaris-sto-srv-02", "device_type_slug": "dell-poweredge-r650", "role_slug": "server",
        "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-b",
        "rack_name": "STO-RACK-B1", "position": 41, "tenant_slug": "polaris-cloud-services",
        "mgmt_interface": "iDRAC9", "mgmt_ip": "10.0.1.22/24", "ip_tenant_slug": "polaris-cloud-services",
    },
    {
        "name": "polaris-got-srv-01", "device_type_slug": "dell-poweredge-r650", "role_slug": "server",
        "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-telecom-room",
        "rack_name": "GOT-RACK-2", "position": 42, "tenant_slug": "polaris-cloud-services",
        "mgmt_interface": "iDRAC9", "mgmt_ip": "10.0.2.21/24", "ip_tenant_slug": "polaris-cloud-services",
    },
    {
        "name": "vasthamnen-got-srv-01", "device_type_slug": "dell-poweredge-r650", "role_slug": "server",
        "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-telecom-room",
        "rack_name": "GOT-RACK-3", "position": 42, "tenant_slug": "vasthamnen-logistics",
        "mgmt_interface": "iDRAC9", "mgmt_ip": "10.0.2.22/24", "ip_tenant_slug": "vasthamnen-logistics",
    },
]

# ---------------------------------------------------------------------------
# Phase 3: Connections
# ---------------------------------------------------------------------------
# Two kinds of cable, deliberately simple:
#   - "uplink": the site's router to its own aggregation switch (xe-0/1/0,
#     one of the router's 10GbE ports, kept separate from its 100GbE
#     et-0/0/0..3 ports which are reserved for Phase 4's inter-site
#     circuits).
#   - "cross-connect": a colocated customer's server uplinked into the
#     SAME switch Nordfiber operates in that rack — realistic for how a
#     small colo customer's single-homed server actually gets network
#     access, and a good demo of NetBox modeling a cable between two
#     different tenants' equipment.
# Known simplification, noted rather than hidden: the switch's data ports
# are all optical (25G/100G); the servers' data port is 1000BASE-T copper.
# Real hardware would need a 1000BASE-T SFP in the switch or a media
# converter to make this exact link physically real — NetBox's Cable model
# doesn't enforce physical media compatibility, so this doesn't block
# anything, but it's a corner cut for dataset simplicity, not an oversight.
# label = physical cable ID, printed-on-the-jacket style: "<site>-cbl-<NNNNN>",
# site-scoped sequential numbering (each site restarts at 00001), reusing
# the same site prefixes already used in device names (sto/got/mma/osl).
# 5-digit zero-padding (bumped from 3, per user preference 2026-09-27, to
# match their real numbering convention) avoids a cbl-9-vs-cbl-10 sort
# problem at any realistic scale.
# comments = human-readable description of what the cable is for; this used
# to live in `label` and was moved here since a real label needs to be a
# short physical ID, not a description.
# tenant reflects who owns/operates the physical CABLE itself, not who
# commercially benefits from what rides over it: Nordfiber-to-Nordfiber
# links (uplinks) are tenanted to Nordfiber; a cross-connect landing on a
# customer's own colocated device is tenanted to that customer, matching
# how that device/rack was already tenanted back in Phase 2.
CABLES = [
    {"a_device": "sto-rtr-01", "a_iface": "xe-0/1/0", "b_device": "sto-sw-01", "b_iface": "Ethernet1", "label": "sto-cbl-00001", "comments": "sto-rtr-01 <-> sto-sw-01 uplink", "tenant_slug": "nordfiber-ab"},
    {"a_device": "sto-sw-01", "a_iface": "Ethernet2", "b_device": "polaris-sto-srv-01", "b_iface": "Gig-E 1", "label": "sto-cbl-00002", "comments": "Polaris cross-connect", "tenant_slug": "polaris-cloud-services"},
    {"a_device": "sto-sw-01", "a_iface": "Ethernet3", "b_device": "polaris-sto-srv-02", "b_iface": "Gig-E 1", "label": "sto-cbl-00003", "comments": "Polaris cross-connect", "tenant_slug": "polaris-cloud-services"},
    {"a_device": "got-rtr-01", "a_iface": "xe-0/1/0", "b_device": "got-sw-01", "b_iface": "Ethernet1", "label": "got-cbl-00001", "comments": "got-rtr-01 <-> got-sw-01 uplink", "tenant_slug": "nordfiber-ab"},
    {"a_device": "got-sw-01", "a_iface": "Ethernet2", "b_device": "polaris-got-srv-01", "b_iface": "Gig-E 1", "label": "got-cbl-00002", "comments": "Polaris cross-connect", "tenant_slug": "polaris-cloud-services"},
    {"a_device": "got-sw-01", "a_iface": "Ethernet3", "b_device": "vasthamnen-got-srv-01", "b_iface": "Gig-E 1", "label": "got-cbl-00003", "comments": "Vasthamnen cross-connect", "tenant_slug": "vasthamnen-logistics"},
    {"a_device": "mma-rtr-01", "a_iface": "xe-0/1/0", "b_device": "mma-sw-01", "b_iface": "Ethernet1", "label": "mma-cbl-00001", "comments": "mma-rtr-01 <-> mma-sw-01 uplink", "tenant_slug": "nordfiber-ab"},
    {"a_device": "osl-rtr-01", "a_iface": "xe-0/1/0", "b_device": "osl-sw-01", "b_iface": "Ethernet1", "label": "osl-cbl-00001", "comments": "osl-rtr-01 <-> osl-sw-01 uplink", "tenant_slug": "nordfiber-ab"},
]

# ---------------------------------------------------------------------------
# Phase 4: Circuits
# ---------------------------------------------------------------------------
# Two circuits telling two different real-world stories:
#   1. Nordfiber AB SELLS a lit Ethernet circuit to Baltic Retail Group,
#      Stockholm <-> Malmo, riding over Nordfiber's own fiber (built in
#      Phase 5/FMS). Provider = Nordfiber AB (as a Provider object,
#      distinct from — but referring to the same company as — the Tenant
#      of the same name; NetBox tracks "who owns this" and "who sells this
#      service" as separate concerns, and a company is very often both).
#   2. Nordfiber AB BUYS (leases) dark fiber from a wholesale transit
#      provider for the harder cross-border segment, Stockholm <-> Oslo —
#      realistic: regional carriers rarely own fiber across a national
#      border themselves. Tenant on this circuit is Nordfiber AB (they're
#      the customer here, not the provider). This leased dark fiber is
#      deliberately left UNTERMINATED to any device interface in this
#      phase: dark fiber has no active gear on it yet. It becomes a real
#      physical asset in Phase 5 (FMS) and gets lit by Nordfiber's own
#      SmartOptics WDM equipment in Phase 6 — which is what Fjord Media
#      Networks' wavelength service (see their tenant description) will
#      actually ride over.

PROVIDERS = [
    {"name": "Nordfiber AB", "slug": "nordfiber-ab", "description": "Nordfiber acting as a provider: the circuits it sells to its own customers."},
    {"name": "Polarlink Transit", "slug": "polarlink-transit", "description": "Fictional pan-Nordic wholesale dark fiber and transit provider. Leases a cross-border dark fiber pair to Nordfiber AB for the Stockholm-Oslo route."},
]

CIRCUIT_TYPES = [
    {"name": "Ethernet Private Line", "slug": "epl", "color": "2196f3"},
    {"name": "Dark Fiber", "slug": "dark-fiber", "color": "795548"},
]

CIRCUITS = [
    {
        "cid": "NF-BRG-0001",
        "provider_slug": "nordfiber-ab",
        "type_slug": "epl",
        "tenant_slug": "baltic-retail-group",
        "status": "active",
        "commit_rate": 10_000_000,  # Kbps = 10 Gbps (upgraded from 1 Gbps, Phase 15, 2026-09-30)
        "description": "Baltic Retail Group leased line, Stockholm <-> Malmo",
        "terminations": [
            {
                "term_side": "A", "site_slug": "nordfiber-stockholm-dc",
                "device": "sto-rtr-01", "iface": "et-0/0/0",
                "cable_label": "sto-cbl-00004",
            },
            {
                "term_side": "Z", "site_slug": "nordfiber-malmo-pop",
                "device": "mma-rtr-01", "iface": "et-0/0/0",
                "cable_label": "mma-cbl-00002",
            },
        ],
    },
    {
        "cid": "PLT-100234",
        "provider_slug": "polarlink-transit",
        "type_slug": "dark-fiber",
        "tenant_slug": "nordfiber-ab",
        "status": "active",
        "commit_rate": None,  # unlit fiber, no bandwidth to commit to
        "description": "Leased dark fiber pair, Stockholm <-> Oslo (cross-border) — to be lit with Nordfiber's own WDM equipment (Phase 6)",
        "terminations": [
            {"term_side": "A", "site_slug": "nordfiber-stockholm-dc", "device": None, "iface": None, "cable_label": None},
            {"term_side": "Z", "site_slug": "nordfiber-oslo-pop", "device": None, "iface": None, "cable_label": None},
        ],
    },
]

# ---------------------------------------------------------------------------
# Phase 5: FMS (fiber physical plant)
# ---------------------------------------------------------------------------
# Three backbone fiber runs, all sharing one real-world-modeled cable type:
#   - STO<->GOT and STO<->MMA: Nordfiber's OWN fiber (Stockholm is the hub;
#     this is the physical path Baltic Retail Group's EPL circuit from
#     Phase 4 actually rides over).
#   - STO<->OSL: the physical realization of the dark fiber Nordfiber
#     LEASES from Polarlink Transit (circuit PLT-100234, Phase 4) — same
#     cable type, since Nordfiber doesn't control what Polarlink installed,
#     but conceptually a different ownership story (noted in its FiberCable
#     notes). Left unlit — no WDM gear connects to it until Phase 6.
#
# Termination point: a small LC patch panel at each site (real generic
# device from the devicetype-library), NOT the routers directly. Real
# outside-plant fiber lands on a demarc/ODF, not straight into a router's
# optics. Patch panel FRONT ports are deliberately left uncabled in this
# phase — nothing needs to cross-connect to them yet (Phase 4's circuit
# terminations were already cabled straight to the routers as a
# pre-existing simplification, not retrofitted here; Phase 6's WDM
# transponders will be the first real consumer of a front-port cross-connect).
#
# Cable label scheme extended from Phase 3's site-scoped "<site>-cbl-NNN":
# backbone runs cross two sites, so they get their own "bb-cbl-NNN"
# namespace instead of arbitrarily picking one site's sequence.

FMS_MANUFACTURERS = [
    {"name": "Generic", "slug": "generic"},
    {"name": "Corning", "slug": "corning"},
]

FMS_DEVICE_TYPE_SOURCES = [
    ("Generic", "Generic/LC-24-port-fiber-patch-panel"),
]

FMS_DEVICE_ROLES = [
    {"name": "Patch Panel", "slug": "patch-panel", "color": "607d8b"},
]

PATCH_PANELS = [
    {"name": "sto-patch-01", "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-a", "rack_name": "STO-RACK-A1", "position": 40, "tenant_slug": "nordfiber-ab"},
    {"name": "got-patch-01", "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-telecom-room", "rack_name": "GOT-RACK-1", "position": 40, "tenant_slug": "nordfiber-ab"},
    {"name": "mma-patch-01", "site_slug": "nordfiber-malmo-pop", "location_slug": "malmo-telecom-room", "rack_name": "MMA-RACK-1", "position": 40, "tenant_slug": "nordfiber-ab"},
    {"name": "osl-patch-01", "site_slug": "nordfiber-oslo-pop", "location_slug": "oslo-telecom-room", "rack_name": "OSL-RACK-1", "position": 40, "tenant_slug": "nordfiber-ab"},
]

# Real product line: Corning ALTOS is an actual outdoor loose-tube cable
# family. din_iec_60304 color scheme chosen for Nordic-region authenticity
# (consistent with SmartOptics being a Norwegian vendor, Phase 2) rather
# than defaulting to the more US-centric EIA/598.
FMS_CABLE_TYPE = {
    "manufacturer_name": "Corning",
    "model": "ALTOS Loose Tube 24F SM",
    "construction": "loose_tube",
    "strand_count": 24,
    "color_scheme": "din_iec_60304",
    "sheath_material": "hdpe",
    "deployment": "duct",
    "is_armored": True,
    "armor_type": "steel_tape",
}

FMS_BUFFER_TUBE_TEMPLATES = [
    {"name": "Tube 1", "position": 1, "fiber_count": 12},
    {"name": "Tube 2", "position": 2, "fiber_count": 12},
]

# tenant is nordfiber-ab on all three, including bb-cbl-00003: Nordfiber
# operates/uses that fiber even though it's leased rather than owned,
# consistent with circuit PLT-100234 (Phase 4) also being tenanted to
# Nordfiber AB as the paying customer of that lease.
BACKBONE_FIBER_CABLES = [
    {
        "label": "bb-cbl-00001",
        "a_device": "sto-patch-01", "a_port": "Port 1",
        "b_device": "got-patch-01", "b_port": "Port 1",
        "comments": "Nordfiber-owned backbone, Stockholm <-> Gothenburg",
        "fms_notes": "Owned by Nordfiber AB. Carries in-country backbone traffic.",
        "tenant_slug": "nordfiber-ab",
    },
    {
        "label": "bb-cbl-00002",
        "a_device": "sto-patch-01", "a_port": "Port 2",
        "b_device": "mma-patch-01", "b_port": "Port 1",
        "comments": "Nordfiber-owned backbone, Stockholm <-> Malmo",
        "fms_notes": "Owned by Nordfiber AB. Physical path for Baltic Retail Group's EPL circuit NF-BRG-0001.",
        "tenant_slug": "nordfiber-ab",
    },
    {
        "label": "bb-cbl-00003",
        "a_device": "sto-patch-01", "a_port": "Port 3",
        "b_device": "osl-patch-01", "b_port": "Port 1",
        "comments": "Leased dark fiber (Polarlink Transit), Stockholm <-> Oslo",
        "fms_notes": "Leased from Polarlink Transit under circuit PLT-100234. Unlit — reserved for Nordfiber's own WDM equipment in Phase 6.",
        "tenant_slug": "nordfiber-ab",
    },
]

# ---------------------------------------------------------------------------
# Phase 6: WDM
# ---------------------------------------------------------------------------
# Lights the Stockholm <-> Oslo leased dark fiber (bb-cbl-00003 / circuit
# PLT-100234) with a real SmartOptics muxponder at each end, and reserves
# one ITU channel on it for Fjord Media Networks' wavelength service.
#
# Device: SmartOptics DCP-M40-PAM4-ER — real 1U 40-channel muxponder. Front
# ports are individually named/labeled by real ITU 100GHz-grid frequency
# ("921" = ITU channel 21, etc.) and all fan into one combined "Line" rear
# port (real device: one physical fiber pair carries all 40 multiplexed
# wavelengths). This is what makes the netbox-wdm plugin's own
# auto-computed channel labels line up with reality: creating a WDM node
# against this device type and a channel-plan entry at grid_position=1
# auto-generates a channel labeled "C21" at the correct ITU wavelength —
# verified empirically before writing this, not assumed from either the
# devicetype-library YAML or the plugin's docs alone.
#
# Physical path completed: WDM node's "Line" rear port <-> the SAME site's
# patch panel FRONT port that corresponds to the fiber going to the other
# site (front port N passes through to rear port N on our simple 24-port
# panel, and rear port N was already cabled to the right backbone fiber in
# Phase 5) <-> outside-plant fiber <-> far-end patch panel <-> far-end WDM
# node. This is the first phase where the patch panels' front ports
# (deliberately left uncabled since Phase 5) actually get used.

WDM_MANUFACTURERS = [
    {"name": "Smartoptics", "slug": "smartoptics"},
]

WDM_DEVICE_TYPE_SOURCES = [
    ("Smartoptics", "Smartoptics/DCP-M40-PAM4-ER"),
]

WDM_DEVICE_ROLES = [
    {"name": "WDM Terminal", "slug": "wdm-terminal", "color": "9c27b0"},
]

WDM_NODES = [
    {
        "name": "sto-wdm-01", "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-a",
        "rack_name": "STO-RACK-A1", "position": 39, "tenant_slug": "nordfiber-ab",
        # Front port "Port 3" on this panel passes through to rear "Port 3",
        # which Phase 5 cabled to Oslo via bb-cbl-00003.
        "patch_panel": "sto-patch-01", "patch_panel_front_port": "Port 3",
    },
    {
        "name": "osl-wdm-01", "site_slug": "nordfiber-oslo-pop", "location_slug": "oslo-telecom-room",
        "rack_name": "OSL-RACK-1", "position": 39, "tenant_slug": "nordfiber-ab",
        # osl-patch-01's rear "Port 1" is the Oslo end of bb-cbl-00003.
        "patch_panel": "osl-patch-01", "patch_panel_front_port": "Port 1",
    },
]

WDM_PROFILE = {
    "node_type": "terminal_mux",
    "grid": "dwdm_100ghz",
    "fiber_type": "single_fiber",  # one combined "Line" fiber pair carries all channels
}

# grid_position is a 1-based index into the device's real ITU front-port
# grid (position 1 = front port "921" = ITU channel 21) — NOT an arbitrary
# label. The plugin computes the real ITU wavelength/label itself; any
# label/wavelength_nm value supplied here is overridden, confirmed
# empirically, so none is provided.
WDM_CHANNEL_PLAN = [
    {"grid_position": 1, "front_port_name": "921"},
]

WDM_CIRCUIT = {
    "name": "Fjord Media Networks - Wavelength Service",
    "tenant_slug": "fjord-media-networks",
    "status": "active",
    "description": "ITU channel 21 (100GHz grid), Stockholm <-> Oslo, over Nordfiber's leased dark fiber (circuit PLT-100234)",
    "grid_position": 1,
}

# The missing piece that makes the wavelength service carry real traffic,
# not just exist as lit glass between two empty transponder ports: each
# WDM node's client-facing channel port (front port "921" = ITU channel 21)
# cross-connected to that site's own switch, on one of its spare 100GbE
# ports (Ethernet49/1 — untouched until now; Ethernet1-3 were already used
# for the router uplink and colo cross-connects in Phase 3). This is
# Nordfiber's own shared transport plumbing — the customer relationship
# lives on the WdmCircuit and the leased-fiber Circuit, not this cable.
WDM_CLIENT_CROSS_CONNECTS = [
    {
        "wdm_node": "sto-wdm-01", "wdm_front_port": "921",
        "switch": "sto-sw-01", "switch_iface": "Ethernet49/1",
        "label": "sto-wdm-01-client",
    },
    {
        "wdm_node": "osl-wdm-01", "wdm_front_port": "921",
        "switch": "osl-sw-01", "switch_iface": "Ethernet49/1",
        "label": "osl-wdm-01-client",
    },
]

# ---------------------------------------------------------------------------
# Phase 7: BGP, Secrets, Inventory
# ---------------------------------------------------------------------------

# -- BGP: a full iBGP mesh among Nordfiber's own 4 core routers, peered on
# loopback addresses (standard ISP practice — session survives any single
# physical link flapping). One private-use ASN (Nordfiber doesn't need a
# real public one for internal iBGP). Simplification, disclosed rather than
# silently made: one Session object per router PAIR (6 total for 4 routers),
# not one per router's own view of each peer (which would be 12) — a real
# deployment would configure and document both sides.
RIR_PRIVATE_USE = {"name": "Private Use (RFC 6996)", "slug": "private-use", "is_private": True}

BGP_ASN = {"asn": 65001, "description": "Nordfiber AB", "tenant_slug": "nordfiber-ab"}

LOOPBACKS = [
    {"device": "sto-rtr-01", "ip": "10.255.0.1/32"},
    {"device": "got-rtr-01", "ip": "10.255.0.2/32"},
    {"device": "mma-rtr-01", "ip": "10.255.0.3/32"},
    {"device": "osl-rtr-01", "ip": "10.255.0.4/32"},
]

BGP_PEER_GROUP = {
    "name": "NORDFIBER-IBGP",
    "description": "Full-mesh iBGP among Nordfiber's core routers",
}

BGP_SESSIONS = [
    {"device": "sto-rtr-01", "local_ip": "10.255.0.1/32", "remote_ip": "10.255.0.2/32", "name": "sto-rtr-01_got-rtr-01"},
    {"device": "sto-rtr-01", "local_ip": "10.255.0.1/32", "remote_ip": "10.255.0.3/32", "name": "sto-rtr-01_mma-rtr-01"},
    {"device": "sto-rtr-01", "local_ip": "10.255.0.1/32", "remote_ip": "10.255.0.4/32", "name": "sto-rtr-01_osl-rtr-01"},
    {"device": "got-rtr-01", "local_ip": "10.255.0.2/32", "remote_ip": "10.255.0.3/32", "name": "got-rtr-01_mma-rtr-01"},
    {"device": "got-rtr-01", "local_ip": "10.255.0.2/32", "remote_ip": "10.255.0.4/32", "name": "got-rtr-01_osl-rtr-01"},
    {"device": "mma-rtr-01", "local_ip": "10.255.0.3/32", "remote_ip": "10.255.0.4/32", "name": "mma-rtr-01_osl-rtr-01"},
]

# -- Secrets: netbox-secrets encrypts with an RSA keypair activated per
# NetBox user, not with a static site key — see 07's own module docstring
# for the full mechanics. Values below are obvious placeholders, never real
# credentials; a real deployment would generate genuinely random per-device
# passwords through a password manager, not predictable strings.
SECRET_ROLE = {"name": "Device Login", "slug": "device-login"}

DEVICE_SECRETS = [
    {"device": "sto-rtr-01", "name": "local-admin", "plaintext": "Nf-Sto-Rtr-D3mo!"},
    {"device": "got-rtr-01", "name": "local-admin", "plaintext": "Nf-Got-Rtr-D3mo!"},
    {"device": "mma-rtr-01", "name": "local-admin", "plaintext": "Nf-Mma-Rtr-D3mo!"},
    {"device": "osl-rtr-01", "name": "local-admin", "plaintext": "Nf-Osl-Rtr-D3mo!"},
]

# -- Inventory: a small spares depot at the Stockholm hub — one of each
# major chassis type in use, matching real practice of stocking a cold
# spare for anything whose failure would take a site fully offline.
ASSET_ROLES = [
    {"name": "Spare Chassis", "slug": "spare-chassis", "color": "ff9800"},
]

SPARE_ASSETS = [
    {"name": "Spare Juniper MX204", "device_type_slug": "juniper-mx204", "serial": "SPARE-MX204-001"},
    {"name": "Spare Arista DCS-7050SX3-48YC8-F", "device_type_slug": "arista-dcs-7050sx3-48yc8-f", "serial": "SPARE-7050-001"},
    {"name": "Spare SmartOptics DCP-M40-PAM4-ER", "device_type_slug": "smartoptics-dcp-m40-pam4-er", "serial": "SPARE-DCPM40-001"},
]

# ---------------------------------------------------------------------------
# Phase 8: Baltic Retail Group backup path (added post-hoc, 2026-09-27)
# ---------------------------------------------------------------------------
# A DWDM-based protect path for circuit NF-BRG-0001 (Phase 4), routed
# Stockholm <-> Gothenburg <-> Malmo instead of a second direct fiber run.
#
# Our WDM device (SmartOptics DCP-M40-PAM4-ER) is a simple TERMINAL MUX, not
# a ROADM — it can terminate a wavelength, not pass one through a site
# optically. A genuinely multi-hop path therefore needs two independent
# lit segments with ELECTRICAL REGENERATION at Gothenburg (two muxponders,
# back to back, jumpered client-port to client-port) rather than one
# continuous wavelength end to end. This is realistic for a regional
# carrier without ROADM investment, and it has a real modeling
# consequence, confirmed rather than assumed: netbox-wdm's /stitch/ will
# report TWO separate complete paths (STO<->GOT, GOT<->MMA), not one
# STO<->MMA path — which is the CORRECT representation of a regenerated
# circuit, not a bug to work around.
#
# Client-side handoff at Stockholm/Malmo lands on the SAME ROUTER that
# terminates the primary circuit (a spare 100GbE port, et-0/0/1 — et-0/0/0
# is the primary NF-BRG-0001 demarc), so the router itself can fail over
# between primary and backup paths — confirmed with the user rather than
# assumed, since Fjord Media's WDM handoff (Phase 6) went to a switch, a
# different, also-reasonable choice that didn't fit this specific case.
#
# The commercial Circuit's terminations are deliberately left uncabled to
# any device (same pattern as the dark-fiber circuit PLT-100234, Phase 4):
# the router ports are already physically used by the WDM client
# cross-connects below, so a SECOND direct cable from the CircuitTermination
# to the same router port would be physically impossible (one port, one
# cable) as well as redundant — the physical path is fully documented by
# the WDM/fiber layer instead.

NEW_BACKBONE_FIBER_CABLE = {
    "label": "bb-cbl-00004",
    "a_device": "got-patch-01", "a_port": "Port 2",
    "b_device": "mma-patch-01", "b_port": "Port 2",
    "comments": "Nordfiber-owned backbone, Gothenburg <-> Malmo",
    "fms_notes": "Owned by Nordfiber AB. Second leg of the Baltic Retail Group backup path (Phase 8), regenerated at Gothenburg.",
    "tenant_slug": "nordfiber-ab",
}

# sto-wdm-02 is a SEPARATE chassis from the existing sto-wdm-01, even
# though sto-wdm-01 has 39 unused channels that could technically host
# channel 22 instead. Confirmed with the user (2026-09-27) rather than
# assumed: a protect path sharing its primary's physical muxponder would
# defeat the point of protection (a chassis/card/software failure on
# sto-wdm-01 takes out the backup too, not just a fiber cut) — real path
# protection wants independent hardware, not just an independent
# wavelength on the same box. Gothenburg's two new nodes (below) are
# separate for a different, harder reason: the terminal-mux hardware can't
# pass a wavelength through a site at all (see the Phase 8 header comment).
BACKUP_WDM_NODES = [
    {
        "name": "sto-wdm-02", "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-a",
        "rack_name": "STO-RACK-A1", "position": 38, "tenant_slug": "nordfiber-ab",
        "patch_panel": "sto-patch-01", "patch_panel_front_port": "Port 1",  # passes to rear Port 1 -> bb-cbl-00001 -> Gothenburg
    },
    {
        "name": "got-wdm-01", "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-telecom-room",
        "rack_name": "GOT-RACK-1", "position": 39, "tenant_slug": "nordfiber-ab",
        "patch_panel": "got-patch-01", "patch_panel_front_port": "Port 1",  # passes to rear Port 1 -> bb-cbl-00001 -> Stockholm
    },
    {
        "name": "got-wdm-02", "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-telecom-room",
        "rack_name": "GOT-RACK-1", "position": 38, "tenant_slug": "nordfiber-ab",
        "patch_panel": "got-patch-01", "patch_panel_front_port": "Port 2",  # passes to rear Port 2 -> bb-cbl-00004 -> Malmo
    },
    {
        "name": "mma-wdm-01", "site_slug": "nordfiber-malmo-pop", "location_slug": "malmo-telecom-room",
        "rack_name": "MMA-RACK-1", "position": 39, "tenant_slug": "nordfiber-ab",
        "patch_panel": "mma-patch-01", "patch_panel_front_port": "Port 2",  # passes to rear Port 2 -> bb-cbl-00004 -> Gothenburg
    },
]

# Second ITU channel on the shared WDM_PROFILE (Phase 6) — grid_position 2
# = front port "922" = ITU channel 22, distinct from Fjord Media's channel
# 1/921. Adding this to the existing profile means sto-wdm-01/osl-wdm-01
# also gain an unused channel-2 slot — harmless spare capacity, consistent
# with a 40-channel muxponder.
BACKUP_WDM_CHANNEL_PLAN_ENTRY = {"grid_position": 2, "front_port_name": "922"}

# The Gothenburg regeneration jumper: got-wdm-01's and got-wdm-02's client
# ports patched directly together (both devices, same rack) rather than
# through the site switch — this IS the electrical regeneration point.
GOTHENBURG_REGEN_JUMPER = {
    "label": "got-cbl-00004",
    "a_device": "got-wdm-01", "a_front_port": "922",
    "b_device": "got-wdm-02", "b_front_port": "922",
    "comments": "Regeneration jumper: Baltic Retail Group backup path, STO-facing <-> MMA-facing WDM hop",
    "tenant_slug": "nordfiber-ab",
}

# Client handoff to the routers at each end of the backup path.
BACKUP_WDM_CLIENT_CROSS_CONNECTS = [
    {
        "wdm_node": "sto-wdm-02", "wdm_front_port": "922",
        "router": "sto-rtr-01", "router_iface": "et-0/0/1",
        "label": "sto-wdm-02-client",
    },
    {
        "wdm_node": "mma-wdm-01", "wdm_front_port": "922",
        "router": "mma-rtr-01", "router_iface": "et-0/0/1",
        "label": "mma-wdm-01-client",
    },
]

BACKUP_CIRCUIT = {
    "cid": "NF-BRG-0002",
    "provider_slug": "nordfiber-ab",
    "type_slug": "epl",
    "tenant_slug": "baltic-retail-group",
    "status": "active",
    "commit_rate": 10_000_000,  # matches NF-BRG-0001's upgrade, Phase 15
    "description": "Backup/protect path for NF-BRG-0001, Stockholm <-> Malmo via Gothenburg over DWDM (regenerated at got-wdm-01/got-wdm-02)",
    # Uncabled at both ends, same pattern as PLT-100234 (Phase 4): the
    # router ports are already physically used by the WDM client
    # cross-connects above, so the physical path is fully documented by the
    # WDM/fiber layer instead of a second cable to the same port.
    "terminations": [
        {"term_side": "A", "site_slug": "nordfiber-stockholm-dc", "device": None, "iface": None, "cable_label": None},
        {"term_side": "Z", "site_slug": "nordfiber-malmo-pop", "device": None, "iface": None, "cable_label": None},
    ],
}

# Two independent regenerated segments -> two WdmCircuits, one per segment,
# each stitched from the pair of devices that are actually physically
# connected for grid_position 2 (see 08's own script comments for how the
# right WdmWavelengthPath is identified per segment, since both segments
# share the same grid_position and aren't distinguishable by that alone).
BACKUP_WDM_CIRCUITS = [
    {
        "name": "Baltic Retail Group Backup - Segment 1 (Stockholm-Gothenburg)",
        "tenant_slug": "baltic-retail-group",
        "status": "active",
        "description": "First hop of NF-BRG-0002's backup path, ITU channel 22",
        "segment_devices": ("sto-wdm-02", "got-wdm-01"),
    },
    {
        "name": "Baltic Retail Group Backup - Segment 2 (Gothenburg-Malmo)",
        "tenant_slug": "baltic-retail-group",
        "status": "active",
        "description": "Second hop of NF-BRG-0002's backup path, ITU channel 22, regenerated at Gothenburg",
        "segment_devices": ("got-wdm-02", "mma-wdm-01"),
    },
]

# ---------------------------------------------------------------------------
# Phase 9: Erik Lindqvist's workplace + a Gothenburg Internet circuit
# (added post-hoc, 2026-09-27)
# ---------------------------------------------------------------------------
# Erik Lindqvist already exists as a Contact (NOC Engineer, assigned to all
# 4 sites, Phase 1). This gives him an actual physical workplace: a desk on
# an office floor at the Gothenburg PoP building, one floor above the
# ground-floor telecom room, wired the way a real office floor is — a
# copper (TP) outlet at his desk back to an IDF/distribution switch on the
# same floor, which then has its own fiber uplink down to the core switch
# in the telecom room. Modeled as two new Locations under the EXISTING
# nordfiber-gothenburg-pop site (not a new Site) — confirmed with the user
# as the simpler, still-realistic choice over a separate office site
# elsewhere in the city.
#
# IP addressing: both the IDF switch and Erik's PC sit on the SAME
# Gothenburg mgmt prefix (10.0.2.0/24) as the rest of the site's
# infrastructure, rather than a separate office/user VLAN — confirmed with
# the user as the simplest way to reflect "he can reach OOB management"
# without having to model a separate prefix + inter-VLAN routing policy
# that nothing else in this dataset enforces anyway.

GOTHENBURG_OFFICE_LOCATIONS = [
    {"name": "Office Floor 3", "slug": "gothenburg-office-floor-3", "site_slug": "nordfiber-gothenburg-pop", "parent_slug": None},
    {"name": "IDF Floor 3", "slug": "gothenburg-idf-floor-3", "site_slug": "nordfiber-gothenburg-pop", "parent_slug": None},
]

GOTHENBURG_OFFICE_RACKS = [
    {"name": "GOT-RACK-IDF3", "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-idf-floor-3", "tenant_slug": "nordfiber-ab"},
]

GOTHENBURG_OFFICE_DEVICE_ROLES = [
    {"name": "Access Switch", "slug": "access-switch", "color": "8bc34a"},
    {"name": "Workstation", "slug": "workstation", "color": "795548"},
]

# Both manufacturers (Arista, Dell) already exist from Phases 2/1 — only
# new device TYPES are needed here.
GOTHENBURG_OFFICE_DEVICE_TYPE_SOURCES = [
    ("Arista", "Arista/DCS-7010T-48"),   # 48x1000base-T copper + 4x10G SFP+ uplinks
    ("Dell", "Dell/OptiPlex-SFF-7050"),  # Erik's desktop
]

GOTHENBURG_OFFICE_DEVICES = [
    {
        "name": "got-idf-sw-01", "device_type_slug": "arista-dcs-7010t-48", "role_slug": "access-switch",
        "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-idf-floor-3",
        "rack_name": "GOT-RACK-IDF3", "position": 42, "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "Management1", "mgmt_ip": "10.0.2.13/24", "ip_tenant_slug": "nordfiber-ab",
    },
    {
        "name": "got-ws-erik", "device_type_slug": "dell-optiplex-sff-7050", "role_slug": "workstation",
        "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-office-floor-3",
        # Deliberately no rack/position — a desk PC isn't rack-mounted, unlike everything else in this dataset.
        "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "Gig-E 1", "mgmt_ip": "10.0.2.14/24", "ip_tenant_slug": "nordfiber-ab",
    },
]

# Erik's own workstation gets him as its device-level contact, in addition
# to his existing site-level NOC Engineer assignments (Phase 1).
GOTHENBURG_OFFICE_CONTACT_ASSIGNMENT = {
    "contact": "Erik Lindqvist", "role_slug": "noc-engineer", "device_name": "got-ws-erik",
}

# The TP outlet run: single cable standing in for the outlet + horizontal
# cabling, same simplification this dataset already uses elsewhere for
# patch-panel front ports (Phase 5/6/8) — there's no separate "wall jack"
# object in NetBox's data model.
GOTHENBURG_OFFICE_CABLES = [
    {
        "label": "got-cbl-00005",
        "a_device": "got-ws-erik", "a_iface": "Gig-E 1",
        "b_device": "got-idf-sw-01", "b_iface": "Ethernet1",
        "type": "cat6a",
        "comments": "TP outlet, Erik Lindqvist's desk (Office Floor 3) <-> IDF Floor 3 distribution switch",
        "tenant_slug": "nordfiber-ab",
    },
    {
        "label": "got-cbl-00006",
        "a_device": "got-idf-sw-01", "a_iface": "Ethernet49",
        "b_device": "got-sw-01", "b_iface": "Ethernet4",
        "type": "smf-os2",
        "comments": "Inter-floor riser fiber uplink, IDF Floor 3 <-> ground-floor telecom room",
        "tenant_slug": "nordfiber-ab",
    },
]

# A regional ISP the size of Nordfiber still has to buy its OWN upstream
# Internet transit somewhere — modeled as a single circuit at the
# Gothenburg PoP, terminated only on the A-side (the local demarc into
# got-rtr-01); the provider's own network beyond that isn't Nordfiber's to
# document, so there's no Z-side termination (valid in NetBox — a
# CircuitTermination's far end is optional).
GOTHENBURG_INTERNET_PROVIDER = {
    "name": "Vastkust Bredband AB",
    "slug": "vastkust-bredband-ab",
    "description": "Fictional regional Internet transit provider. Supplies Nordfiber AB's own upstream Internet access at the Gothenburg PoP.",
}

GOTHENBURG_INTERNET_CIRCUIT_TYPE = {"name": "Internet Access", "slug": "internet-access", "color": "00bcd4"}

GOTHENBURG_INTERNET_CIRCUIT = {
    "cid": "VKB-INET-0001",
    "provider_slug": "vastkust-bredband-ab",
    "type_slug": "internet-access",
    "tenant_slug": "nordfiber-ab",
    "status": "active",
    "commit_rate": 10_000_000,  # Kbps = 10 Gbps
    "description": "Nordfiber AB's own upstream Internet transit, Gothenburg PoP",
    "site_slug": "nordfiber-gothenburg-pop",
    "device": "got-rtr-01",
    "iface": "xe-0/1/1",
    "cable_label": "got-cbl-00007",
}

# ---------------------------------------------------------------------------
# Phase 10: WDM client demarc shelf (added post-hoc, 2026-09-27)
# ---------------------------------------------------------------------------
# One SmartOptics DCP-2 chassis at every site that has WDM equipment
# (Stockholm, Gothenburg, Malmo, Oslo), so a tenant is always handed a
# plain grey 1310/1550nm optic on a dedicated demarc shelf instead of
# patching straight into the DWDM muxponder's own channel port. Confirmed
# with the user (2026-09-27), including two real hardware findings that
# changed the original ask:
#
#   - The DCP-1610 module (10x independent 10G Line/Client transponder
#     pairs) does NOT fit here: its "Line" side is only 10G, but our
#     existing muxponder (DCP-M40-PAM4-ER) puts a full 100G signal on each
#     DWDM channel. There's no matching 10G-per-channel DWDM layer in this
#     dataset for it to plug into, so it's dropped for now (confirmed).
#   - The DCP-110 module (1x 100G Line QSFP28 + 10x 10G SFP+ Client) DOES
#     fit: its 100G Line port plugs straight into a muxponder channel front
#     port, and it hands out up to 10 independent grey 10G client ports
#     from that single wavelength. This is the only module deployed here.
#
# Retrofit (confirmed): Fjord Media's wavelength-service handoff (Phase 6)
# and the Baltic Retail Group backup path's router handoffs (Phase 8) are
# REWIRED through this shelf — the old direct muxponder-channel-to-router/
# switch cable is deleted and replaced with two cables: muxponder channel
# front port -> DCP-110 Line port, then DCP-110 Client port -> the same
# router/switch interface as before.
#
# Gothenburg is the one exception with nothing to retrofit: got-wdm-01's
# and got-wdm-02's only channel (922) is already fully consumed by the
# electrical-regeneration jumper between them (Phase 8), not a tenant
# handoff — there's no free channel there yet to plug the DCP-110 into. Its
# DCP-2 chassis and DCP-110 module are still created (available for
# whenever Gothenburg gets its own lit tenant channel) but left uncabled.
#
# Stockholm has TWO WDM nodes (sto-wdm-01 for Fjord Media, sto-wdm-02 for
# the Baltic Retail backup), so its one DCP-2 chassis uses BOTH module
# bays — one DCP-110 per node — rather than needing a second chassis.

DCP2_MANUFACTURERS = [
    {"name": "Smartoptics", "slug": "smartoptics"},
]

DCP2_DEVICE_TYPE_SOURCES = [
    ("Smartoptics", "Smartoptics/DCP-2"),
]

DCP2_MODULE_TYPE_SOURCES = [
    ("Smartoptics", "Smartoptics/DCP-110"),
]

DCP2_DEVICE_ROLES = [
    {"name": "WDM Client Shelf", "slug": "wdm-client-shelf", "color": "3f51b5"},
]

DCP2_CHASSIS = [
    {"name": "sto-dcp2-01", "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-a", "rack_name": "STO-RACK-A1", "position": 37, "tenant_slug": "nordfiber-ab"},
    {"name": "got-dcp2-01", "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-telecom-room", "rack_name": "GOT-RACK-1", "position": 37, "tenant_slug": "nordfiber-ab"},
    {"name": "mma-dcp2-01", "site_slug": "nordfiber-malmo-pop", "location_slug": "malmo-telecom-room", "rack_name": "MMA-RACK-1", "position": 37, "tenant_slug": "nordfiber-ab"},
    {"name": "osl-dcp2-01", "site_slug": "nordfiber-oslo-pop", "location_slug": "oslo-telecom-room", "rack_name": "OSL-RACK-1", "position": 37, "tenant_slug": "nordfiber-ab"},
]

# `module_position` is the DCP-2 module-bay's own `position` value
# (slot-1/1 = "1", slot-1/2 = "2") — NetBox substitutes this for the
# "{module}" placeholder in the DCP-110's interface-template names when the
# module is installed, giving real interfaces like "Line/1/1"/"Client/1/1".
DCP2_MODULES = [
    {"chassis": "sto-dcp2-01", "bay": "slot-1/1", "module_position": "1"},
    {"chassis": "sto-dcp2-01", "bay": "slot-1/2", "module_position": "2"},
    {"chassis": "got-dcp2-01", "bay": "slot-1/1", "module_position": "1"},
    {"chassis": "mma-dcp2-01", "bay": "slot-1/1", "module_position": "1"},
    {"chassis": "osl-dcp2-01", "bay": "slot-1/1", "module_position": "1"},
]

# Each entry retrofits one existing direct muxponder-to-client cable into
# muxponder -> DCP-110 Line -> DCP-110 Client -> (same client as before).
# The client-facing cable label is deliberately UNCHANGED — it's still the
# same logical tenant handoff, just physically re-landed one hop over.
DCP2_RETROFITS = [
    {
        "chassis": "sto-dcp2-01", "module_position": "1",
        "wdm_node": "sto-wdm-01", "wdm_front_port": "921",
        "client_device": "sto-sw-01", "client_iface": "Ethernet49/1",
        "line_cable_label": "sto-dcp2-01-mod1-line",
        "client_cable_label": "sto-wdm-01-client",
    },
    {
        "chassis": "sto-dcp2-01", "module_position": "2",
        "wdm_node": "sto-wdm-02", "wdm_front_port": "922",
        "client_device": "sto-rtr-01", "client_iface": "et-0/0/1",
        "line_cable_label": "sto-dcp2-01-mod2-line",
        "client_cable_label": "sto-wdm-02-client",
    },
    {
        "chassis": "mma-dcp2-01", "module_position": "1",
        "wdm_node": "mma-wdm-01", "wdm_front_port": "922",
        "client_device": "mma-rtr-01", "client_iface": "et-0/0/1",
        "line_cable_label": "mma-dcp2-01-mod1-line",
        "client_cable_label": "mma-wdm-01-client",
    },
    {
        "chassis": "osl-dcp2-01", "module_position": "1",
        "wdm_node": "osl-wdm-01", "wdm_front_port": "921",
        "client_device": "osl-sw-01", "client_iface": "Ethernet49/1",
        "line_cable_label": "osl-dcp2-01-mod1-line",
        "client_cable_label": "osl-wdm-01-client",
    },
]

# ---------------------------------------------------------------------------
# Phase 11: colo tenant fiber cross-connects via a MeetMe room
# (added post-hoc, 2026-09-27)
# ---------------------------------------------------------------------------
# Re-architects how Polaris Cloud Services and Vasthamnen Logistics (the
# two colo tenants — Baltic Retail Group and Fjord Media Networks are
# service customers, not colocated, and are unaffected) reach Nordfiber's
# network. Confirmed with the user across two rounds of questions:
#
#   OLD: tenant server -> (direct copper cable) -> Nordfiber's own switch.
#   NEW: tenant server -> tenant's OWN switch -> tenant's own top-of-rack
#        (ToR) fiber patch panel -> trunk -> tenant's own dedicated panel
#        in a MeetMe/cross-connect room -> trunk -> Nordfiber's EXISTING
#        patch panel (sto-patch-01/got-patch-01, reused rather than
#        duplicated) -> jumper -> Nordfiber's switch.
#
# Confirmed design points:
#   - Each tenant gets its OWN dedicated demarc panel in the MeetMe room
#     (not a shared port on someone else's panel) — matches real
#     carrier-neutral practice.
#   - Nordfiber's own link back to its rack REUSES the existing
#     sto-patch-01/got-patch-01 (already the site's fiber demarc for
#     backbone+WDM) rather than adding a parallel dedicated panel — same
#     front-port-jumper/rear-port-trunk pattern already used for WDM Line
#     ports (Phase 6/8).
#   - A MeetMe Location is created at all 4 sites for consistency, but
#     only Stockholm and Gothenburg get an actual rack + panels — Malmo
#     and Oslo have no colo tenants today, so there's nothing to demarc
#     there yet.
#   - CRITICAL correction from the user after the above was already
#     confirmed: the MeetMe room does NOT belong to Nordfiber. It's a
#     third-party carrier-neutral facility — Nordfiber is a customer of it
#     for cross-connect services, exactly like Polaris/Vasthamnen are.
#     This means the MeetMe room's RACK is tenanted to a NEW fictional
#     facility-operator tenant (Skagerrak Interconnect AB), not to
#     nordfiber-ab — even though the Location itself still sits under
#     Nordfiber's existing Site (a shared interconnection floor in the
#     same building Nordfiber's PoP occupies, a common real carrier-hotel
#     arrangement). Each party's OWN panel inside that rack still carries
#     ITS OWN tenant, same as before.
#
# A real, forced consequence of this topology (not an open choice, so not
# asked about): since both Stockholm Polaris servers now aggregate through
# ONE tenant-owned switch with ONE fiber uplink, Nordfiber only needs ONE
# port on sto-sw-01 for Polaris's cross-connect instead of two — the
# second (`sto-cbl-00003`'s old Nordfiber-side port) is simply freed, not
# replaced.

MEETME_TENANT_GROUPS = [
    {"name": "Facility Operators", "slug": "facility-operators"},
]

MEETME_TENANT = {
    "name": "Skagerrak Interconnect AB",
    "slug": "skagerrak-interconnect-ab",
    "group_slug": "facility-operators",
    "description": "Fictional carrier-neutral facility operator. Operates the MeetMe/cross-connect rooms; Nordfiber and its colo customers are all customers of this facility, not owners of the room.",
}

MEETME_LOCATIONS = [
    {"name": "MeetMe Room", "slug": "stockholm-meetme-room", "site_slug": "nordfiber-stockholm-dc", "parent_slug": None},
    {"name": "MeetMe Room", "slug": "gothenburg-meetme-room", "site_slug": "nordfiber-gothenburg-pop", "parent_slug": None},
    {"name": "MeetMe Room", "slug": "malmo-meetme-room", "site_slug": "nordfiber-malmo-pop", "parent_slug": None},
    {"name": "MeetMe Room", "slug": "oslo-meetme-room", "site_slug": "nordfiber-oslo-pop", "parent_slug": None},
]

# Only Stockholm and Gothenburg get an actual rack — Malmo/Oslo's MeetMe
# Locations exist (above) but stay empty until a colo tenant shows up there.
MEETME_RACKS = [
    # Corrected in Phase 12: Stockholm's MeetMe room is Nordfiber's OWN
    # (it's their datacenter, not a colocation PoP) — unlike the 3 PoPs,
    # where Nordfiber is itself a facility customer. get_or_create() never
    # updates an existing object's fields, so fixing this line alone isn't
    # enough — 12_meetme_ownership.py explicitly reconciles the live tenant.
    {"name": "STO-RACK-MMR1", "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-meetme-room", "tenant_slug": "nordfiber-ab"},
    {"name": "GOT-RACK-MMR1", "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-meetme-room", "tenant_slug": "skagerrak-interconnect-ab"},
]

# One entry per tenant-rack cross-connect chain. Reuses the Arista
# DCS-7010T-48 (Phase 9, copper client ports + SFP+ uplink) for the
# tenant's own switch, and the Generic 24-port LC patch panel (Phase 5)
# for every panel — ToR, MeetMe-room, AND Nordfiber's existing ones.
COLO_CROSSCONNECTS = [
    {
        "tenant_slug": "polaris-cloud-services",
        "colo_rack": "STO-RACK-B1",
        "switch_name": "polaris-sto-sw-01", "switch_position": 39,
        "tor_panel_name": "polaris-sto-tor-01", "tor_panel_position": 40,
        "servers": [
            {"device": "polaris-sto-srv-01", "iface": "Gig-E 1", "switch_iface": "Ethernet1", "cable_label": "sto-cbl-00002", "old_nordfiber_switch": "sto-sw-01", "old_nordfiber_iface": "Ethernet2"},
            {"device": "polaris-sto-srv-02", "iface": "Gig-E 1", "switch_iface": "Ethernet2", "cable_label": "sto-cbl-00003", "old_nordfiber_switch": "sto-sw-01", "old_nordfiber_iface": "Ethernet3"},
        ],
        "switch_uplink_iface": "Ethernet49",
        "tor_port": "Port 1",
        "mmr_location_slug": "stockholm-meetme-room",
        "mmr_rack": "STO-RACK-MMR1",
        "mmr_panel_name": "polaris-sto-mmr-01", "mmr_panel_position": 42,
        "mmr_port": "Port 1",
        "nordfiber_patch_panel": "sto-patch-01", "nordfiber_patch_port": "Port 4",
        "nordfiber_switch": "sto-sw-01", "nordfiber_switch_iface": "Ethernet2",
        "cables": {
            "switch_to_tor": "sto-cbl-00005",
            "tor_to_mmr": "sto-cbl-00006",
            "mmr_to_nordfiber_patch": "sto-cbl-00007",
            "nordfiber_patch_to_switch": "sto-cbl-00008",
        },
    },
    {
        "tenant_slug": "polaris-cloud-services",
        "colo_rack": "GOT-RACK-2",
        "switch_name": "polaris-got-sw-01", "switch_position": 40,
        "tor_panel_name": "polaris-got-tor-01", "tor_panel_position": 41,
        "servers": [
            {"device": "polaris-got-srv-01", "iface": "Gig-E 1", "switch_iface": "Ethernet1", "cable_label": "got-cbl-00002", "old_nordfiber_switch": "got-sw-01", "old_nordfiber_iface": "Ethernet2"},
        ],
        "switch_uplink_iface": "Ethernet49",
        "tor_port": "Port 1",
        "mmr_location_slug": "gothenburg-meetme-room",
        "mmr_rack": "GOT-RACK-MMR1",
        "mmr_panel_name": "polaris-got-mmr-01", "mmr_panel_position": 42,
        "mmr_port": "Port 1",
        "nordfiber_patch_panel": "got-patch-01", "nordfiber_patch_port": "Port 4",
        "nordfiber_switch": "got-sw-01", "nordfiber_switch_iface": "Ethernet2",
        "cables": {
            "switch_to_tor": "got-cbl-00008",
            "tor_to_mmr": "got-cbl-00009",
            "mmr_to_nordfiber_patch": "got-cbl-00010",
            "nordfiber_patch_to_switch": "got-cbl-00011",
        },
    },
    {
        "tenant_slug": "vasthamnen-logistics",
        "colo_rack": "GOT-RACK-3",
        "switch_name": "vasthamnen-got-sw-01", "switch_position": 40,
        "tor_panel_name": "vasthamnen-got-tor-01", "tor_panel_position": 41,
        "servers": [
            {"device": "vasthamnen-got-srv-01", "iface": "Gig-E 1", "switch_iface": "Ethernet1", "cable_label": "got-cbl-00003", "old_nordfiber_switch": "got-sw-01", "old_nordfiber_iface": "Ethernet3"},
        ],
        "switch_uplink_iface": "Ethernet49",
        "tor_port": "Port 1",
        "mmr_location_slug": "gothenburg-meetme-room",
        "mmr_rack": "GOT-RACK-MMR1",
        "mmr_panel_name": "vasthamnen-got-mmr-01", "mmr_panel_position": 41,
        "mmr_port": "Port 1",
        "nordfiber_patch_panel": "got-patch-01", "nordfiber_patch_port": "Port 5",
        "nordfiber_switch": "got-sw-01", "nordfiber_switch_iface": "Ethernet3",
        "cables": {
            "switch_to_tor": "got-cbl-00012",
            "tor_to_mmr": "got-cbl-00013",
            "mmr_to_nordfiber_patch": "got-cbl-00014",
            "nordfiber_patch_to_switch": "got-cbl-00015",
        },
    },
]

# ---------------------------------------------------------------------------
# Phase 12: MeetMe room ownership + empty-room racks (added post-hoc, 2026-09-27)
# ---------------------------------------------------------------------------
# Two corrections to Phase 11's MeetMe room model, both confirmed with the
# user across a further round of questions:
#
#   1. Malmo and Oslo's MeetMe rooms (created empty in Phase 11) now get
#      real racks. Room ownership follows a DC-vs-PoP pattern, confirmed
#      explicitly: Stockholm is Nordfiber's OWN datacenter, so ITS MeetMe
#      room's rack is tenanted to `nordfiber-ab` (corrected above — it was
#      wrongly tenanted to Skagerrak in Phase 11). Gothenburg and Oslo are
#      PoPs inside the SAME third-party facility operator, Skagerrak
#      Interconnect AB. Malmo is a PoP inside a DIFFERENT third-party
#      facility, so it gets its OWN new facility-operator tenant,
#      Oresund Exchange AB — confirmed explicitly: "the owner of these
#      meetme rooms are the providers housing Nordfiber as customers", not
#      a single company operating every PoP.
#   2. Every MeetMe room gets a Nordfiber-owned demarc panel — Nordfiber is
#      a facility customer at every PoP just like Polaris/Vasthamnen are,
#      so it needs its own dedicated panel there too, not just a trunk
#      straight through to its own equipment room. Confirmed: this panel
#      is INSERTED into the existing tenant cross-connect chains (the
#      tenant's MeetMe panel now jumpers to Nordfiber's MeetMe panel, which
#      then trunks back to sto-patch-01/got-patch-01 — a new hop, not a
#      replacement for the existing patch panels). Where Nordfiber already
#      OWNS the room (Stockholm), one panel does double duty as both "the
#      room owner's panel" and "Nordfiber's own demarc" — a separate
#      facility-operator panel there would be a pointless duplicate, since
#      Nordfiber IS the facility operator at that one site. Gothenburg,
#      Malmo, and Oslo each get TWO panels: the facility operator's own
#      (uncabled — it's their own administrative presence, not part of any
#      Nordfiber traffic path modeled here) and Nordfiber's (cabled into
#      the chain wherever a tenant is already present).
#
# This also finally makes the front/rear convention consistent everywhere
# in the MeetMe chain: REAR = trunk (outside this panel), FRONT = jumper/
# cross-connect (working side) — Phase 11's tenant-panel-front-to-
# Nordfiber's-own-patch-panel-REAR link skipped this by going straight
# from a meetme-room panel to a telecom-room panel in one hop; Phase 12
# splits that into a proper front-to-front cross-connect jumper (within
# the MeetMe room) followed by a proper rear-to-rear trunk (back to
# Nordfiber's equipment room).

MEETME_TENANT_2 = {
    "name": "Oresund Exchange AB",
    "slug": "oresund-exchange-ab",
    "group_slug": "facility-operators",
    "description": "Fictional carrier-neutral facility operator at Malmo, distinct from Skagerrak (Gothenburg/Oslo). Nordfiber colocates there as a customer, not an owner.",
}

MEETME_NEW_RACKS = [
    {"name": "MMA-RACK-MMR1", "site_slug": "nordfiber-malmo-pop", "location_slug": "malmo-meetme-room", "tenant_slug": "oresund-exchange-ab"},
    {"name": "OSL-RACK-MMR1", "site_slug": "nordfiber-oslo-pop", "location_slug": "oslo-meetme-room", "tenant_slug": "skagerrak-interconnect-ab"},
]

# One Nordfiber-owned demarc panel per MeetMe room, plus a facility-owner's
# own (uncabled) panel wherever that owner ISN'T Nordfiber itself.
MEETME_PANELS = [
    {"name": "sto-mmr-nordfiber-01", "rack": "STO-RACK-MMR1", "location_slug": "stockholm-meetme-room", "tenant_slug": "nordfiber-ab", "position": 41},
    {"name": "got-mmr-nordfiber-01", "rack": "GOT-RACK-MMR1", "location_slug": "gothenburg-meetme-room", "tenant_slug": "nordfiber-ab", "position": 40},
    {"name": "got-mmr-skagerrak-01", "rack": "GOT-RACK-MMR1", "location_slug": "gothenburg-meetme-room", "tenant_slug": "skagerrak-interconnect-ab", "position": 39},
    {"name": "mma-mmr-nordfiber-01", "rack": "MMA-RACK-MMR1", "location_slug": "malmo-meetme-room", "tenant_slug": "nordfiber-ab", "position": 41},
    {"name": "mma-mmr-oresund-01", "rack": "MMA-RACK-MMR1", "location_slug": "malmo-meetme-room", "tenant_slug": "oresund-exchange-ab", "position": 42},
    {"name": "osl-mmr-nordfiber-01", "rack": "OSL-RACK-MMR1", "location_slug": "oslo-meetme-room", "tenant_slug": "nordfiber-ab", "position": 41},
    {"name": "osl-mmr-skagerrak-01", "rack": "OSL-RACK-MMR1", "location_slug": "oslo-meetme-room", "tenant_slug": "skagerrak-interconnect-ab", "position": 42},
]

# Retrofits the 3 existing colo cross-connect chains (Phase 11) to insert
# Nordfiber's new MeetMe panel between the tenant's panel and Nordfiber's
# existing telecom-room patch panel. Deletes the old direct
# tenant-panel-to-sto/got-patch-01 cable and replaces it with two: a
# front-to-front cross-connect jumper (tenant panel <-> Nordfiber's panel,
# both in the MeetMe room) and a rear-to-rear trunk (Nordfiber's MeetMe
# panel back to sto-patch-01/got-patch-01). The jumper reuses the OLD
# cable's label (still the same logical cross-connect); the trunk gets a
# new one.
MEETME_RETROFITS = [
    {
        "tenant_mmr_panel": "polaris-sto-mmr-01", "tenant_mmr_port": "Port 1",
        "nordfiber_mmr_panel": "sto-mmr-nordfiber-01", "nordfiber_mmr_port": "Port 1",
        "nordfiber_patch_panel": "sto-patch-01", "nordfiber_patch_port": "Port 4",
        "old_cable_label": "sto-cbl-00007",
        "jumper_cable_label": "sto-cbl-00007",
        "trunk_cable_label": "sto-cbl-00009",
        "tenant_slug": "polaris-cloud-services",
    },
    {
        "tenant_mmr_panel": "polaris-got-mmr-01", "tenant_mmr_port": "Port 1",
        "nordfiber_mmr_panel": "got-mmr-nordfiber-01", "nordfiber_mmr_port": "Port 1",
        "nordfiber_patch_panel": "got-patch-01", "nordfiber_patch_port": "Port 4",
        "old_cable_label": "got-cbl-00010",
        "jumper_cable_label": "got-cbl-00010",
        "trunk_cable_label": "got-cbl-00016",
        "tenant_slug": "polaris-cloud-services",
    },
    {
        "tenant_mmr_panel": "vasthamnen-got-mmr-01", "tenant_mmr_port": "Port 1",
        "nordfiber_mmr_panel": "got-mmr-nordfiber-01", "nordfiber_mmr_port": "Port 2",
        "nordfiber_patch_panel": "got-patch-01", "nordfiber_patch_port": "Port 5",
        "old_cable_label": "got-cbl-00014",
        "jumper_cable_label": "got-cbl-00014",
        "trunk_cable_label": "got-cbl-00017",
        "tenant_slug": "vasthamnen-logistics",
    },
]

MEETME_FACILITY_CONTACTS = [
    {
        "name": "Fredrik Dahl",
        "group_slug": "customer-contacts",
        "title": "Facility Operations Manager, Skagerrak Interconnect AB",
        "email": "fredrik.dahl@skagerrakinterconnect.example",
        "phone": "+46 70 888 22 11",
        "tenant_slug": "skagerrak-interconnect-ab",
        "site_slugs": ["nordfiber-gothenburg-pop", "nordfiber-oslo-pop"],
        "racks": ["GOT-RACK-MMR1", "OSL-RACK-MMR1"],
        "devices": ["got-mmr-skagerrak-01", "osl-mmr-skagerrak-01"],
    },
    {
        "name": "Kristina Holm",
        "group_slug": "customer-contacts",
        "title": "Facility Operations Manager, Oresund Exchange AB",
        "email": "kristina.holm@oresundexchange.example",
        "phone": "+46 70 888 33 22",
        "tenant_slug": "oresund-exchange-ab",
        "site_slugs": ["nordfiber-malmo-pop"],
        "racks": ["MMA-RACK-MMR1"],
        "devices": ["mma-mmr-oresund-01"],
    },
]

# ---------------------------------------------------------------------------
# Phase 13: Vastkust Bredband AB's own MeetMe panel (added post-hoc,
# 2026-09-27)
# ---------------------------------------------------------------------------
# Applies the exact same splitting method already used in Phase 12 to
# `got-cbl-00007` (Phase 9's Internet-transit circuit demarc, previously a
# single direct cable from the circuit termination straight to
# got-rtr-01). Vastkust Bredband AB is Nordfiber's own upstream Internet
# provider — like any other party cross-connecting at this site, its fiber
# handoff gets its own dedicated panel in the Gothenburg MeetMe room rather
# than landing directly on Nordfiber's router.
#
# New chain (was 1 cable, now 4):
#   CircuitTermination -> Vastkust's own MeetMe panel (REAR: their incoming
#   fiber; FRONT: the jumper) -> Nordfiber's MeetMe panel (a new port,
#   since Port 1/2 are already Polaris/Vasthamnen) -> got-patch-01 (a new
#   spare port, Port 3) -> got-rtr-01:xe-0/1/1 (unchanged interface).
#
# Same labeling rule as Phase 12's retrofits: the segment immediately
# adjacent to the UNCHANGED endpoint (the CircuitTermination) keeps the old
# label; every newly-inserted segment gets a fresh one.

# Vastkust Bredband AB has existed as a circuits.Provider since Phase 9
# (Nordfiber's upstream Internet transit supplier) — but a Device's
# `tenant` field is a tenancy.Tenant, a different model entirely, so
# giving them an owned panel needs a matching Tenant record too. Same
# pattern already used for Nordfiber AB itself (both a Provider AND a
# Tenant, same slug, two different NetBox models for two different
# relationships). A new TenantGroup, "Suppliers", since Vastkust is the
# opposite commercial direction from "Customers" (Nordfiber buys from
# them, not the other way around) and isn't a facility operator either.
VASTKUST_TENANT_GROUP = {"name": "Suppliers", "slug": "suppliers"}

VASTKUST_TENANT = {
    "name": "Vastkust Bredband AB",
    "slug": "vastkust-bredband-ab",
    "group_slug": "suppliers",
    "description": "Nordfiber's upstream Internet transit supplier (Phase 9), also modeled as a Tenant here (Phase 13) so its own MeetMe-room panel can be owned by it.",
}

VASTKUST_MEETME_PANEL = {
    "name": "vastkust-got-panel-01", "rack": "GOT-RACK-MMR1", "location_slug": "gothenburg-meetme-room",
    "tenant_slug": "vastkust-bredband-ab", "position": 38,
}

VASTKUST_MEETME_RETROFIT = {
    "circuit_cid": "VKB-INET-0001", "circuit_term_side": "A",
    "vastkust_panel": "vastkust-got-panel-01", "vastkust_port": "Port 1",
    "nordfiber_mmr_panel": "got-mmr-nordfiber-01", "nordfiber_mmr_port": "Port 3",
    "nordfiber_patch_panel": "got-patch-01", "nordfiber_patch_port": "Port 3",
    "nordfiber_device": "got-rtr-01", "nordfiber_iface": "xe-0/1/1",
    "cables": {
        "circuit_to_vastkust_panel": "got-cbl-00007",
        "vastkust_panel_to_nordfiber_mmr": "got-cbl-00018",
        "nordfiber_mmr_to_patch": "got-cbl-00019",
        "patch_to_router": "got-cbl-00020",
    },
}

# ---------------------------------------------------------------------------
# Phase 14: full 40-channel WDM plan (added post-hoc, 2026-09-27)
# ---------------------------------------------------------------------------
# Only grid_position 1 (WDM_CHANNEL_PLAN, Phase 6) and 2
# (BACKUP_WDM_CHANNEL_PLAN_ENTRY, Phase 8) exist so far, even though the
# muxponder (SmartOptics DCP-M40-PAM4-ER) has 40 real channel front ports
# on its device type (confirmed live: "921" through "960"). User-requested:
# populate the rest (grid_position 3-40) so every WDM node's full capacity
# is represented, not just the 2 channels that happen to be lit.
#
# This is unlit SPARE capacity, same as grid_position 1/2 already were on
# every node other than the one pair each is actually cabled to (see
# Phase 6's own comment: adding a channel-plan entry to the shared profile
# gives EVERY existing node on it a new channel slot automatically, since
# WdmChannel auto-instantiates per node from the profile's channel plan).
#
# `front_port_name` continues the device type's own naming (grid_position
# N -> front port str(920+N), i.e. ITU channel (20+N)). `wavelength_nm` is
# only ever a placeholder (the plugin overrides the real value on the
# derived WdmChannel, but NOT on WdmChannelPlan itself — see Phase 8's
# comment) and must be unique per profile, so it continues the same
# `1550.0 + grid_position` scheme already used for grid_position 1 and 2.
WDM_REMAINING_CHANNEL_PLAN = [
    {"grid_position": n, "front_port_name": str(920 + n), "wavelength_nm": 1550.0 + n}
    for n in range(3, 41)
]

# ---------------------------------------------------------------------------
# Phase 16: Gothenburg PoP -> Datacenter, plus new growth capacity
# (added post-hoc, 2026-09-30)
# ---------------------------------------------------------------------------
# The Site's own name/group_slug change is in SITES above (Phase 1) — kept
# there rather than duplicated here, since SITES is the single source of
# truth for the site record and get_or_create() needs the live values to
# reconcile against. This section only adds the NEW growth capacity: one
# new Location ("Suite 200" / "Row C", mirroring Stockholm's Suite 100 /
# Row A|B naming) with 2 new empty racks — real datacenters carry spare
# white space, unlike a lean PoP. Deliberately left unpopulated: no new
# tenant or service was requested, just capacity.

GOTHENBURG_DC_LOCATIONS = [
    {"name": "Suite 200", "slug": "gothenburg-suite-200", "site_slug": "nordfiber-gothenburg-pop", "parent_slug": None},
    {"name": "Row C", "slug": "gothenburg-suite-200-row-c", "site_slug": "nordfiber-gothenburg-pop", "parent_slug": "gothenburg-suite-200"},
]

GOTHENBURG_DC_RACKS = [
    {"name": "GOT-RACK-C1", "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-suite-200-row-c", "tenant_slug": "nordfiber-ab"},
    {"name": "GOT-RACK-C2", "site_slug": "nordfiber-gothenburg-pop", "location_slug": "gothenburg-suite-200-row-c", "tenant_slug": "nordfiber-ab"},
]

# ---------------------------------------------------------------------------
# Phase 17: Helsinki DC + dual leased dark fiber to Stockholm
# (added post-hoc, 2026-09-30)
# ---------------------------------------------------------------------------
# A third, smaller Nordfiber-owned datacenter (Finland — a new Region,
# alongside Sweden/Norway) built the same way Malmo/Oslo were: one rack,
# one router, one switch, one patch panel. Reached from Stockholm over TWO
# independently-routed leased dark fiber pairs from TWO DIFFERENT vendors —
# confirmed with the user across several questions:
#   - Dark fiber, lit later (same pattern as the existing Polarlink/Oslo
#     leg) — NOT lit as part of this phase. Both terminations are left
#     uncabled, exactly like PLT-100234.
#   - One primary (the shorter route) + one backup (the longer, more
#     diverse route) rather than active/active — matching this dataset's
#     existing Baltic Retail Group backup-path pattern.
#   - The physical route itself is modeled as REAL geography via the
#     newly-adopted netbox-pathways plugin's `circuit-geometries` endpoint
#     (a real multi-point LineString attached directly to the Circuit) —
#     the right-sized fit for "here is the real route", as opposed to
#     building out full conduit/duct-bank physical plant, which nothing
#     here asked for. No new NetBox Sites are created at the waypoints
#     (Mariehamn, Vaasa, Gotland, Riga, Tallinn) — Nordfiber has no actual
#     equipment there, just transit fiber passing through.
#
# Following this dataset's established convention: kept as its own
# self-contained phase, NOT appended into Phase 1/2's global
# REGIONS/SITES/LOCATIONS/RACKS/DEVICES/MGMT_PREFIXES lists (same as every
# other post-hoc phase's new devices/sites).

HELSINKI_REGION = {"name": "Finland", "slug": "finland", "parent_slug": "nordics"}

HELSINKI_SITE = {
    "name": "Nordfiber Helsinki DC",
    "slug": "nordfiber-helsinki-dc",
    "status": "active",
    "region_slug": "finland",
    "group_slug": "data-centers",
    "tenant_slug": "nordfiber-ab",
    "facility": "HEL1",
    "physical_address": "Ratamestarinkatu 11, 00520 Helsinki, Finland",
    "time_zone": "Europe/Helsinki",
    "latitude": 60.1699,
    "longitude": 24.9384,
    "description": "Third datacenter — smaller footprint, reached from Stockholm over two independently-routed leased dark fiber pairs.",
}

HELSINKI_LOCATIONS = [
    {"name": "Telecom Room", "slug": "helsinki-telecom-room", "site_slug": "nordfiber-helsinki-dc", "parent_slug": None},
]

HELSINKI_RACKS = [
    {"name": "HEL-RACK-1", "site_slug": "nordfiber-helsinki-dc", "location_slug": "helsinki-telecom-room", "tenant_slug": "nordfiber-ab"},
]

HELSINKI_MGMT_PREFIX = {"prefix": "10.0.5.0/24", "site_slug": "nordfiber-helsinki-dc", "tenant_slug": "nordfiber-ab"}

HELSINKI_DEVICES = [
    {
        "name": "hel-rtr-01", "device_type_slug": "juniper-mx204", "role_slug": "core-router",
        "site_slug": "nordfiber-helsinki-dc", "location_slug": "helsinki-telecom-room",
        "rack_name": "HEL-RACK-1", "position": 42, "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "fxp0", "mgmt_ip": "10.0.5.11/24", "ip_tenant_slug": "nordfiber-ab",
    },
    {
        "name": "hel-sw-01", "device_type_slug": "arista-dcs-7050sx3-48yc8-f", "role_slug": "aggregation-switch",
        "site_slug": "nordfiber-helsinki-dc", "location_slug": "helsinki-telecom-room",
        "rack_name": "HEL-RACK-1", "position": 41, "tenant_slug": "nordfiber-ab",
        "mgmt_interface": "Management1", "mgmt_ip": "10.0.5.12/24", "ip_tenant_slug": "nordfiber-ab",
    },
]

HELSINKI_UPLINK_CABLE = {
    "a_device": "hel-rtr-01", "a_iface": "xe-0/1/0", "b_device": "hel-sw-01", "b_iface": "Ethernet1",
    "label": "hel-cbl-00001", "comments": "hel-rtr-01 <-> hel-sw-01 uplink", "tenant_slug": "nordfiber-ab",
}

FMS_HELSINKI_PATCH_PANEL = {
    "name": "hel-patch-01", "site_slug": "nordfiber-helsinki-dc", "location_slug": "helsinki-telecom-room",
    "rack_name": "HEL-RACK-1", "position": 40, "tenant_slug": "nordfiber-ab",
}

# Two new fictional dark-fiber transit vendors — deliberately different
# companies from Polarlink Transit (the existing Oslo dark-fiber lessor),
# since the user asked for two DIFFERENT vendors on two DIFFERENT routes.
HELSINKI_FIBER_PROVIDERS = [
    {
        "name": "Nordic Subsea Networks AB",
        "slug": "nordic-subsea-networks-ab",
        "description": "Fictional Nordic submarine/terrestrial fiber transit vendor. Leases Route 1 (Stockholm-Mariehamn-Vaasa-Helsinki) to Nordfiber AB.",
    },
    {
        "name": "Baltic Fibre Networks OU",
        "slug": "baltic-fibre-networks-ou",
        "description": "Fictional Baltic-states fiber transit vendor. Leases Route 2 (Stockholm-Gotland-Riga-Tallinn-Helsinki) to Nordfiber AB.",
    },
]

# Both circuits uncabled at both ends (device: None), same pattern as
# PLT-100234 (Phase 4) — dark fiber, no active gear on it until a future
# phase lights it.
HELSINKI_FIBER_CIRCUITS = [
    {
        "cid": "NSN-DF-0001",
        "provider_slug": "nordic-subsea-networks-ab",
        "type_slug": "dark-fiber",
        "tenant_slug": "nordfiber-ab",
        "status": "active",
        "commit_rate": None,
        "role": "primary",
        "description": "Primary leased dark fiber pair, Stockholm <-> Helsinki via Mariehamn (Aland) and Vaasa. Shorter of the two routes.",
        "terminations": [
            {"term_side": "A", "site_slug": "nordfiber-stockholm-dc", "device": None, "iface": None, "cable_label": None},
            {"term_side": "Z", "site_slug": "nordfiber-helsinki-dc", "device": None, "iface": None, "cable_label": None},
        ],
        "route_waypoints": [
            ("Stockholm", 18.0686, 59.3293),
            ("Mariehamn (Aland)", 19.9348, 60.0971),
            ("Vaasa", 21.6165, 63.0951),
            ("Helsinki", 24.9384, 60.1699),
        ],
    },
    {
        "cid": "BFN-DF-0001",
        "provider_slug": "baltic-fibre-networks-ou",
        "type_slug": "dark-fiber",
        "tenant_slug": "nordfiber-ab",
        "status": "active",
        "commit_rate": None,
        "role": "backup",
        "description": "Backup leased dark fiber pair, Stockholm <-> Helsinki via Gotland, Riga (Latvia), and Tallinn (Estonia). Longer, geographically diverse route.",
        "terminations": [
            {"term_side": "A", "site_slug": "nordfiber-stockholm-dc", "device": None, "iface": None, "cable_label": None},
            {"term_side": "Z", "site_slug": "nordfiber-helsinki-dc", "device": None, "iface": None, "cable_label": None},
        ],
        "route_waypoints": [
            ("Stockholm", 18.0686, 59.3293),
            ("Visby (Gotland)", 18.2948, 57.6348),
            ("Riga", 24.1052, 56.9496),
            ("Tallinn", 24.7536, 59.4370),
            ("Helsinki", 24.9384, 60.1699),
        ],
    },
]

# ---------------------------------------------------------------------------
# Phase 18: real route geography for the domestic backbone fiber
# (added post-hoc, 2026-09-30)
# ---------------------------------------------------------------------------
# User-requested: the same real-route treatment Phase 17 gave the Helsinki
# dark fiber, now for the 3 ORIGINAL backbone cables (Phase 5) — but these
# are physical dcim.Cables (FMS FiberCables), not commercial circuits.Circuit
# objects, so `circuit-geometries` (Phase 17's endpoint) doesn't apply here.
#
# Verified empirically before building this: netbox-pathways models a
# physical route as its own object (a `DirectBuried` pathway here — fiber
# genuinely buried alongside a road corridor, the realistic real-world
# choice over `aerial-spans`/`conduit-banks`), which carries the `path`
# LineString itself; a separate `CableSegment` join record is what actually
# links that route to a real `dcim.Cable` (confirmed live: `cable` +
# `pathway` + `sequence`, and creating one correctly bumped the pathway's
# own `cables_routed` counter from 0 to 1).
#
# Routes as given by the user, one DirectBuried + one CableSegment per
# cable:
#   - bb-cbl-00001 (Stockholm<->Gothenburg): via Vasteras, Orebro,
#     Karlstad, Trollhattan (swapped in for Tanumshede, 2026-09-30, at the
#     user's request) — NOT the shortest real route (that would go via
#     Orebro/Skovde), but this is the user's own specified path, followed
#     as given rather than "corrected" to the shortest real one.
#   - bb-cbl-00002 (Stockholm<->Malmo): via the E4, through Linkoping,
#     Jonkoping, Markaryd, Hassleholm, Lund.
#   - bb-cbl-00003 (Stockholm<->Oslo): CORRECTED 2026-10-02. It was first
#     built as Gothenburg->E6->Oslo, but the cable itself is physically
#     Stockholm<->Oslo (sto-patch-01 to osl-patch-01) — the geometry
#     contradicted the cable and the mismatch wasn't flagged at the time.
#     Now Stockholm via Vasteras, Orebro, Karlstad, Charlottenberg (the
#     E18 corridor) to Oslo, as specified by the user.
BACKBONE_CABLE_ROUTES = [
    {
        "cable_label": "bb-cbl-00001",
        "pathway_label": "bb-cbl-00001-route",
        "comments": "Stockholm <-> Gothenburg via Vasteras, Orebro, Karlstad, Trollhattan",
        "waypoints": [
            ("Stockholm", 18.0686, 59.3293),
            ("Vasteras", 16.5528, 59.6099),
            ("Orebro", 15.2066, 59.2741),
            ("Karlstad", 13.5116, 59.3793),
            ("Trollhattan", 12.2886, 58.2837),
            ("Gothenburg", 11.9746, 57.7089),
        ],
    },
    {
        "cable_label": "bb-cbl-00002",
        "pathway_label": "bb-cbl-00002-route",
        "comments": "Stockholm <-> Malmo via the E4: Linkoping, Jonkoping, Markaryd, Hassleholm, Lund",
        "waypoints": [
            ("Stockholm", 18.0686, 59.3293),
            ("Linkoping", 15.6214, 58.4108),
            ("Jonkoping", 14.1618, 57.7826),
            ("Markaryd", 13.5975, 56.4402),
            ("Hassleholm", 13.7660, 56.1590),
            ("Lund", 13.1910, 55.7047),
            ("Malmo", 12.9819, 55.5636),
        ],
    },
    {
        "cable_label": "bb-cbl-00003",
        "pathway_label": "bb-cbl-00003-route",
        "comments": "Stockholm <-> Oslo (leased, Polarlink Transit) via Vasteras, Orebro, Karlstad, Charlottenberg",
        "waypoints": [
            ("Stockholm", 18.0686, 59.3293),
            ("Vasteras", 16.5528, 59.6099),
            ("Orebro", 15.2066, 59.2741),
            ("Karlstad", 13.5116, 59.3793),
            ("Charlottenberg", 12.2942, 59.8900),
            ("Oslo", 10.7522, 59.9139),
        ],
    },
]

# ---------------------------------------------------------------------------
# Phase 19: Helsinki MeetMe room + lighting the two leased dark fiber
# pairs (added post-hoc, 2026-10-01)
# ---------------------------------------------------------------------------
# Two gaps found by the user while reviewing live data, both fixed here:
#   1. Helsinki never got a MeetMe room — every other site (Stockholm,
#      Gothenburg, Malmo, Oslo) has one since Phase 11/12, but Helsinki
#      didn't exist yet at that time. Confirmed: Nordfiber-owned (like
#      Stockholm), since Helsinki is Nordfiber's own datacenter, not a
#      colocation PoP inside a third-party facility.
#   2. NSN-DF-0001 and BFN-DF-0001 (Phase 17) were left dark, as planned —
#      this phase lights them, which also means the two fiber vendors
#      (previously only `circuits.Provider` records, same gap as Vastkust
#      in Phase 13) need matching `tenancy.Tenant` records too, so they can
#      own a demarc panel at BOTH ends. Confirmed with the user: a leased
#      fiber pair has two physical ends, so each vendor gets its own panel
#      at Stockholm AND Helsinki — not just Helsinki as first described.
#
# Each circuit's lit path (7 physical cable segments, mirroring Phase
# 11/12/13's trunk/jumper conventions — REAR = trunk/outside this panel,
# FRONT = jumper/cross-connect — plus 2 client handoffs). IMPORTANT,
# caught only by testing the WDM trace after the first build attempt: the
# physical fiber does NOT run through the Circuit's own CircuitTermination
# objects — those stay UNCABLED, exactly like PLT-100234 (confirmed live:
# both its terminations have cable=None). A commercial Circuit in this
# dataset is a billing/contractual record, deliberately disconnected from
# the physical cable graph; the real long-haul span is modeled the same
# way bb-cbl-00001/2/3 model Nordfiber's OWN backbone fiber — as ONE
# direct dcim.Cable between two real ports, here the two vendor panels at
# either end (REAR-to-REAR, matching bb-cbl-00003's own rear-to-rear
# pattern):
#
#   sto-wdm-0X:Line --[WDM x-connect]--> sto-patch-01 (front<->rear)
#     --[trunk]--> sto-mmr-nordfiber-01 (rear<->front)
#     --[jumper]--> sto-mmr-<vendor>-01 (front<->rear)
#     --[the leased fiber span itself, a real Cable]--> hel-mmr-<vendor>-01
#     (rear<->front) --[jumper]--> hel-mmr-nordfiber-01 (front<->rear)
#     --[trunk]--> hel-patch-01 (rear<->front)
#     --[WDM x-connect]--> hel-wdm-0Y:Line
#
# (CircuitTermination A/Z remain uncabled, as Phase 17 originally built
# them — the diagram above has no CircuitTermination step at all.)
#
# Client handoff (so the wavelength carries real traffic, not just lit
# glass — same principle as Phase 6's own comment): each muxponder's
# channel 1 front port ("921") goes DIRECTLY to a spare 100GE port on the
# local router (sto-rtr-01/hel-rtr-01) — NOT through the DCP-2/DCP-110
# client shelf (Phase 10), since that shelf exists specifically for
# handing a GREY optic to an external customer; these two links are
# Nordfiber's own internal backbone connectivity between its own routers,
# so no customer-facing demarc applies. Flagged as a judgment call, not
# confirmed with the user — easy to add a DCP-110 hop later if wanted.
#
# Channel 1 (front port "921") was chosen for every new node — grid
# positions 1-40 already exist on the shared profile (Phase 14), so each
# new device auto-instantiates all 40 channels on creation; channel 1 is
# simply the first one, with 39 spare on each new node exactly like
# everywhere else in this dataset.
#
# NEW UPSTREAM LIMITATION, found and confirmed while verifying this phase:
# netbox-wdm's own /trace/ action returns completely empty (is_complete:
# false, elements: [], wavelength_path_id: null — not even a duplicate
# entry, confirmed at the SQL level: zero rows reference either new
# channel in netbox_wdm_wdmwavelengthpathchannel) for sto-wdm-03 and
# sto-wdm-04's channel 1, despite the physical cabling being verified
# 100% correct and continuous, port by port, by hand. The one genuinely
# novel thing about this topology vs. every other lit path in this
# dataset: it's the FIRST Line-side physical path to route through a
# front-port-to-front-port cable (the two MeetMe-room "jumper" hops) —
# every prior lit path (Oslo, the Baltic Retail backup) uses exactly one
# intermediate patch panel per hop, relying on that panel's own built-in
# front<->rear template mapping to pass through, never a direct
# front-to-front cable between two DIFFERENT panels. Best explanation:
# netbox-wdm's path walker assumes that single-panel-passthrough shape
# and doesn't know how to continue past a front port that's cabled
# directly (rather than via its own device's rear-port mapping).
# Not treated as a reason to re-architect the physical model — the
# cabling already matches this dataset's own established MeetMe-room
# conventions exactly, and IS correct — this is a plugin display/
# computation limitation, verified via manual cable-chain inspection
# instead (same category as the already-documented sync-ports 500 and
# duplicate-wavelength-path bugs).

HELSINKI_MEETME_LOCATION = {
    "name": "MeetMe Room", "slug": "helsinki-meetme-room", "site_slug": "nordfiber-helsinki-dc", "parent_slug": None,
}

HELSINKI_MEETME_RACK = {
    "name": "HEL-RACK-MMR1", "site_slug": "nordfiber-helsinki-dc", "location_slug": "helsinki-meetme-room", "tenant_slug": "nordfiber-ab",
}

# Nordic Subsea Networks AB / Baltic Fibre Networks OU have existed as
# circuits.Provider since Phase 17 — same gap as Vastkust Bredband AB in
# Phase 13, fixed the same way (matching Tenant record, Suppliers group,
# so they can own a Device).
FIBER_VENDOR_TENANTS = [
    {
        "name": "Nordic Subsea Networks AB", "slug": "nordic-subsea-networks-ab", "group_slug": "suppliers",
        "description": "Fictional Nordic fiber transit vendor (Phase 17); also a Tenant since Phase 19 so it can own demarc panels at both ends of its leased route.",
    },
    {
        "name": "Baltic Fibre Networks OU", "slug": "baltic-fibre-networks-ou", "group_slug": "suppliers",
        "description": "Fictional Baltic-states fiber transit vendor (Phase 17); also a Tenant since Phase 19 so it can own demarc panels at both ends of its leased route.",
    },
]

HELSINKI_MEETME_PANELS = [
    {"name": "hel-mmr-nordfiber-01", "tenant_slug": "nordfiber-ab", "position": 42},
    {"name": "hel-mmr-nsn-01", "tenant_slug": "nordic-subsea-networks-ab", "position": 41},
    {"name": "hel-mmr-bfn-01", "tenant_slug": "baltic-fibre-networks-ou", "position": 40},
]

STOCKHOLM_MEETME_VENDOR_PANELS = [
    {"name": "sto-mmr-nsn-01", "tenant_slug": "nordic-subsea-networks-ab", "position": 40},
    {"name": "sto-mmr-bfn-01", "tenant_slug": "baltic-fibre-networks-ou", "position": 39},
]

HELSINKI_LIGHTING_WDM_NODES = [
    {"name": "sto-wdm-03", "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-a", "rack_name": "STO-RACK-A1", "position": 36, "tenant_slug": "nordfiber-ab"},
    {"name": "sto-wdm-04", "site_slug": "nordfiber-stockholm-dc", "location_slug": "stockholm-suite-100-row-a", "rack_name": "STO-RACK-A1", "position": 35, "tenant_slug": "nordfiber-ab"},
    {"name": "hel-wdm-01", "site_slug": "nordfiber-helsinki-dc", "location_slug": "helsinki-telecom-room", "rack_name": "HEL-RACK-1", "position": 39, "tenant_slug": "nordfiber-ab"},
    {"name": "hel-wdm-02", "site_slug": "nordfiber-helsinki-dc", "location_slug": "helsinki-telecom-room", "rack_name": "HEL-RACK-1", "position": 38, "tenant_slug": "nordfiber-ab"},
]

HELSINKI_LIGHTING_CHAINS = [
    {
        "circuit_cid": "NSN-DF-0001",
        "vendor_tenant_slug": "nordic-subsea-networks-ab",
        "sto_wdm_node": "sto-wdm-03", "hel_wdm_node": "hel-wdm-01",
        "sto_patch_port": "Port 5", "hel_patch_port": "Port 1",
        "sto_mmr_nordfiber_port": "Port 2", "hel_mmr_nordfiber_port": "Port 1",
        "sto_mmr_vendor_panel": "sto-mmr-nsn-01", "hel_mmr_vendor_panel": "hel-mmr-nsn-01",
        "sto_mmr_vendor_port": "Port 1", "hel_mmr_vendor_port": "Port 1",
        "sto_router_iface": "et-0/0/2", "hel_router_iface": "et-0/0/0",
        "channel_front_port": "921",
        "cables": {
            "sto_patch_to_wdm": "sto-wdm-03-line",
            "sto_patch_to_mmr_nordfiber": "sto-cbl-00010",
            "sto_mmr_nordfiber_to_vendor": "sto-cbl-00011",
            "vendor_span": "nsn-cbl-00001",
            "hel_mmr_vendor_to_nordfiber": "hel-cbl-00003",
            "hel_mmr_nordfiber_to_patch": "hel-cbl-00004",
            "hel_patch_to_wdm": "hel-wdm-01-line",
            "sto_wdm_client": "sto-wdm-03-client",
            "hel_wdm_client": "hel-wdm-01-client",
        },
    },
    {
        "circuit_cid": "BFN-DF-0001",
        "vendor_tenant_slug": "baltic-fibre-networks-ou",
        "sto_wdm_node": "sto-wdm-04", "hel_wdm_node": "hel-wdm-02",
        "sto_patch_port": "Port 6", "hel_patch_port": "Port 2",
        "sto_mmr_nordfiber_port": "Port 3", "hel_mmr_nordfiber_port": "Port 2",
        "sto_mmr_vendor_panel": "sto-mmr-bfn-01", "hel_mmr_vendor_panel": "hel-mmr-bfn-01",
        "sto_mmr_vendor_port": "Port 1", "hel_mmr_vendor_port": "Port 1",
        "sto_router_iface": "et-0/0/3", "hel_router_iface": "et-0/0/1",
        "channel_front_port": "921",
        "cables": {
            "sto_patch_to_wdm": "sto-wdm-04-line",
            "sto_patch_to_mmr_nordfiber": "sto-cbl-00013",
            "sto_mmr_nordfiber_to_vendor": "sto-cbl-00014",
            "vendor_span": "bfn-cbl-00001",
            "hel_mmr_vendor_to_nordfiber": "hel-cbl-00006",
            "hel_mmr_nordfiber_to_patch": "hel-cbl-00007",
            "hel_patch_to_wdm": "hel-wdm-02-line",
            "sto_wdm_client": "sto-wdm-04-client",
            "hel_wdm_client": "hel-wdm-02-client",
        },
    },
]

# ---------------------------------------------------------------------------
# Phase 20: uniform rack layout + out-of-band (OOB) management cabling
# (added post-hoc, 2026-10-02)
# ---------------------------------------------------------------------------
# Two user-requested changes from an audit of the live data:
#   1. Every rack of the same kind gets the same top-down layout, with 2U
#      gaps between different KINDS of equipment (room to grow). Before
#      this, positions were just "whatever order it was created in", so the
#      same device sat at different heights at different sites.
#   2. Every device's management port is cabled (the audit found 48
#      mgmt-only interfaces, none cabled, and no OOB hardware at all).
#      Missing hardware added: one 48-port copper OOB switch per site, in
#      the core rack (reuses the Arista DCS-7010T-48 already in the
#      dataset), uplinked to the site's core router.
#
# Layout (top-down; NetBox position 42 = top):
#   core racks:    42 patch panel | 41-40 gap | 39 OOB switch | 38-37 gap |
#                  36 router, 35 switch | 34-33 gap | 32.. WDM nodes |
#                  28 DCP-2 (fixed height so it lines up at every site;
#                  sites with fewer WDM nodes just have spare U above it)
#   customer racks: 42 ToR panel | 39 tenant switch | 36.. servers
#   MeetMe racks:  42 Nordfiber panel | 41 facility owner's own panel
#                  (where there is one) | 38.. external parties
#
# Scope decisions (flagged, not asked): ONE management port per device —
# DCP-2 chassis have five mgmt-only ports, so only if-1/eth1 (Management)
# is cabled, not the craft port. Colo tenants' servers AND switches are
# cabled too (Phase 2's premise: the operator provides OOB access to
# colo tenants as a service); those cables end on Nordfiber's OOB switch,
# so they are tenanted to Nordfiber per the cable tenancy rule. The
# Gothenburg IDF switch is cabled over a copper riser. Each OOB switch's
# OWN Management1 is left uncabled: it is reached through its uplink to
# the router (serial/console access is not modeled — out of scope).
# Passive panels have no management port. Power: out of scope.

RACK_LAYOUT = {
    "STO-RACK-A1": {"sto-patch-01": 42, "sto-rtr-01": 36, "sto-sw-01": 35, "sto-wdm-01": 32, "sto-wdm-02": 31, "sto-wdm-03": 30, "sto-wdm-04": 29, "sto-dcp2-01": 28},
    "GOT-RACK-1": {"got-patch-01": 42, "got-rtr-01": 36, "got-sw-01": 35, "got-wdm-01": 32, "got-wdm-02": 31, "got-dcp2-01": 28},
    "MMA-RACK-1": {"mma-patch-01": 42, "mma-rtr-01": 36, "mma-sw-01": 35, "mma-wdm-01": 32, "mma-dcp2-01": 28},
    "OSL-RACK-1": {"osl-patch-01": 42, "osl-rtr-01": 36, "osl-sw-01": 35, "osl-wdm-01": 32, "osl-dcp2-01": 28},
    "HEL-RACK-1": {"hel-patch-01": 42, "hel-rtr-01": 36, "hel-sw-01": 35, "hel-wdm-01": 32, "hel-wdm-02": 31},
    "STO-RACK-B1": {"polaris-sto-tor-01": 42, "polaris-sto-sw-01": 39, "polaris-sto-srv-01": 36, "polaris-sto-srv-02": 35},
    "GOT-RACK-2": {"polaris-got-tor-01": 42, "polaris-got-sw-01": 39, "polaris-got-srv-01": 36},
    "GOT-RACK-3": {"vasthamnen-got-tor-01": 42, "vasthamnen-got-sw-01": 39, "vasthamnen-got-srv-01": 36},
    "STO-RACK-MMR1": {"sto-mmr-nordfiber-01": 42, "polaris-sto-mmr-01": 38, "sto-mmr-nsn-01": 37, "sto-mmr-bfn-01": 36},
    "GOT-RACK-MMR1": {"got-mmr-nordfiber-01": 42, "got-mmr-skagerrak-01": 41, "polaris-got-mmr-01": 38, "vasthamnen-got-mmr-01": 37, "vastkust-got-panel-01": 36},
    "MMA-RACK-MMR1": {"mma-mmr-nordfiber-01": 42, "mma-mmr-oresund-01": 41},
    "OSL-RACK-MMR1": {"osl-mmr-nordfiber-01": 42, "osl-mmr-skagerrak-01": 41},
    "HEL-RACK-MMR1": {"hel-mmr-nordfiber-01": 42, "hel-mmr-nsn-01": 38, "hel-mmr-bfn-01": 37},
}

OOB_DEVICE_ROLE = {"name": "OOB Switch", "slug": "oob-switch", "color": "ffc107"}

# Management interface to cable, per device type.
OOB_MGMT_IFACE = {
    "juniper-mx204": "fxp0",
    "arista-dcs-7050sx3-48yc8-f": "Management1",
    "arista-dcs-7010t-48": "Management1",
    "smartoptics-dcp-m40-pam4-er": "Eth0 / Local",
    "smartoptics-dcp-2": "if-1/eth1",
    "dell-poweredge-r650": "iDRAC9",
}

# OOB switch port plan — the SAME slots at every site: 1 router, 2 switch,
# 3-6 WDM nodes, 7 DCP-2, 8+ everything else. `label_start` continues each
# site's existing cable numbering (gaps left by earlier deleted cables are
# deliberately not back-filled).
def _oob_site(prefix, site_slug, location_slug, rack, label_start, ports):
    labels = [f"{prefix}-cbl-{label_start + i:05d}" for i in range(len(ports) + 1)]
    return {
        "name": f"{prefix}-oob-01", "site_slug": site_slug, "location_slug": location_slug,
        "rack_name": rack, "position": 39, "router": f"{prefix}-rtr-01",
        "ports": [{"port": p, "device": d, "label": labels[i]} for i, (p, d) in enumerate(ports)],
        "uplink_label": labels[-1],
    }

OOB_SITES = [
    _oob_site("sto", "nordfiber-stockholm-dc", "stockholm-suite-100-row-a", "STO-RACK-A1", 15, [
        (1, "sto-rtr-01"), (2, "sto-sw-01"), (3, "sto-wdm-01"), (4, "sto-wdm-02"), (5, "sto-wdm-03"), (6, "sto-wdm-04"),
        (7, "sto-dcp2-01"), (8, "polaris-sto-sw-01"), (9, "polaris-sto-srv-01"), (10, "polaris-sto-srv-02")]),
    _oob_site("got", "nordfiber-gothenburg-pop", "gothenburg-telecom-room", "GOT-RACK-1", 21, [
        (1, "got-rtr-01"), (2, "got-sw-01"), (3, "got-wdm-01"), (4, "got-wdm-02"), (7, "got-dcp2-01"),
        (8, "got-idf-sw-01"), (9, "polaris-got-sw-01"), (10, "polaris-got-srv-01"),
        (11, "vasthamnen-got-sw-01"), (12, "vasthamnen-got-srv-01")]),
    _oob_site("mma", "nordfiber-malmo-pop", "malmo-telecom-room", "MMA-RACK-1", 3, [
        (1, "mma-rtr-01"), (2, "mma-sw-01"), (3, "mma-wdm-01"), (7, "mma-dcp2-01")]),
    _oob_site("osl", "nordfiber-oslo-pop", "oslo-telecom-room", "OSL-RACK-1", 2, [
        (1, "osl-rtr-01"), (2, "osl-sw-01"), (3, "osl-wdm-01"), (7, "osl-dcp2-01")]),
    _oob_site("hel", "nordfiber-helsinki-dc", "helsinki-telecom-room", "HEL-RACK-1", 8, [
        (1, "hel-rtr-01"), (2, "hel-sw-01"), (3, "hel-wdm-01"), (4, "hel-wdm-02")]),
]
OOB_UPLINK_OOB_IFACE = "Ethernet49"   # SFP+ on the OOB switch
OOB_UPLINK_ROUTER_IFACE = "xe-0/1/2"  # first spare 10GE on every core router

# ---------------------------------------------------------------------------
# Phase 21: asset identity — serials and asset tags (added post-hoc, 2026-10-02)
# ---------------------------------------------------------------------------
# The audit found all 57 devices with no serial and no asset tag. Formats:
#   serial:    <MFR>-<SITE>-<nnnn>   e.g. JNP-STO-0001  (every device; fictional,
#              sequential per manufacturer per site)
#   asset tag: NF-<SITE>-<nnnnn>     e.g. NF-STO-00001  (ONLY Nordfiber-owned
#              devices — a colo tenant's server or a vendor's demarc panel is
#              not Nordfiber's asset, so it carries a serial but no NF tag)
# Numbering continues from the highest existing value, so a device added
# later never renumbers an existing one; devices that already have a value
# are left alone. Linking installed gear to netbox-inventory assets was
# considered and left out (the plugin only models spares today).
SITE_CODES = {
    "nordfiber-stockholm-dc": "STO",
    "nordfiber-gothenburg-pop": "GOT",
    "nordfiber-malmo-pop": "MMA",
    "nordfiber-oslo-pop": "OSL",
    "nordfiber-helsinki-dc": "HEL",
}
MANUFACTURER_CODES = {"juniper": "JNP", "arista": "ARI", "dell": "DLL", "smartoptics": "SMO", "generic": "GEN"}
ASSET_TAG_OWNER_TENANT = "nordfiber-ab"
