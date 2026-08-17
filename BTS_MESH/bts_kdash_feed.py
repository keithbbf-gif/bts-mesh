#!/usr/bin/env python3
r"""bts_kdash_feed.py — ONE REGISTRY -> ONE DASHBOARD.  2026-07-31

    Keith: "Full integrate KDash and BFast so we can get an accurate view of KMesh."

THE PROBLEM THIS CLOSES
-----------------------
`bench.json` kept its own hardcoded node list — crossref, itc, gem, vertex, sgh. Five entries, and
the mesh has SIX NODES and TEN RAILS. **CoW, GW and CoPG were invisible**, and so was the MCP rail
that every node uses for every file operation. That list was a SECOND COPY of a registry, which is
this project's oldest and most expensive defect: `00_TOOLS_INDEX.md` vs `TOOLS_REGISTRY.json` drifted
in both directions and shipped `bts_identity.py` invisible for weeks.

⇒ **`ROLD\rails.toml` is the registry. This file RENDERS it. KDash never keeps its own list again.**

WHY A DERIVED FILE IS ALLOWED HERE, WHEN A GENERATED MARKDOWN TWIN WAS NOT
--------------------------------------------------------------------------
GEM's argument against generated docs was: *someone will edit the generated file.* Nobody hand-edits
`dash.json` — it is machine-to-machine and rewritten on every run. The failure mode does not exist.
A generated artefact is safe exactly when no human has a reason to touch it.

THE TWO RULES THIS FEED ENFORCES (they are the point, not decoration)
---------------------------------------------------------------------
1. **UNMEASURED RENDERS AS "UNMEASURED", NEVER AS A NUMBER.** No zero, no last-known-good, no
   plausible default. Four CLI/MCP rails have never been timed and the panel must SAY so.
2. **STALE RENDERS RED.** A measurement older than its cadence is not evidence. `dash.json` refreshes
   only when KDash launches, so every number on that screen is a snapshot of the last time someone
   looked — and on 2026-07-30 two scheduled tasks reported `Last Result: 0` while measuring nothing.

NEGATIVE CONTROL — a feed that has never mislabelled anything has not been tested:
    python bts_kdash_feed.py --selftest
asserts a rail with no latency renders UNMEASURED (not 0), and a measurement older than its cadence
renders RED (not green).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys

try:
    import tomllib                      # stdlib >= 3.11 (Windows runs 3.14)
except ModuleNotFoundError:             # sandbox is 3.10
    import tomli as tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
RAILS = os.path.join(os.path.dirname(HERE), "ROLD", "rails.toml")
DASH = os.path.join(HERE, "dash.json")

STALE_DAYS_DEFAULT = 7.0                # a rail unmeasured for a week is not a live reading


def _age_days(d) -> float | None:
    if d is None:
        return None
    if isinstance(d, _dt.datetime):
        d = d.date()
    if not isinstance(d, _dt.date):
        try:
            d = _dt.date.fromisoformat(str(d)[:10])
        except Exception:               # noqa: BLE001
            return None
    return (_dt.date.today() - d).days


def _status(measured, cadence_h=None, unmeasured=False) -> str:
    """GREEN | AMBER | RED | UNMEASURED — and UNMEASURED is never silently a number."""
    if unmeasured:
        return "UNMEASURED"
    age = _age_days(measured)
    if age is None:
        return "UNMEASURED"
    limit = (cadence_h / 24.0) if cadence_h else STALE_DAYS_DEFAULT
    if age <= limit:
        return "GREEN"
    if age <= limit * 3:
        return "AMBER"
    return "RED"


def build(rails_path: str = RAILS) -> dict:
    with open(rails_path, "rb") as fh:
        r = tomllib.load(fh)

    # 2026-07-31: a node with kind = "observation-only" is REGISTERED but NOT
    # COUNTED. CoP365 was demoted by unanimous verdict of four nodes (KMESH
    # blueprint) — it has no MCP client and has never been invoked, so counting
    # it inflated the node count by 20%. The demotion was first written as PROSE
    # in rails.toml's `state` and `owed` fields, and this renderer went on
    # reporting "NODES (6) · CoP365 GREEN" exactly as before. That is tonight's
    # own lesson repeating (S-97/98/99: prose mistaken for a control) — so the
    # rule is enforced HERE, on an explicit `kind`, where the count is computed.
    nodes, observers = [], []
    for n in r.get("node", []):
        entry = {
            "id": n["id"], "name": n.get("name"), "kind": n.get("kind"),
            "state": n.get("state"), "status": _status(n.get("measured")),
            "age_days": _age_days(n.get("measured")),
            "owed": n.get("owed"),
            "on_kdash": "NOT ON KDASH" not in (n.get("owed") or "").upper(),
        }
        if (n.get("kind") or "").strip().lower() == "observation-only":
            entry["status"] = "OBSERVER"
            observers.append(entry)
        else:
            nodes.append(entry)

    rails = []
    for x in r.get("rail", []):
        lat = x.get("latency_ms")
        rails.append({
            "name": x["name"], "kind": x["kind"], "what": x.get("what"),
            # 🔴 never coerce a missing latency to 0 — that is the lie this feed exists to prevent
            "latency_ms": lat if lat is not None else None,
            "latency_label": (f"{lat:.0f} ms" if lat is not None else "UNMEASURED"),
            "lands_on": x.get("lands_on"),
            "write_mbs": x.get("write_mbs"),
            # 🔴 TWO DEFECTS ON THIS ONE LINE, both found 2026-08-11.
            #
            # 1. THE LABEL SAID WHAT IT WAS NOT. `107 MB/s` appeared against ELEVEN rail
            #    rows in dash.json and read as "this rail runs at 107 MB/s". It never
            #    meant that. It is the WRITE SPEED OF THE SURFACE THE RAIL'S RETURNS LAND
            #    ON - V: Ai - and it is the same figure for every rail that lands there,
            #    which is exactly why it looked like a propagated constant. The number was
            #    right and the column was lying. Measured one thing, displayed against
            #    another. Now the label names the surface, so it cannot be read as the
            #    rail's own throughput.
            #
            # 2. TRUTHINESS ON A REAL ZERO - the bug this file's own `_pct` comment
            #    forbids, ten lines below, in a function written to fix it elsewhere.
            #    `if x.get("write_mbs")` renders 0.0 as "—", i.e. UNMEASURED. The `itc`
            #    rail carries write_mbs = 0.0 and has been displaying as unmeasured ever
            #    since. A rule fixed in one function and not in its neighbour is a rule
            #    scoped to the instance, which is the same shape as "NO EMOJI IN A .bat"
            #    never reaching the Python tools' stdout (S-134).
            "write_label": (
                (f"{x['write_mbs']:.0f} MB/s on {x.get('lands_on') or 'an unnamed surface'}"
                 f" (surface write speed, NOT rail throughput)")
                if x.get("write_mbs") is not None else "UNMEASURED"),
            "cost": x.get("cost"),
            "status": _status(x.get("measured"), unmeasured=(lat is None)),
            "owed": x.get("owed"),
        })

    def _pct(s):
        # 🔴 `is not None`, NEVER truthiness. A surface that is genuinely 0.0% full is a MEASUREMENT;
        # `if s.get("used_gb")` treats 0.0 as absent and renders it "—", i.e. UNKNOWN. Caught the day
        # a 15 GB Drive holding 550 KB was added and rendered as unmeasured. This feed exists to stop
        # a missing number looking like a real one — the inverse error is just as wrong.
        u, q = s.get("used_gb"), s.get("quota_gb")
        return round(100 * u / q, 1) if (u is not None and q) else None

    def _surface_status(s):
        # 🔴 A FAULTED SURFACE IS NOT GREEN BECAUSE SOMEONE MEASURED IT RECENTLY. _status() answers
        # "is this reading fresh?" — never "is this thing working?". G: was rendering GREEN while
        # powered off with a failed USB bridge, because the fault was measured TODAY. Freshness of a
        # measurement and health of the subject are different questions (S-96).
        st = (s.get("state") or "").upper()
        if any(w in st for w in ("FAULTED", "DOWN", "DEAD", "OFFLINE", "FAILED")):
            return "RED"
        if any(w in st for w in ("CANDIDATE", "NOT IN USE", "NOT MOUNTED", "UNTRIED")):
            return "CANDIDATE"
        if "CANDIDATE" in (s.get("job") or "").upper():
            return "CANDIDATE"
        return _status(s.get("measured"))

    surfaces = [{
        "name": s["name"], "job": s.get("job"), "reach": s.get("node_reach"),
        # Drive letters / URLs are configured path values, never surface identity.
        "configured_path": s.get("path"),
        "write_mbs": s.get("write_mbs"), "read_mbs": s.get("read_mbs"),
        "used_gb": s.get("used_gb"), "quota_gb": s.get("quota_gb"),
        "pct": _pct(s),
        "pct_label": ("—" if _pct(s) is None else f"{_pct(s)}%"),
        "state": s.get("state"),
        "status": _surface_status(s), "age_days": _age_days(s.get("measured")),
        "owed": s.get("owed"),
    } for s in r.get("surface", [])]

    monitors = [{
        "name": m["name"], "scheduler": m.get("scheduler"), "cadence_h": m.get("cadence_h"),
        "writes": m.get("writes"), "state": m.get("state"),
        "status": _status(m.get("measured"), m.get("cadence_h")),
        "age_days": _age_days(m.get("measured")), "owed": m.get("owed"),
        # the finding that started PLM-13: a task can report success and measure nothing
        "measures_nothing": "NOTHING" in (str(m.get("writes", "")) + str(m.get("state", ""))).upper(),
    } for m in r.get("monitor", [])]

    # 🔴 A SETTLED CLOCK MUST NOT RENDER AS A LIVE COUNTDOWN. Caught at TidyUP 2026-07-31: the GCP
    # soft-delete was measured as a NON-EVENT and the panel still said "14 days out", because this
    # feed read `when` and ignored `state`. A dashboard that shows a resolved item as pending trains
    # the reader to discount it — the same way the two `Last Result: 0` tasks did.
    clocks = []
    for c in r.get("clock", []):
        # 🔴 `settled` IS AN EXPLICIT BOOLEAN FIELD. Do not infer it from the prose.
        # The first version tested `"SETTLED" in state.upper()`, and within the hour the state became
        # "🔴 NOT SETTLED — THE CHECK QUERIED THE WRONG ACCOUNT" — which CONTAINS the substring. The
        # panel cheerfully rendered a withdrawn finding as ✅ SETTLED. Sniffing a substring out of a
        # human sentence is not a flag; it is a guess that happens to be right until someone writes
        # the negation. Same family as the root-shadowing guard: parse structure, never prose.
        settled = bool(c.get("settled", False))
        clocks.append({
            "name": c["name"], "when": str(c.get("when")), "note": c.get("note"),
            "state": c.get("state"), "settled": settled,
            "days_out": None if settled else (_age_days(c.get("when")) and -_age_days(c.get("when"))),
            "status": "SETTLED" if settled else "PENDING",
        })

    # things measured to be WRONG that no rail will report, because the service still answers
    discrepancies = [{"name": d["name"], "detail": d.get("detail"), "but": d.get("but"),
                      "owed": d.get("owed"), "found": str(d.get("found"))}
                     for d in r.get("discrepancy", [])]

    bfast = r.get("bfast", {})
    return {
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "source": rails_path,
        "source_rule": "rails.toml is THE registry. KDash renders it and never keeps its own list.",
        "bfast": {"home": bfast.get("home"), "entry": bfast.get("entry"),
                  "config": bfast.get("config"), "tools": bfast.get("tools"),
                  "roots": [{"name": t["name"], "path": t["path"], "role": t.get("role")}
                            for t in bfast.get("root", [])]},
        "nodes": nodes, "observers": observers, "rails": rails, "surfaces": surfaces,
        "monitors": monitors, "clocks": clocks, "discrepancies": discrepancies,
        "counts": {
            "nodes": len(nodes), "observers": len(observers), "rails": len(rails),
            "rails_unmeasured": sum(1 for x in rails if x["latency_ms"] is None),
            "nodes_missing_from_kdash": sum(1 for n in nodes if not n["on_kdash"]),
            "monitors_measuring_nothing": sum(1 for m in monitors if m["measures_nothing"]),
            "clocks_pending": sum(1 for k in clocks if not k["settled"]),
            "discrepancies_open": len(discrepancies),
        },
    }


def write(km: dict, dash: str = DASH) -> None:
    """Merge under a 'kmesh' key. Never clobber the rest of dash.json."""
    try:
        with open(dash, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:                    # noqa: BLE001
        d = {}
    d["kmesh"] = km
    with open(dash, "w", encoding="utf-8", newline="") as fh:
        json.dump(d, fh, indent=2)


def report(km: dict) -> None:
    c = km["counts"]
    print("=" * 78)
    print(f"  KMesh — rendered from {os.path.basename(km['source'])} at {km['generated']}")
    print("=" * 78)
    print(f"  NODES ({c['nodes']})")
    for n in km["nodes"]:
        print(f"    {n['id']:<7} {str(n['kind']):<8} {n['status']:<10} "
              f"{'' if n['on_kdash'] else '🔴 NOT ON KDASH'}")
    if km.get("observers"):
        print(f"\n  OBSERVATION-ONLY ({c['observers']}) — registered, NOT counted as nodes")
        for n in km["observers"]:
            print(f"    {n['id']:<7} {str(n['kind']):<18} {n['status']:<10}")
    print(f"\n  RAIL LATENCY PANEL ({c['rails']} rails, {c['rails_unmeasured']} unmeasured)")
    print(f"    {'rail':<16}{'kind':<6}{'over rail':>12}{'write local':>14}")
    for x in km["rails"]:
        print(f"    {x['name']:<16}{x['kind']:<6}{x['latency_label']:>12}{x['write_label']:>14}")
    print(f"\n  SURFACES")
    for s in km["surfaces"]:
        print(f"    {s['name']:<22}{str(s['write_mbs'] or '—'):>7} MB/s w  "
              f"{s['pct_label']:>7} full  {s['status']}")
    print(f"\n  MONITORS ({c['monitors_measuring_nothing']} measure NOTHING)")
    for m in km["monitors"]:
        flag = "🔴 MEASURES NOTHING" if m["measures_nothing"] else ""
        print(f"    {m['name']:<24}{m['status']:<10}{flag}")
    if km["clocks"]:
        print(f"\n  CLOCKS ({c['clocks_pending']} pending)")
        for k in km["clocks"]:
            d = k["days_out"]
            tail = "✅ SETTLED" if k["settled"] else (
                (str(d) + " days out") if isinstance(d, int) else "")
            print(f"    {k['name']:<28}{k['when']:<24}{tail}")
    if km["discrepancies"]:
        print(f"\n  🔴 OPEN DISCREPANCIES ({c['discrepancies_open']}) — measured wrong, "
              f"and NO RAIL WILL REPORT THEM")
        for x in km["discrepancies"]:
            print(f"    · {x['name']}")
    print("-" * 78)
    print(f"  nodes missing from KDash: {c['nodes_missing_from_kdash']}   "
          f"rails unmeasured: {c['rails_unmeasured']}   "
          f"monitors measuring nothing: {c['monitors_measuring_nothing']}   "
          f"discrepancies: {c['discrepancies_open']}")


def selftest() -> int:
    import tempfile
    # 🔴 THE FIXTURE DATES ARE RELATIVE, AND THEY DID NOT USED TO BE.
    #
    # This fixture hardcoded `measured = 2026-07-31` for a monitor with cadence_h = 24,
    # and asserted its status was GREEN. That was true on 2026-07-31 and FALSE from
    # 2026-08-01 onward: an 11-day-old reading against a 1-day cadence is correctly RED,
    # so the selftest was asserting the feed's staleness logic was BROKEN.
    #
    # Nobody saw it for eleven days because bts_kdash_feed ALSO crashed on a red-circle
    # emoji whenever stdout was redirected (S-134), so the scheduler never got far enough
    # to run this. Fixing the encoding is what made the failure visible - one repair
    # exposing another is the normal shape, not a surprise.
    #
    # ==> A FIXTURE WITH AN ABSOLUTE DATE TESTS "IS IT 2026-07-31" AS MUCH AS IT TESTS
    #     THE LOGIC. A test that expires is worse than no test: it goes from proving
    #     something to disproving something, silently, on a date nobody wrote down.
    today = _dt.date.today()
    fresh_d = today.isoformat()
    ancient_d = (today - _dt.timedelta(days=220)).isoformat()
    soon_d = (today + _dt.timedelta(days=3)).isoformat()      # a clock still ahead of us
    far_d = (today + _dt.timedelta(days=136)).isoformat()     # comfortably ahead
    fixture = f"""
