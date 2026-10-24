"""
Renders real traces from the running NetBox into /tmp/tp-out/live-*.pdf. Run inside the NetBox container:

  tests/tracepath/run.sh        (runs all of them; or pipe this file into `manage.py shell` in the container)
"""

from django.apps import apps as _apps
from dcim.models import Device as _Device

_missing = [a for a in ["netbox_tracepath_plugin"] if not _apps.is_installed(a)]
if _missing:
    print("[skipped] this test needs " + ", ".join(_missing) + ", which is not installed")
    raise SystemExit(0)
if not _Device.objects.filter(name="stn-rtr-01").exists():
    print("[skipped] the Nordfiber sample data is not loaded (no device stn-rtr-01)")
    raise SystemExit(0)

import os

from django.contrib.auth import get_user_model

from circuits.models import CircuitTermination
from dcim.models import FrontPort, Interface, RearPort
from netbox_tracepath_plugin.collect import Collector, describe_path, paths_through
from netbox_tracepath_plugin.layout import LayoutSpec, render

OUT = "/tmp/tp-out"
os.makedirs(OUT, exist_ok=True)
user = get_user_model().objects.get(username="demo-loader")

CASES = {
    "colo-tenant": lambda: Interface.objects.get(device__name="polaris-stn-sw-01", name="Ethernet49"),
    "circuit-primary": lambda: Interface.objects.get(device__name="mma-rtr-01", name="et-0/0/0"),
    "internet-handoff": lambda: Interface.objects.get(device__name="got-rtr-01", name="xe-0/1/1"),
    "patch-front-port": lambda: FrontPort.objects.get(device__name="stn-patch-mmr-01", name="Port 1"),
    "patch-rear-trunk": lambda: RearPort.objects.get(device__name="stn-patch-mmr-01", name="Trunk"),
    "circuit-termination": lambda: CircuitTermination.objects.get(circuit__cid="NF-BRG-0001", term_side="Z"),
    "hel-nsn-wdm": lambda: Interface.objects.get(device__name="hel-rtr-01", name="et-0/0/2"),
    "fjord-client": lambda: Interface.objects.get(device__name="stn-sw-01", name="Ethernet49/1"),
}

for name, get in CASES.items():
    obj = get()
    paths = paths_through(obj)
    if not paths:
        print(f"{name:22} {obj}: no path")
        continue
    for i, path in enumerate(paths):
        doc = Collector(user).trace_doc(path, origin_label=str(obj))
        pdf, rep = render(doc, LayoutSpec(paper="A4", orientation="landscape"))
        fname = f"live-{name}{'' if len(paths) == 1 else f'-path{i + 1}'}.pdf"
        open(os.path.join(OUT, fname), "wb").write(pdf)
        print(f"{fname:42} blocks={len(doc.blocks):2} cables={sum(len(l.cables) for l in doc.links):2} pages={rep.pages} "
              f"cols={rep.columns} fits={rep.fits}  {doc.title}")
        for n in doc.notes:
            print("      note:", n)
