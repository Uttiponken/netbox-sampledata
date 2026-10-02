"""
Shared connection + idempotent-create helpers for the Nordfiber AB demo
dataset. Every phase script (01_organization.py, 02_infrastructure.py, ...)
imports this module rather than talking to pynetbox directly, so the
"check-then-create" pattern stays consistent and every script is safe to
re-run.
"""

import os
import sys
import urllib.request

import pynetbox
import yaml
from dotenv import load_dotenv

load_dotenv()

NETBOX_URL = os.environ.get("NETBOX_URL", "http://localhost:8000")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")

if not NETBOX_TOKEN:
    sys.exit(
        "NETBOX_TOKEN is not set. Copy .env.example to .env and fill in a "
        "NetBox API token (see README.md for how to create one)."
    )


def connect():
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
    try:
        nb.status()
    except pynetbox.RequestError as e:
        sys.exit(f"Could not reach or authenticate to {NETBOX_URL}: {e}")
    return nb


def call_plugin_action(path, method="get", json=None, extra_headers=None):
    """
    pynetbox doesn't auto-generate methods for custom DRF actions on a
    ViewSet (e.g. netbox-wdm's GET .../wdm-circuits/{id}/stitch/, or
    netbox-secrets' POST .../session-key/) — only plain CRUD. This issues
    the raw request. `path` is relative to NETBOX_URL, e.g.
    "/api/plugins/wdm/wdm-circuits/1/stitch/".
    """
    import requests

    headers = {"Authorization": f"Token {NETBOX_TOKEN}"}
    headers.update(extra_headers or {})
    resp = requests.request(
        method,
        f"{NETBOX_URL}{path}",
        headers=headers,
        json=json,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def get_or_create(endpoint, lookup, **fields):
    """
    Fetch an object matching `lookup` (usually {"slug": "..."} or
    {"name": "..."}); create it with `fields` (which should include the
    lookup keys) if it doesn't exist yet. Returns (object, created: bool).

    This is the whole idempotency strategy for every phase script: run a
    script twice and the second run should report everything as
    already-exists, not raise duplicate errors or create doubles.
    """
    existing = endpoint.get(**lookup)
    if existing:
        return existing, False
    obj = endpoint.create(**fields)
    return obj, True


def report(label, obj, created):
    marker = "created" if created else "exists "
    name = getattr(obj, "name", None) or getattr(obj, "display", obj)
    print(f"  [{marker}] {label}: {name} (id={obj.id})")


DEVICETYPE_LIBRARY_RAW = "https://raw.githubusercontent.com/netbox-community/devicetype-library/master"


def fetch_devicetype_yaml(path):
    """
    Fetch a real device-type definition straight from the NetBox community
    Device Type Library, e.g. fetch_devicetype_yaml("Juniper/MX204").

    This is deliberately NOT vendored/copied into this repo: it always
    pulls the current definition, same as a real user would via the
    library's own import tooling. Requires internet access when a phase
    script runs (a one-time cost per device type — the resulting NetBox
    objects persist in NetBox itself afterward).
    """
    url = f"{DEVICETYPE_LIBRARY_RAW}/device-types/{path}.yaml"
    with urllib.request.urlopen(url) as resp:
        return yaml.safe_load(resp.read())


def fetch_moduletype_yaml(path):
    """
    Same as fetch_devicetype_yaml, but for the library's separate
    module-types/ tree (pluggable line cards/modules, e.g. a DWDM
    muxponder module that installs into a chassis' module bay).
    """
    url = f"{DEVICETYPE_LIBRARY_RAW}/module-types/{path}.yaml"
    with urllib.request.urlopen(url) as resp:
        return yaml.safe_load(resp.read())


def create_device_type_from_yaml(nb, manufacturers, yaml_data):
    """
    Create a DeviceType plus its interface templates from a
    devicetype-library YAML dict (as returned by fetch_devicetype_yaml).
    Idempotent: if the DeviceType already exists, its templates are
    assumed to already exist too and are not re-checked individually.
    """
    mfr = manufacturers[yaml_data["manufacturer"]]
    dt, created = get_or_create(
        nb.dcim.device_types,
        {"slug": yaml_data["slug"]},
        manufacturer=mfr.id,
        model=yaml_data["model"],
        slug=yaml_data["slug"],
        part_number=yaml_data.get("part_number", ""),
        u_height=yaml_data.get("u_height", 1),
        is_full_depth=yaml_data.get("is_full_depth", True),
    )
    report("device type", dt, created)

    if created:
        interfaces = yaml_data.get("interfaces", [])
        for iface in interfaces:
            nb.dcim.interface_templates.create(
                device_type=dt.id,
                name=iface["name"],
                type=iface["type"],
                mgmt_only=iface.get("mgmt_only", False),
            )
        if interfaces:
            print(f"           + {len(interfaces)} interface templates")

        # Rear ports must exist before front ports, since front ports map
        # to them by ID. The devicetype-library YAML has two conventions:
        # a simple 1:1 same-name pairing with NO explicit mapping (its own
        # matching UI import infers this by position — the plain REST API
        # doesn't, so it's done here by list position), or an explicit
        # `port-mappings` list (used by real many-to-one devices, e.g. a
        # 40-channel muxponder where all 40 front ports fan into ONE rear
        # "Line" port at 40 different positions) which is followed exactly
        # when present.
        rear_ports = yaml_data.get("rear-ports", [])
        rear_port_ids_by_name = {}
        for rp in rear_ports:
            obj = nb.dcim.rear_port_templates.create(
                device_type=dt.id,
                name=rp["name"],
                type=rp["type"],
                positions=rp.get("positions", 1),
            )
            rear_port_ids_by_name[rp["name"]] = obj.id
        if rear_ports:
            print(f"           + {len(rear_ports)} rear port templates")

        # NetBox's mapping object has two DIFFERENT position fields, easy to
        # transpose (confirmed the hard way, via a live 400 error, before
        # this comment existed): `position` is the FRONT port's own
        # internal position (always 1 for a plain simplex LC connector —
        # only relevant for a multi-position front port like an MPO
        # breakout), while `rear_port_position` is which slot on the REAR
        # port this mapping occupies (1-40 for our 40-channel muxponder).
        # Leaving `rear_port_position` unset silently defaults it to 1,
        # which is why the second front port created this way collided
        # with the first: both ended up targeting rear-port slot 1.
        front_ports = yaml_data.get("front-ports", [])
        port_mappings = yaml_data.get("port-mappings")
        rear_port_ids = list(rear_port_ids_by_name.values())
        for i, fp in enumerate(front_ports):
            if port_mappings:
                mapping = next(m for m in port_mappings if m["front_port"] == fp["name"])
                rear_ports_field = [{
                    "rear_port": rear_port_ids_by_name[mapping["rear_port"]],
                    "position": mapping["front_port_position"],
                    "rear_port_position": mapping["rear_port_position"],
                }]
            else:
                rear_ports_field = [{"rear_port": rear_port_ids[i], "position": 1}]
            nb.dcim.front_port_templates.create(
                device_type=dt.id,
                name=fp["name"],
                type=fp["type"],
                rear_ports=rear_ports_field,
            )
        if front_ports:
            print(f"           + {len(front_ports)} front port templates")

        module_bays = yaml_data.get("module-bays", [])
        for mb in module_bays:
            nb.dcim.module_bay_templates.create(
                device_type=dt.id,
                name=mb["name"],
                position=mb.get("position", ""),
                description=mb.get("description", ""),
            )
        if module_bays:
            print(f"           + {len(module_bays)} module bay templates")

    return dt


def create_module_type_from_yaml(nb, manufacturers, yaml_data):
    """
    Create a ModuleType plus its interface templates from a
    devicetype-library module-types YAML dict. Unlike DeviceType, ModuleType
    has no slug field — it's looked up by (manufacturer, model) instead.

    Interface template names may contain a literal "{module}" placeholder
    (e.g. "Client/{module}/1") — NetBox substitutes this with the hosting
    ModuleBay's `position` value when a real Module is installed into a bay,
    so the templates are created exactly as given, unresolved.
    """
    mfr = manufacturers[yaml_data["manufacturer"]]
    mt, created = get_or_create(
        nb.dcim.module_types,
        {"manufacturer_id": mfr.id, "model": yaml_data["model"]},
        manufacturer=mfr.id,
        model=yaml_data["model"],
        part_number=yaml_data.get("part_number", ""),
    )
    report("module type", mt, created)

    if created:
        interfaces = yaml_data.get("interfaces", [])
        for iface in interfaces:
            nb.dcim.interface_templates.create(
                module_type=mt.id,
                name=iface["name"],
                type=iface["type"],
                label=iface.get("label", ""),
            )
        if interfaces:
            print(f"           + {len(interfaces)} interface templates")

    return mt


def get_module_bay(nb, device, name):
    bay = nb.dcim.module_bays.get(device_id=device.id, name=name)
    if bay is None:
        raise SystemExit(f"Module bay {name!r} not found on device {device.name!r}")
    return bay


def install_module_if_needed(nb, device, bay, module_type, **fields):
    existing = nb.dcim.modules.get(device_id=device.id, module_bay_id=bay.id)
    if existing:
        report("module", existing, False)
        return existing, False
    obj = nb.dcim.modules.create(
        device=device.id,
        module_bay=bay.id,
        module_type=module_type.id,
        status="active",
        **fields,
    )
    report("module", obj, True)
    return obj, True


def get_interface(nb, device, name):
    iface = nb.dcim.interfaces.get(device_id=device.id, name=name)
    if iface is None:
        raise SystemExit(f"Interface {name!r} not found on device {device.name!r}")
    return iface


def get_rear_port(nb, device, name):
    port = nb.dcim.rear_ports.get(device_id=device.id, name=name)
    if port is None:
        raise SystemExit(f"Rear port {name!r} not found on device {device.name!r}")
    return port


def get_front_port(nb, device, name):
    port = nb.dcim.front_ports.get(device_id=device.id, name=name)
    if port is None:
        raise SystemExit(f"Front port {name!r} not found on device {device.name!r}")
    return port


# Cables in this dataset connect either two device interfaces (Phase 3) or
# a device interface to a circuit termination (Phase 4). Both endpoint
# kinds expose `.cable` and can be refetched from their own endpoint; this
# table is how create_cable_if_needed stays generic across both.
_CABLE_ENDPOINTS = {
    "dcim.interface": lambda nb: nb.dcim.interfaces,
    "circuits.circuittermination": lambda nb: nb.circuits.circuit_terminations,
    "dcim.rearport": lambda nb: nb.dcim.rear_ports,
    "dcim.frontport": lambda nb: nb.dcim.front_ports,
}


def _describe_termination(obj, object_type):
    if object_type in ("dcim.interface", "dcim.rearport", "dcim.frontport"):
        return f"{obj.device.name}:{obj.name}"
    if object_type == "circuits.circuittermination":
        return f"circuit {obj.circuit.cid} ({obj.term_side}-side)"
    return str(obj)


def _verify_cable_far_end(nb, a_obj, a_type, cable_id, b_obj, b_type, endpoints):
    cable = nb.dcim.cables.get(id=cable_id)
    far_terminations = list(cable.a_terminations) + list(cable.b_terminations)
    if any(t.object_type == b_type and t.object.id == b_obj.id for t in far_terminations):
        return
    raise SystemExit(
        f"{_describe_termination(a_obj, a_type)} is already cabled (cable id={cable.id}, "
        f"label={cable.label!r}) to something OTHER than what this call expects "
        f"({endpoints}). This interface was likely re-cabled by a LATER phase script "
        "(e.g. a retrofit) since this cable was first created. Re-running an earlier "
        "phase script after a later retrofitting phase has already run is not "
        "supported — run phases 01-13 in order from a clean database instead."
    )


def create_cable_if_needed(nb, a_obj, a_type, b_obj, b_type, **fields):
    """
    Idempotency for cables works differently than get_or_create: there's no
    natural slug/name to look up, so instead check whether EITHER endpoint
    already has a cable attached. An interface or circuit termination can
    only ever be one end of one cable, so this is a reliable existence
    check regardless of what kind of object each end is.

    Unlike get_or_create, an existing cable's fields (label, comments,
    status, ...) ARE reconciled against `fields` and updated if they've
    drifted — cable metadata (especially the label) is exactly the kind of
    thing expected to change after the fact as a cable plan gets refined,
    so "create once and never touch again" isn't the right idempotency
    model here the way it is for identity-bearing objects like sites.

    IMPORTANT: `a_obj.cable` existing is NOT enough to assume it's THIS
    cable — a later retrofit phase (e.g. Phase 11) may have moved a_obj
    onto a completely different cable than the one an earlier phase (e.g.
    Phase 3) originally created for it. Blindly reconciling fields onto
    whatever cable is there would silently mislabel an unrelated cable,
    and then still fail below with a confusing "duplicate termination"
    error once b_obj (already cabled elsewhere by the retrofit) is
    reached. Caught the hard way: re-running 03_connections.py against a
    database that Phase 11 had already retrofitted overwrote
    sto-patch-01<->sto-sw-01's label/tenant with Polaris's server-cable
    metadata before crashing. Fixed by verifying the existing cable's far
    end actually IS b_obj before treating it as a match.
    """
    a_obj = _CABLE_ENDPOINTS[a_type](nb).get(id=a_obj.id)  # refetch: .cable may be stale
    endpoints = f"{_describe_termination(a_obj, a_type)} <-> {_describe_termination(b_obj, b_type)}"

    if a_obj.cable:
        _verify_cable_far_end(nb, a_obj, a_type, a_obj.cable.id, b_obj, b_type, endpoints)
        cable = nb.dcim.cables.get(id=a_obj.cable.id)
        changed = []
        for key, desired in fields.items():
            current = getattr(cable, key)
            # Unwrap either a choice field (has .value, e.g. status) or a
            # nested-object field (has .id, e.g. tenant) down to the plain
            # value `desired` is expressed in — comparing a Record to a
            # plain int/str would never be equal and falsely report
            # "[updated]" on every single run.
            if hasattr(current, "value"):
                current_value = current.value
            elif hasattr(current, "id"):
                current_value = current.id
            else:
                current_value = current
            if current_value != desired:
                setattr(cable, key, desired)
                changed.append(key)
        if changed:
            cable.save()
            print(f"  [updated] cable: {endpoints} (id={cable.id}) — {', '.join(changed)}")
        else:
            print(f"  [exists ] cable: {endpoints} (id={cable.id})")
        return cable, False

    cable = nb.dcim.cables.create(
        a_terminations=[{"object_type": a_type, "object_id": a_obj.id}],
        b_terminations=[{"object_type": b_type, "object_id": b_obj.id}],
        **fields,
    )
    print(f"  [created] cable: {endpoints} (id={cable.id})")
    return cable, True


def disconnect_direct_cable_if_present(nb, a_obj, a_type, b_obj, b_type):
    """
    Delete the cable directly connecting a_obj <-> b_obj, if one exists.
    Used when retrofitting a physical path — e.g. inserting a
    media-converter shelf between two endpoints that used to be cabled
    directly to each other — since create_cable_if_needed only ever adds
    or reconciles a cable's fields, it never re-terminates one, so the old
    direct cable has to be removed before the new intermediate cables can
    be created (an interface/front-port can only ever be one end of one
    cable).

    Checks BOTH ends resolve to the SAME cable before deleting, so this is
    safe to call on every run: once the retrofit has happened, a_obj and
    b_obj are on two DIFFERENT cables (each now goes to the shelf instead
    of to each other) and nothing is deleted.
    """
    a_obj = _CABLE_ENDPOINTS[a_type](nb).get(id=a_obj.id)  # refetch: .cable may be stale
    b_obj = _CABLE_ENDPOINTS[b_type](nb).get(id=b_obj.id)
    a_cable_id = a_obj.cable.id if a_obj.cable else None
    b_cable_id = b_obj.cable.id if b_obj.cable else None
    if a_cable_id is None or a_cable_id != b_cable_id:
        return False
    nb.dcim.cables.get(id=a_cable_id).delete()
    print(
        f"  [deleted] old direct cable id={a_cable_id} "
        f"({_describe_termination(a_obj, a_type)} <-> {_describe_termination(b_obj, b_type)})"
    )
    return True


def create_fiber_cable_if_needed(nb, dcim_cable, fiber_cable_type, **fields):
    """
    netbox-fms's FiberCable "decorates" an existing dcim.Cable with
    fiber-specific metadata — it doesn't carry its own endpoints. Creating
    one auto-instantiates BufferTubes and FiberStrands from the
    FiberCableType's templates (verified empirically before writing this
    dataset: a 4-strand test cable type produced exactly 1 buffer tube +
    4 correctly EIA/598-colored strands with no manual strand creation
    needed). Idempotency is by the underlying dcim.Cable — a cable can only
    ever back one FiberCable.
    """
    existing = nb.plugins.fms.fiber_cables.get(cable_id=dcim_cable.id)
    if existing:
        report("fiber cable", existing, False)
        return existing, False

    fc = nb.plugins.fms.fiber_cables.create(
        cable=dcim_cable.id,
        fiber_cable_type=fiber_cable_type.id,
        **fields,
    )
    report("fiber cable", fc, True)
    return fc, True


SECRETS_KEY_FILE = os.path.join(os.path.dirname(__file__), ".secrets_userkey.pem")


def get_secrets_session_key(nb):
    """
    netbox-secrets encrypts every secret with the site's master key, which
    is itself stored once per user, encrypted with THAT user's RSA public
    key. Writing a secret needs a "session key" — obtained by submitting
    your PRIVATE key to unlock your copy of the master key for this
    session — passed as the X-Session-Key header on every secrets/ write.

    The private key exists only once, in memory, at the moment it's
    generated — there is no "fetch it again later" the way there is for
    most NetBox objects (this mirrors the API token lesson from Phase 1,
    but for a plugin that encrypts real data, not just an auth credential).
    So it's persisted locally, in SECRETS_KEY_FILE (gitignored, analogous
    to .env) — generated once, reused on every subsequent run. If that file
    is ever lost, the secrets already stored under the old key become
    unrecoverable; this is expected netbox-secrets behavior, not a bug in
    this script.
    """
    if os.path.exists(SECRETS_KEY_FILE):
        with open(SECRETS_KEY_FILE) as f:
            private_key = f.read()
        print(f"  (reusing existing keypair from {SECRETS_KEY_FILE})")
    else:
        keypair = call_plugin_action("/api/plugins/secrets/generate-rsa-key-pair/")
        private_key = keypair["private_key"]
        existing_userkey = nb.plugins.secrets.user_keys.get(user_id=nb.users.users.get(username="demo-loader").id)
        if existing_userkey:
            raise SystemExit(
                f"A UserKey already exists for demo-loader but {SECRETS_KEY_FILE} is missing — "
                "the matching private key was never saved and cannot be recovered. Delete the "
                "existing UserKey via the NetBox UI/API before re-running, or restore the file."
            )
        nb.plugins.secrets.user_keys.create(public_key=keypair["public_key"])
        with open(SECRETS_KEY_FILE, "w") as f:
            f.write(private_key)
        os.chmod(SECRETS_KEY_FILE, 0o600)
        print(f"  (generated new keypair, activated UserKey, saved private key to {SECRETS_KEY_FILE})")

    session = call_plugin_action("/api/plugins/secrets/session-key/", method="post", json={"private_key": private_key})
    return session["session_key"]
