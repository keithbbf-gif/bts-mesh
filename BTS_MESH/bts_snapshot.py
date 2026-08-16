"""
bts_snapshot.py — writes ONE file, dash.json, that the dashboard reads for everything.

WHY THIS EXISTS (Keith, 2026-07-12)
  The dashboard was fetching /api/burn, /api/surfaces and /api/policy live. That only works if
  bts_serve.py is the thing serving the page — and if it is not (plain http.server, or the page
  opened as file://), every panel silently fell back to its hardcoded value and said "unknown".
  Which is exactly what Keith saw: GDX "? / 100 GB" on screen while bts_surfaces.py had just
  measured 15 / 100 GB on the command line.

  Keith's call, and it is the right one:
      "It is only working to load the numbers from the json file... the disk cap can be
       static updated only at the Open or Close of the Dash."

  So: ONE static JSON snapshot. The page just reads it. That works on ANY http server, needs no
  /api routes, and cannot half-fail. The expensive part (walking OneDrive to size it — 105 GB of
  files) runs at Open, not on a 15-second poll, which is what it should have been all along.

WHAT IS LIVE vs SNAPSHOT — this distinction matters and the dashboard shows it:
  * SURFACES (disk caps)  -> SNAPSHOT. Refreshed at dashboard Open (and on <TEST>). A folder walk
                             is far too slow to poll, and the numbers move slowly anyway.
  * BURN (tokens/$)       -> re-read from the ledgers every time this runs; cheap (two small JSONs).
  * BENCH (rail latency)  -> only refreshed when <TEST> is pressed, because probing the paid rail
                             costs money. Never on a timer.

Run:
  python bts_snapshot.py            # surfaces + burn + policy   (fast: no paid calls)
  python bts_snapshot.py --bench    # ...and re-run the mesh <TEST>  (costs ~$0.001)
"""
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "dash.json")


def _read(name, default=None):
    try:
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def burn():
    """GEM and SGH are NOT the same kind of meter, and one number for both would lie:
         GEM is FREE -> the scarce thing is REQUESTS/day.  Tokens are volume.
         SGH is PAID -> the scarce thing is DOLLARS/month. Tokens are what you are buying."""
    out = {}

    g = _read("gem_quota.json", {}) or {}
    try:
        import bts_gem
        rpd, pshare = bts_gem.MAX_RPD, bts_gem.POLL_SHARE
    except Exception:
        rpd, pshare = 1500, 0.20
    used = (g.get("WORK", 0) or 0) + (g.get("POLL", 0) or 0)
    # WHICH RAIL IS ACTUALLY SERVING GEM? (2026-07-12) AI Studio's express prepay credits are
    # depleted, so bts_gem fails over to Vertex — which is NOT free, it draws the $300 credit.
    # The dashboard must show that, not a comfortable "free".
    gem_via, gem_note = "aistudio", None
    try:
        import bts_gem
        probe = bts_gem.ask("ping", priority="POLL", allow_failover=False)
        if not probe.get("ok") and probe.get("reason") == "CREDITS_DEPLETED":
            gem_via = "vertex"
            # *** REWRITTEN 2026-07-15 — the old text was false on every clause. ***
            # It said the credit "expires ~2026-10-10" on billing account 0142FE, which NEVER HELD A
            # CREDIT: bts_vertex was charging a real card (~$1) the whole time. It also implied the
            # free tier was merely "depleted" and would come back. It will not.
            gem_note = (
                "GEM's free tier is DEAD, not spent. The 429 says 'prepayment credits are depleted' "
                "— that is a BILLING STATE, not a quota, and it does NOT reset at midnight. Google: "
                "'Your projects aren't automatically downgraded to the Free Tier.' MEASURED 2026-07-15: "
                "ANY billing account linked to the project — INCLUDING A FREE-TRIAL ONE — kills the "
                "free tier (Tier 1/Prepay @ $0). Only a project with billing NEVER linked gets it. "
                "GEM is now failing over to VERTEX (gemini-2.5-flash) on the JOANNA account's $300 "
                "(010E47-824B53-7202F5). ⚠ Whether that credit actually PAYS for Agent Platform is "
                "UNVERIFIED — no Google page states it; only Billing→Reports can say. "
                "See BTS_MESH/GEMINI_TOPOLOGY_CORRECTION_2026-07-15.md.")
    except Exception:
        pass

    # ⚠ cap=RPD: 1500 is NOT measured and Google NO LONGER PUBLISHES a number (docs/rate-limits links
    # an authenticated dashboard). Measured here: gemini-flash-latest 429'd after ~18 calls. This is a
    # LOCAL governor, not Google's quota — the dashboard's "x / 1500" bar is decorative. Do not plan
    # a sweep against it.
    out["gem"] = {"kind": "free" if gem_via == "aistudio" else "credit",
                  "date": g.get("date"),
                  "via": gem_via, "via_note": gem_note,
                  "used": used, "cap": rpd,
                  "cap_measured": False,
                  "pct": round(100.0 * used / rpd, 1) if rpd else 0.0,
                  "work": g.get("WORK", 0), "poll": g.get("POLL", 0),
                  "poll_cap": int(rpd * pshare),
                  "tok": g.get("tok", 0)}

    s = _read("sgh_spend.json", {}) or {}
    try:
        import bts_sgh
        cap, pshare = bts_sgh.MONTHLY_BUDGET_USD, bts_sgh.POLL_SHARE
    except Exception:
        cap, pshare = 10.00, 0.20
    spent = (s.get("WORK", 0.0) or 0.0) + (s.get("POLL", 0.0) or 0.0)
    ti, to = s.get("tok_in", 0), s.get("tok_out", 0)
    tc = s.get("tok_cached", 0)
    out["sgh"] = {"kind": "paid", "month": s.get("month"),
                  "spent": round(spent, 6), "cap": cap,
                  "pct": round(100.0 * spent / cap, 2) if cap else 0.0,
                  "left": round(max(0.0, cap - spent), 4),
                  "calls": s.get("calls", 0), "tool_calls": s.get("tool_calls", 0),
                  "tok_in": ti, "tok_out": to, "tok": ti + to,
                  "tok_cached": tc,
                  "cache_hit_pct": round(100.0 * tc / ti, 1) if ti else 0.0,
                  "usd_saved": round(s.get("usd_saved", 0.0), 6),
                  "usd_per_ktok": round(spent / ((ti + to) / 1000.0), 4) if (ti + to) else None,
                  "autoreload": True}
    return out


