"""
Turns the site profiles (data/organization.py) and placement rules
(data/hardware.py) into the full list of racks and devices.

Nothing here is NetBox-specific: it returns plain dicts, so the same
generator feeds the hardware layer, the cabling layer and verify.py and
they can never disagree about a name or a slot.
"""

from data import hardware as H
from data.organization import SITES
from naming import rack_name, room_slug


def site_by_code(code):
    return next(s for s in SITES if s["code"] == code)


def core_names(site):
    """Names of the core-rack devices for a site (used by cabling too)."""
    c = site["code"]
    patch = {"mmr": f"{c}-patch-mmr-01"}
    patch.update({peer: f"{c}-patch-{peer}-01" for peer in H.backbone_peers(c)})
    n = {"patch": patch, "oob": f"{c}-oob-01", "rtr": [f"{c}-rtr-01"], "sw": [f"{c}-sw-01"],
         "wdm": [f"{c}-wdm-{i:02d}" for i in range(1, site["wdm_nodes"] + 1)], "dcp2": f"{c}-dcp2-01"}
    if site["kind"] == "dc":
        n["rtr"].append(f"{c}-rtr-02")
        n["sw"].append(f"{c}-sw-02")
    return n


def colo_racks(site):
    """[(rack name, tenant code)] for customer racks, then growth racks."""
    out = [(rack_name(site, "ch", i), c) for i, c in enumerate(site["colo"], start=1)]
    start = len(out) + 1
    out += [(rack_name(site, "ch", start + i), "nordfiber") for i in range(site["growth_racks"])]
    return out


def inventory():
    racks, devices = [], []

    def rack(site, room, n, tenant, role):
        racks.append({"name": rack_name(site, room, n), "site": site["code"], "room": room, "tenant": tenant, "role": role})

    def dev(name, type_, role, site, room, rack_, pos, tenant, mgmt_host=None, mgmt_iface=None):
        devices.append({"name": name, "type": type_, "role": role, "site": site["code"], "room": room,
                        "rack": rack_, "position": pos, "tenant": tenant,
                        "mgmt_ip": f"10.0.{site['mgmt']}.{mgmt_host}/24" if mgmt_host else None,
                        "mgmt_iface": mgmt_iface or H.MGMT_IFACE.get(type_)})

    for site in SITES:
        code = site["code"]
        names = core_names(site)

        # ---- core rack (Telecom Room)
        tr = rack_name(site, "tr", 1)
        rack(site, "tr", 1, "nordfiber", "core")
        for key, pname in names["patch"].items():
            ptype = H.T_PANEL if key == "mmr" else H.panel_type(code, key)
            dev(pname, ptype, "patch-panel", site, "tr", tr, H.CORE_SLOTS["patch"][key], "nordfiber")
        dev(names["oob"], H.T_COPPER_SWITCH, "oob-switch", site, "tr", tr, H.CORE_SLOTS["oob"], "nordfiber")
        for i, n in enumerate(names["rtr"]):
            dev(n, H.T_ROUTER, "core-router", site, "tr", tr, H.CORE_SLOTS["rtr"][i], "nordfiber",
                H.MGMT_HOST[f"rtr-0{i + 1}"])
        for i, n in enumerate(names["sw"]):
            dev(n, H.T_AGG_SWITCH, "aggregation-switch", site, "tr", tr, H.CORE_SLOTS["sw"][i], "nordfiber",
                H.MGMT_HOST[f"sw-0{i + 1}"])
        for i, n in enumerate(names["wdm"]):
            dev(n, H.T_WDM, "wdm-terminal", site, "tr", tr, H.CORE_SLOTS["wdm_first"] - i, "nordfiber")
        dev(names["dcp2"], H.T_DCP2, "wdm-client-shelf", site, "tr", tr, H.CORE_SLOTS["dcp2"], "nordfiber")

        # ---- MeetMe rack
        mm = rack_name(site, "mm", 1)
        rack(site, "mm", 1, site["mm_owner"], "meetme")
        dev(f"{code}-mmr-nordfiber-01", H.T_PANEL, "patch-panel", site, "mm", mm, H.MEETME_SLOTS["nordfiber"], "nordfiber")
        if site["mm_owner"] != "nordfiber":
            dev(f"{code}-mmr-{site['mm_owner']}-01", H.T_PANEL, "patch-panel", site, "mm", mm,
                H.MEETME_SLOTS["owner"], site["mm_owner"])
        for i, party in enumerate(H.MEETME_PARTIES[code]):
            dev(f"{code}-mmr-{party}-01", H.T_PANEL, "patch-panel", site, "mm", mm,
                H.MEETME_SLOTS["party_first"] - i, party)

        # ---- Colo Hall: customer racks (tenant-owned kit) and empty growth racks
        for idx, (rname, tenant) in enumerate(colo_racks(site), start=1):
            rack(site, "ch", idx, tenant, "colo")
            if tenant == "nordfiber":
                continue
            dev(f"{tenant}-{code}-tor-01", H.T_PANEL, "patch-panel", site, "ch", rname, H.COLO_SLOTS["tor"], tenant)
            dev(f"{tenant}-{code}-sw-01", H.T_COPPER_SWITCH, "access-switch", site, "ch", rname, H.COLO_SLOTS["sw"], tenant)
            for s in range(1, H.COLO_SERVERS[(code, tenant)] + 1):
                host = H.MGMT_HOST["srv"] + sum(
                    H.COLO_SERVERS[k] for k in H.COLO_SERVERS if k[0] == code and
                    [c for c in site["colo"]].index(k[1]) < site["colo"].index(tenant)) + (s - 1)
                dev(f"{tenant}-{code}-srv-{s:02d}", H.T_SERVER, "server", site, "ch", rname,
                    H.COLO_SLOTS["srv_first"] - (s - 1), tenant, host)

    # ---- Gothenburg office: IDF closet on floor 3 and Erik's desk
    got = site_by_code("got")
    rack(got, "idf", 1, "nordfiber", "idf")
    dev(H.IDF_SWITCH_NAME, H.T_COPPER_SWITCH, "access-switch", got, "idf", rack_name(got, "idf", 1),
        H.IDF_SLOTS["sw"], "nordfiber", H.MGMT_HOST["idf"])
    dev(H.WORKSTATION_NAME, H.T_WORKSTATION, "workstation", got, "office", None, None, "nordfiber",
        H.MGMT_HOST["ws"], "Gig-E 1")
    return racks, devices


def rooms_for(site):
    """Room keys a site needs, in a stable order."""
    rooms = ["tr", "mm"]
    if site["colo"] or site["growth_racks"]:
        rooms.append("ch")
    if site["code"] == "got":
        rooms += ["idf", "office"]
    return rooms
