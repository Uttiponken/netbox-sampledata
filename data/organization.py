"""
Layer 1 data: who and where — tenants, regions, sites, rooms, contacts.

Sites are described as PROFILES (kind="dc" or "pop") plus per-site facts;
layout.py turns a site's kind into its racks and devices, so two sites of
the same kind are alike by construction rather than by copy-paste.

Contact emails use the .example TLD (RFC 2606), never a real domain.
"""

from data import metro
from data.municipalities import NAMES as MUNICIPALITY_NAMES

TENANT_GROUPS = [
    {"name": "Internal", "slug": "internal"},
    {"name": "Customers", "slug": "customers"},
    {"name": "Facility Operators", "slug": "facility-operators"},
    {"name": "Suppliers", "slug": "suppliers"},
    {"name": "Municipalities", "slug": "municipalities"},
]

# `code` is the short party name used in device names (e.g. stn-mmr-<code>-01).
TENANTS = [
    {"code": "nordfiber", "name": "Nordfiber AB", "slug": "nordfiber-ab", "group": "internal",
     "description": "Regional fiber-optic network operator headquartered in Stockholm; owns the sites and core infrastructure in this dataset."},
    {"code": "baltic-retail", "name": "Baltic Retail Group", "slug": "baltic-retail-group", "group": "customers",
     "description": "Nordic retail chain. Leases WAN connectivity between its Stockholm and Malmö distribution centers; colocated server and switch in all three Stockholm datacenters and in Malmö."},
    {"code": "polaris", "name": "Polaris Cloud Services", "slug": "polaris-cloud-services", "group": "customers",
     "description": "Cloud hosting provider. Colocates compute racks at the Stockholm North and Gothenburg datacenters."},
    {"code": "vasthamnen", "name": "Västhamnen Logistics", "slug": "vasthamnen-logistics", "group": "customers",
     "description": "Port logistics and container-tracking operator. Colocates edge-compute servers at the Gothenburg datacenter for IoT telemetry from Port of Gothenburg operations."},
    {"code": "fjord", "name": "Fjord Media Networks", "slug": "fjord-media-networks", "group": "customers",
     "description": "Broadcast/media company. Leases a high-bandwidth wavelength service between Oslo and Stockholm."},
    {"code": "skagerrak", "name": "Skagerrak Interconnect AB", "slug": "skagerrak-interconnect-ab", "group": "facility-operators",
     "description": "Fictional carrier-neutral facility operator running the MeetMe rooms at Gothenburg and Oslo; Nordfiber and its colo customers rent space there."},
    {"code": "oresund", "name": "Öresund Exchange AB", "slug": "oresund-exchange-ab", "group": "facility-operators",
     "description": "Fictional carrier-neutral facility operator running the MeetMe room at Malmö, a different landlord than Skagerrak."},
    {"code": "vastkust", "name": "Västkust Bredband AB", "slug": "vastkust-bredband-ab", "group": "suppliers",
     "description": "Fictional regional Internet transit provider; supplies Nordfiber's upstream Internet access at Gothenburg."},
    {"code": "nsn", "name": "Nordic Subsea Networks AB", "slug": "nordic-subsea-networks-ab", "group": "suppliers",
     "description": "Fictional Nordic fiber transit vendor; leases Nordfiber the primary Stockholm-Helsinki dark fiber (via Norrtälje, Åland, Turku and Salo)."},
    {"code": "bfn", "name": "Baltic Fibre Networks OÜ", "slug": "baltic-fibre-networks-ou", "group": "suppliers",
     "description": "Fictional Baltic fiber transit vendor; leases Nordfiber the backup Stockholm-Helsinki dark fiber (via Gotland, Riga and Tallinn)."},
    {"code": "smf", "name": "Stockholm Metro Fibre AB", "slug": "stockholm-metro-fibre-ab", "group": "suppliers",
     "description": "Fictional Stockholm metro fiber operator; owns the Södertälje - Nacka cable between Nordfiber's West and East datacenters and leases it, whole, to Nordfiber."},
    {"code": "mkab", "name": "Mälar Kabelentreprenad AB", "slug": "malar-kabelentreprenad-ab", "group": "suppliers",
     "description": "Fictional civil-works contractor that installed the metro ducts and cables around Stockholm."},
    # The municipalities own the ducts in their territory: the ones the metro ring passes through (data/metro.py). In this
    # fictional scenario the ownership is invented for the dataset; it says nothing about the real conduit owners.
    *({"code": code, "name": MUNICIPALITY_NAMES[code][0], "slug": MUNICIPALITY_NAMES[code][1], "group": "municipalities",
       "description": "Municipality in Stockholm County. Owner of the ducts in its territory in this fictional scenario "
                      "(the ownership is invented for the dataset)."}
      for code in metro.municipalities()),
]

