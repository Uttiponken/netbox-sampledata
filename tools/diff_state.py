#!/usr/bin/env python3
"""
Compare two state dumps (tools/dump_state.py) section by section.

    python tools/diff_state.py reference/state-before-refactor.json /tmp/state-after.json

The old dump is first rewritten through RENAMES (the intended renames of the
refactor), so what is left are the differences nobody asked for — or the ones
that were asked for and can now be reviewed. Cable labels, types, colours and
lengths are not compared: those were redefined on purpose.
"""

import json
import sys

RENAMES = {
    "sites": {"nordfiber-gothenburg-pop": "nordfiber-gothenburg-dc"},
    "racks": {
        "STO-RACK-A1": "STO-TR-01", "STO-RACK-B1": "STO-CH-01", "STO-RACK-MMR1": "STO-MM-01",
        "GOT-RACK-1": "GOT-TR-01", "GOT-RACK-2": "GOT-CH-01", "GOT-RACK-3": "GOT-CH-02",
        "GOT-RACK-C1": "GOT-CH-03", "GOT-RACK-C2": "GOT-CH-04", "GOT-RACK-IDF3": "GOT-IDF-01", "GOT-RACK-MMR1": "GOT-MM-01",
        "MMA-RACK-1": "MMA-TR-01", "MMA-RACK-MMR1": "MMA-MM-01",
        "OSL-RACK-1": "OSL-TR-01", "OSL-RACK-MMR1": "OSL-MM-01",
        "HEL-RACK-1": "HEL-TR-01", "HEL-RACK-MMR1": "HEL-MM-01",
    },
    "locations": {
        "stockholm-suite-100-row-a": "stockholm-telecom-room", "stockholm-suite-100-row-b": "stockholm-colo-hall",
        "gothenburg-suite-200": "gothenburg-colo-hall", "gothenburg-suite-200-row-c": "gothenburg-colo-hall",
    },
    "devices": {
        "polaris-sto-mmr-01": "sto-mmr-polaris-01", "polaris-got-mmr-01": "got-mmr-polaris-01",
        "vasthamnen-got-mmr-01": "got-mmr-vasthamnen-01", "vastkust-got-panel-01": "got-mmr-vastkust-01",
    },
}
IGNORED_CABLE_FIELDS = {"label", "type", "color", "length", "length_unit", "custom_fields", "description", "comments"}
IGNORED_SECTIONS = {"wdm"}   # compared separately below
# serials and asset tags are numbered by creation order, which the new layout changed;
# only whether they are set is compared
PRESENCE_ONLY = {"devices": {"serial", "asset_tag"}}


def rename_text(s, maps):
    for m in maps:
        for old, new in sorted(m.items(), key=lambda kv: -len(kv[0])):
            s = s.replace(old, new)
    return s


def apply_renames(old):
    all_maps = [RENAMES["devices"], RENAMES["racks"], RENAMES["sites"], RENAMES["locations"]]
    out = {}
    for sec, val in old.items():
        if isinstance(val, dict):
            out[sec] = {}
            for k, v in val.items():
                nk = RENAMES.get(sec, {}).get(k, k)
                if sec in ("cables", "ip_addresses"):
                    nk = rename_text(k, [RENAMES["devices"]])
                if sec == "cables":
                    nk = " <> ".join(sorted(nk.split(" <> ")))
                if isinstance(v, dict):
                    v = {fk: (RENAMES.get({"rack": "racks", "location": "locations", "site": "sites"}.get(fk, ""), {}).get(fv, fv)
                              if isinstance(fv, str) else fv) for fk, fv in v.items()}
                    if sec == "ip_addresses" and v.get("assigned"):
                        v["assigned"] = rename_text(v["assigned"], [RENAMES["devices"]])
                out[sec][nk] = v
        elif isinstance(val, list):
            out[sec] = sorted(rename_text(x, all_maps) if isinstance(x, str) else x for x in val)
        else:
            out[sec] = val
    return out


def diff(old, new, limit=40):
    for sec in sorted(set(old) | set(new)):
        if sec in IGNORED_SECTIONS:
            continue
        a, b = old.get(sec), new.get(sec)
        if isinstance(a, dict) and isinstance(b, dict):
            only_old, only_new = sorted(set(a) - set(b)), sorted(set(b) - set(a))
            changed = []
            for k in sorted(set(a) & set(b)):
                if isinstance(a[k], dict) and isinstance(b[k], dict):
                    ign = IGNORED_CABLE_FIELDS if sec == "cables" else set()
                    pres = PRESENCE_ONLY.get(sec, set())
                    fields = {f: (a[k].get(f), b[k].get(f)) for f in set(a[k]) | set(b[k])
                              if f not in ign and (bool(a[k].get(f)) != bool(b[k].get(f)) if f in pres
                                                   else a[k].get(f) != b[k].get(f))}
                    if fields:
                        changed.append((k, fields))
                elif a[k] != b[k]:
                    changed.append((k, {"value": (a[k], b[k])}))
            same = len(set(a) & set(b)) - len(changed)
            print(f"## {sec}: {same} identical, {len(changed)} changed, {len(only_old)} only in old, {len(only_new)} only in new")
            for label, items in (("only in old", only_old), ("only in new", only_new)):
                for k in items[:limit]:
                    print(f"   {label}: {k}")
                if len(items) > limit:
                    print(f"   {label}: ... {len(items) - limit} more")
            for k, fields in changed[:limit]:
                print(f"   changed: {k}: " + "; ".join(f"{f}: {x!r} -> {y!r}" for f, (x, y) in sorted(fields.items())))
            if len(changed) > limit:
                print(f"   changed: ... {len(changed) - limit} more")
        elif a != b:
            if isinstance(a, list) and isinstance(b, list):
                print(f"## {sec}: only in old {sorted(set(a) - set(b))}  only in new {sorted(set(b) - set(a))}")
            else:
                print(f"## {sec}: {a!r} -> {b!r}")
    print(f"## wdm: old {old.get('wdm', {}).get('circuits')} / new {new.get('wdm', {}).get('circuits')}")


if __name__ == "__main__":
    old = json.load(open(sys.argv[1], encoding="utf-8"))
    new = json.load(open(sys.argv[2], encoding="utf-8"))
    diff(apply_renames(old), new)
