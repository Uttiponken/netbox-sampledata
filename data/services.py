"""
Layer 6 data: addressing and services on top of the physical build.

Scope is deliberately thin: out-of-band management addressing, a loopback
per core router with an iBGP full mesh, one login secret per core router
and a small cold-spares depot. Nothing higher up the stack.
"""

BGP_ASN = 65001
PEER_GROUP = {"name": "NORDFIBER-IBGP", "description": "Full-mesh iBGP among Nordfiber's core routers"}

# Router 01 at every site carries the loopback and the BGP/credential records;
# router 02 (data centers only) is a management-only second chassis for now.
# Loopbacks are 10.255.0.N/32 in this order, which is also the session order.
ROUTER_ORDER = ["sto", "got", "mma", "osl", "hel"]

# Placeholder passwords, obviously fake; a real deployment uses generated ones.
SECRET_ROLE = {"name": "Device Login", "slug": "device-login"}
PASSWORDS = {"sto": "Nf-Sto-Rtr-D3mo!", "got": "Nf-Got-Rtr-D3mo!", "mma": "Nf-Mma-Rtr-D3mo!",
             "osl": "Nf-Osl-Rtr-D3mo!", "hel": "Nf-Hel-Rtr-D3mo!"}

ASSET_ROLE = {"name": "Spare Chassis", "slug": "spare-chassis", "color": "ff9800"}
# One cold spare of each chassis whose failure would take a site down; kept in Stockholm's telecom room.
SPARE_ASSETS = [
    {"name": "Spare Juniper MX204", "type": "juniper-mx204", "serial": "SPARE-MX204-001"},
    {"name": "Spare Arista DCS-7050SX3-48YC8-F", "type": "arista-dcs-7050sx3-48yc8-f", "serial": "SPARE-7050-001"},
    {"name": "Spare SmartOptics DCP-M40-PAM4-ER", "type": "smartoptics-dcp-m40-pam4-er", "serial": "SPARE-DCPM40-001"},
]
