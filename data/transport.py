"""
Layer 4 data: everything between sites — providers, circuits, the backbone
fiber, the leased spans, their physical plant (FMS) and geography (pathways).

Route waypoints are (name, lon, lat). Each long-haul route is used three times: its
haversine length becomes the cable's length in km, its LineString is the
cable's DirectBuried pathway, and (for leased circuits) the circuit's own
geometry. The Stockholm metro ring is different: its cables run through real
ducts, structure by structure (data/metro.py), and only its lengths and the leased
circuit's geometry come from here.
"""

from data import metro as M
from data import optical as O

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
    {"name": "Stockholm Metro Fibre AB", "slug": "stockholm-metro-fibre-ab",
     "description": "Fictional Stockholm metro fiber operator. Owns the Södertälje - Nacka cable and leases it, whole, to Nordfiber."},
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
     "rate": 10_000_000, "sites": {"A": "stw", "Z": "mma"},
     "description": "Baltic Retail Group leased line, Stockholm West - Malmö (primary, direct fiber)."},
    {"cid": "NF-BRG-0002", "provider": "nordfiber-ab", "type": "epl", "tenant": "baltic-retail",
     "rate": 10_000_000, "sites": {"A": "stn", "Z": "mma"},
     "description": "Baltic Retail Group protect path for NF-BRG-0001, Stockholm North - Malmö via Gothenburg over DWDM, regenerated in Gothenburg."},
    {"cid": "PLT-100234", "provider": "polarlink-transit", "type": "dark-fiber", "tenant": "nordfiber",
     "rate": None, "sites": {"A": "stn", "Z": "osl"},
     "description": "Leased dark fiber pair, Stockholm North - Oslo, lit with Nordfiber's own WDM equipment.",
     "geometry": "bb3"},
    {"cid": "NSN-DF-0001", "provider": "nordic-subsea-networks-ab", "type": "dark-fiber", "tenant": "nordfiber",
     "rate": None, "sites": {"A": "stn", "Z": "hel"},
     "description": "Primary leased dark fiber pair, Stockholm North - Helsinki via Mariehamn (Åland) and Vaasa. The shorter route.",
     "geometry": "nsn"},
    {"cid": "BFN-DF-0001", "provider": "baltic-fibre-networks-ou", "type": "dark-fiber", "tenant": "nordfiber",
     "rate": None, "sites": {"A": "ste", "Z": "hel"},
     "description": "Backup leased dark fiber pair, Stockholm East - Helsinki via Gotland, Riga and Tallinn. Longer, geographically diverse route.",
     "geometry": "bfn"},
    {"cid": "SMF-DF-0001", "provider": "stockholm-metro-fibre-ab", "type": "dark-fiber", "tenant": "nordfiber",
     "rate": None, "sites": {"A": "stw", "Z": "ste"},
     "description": "Leased dark fiber cable (144 pairs, the whole cable), Stockholm West (Södertälje) - Stockholm East (Nacka) "
                    "along the E4 and road 222. The third side of the metro ring.",
     "geometry": "we"},
    {"cid": "VKB-INET-0001", "provider": "vastkust-bredband-ab", "type": "internet-access", "tenant": "nordfiber",
     "rate": 10_000_000, "sites": {"A": "got"},
     "description": "Nordfiber's own upstream Internet transit, Gothenburg."},
]

# Circuit terminations that are physically cabled: (cid, side, device, port kind, port)
CABLED_TERMINATIONS = [
    ("NF-BRG-0001", "A", ("interface", "stw-rtr-01", "et-0/0/0"), "primary demarc"),
    ("NF-BRG-0001", "Z", ("interface", "mma-rtr-01", "et-0/0/0"), "primary demarc"),
    ("VKB-INET-0001", "A", ("rearport", "got-mmr-vastkust-01", "Trunk"), "Internet handoff at the provider's MeetMe panel"),
]

# Zone coordinates (lon, lat), the same as the sites in data/organization.py.
_STN = ("Stockholm North (Sollentuna)", 17.9200, 59.4405)
_STW = ("Stockholm West (Södertälje)", 17.6420, 59.1745)
_STE = ("Stockholm East (Nacka)", 18.1660, 59.3125)

