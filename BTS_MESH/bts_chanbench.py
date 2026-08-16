#!/usr/bin/env python3
"""
bts_chanbench.py — MEASURE THE CHANNELS. Not the endpoints: the links.

Keith, 2026-07-13: "Measure the speed please and we need to check/fix and use these channels."

Writes results into dash.json -> bench.internodes, which is exactly what the SIGNAL CORE channel map
and the TELEMETRY / INTERNODES panel read. A channel with no measurement renders DASHED and says
"not measured" — never a plausible number. This script is how a dashed link becomes solid.

⚠ WHAT A "CHANNEL" NUMBER MUST NOT CONTAIN (Keith, 2026-07-13 — he caught this):
  Every ms below is a ROUND TRIP: wire + queueing + THE MODEL THINKING. For the API rails that is
  tolerable ONLY because the bench prompt is trivial ("Reply with exactly: OK", ~2 output tokens), so
  inference is a thin slice. The moment you bench with a REAL prompt, inference DOMINATES and the number
  stops being a channel measurement at all. That is exactly how SGH->GDX got reported as "~40 s": it was
  ~21 s of Grok thinking + ~17 s writing, and the sync leg was never separated. Twice now I have pinned
  someone else's latency on a wire (see the '30-90 s browser bridge' = COWORK's own overhead).
  THE ONLY PURE-TRANSPORT NUMBER WE HAVE IS TTFT: 254 ms trivial, 279 ms on a 2.4 KB payload — it barely
  moved with a 10x prompt, which is what a transport figure should do. Treat ms[] as ROUND TRIP, and
  never compare a trivially-benched rail against a really-benched one.

WHAT IS MEASURABLE FROM COWORK, AND WHAT HONESTLY IS NOT:
  COWORK↔GEM      API round trip. MEASURABLE. Free tier first (its daily quota dies at midnight).
  COWORK↔SGH      API round trip, UNGROUNDED (~$0.01-0.02). MEASURABLE. Grounded search stays refused.
  COWORK↔CROSSREF free, and the fastest rail we have. MEASURABLE.
  COWORK↔ITC      HTTP GET of the published site. MEASURABLE (bytes/s, not just ms).
  COWORK↔GDX      local Drive-mount write/read. MEASURABLE — but this is the LOCAL CACHE, not the
                  cloud round trip a remote node pays. Both numbers are reported, separately labelled.
  COWORK↔SGH(DOM) the browser bridge. NOT measurable from here — it is driven through the Chrome
                  extension, not from python. Reported as null. We do not invent it.
  SGH↔GDX         written by Grok's own connector; never passes through us. NOT measurable here.
                  It becomes measurable the moment SGH writes a file: bts_gdxbench.py --watch times it.
  SGH↔GBW         BOTH ARE GROK. Not a channel to optimise — a correlation to distrust.
"""
import json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DASH = os.path.join(HERE, "dash.json")
GDX = r"X:\My Drive\BTS_SGH_Handoff"


def ms(t0):
    return round((time.perf_counter() - t0) * 1000, 1)


def bench_gem():
    try:
        import bts_gem
        t0 = time.perf_counter()
        r = bts_gem.ask("Reply with exactly: OK")
        dt = ms(t0)
        txt = (r.get("text") if isinstance(r, dict) else str(r)) or ""
        # ⚠ THIS NOTE USED TO SAY "free tier" UNCONDITIONALLY — a HARDCODED STRING, printed no matter which
        # rail actually answered. On 2026-07-14 it made Cowork tell Keith "GEM's free tier is back!" when
        # AI Studio was still CREDITS_DEPLETED and ask() had silently failed over to VERTEX, spending the
        # $300 credit. A label that reports instead of measuring is the same bug as bias_voltage=0.
        # REPORT THE RAIL THE ANSWER CAME BACK ON, or say we do not know.
        rail = (r.get("rail") or r.get("model") or r.get("via") or "rail NOT reported by ask()") if isinstance(r, dict) else "?"
        return {"a": "COWORK", "b": "GEM", "ms": dt, "col": "#8b7cff",
                "note": "Gemini. RAIL=%s. Reply: %s" % (rail, txt.strip()[:20])}
    except Exception as e:
        try:
            import bts_vertex
            t0 = time.perf_counter()
            r = bts_vertex.ask("Reply with exactly: OK")
            return {"a": "COWORK", "b": "GEM", "ms": ms(t0), "col": "#8b7cff",
                    # 2026-08-11: this said 2026-10-10 - the UNSOURCED figure, superseded
                    # by the MEASURED 2026-10-13 (console banner: 74 days remaining on
                    # 2026-07-31; 07-31 + 74 = 10-13). It survived the 08-06 sweep that
                    # recorded "zero live 2026-10-10 references remain" because that sweep
                    # looked at three documents it already suspected, and this is a string
                    # literal inside an UNREGISTERED tool that fed the dashboard.
                    # ⇒ A DATE HARDCODED IN A STRING IS A COPY OF A FACT, AND COPIES ROT.
                    #   rails.toml [[clock]] "Vertex $300 credit expiry" is the source.
                    "note": "free tier 429'd -> VERTEX credit ($300, expires 2026-10-13 "
                            "- see rails.toml [[clock]], do not re-hardcode this)"}
        except Exception as e2:
            return {"a": "COWORK", "b": "GEM", "ms": None, "col": "#8b7cff",
                    "note": "BOTH Gemini rails failed: %r / %r" % (e, e2)}


