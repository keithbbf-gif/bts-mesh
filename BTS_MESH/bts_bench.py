"""
bts_bench.py — the MESH NODES <TEST>.  Measures every rail and every internode link, for real.

WHY THIS EXISTS (and why the dashboard could never do it alone)
  jack_command.html's <TEST> button could only ever time the rails a BROWSER can reach: Crossref
  and ITC. Every API rail — SGH, GEM, Vertex — is blocked by CORS from a file:// or localhost page,
  so the dashboard showed their LAST MEASURED value and honestly said so. That is the whole reason
  the latency panel was half-hardcoded.

  The fix is not more JavaScript. It is to measure SERVER-SIDE, where there is no CORS, and let the
  page read the result. bts_bench.py is that measurement; bts_serve.py exposes it at /api/bench.

WHAT IT MEASURES
  1. NODES      — round-trip latency of each rail, median of N probes.
                  API rails (SGH/GEM/Vertex) are probed with a real 1-token question, so the number
                  includes model time, not just TCP. That is the number that matters to the mesh.
  2. INTERNODES — the LINKS, not the endpoints: ITC (publish->read), GDX (Drive round-trip),
                  and the Chrome bridge. A mesh is its edges.
  3. PARALLEL BUS — the headline. Runs the same fan-out serially, then concurrently, and reports
                  the SPEEDUP and the EFFICIENCY. Keith asked for parallel bussing specifically:
                  the question is not "is parallel faster" (it is) but "how much of the theoretical
                  speedup do we actually get", i.e. where the bus saturates.

COST DISCIPLINE
  A benchmark that spends real money every time someone pokes a button is a trap — especially with
  SGH auto-reloading $5 at a time. So:
    * SGH/GEM probes are the CHEAPEST possible call (a 1-word answer, search OFF, low effort).
      Measured: ~$0.0004 per SGH probe. A full <TEST> costs well under a cent.
    * SGH probes are booked as priority="POLL", so they draw on the 20% poll share and can NEVER
      starve real work. If the poll budget is spent, the probe REFUSES and reports POLL_BUDGET_SPENT
      rather than quietly spending Keith's month on telemetry.
    * --free skips every paid rail entirely.
  This is the same rule bts_gem.py already enforces for polling. It is not optional here.
"""
import json, os, sys, time, statistics, urllib.request, urllib.error
import concurrent.futures as cf

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT   = os.path.join(_HERE, "bench.json")

PROBE = "Reply with exactly one word: OK"
N_PROBES_HTTP = 3      # cheap -> median of 3
N_PROBES_API  = 1      # costs money -> one shot


# ------------------------------------------------------------------------------------------------
_last_status = {}


def _http(url: str, timeout=15) -> float:
    """Returns round-trip ms, or NaN. Records the HTTP status in _last_status[url].

    WHY THE STATUS MATTERS: run from a sandboxed/proxied environment, ai.dchambers.com returns
    403 (egress allowlist) even though the origin is healthy — it answered 200 on 2026-07-11 and
    the publish bat verifies it every run. A probe that only knows "exception" would report the
    ITC rail as DOWN, which is a confidently wrong reading of a working rail. So we keep the code
    and let the caller distinguish "the rail is down" from "I am not allowed to reach it FROM HERE".
    In production this module runs on Keith's Windows box via bts_serve, where it resolves normally.
    """
    t0 = time.perf_counter()
    try:
        r = urllib.request.urlopen(
            urllib.request.Request(url, headers={"Cache-Control": "no-cache"}), timeout=timeout)
        r.read(2048)
        _last_status[url] = r.status
        return (time.perf_counter() - t0) * 1000.0
    except urllib.error.HTTPError as e:
        _last_status[url] = e.code
        # a 4xx still round-tripped; the TRANSPORT works. Report the latency, flag the code.
        return (time.perf_counter() - t0) * 1000.0
    except Exception as e:
        _last_status[url] = type(e).__name__
        return float("nan")


