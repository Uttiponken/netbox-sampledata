"""
Layer 4 data: everything between sites — providers, circuits, the backbone
fiber, the leased spans, their physical plant (FMS) and geography (pathways).

Route waypoints are (name, lon, lat). Each route is used three times: its
haversine length becomes the cable's length in km, its LineString is the
cable's DirectBuried pathway, and (for leased circuits) the circuit's own
geometry.
"""

PROVIDERS = [
    {"name": "Nordfiber AB", "slug": "nordfiber-ab",
     "description": "Nordfiber acting as a provider: the circuits it sells to its own customers."},
    {"name": "Polarlink Transit", "slug": "polarlink-transit",
     "description": "Fictional pan-Nordic wholesale dark fiber and transit provider. Leases the Stockholm-Oslo fiber pair to Nordfiber."},
    {"name": "Västkust Bredband AB", "slug": "vastkust-bredband-ab",
     "description": "Fictional regional Internet transit provider. Supplies Nordfiber's upstream Internet access in Gothenburg."},
    {"name": "Nordic Subsea Networks AB", "slug": "nordic-subsea-networks-ab",
     "description": "Fictional Nordic subsea/terrestrial fiber vendor. Leases Route 1 (Stockholm, Mariehamn, Vaasa, Helsinki) to Nordfiber."},
    {"name": "Baltic Fibre Networks OÜ", "slug": "baltic-fibre-networks-ou",
     "description": "Fictional Baltic fiber vendor. Leases Route 2 (Stockholm, Gotland, Riga, Tallinn, Helsinki) to Nordfiber."},
]

CIRCUIT_TYPES = [
    {"name": "Ethernet Private Line", "slug": "epl", "color": "2196f3"},
    {"name": "Dark Fiber", "slug": "dark-fiber", "color": "795548"},
    {"name": "Internet Access", "slug": "internet-access", "color": "00bcd4"},
]

# sites: {side: site code}.  rate in kbps.
# `cabled`: circuit terminations that are cabled — (side, far end endpoint) — as
# opposed to dark-fiber/backup circuits that stay commercial records only
# (the physical path is the cable chain, not the circuit).
CIRCUITS = [
    {"cid": "NF-BRG-0001", "provider": "nordfiber-ab", "type": "epl", "tenant": "baltic-retail",
     "rate": 10_000_000, "sites": {"A": "sto", "Z": "mma"},
     "description": "Baltic Retail Group leased line, Stockholm - Malmö (primary, direct fiber)."},
    {"cid": "NF-BRG-0002", "provider": "nordfiber-ab", "type": "epl", "tenant": "baltic-retail",
     "rate": 10_000_000, "sites": {"A": "sto", "Z": "mma"},
     "description": "Baltic Retail Group protect path for NF-BRG-0001, Stockholm - Malmö via Gothenburg over DWDM, regenerated in Gothenburg."},
    {"cid": "PLT-100234", "provider": "polarlink-transit", "type": "dark-fiber", "tenant": "nordfiber",
     "rate": None, "sites": {"A": "sto", "Z": "osl"},
     "description": "Leased dark fiber pair, Stockholm - Oslo, lit with Nordfiber's own WDM equipment.",
     "geometry": "bb3"},
    {"cid": "NSN-DF-0001", "provider": "nordic-subsea-networks-ab", "type": "dark-fiber", "tenant": "nordfiber",
     "rate": None, "sites": {"A": "sto", "Z": "hel"},
     "description": "Primary leased dark fiber pair, Stockholm - Helsinki via Mariehamn (Åland) and Vaasa. The shorter route.",
     "geometry": "nsn"},
    {"cid": "BFN-DF-0001", "provider": "baltic-fibre-networks-ou", "type": "dark-fiber", "tenant": "nordfiber",
     "rate": None, "sites": {"A": "sto", "Z": "hel"},
     "description": "Backup leased dark fiber pair, Stockholm - Helsinki via Gotland, Riga and Tallinn. Longer, geographically diverse route.",
     "geometry": "bfn"},
    {"cid": "VKB-INET-0001", "provider": "vastkust-bredband-ab", "type": "internet-access", "tenant": "nordfiber",
     "rate": 10_000_000, "sites": {"A": "got"},
     "description": "Nordfiber's own upstream Internet transit, Gothenburg."},
]

# Circuit terminations that are physically cabled: (cid, side, device, port kind, port)
CABLED_TERMINATIONS = [
    ("NF-BRG-0001", "A", ("interface", "sto-rtr-01", "et-0/0/0"), "primary demarc"),
    ("NF-BRG-0001", "Z", ("interface", "mma-rtr-01", "et-0/0/0"), "primary demarc"),
    ("VKB-INET-0001", "A", ("rearport", "got-mmr-vastkust-01", "Trunk"), "Internet handoff at the provider's MeetMe panel"),
]