ROUTES = {
    "bb1": [_STN, ("Västerås", 16.5528, 59.6099), ("Örebro", 15.2066, 59.2741),
            ("Karlstad", 13.5116, 59.3793), ("Trollhättan", 12.2886, 58.2837), ("Gothenburg", 11.9746, 57.7089)],
    "bb2": [_STW, ("Linköping", 15.6214, 58.4108), ("Jönköping", 14.1618, 57.7826),
            ("Markaryd", 13.5975, 56.4402), ("Hässleholm", 13.7660, 56.1590), ("Lund", 13.1910, 55.7047),
            ("Malmö", 12.9819, 55.5636)],
    "bb3": [_STN, ("Västerås", 16.5528, 59.6099), ("Örebro", 15.2066, 59.2741),
            ("Karlstad", 13.5116, 59.3793), ("Charlottenberg", 12.2942, 59.8900), ("Oslo", 10.7522, 59.9139)],
    "bb4": [("Gothenburg", 11.9746, 57.7089), ("Varberg", 12.2508, 57.1057), ("Halmstad", 12.8578, 56.6745),
            ("Ängelholm", 12.8623, 56.2428), ("Helsingborg", 12.6945, 56.0465), ("Landskrona", 12.8302, 55.8708),
            ("Malmö", 12.9819, 55.5636)],
    "bb5": [_STW, ("Nyköping", 17.0090, 58.7530), ("Norrköping", 16.1924, 58.5877), ("Linköping", 15.6214, 58.4108),
            ("Jönköping", 14.1618, 57.7826), ("Borås", 12.9401, 57.7210), ("Gothenburg", 11.9746, 57.7089)],
    "nsn": [_STN, ("Mariehamn (Åland)", 19.9348, 60.0971), ("Vaasa", 21.6165, 63.0951),
            ("Helsinki", 24.9384, 60.1699)],
    "bfn": [_STE, ("Visby (Gotland)", 18.2948, 57.6348), ("Riga", 24.1052, 56.9496),
            ("Tallinn", 24.7536, 59.4370), ("Helsinki", 24.9384, 60.1699)],
}
ROUTES.update(M.ROUTES)      # the metro links' routes (nw, ne, we), for the leased circuit's geometry

# Long-haul cables, created in this order: the label bb-cbl-0000N follows it (the metro ring continues the numbering).
#   (route key, end A, end B, note, FMS note)
# End = (device, rear port). Cable tenant: Nordfiber for its own and the leased
# Polarlink fiber, the vendor for a vendor span (the cabler infers it from the panels).
LONG_HAUL = [
    ("bb1", ("stn-patch-got-01", "Trunk"), ("got-patch-stn-01", "Trunk"),
     "Nordfiber-owned 24-pair trunk, Stockholm North - Gothenburg via Västerås, Örebro, Karlstad, Trollhättan",
     "Owned by Nordfiber AB. In-country backbone, the northern route to Gothenburg, 24 pairs (48 fibers)."),
    ("bb2", ("stw-patch-mma-01", "Trunk"), ("mma-patch-stw-01", "Trunk"),
     "Nordfiber-owned 24-pair trunk, Stockholm West - Malmö via the E4",
     "Owned by Nordfiber AB. Physical path of Baltic Retail Group's NF-BRG-0001. 24 pairs (48 fibers)."),
    ("bb3", ("stn-patch-osl-01", "Trunk"), ("osl-patch-stn-01", "Trunk"),
     "Leased 24-pair trunk (Polarlink Transit, PLT-100234), Stockholm North - Oslo via Västerås, Örebro, Karlstad, Charlottenberg",
     "Leased from Polarlink Transit under PLT-100234. 24 pairs (48 fibers). Lit with Nordfiber's own WDM equipment."),
    ("bb4", ("got-patch-mma-01", "Trunk"), ("mma-patch-got-01", "Trunk"),
     "Nordfiber-owned 24-pair trunk, Gothenburg - Malmö along the west coast via Varberg, Halmstad, Helsingborg",
     "Owned by Nordfiber AB. 24 pairs (48 fibers). Second leg of the NF-BRG-0002 protect path, regenerated in Gothenburg."),
    ("nsn", ("stn-mmr-nsn-01", "Trunk"), ("hel-mmr-nsn-01", "Trunk"),
     "NSN-DF-0001: leased 24-pair trunk between the vendor's MeetMe panels, Stockholm North - Helsinki via Mariehamn and Vaasa",
     "Leased from Nordic Subsea Networks AB under NSN-DF-0001. 24 pairs (48 fibers)."),
    ("bfn", ("ste-mmr-bfn-01", "Trunk"), ("hel-mmr-bfn-01", "Trunk"),
     "BFN-DF-0001: leased 24-pair trunk between the vendor's MeetMe panels, Stockholm East - Helsinki via Gotland, Riga and Tallinn",
     "Leased from Baltic Fibre Networks OÜ under BFN-DF-0001. 24 pairs (48 fibers)."),
    ("bb5", ("stw-patch-got-01", "Trunk"), ("got-patch-stw-01", "Trunk"),
     "Nordfiber-owned 24-pair trunk, Stockholm West - Gothenburg, the southern route via Nyköping, Norrköping, Linköping, Jönköping, Borås",
     "Owned by Nordfiber AB. The southern route to Gothenburg, same technology as the northern one: 24 pairs (48 fibers), "
     "pair 1 lit with DWDM."),
]
# The long-haul cables Nordfiber owns itself (the leased Polarlink pair is also booked as Nordfiber's cable).
NORDFIBER_CABLES = ("bb1", "bb2", "bb3", "bb4", "bb5")