schema = 1
[[rail]]
name = "timed"
kind = "api"
latency_ms = 100.0
measured = {fresh_d}
[[rail]]
name = "never-timed"
kind = "cli"
[[monitor]]
name = "fresh"
cadence_h = 24
measured = {fresh_d}
[[monitor]]
name = "ancient"
cadence_h = 24
measured = {ancient_d}
[[surface]]
name = "empty-but-measured"
used_gb = 0.0
quota_gb = 15.0
measured = {fresh_d}
[[surface]]
name = "broken"
state = "FAULTED {fresh_d} - powered off"
measured = {fresh_d}
[[clock]]
name = "still-coming"
when = {far_d}
[[clock]]
name = "already-settled"
when = {soon_d}
settled = true
state = "SETTLED {fresh_d} - NON-EVENT."
[[clock]]
name = "withdrawn"
when = {soon_d}
settled = false
state = "NOT SETTLED - the check queried the wrong account."
"""
    p = os.path.join(tempfile.mkdtemp(), "f.toml")
    open(p, "w", encoding="utf-8").write(fixture)
    km = build(p)
    r = {x["name"]: x for x in km["rails"]}
    m = {x["name"]: x for x in km["monitors"]}
    ok1 = r["never-timed"]["latency_label"] == "UNMEASURED" and r["never-timed"]["latency_ms"] is None
    ok2 = r["timed"]["latency_label"] == "100 ms"
    ok3 = m["ancient"]["status"] == "RED"
    ok4 = m["fresh"]["status"] == "GREEN"
    k = {x["name"]: x for x in km["clocks"]}
    # added 2026-07-31: the panel said "14 days out" about a clock already measured as a non-event
    ok5 = k["already-settled"]["settled"] and k["already-settled"]["days_out"] is None
    ok6 = (not k["still-coming"]["settled"]) and isinstance(k["still-coming"]["days_out"], int)
    ok7 = km["counts"]["clocks_pending"] == 2
    # the substring bug: "NOT SETTLED" contains "SETTLED" and rendered as ✅ for an hour
    ok8 = (not k["withdrawn"]["settled"]) and isinstance(k["withdrawn"]["days_out"], int)
    sf = {x["name"]: x for x in km["surfaces"]}
    ok9 = sf["empty-but-measured"]["pct"] == 0.0 and sf["empty-but-measured"]["pct_label"] == "0.0%"
    ok10 = sf["broken"]["status"] == "RED"
    for n, v in (("untimed rail -> UNMEASURED, not 0", ok1), ("timed rail -> the number", ok2),
                 ("measurement older than cadence -> RED", ok3), ("fresh -> GREEN", ok4),
                 ("SETTLED clock -> no countdown", ok5),
                 ("pending clock -> still counts down", ok6),
                 ("only pending clocks are tallied", ok7),
                 ('"NOT SETTLED" does NOT read as settled', ok8),
                 ("0.0% full renders as 0.0%, not as unknown", ok9),
                 ("a FAULTED surface renders RED, not fresh-GREEN", ok10)):
        print(f"  {'OK  ' if v else 'FAIL'}  {n}")
    good = ok1 and ok2 and ok3 and ok4 and ok5 and ok6 and ok7 and ok8 and ok9 and ok10
    print("SELFTEST PASS — the feed cannot render a missing number as a real one, and cannot "
          "render a stale reading as current." if good else "SELFTEST FAIL — do not trust this feed.")
    return 0 if good else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    km = build()
    report(km)
    if "--dry-run" not in sys.argv:
        write(km)
        print(f"\n  written -> {DASH} (key: 'kmesh')")
    sys.exit(0)
