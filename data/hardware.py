"""
Layer 2 data: the hardware catalogue and the rules for placing it.

Real device types are fetched live from the community Device Type Library
(never hand-typed) so interface lists are authoritative. Power and console
ports are not imported — power is out of scope for this dataset.
"""

MANUFACTURERS = [
    {"name": "Juniper", "slug": "juniper"},
    {"name": "Arista", "slug": "arista"},
    {"name": "Dell", "slug": "dell"},
    {"name": "Generic", "slug": "generic"},
    {"name": "Smartoptics", "slug": "smartoptics"},
    {"name": "Corning", "slug": "corning"},
]

DEVICE_TYPE_SOURCES = [
    "Juniper/MX204",
    "Arista/DCS-7050SX3-48YC8-F",
    "Arista/DCS-7010T-48",
    "Dell/PowerEdge-R650",
    "Dell/OptiPlex-SFF-7050",
    "Generic/LC-24-port-fiber-patch-panel",
    "Smartoptics/DCP-M40-PAM4-ER",
    "Smartoptics/DCP-2",
]
MODULE_TYPE_SOURCES = ["Smartoptics/DCP-110"]

# Short names used in the layout/cabling data.
T_ROUTER = "juniper-mx204"
T_AGG_SWITCH = "arista-dcs-7050sx3-48yc8-f"
T_COPPER_SWITCH = "arista-dcs-7010t-48"   # 48x1G copper + 4x10G SFP+: OOB, IDF and tenant switches
T_SERVER = "dell-poweredge-r650"
T_WORKSTATION = "dell-optiplex-sff-7050"
T_PANEL = "generic-lc-24-port-fiber-patch-panel"
T_WDM = "smartoptics-dcp-m40-pam4-er"
T_DCP2 = "smartoptics-dcp-2"

DEVICE_ROLES = [
    {"name": "Core Router", "slug": "core-router", "color": "2196f3"},
    {"name": "Aggregation Switch", "slug": "aggregation-switch", "color": "4caf50"},
    {"name": "Access Switch", "slug": "access-switch", "color": "8bc34a"},
    {"name": "OOB Switch", "slug": "oob-switch", "color": "ffc107"},
    {"name": "Server", "slug": "server", "color": "9e9e9e"},
    {"name": "Workstation", "slug": "workstation", "color": "795548"},
    {"name": "Patch Panel", "slug": "patch-panel", "color": "607d8b"},
    {"name": "WDM Terminal", "slug": "wdm-terminal", "color": "9c27b0"},
    {"name": "WDM Client Shelf", "slug": "wdm-client-shelf", "color": "3f51b5"},
]

RACK_ROLES = [
    {"name": "Core", "slug": "core", "color": "2196f3"},
    {"name": "MeetMe", "slug": "meetme", "color": "ff9800"},
    {"name": "Colo", "slug": "colo", "color": "4caf50"},
    {"name": "IDF", "slug": "idf", "color": "9e9e9e"},
]

# The management interface that carries the OOB cable (and the mgmt IP), per type.
MGMT_IFACE = {
    T_ROUTER: "fxp0",
    T_AGG_SWITCH: "Management1",
    T_COPPER_SWITCH: "Management1",
    T_WDM: "Eth0 / Local",
    T_DCP2: "if-1/eth1",     # not the craft port, "eth0 / local"
    T_SERVER: "iDRAC9",
}

# Rack slots (NetBox position 42 = top), identical at every site, with a 2U gap
# between different kinds of equipment so more can be added later.
#   core rack:   patch panel | gap | OOB switch | gap | routers, switches | gap | WDM nodes | gap | DCP-2
#   colo rack:   ToR panel | gap | tenant switch | gap | servers
#   MeetMe rack: Nordfiber panel, facility owner's panel | gap | external parties
CORE_SLOTS = {"patch": 42, "oob": 39, "rtr": (36, 35), "sw": (34, 33), "wdm_first": 30, "dcp2": 24}
COLO_SLOTS = {"tor": 42, "sw": 39, "srv_first": 36}
MEETME_SLOTS = {"nordfiber": 42, "owner": 41, "party_first": 38}
IDF_SLOTS = {"sw": 42}

# Colo customers' servers per (site, customer).
COLO_SERVERS = {("sto", "polaris"): 2, ("got", "polaris"): 1, ("got", "vasthamnen"): 1}

# External parties with a demarc panel in each site's MeetMe room, in rack order.
MEETME_PARTIES = {
    "sto": ["polaris", "nsn", "bfn"],
    "got": ["polaris", "vasthamnen", "vastkust"],
    "mma": [],
    "osl": [],
    "hel": ["nsn", "bfn"],
}

# DCP-110 modules installed in each site's DCP-2 shelf (Stockholm serves two wavelengths).
DCP2_MODULE_BAYS = {"sto": ["slot-1/1", "slot-1/2"], "got": ["slot-1/1"], "mma": ["slot-1/1"],
                    "osl": ["slot-1/1"], "hel": ["slot-1/1"]}

# Management addressing: last octet by role within each site's 10.0.N.0/24.
MGMT_HOST = {"rtr-01": 11, "sw-01": 12, "idf": 13, "ws": 14, "rtr-02": 15, "sw-02": 16, "srv": 21}

WORKSTATION_NAME = "got-ws-erik"
IDF_SWITCH_NAME = "got-idf-sw-01"
