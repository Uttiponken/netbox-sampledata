"""
The one place cables are made.

Every cable in the dataset goes through Cabler.connect(), which decides —
from the two endpoints alone — everything about it, at creation time:

  type / colour   copper TP -> cat6 (cat6a to a workstation), gray
                  24-pair trunk between two patch panels (rear port to rear port) -> smf-os2, green; blue
                  when the two panels are at different sites
                  rack-to-rack DAC between network devices -> dac-passive, black
                  anything with an LC fiber end, or a circuit termination -> smf-os2, yellow
  length          same rack: 2 m, or 3 m if the devices are more than 20U apart
                  same room, other rack: 5 m;  other room, same site: 30 m
                  floor riser (IDF/office floor to the telecom room): 40 m
                  workstation horizontal run: 30 m
                  between sites: the route length in km (passed in)
                  circuit termination: none (there is no rack end to measure)
  label           <site>-cbl-NNNNN inside a site, bb-cbl-NNNNN between sites,
                  allocated in creation order; never changed once assigned
  end labels      custom fields label_a / label_b: "<cable id> -> <far end>",
                  what to print at each end so a technician sees where the
                  other end goes (TIA-606 style)
  tenant          the external party wins over Nordfiber when exactly one end
                  belongs to one (it's their cross-connect); both Nordfiber -> Nordfiber

So there is no separate "fix the cable attributes" pass: a cable that exists
already has them, and verify.py checks that.
"""

import re

import naming
from common import _same, port
from data.organization import SITES

GRAY, YELLOW, BLACK, GREEN, BLUE = "9e9e9e", "ffeb3b", "111111", "4caf50", "2196f3"
NETWORK_ROLES = {"core-router", "aggregation-switch", "oob-switch"}
COPPER_TYPES = ("1000base-t", "100base-tx", "10gbase-t")


def I(device, name):   # interface
    return ("interface", device, name)


def F(device, name):   # front port
    return ("frontport", device, name)


def R(device, name):   # rear port
    return ("rearport", device, name)


def CT(cid, side):     # circuit termination
    return ("ct", cid, side)