FMS_CABLE_TYPE = {
    "manufacturer": "corning", "model": "ALTOS Loose Tube 48F SM", "construction": "loose_tube", "strand_count": 48,
    "color_scheme": "din_iec_60304", "sheath_material": "hdpe", "deployment": "duct", "is_armored": True,
    "armor_type": "steel_tape", "mark_unit": "m",
}
# The metro ring uses the largest ALTOS loose-tube count: 24 tubes of 12 fibers (Corning's 288-fiber gel-free,
# all-dielectric duct cable, about 18 mm across).
FMS_CABLE_TYPE_288 = {
    "manufacturer": "corning", "model": "ALTOS Loose Tube 288F SM", "construction": "loose_tube", "strand_count": 288,
    "color_scheme": "din_iec_60304", "sheath_material": "hdpe", "deployment": "duct", "is_armored": False,
    "mark_unit": "m",
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
    "bb5": {"serial_number": "CNG-ALTOS24-0007", "install_date": "2025-08-26", "installer": "nordfiber"},
    "nw": {"serial_number": "CNG-ALTOS288-0001", "install_date": "2025-03-18", "installer": "mkab"},
    "ne": {"serial_number": "CNG-ALTOS288-0002", "install_date": "2025-04-22", "installer": "mkab"},
    "we": {"serial_number": "CNG-ALTOS288-0003", "install_date": "2024-11-12", "installer": "mkab"},
}
FMS_BUFFER_TUBES = [{"name": f"Tube {n}", "position": n, "fiber_count": 12} for n in range(1, 5)]   # 4 x 12 = 48
FMS_BUFFER_TUBES_288 = [{"name": f"Tube {n}", "position": n, "fiber_count": 12} for n in range(1, 25)]   # 24 x 12 = 288

# How the 24 tubes of a metro cable are used. Half the fibers (tubes 1-12, pairs 1-72) are for WDM: pair 1 is lit,
# the rest is reserved. The other half (tubes 13-24, pairs 73-144) is dark fiber, partly for Nordfiber's own use and
# partly to lease out. The tube name carries the use, so it shows on the cable's page.
TUBE_PLAN = [(1, 12, "WDM"), (13, 16, "Nordfiber dark"), (17, 24, "leasable dark")]


def tube_use(position):
    return next(use for first, last, use in TUBE_PLAN if first <= position <= last)


