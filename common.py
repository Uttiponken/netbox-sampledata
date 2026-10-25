"""
Shared helpers for the Nordfiber AB sample-data build.

Every layer script (01_organization.py ... 07_finalize.py) goes through this
module instead of calling pynetbox directly, so two rules hold everywhere:

  * ensure() is idempotent AND reconciling: it creates what is missing and
    UPDATES existing objects whose declared fields have drifted. (The old
    get_or_create() only ever created, so editing the data never reached an
    object that already existed — the cause of several earlier bugs.)
  * Anything that can only be decided at creation time (rack placement,
    serials) is passed in `once=` and is never touched on a re-run.
"""

import math
import os
import re
import sys
import urllib.request

import pynetbox
import requests
import yaml
from dotenv import load_dotenv

load_dotenv()

NETBOX_URL = os.environ.get("NETBOX_URL", "http://localhost:8000")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")

if not NETBOX_TOKEN:
    sys.exit(
        "NETBOX_TOKEN is not set. Copy .env.example to .env and fill in a "
        "NetBox API token (see README.md), or run tools/reset_netbox.sh."
    )


def connect():
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
    try:
        status = nb.status()
    except pynetbox.RequestError as e:
        sys.exit(f"Could not reach or authenticate to {NETBOX_URL}: {e}")
    detect_plugins(status)
    return nb


def api(path, method="get", json=None, extra_headers=None):
    """
    Raw request for things pynetbox has no method for (custom DRF actions such
    as netbox-wdm's /stitch/ and /trace/, netbox-secrets' /session-key/).
    `path` is relative to NETBOX_URL, e.g. "/api/plugins/wdm/wdm-circuits/1/stitch/".
    """
    headers = {"Authorization": f"Token {NETBOX_TOKEN}"}
    headers.update(extra_headers or {})
    resp = requests.request(method, f"{NETBOX_URL}{path}", headers=headers, json=json, timeout=60)
    resp.raise_for_status()
    return resp.json() if resp.content else None


# ---------------------------------------------------------------------------
# Optional plugins
# ---------------------------------------------------------------------------
#
# The dataset loads into a vanilla NetBox. The six plugins below add layers on top of the core data (cables,
# circuits, devices, addresses are always loaded); each plugin step asks have() first and says [skipped] when
# the plugin is missing. NETBOX_SKIP_PLUGINS=wdm,pathways switches plugins off on purpose, to test a subset.

PLUGINS = {          # name -> (python module as NetBox reports it, what the dataset uses it for)
    "pathways": ("netbox_pathways", "structures, ducts, water crossings, cable routes and circuit geometries"),
    "fms": ("netbox_fms", "fiber cable records, tubes, strands and fiber circuits"),
    "wdm": ("netbox_wdm", "WDM nodes, channels and wavelength services"),
    "bgp": ("netbox_bgp", "the BGP peer group and the iBGP sessions"),
    "secrets": ("netbox_secrets", "encrypted device logins"),
    "inventory": ("netbox_inventory", "spare-asset records"),
}

PLUGIN_STATE = {}    # name -> "ok", or the reason it is not used ("is not installed", ...)
PLUGIN_VERSION = {}


def detect_plugins(status):
    """Decide per plugin whether it can be used: installed, not switched off, and its REST API answers."""
    off = {n.strip() for n in os.environ.get("NETBOX_SKIP_PLUGINS", "").split(",") if n.strip()}
    unknown = off - set(PLUGINS)
    if unknown:
        sys.exit(f"NETBOX_SKIP_PLUGINS names unknown plugins {sorted(unknown)}; known: {', '.join(PLUGINS)}")
    installed = status.get("plugins") or {}
    for name, (module, _what) in PLUGINS.items():
        PLUGIN_VERSION[name] = installed.get(module)
        if name in off:
            PLUGIN_STATE[name] = "is switched off by NETBOX_SKIP_PLUGINS"
        elif module not in installed:
            PLUGIN_STATE[name] = "is not installed"
        else:
            try:
                api(f"/api/plugins/{name}/")
                PLUGIN_STATE[name] = "ok"
            except requests.HTTPError as e:
                PLUGIN_STATE[name] = f"is installed but its REST API answers HTTP {e.response.status_code}"


def have(name):
    """True if the plugin is installed, not switched off, and usable through the REST API."""
    if not PLUGIN_STATE:
        raise RuntimeError("have() before connect(): plugins are detected when connecting")
    return PLUGIN_STATE[name] == "ok"


def version_at_least(name, *wanted):
    """True if the installed plugin is at least this version, e.g. version_at_least("pathways", 0, 3)."""
    found = tuple(int(part) for part in re.findall(r"\d+", PLUGIN_VERSION.get(name) or "")[:3])
    return found >= wanted


def skip(name, what):
    """Say that a plugin step was left out, and why. The line is counted by build.py's summary."""
    print(f"  [skipped] {what}: netbox-{name} {PLUGIN_STATE[name]}")


