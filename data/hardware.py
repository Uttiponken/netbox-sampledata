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
    "Smartoptics/DCP-M40-PAM4-ER",
    "Smartoptics/DCP-2",
]
MODULE_TYPE_SOURCES = ["Smartoptics/DCP-110"]

# A fiber patch panel is always the end of a 24-pair trunk: 24 duplex LC ports on the front, all fed by ONE
# rear port with 24 positions (position n carries front port n). A trunk is one cable between two such rear
# ports, 24 pairs = 48 fibers. There is no such type in the community library, so it is defined here.
TRUNK_PANEL = {
    "manufacturer": "Generic", "model": "LC-24 trunk patch panel (24-pair)", "slug": "generic-lc-24-trunk-patch-panel",
    "part_number": "", "u_height": 1, "is_full_depth": False,
    "rear-ports": [{"name": "Trunk", "type": "splice", "positions": 24}],
    "front-ports": [{"name": f"Port {n}", "type": "lc"} for n in range(1, 25)],
    "port-mappings": [{"front_port": f"Port {n}", "front_port_position": 1, "rear_port": "Trunk",
                       "rear_port_position": n} for n in range(1, 25)],
}

# The metro ring between Nordfiber's Stockholm datacenters is 288-fiber ALTOS cable: 144 pairs. Its panels are the
# same idea, 144 duplex LC ports on the front and ONE rear port "Trunk" with 144 positions (position n carries front
# port n), 3U high.
TRUNK_PANEL_144 = {
    "manufacturer": "Generic", "model": "LC-144 trunk patch panel (144-pair)", "slug": "generic-lc-144-trunk-patch-panel",
    "part_number": "", "u_height": 3, "is_full_depth": False,
    "rear-ports": [{"name": "Trunk", "type": "splice", "positions": 144}],
    "front-ports": [{"name": f"Port {n}", "type": "lc"} for n in range(1, 145)],
    "port-mappings": [{"front_port": f"Port {n}", "front_port_position": 1, "rear_port": "Trunk",
                       "rear_port_position": n} for n in range(1, 145)],
}
CUSTOM_DEVICE_TYPES = [TRUNK_PANEL, TRUNK_PANEL_144]

# Short names used in the layout/cabling data.
T_ROUTER = "juniper-mx204"
T_AGG_SWITCH = "arista-dcs-7050sx3-48yc8-f"
T_COPPER_SWITCH = "arista-dcs-7010t-48"   # 48x1G copper + 4x10G SFP+: OOB, IDF and tenant switches
T_SERVER = "dell-poweredge-r650"
T_WORKSTATION = "dell-optiplex-sff-7050"
T_PANEL = "generic-lc-24-trunk-patch-panel"
T_PANEL_144 = "generic-lc-144-trunk-patch-panel"
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
#   core rack:   trunk patch panels | gap | OOB switch | gap | routers, switches | gap | WDM nodes | gap | DCP-2
#                A panel per trunk: "mmr" is the trunk to the MeetMe room, the others are the trunks to that
#                site. A panel sits at the same height at every site; the slot of the site itself stays free.
#                The three 144-pair ring panels are 3U (the slot is the lowest unit, as in NetBox).
#   colo rack:   ToR panel | gap | tenant switch | gap | servers
#   MeetMe rack: Nordfiber panel, facility owner's panel | gap | external parties
CORE_SLOTS = {"patch": {"mmr": 42, "got": 41, "mma": 40, "osl": 39, "stn": 36, "stw": 33, "ste": 30},
              "oob": 27, "rtr": (24, 23), "sw": (22, 21), "wdm_first": 18, "dcp2": 12}

# The backbone: one 24-pair trunk per pair of sites. Stockholm has two trunks to Gothenburg, one from North and
# one from West; Oslo and Malmö land on one zone each.
BACKBONE_PAIRS = [("stn", "got"), ("stw", "got"), ("stw", "mma"), ("stn", "osl"), ("got", "mma")]
# The Stockholm metro ring: one 144-pair trunk per pair of zones.
RING_PAIRS = [("stn", "stw"), ("stn", "ste"), ("stw", "ste")]


def backbone_peers(code):
    """The sites a site has a trunk to (backbone or ring), in the fixed order got, mma, osl, stn, stw, ste."""
    order = ["got", "mma", "osl", "stn", "stw", "ste"]
    peers = {b if a == code else a for a, b in BACKBONE_PAIRS + RING_PAIRS if code in (a, b)}
    return [c for c in order if c in peers]


def panel_type(code, peer):
    """The panel type at `code` for the trunk to `peer`: 144-pair on the ring, 24-pair everywhere else."""
    return T_PANEL_144 if (code, peer) in RING_PAIRS or (peer, code) in RING_PAIRS else T_PANEL
COLO_SLOTS = {"tor": 42, "sw": 39, "srv_first": 36}
MEETME_SLOTS = {"nordfiber": 42, "owner": 41, "party_first": 38}
IDF_SLOTS = {"sw": 42}

# Colo customers' servers per (site, customer).
COLO_SERVERS = {("stn", "polaris"): 2, ("stn", "baltic-retail"): 1, ("stw", "baltic-retail"): 1,
                ("ste", "baltic-retail"): 1, ("got", "polaris"): 1, ("got", "vasthamnen"): 1,
                ("mma", "baltic-retail"): 1}

# External parties with a demarc panel in each site's MeetMe room, in rack order.
MEETME_PARTIES = {
    "stn": ["polaris", "nsn", "baltic-retail"],
    "stw": ["baltic-retail"],
    "ste": ["bfn", "baltic-retail"],
    "got": ["polaris", "vasthamnen", "vastkust"],
    "mma": ["baltic-retail"],
    "osl": [],
    "hel": ["nsn", "bfn"],
}

# DCP-110 modules installed in each site's DCP-2 shelf (Stockholm North serves two wavelengths).
DCP2_MODULE_BAYS = {"stn": ["slot-1/1", "slot-1/2"], "stw": ["slot-1/1"], "ste": ["slot-1/1"], "got": ["slot-1/1"],
                    "mma": ["slot-1/1"], "osl": ["slot-1/1"], "hel": ["slot-1/1"]}

# Management addressing: last octet by role within each site's 10.0.N.0/24.
MGMT_HOST = {"rtr-01": 11, "sw-01": 12, "idf": 13, "ws": 14, "rtr-02": 15, "sw-02": 16, "srv": 21}

WORKSTATION_NAME = "got-ws-erik"
IDF_SWITCH_NAME = "got-idf-sw-01"