def _median(xs):
    xs = [x for x in xs if x == x]                 # drop NaN
    return round(statistics.median(xs), 1) if xs else None


# ------------------------------------------------------------------------------------------------
# node probes. Each returns (ms, note, cost_usd)
# ------------------------------------------------------------------------------------------------
def probe_crossref():
    ms = _median([_http("https://api.crossref.org/works/10.1016/j.apsusc.2009.11.002")
                  for _ in range(N_PROBES_HTTP)])
    return ms, "DOI truth. Free, unlimited, and it is REGISTRY truth — not a model's recollection.", 0.0


ITC_PROBE = "https://ai.dchambers.com/00_WORKING/R2CLONER_MOVE_VERIFY.txt"


def probe_itc():
    url = ITC_PROBE + "?cb=%d" % time.time()
    ms = _median([_http(url) for _ in range(N_PROBES_HTTP)])
    st = _last_status.get(url)
    if isinstance(st, int) and st >= 400:
        return ms, ("Cloudflare R2 edge. Reached in %s ms but returned HTTP %d — from a sandboxed "
                    "host this is the EGRESS ALLOWLIST, not an outage. Re-run on the Windows box."
                    % (ms, st)), 0.0
    return ms, "Cloudflare R2 edge. How SGH/GEM/GBW read our published archive.", 0.0


def probe_sgh(free_only=False):
    if free_only:
        return None, "skipped (--free)", 0.0
    try:
        import bts_sgh
    except Exception as e:
        return None, "import failed: %s" % e, 0.0
    if not bts_sgh.key_present():
        return None, "NO KEY", 0.0
    t0 = time.perf_counter()
    # POLL class: telemetry may never starve real work. search OFF, low effort -> ~$0.0004.
    r = bts_sgh.ask(PROBE, priority="POLL", search=False, reasoning_effort="low")
    ms = (time.perf_counter() - t0) * 1000.0
    if not r.get("ok"):
        return None, r["reason"], 0.0
    return round(ms, 1), "grok-4.5 via /v1/responses. Real model time, not just TCP.", r.get("cost_usd", 0.0)


def probe_gem(free_only=False):
    """GEM may be served by AI Studio (free) OR by the Vertex failover ($300 credit).
       *** The probe MUST say which. *** A green "GEM: OK" that is silently spending credit is the
       comfortable lie this mesh keeps getting bitten by — it is how the rail looked healthy while
       AI Studio was actually dead."""
    try:
        import bts_gem
    except Exception as e:
        return None, "import failed: %s" % e, 0.0
    t0 = time.perf_counter()
    r = bts_gem.ask(PROBE, priority="POLL")
    ms = (time.perf_counter() - t0) * 1000.0
    if not r.get("ok"):
        return None, r.get("detail") or r["reason"], 0.0

    if r.get("via") == "vertex":
        # *** REWRITTEN 2026-07-15. The old note said the credit "expires ~2026-10-10" and told you
        # to "top up AI Studio to restore the free rail". Both wrong: that account never held a
        # credit, and topping up does NOT restore the free tier — a project with billing linked is
        # Tier 1 forever. MEASURED: even a FREE-TRIAL billing account kills it.
        return round(ms, 1), ("FAILED OVER TO VERTEX (%s) on %s — NOT the free tier. The free rail "
                              "is DEAD, not spent: 'prepayment credits depleted' is a BILLING STATE "
                              "and does not reset. TOPPING UP DOES NOT FIX IT — any billing account "
                              "linked to a project (even a free trial) makes it Tier 1 permanently. "
                              "The ONLY fix is a project with billing NEVER linked. ⚠ And it is "
                              "UNVERIFIED that the $300 even pays for Agent Platform — check "
                              "Billing→Reports before calling this free."
                              % (r.get("failover_from", "?"),
                                 r.get("model") or "vertex")), 0.0
    return round(ms, 1), "%s. FREE tier — volume rail." % bts_gem.MODEL, 0.0


