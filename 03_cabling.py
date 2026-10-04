#!/usr/bin/env python3
"""
Layer 3: cabling inside each building.

Core rack interconnects, out-of-band management, MeetMe-room jumpers and
trunks, colo customers' racks, the Gothenburg office floor. Everything that
crosses a site border (backbone, leased spans, circuits) is layer 4; the WDM
equipment's own cabling is layer 5.

Cable type, colour, length, label and end labels are decided by
cabling.Cabler — this script only says WHAT connects to WHAT
(data/cabling.py). Safe to re-run.
"""

from cabling import Cabler
from common import connect
from data import cabling as plan
from data.organization import SITES


def run(nb):
    cabler = Cabler(nb)
    for site in SITES:
        print(f"== {site['name']} ==")
        sections = [
            ("core", plan.core_pair(site), None),
            ("meetme", plan.meetme(site), None),
            ("colo", plan.colo(site), None),
            ("office", plan.office(site), None),
            # OOB cables end on Nordfiber's switch even when the device at the
            # other end is a colo customer's: Nordfiber provides and owns them.
            ("oob", plan.oob(site), "nordfiber-ab"),
        ]
        for _name, cables, tenant in sections:
            for a, b, note in cables:
                cabler.connect(a, b, note=note, tenant=tenant)
    cabler.summary()


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nLayer 3 (in-building cabling) complete.")