def bench_sgh():
    try:
        import bts_sgh
        t0 = time.perf_counter()
        r = bts_sgh.ask("Reply with exactly: OK", priority="WORK", spill=False)
        dt = ms(t0)
        if not r.get("ok"):
            return {"a": "COWORK", "b": "SGH", "ms": None, "col": "#ffffff",
                    "note": "refused: %s" % r.get("reason")}
        b = r.get("budget", {})
        return {"a": "COWORK", "b": "SGH", "ms": dt, "col": "#ffffff",
                "note": "grok-4.5 API, UNGROUNDED. month $%.4f/$%.2f" % (b.get("spent", 0), b.get("budget", 0))}
    except Exception as e:
        return {"a": "COWORK", "b": "SGH", "ms": None, "col": "#ffffff", "note": "error: %r" % (e,)}


def bench_crossref():
    try:
        t0 = time.perf_counter()
        req = urllib.request.Request("https://api.crossref.org/works/10.1063/1.5129140",
                                     headers={"User-Agent": "BTS-mesh/1.0 (mailto:keith.bbf@gmail.com)"})
        urllib.request.urlopen(req, timeout=20).read(2000)
        return {"a": "COWORK", "b": "CROSSREF", "ms": ms(t0), "col": "#3ddc84",
                "note": "free, and the fastest rail we have. NEVER ask a model for a DOI."}
    except Exception as e:
        return {"a": "COWORK", "b": "CROSSREF", "ms": None, "col": "#3ddc84", "note": "error: %r" % (e,)}


def bench_itc():
    """ITC = the published site. NOTE: a bare urllib request gets 403 from Cloudflare — it sends no
    User-Agent and is treated as a bot. That was OUR bug, not an outage (2026-07-13). Send a UA."""
    try:
        t0 = time.perf_counter()
        u = "https://ai.dchambers.com/00_WORKING/00_NEXT_SESSION_HANDOFF_2026-07-12c.md?cb=%d" % time.time()
        req = urllib.request.Request(u, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BTS-mesh/1.0",
            "Accept": "*/*"})
        data = urllib.request.urlopen(req, timeout=25).read()
        dt = ms(t0)
        kb = len(data) / 1024.0
        return {"a": "COWORK", "b": "ITC", "ms": dt, "col": "#FBAD41",
                "note": "READ ONLY for the nodes. %.0f KB in %.0f ms = %.0f KB/s. Only COWORK can WRITE (R2 keys)."
                        % (kb, dt, kb / (dt / 1000.0) if dt else 0)}
    except Exception as e:
        return {"a": "COWORK", "b": "ITC", "ms": None, "col": "#FBAD41", "note": "error: %r" % (e,)}


def bench_gdx():
    if not os.path.isdir(GDX):
        return {"a": "COWORK", "b": "GDX", "ms": None, "col": "#3ddc84",
                "note": "X:\\My Drive\\BTS_SGH_Handoff not present"}
    payload = os.urandom(1 << 20) * 8          # 8 MB
    fn = os.path.join(GDX, "_chanbench_%d.tmp" % os.getpid())
    t0 = time.perf_counter()
    with open(fn, "wb", buffering=0) as f:
        f.write(payload); f.flush(); os.fsync(f.fileno())
    wt = ms(t0)
    t0 = time.perf_counter()
    with open(fn, "rb", buffering=0) as f:
        f.read()
    rt = ms(t0)
    os.remove(fn)
    return {"a": "COWORK", "b": "GDX", "ms": round((wt + rt) / 2, 1), "col": "#3ddc84",
            "note": "8 MB: write %.0f ms (%.0f MB/s), read %.0f ms (%.0f MB/s). LOCAL Drive cache — "
                    "NOT the cloud round trip a remote node pays (that is bts_gdxbench.py)."
                    % (wt, 8 / (wt / 1000.0), rt, 8 / (rt / 1000.0))}