REGIONS = [
    {"name": "Nordics", "slug": "nordics", "parent": None},
    {"name": "Sweden", "slug": "sweden", "parent": "nordics"},
    {"name": "Greater Stockholm", "slug": "greater-stockholm", "parent": "sweden"},
    {"name": "Norway", "slug": "norway", "parent": "nordics"},
    {"name": "Finland", "slug": "finland", "parent": "nordics"},
]

SITE_GROUPS = [
    {"name": "Data Centers", "slug": "data-centers"},
    {"name": "Points of Presence", "slug": "points-of-presence"},
]

# kind:      "dc" -> redundant core pair (router/switch 01+02); "pop" -> single
#            pair with the second slots left free in the rack.
# mm_owner:  party that owns the MeetMe room's rack (Nordfiber where it owns
#            the building; a third-party facility operator at the others).
# colo:      customers that colocate here (get a rack in the Colo Hall).
# wdm_nodes: number of WDM terminal muxponders (named <code>-wdm-01..).
# mgmt:      third octet of the site's 10.0.N.0/24 out-of-band prefix.
SITES = [
    # Stockholm is three datacenters, one per availability zone, tied together by a metro ring (data/metro.py).
    # `city` is the slug stem, so the three read "Stockholm North/West/East" everywhere.
    {"code": "stn", "city": "stockholm-north", "name": "Nordfiber Stockholm North DC", "kind": "dc", "region": "greater-stockholm",
     "facility": "STN1", "address": "Kabelvägen 1, 191 47 Sollentuna, Sweden", "tz": "Europe/Stockholm",
     "lat": 59.4405, "lon": 17.9200,
     "description": "Stockholm availability zone North (Sollentuna): primary datacenter and network core (HQ). "
                    "Lands the northern routes to Gothenburg, Oslo and Helsinki.",
     "mm_owner": "nordfiber", "colo": ["polaris", "baltic-retail"], "wdm_nodes": 5, "growth_racks": 0, "mgmt": 1},
    {"code": "stw", "city": "stockholm-west", "name": "Nordfiber Stockholm West DC", "kind": "dc", "region": "greater-stockholm",
     "facility": "STW1", "address": "Optikgatan 3, 151 36 Södertälje, Sweden", "tz": "Europe/Stockholm",
     "lat": 59.1745, "lon": 17.6420,
     "description": "Stockholm availability zone West (Södertälje). Lands the Malmö trunk and the southern route to Gothenburg.",
     "mm_owner": "nordfiber", "colo": ["baltic-retail"], "wdm_nodes": 3, "growth_racks": 0, "mgmt": 6},
    {"code": "ste", "city": "stockholm-east", "name": "Nordfiber Stockholm East DC", "kind": "dc", "region": "greater-stockholm",
     "facility": "STE1", "address": "Glasfibervägen 7, 131 54 Nacka, Sweden", "tz": "Europe/Stockholm",
     "lat": 59.3125, "lon": 18.1660,
     "description": "Stockholm availability zone East (Nacka). Lands the backup route to Helsinki via Gotland, Riga and Tallinn.",
     "mm_owner": "nordfiber", "colo": ["baltic-retail"], "wdm_nodes": 3, "growth_racks": 0, "mgmt": 7},
    {"code": "got", "city": "gothenburg", "name": "Nordfiber Gothenburg DC", "kind": "dc", "region": "sweden",
     "facility": "GOT1", "address": "Lindholmspiren 5, 417 56 Göteborg, Sweden", "tz": "Europe/Stockholm",
     "lat": 57.7089, "lon": 11.9746, "description": "Second full datacenter, on the west coast.",
     "mm_owner": "skagerrak", "colo": ["polaris", "vasthamnen"], "wdm_nodes": 3, "growth_racks": 2, "mgmt": 2},
    {"code": "mma", "city": "malmo", "name": "Nordfiber Malmö PoP", "kind": "pop", "region": "sweden",
     "facility": "MMA1", "address": "Hyllie Boulevard 21, 215 32 Malmö, Sweden", "tz": "Europe/Stockholm",
     "lat": 55.5636, "lon": 12.9819, "description": "Southern point of presence, near the Öresund Bridge crossing to Denmark.",
     "mm_owner": "oresund", "colo": ["baltic-retail"], "wdm_nodes": 1, "growth_racks": 0, "mgmt": 3},
    {"code": "osl", "city": "oslo", "name": "Nordfiber Oslo PoP", "kind": "pop", "region": "norway",
     "facility": "OSL1", "address": "Nydalsveien 28, 0484 Oslo, Norway", "tz": "Europe/Oslo",
     "lat": 59.9139, "lon": 10.7522, "description": "Cross-border point of presence into Norway.",
     "mm_owner": "skagerrak", "colo": [], "wdm_nodes": 1, "growth_racks": 0, "mgmt": 4},
    {"code": "hel", "city": "helsinki", "name": "Nordfiber Helsinki DC", "kind": "dc", "region": "finland",
     "facility": "HEL1", "address": "Ratamestarinkatu 11, 00520 Helsinki, Finland", "tz": "Europe/Helsinki",
     "lat": 60.1699, "lon": 24.9384,
     "description": "Third datacenter, smaller footprint; reached from Stockholm over two independently routed leased dark fiber pairs.",
     "mm_owner": "nordfiber", "colo": [], "wdm_nodes": 2, "growth_racks": 0, "mgmt": 5},
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
    {"name": "Erik Lindqvist", "group": "network-operations", "title": "NOC Engineer",
     "email": "erik.lindqvist@nordfiber.example", "phone": "+46 70 123 45 67"},
    {"name": "Astrid Nilsen", "group": "network-operations", "title": "Field Technician, Oslo",
     "email": "astrid.nilsen@nordfiber.example", "phone": "+47 400 12 345"},
    {"name": "Mikko Virtanen", "group": "network-operations", "title": "Field Technician, Helsinki",
     "email": "mikko.virtanen@nordfiber.example", "phone": "+358 40 123 4567"},
    {"name": "Maria Svensson", "group": "customer-contacts", "title": "IT Infrastructure Manager, Baltic Retail Group",
     "email": "maria.svensson@balticretail.example", "phone": "+46 70 555 11 22"},
    {"name": "Johan Eriksson", "group": "customer-contacts", "title": "Head of Platform Engineering, Polaris Cloud Services",
     "email": "johan.eriksson@polariscloud.example", "phone": "+46 70 555 33 44"},
    {"name": "Lena Björk", "group": "customer-contacts", "title": "Systems Engineer, Västhamnen Logistics",
     "email": "lena.bjork@vasthamnen.example", "phone": "+46 70 555 66 77"},
    {"name": "Ingrid Haugen", "group": "customer-contacts", "title": "Broadcast Engineering Lead, Fjord Media Networks",
     "email": "ingrid.haugen@fjordmedia.example", "phone": "+47 400 99 887"},
    {"name": "Fredrik Dahl", "group": "customer-contacts", "title": "Facility Operations Manager, Skagerrak Interconnect AB",
     "email": "fredrik.dahl@skagerrakinterconnect.example", "phone": "+46 70 888 22 11"},
    {"name": "Kristina Holm", "group": "customer-contacts", "title": "Facility Operations Manager, Öresund Exchange AB",
     "email": "kristina.holm@oresundexchange.example", "phone": "+46 70 888 33 22"},
]

