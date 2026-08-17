#!/usr/bin/env python3
r"""bts_kmesh_cockpit.py — measured KMesh cockpit for /api/burn.

    rails.toml is THE registry. bts_kdash_feed.build() RENDERS it. This module
    ASSEMBLES the cockpit object the dashboard paints:

      * every counted node, with honest family/model distinctions
      * Vertex is GEM's Google API/credit rail — never a sibling node
      * rails keep Vertex in the ledger; availability is never a fake green/0
      * surfaces expose configured_path (drive letters are values, not identity)
      * ITC publish/GrokDex fields are null unless a file already measured them
      * packets / queue / meters / family independence / staleness

    In-memory only. Does not write dash.json. Does not probe rails. Does not
    read .secrets. Does not spend.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RAILS = os.path.join(os.path.dirname(HERE), "ROLD", "rails.toml")
METERS = os.path.join(HERE, "meters.json")
QUEUE_LEDGER = os.path.join(HERE, "QUEUE.json")
DASH = os.path.join(HERE, "dash.json")

# Honest family/model map. toml `model` wins when present.
FAMILY = {
    "CoW": ("Anthropic Claude", "Opus 5 (1M ctx), Claude Max"),
    "GW": ("xAI Grok Build", "grok-build-0.1"),
    "SGH": ("xAI Grok", "grok-4.5"),
    "GEM": ("Google Gemini", "Gemini 2.5"),
    "CoPG": ("GitHub Copilot", "Copilot CLI"),
    "OA": ("OpenAI", "gpt-5.6 / Codex"),
    "CoP365": ("Microsoft 365 Copilot", "observation-only"),
}

AUTH_KINDS = {"api", "cli", "dom"}
VERTEX_NAMES = {"vertex"}
P_ARCHIVE_PATH = r"V:\Research4\Ai\PhD2_DATA_ARCHIVE"
QUEUE_ROOT_PATH = r"V:\Ai\_queue"

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def _now_iso(now=None) -> str:
    if now is None:
        now = _dt.datetime.now()
    if isinstance(now, str):
        return now
    return now.isoformat(timespec="seconds")


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def _load_toml(path):
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def _iso_date(v):
    if v is None:
        return None
    if isinstance(v, _dt.datetime):
        return v.date().isoformat()
    if isinstance(v, _dt.date):
        return v.isoformat()
    s = str(v)[:10]
    try:
        _dt.date.fromisoformat(s)
        return s
    except Exception:
        return str(v)


def _gem_display_name(raw) -> str:
    """GEM once. 'Gemini (Vertex)' is a historical label, not a second node."""
    if not raw:
        return "Gemini"
    name = str(raw).replace("(Vertex)", "").replace("Vertex", "")
    name = name.replace("  ", " ").strip(" ()")
    return name or "Gemini"


def _availability_for_rail(raw: dict, generated: str) -> dict:
    """Auth-dependent / unavailable rails are BLOCKED or UNKNOWN — never green/0."""
    kind = (raw.get("kind") or "").strip().lower()
    state = str(raw.get("state") or "")
    st_u = state.upper()
    measured = _iso_date(raw.get("measured"))
    lat = raw.get("latency_ms")

    if any(w in st_u for w in ("BROKEN", "DEAD", "FAILED", "DEPLETED")):
        return {
            "availability": "BLOCKED",
            "reason": state or "recorded broken",
            "as_of": measured or generated,
        }
    if any(w in st_u for w in ("NOT YET DRIVEN", "NOT LIVE", "REGISTERED, NOT LIVE")):
        return {
            "availability": "UNKNOWN",
            "reason": state or "registered, not proven",
            "as_of": measured or generated,
        }
    if kind in AUTH_KINDS:
        return {
            "availability": "UNKNOWN",
            "reason": ("auth-dependent rail not probed this run "
                       "(no spend; secrets not read; host is not the live Windows box)"),
            "as_of": generated,
        }
    if kind == "mcp":
        return {
            "availability": "UNKNOWN",
            "reason": "MCP path not present on this host; not probed",
            "as_of": generated,
        }
    if lat is None:
        return {
            "availability": "UNMEASURED",
            "reason": "no latency recorded",
            "as_of": measured or generated,
        }
    return {
        "availability": "UNKNOWN",
        "reason": "recorded measurement only; liveness not probed this run",
        "as_of": generated,
    }


def _paint_status(freshness: str, availability: str) -> str:
    """A rail that is BLOCKED/UNKNOWN/UNMEASURED must not render as GREEN."""
    av = (availability or "").upper()
    if av in ("BLOCKED", "UNKNOWN", "UNMEASURED"):
        return av
    return freshness or "UNKNOWN"


def _raw_by(rows, key="name"):
    return {str(x.get(key)): x for x in (rows or []) if x.get(key)}


def _itc_tile(raw_surfaces, generated: str, mesh_dir: str = None) -> dict:
    """Publish / keyed count / GrokDex — null unless a file already measured them.

    Public HTTP cannot enumerate R2. A source-tree walk is not a keyed object count.
    """
    mesh_dir = mesh_dir or HERE
    itc_raw = next((s for s in (raw_surfaces or [])
                    if str(s.get("name") or "").upper() == "ITC"), {})
    publish_log = os.path.join(mesh_dir, "PUBLISH.log")
    last_log = os.path.join(mesh_dir, "R2_PUBLISH_LAST.log")
    publish_present = os.path.isfile(publish_log) or os.path.isfile(last_log)

    # dash.json may carry a source-walk file count. That is NOT R2 enumeration.
    source_walk = None
    dash = _read_json(os.path.join(mesh_dir, "dash.json"), {}) or {}
    for sf in dash.get("surfaces") or []:
        if str(sf.get("id") or "").lower() == "itc":
            method = str(sf.get("method") or "")
            if "walk" in method.lower() and "file" in method.lower():
                source_walk = {
                    "method": method,
                    "used_gb": sf.get("used_gb"),
                    "note": "source-tree walk — not an R2 keyed object count",
                }
            break

    return {
        "identity": "ITC",
        "configured_path": itc_raw.get("path") or "https://ai.dchambers.com",
        "job": itc_raw.get("job"),
        "publish_status": "UNKNOWN",
        "publish_reason": (
            "PUBLISH.log / R2_PUBLISH_LAST.log not on this snapshot"
            if not publish_present
            else "log present — status not parsed this run (no live publish)"
        ),
        "publish_as_of": generated,
        "keyed_object_count": None,
        "keyed_object_count_reason": (
            "public HTTP cannot enumerate; no R2 object-listing artifact on this snapshot"
        ),
        "source_walk": source_walk,
        "grokdex": {
            "timestamp": None,
            "count": None,
            "status": "UNMEASURED",
            "reason": "no GrokDex/index artifact in this snapshot",
        },
        "mismatch": {
            "status": "UNKNOWN",
            "reason": "cannot compare R2 objects to source without a keyed listing",
        },
        "failure": None,
        "used_gb": itc_raw.get("used_gb"),
        "quota_gb": itc_raw.get("quota_gb"),
        "measured": _iso_date(itc_raw.get("measured")),
    }


def _extra_surfaces(generated: str) -> list:
    """Recorded / planned surfaces that are not first-class rails.toml rows."""
    return [
        {
            "name": "P archive",
            "identity": "PhD2_DATA_ARCHIVE",
            "job": "published/archive subtree (not a drive letter)",
            "configured_path": P_ARCHIVE_PATH,
            "path_role": "configured_path",
            "status": "UNKNOWN",
            "availability": "UNKNOWN",
            "used_gb": None,
            "quota_gb": None,
            "pct": None,
            "pct_label": "—",
            "age_days": None,
            "source": "recorded",
            "reason": ("size is not in a structured surface block; "
                       "do not promote a why-string figure to a measurement"),
            "as_of": generated,
        },
        {
            "name": "planned V:\\A share",
            "identity": "planned-va-share",
            "job": "planned share — not in rails.toml",
            "configured_path": None,
            "path_role": "none — drive letter is not identity",
            "status": "UNKNOWN",
            "availability": "UNKNOWN",
            "used_gb": None,
            "quota_gb": None,
            "pct": None,
            "pct_label": "—",
            "age_days": None,
            "source": "planned",
            "reason": "no measured configured path on this snapshot",
            "as_of": generated,
        },
    ]


def _queue(generated: str, mesh_dir: str = None) -> dict:
    mesh_dir = mesh_dir or HERE
    ledger_path = os.path.join(mesh_dir, "QUEUE.json")
    ledger = _read_json(ledger_path, None)
    live_present = os.path.isdir(QUEUE_ROOT_PATH)
    out = {
        "live_root": {
            "configured_path": QUEUE_ROOT_PATH,
            "present": live_present,
            "status": "LIVE" if live_present else "UNKNOWN",
            "reason": (None if live_present else
                       "live queue root not on this host; ledger silence ≠ idle and ≠ dead"),
            "as_of": generated,
        },
        "ledger": {
            "path": ledger_path if os.path.isfile(ledger_path) else None,
            "present": bool(ledger),
            "generated": (ledger or {}).get("generated"),
            "owners": (ledger or {}).get("owners"),
            "status": "STALE" if ledger else "UNKNOWN",
            "reason": ("QUEUE.json is a 2026-07-13 task sweep, not the live runner"
                       if ledger else "no queue ledger on this snapshot"),
            "as_of": generated,
        },
        "note": "liveness cannot be inferred from ledger silence (idle ≡ dead)",
    }
    return out


def _identity(generated: str) -> dict:
    try:
        import bts_identity as I
        ready, blockers = I.federation_ready()
        peers = {
            k: {"owner": v.get("owner"), "status": v.get("status"),
                "link": v.get("link"), "note": v.get("note")}
            for k, v in (I.PEERS or {}).items()
        }
        return {
            "mesh_id": I.MESH_ID,
            "host": I.HOST,
            "owner": I.OWNER,
            "software": "BTS_MESH",
            "registry": "ROLD/rails.toml",
            "instance_vs_software": "BTS_MESH is the software; KMesh is this instance",
            "federation_ready": ready,
            "federation_blockers": blockers,
            "peers": peers,
            "as_of": generated,
        }
    except Exception as e:
        return {
            "mesh_id": "KMesh",
            "software": "BTS_MESH",
            "registry": "ROLD/rails.toml",
            "status": "UNKNOWN",
            "reason": "bts_identity import failed: %s" % type(e).__name__,
            "as_of": generated,
        }


def _meters(generated: str, mesh_dir: str = None) -> dict:
    raw = _read_json(os.path.join(mesh_dir or HERE, "meters.json"), None)
    if not raw:
        return {
            "status": "UNKNOWN",
            "reason": "meters.json not readable on this snapshot",
            "as_of": generated,
            "pools": {},
        }
    pools = dict(raw.get("meters") or {})
    # Vertex dollars live under GEM. Do not emit a sibling VERTEX pool.
    gem_credit = pools.get("gem_api")
    return {
        "status": "RECORDED",
        "when": raw.get("when"),
        "as_of": generated,
        "pools": pools,
        "gem_credit": gem_credit,
        "vertex_is": "GEM credit rail (gem_api) — not a sibling pool",
    }


def _nodes(feed_nodes, feed_observers, raw_nodes, vertex_rail, generated):
    raw_map = _raw_by(raw_nodes, "id")
    nodes = []
    for n in feed_nodes or []:
        nid = n["id"]
        # Vertex is a rail. Skip only a Vertex *identity* — GEM's historical
        # name "Gemini (Vertex)" must still count as GEM.
        if str(nid).lower() in VERTEX_NAMES:
            continue
        if str(n.get("name") or "").strip().lower() in VERTEX_NAMES:
            continue
        raw = raw_map.get(nid, {})
        fam, model_default = FAMILY.get(nid, (None, None))
        display = n.get("name")
        if nid == "GEM":
            display = _gem_display_name(display)
        entry = {
            "id": nid,
            "display_name": display,
            "family": fam,
            "model": raw.get("model") or model_default,
            "kind": n.get("kind") or raw.get("kind"),
            "state": n.get("state") or raw.get("state"),
            "status": n.get("status"),
            "age_days": n.get("age_days"),
            "on_kdash": n.get("on_kdash"),
            "availability": "UNKNOWN",
            "availability_reason": "node liveness not probed this run",
            "as_of": generated,
        }
        if nid == "GEM":
            entry["studio_path"] = {
                "name": "AI Studio free tier",
                "availability": "BLOCKED",
                "reason": ("keith.bbf AI-Studio free-tier path BROKEN "
                           "(recorded on the GEM node; not a Vertex fact)"),
                "as_of": _iso_date(raw.get("measured")) or generated,
            }
            if vertex_rail:
                entry["credit_rail"] = vertex_rail
            else:
                entry["credit_rail"] = {
                    "name": "vertex",
                    "role": "gem_credit_rail",
                    "not_a_node": True,
                    "availability": "UNKNOWN",
                    "reason": "vertex rail not in registry",
                    "as_of": generated,
                    "latency_ms": None,
                }
        nodes.append(entry)

    observers = []
    for n in feed_observers or []:
        nid = n["id"]
        raw = raw_map.get(nid, {})
        fam, model_default = FAMILY.get(nid, (None, None))
        observers.append({
            "id": nid,
            "display_name": n.get("name"),
            "family": fam,
            "model": raw.get("model") or model_default,
            "kind": n.get("kind"),
            "status": "OBSERVER",
            "state": n.get("state") or raw.get("state"),
            "availability": "UNKNOWN",
            "reason": "observation-only — registered, not counted",
            "as_of": generated,
        })
    return nodes, observers


def _vertex_rail(feed_rails, raw_rails, generated):
    raw_map = _raw_by(raw_rails, "name")
    feed_map = {x["name"]: x for x in (feed_rails or [])}
    raw = raw_map.get("vertex") or {}
    fed = feed_map.get("vertex") or {}
    if not raw and not fed:
        return None
    avail = _availability_for_rail(raw or {"kind": "api"}, generated)
    return {
        "name": "vertex",
        "role": "gem_credit_rail",
        "not_a_node": True,
        "belongs_to": "GEM",
        "what": raw.get("what") or fed.get("what") or "GEM Google API/credit execution rail",
        "kind": raw.get("kind") or fed.get("kind") or "api",
        "cost": raw.get("cost") or fed.get("cost"),
        "expiry": "2026-10-13",
        "expiry_note": "confirmed twice (console banner); credit does not renew",
        "cap_usd": 300,
        "balance_usd": None,
        "balance_status": "UNKNOWN",
        "balance_reason": ("console banner is the only source; no Cloud Billing spend API. "
                           "Structured clock figure 297.09 is dated 2026-07-31 and superseded "
                           "in rail prose — not promoted to a live number."),
        "latency_ms": fed.get("latency_ms"),
        "latency_label": fed.get("latency_label") or "UNMEASURED",
        "status": _paint_status(fed.get("status"), avail["availability"]),
        "freshness": fed.get("status"),
        **avail,
    }


def _rails(feed_rails, raw_rails, generated):
    raw_map = _raw_by(raw_rails, "name")
    out = []
    for x in feed_rails or []:
        raw = raw_map.get(x["name"], {})
        avail = _availability_for_rail(raw or {"kind": x.get("kind"),
                                               "latency_ms": x.get("latency_ms"),
                                               "measured": None,
                                               "state": raw.get("state")}, generated)
        row = {
            "name": x["name"],
            "kind": x.get("kind"),
            "what": x.get("what"),
            "latency_ms": x.get("latency_ms"),
            "latency_label": x.get("latency_label") or (
                "UNMEASURED" if x.get("latency_ms") is None else None),
            "lands_on": x.get("lands_on"),
            "write_label": x.get("write_label"),
            "cost": x.get("cost"),
            "freshness": x.get("status"),
            "status": _paint_status(x.get("status"), avail["availability"]),
            **avail,
        }
        if x["name"].lower() in VERTEX_NAMES:
            row["role"] = "gem_credit_rail"
            row["belongs_to"] = "GEM"
            row["not_a_node"] = True
        out.append(row)
    return out


def _surfaces(feed_surfaces, generated, itc):
    rows = []
    for s in feed_surfaces or []:
        row = dict(s)
        row["identity"] = s.get("name")
        row["path_role"] = "configured_path"
        if "configured_path" not in row:
            row["configured_path"] = None
        if str(s.get("name") or "").upper() == "ITC":
            row["itc"] = itc
        rows.append(row)
    rows.extend(_extra_surfaces(generated))
    return rows


def empty(reason: str, generated: str, packets=None) -> dict:
    """Honest UNKNOWN cockpit when the registry cannot be read."""
    return {
        "ok": False,
        "generated": generated,
        "source_rule": "rails.toml is THE registry. KDash renders it and never keeps its own list.",
        "reason": reason,
        "nodes": [],
        "observers": [],
        "rails": [],
        "surfaces": _extra_surfaces(generated),
        "itc": _itc_tile([], generated, HERE),
        "packets": packets or {},
        "counts": {"nodes": 0, "observers": 0, "rails": 0, "rails_unmeasured": 0},
        "vertex_node_drawn": False,
    }


def build(rails_path: str = None, packets=None, now=None, mesh_dir: str = None) -> dict:
    """In-memory cockpit. Never writes dash.json."""
    generated = _now_iso(now)
    rails_path = rails_path or RAILS
    mesh_dir = mesh_dir or HERE

    if not os.path.isfile(rails_path):
        return empty("rails.toml missing — nothing measured", generated, packets)

    try:
        import bts_kdash_feed
        feed = bts_kdash_feed.build(rails_path)
        raw = _load_toml(rails_path)
    except Exception as e:
        return empty("%s: %s" % (type(e).__name__, str(e)[:180]), generated, packets)

    vertex = _vertex_rail(feed.get("rails"), raw.get("rail"), generated)
    nodes, observers = _nodes(feed.get("nodes"), feed.get("observers"),
                              raw.get("node"), vertex, generated)
    rails = _rails(feed.get("rails"), raw.get("rail"), generated)
    itc = _itc_tile(raw.get("surface"), generated, mesh_dir)
    surfaces = _surfaces(feed.get("surfaces"), generated, itc)

    families = []
    for n in nodes:
        families.append({
            "id": n["id"],
            "family": n.get("family"),
            "model": n.get("model"),
            "independent": True,
        })

    return {
        "ok": True,
        "generated": generated,
        "ts": int(time.time()),
        "source": rails_path,
        "source_rule": feed.get("source_rule") or (
            "rails.toml is THE registry. KDash renders it and never keeps its own list."),
        "wrote_dash": False,
        "identity": _identity(generated),
        "family_independence": {
            "rule": "families are independent nodes; a rail is not a node",
            "families": families,
            "not_nodes": ["vertex", "CoP365"],
            "vertex": "GEM Google API/credit execution rail — nest under GEM, keep in ledger",
        },
        "nodes": nodes,
        "observers": observers,
        "rails": rails,
        "surfaces": surfaces,
        "itc": itc,
        "monitors": feed.get("monitors") or [],
        "clocks": feed.get("clocks") or [],
        "discrepancies": feed.get("discrepancies") or [],
        "bfast": feed.get("bfast") or {},
        "packets": packets or {},
        "queue": _queue(generated, mesh_dir),
        "meters": _meters(generated, mesh_dir),
        "counts": {
            "nodes": len(nodes),
            "observers": len(observers),
            "rails": len(rails),
            "rails_unmeasured": sum(1 for x in rails if x.get("latency_ms") is None),
            "rails_not_green": sum(1 for x in rails if x.get("status") != "GREEN"),
            "surfaces": len(surfaces),
        },
        "vertex_node_drawn": False,
        "last_measured": generated,
        "staleness_rule": "UNMEASURED never a number; stale = RED; auth-unavailable = BLOCKED/UNKNOWN, never green/0",
    }
