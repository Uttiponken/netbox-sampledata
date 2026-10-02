"""
Layer 5 data: the optical layer — WDM line cabling, client demarc shelves
and the wavelength services that ride on them.

Channel 1 of a muxponder is front port "921" (ITU C21), channel 2 is "922".
"""

# WDM node -> patch panel port its Line side lands on (same port number as the
# trunk that carries it: the panel passes front port N through to rear port N).
LINE_PATCH_PORT = {
    "sto-wdm-01": 3, "sto-wdm-02": 1, "sto-wdm-03": 5, "sto-wdm-04": 6,
    "got-wdm-01": 1, "got-wdm-02": 2,
    "mma-wdm-01": 2,
    "osl-wdm-01": 1,
    "hel-wdm-01": 1, "hel-wdm-02": 2,
}

# Muxponder channel -> DCP-2 shelf line port (the DCP-110 turns the 100G DWDM
# channel into grey 10G clients a tenant can be handed).
SHELF_LINE = [
    ("sto-wdm-01", "921", "sto-dcp2-01", "Line/1/1"),   # Fjord, to Oslo
    ("sto-wdm-02", "922", "sto-dcp2-01", "Line/2/1"),   # Baltic Retail protect, to Gothenburg
    ("osl-wdm-01", "921", "osl-dcp2-01", "Line/1/1"),   # Fjord, to Stockholm
    ("mma-wdm-01", "922", "mma-dcp2-01", "Line/1/1"),   # Baltic Retail protect, to Gothenburg
]

# Grey client side of the shelf -> the equipment the service is delivered to.
# Gothenburg's and Helsinki's shelves are installed with their module but not
# cabled: nothing is delivered there yet.
SHELF_CLIENT = [
    ("sto-dcp2-01", "Client/1/1", ("interface", "sto-sw-01", "Ethernet49/1")),
    ("sto-dcp2-01", "Client/2/1", ("interface", "sto-rtr-02", "et-0/0/1")),
    ("osl-dcp2-01", "Client/1/1", ("interface", "osl-sw-01", "Ethernet49/1")),
    ("mma-dcp2-01", "Client/1/1", ("interface", "mma-rtr-01", "et-0/0/1")),
]

# Nordfiber's own backbone links to Helsinki skip the shelf: no tenant to hand a
# grey optic to. NSN rides router 01 at both ends, BFN router 02 at both ends.
DIRECT_HANDOFF = [
    ("sto-wdm-03", "921", "sto-rtr-01", "et-0/0/2"),
    ("hel-wdm-01", "921", "hel-rtr-01", "et-0/0/2"),
    ("sto-wdm-04", "921", "sto-rtr-02", "et-0/0/3"),
    ("hel-wdm-02", "921", "hel-rtr-02", "et-0/0/3"),
]

# A muxponder terminates a wavelength, it cannot pass one through (not a ROADM), so the
# Stockholm - Malmö protect path is regenerated in Gothenburg: two muxponders
# back to back, client to client.
REGEN_JUMPER = ("got-wdm-01", "922", "got-wdm-02", "922")

# Wavelength services. `nodes` are the two muxponders a path must run between;
# `channel` the grid position; the path is found by tracing from the first node.
WDM_CIRCUITS = [
    {"name": "Fjord Media Networks - Wavelength Service", "tenant": "fjord", "channel": 1,
     "nodes": ("sto-wdm-01", "osl-wdm-01"),
     "description": "ITU channel 21 (100 GHz grid), Stockholm - Oslo, over Nordfiber's leased dark fiber (PLT-100234)."},
    {"name": "Baltic Retail Group Backup - Segment 1 (Stockholm-Gothenburg)", "tenant": "baltic-retail", "channel": 2,
     "nodes": ("sto-wdm-02", "got-wdm-01"),
     "description": "First hop of NF-BRG-0002, ITU channel 22."},
    {"name": "Baltic Retail Group Backup - Segment 2 (Gothenburg-Malmö)", "tenant": "baltic-retail", "channel": 2,
     "nodes": ("got-wdm-02", "mma-wdm-01"),
     "description": "Second hop of NF-BRG-0002, ITU channel 22, regenerated in Gothenburg."},
]