# object kinds: "site" (by site code), "tenant" (by party code), and — assigned
# in the hardware layer once they exist — "rack" and "device" (by name).
CONTACT_ASSIGNMENTS = [
    *({"contact": "Erik Lindqvist", "role": "noc-engineer", "kind": "site", "ref": c} for c in ("stn", "stw", "ste", "got", "mma", "osl", "hel")),
    {"contact": "Astrid Nilsen", "role": "site-technician", "kind": "site", "ref": "osl"},
    {"contact": "Mikko Virtanen", "role": "site-technician", "kind": "site", "ref": "hel"},
    {"contact": "Maria Svensson", "role": "technical-contact", "kind": "tenant", "ref": "baltic-retail"},
    {"contact": "Johan Eriksson", "role": "technical-contact", "kind": "tenant", "ref": "polaris"},
    {"contact": "Lena Björk", "role": "technical-contact", "kind": "tenant", "ref": "vasthamnen"},
    {"contact": "Ingrid Haugen", "role": "technical-contact", "kind": "tenant", "ref": "fjord"},
    # Facility operators: at every site they run, plus their own rack and panel.
    {"contact": "Fredrik Dahl", "role": "technical-contact", "kind": "site", "ref": "got"},
    {"contact": "Fredrik Dahl", "role": "technical-contact", "kind": "site", "ref": "osl"},
    {"contact": "Fredrik Dahl", "role": "technical-contact", "kind": "rack", "ref": "GOT-MM-01"},
    {"contact": "Fredrik Dahl", "role": "technical-contact", "kind": "rack", "ref": "OSL-MM-01"},
    {"contact": "Fredrik Dahl", "role": "technical-contact", "kind": "device", "ref": "got-mmr-skagerrak-01"},
    {"contact": "Fredrik Dahl", "role": "technical-contact", "kind": "device", "ref": "osl-mmr-skagerrak-01"},
    {"contact": "Kristina Holm", "role": "technical-contact", "kind": "site", "ref": "mma"},
    {"contact": "Kristina Holm", "role": "technical-contact", "kind": "rack", "ref": "MMA-MM-01"},
    {"contact": "Kristina Holm", "role": "technical-contact", "kind": "device", "ref": "mma-mmr-oresund-01"},
    # Erik's own workstation.
    {"contact": "Erik Lindqvist", "role": "noc-engineer", "kind": "device", "ref": "got-ws-erik"},
]
