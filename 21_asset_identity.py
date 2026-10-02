#!/usr/bin/env python3
"""
Phase 21: asset identity — serials and asset tags (added post-hoc,
2026-10-02). Gives every device a serial and every Nordfiber-owned device
an asset tag; formats and rationale in config.py's Phase 21 comment.

Only fills in what's missing and continues each counter from the highest
existing value, so it is safe to re-run and never renumbers anything.

Depends on every phase that creates devices (run last of the device
phases). Safe to re-run.
"""

import re

from common import connect
from config import ASSET_TAG_OWNER_TENANT, MANUFACTURER_CODES, SITE_CODES


def run(nb):
    devices = sorted(nb.dcim.devices.all(), key=lambda d: d.name)

    serial_next, tag_next = {}, {}
    for d in devices:
        site = SITE_CODES[d.site.slug]
        mfr = MANUFACTURER_CODES[d.device_type.manufacturer.slug]
        m = re.fullmatch(rf"{mfr}-{site}-(\d+)", d.serial or "")
        if m:
            serial_next[(mfr, site)] = max(serial_next.get((mfr, site), 1), int(m.group(1)) + 1)
        m = re.fullmatch(rf"NF-{site}-(\d+)", d.asset_tag or "")
        if m:
            tag_next[site] = max(tag_next.get(site, 1), int(m.group(1)) + 1)

    print("== Serials and asset tags ==")
    changed = 0
    for d in devices:
        site = SITE_CODES[d.site.slug]
        mfr = MANUFACTURER_CODES[d.device_type.manufacturer.slug]
        updates = []
        if not d.serial:
            n = serial_next.get((mfr, site), 1)
            serial_next[(mfr, site)] = n + 1
            d.serial = f"{mfr}-{site}-{n:04d}"
            updates.append(f"serial {d.serial}")
        if not d.asset_tag and d.tenant and d.tenant.slug == ASSET_TAG_OWNER_TENANT:
            n = tag_next.get(site, 1)
            tag_next[site] = n + 1
            d.asset_tag = f"NF-{site}-{n:05d}"
            updates.append(f"asset tag {d.asset_tag}")
        if updates:
            d.save()
            changed += 1
            print(f"  [updated] {d.name}: {', '.join(updates)}")
    if not changed:
        print("  [exists ] every device already has its serial/asset tag")


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 21 (asset identity) complete.")