# A duplex LC port on a trunk panel carries one PAIR of the trunk: strands 2n-1 and 2n land on port n at
# both ends (netbox-fms FiberStrand.front_port_a / front_port_b).
#
# FMS fiber circuits: one per trunk pair that is actually in use, from the line panel port of one muxponder to the
# line panel port of the other (data/optical.py LINE_PATCH). A circuit is 2 strands (a duplex pair), so it has two
# circuit paths, both starting at the same duplex port. FMS follows the glass from there, including the MeetMe jumpers
# of the Helsinki links. `trunk` is the cable (bb<n> as in LONG_HAUL, or a metro link key) that gives the glass length.
# A dark pair that is leased has no muxponders: it names its two `ends` (panel, port) and its `tenant` instead.
# Loss and wavelength are the end-to-end figures of the bare fiber: 0.21 dB/km plus 1.5 dB of connectors.
FIBER_CIRCUITS = [
    {"name": "Stockholm North - Gothenburg, pair 1", "cid": "NF-FC-0001", "trunk": "bb1", "wdms": ("stn-wdm-02", "got-wdm-01"),
     "description": "Line side of stn-wdm-02 and got-wdm-01: the first leg of Baltic Retail Group's protect path."},
    {"name": "Stockholm North - Oslo, pair 1", "cid": "NF-FC-0002", "trunk": "bb3", "wdms": ("stn-wdm-01", "osl-wdm-01"),
     "description": "Line side of stn-wdm-01 and osl-wdm-01: carries Fjord Media Networks' wavelength service."},
    {"name": "Gothenburg - Malmö, pair 1", "cid": "NF-FC-0003", "trunk": "bb4", "wdms": ("got-wdm-02", "mma-wdm-01"),
     "description": "Line side of got-wdm-02 and mma-wdm-01: the second leg of the protect path, regenerated in Gothenburg."},
    {"name": "Stockholm North - Helsinki (NSN), pair 1", "cid": "NF-FC-0004", "trunk": "nsn", "wdms": ("stn-wdm-03", "hel-wdm-01"),
     "description": "Line side of stn-wdm-03 and hel-wdm-01, over the NSN-DF-0001 trunk and both MeetMe rooms."},
    {"name": "Stockholm East - Helsinki (BFN), pair 1", "cid": "NF-FC-0005", "trunk": "bfn", "wdms": ("ste-wdm-01", "hel-wdm-02"),
     "description": "Line side of ste-wdm-01 and hel-wdm-02, over the BFN-DF-0001 trunk and both MeetMe rooms."},
    {"name": "Stockholm West - Gothenburg, pair 1", "cid": "NF-FC-0006", "trunk": "bb5", "wdms": ("stw-wdm-01", "got-wdm-03"),
     "description": "Line side of stw-wdm-01 and got-wdm-03: the southern route, carries Baltic Retail Group's secondary wavelength service."},
    {"name": "Stockholm North - Stockholm West, pair 1", "cid": "NF-FC-0007", "trunk": "nw", "wdms": ("stn-wdm-04", "stw-wdm-02"),
     "description": "Line side of stn-wdm-04 and stw-wdm-02 on the North - West metro cable."},
    {"name": "Stockholm North - Stockholm East, pair 1", "cid": "NF-FC-0008", "trunk": "ne", "wdms": ("stn-wdm-05", "ste-wdm-02"),
     "description": "Line side of stn-wdm-05 and ste-wdm-02 on the North - East metro cable."},
    {"name": "Stockholm West - Stockholm East, pair 1", "cid": "NF-FC-0009", "trunk": "we", "wdms": ("stw-wdm-03", "ste-wdm-03"),
     "description": "Line side of stw-wdm-03 and ste-wdm-03 on the leased West - East metro cable (SMF-DF-0001)."},
    {"name": "Stockholm North - Stockholm East, pair 97 (leased)", "cid": "NF-FC-0010", "trunk": "ne",
     "ends": (("stn-patch-ste-01", 97), ("ste-patch-stn-01", 97)), "tenant": "baltic-retail",
     "description": "A dark pair from the leasable half of the North - East metro cable, leased to Baltic Retail Group."},
]
FIBER_CIRCUIT_WAVELENGTH_NM = 1550
FIBER_CIRCUIT_LOSS_DB_PER_KM = 0.21
FIBER_CIRCUIT_CONNECTOR_LOSS_DB = 1.5


def circuit_ends(fc):
    """((panel, port), (panel, port)): where a fiber circuit's strands start and end."""
    if "ends" in fc:
        return fc["ends"]
    return tuple(O.LINE_PATCH[w] for w in fc["wdms"])
