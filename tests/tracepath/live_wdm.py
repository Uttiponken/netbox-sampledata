"""
Real WDM circuits (and the Polaris colo trace, to show the green trunks) printed into /tmp/tp-out in the container.
Run inside the NetBox container:

  tests/tracepath/run.sh        (runs all of them; or pipe this file into `manage.py shell` in the container)
"""

from django.apps import apps as _apps
from dcim.models import Device as _Device

_missing = [a for a in ["netbox_tracepath_plugin", "netbox_wdm"] if not _apps.is_installed(a)]
if _missing:
    print("[skipped] this test needs " + ", ".join(_missing) + ", which is not installed")
    raise SystemExit(0)
if not _Device.objects.filter(name="stn-rtr-01").exists():
    print("[skipped] the Nordfiber sample data is not loaded (no device stn-rtr-01)")
    raise SystemExit(0)

import os

from django.contrib.auth import get_user_model
from django.utils.text import slugify

from dcim.models import Interface
from netbox_wdm.models import WdmCircuit
from netbox_tracepath_plugin.collect import Collector, paths_through
from netbox_tracepath_plugin.integrations import wdm
from netbox_tracepath_plugin.layout import LayoutSpec, render
from netbox_tracepath_plugin.models import PrintProfile
from netbox_tracepath_plugin.selection import apply_selection

OUT = "/tmp/tp-out"
os.makedirs(OUT, exist_ok=True)
user = get_user_model().objects.get(username="demo-loader")
collector = Collector(user)
profiles = list(PrintProfile.objects.filter(name__in=["Full information", "Field technician"]))

jobs = []
for name, label in (("Fjord", "fjord"), ("Baltic Retail Group Backup - Segment 1", "brg-segment-1")):
    circuit = WdmCircuit.objects.get(name__startswith=name)
    entry = wdm.circuit_paths(circuit)[0]
    doc = wdm.trim_doc(collector.chain_doc([collector.part(entry["path"])]), entry, circuit)
    jobs.append((f"wdm-circuit-{label}", doc))
iface = Interface.objects.get(device__name="polaris-stn-sw-01", name="Ethernet49")
jobs.append(("colo-tenant", collector.trace_doc(paths_through(iface)[0], origin_label=str(iface))))

for label, doc in jobs:
    for profile in profiles:
        out = apply_selection(doc, profile.keys, layout_name=profile.name)
        pdf, rep = render(out, LayoutSpec(paper="A4", orientation="landscape"))
        name = f"{slugify(profile.name)}-nordfiber-{label}-a4-landscape.pdf"
        open(os.path.join(OUT, name), "wb").write(pdf)
        print(f"{name:75} pages={rep.pages} fits={rep.fits}")
