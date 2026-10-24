"""
Layer 5 data: the optical layer — WDM line cabling, client demarc shelves
and the wavelength services that ride on them.

Channel 1 of a muxponder is front port "921" (ITU C21), channel 2 is "922".
"""

# WDM node -> (patch panel, front port) its Line side lands on. The pair number is the trunk position, so it is
# also the port at the far end: both muxponders of a link sit on the same-numbered port of their panels.
# Pair 1 of every long-haul and ring cable is the lit one.
LINE_PATCH = {
    "stn-wdm-01": ("stn-patch-osl-01", 1), "stn-wdm-02": ("stn-patch-got-01", 1),
    "stn-wdm-03": ("stn-patch-mmr-01", 2),                                          # NSN via the MeetMe trunk
    "stn-wdm-04": ("stn-patch-stw-01", 1), "stn-wdm-05": ("stn-patch-ste-01", 1),   # the ring, North - West and North - East
    "stw-wdm-01": ("stw-patch-got-01", 1),                                          # the southern route to Gothenburg
    "stw-wdm-02": ("stw-patch-stn-01", 1), "stw-wdm-03": ("stw-patch-ste-01", 1),
    "ste-wdm-01": ("ste-patch-mmr-01", 1),                                          # BFN via the MeetMe trunk
    "ste-wdm-02": ("ste-patch-stn-01", 1), "ste-wdm-03": ("ste-patch-stw-01", 1),
    "got-wdm-01": ("got-patch-stn-01", 1), "got-wdm-02": ("got-patch-mma-01", 1),
    "got-wdm-03": ("got-patch-stw-01", 1),
    "mma-wdm-01": ("mma-patch-got-01", 1),
    "osl-wdm-01": ("osl-patch-stn-01", 1),
    "hel-wdm-01": ("hel-patch-mmr-01", 1), "hel-wdm-02": ("hel-patch-mmr-01", 2),
}

# Muxponder channel -> DCP-2 shelf line port (the DCP-110 turns the 100G DWDM
# channel into grey 10G clients a tenant can be handed).
SHELF_LINE = [
    ("stn-wdm-01", "921", "stn-dcp2-01", "Line/1/1"),   # Fjord, to Oslo
    ("stn-wdm-02", "922", "stn-dcp2-01", "Line/2/1"),   # Baltic Retail protect, to Gothenburg (north)
    ("stw-wdm-01", "922", "stw-dcp2-01", "Line/1/1"),   # Baltic Retail secondary, to Gothenburg (south)
    ("got-wdm-03", "922", "got-dcp2-01", "Line/1/1"),   # the secondary ends in Gothenburg
    ("osl-wdm-01", "921", "osl-dcp2-01", "Line/1/1"),   # Fjord, to Stockholm
    ("mma-wdm-01", "922", "mma-dcp2-01", "Line/1/1"),   # Baltic Retail protect, to Gothenburg
]

# Grey client side of the shelf -> the equipment the service is delivered to.
# Gothenburg's and Helsinki's shelves are installed with their module but their client side is not cabled:
# nothing is delivered there yet.
SHELF_CLIENT = [
    ("stn-dcp2-01", "Client/1/1", ("interface", "stn-sw-01", "Ethernet49/1")),
    ("stn-dcp2-01", "Client/2/1", ("interface", "stn-rtr-02", "et-0/0/1")),
    ("stw-dcp2-01", "Client/1/1", ("interface", "stw-rtr-02", "et-0/0/1")),
    ("osl-dcp2-01", "Client/1/1", ("interface", "osl-sw-01", "Ethernet49/1")),
    ("mma-dcp2-01", "Client/1/1", ("interface", "mma-rtr-01", "et-0/0/1")),
]

# Nordfiber's own backbone links skip the shelf: no tenant to hand a grey optic to. NSN rides router 01 at both
# ends, BFN router 02 at both ends. On the ring, the North - West link rides router 01 at both ends, North - East
# router 02 at North and 01 at East, West - East router 02 at West and 01 at East.
DIRECT_HANDOFF = [
    ("stn-wdm-03", "921", "stn-rtr-01", "et-0/0/2"),
    ("hel-wdm-01", "921", "hel-rtr-01", "et-0/0/2"),
    ("ste-wdm-01", "921", "ste-rtr-02", "et-0/0/3"),
    ("hel-wdm-02", "921", "hel-rtr-02", "et-0/0/3"),
    ("stn-wdm-04", "921", "stn-rtr-01", "et-0/0/3"),
    ("stw-wdm-02", "921", "stw-rtr-01", "et-0/0/2"),
    ("stn-wdm-05", "921", "stn-rtr-02", "et-0/0/3"),
    ("ste-wdm-02", "921", "ste-rtr-01", "et-0/0/2"),
    ("stw-wdm-03", "921", "stw-rtr-02", "et-0/0/3"),
    ("ste-wdm-03", "921", "ste-rtr-01", "et-0/0/3"),
]

# A muxponder terminates a wavelength, it cannot pass one through (not a ROADM), so the
# Stockholm - Malmö protect path is regenerated in Gothenburg: two muxponders
# back to back, client to client.
REGEN_JUMPER = ("got-wdm-01", "922", "got-wdm-02", "922")

# Wavelength services. `nodes` are the two muxponders a path must run between;
# `channel` the grid position; the path is found by tracing from the first node.
WDM_CIRCUITS = [
    {"name": "Fjord Media Networks - Wavelength Service", "tenant": "fjord", "channel": 1,
     "nodes": ("stn-wdm-01", "osl-wdm-01"),
     "description": "ITU channel 21 (100 GHz grid), Stockholm North - Oslo, over Nordfiber's leased dark fiber (PLT-100234)."},
    {"name": "Baltic Retail Group Backup - Segment 1 (Stockholm North-Gothenburg)", "tenant": "baltic-retail", "channel": 2,
     "nodes": ("stn-wdm-02", "got-wdm-01"),
     "description": "First hop of NF-BRG-0002 over the northern route, ITU channel 22."},
    {"name": "Baltic Retail Group Backup - Segment 2 (Gothenburg-Malmö)", "tenant": "baltic-retail", "channel": 2,
     "nodes": ("got-wdm-02", "mma-wdm-01"),
     "description": "Second hop of NF-BRG-0002, ITU channel 22, regenerated in Gothenburg."},
    {"name": "Baltic Retail Group Secondary - Segment 1 (Stockholm West-Gothenburg)", "tenant": "baltic-retail", "channel": 2,
     "nodes": ("stw-wdm-01", "got-wdm-03"),
     "description": "Secondary wavelength for Baltic Retail Group over the southern route, ITU channel 22. "
                    "It ends in Gothenburg: the continuation to Malmö is not cabled."},
]