def plugin_report():
    """Lines for the start of a build: which plugins will be used, which are missing and what they would add."""
    lines = []
    for name, (_module, what) in PLUGINS.items():
        if PLUGIN_STATE[name] == "ok":
            lines.append(f"  used     netbox-{name} {PLUGIN_VERSION[name]}")
        else:
            lines.append(f"  missing  netbox-{name} {PLUGIN_STATE[name]}; would add {what}")
    return lines


# ---------------------------------------------------------------------------
# ensure(): create-or-reconcile
# ---------------------------------------------------------------------------

def _plain(v):
    """Reduce a pynetbox value (nested record, choice, list) to a comparable plain value."""
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        return sorted(_plain(x) for x in v)
    if hasattr(v, "value") and not isinstance(v, (str, int, float)):
        return v.value
    if hasattr(v, "id") and not isinstance(v, (str, int, float)):
        return v.id
    return v


def _same(current, wanted):
    current, wanted = _plain(current), _plain(wanted)
    if isinstance(wanted, list):
        cur = current if isinstance(current, list) else ([] if current is None else [current])
        return sorted(wanted) == sorted(cur)
    if isinstance(current, bool) or isinstance(wanted, bool):
        return current == wanted
    if isinstance(current, (int, float)) and isinstance(wanted, (int, float)):
        return abs(float(current) - float(wanted)) < 1e-6
    if current in (None, "") and wanted in (None, ""):
        return True
    return str(current).strip() == str(wanted).strip()


def ensure(endpoint, lookup, once=(), **fields):
    """
    Return (object, state), state in {"created", "updated", "exists"}.

    `lookup` finds the object (e.g. {"slug": "x"}); `fields` is the full
    desired state (must include everything needed to create). On an
    existing object every declared field is reconciled except those named
    in `once`, which are only ever applied at creation.
    """
    obj = endpoint.get(**lookup)
    if obj is None:
        return endpoint.create(**fields), "created"
    changes = {}
    for key, wanted in fields.items():
        if key in once:
            continue
        if not _same(getattr(obj, key, None), wanted):
            changes[key] = wanted
    if changes:
        obj.update(changes)
        obj = endpoint.get(**lookup)
        return obj, "updated"
    return obj, "exists"


def report(label, obj, state, detail=""):
    name = getattr(obj, "name", None) or getattr(obj, "label", None) or getattr(obj, "cid", None) or getattr(obj, "display", obj)
    extra = f" — {detail}" if detail else ""
    print(f"  [{state:7}] {label}: {name}{extra}")


def get_or_create(endpoint, lookup, **fields):
    """Create-only variant, for children that are created in bulk (templates)."""
    obj = endpoint.get(**lookup)
    if obj:
        return obj, False
    return endpoint.create(**fields), True


# ---------------------------------------------------------------------------
# Real device/module types from the NetBox community library
# ---------------------------------------------------------------------------

DEVICETYPE_LIBRARY_RAW = "https://raw.githubusercontent.com/netbox-community/devicetype-library/master"


def fetch_devicetype_yaml(path):
    """Fetch e.g. "Juniper/MX204" live from the community Device Type Library."""
    with urllib.request.urlopen(f"{DEVICETYPE_LIBRARY_RAW}/device-types/{path}.yaml") as resp:
        return yaml.safe_load(resp.read())


def fetch_moduletype_yaml(path):
    """Same, for the library's separate module-types/ tree."""
    with urllib.request.urlopen(f"{DEVICETYPE_LIBRARY_RAW}/module-types/{path}.yaml") as resp:
        return yaml.safe_load(resp.read())


def create_device_type_from_yaml(nb, manufacturers, yaml_data):
    """
    DeviceType + interface/rear-port/front-port/module-bay templates from a
    library YAML dict. Templates are only created together with a NEW type.
    Power and console ports are deliberately not imported (out of scope).
    """
    mfr = manufacturers[yaml_data["manufacturer"]]
    dt, created = get_or_create(
        nb.dcim.device_types, {"slug": yaml_data["slug"]},
        manufacturer=mfr.id, model=yaml_data["model"], slug=yaml_data["slug"],
        part_number=yaml_data.get("part_number", ""), u_height=yaml_data.get("u_height", 1),
        is_full_depth=yaml_data.get("is_full_depth", True),
    )
    print(f"  [{'created' if created else 'exists ':7}] device type: {dt.model}")
    if not created:
        return dt

    for iface in yaml_data.get("interfaces", []):
        nb.dcim.interface_templates.create(
            device_type=dt.id, name=iface["name"], type=iface["type"], mgmt_only=iface.get("mgmt_only", False),
        )

    # Rear ports first (front ports map to them by id). A front port's
    # mapping has TWO position fields: `position` (the front port's own
    # slot, 1 for a simplex LC) and `rear_port_position` (which slot of the
    # rear port it uses — 1..40 on a 40-channel muxponder). Leaving the
    # latter unset defaults it to 1 and every front port past the first
    # collides.
    rear_ids = {}
    for rp in yaml_data.get("rear-ports", []):
        obj = nb.dcim.rear_port_templates.create(
            device_type=dt.id, name=rp["name"], type=rp["type"], positions=rp.get("positions", 1),
        )
        rear_ids[rp["name"]] = obj.id
    ordered_rear = list(rear_ids.values())
    mappings = yaml_data.get("port-mappings")
    for i, fp in enumerate(yaml_data.get("front-ports", [])):
        if mappings:
            m = next(m for m in mappings if m["front_port"] == fp["name"])
            rear_field = [{"rear_port": rear_ids[m["rear_port"]], "position": m["front_port_position"],
                           "rear_port_position": m["rear_port_position"]}]
        else:
            rear_field = [{"rear_port": ordered_rear[i], "position": 1}]
        nb.dcim.front_port_templates.create(device_type=dt.id, name=fp["name"], type=fp["type"], rear_ports=rear_field)

    for mb in yaml_data.get("module-bays", []):
        nb.dcim.module_bay_templates.create(
            device_type=dt.id, name=mb["name"], position=mb.get("position", ""), description=mb.get("description", ""),
        )
    return dt


