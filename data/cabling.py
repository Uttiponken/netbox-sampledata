"""
Layer 3 data: the cabling inside each building, as plain lists of
(end A, end B, note[, options]) so the plan can be read top to bottom.

Port conventions (identical at every site, which is the point):

  trunk patch panel            24 duplex LC ports on the front, ONE rear port "Trunk" with 24 positions: the
  (Telecom Room)               rear is a 24-pair trunk (one cable, 48 fibers) to the panel at the other end,
                               the FRONT goes to the equipment that uses the pair
  Nordfiber MeetMe panel       one port per external party; REAR = trunk to the
                               patch panel, FRONT = jumper to the party's own panel
  core rack                    rtr-01 xe-0/1/0 -> sw-01 Ethernet1 (+ the DC redundancy mesh)
  OOB switch                   1 router-01, 2 switch-01, 3.. WDM nodes, 7 DCP-2,
                               8.. everything else in the building, 13/14 router/switch 02,
                               49 uplink to router-01 (50 to router-02 at DCs)
"""

from cabling import F, I, R
from data import hardware as H
from layout import colo_racks, core_names

# ---------------------------------------------------------------------------
# MeetMe room: which party lands on which Nordfiber MeetMe port, and where the
# trunk's front port at the telecom-room panel finally goes. The trunk keeps the
# pair number, so MeetMe port N is port N on `<site>-patch-mmr-01` too.
#   party -> (MeetMe port, handoff)
# handoff: (device suffix, interface) on the local core, or None when the
# port is lit by a WDM node (layer 5) instead.
# ---------------------------------------------------------------------------
PARTY_LINKS = {
    "sto": {"polaris": (1, ("sw-01", "Ethernet2")), "nsn": (2, None), "bfn": (3, None),
            "baltic-retail": (4, ("sw-01", "Ethernet3"))},
    "got": {"polaris": (1, ("sw-01", "Ethernet2")), "vasthamnen": (2, ("sw-01", "Ethernet3")),
            "vastkust": (3, ("rtr-01", "xe-0/1/1"))},
    "mma": {"baltic-retail": (1, ("sw-01", "Ethernet2"))},
    "hel": {"nsn": (1, None), "bfn": (2, None)},
}

# The party's own panel always uses its port 1.
PARTY_PORT = 1

# Gothenburg office floor: the IDF switch uplinks to the aggregation switch,
# Erik's workstation hangs off the IDF switch.
IDF_UPLINK = ("Ethernet49", "Ethernet4")      # (IDF switch, got-sw-01)
WORKSTATION_PORT = ("Ethernet1", "Gig-E 1")    # (IDF switch, workstation)


def core_pair(site):
    """Router/switch interconnect in the core rack. DCs get a full cross-connect mesh."""
    c = site["code"]
    r1, sw1 = f"{c}-rtr-01", f"{c}-sw-01"
    plan = [(I(r1, "xe-0/1/0"), I(sw1, "Ethernet1"), "router to aggregation switch")]
    if site["kind"] == "dc":
        r2, sw2 = f"{c}-rtr-02", f"{c}-sw-02"
        plan += [
            (I(r1, "xe-0/1/3"), I(sw2, "Ethernet1"), "router 01 to switch 02 (cross-connect)"),
            (I(r2, "xe-0/1/0"), I(sw1, "Ethernet5"), "router 02 to switch 01 (cross-connect)"),
            (I(r2, "xe-0/1/3"), I(sw2, "Ethernet5"), "router 02 to switch 02"),
            (I(r1, "xe-0/1/4"), I(r2, "xe-0/1/4"), "router interconnect"),
            (I(sw1, "Ethernet6"), I(sw2, "Ethernet6"), "switch interconnect"),
        ]
    return plan