ROUTES = {
    "bb1": [("Stockholm", 18.0686, 59.3293), ("Västerås", 16.5528, 59.6099), ("Örebro", 15.2066, 59.2741),
            ("Karlstad", 13.5116, 59.3793), ("Trollhättan", 12.2886, 58.2837), ("Gothenburg", 11.9746, 57.7089)],
    "bb2": [("Stockholm", 18.0686, 59.3293), ("Linköping", 15.6214, 58.4108), ("Jönköping", 14.1618, 57.7826),
            ("Markaryd", 13.5975, 56.4402), ("Hässleholm", 13.7660, 56.1590), ("Lund", 13.1910, 55.7047),
            ("Malmö", 12.9819, 55.5636)],
    "bb3": [("Stockholm", 18.0686, 59.3293), ("Västerås", 16.5528, 59.6099), ("Örebro", 15.2066, 59.2741),
            ("Karlstad", 13.5116, 59.3793), ("Charlottenberg", 12.2942, 59.8900), ("Oslo", 10.7522, 59.9139)],
    "bb4": [("Gothenburg", 11.9746, 57.7089), ("Varberg", 12.2508, 57.1057), ("Halmstad", 12.8578, 56.6745),
            ("Ängelholm", 12.8623, 56.2428), ("Helsingborg", 12.6945, 56.0465), ("Landskrona", 12.8302, 55.8708),
            ("Malmö", 12.9819, 55.5636)],
    "nsn": [("Stockholm", 18.0686, 59.3293), ("Mariehamn (Åland)", 19.9348, 60.0971), ("Vaasa", 21.6165, 63.0951),
            ("Helsinki", 24.9384, 60.1699)],
    "bfn": [("Stockholm", 18.0686, 59.3293), ("Visby (Gotland)", 18.2948, 57.6348), ("Riga", 24.1052, 56.9496),
            ("Tallinn", 24.7536, 59.4370), ("Helsinki", 24.9384, 60.1699)],
}

# Long-haul cables, created in this order: the label bb-cbl-0000N follows it.
#   (route key, end A, end B, note, FMS note)
# End = (device, rear port). Cable tenant: Nordfiber for its own and the leased
# Polarlink fiber, the vendor for a vendor span (the cabler infers it from the panels).
LONG_HAUL = [
    ("bb1", ("sto-patch-got-01", "Trunk"), ("got-patch-sto-01", "Trunk"),
     "Nordfiber-owned 24-pair trunk, Stockholm - Gothenburg via Västerås, Örebro, Karlstad, Trollhättan",
     "Owned by Nordfiber AB. In-country backbone, 24 pairs (48 fibers)."),
    ("bb2", ("sto-patch-mma-01", "Trunk"), ("mma-patch-sto-01", "Trunk"),
     "Nordfiber-owned 24-pair trunk, Stockholm - Malmö via the E4",
     "Owned by Nordfiber AB. Physical path of Baltic Retail Group's NF-BRG-0001. 24 pairs (48 fibers)."),
    ("bb3", ("sto-patch-osl-01", "Trunk"), ("osl-patch-sto-01", "Trunk"),
     "Leased 24-pair trunk (Polarlink Transit, PLT-100234), Stockholm - Oslo via Västerås, Örebro, Karlstad, Charlottenberg",
     "Leased from Polarlink Transit under PLT-100234. 24 pairs (48 fibers). Lit with Nordfiber's own WDM equipment."),
    ("bb4", ("got-patch-mma-01", "Trunk"), ("mma-patch-got-01", "Trunk"),
     "Nordfiber-owned 24-pair trunk, Gothenburg - Malmö along the west coast via Varberg, Halmstad, Helsingborg",
     "Owned by Nordfiber AB. 24 pairs (48 fibers). Second leg of the NF-BRG-0002 protect path, regenerated in Gothenburg."),
    ("nsn", ("sto-mmr-nsn-01", "Trunk"), ("hel-mmr-nsn-01", "Trunk"),
     "NSN-DF-0001: leased 24-pair trunk between the vendor's MeetMe panels, Stockholm - Helsinki via Mariehamn and Vaasa",
     "Leased from Nordic Subsea Networks AB under NSN-DF-0001. 24 pairs (48 fibers)."),
    ("bfn", ("sto-mmr-bfn-01", "Trunk"), ("hel-mmr-bfn-01", "Trunk"),
     "BFN-DF-0001: leased 24-pair trunk between the vendor's MeetMe panels, Stockholm - Helsinki via Gotland, Riga and Tallinn",
     "Leased from Baltic Fibre Networks OÜ under BFN-DF-0001. 24 pairs (48 fibers)."),
]

FMS_CABLE_TYPE = {
    "manufacturer": "corning", "model": "ALTOS Loose Tube 48F SM", "construction": "loose_tube", "strand_count": 48,
    "color_scheme": "din_iec_60304", "sheath_material": "hdpe", "deployment": "duct", "is_armored": True,
    "armor_type": "steel_tape", "mark_unit": "m",
}

# What the fiber-plant record of each long-haul cable says about its manufacture and installation. Route marks
# run from 0 to the route length in metres. The Polarlink pair has no installer here: Polarlink is a provider,
# not a tenant.
FIBER_DETAILS = {
    "bb1": {"serial_number": "CNG-ALTOS24-0001", "install_date": "2022-05-16", "installer": "nordfiber"},
    "bb2": {"serial_number": "CNG-ALTOS24-0002", "install_date": "2022-06-20", "installer": "nordfiber"},
    "bb3": {"serial_number": "CNG-ALTOS24-0003", "install_date": "2021-09-01", "installer": None},
    "bb4": {"serial_number": "CNG-ALTOS24-0004", "install_date": "2024-04-08", "installer": "nordfiber"},
    "nsn": {"serial_number": "CNG-ALTOS24-0005", "install_date": "2023-11-27", "installer": "nsn"},
    "bfn": {"serial_number": "CNG-ALTOS24-0006", "install_date": "2024-02-14", "installer": "bfn"},
}
FMS_BUFFER_TUBES = [{"name": f"Tube {n}", "position": n, "fiber_count": 12} for n in range(1, 5)]   # 4 x 12 = 48