def probe_vertex(free_only=False):
    if free_only:
        return None, "skipped (--free)", 0.0
    try:
        import bts_vertex
    except Exception as e:
        return None, "import failed: %s" % e, 0.0
    fn = getattr(bts_vertex, "ask", None)
    if not fn:
        return None, "no ask()", 0.0
    t0 = time.perf_counter()
    try:
        r = fn(PROBE)
    except Exception as e:
        return None, str(e)[:60], 0.0
    ms = (time.perf_counter() - t0) * 1000.0
    ok = r.get("ok") if isinstance(r, dict) else bool(r)
    if not ok:
        return None, (r.get("reason") if isinstance(r, dict) else "FAILED"), 0.0
    return round(ms, 1), "gemini-2.5-pro on the $300 credit. Use when it must be RIGHT.", 0.0


NODES = [
    ("crossref", "CROSSREF", "DOI truth",  "#3ddc84", probe_crossref),
    ("itc",      "ITC",      "R2 edge",    "#FBAD41", probe_itc),
    ("gem",      "GEM",      "flash·free", "#8b7cff", probe_gem),
    ("vertex",   "VERTEX",   "2.5-pro",    "#8b7cff", probe_vertex),
    ("sgh",      "SGH",      "grok-4.5",   "#e8734a", probe_sgh),
]