def create_module_type_from_yaml(nb, manufacturers, yaml_data):
    """ModuleType (no slug; keyed by manufacturer+model) + interface templates ('{module}' placeholders kept)."""
    mfr = manufacturers[yaml_data["manufacturer"]]
    mt, created = get_or_create(
        nb.dcim.module_types, {"manufacturer_id": mfr.id, "model": yaml_data["model"]},
        manufacturer=mfr.id, model=yaml_data["model"], part_number=yaml_data.get("part_number", ""),
    )
    print(f"  [{'created' if created else 'exists ':7}] module type: {mt.model}")
    if created:
        for iface in yaml_data.get("interfaces", []):
            nb.dcim.interface_templates.create(
                module_type=mt.id, name=iface["name"], type=iface["type"], label=iface.get("label", ""),
            )
    return mt


# ---------------------------------------------------------------------------
# Port lookups
# ---------------------------------------------------------------------------

_PORT_ENDPOINTS = {
    "interface": lambda nb: nb.dcim.interfaces,
    "frontport": lambda nb: nb.dcim.front_ports,
    "rearport": lambda nb: nb.dcim.rear_ports,
}


def port(nb, device, kind, name):
    """A device's interface / front port / rear port by name. `device` is a record or a name."""
    dev = nb.dcim.devices.get(name=device) if isinstance(device, str) else device
    obj = _PORT_ENDPOINTS[kind](nb).get(device_id=dev.id, name=name)
    if obj is None:
        raise SystemExit(f"{kind} {name!r} not found on {dev.name!r}")
    return obj


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def route_km(waypoints):
    """Geodesic length (haversine) in km of a polyline of (name, lon, lat) points."""
    total = 0.0
    for (_, lon1, lat1), (_, lon2, lat2) in zip(waypoints, waypoints[1:]):
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp, dl = p2 - p1, math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        total += 6371.0088 * 2 * math.asin(math.sqrt(a))
    return total


def linestring(waypoints):
    return "LINESTRING (" + ", ".join(f"{lon} {lat}" for _, lon, lat in waypoints) + ")"


# ---------------------------------------------------------------------------
# netbox-secrets session key
# ---------------------------------------------------------------------------

SECRETS_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".secrets_userkey.pem")


def get_secrets_session_key(nb):
    """
    netbox-secrets encrypts with a per-user RSA keypair; writing a secret needs
    a session key obtained by submitting the PRIVATE key. The private key
    exists in full only once, at generation, so it is persisted in a
    gitignored file and reused. Losing that file makes stored secrets
    permanently undecryptable (expected plugin behaviour).
    """
    if os.path.exists(SECRETS_KEY_FILE):
        with open(SECRETS_KEY_FILE) as f:
            private_key = f.read()
    else:
        keypair = api("/api/plugins/secrets/generate-rsa-key-pair/")
        private_key = keypair["private_key"]
        user = nb.users.users.get(username="demo-loader")
        if nb.plugins.secrets.user_keys.get(user_id=user.id):
            raise SystemExit(
                f"A UserKey already exists for demo-loader but {SECRETS_KEY_FILE} is missing; "
                "delete the UserKey in NetBox or restore the key file."
            )
        nb.plugins.secrets.user_keys.create(public_key=keypair["public_key"])
        with open(SECRETS_KEY_FILE, "w") as f:
            f.write(private_key)
        os.chmod(SECRETS_KEY_FILE, 0o600)
        print("  (generated a new secrets keypair and saved the private key)")
    return api("/api/plugins/secrets/session-key/", method="post", json={"private_key": private_key})["session_key"]


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

def assign_contact(nb, contact, role, object_type, object_id):
    """Create the contact assignment if it doesn't exist. Returns "created"/"exists"."""
    existing = list(nb.tenancy.contact_assignments.filter(contact_id=contact.id, object_type=object_type, object_id=object_id))
    if existing:
        return "exists"
    nb.tenancy.contact_assignments.create(contact=contact.id, role=role.id, object_type=object_type, object_id=object_id)
    return "created"