def oob(site):
    """Every management port in the building, onto the site's OOB switch."""
    c = site["code"]
    names = core_names(site)
    plan = []

    def add(n, device, iface, note="OOB management"):
        plan.append((I(names["oob"], f"Ethernet{n}"), I(device, iface), note))

    add(1, names["rtr"][0], H.MGMT_IFACE[H.T_ROUTER])
    add(2, names["sw"][0], H.MGMT_IFACE[H.T_AGG_SWITCH])
    for i, w in enumerate(names["wdm"]):
        add(3 + i, w, H.MGMT_IFACE[H.T_WDM])
    add(7, names["dcp2"], H.MGMT_IFACE[H.T_DCP2])
    nxt = 8
    if c == "got":
        add(nxt, H.IDF_SWITCH_NAME, H.MGMT_IFACE[H.T_COPPER_SWITCH])
        nxt += 1
    for rack, tenant in colo_racks(site):
        if tenant == "nordfiber":
            continue
        add(nxt, f"{tenant}-{c}-sw-01", H.MGMT_IFACE[H.T_COPPER_SWITCH])
        nxt += 1
        for n in range(1, H.COLO_SERVERS.get((c, tenant), 0) + 1):
            add(nxt, f"{tenant}-{c}-srv-{n:02d}", H.MGMT_IFACE[H.T_SERVER])
            nxt += 1
    if site["kind"] == "dc":
        add(13, names["rtr"][1], H.MGMT_IFACE[H.T_ROUTER])
        add(14, names["sw"][1], H.MGMT_IFACE[H.T_AGG_SWITCH])
    plan.append((I(names["oob"], "Ethernet49"), I(names["rtr"][0], "xe-0/1/2"), "OOB uplink"))
    if site["kind"] == "dc":
        plan.append((I(names["oob"], "Ethernet50"), I(names["rtr"][1], "xe-0/1/2"), "OOB uplink (second router)"))
    return plan


def meetme(site):
    """MeetMe room legs that belong to this building: the trunk, jumpers and the patch-panel handoff."""
    c = site["code"]
    names = core_names(site)
    nf = f"{c}-mmr-nordfiber-01"
    plan = [(R(nf, "Trunk"), R(names["patch"]["mmr"], "Trunk"), "24-pair trunk, MeetMe room to telecom room")]
    for party, (mm_port, handoff) in PARTY_LINKS.get(c, {}).items():
        panel = f"{c}-mmr-{party}-01"
        plan.append((F(nf, f"Port {mm_port}"), F(panel, f"Port {PARTY_PORT}"), f"cross-connect jumper to {party}"))
        if handoff:
            suffix, iface = handoff
            plan.append((F(names["patch"]["mmr"], f"Port {mm_port}"), I(f"{c}-{suffix}", iface), f"{party} handoff"))
    return plan


def colo(site):
    """Each colo customer's rack: servers -> switch -> ToR panel -> trunk to the customer's MeetMe panel."""
    c = site["code"]
    plan = []
    for rack, tenant in colo_racks(site):
        if tenant == "nordfiber":
            continue
        tor, sw = f"{tenant}-{c}-tor-01", f"{tenant}-{c}-sw-01"
        for n in range(1, H.COLO_SERVERS.get((c, tenant), 0) + 1):
            plan.append((I(f"{tenant}-{c}-srv-{n:02d}", "Gig-E 1"), I(sw, f"Ethernet{n}"), "server uplink"))
        plan.append((F(tor, f"Port {PARTY_PORT}"), I(sw, "Ethernet49"), "switch uplink to ToR panel"))
        plan.append((R(f"{c}-mmr-{tenant}-01", "Trunk"), R(tor, "Trunk"), "24-pair trunk, MeetMe room to colo hall"))
    return plan


def office(site):
    if site["code"] != "got":
        return []
    sw = H.IDF_SWITCH_NAME
    return [
        (I(sw, WORKSTATION_PORT[0]), I(H.WORKSTATION_NAME, WORKSTATION_PORT[1]), "workstation, horizontal cabling"),
        (I(sw, IDF_UPLINK[0]), I("got-sw-01", IDF_UPLINK[1]), "IDF riser to aggregation switch"),
    ]