UNMEASURABLE = [
    # ── SGH·DOM — MEASURED 2026-07-13, and it OVERTURNED our own routing premise ────────────────────
    # Still not measurable FROM PYTHON (the send has to be a real keypress — a synthetic Return
    # navigates the tab instead of submitting). So it was measured the only honest way: a DOM
    # MutationObserver armed in the page, Keith pressed Enter, and we read the transcript's growth.
    #   TTFT 254 ms · full round trip 2093 ms · 25 growth events · settled after 20 s of quiet.
    # The note this replaces claimed "typical observed: 30-90 s per exchange". That was NOT the
    # channel — it was COWORK's own overhead driving it (compose through the extension, poll, poll
    # again, click). The WIRE is faster than the SGH API (1838 ms) and faster than GEM (2857 ms).
    # We had been routing around a bottleneck that was us. Re-measure with a REAL payload before
    # trusting it for bulk: a trivial prompt says nothing about the 20 KB case, and 20 KB is exactly
    # where this bridge has silently truncated before (see feedback_bridge_fake_done).
    {"a": "COWORK", "b": "SGH·DOM", "ms": 2093.0, "col": "#8fa0c8",
     "note": "Chrome bridge. MEASURED 2026-07-13 via DOM observer + a HUMAN-pressed send. TTFT 254 ms, "
             "round trip 2093 ms. TRIVIAL PROMPT ONLY. The old '30-90 s' was COWORK's driving overhead, "
             "not the wire — the wire beats both APIs."},
    {"a": "SGH", "b": "GDX", "ms": None, "col": "#3ddc84",
     "note": "written by Grok's OWN Drive connector; never passes through Cowork. Becomes measurable the "
             "moment SGH writes a file: run bts_gdxbench.py --watch <name>."},
    {"a": "SGH", "b": "GBW", "ms": None, "col": "#ff6b6b",
     "note": "BOTH ARE GROK. Not a channel to optimise — a correlation to distrust. Never use one to "
             "check the other."},
]

if __name__ == "__main__":
    # the Windows console is cp1252 — arrows and em-dashes crash it. Keep stdout ASCII.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    out = []
    print("%-18s %10s   %s" % ("channel", "ms", "note"))
    print("-" * 100)
    for fn in (bench_crossref, bench_gdx, bench_itc, bench_gem, bench_sgh):
        r = fn()
        out.append(r)
        print("%-18s %10s   %s" % (r["a"] + "<->" + r["b"], r["ms"] if r["ms"] is not None else "-", r["note"][:70]))
        # PASSIVE STATE FEED — record each channel measurement for the dashboard. ms=None (a refused
        # or failed probe) is recorded honestly, not as a fake number. Never breaks the bench.
        try:
            import bts_state
            bts_state.emit(r["a"], r["b"], "channel_measured", (r.get("note") or "")[:120],
                           ms=r["ms"] if r.get("ms") is not None else None)
        except Exception:
            pass
    for r in UNMEASURABLE:
        out.append(r)
        print("%-18s %10s   %s" % (r["a"] + "↔" + r["b"], "—", r["note"][:70]))

    # OWN FILE, not dash.json. bts_snapshot.py REBUILDS dash.json on every dashboard open, so anything
    # written straight into it is destroyed by the next launch — which is exactly what happened to every
    # channel measured on 2026-07-13 (GEM at 5183 ms went back to reading "not measured"). The snapshot
    # now MERGES chan.json in. A measurement a refresh can erase is not a measurement.
    CHAN = os.path.join(HERE, "chan.json")
    payload = {"internodes": out, "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    tmp = CHAN + ".tmp"
    json.dump(payload, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, CHAN)
    print("\nwrote %d channels -> chan.json  (bts_snapshot merges it into dash.json; the SIGNAL CORE reads it)" % len(out))
