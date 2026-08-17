"""test_kmesh_cockpit.py — missing/stale/unmeasured + Vertex-under-GEM."""
import datetime as dt
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bts_kmesh_cockpit as C
import bts_serve as S

fails = []


def check(name, cond):
    print(("  PASS " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


today = dt.date.today()
fresh = today.isoformat()
ancient = (today - dt.timedelta(days=220)).isoformat()

print("== live registry (rails.toml) ==")
km = C.build()
check("ok", km.get("ok") is True)
ids = [n["id"] for n in km.get("nodes") or []]
names = [str(n.get("display_name") or "") for n in km.get("nodes") or []]
check("no Vertex node id", "vertex" not in {i.lower() for i in ids})
check("no Vertex display name as a node",
      all("vertex" not in n.lower() for n in names))
check("GEM present once", ids.count("GEM") == 1)
gem = next(n for n in km["nodes"] if n["id"] == "GEM")
check("GEM display is Gemini not Vertex",
      gem["display_name"] == "Gemini" and "Vertex" not in (gem["display_name"] or ""))
cr = gem.get("credit_rail") or {}
check("GEM nests Vertex credit rail",
      cr.get("name") == "vertex" and cr.get("not_a_node") is True
      and cr.get("belongs_to") == "GEM")
check("credit rail balance not fabricated", cr.get("balance_usd") is None)
check("studio path BLOCKED",
      (gem.get("studio_path") or {}).get("availability") == "BLOCKED")
check("vertex_node_drawn false", km.get("vertex_node_drawn") is False)
check("did not write dash.json", km.get("wrote_dash") is False)

rail_names = [r["name"] for r in km.get("rails") or []]
check("vertex remains in ledger/rails", "vertex" in rail_names)
vtx = next(r for r in km["rails"] if r["name"] == "vertex")
check("vertex rail marked gem_credit_rail",
      vtx.get("role") == "gem_credit_rail" and vtx.get("not_a_node") is True)
check("vertex rail not GREEN availability",
      vtx.get("availability") in ("BLOCKED", "UNKNOWN", "UNMEASURED")
      and vtx.get("status") != "GREEN")
check("auth rails never GREEN",
      all(r.get("status") != "GREEN" for r in km["rails"]
          if (r.get("kind") or "") in ("api", "cli", "dom")))
check("unmeasured latency is null not 0",
      all(r.get("latency_ms") is None or r.get("latency_ms") != 0
          or r.get("name") == "never-zero-ok"
          for r in km["rails"] if r.get("latency_label") == "UNMEASURED"))
unmeas = [r for r in km["rails"] if r.get("latency_ms") is None]
check("unmeasured rails exist and are not 0",
      unmeas and all(r.get("latency_ms") is None for r in unmeas)
      and all(r.get("status") in ("UNMEASURED", "UNKNOWN", "BLOCKED") for r in unmeas))

check("honest families: GW != SGH",
      next(n for n in km["nodes"] if n["id"] == "GW")["model"] !=
      next(n for n in km["nodes"] if n["id"] == "SGH")["model"])
check("CoPG != CoP365",
      "CoPG" in ids and all(n["id"] != "CoP365" for n in km["nodes"])
      and any(o["id"] == "CoP365" for o in km.get("observers") or []))
check("OA is a counted node", "OA" in ids)

itc = km.get("itc") or {}
check("ITC keyed count is null", itc.get("keyed_object_count") is None)
check("GrokDex unmeasured",
      (itc.get("grokdex") or {}).get("count") is None
      and (itc.get("grokdex") or {}).get("status") == "UNMEASURED")
check("ITC publish not green", itc.get("publish_status") in ("UNKNOWN", "UNMEASURED", "BLOCKED"))

surf = {s["name"]: s for s in km.get("surfaces") or []}
check("surfaces carry configured_path key",
      all("configured_path" in s for s in km["surfaces"] if s.get("source") != "planned"))
check("V: Ai path is configured not identity",
      surf.get("V: Ai", {}).get("identity") == "V: Ai"
      and surf.get("V: Ai", {}).get("path_role") == "configured_path")
check("P archive present UNKNOWN",
      surf.get("P archive", {}).get("status") == "UNKNOWN"
      and surf.get("P archive", {}).get("used_gb") is None)
check("planned V:\\A share UNKNOWN no path identity",
      surf.get("planned V:\\A share", {}).get("status") == "UNKNOWN"
      and surf.get("planned V:\\A share", {}).get("configured_path") is None)
check("GHX present", "GHX" in surf)
check("queue silence is not LIVE",
      km["queue"]["live_root"]["status"] in ("UNKNOWN", "LIVE")
      and km["queue"]["note"])

print("== missing registry ==")
missing = C.build(rails_path=os.path.join(HERE, "no_such_rails.toml"))
check("missing rails -> not ok", missing.get("ok") is False)
check("missing rails -> no nodes", missing.get("nodes") == [])
check("missing rails -> no Vertex node", missing.get("vertex_node_drawn") is False)
check("missing rails surfaces still UNKNOWN extras",
      all(s.get("status") == "UNKNOWN" for s in missing.get("surfaces") or []))

print("== fixture: stale / unmeasured / Vertex-under-GEM ==")
d = tempfile.mkdtemp(prefix="kmesh_cockpit_")
try:
    fixture = f"""
schema = 1
[[node]]
id = "GEM"
name = "Gemini (Vertex)"
kind = "cli+api"
state = "LIVE on Vertex; AI-Studio free-tier path BROKEN"
measured = {fresh}
[[node]]
id = "SGH"
name = "Grok 4.5"
kind = "api"
measured = {ancient}
[[node]]
id = "CoP365"
name = "Microsoft 365 Copilot"
kind = "observation-only"
measured = {fresh}
[[rail]]
name = "vertex"
kind = "api"
what = "GEM credit rail"
latency_ms = 2019.2
measured = {fresh}
[[rail]]
name = "never-timed"
kind = "cli"
[[rail]]
name = "stale-api"
kind = "api"
latency_ms = 100.0
measured = {ancient}
[[surface]]
name = "ITC"
path = "https://ai.dchambers.com"
used_gb = 5.09
quota_gb = 10.0
measured = {ancient}
[[surface]]
name = "V: Ai"
path = 'V:\\Ai'
measured = {fresh}
"""
    p = os.path.join(d, "rails.toml")
    _write(p, fixture)
    dash_before = None
    dash_path = os.path.join(HERE, "dash.json")
    if os.path.isfile(dash_path):
        dash_before = os.path.getmtime(dash_path)
    fx = C.build(rails_path=p, now="2026-08-17T00:00:00", mesh_dir=d)
    check("fixture ok", fx.get("ok") is True)
    fids = [n["id"] for n in fx["nodes"]]
    check("fixture GEM once, no Vertex node",
          fids == ["GEM", "SGH"] or (fids.count("GEM") == 1 and "vertex" not in {i.lower() for i in fids}))
    fgem = next(n for n in fx["nodes"] if n["id"] == "GEM")
    check("fixture GEM display stripped", fgem["display_name"] == "Gemini")
    check("fixture credit rail nested",
          (fgem.get("credit_rail") or {}).get("name") == "vertex"
          and (fgem.get("credit_rail") or {}).get("not_a_node") is True)
    check("fixture observer CoP365 not counted",
          all(n["id"] != "CoP365" for n in fx["nodes"])
          and any(o["id"] == "CoP365" for o in fx["observers"]))
    fr = {r["name"]: r for r in fx["rails"]}
    check("never-timed latency null not 0",
          fr["never-timed"]["latency_ms"] is None
          and fr["never-timed"]["latency_label"] == "UNMEASURED"
          and fr["never-timed"]["status"] in ("UNMEASURED", "UNKNOWN"))
    check("stale-api freshness RED", fr["stale-api"]["freshness"] == "RED")
    check("stale-api paint not GREEN", fr["stale-api"]["status"] != "GREEN")
    check("vertex fixture not a node and not GREEN",
          fr["vertex"]["not_a_node"] is True and fr["vertex"]["status"] != "GREEN")
    check("ITC keyed still null on fixture", fx["itc"]["keyed_object_count"] is None)
    check("no dash.json rewrite",
          (not os.path.isfile(dash_path) and dash_before is None)
          or os.path.getmtime(dash_path) == dash_before)

    print("== no vertex rail ==")
    p2 = os.path.join(d, "no_vertex.toml")
    _write(p2, f"""
schema = 1
[[node]]
id = "GEM"
name = "Gemini (Vertex)"
kind = "cli+api"
measured = {fresh}
[[rail]]
name = "crossref"
kind = "api"
latency_ms = 200
measured = {fresh}
""")
    nv = C.build(rails_path=p2, mesh_dir=d)
    ng = next(n for n in nv["nodes"] if n["id"] == "GEM")
    check("missing vertex rail -> UNKNOWN credit_rail, no invented balance",
          (ng.get("credit_rail") or {}).get("availability") == "UNKNOWN"
          and (ng.get("credit_rail") or {}).get("latency_ms") is None
          and "vertex" not in {i.lower() for i in [x["id"] for x in nv["nodes"]]})
finally:
    shutil.rmtree(d, ignore_errors=True)

print("== burn() carries cockpit ==")
b = S.burn({
    "phone_out": None, "phone_in": None, "board": None, "lock": None, "tmp": None,
})
check("burn.kmesh is dict", isinstance(b.get("kmesh"), dict))
check("burn.kmesh no Vertex node",
      "vertex" not in {str(n.get("id") or "").lower()
                       for n in (b.get("kmesh") or {}).get("nodes") or []})
check("packets still on burn", "phone_out" in (b.get("packets") or {}))

print("RESULT %s" % ("PASS" if not fails else "FAIL: " + ", ".join(fails)))
sys.exit(0 if not fails else 1)