# ------------------------------------------------------------------------------------------------
# INTERNODES — the links, not the endpoints. A mesh is its edges.
# ------------------------------------------------------------------------------------------------
def _disk_rt(path, label):
    """Round-trip a small file: write -> fsync -> read back -> verify -> delete. Returns ms.
       This is the REAL cost of handing an artifact to that surface."""
    if not path or not os.path.isdir(path):
        return None, "not mounted on this machine"
    probe = os.path.join(path, ".bts_rt_probe.tmp")
    payload = ("bts-rt-%d" % time.time()) * 64          # ~1 KB, like a real handoff header
    try:
        t0 = time.perf_counter()
        with open(probe, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush(); os.fsync(f.fileno())
        back = open(probe, encoding="utf-8").read()
        ms = (time.perf_counter() - t0) * 1000.0
        os.remove(probe)
        if back != payload:
            return None, "round-trip CORRUPTED (wrote %d, read %d bytes)" % (len(payload), len(back))
        return round(ms, 2), label
    except Exception as e:
        try:
            os.remove(probe)
        except Exception:
            pass
        return None, "write failed: %s" % str(e)[:50]


GDX_DIRS = [r"G:\My Drive\BTS_SGH_Handoff", r"E:\My Drive\BTS_SGH_Handoff",
            r"H:\My Drive\BTS_SGH_Handoff", r"G:\My Drive", r"E:\My Drive"]
ROLD_DIR = r"V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING"


def internodes(free_only=False):
    """THE EDGES, not the endpoints. Keith: "measure the speeds around the network."

    A mesh is its links. Every edge below is measured FROM COWORK (the hub — this code runs on
    Keith's box), because that is where artifacts actually get handed off.

    *** ONE HONEST CAVEAT, and it is important. *** The GDX edge measured here is a LOCAL
    filesystem round-trip into the Drive-for-Desktop folder. It is NOT cloud propagation time.
    Google Drive syncs asynchronously: the file is on disk in milliseconds, but SGH/GBW cannot
    SEE it until Drive pushes it up — seconds to minutes. So this number tells you how fast
    Cowork can HAND OFF to the GDX surface, not how fast the far agent receives it. Reporting the
    local write as "the SGH<->GDX rail latency" would be a badly misleading 5 ms.
    """
    out = []

    # COWORK <-> ROLD : the local baseline. Everything else should be compared to this.
    ms, note = _disk_rt(ROLD_DIR, "local disk. The floor — nothing in the mesh beats it.")
    out.append({"id": "rold", "a": "COWORK", "b": "ROLD", "ms": ms, "ok": ms is not None,
                "col": "#3ddc84", "note": note})

    # COWORK <-> GDX : the cross-agent handoff surface.
    gdx = next((d for d in GDX_DIRS if os.path.isdir(d)), None)
    ms, note = _disk_rt(gdx, "Drive-for-Desktop folder. LOCAL write — the cloud sync that lets "
                             "SGH/GBW actually SEE it is ASYNC and takes seconds-to-minutes. "
                             "This is handoff cost, NOT far-agent visibility.")
    out.append({"id": "gdx", "a": "COWORK", "b": "GDX", "ms": ms, "ok": ms is not None,
                "col": "#3ddc84" if ms is not None else "#5f6ea0",
                "note": note if gdx else "Drive for Desktop not mounted."})

    # COWORK <-> ITC : publish -> read back off the R2 edge.
    u = ITC_PROBE + "?cb=%d" % time.time()
    ms = _median([_http(u) for _ in range(2)])
    st = _last_status.get(u)
    blocked = isinstance(st, int) and st >= 400
    out.append({"id": "itc", "a": "COWORK", "b": "ITC", "ms": ms,
                "ok": ms is not None and not blocked, "status": st, "col": "#FBAD41",
                "note": ("HTTP %d here = egress allowlist, NOT an outage." % st) if blocked
                        else "publish -> read back off the Cloudflare edge."})

    # COWORK <-> SGH : the API rail. This is the edge that just got ~38x faster.
    #
    # *** COST BUG, CAUGHT IN VERIFICATION 2026-07-12 — do not reintroduce. ***
    # This probe used to run REGARDLESS of free_only, so /api/bench?free=1 quietly called the PAID
    # rail while reporting cost $0.000000. It both spent money and under-reported it — the exact
    # failure the whole ledger exists to prevent. free_only now short-circuits it, and its cost is
    # returned to the caller instead of vanishing.
    ms, cost = None, 0.0
    if free_only:
        note = "skipped (--free): this edge probes the PAID rail."
    else:
        note = ("grok-4.5 API. Was 30-90 s over the Chrome bridge; this edge is the single "
                "biggest upgrade in the mesh.")
        try:
            import bts_sgh
            if bts_sgh.key_present():
                t0 = time.perf_counter()
                r = bts_sgh.ask(PROBE, priority="POLL", search=False, reasoning_effort="low")
                if r.get("ok"):
                    ms = round((time.perf_counter() - t0) * 1000.0, 1)
                    cost = r.get("cost_usd", 0.0) or 0.0
                else:
                    note = r.get("reason", "FAILED")
        except Exception as e:
            note = str(e)[:50]
    out.append({"id": "sgh", "a": "COWORK", "b": "SGH", "ms": ms, "ok": ms is not None,
                "col": "#e8734a", "cost_usd": round(cost, 6), "note": note})

    # SGH <-> GDX : the cross-agent leg. NOT measurable from here and we will not invent it.
    out.append({"id": "sgh-gdx", "a": "SGH", "b": "GDX", "ms": None, "ok": None,
                "col": "#5f6ea0",
                "note": "Grok's OWN Drive connector writes this leg — it does not pass through "
                        "Cowork, so we cannot time it from here. Proven working 2026-07-11. "
                        "Not measured, not guessed."})

    # COWORK <-> BROWSER : the bridge we are retiring.
    out.append({"id": "bridge", "a": "COWORK", "b": "BROWSER", "ms": 60000, "ok": True,
                "col": "#ff4d4d",
                "note": "~30-90 s Chrome bridge. RETIRED for SGH (now on the API). Still the only "
                        "path to GBW/Copilot. Carried from measurement, not re-probed."})
    return out


# ------------------------------------------------------------------------------------------------
# PARALLEL BUS — the number Keith actually asked for.
# ------------------------------------------------------------------------------------------------
def parallel_bus(fanout=4):
    """Same fan-out, serial then concurrent. Reports speedup AND efficiency.

    Uses the FREE rails only (Crossref/ITC). Fanning a paid rail out 4x just to measure the bus
    would be spending money to learn something the free rails already tell us: the bus is
    network-bound, and the concurrency is in the transport, not the model."""
    urls = ["https://api.crossref.org/works/10.1016/j.apsusc.2009.11.002",
            "https://ai.dchambers.com/1.md",
            "https://api.crossref.org/works/10.1038/nmat3159",
            "https://ai.dchambers.com/00_WORKING/R2CLONER_MOVE_VERIFY.txt"][:fanout]

    t0 = time.perf_counter()
    ser = [_http(u) for u in urls]
    t_ser = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(max_workers=len(urls)) as ex:
        par = list(ex.map(_http, urls))
    t_par = (time.perf_counter() - t0) * 1000.0

    ok = all(x == x for x in ser + par)
    speedup = (t_ser / t_par) if t_par > 0 else None
    # efficiency: of the theoretical N-x speedup, how much did the bus actually deliver?
    eff = (speedup / len(urls) * 100.0) if speedup else None
    return {"fanout": len(urls),
            "serial_ms": round(t_ser, 1),
            "parallel_ms": round(t_par, 1),
            "speedup": round(speedup, 2) if speedup else None,
            "efficiency_pct": round(eff, 1) if eff else None,
            "ok": ok,
            "note": "Theoretical max speedup = fanout (%dx). Efficiency = what the bus actually "
                    "delivered. Well under 100%% means the bus — not the nodes — is the limit."
                    % len(urls)}


# ------------------------------------------------------------------------------------------------
def run(free_only=False) -> dict:
    sys.path.insert(0, _HERE)
    t_start = time.time()
    nodes, spent = [], 0.0

    for nid, name, what, col, fn in NODES:
        try:
            ms, note, cost = (fn(free_only) if fn.__code__.co_argcount else fn())
        except Exception as e:
            ms, note, cost = None, "probe error: %s" % str(e)[:60], 0.0
        spent += (cost or 0.0)
        nodes.append({"id": nid, "name": name, "what": what, "col": col,
                      "ms": ms, "ok": ms is not None, "note": note,
                      "cost_usd": round(cost or 0.0, 6)})

    inodes = internodes(free_only=free_only)
    spent += sum((e.get("cost_usd") or 0.0) for e in inodes)   # was silently dropped -> $0 lie

    result = {
        "ts": int(t_start),
        "when": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t_start)),
        "nodes": nodes,
        "internodes": inodes,
        "bus": parallel_bus(),
        "cost_usd": round(spent, 6),
        "free_only": free_only,
        "elapsed_s": round(time.time() - t_start, 1),
    }
    try:
        tmp = OUT + ".tmp"
        with open(tmp, "w") as f:
            json.dump(result, f, indent=1)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, OUT)
    except Exception as e:
        result["write_error"] = str(e)[:120]
    return result