def run(with_bench=False, free_only=False) -> dict:
    snap = {"ts": int(time.time()),
            "when": time.strftime("%Y-%m-%d %H:%M:%S"),
            "burn": burn()}

    # SURFACES — the slow one (walks OneDrive). Open/Close only, per Keith.
    try:
        import bts_surfaces
        snap["surfaces"] = bts_surfaces.run()["surfaces"]
    except Exception as e:
        snap["surfaces"] = None
        snap["surfaces_error"] = str(e)[:160]

    # THE COWORK WALLET — the biggest one, and the only UNCAPPED one. An ESTIMATE that grades
    # itself against Keith's pasted ground truth. It is flagged is_estimate=True so the dashboard
    # can never render it as a measurement.
    try:
        import bts_claude
        snap["cowork"] = bts_claude.estimate(record=False)   # don't log a prediction per snapshot
    except Exception as e:
        snap["cowork"] = None
        snap["cowork_error"] = str(e)[:160]

    # THE CREDIT CLOCK — the $300 does NOT renew.
    # 🔴 2026-07-15: THIS METER GENERATED THE "$299 WASTE" PHANTOM. Read before trusting any of it.
    # On 2026-07-15 the free-tier-allotment-check task read this block, reported "$299 about to be
    # WASTED", and made it a headline — on billing account 0142FE, which NEVER HELD A CREDIT. Every
    # input was fiction: `spent` is bts_vertex's OWN token arithmetic (never reconciled with Google),
    # and `total` was a console banner nobody re-read. An estimate divided by an assumption.
    # `projected_waste` is therefore a PROJECTION OF A PROJECTION. It is now explicitly fenced below.
    # GROUND TRUTH IS Billing→Reports ONLY: "Other savings" negative + Subtotal $0.00 = credit paid it.
    try:
        import bts_vertex
        snap["credit"] = bts_vertex.credit_clock()
        if isinstance(snap["credit"], dict):
            snap["credit"]["_trusted"] = False
            snap["credit"]["_warning"] = (
                "DO NOT SOUND AN ALARM WITH THESE NUMBERS. 'spent' is bts_vertex.py's own token "
                "arithmetic, NEVER reconciled against Google. 'projected_waste' is a projection of "
                "that estimate and was the source of the fabricated '$299 waste' on 2026-07-15. "
                "Worse: it is not established that the $300 pays for Agent Platform AT ALL — no "
                "Google page states it, so a 'waste' figure may be measuring a credit that was never "
                "spendable here. VERIFY IN Billing→Reports (group by SKU): 'Other savings' NEGATIVE "
                "with Subtotal $0.00 = the credit paid. NOT the Cloud Hub Optimization page — that "
                "shows GROSS cost with credits invisible. Billing data lags up to 24h.")
            snap["credit"]["_expires_source"] = (
                "COMPUTED (start+90d), NOT read from the console. Terms §1.3 says the earlier of "
                "'$300 spent' or '3 MONTHS' — and Google uses '3 months'/'90 days' interchangeably "
                "though they differ. Read Billing→Overview and fix CREDIT_EXPIRES in bts_vertex.py.")
    except Exception as e:
        snap["credit"] = None
        snap["credit_error"] = str(e)[:160]

    try:
        import bts_policy
        snap["policy"] = bts_policy.resolve()
    except Exception as e:
        snap["policy"] = None
        snap["policy_error"] = str(e)[:160]

    # BENCH — only on demand. It probes the PAID rail, so it never runs on a timer.
    if with_bench:
        try:
            import bts_bench
            snap["bench"] = bts_bench.run(free_only=free_only)
        except Exception as e:
            snap["bench"] = None
            snap["bench_error"] = str(e)[:160]
    else:
        snap["bench"] = _read("bench.json", None)      # last measured, if any

    # ── MERGE THE STANDALONE MEASUREMENTS ────────────────────────────────────────────────────
    # BUG FIXED 2026-07-13, and it silently destroyed every measurement taken today:
    # this function REBUILDS dash.json from scratch on every dashboard open. The bench scripts
    # (bts_chanbench / bts_drivebench / bts_quota) were writing their results straight INTO
    # dash.json — so the next launch overwrote all of them, and the dashboard went back to
    # showing "not measured" for channels we had actually measured (GEM at 5183 ms, for one).
    #
    # A measurement that a refresh can erase is not a measurement. Each bench now owns its OWN
    # file, and the snapshot MERGES them in. Order matters: never clobber, always merge.
    chan = _read("chan.json", None)                    # bts_chanbench -> the node<->node links
    if chan:
        snap.setdefault("bench", {}) or snap.__setitem__("bench", {})
        if not isinstance(snap.get("bench"), dict):
            snap["bench"] = {}
        snap["bench"]["internodes"] = chan.get("internodes")
        snap["bench"]["channels_measured_at"] = chan.get("measured_at")
    drv = _read("drives.json", None)                   # bts_drivebench -> read/write MB/s
    if drv:
        snap["drives"] = drv.get("drives")
        snap["drives_measured_at"] = drv.get("measured_at")
    srf = _read("surfaces.json", None)                 # bts_quota -> real used/quota per surface
    if srf:
        snap["surfaces_measured"] = srf.get("surfaces")
        snap["surfaces_measured_at"] = srf.get("measured_at")

    # SIGNAL LOG — mesh_state.json is now the EVENT-SOURCED projection OWNED by bts_state.py (the
    # passive observer, 2026-07-14). It carries nodes{} + events[] that the dashboard's MESH NODES
    # panel and SIGNAL LOG read live. bts_snapshot MUST NOT overwrite it with the old counts/signals
    # schema — that would erase the live feed. Instead we REBUILD it from the append-only log (the
    # source of truth) so a dashboard Open still refreshes it, and read the newest events for the age
    # stamp. rebuild() is a pure record replay: it dispatches nothing and spends nothing.
    try:
        import bts_state
        proj = bts_state.rebuild()
        evs = proj.get("events") or []
        snap["signal_ts"] = evs[-1].get("ts") if evs else None
        snap["signal_count"] = len(evs)
    except Exception as e:
        snap["state_error"] = str(e)[:160]

    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, OUT)                                # atomic — never a half-written dash.json
    return snap


