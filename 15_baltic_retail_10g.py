#!/usr/bin/env python3
"""
Phase 15: Baltic Retail Group capacity upgrade, 1 Gbps -> 10 Gbps
(added post-hoc, 2026-09-30).

Upgrades both NF-BRG-0001 (primary) and NF-BRG-0002 (backup) to keep the
backup path fully able to cover the primary. No physical rewiring needed:
both circuits already terminate on et-0/0/0 and et-0/0/1 (or their WDM
client-shelf equivalents) on the Juniper MX204s, which are 100GE QSFP28
ports regardless of the commit rate configured on them — confirmed live
before starting this phase.

get_or_create() never updates an existing object's fields (same gotcha as
Phase 12), so this phase explicitly fetches and patches both the Circuit's
commit_rate and each of its CircuitTerminations' port_speed — the two
fields Phase 4/8 set independently at creation time.

Depends on Phase 4 (NF-BRG-0001) and Phase 8 (NF-BRG-0002). Safe to
re-run.
"""

from common import connect
from config import BACKUP_CIRCUIT, CIRCUITS

NF_BRG_0001 = next(c for c in CIRCUITS if c["cid"] == "NF-BRG-0001")


def upgrade_circuit(nb, cid, commit_rate):
    circuit = nb.circuits.circuits.get(cid=cid)
    if circuit.commit_rate != commit_rate:
        circuit.commit_rate = commit_rate
        circuit.save()
        print(f"  [updated] circuit {cid}: commit_rate -> {commit_rate} Kbps")
    else:
        print(f"  [exists ] circuit {cid}: commit_rate already {commit_rate} Kbps")

    for term in nb.circuits.circuit_terminations.filter(circuit_id=circuit.id):
        if term.port_speed != commit_rate:
            term.port_speed = commit_rate
            term.save()
            print(f"  [updated] {cid} termination {term.term_side}: port_speed -> {commit_rate} Kbps")
        else:
            print(f"  [exists ] {cid} termination {term.term_side}: port_speed already {commit_rate} Kbps")


def run(nb):
    print("== NF-BRG-0001 (primary) ==")
    upgrade_circuit(nb, "NF-BRG-0001", NF_BRG_0001["commit_rate"])

    print("== NF-BRG-0002 (backup) ==")
    upgrade_circuit(nb, "NF-BRG-0002", BACKUP_CIRCUIT["commit_rate"])


if __name__ == "__main__":
    nb = connect()
    print(f"Connected to {nb.base_url}\n")
    run(nb)
    print("\nPhase 15 (Baltic Retail Group 10 Gbps upgrade) complete.")
