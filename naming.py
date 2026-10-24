"""
The naming convention, in one place, so it looks the same everywhere.

  site          nordfiber-<city>-<dc|pop>        slug;  "Nordfiber <City> DC|PoP"  name  (Stockholm is three DCs: stockholm-north|west|east)
  room          <city>-<room>                     slug;  Telecom Room / MeetMe Room / Colo Hall / ...
  rack          <SITE>-<ROOM>-<NN>                STN-TR-01, GOT-MM-01, GOT-CH-02, GOT-IDF-01
  Nordfiber kit <site>-<role>-<NN>                stn-rtr-01, got-wdm-02, hel-oob-01
  tenant kit    <tenant>-<site>-<role>-<NN>       polaris-stn-sw-01, vasthamnen-got-srv-01
  MeetMe panel  <site>-mmr-<party>-01             got-mmr-vastkust-01
  trunk panel   <site>-patch-<to>-01              stn-patch-mmr-01, stn-patch-got-01 (one 24-pair trunk each; 144-pair on the Stockholm metro ring)
  cable label   <site>-cbl-NNNNN (inside a site) / bb-cbl-NNNNN (between sites)
  serial        <MFR>-<SITE>-<nnnn>               every device
  asset tag     NF-<SITE>-<nnnnn>                 Nordfiber-owned devices only
"""

ROOMS = {
    "tr": ("Telecom Room", "telecom-room"),
    "mm": ("MeetMe Room", "meetme-room"),
    "ch": ("Colo Hall", "colo-hall"),
    "idf": ("IDF Floor 3", "idf-floor-3"),
    "office": ("Office Floor 3", "office-floor-3"),
}


def site_slug(site):
    return f"nordfiber-{site['city']}-{site['kind']}"


def room_slug(site, room):
    return f"{site['city']}-{ROOMS[room][1]}"


def rack_name(site, room, n):
    return f"{site['code'].upper()}-{room.upper()}-{n:02d}"


MANUFACTURER_CODES = {"juniper": "JNP", "arista": "ARI", "dell": "DLL", "smartoptics": "SMO", "generic": "GEN"}