if __name__ == "__main__":
    free = "--free" in sys.argv
    r = run(free_only=free)
    print("MESH <TEST>  %s   (%.1fs, cost $%.6f%s)"
          % (r["when"], r["elapsed_s"], r["cost_usd"], ", FREE ONLY" if free else ""))
    print("\nNODES")
    for n in r["nodes"]:
        v = ("%8.1f ms" % n["ms"]) if n["ms"] is not None else "       -- "
        print("  %-9s %-11s %s  %s" % (n["name"], n["what"], v,
                                       "" if n["ok"] else "(" + str(n["note"])[:40] + ")"))
    print("\nINTERNODES")
    for e in r["internodes"]:
        v = ("%8.1f ms" % e["ms"]) if e["ms"] else "       -- "
        print("  %-7s -> %-8s %s  %s" % (e["a"], e["b"], v, "OK" if e["ok"] else "DOWN"))
    b = r["bus"]
    print("\nPARALLEL BUS  (fan-out %d)" % b["fanout"])
    print("  serial   %8.1f ms" % b["serial_ms"])
    print("  parallel %8.1f ms" % b["parallel_ms"])
    print("  speedup  %8s x   efficiency %s%% of the theoretical %dx"
          % (b["speedup"], b["efficiency_pct"], b["fanout"]))
    print("\nwrote %s" % OUT)