if __name__ == "__main__":
    wb = "--bench" in sys.argv
    fo = "--free" in sys.argv
    s = run(with_bench=wb, free_only=fo)
    b = s["burn"]
    print("dash.json written  %s" % s["when"])
    print("  SGH  $%.4f / $%.0f (%.2f%%) | %d calls | cache %.1f%% | saved $%.4f"
          % (b["sgh"]["spent"], b["sgh"]["cap"], b["sgh"]["pct"], b["sgh"]["calls"],
             b["sgh"]["cache_hit_pct"], b["sgh"]["usd_saved"]))
    print("  GEM  %d / %d req (%.1f%%)" % (b["gem"]["used"], b["gem"]["cap"], b["gem"]["pct"]))
    for sf in (s.get("surfaces") or []):
        u, t = sf.get("used_gb"), sf.get("total_gb")
        print("  %-5s %s / %s GB  %s" % (sf["name"],
              ("%.2f" % u) if u is not None else "?",
              ("%.0f" % t) if t is not None else "?",
              "" if sf.get("trusted") else "(untrusted)"))
    if s.get("bench"):
        print("  bench: %s" % s["bench"].get("when"))
    if wb:
        print("  <TEST> re-run. cost $%.6f" % (s["bench"] or {}).get("cost_usd", 0.0))
