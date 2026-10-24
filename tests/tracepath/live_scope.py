"""
Scoped prints of real traces into /tmp/tp-out in the container. Run inside the NetBox container:

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
from django.utils.text import slugify

from dcim.models import Interface
from netbox_tracepath_plugin.collect import Collector, paths_through
from netbox_tracepath_plugin.extend import Chain
from netbox_tracepath_plugin.layout import LayoutSpec, render
from netbox_tracepath_plugin.models import PrintProfile
from netbox_tracepath_plugin.scope import apply_scope, scopes_of
from netbox_tracepath_plugin.selection import apply_selection

OUT = "/tmp/tp-out"
os.makedirs(OUT, exist_ok=True)
user = get_user_model().objects.get(username="demo-loader")
collector = Collector(user)
profiles = list(PrintProfile.objects.filter(name__in=["Full information", "Field technician"]))


def pick(doc, text):
    return next(s["value"] for s in scopes_of(doc) if s["label"].endswith(text))


sth = Interface.objects.get(device__name="stn-rtr-01", name="et-0/0/2")
nsn = collector.trace_doc(paths_through(sth)[0], origin_label=str(sth))
pid = lambda dev, name: Interface.objects.get(device__name=dev, name=name).pk
first = paths_through(Interface.objects.get(device__name="baltic-retail-stw-srv-01", name="Gig-E 1"))[0]
chain = Chain(user, first, after=[pid(d, n) for d, n in [
    ("baltic-retail-stw-sw-01", "Ethernet49"), ("stw-sw-01", "Ethernet1"), ("stw-rtr-01", "et-0/0/0"),
    ("mma-rtr-01", "xe-0/1/0"), ("mma-sw-01", "Ethernet2"), ("baltic-retail-mma-sw-01", "Ethernet1")]])
brg = collector.chain_doc(chain.parts(collector), origin_label="server to server")
print("scopes:", [x["label"] for x in scopes_of(brg)])

jobs = [("stn-hel-nsn-rack-stn-mm-01", nsn, pick(nsn, "STN-MM-01")),
        ("stn-hel-nsn-site-helsinki", nsn, "site:Nordfiber Helsinki DC"),
        ("stn-hel-nsn-site-stockholm", nsn, "site:Nordfiber Stockholm North DC"),
        ("baltic-retail-site-malmo", brg, next(s["value"] for s in scopes_of(brg) if "Malm" in s["label"] and s["kind"] == "site")),
        ("baltic-retail-meetme-room-stockholm", brg, pick(brg, "Stockholm West DC › MeetMe Room"))]
for label, doc, scope in jobs:
    scoped = apply_scope(doc, scope)
    for profile in profiles:
        out = apply_selection(scoped, profile.keys, layout_name=profile.name)
        pdf, rep = render(out, LayoutSpec(paper="A4", orientation="landscape"))
        name = f"{slugify(profile.name)}-nordfiber-scope-{label}-a4-landscape.pdf"
        open(os.path.join(OUT, name), "wb").write(pdf)
        print(f"{name:85} pages={rep.pages} segments={len(out.segments)} fits={rep.fits}")