class Cabler:
    def __init__(self, nb):
        self.nb = nb
        self.dev = {d.name: d for d in nb.dcim.devices.all()}
        self.tenants = {t.slug: t for t in nb.tenancy.tenants.all()}
        self.site_code = {naming.site_slug(s): s["code"] for s in SITES}
        self.counters = {}
        for c in nb.dcim.cables.all():
            m = re.fullmatch(r"([a-z]+)-cbl-(\d+)", c.label or "")
            if m:
                self.counters[m.group(1)] = max(self.counters.get(m.group(1), 0), int(m.group(2)))
        self.stats = {"created": 0, "updated": 0, "exists": 0}
        self._ensure_custom_fields()

    # -- setup -------------------------------------------------------------

    def _ensure_custom_fields(self):
        for name, label in (("label_a", "Label at A end"), ("label_b", "Label at B end")):
            if not self.nb.extras.custom_fields.get(name=name):
                self.nb.extras.custom_fields.create(
                    name=name, label=label, type="text", object_types=["dcim.cable"],
                    description="Text to print on the label at this end of the cable: <cable id> -> <far end>.")

    # -- endpoints ---------------------------------------------------------

    def _resolve(self, ep):
        kind, a, b = ep
        if kind == "ct":
            circuit = self.nb.circuits.circuits.get(cid=a)
            obj = self.nb.circuits.circuit_terminations.get(circuit_id=circuit.id, term_side=b)
            return {"kind": "ct", "obj": obj, "type": "circuits.circuittermination", "dev": None,
                    "text": f"{a} ({b})"}
        obj = port(self.nb, a, kind, b)
        return {"kind": kind, "obj": obj, "type": f"dcim.{kind}", "dev": self.dev[a], "text": f"{a}:{b}"}

    # -- the rules ---------------------------------------------------------

    @staticmethod
    def _site(e):
        return e["dev"].site.slug if e["dev"] else None

    def _kind(self, a, b):
        if (a["kind"] == b["kind"] == "rearport" and a["obj"].name == "Trunk" and b["obj"].name == "Trunk"):
            # a 24-pair trunk between two patch panels: blue between sites, green inside one
            return "smf-os2", (BLUE if a["dev"].site.id != b["dev"].site.id else GREEN)
        if a["kind"] == "ct" or b["kind"] == "ct":
            return "smf-os2", YELLOW
        if a["kind"] != "interface" or b["kind"] != "interface":
            return "smf-os2", YELLOW
        types = [a["obj"].type.value, b["obj"].type.value]
        if any(t.startswith(COPPER_TYPES) for t in types):
            workstation = "workstation" in (a["dev"].role.slug, b["dev"].role.slug)
            return ("cat6a" if workstation else "cat6"), GRAY
        same_rack = a["dev"].rack and b["dev"].rack and a["dev"].rack.id == b["dev"].rack.id
        if same_rack and {a["dev"].role.slug, b["dev"].role.slug} <= NETWORK_ROLES:
            return "dac-passive", BLACK
        return "smf-os2", YELLOW

    def _length(self, a, b, km):
        if km is not None:
            return round(km, 1), "km"
        if a["kind"] == "ct" or b["kind"] == "ct":
            return None, None
        da, db = a["dev"], b["dev"]
        if "workstation" in (da.role.slug, db.role.slug):
            return 30, "m"
        if da.site.id != db.site.id:
            raise SystemExit(f"{a['text']} <-> {b['text']} spans sites but no route length was given")
        if da.rack and db.rack and da.rack.id == db.rack.id:
            return (2 if abs(da.position - db.position) <= 20 else 3), "m"
        if da.location.id == db.location.id:
            return 5, "m"
        if "Floor" in da.location.name or "Floor" in db.location.name:
            return 40, "m"
        return 30, "m"

    def _tenant(self, a, b, override):
        if override:
            return self.tenants[override]
        slugs = {e["dev"].tenant.slug for e in (a, b) if e["dev"] and e["dev"].tenant}
        external = sorted(s for s in slugs if s != "nordfiber-ab")
        if len(external) == 1 or (external and all(s == external[0] for s in external)):
            return self.tenants[external[0]]
        return self.tenants["nordfiber-ab"]

    def _label(self, a, b):
        sites = {self._site(e) for e in (a, b)} - {None}
        if len(sites) > 1:
            prefix = "bb"
        else:
            dev = next(e["dev"] for e in (a, b) if e["dev"])
            prefix = self.site_code[dev.site.slug]
        self.counters[prefix] = self.counters.get(prefix, 0) + 1
        return f"{prefix}-cbl-{self.counters[prefix]:05d}"

    # -- connect -----------------------------------------------------------

    def connect(self, a_ep, b_ep, note="", tenant=None, km=None):
        a, b = self._resolve(a_ep), self._resolve(b_ep)
        ctype, color = self._kind(a, b)
        length, unit = self._length(a, b, km)
        ten = self._tenant(a, b, tenant)
        existing = a["obj"].cable
        if existing:
            cable = self.nb.dcim.cables.get(id=existing.id)
            if not any(t.object_type == b["type"] and t.object.id == b["obj"].id for t in
                       list(cable.a_terminations) + list(cable.b_terminations)):
                raise SystemExit(
                    f"{a['text']} is already cabled (cable {cable.label}) to something other than {b['text']}")
            want = {"type": ctype, "color": color, "length": length, "length_unit": unit, "tenant": ten.id,
                    "description": note}
            changes = {k: v for k, v in want.items() if not _same(getattr(cable, k, None), v)}
            label = cable.label
            ends = {"label_a": f"{label} -> {b['text']}", "label_b": f"{label} -> {a['text']}"}
            cf = {k: v for k, v in ends.items() if (cable.custom_fields or {}).get(k) != v}
            if cf:
                changes["custom_fields"] = cf
            if changes:
                cable.update(changes)
                self.stats["updated"] += 1
                print(f"  [updated] {label}: {a['text']} <-> {b['text']} ({', '.join(changes)})")
            else:
                self.stats["exists"] += 1
            return cable
        label = self._label(a, b)
        cable = self.nb.dcim.cables.create(
            a_terminations=[{"object_type": a["type"], "object_id": a["obj"].id}],
            b_terminations=[{"object_type": b["type"], "object_id": b["obj"].id}],
            status="connected", label=label, type=ctype, color=color, length=length, length_unit=unit,
            tenant=ten.id, description=note,
            custom_fields={"label_a": f"{label} -> {b['text']}", "label_b": f"{label} -> {a['text']}"},
        )
        self.stats["created"] += 1
        ln = f", {length}{unit}" if length is not None else ""
        print(f"  [created] {label}: {a['text']} <-> {b['text']} ({ctype}{ln})")
        return cable

    def summary(self):
        s = self.stats
        print(f"  cables: {s['created']} created, {s['updated']} updated, {s['exists']} unchanged")
