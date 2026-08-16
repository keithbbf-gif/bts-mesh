r"""
bts_meters — build meters.json for KDash's top-bar rack.  Keith 2026-07-16:
  "Claude - quota battery, Ai Credits battery, API battery (cost meter)
   SGH - quota (xhours, daily, weekly, monthly), API battery (cost meter)
   GEM - API battery (cost/credit meter).  Let's start with those"

SIX POOLS, FOUR SCARCITY UNITS, SIX CLOCKS. That is why one battery could never work.

WHERE EACH NUMBER COMES FROM — and why most of them need Keith:
  MEASURED 2026-07-16: **all four vendors are UI-ONLY for spend.** Nothing to poll.
    Google    : no spend method in ANY Cloud Billing version (checked the DISCOVERY DOC, the
                authoritative contract: v1 = CRUD+IAM; v1beta/v2beta = SKU price CATALOG only;
                v1beta1/v2 = 404). BigQuery export is the only documented path.
    Anthropic : /v1/organizations/usage_report/messages exists but is Console-org/API-key only.
                Claude Max + Cowork usage = UI-only. SGH and GEM agree, independently, publisher-tier.
    xAI       : api.x.ai/v1/api-key -> 200 but KEY METADATA only. /v1/usage|billing|credits -> 404.
    Microsoft : consumer M365 Family; Graph is enterprise-only.
  ⇒ THE LOOP (Keith's design): we accumulate a raw internal estimate; he posts the vendor's real
    figure; bts_calibrate converts the ratio into a correction. Vertex measured **2.39x LOW**.

  sgh_api  -> sgh_spend.json      ✅ EXACT (xAI bills cost_in_usd_ticks per call).
  oa_api   -> oa_api_spend.json   ✅ EXACT (OpenAI returns a usage block; bts_oa_api prices it).
                                  Added 2026-08-15. ⚠ THE ONLY POOL THAT FAILS OPEN — auto-reload
                                  is ON, so our own MONTHLY_BUDGET_USD is the whole brake.
  gem_api  -> vertex_usage.json   ⚠ RAW, then x factor from calibration.json. ESTIMATE.
  claude_* -> meters_manual.json  ✋ Keith posts. No ledger exists; Cowork cannot read its own spend.
  sgh_quota-> meters_manual.json  ✋ Keith posts.
  claude_api -> NO DATA BY DESIGN. Cowork runs on the subscription, not an API key.

RULE: a pool with no data emits NOTHING and the pill renders grey "no data".
      **Never emit a plausible number.** The battery this replaces once did
      `used += 300 + random()*1400` every 1.5s and looked completely alive.

  RUN:  python bts_meters.py           -> write meters.json + print
        python bts_meters.py --print   -> just print
"""
import os, sys, json, datetime, calendar

BASE   = r"V:\Research4\Ai\BTS_MESH"
OUT    = os.path.join(BASE, "meters.json")
MANUAL = os.path.join(BASE, "meters_manual.json")   # Keith's posted figures

SGH_LEDGER    = os.path.join(BASE, "sgh_spend.json")
VERTEX_LEDGER = os.path.join(BASE, "vertex_usage.json")
OA_LEDGER     = os.path.join(BASE, "oa_api_spend.json")   # added 2026-08-15 — the SECOND exact meter

SGH_CAP_USD    = 10.0     # hard stop in bts_sgh
VERTEX_CAP_USD = 300.0    # the free-trial credit
VERTEX_EXPIRES = "2026-10-13"

# 🔴 ASK THE MODULE FOR THE CAP. bts_oa_api.MONTHLY_BUDGET_USD is the only brake on an account with
# AUTO-RELOAD ON ($20 -> $50, tier cap $500/mo), so a meter drawn against a hand-copied number would
# show a full tank while the real ceiling had moved. Copies rot; this one would rot expensively.
try:
    sys.path.insert(0, BASE)
    from bts_oa_api import MONTHLY_BUDGET_USD as OA_CAP_USD
except Exception:                                                     # noqa: BLE001
    OA_CAP_USD = 25.0


def _j(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def _month_end_epoch():
    n = datetime.datetime.now()
    last = calendar.monthrange(n.year, n.month)[1]
    return int(datetime.datetime(n.year, n.month, last, 23, 59, 59).timestamp())


def build():
    m = {}
    man = _j(MANUAL, {}) or {}

    # ---- SGH API: the one exact meter on the bar -------------------------------------------------
    s = _j(SGH_LEDGER)
    if s:
        used = (s.get("WORK") or 0) + (s.get("POLL") or 0)
        m["sgh_api"] = {"used": round(used, 4), "cap": SGH_CAP_USD, "unit": "usd",
                        "reset_epoch": _month_end_epoch(), "estimate": False,
                        "src": "sgh_spend.json — EXACT, xAI returns cost_in_usd_ticks per call. "
                               "$10/mo hard stop. Grounded search REFUSED without spend_ok=<usd>."}

    # ---- GEM / Vertex: raw ledger x measured correction ------------------------------------------
    v = _j(VERTEX_LEDGER)
    if v:
        raw = v.get("spend") or 0
        try:
            sys.path.insert(0, BASE)
            from bts_calibrate import calibrated
            c = calibrated("vertex", raw)
            used, fac, st = c["calibrated"], c["factor"], c["state"]
        except Exception:
            used, fac, st = raw, 1.0, "uncalibrated"
        m["gem_api"] = {"used": round(used or 0, 4), "cap": VERTEX_CAP_USD, "unit": "usd",
                        "estimate": True,
                        "src": "vertex_usage.json RAW x %.2fx (%s) from calibration.json. "
                               "RECONCILED 2026-07-16: console $300.00->$299.91 proved the credit "
                               "DOES pay for Vertex; the same read showed our raw ledger runs 2.39x "
                               "LOW. Credit EXPIRES %s — the DATE is the binding limit, not the money."
                               % (fac, st, VERTEX_EXPIRES)}

    # ---- OA API: the SECOND exact meter on the bar ------------------------------------------------
    # EXACT because OpenAI returns a `usage` block per call and bts_oa_api prices it against the
    # measured publisher table — nothing here is estimated or calibrated.
    #
    # 🔴 AND IT IS THE ONE POOL WHOSE CAP IS OURS ALONE. Every other meter on this bar draws against
    # a ceiling the vendor enforces: xAI stops at its $10, the Vertex credit runs out, the Claude
    # spend limit binds. This account AUTO-RELOADS — at $20 it tops back up to $50 against a $500/mo
    # tier cap — so it fails OPEN. `MONTHLY_BUDGET_USD` is the entire brake, which makes this pill
    # the only one on the rack where a full battery means "our own code is still refusing calls"
    # rather than "the vendor will stop us."
    o = _j(OA_LEDGER)
    if o:
        mo = datetime.datetime.utcnow().strftime("%Y-%m")
        calls = [c for c in o.get("calls", []) if str(c.get("ts", "")).startswith(mo)]
        used = sum(c.get("usd", 0.0) for c in calls)
        unmeasured = sum(1 for c in calls if not c.get("cost_measured"))
        reloaded = sum(r.get("usd", 0.0) for r in o.get("reloads", [])
                       if str(r.get("ts", "")).startswith(mo))
        src = ("oa_api_spend.json — EXACT, OpenAI returns a usage block per call and bts_oa_api "
               "prices it against the measured publisher table (terra $2/$12, luna $0.20/$1.20, "
               "sol $5/$30 per MTok). 1.05M context in, 128K max out. %d call(s) this month. "
               "⚠ THE CAP IS OURS, NOT THE ACCOUNT'S: auto-reload is ON ($20 -> $50, tier cap "
               "$500/mo), so this pool fails OPEN and MONTHLY_BUDGET_USD is the only brake. "
               "MAX_CALL_USD $3.50 refuses on the ESTIMATE, before the spend." % len(calls))
        if reloaded:
            src += " Reloads recorded this month: $%.2f (a prepaid top-up is a MOVING ceiling)." % reloaded
        if unmeasured:
            # Never let an unpriced call quietly flatter the battery — bts_gw's 204 unpriced calls
            # sat at $0 for weeks and the meter read healthy the whole time.
            src += (" 🔴 %d call(s) returned NO usage block and are recorded at $0 — this figure "
                    "UNDERSTATES spend. grep cost_measured=false." % unmeasured)
        m["oa_api"] = {"used": round(used, 4), "cap": OA_CAP_USD, "unit": "usd",
                       "reset_epoch": _month_end_epoch(), "estimate": bool(unmeasured), "src": src}

    # ---- Keith's posted figures ------------------------------------------------------------------
    # Shape in meters_manual.json:
    #   {"claude_quota":{"used":1,"cap":100,"unit":"pct","reset_epoch":...},
    #    "claude_credits":{"used":242,"cap":250,"unit":"usd"},
    #    "sgh_quota":{"used":15,"cap":100,"unit":"pct"}}
    for k in ("claude_quota", "claude_credits", "sgh_quota", "claude_api"):
        if k in man and man[k] and man[k].get("used") is not None:
            e = dict(man[k])
            e.setdefault("estimate", False)
            e["src"] = e.get("src", "") + " ✋ POSTED BY KEITH — UI-only, no API exposes this."
            if e.get("posted_at"):
                e["src"] += "  read on %s" % e["posted_at"]
            m[k] = e
    # claude_api: absent on purpose. Cowork runs on the subscription; there is no API key to meter.
    return {"when": datetime.datetime.now().isoformat(timespec="seconds"),
            "_README": ("Feed for KDash's top-bar meter rack. sgh_api and oa_api are EXACT — both "
                        "vendors return per-call usage. gem_api is a calibrated estimate; the "
                        "Claude/SGH quota pools are human-posted, because those vendors are UI-only "
                        "for spend (measured 2026-07-16, re-confirmed for Claude 2026-08-12). "
                        "A pool that is ABSENT here renders grey 'no data' — that is correct, never "
                        "fill it in. ⚠ oa_api is the only pool whose ceiling is OURS: the OpenAI "
                        "account auto-reloads, so it fails OPEN and MONTHLY_BUDGET_USD is the brake."),
            "meters": m}


def main():
    d = build()
    if "--print" not in sys.argv:
        json.dump(d, open(OUT, "w", encoding="utf-8"), indent=1)
    print(json.dumps(d, indent=1))
    miss = [k for k in ("claude_quota", "claude_credits", "sgh_quota") if k not in d["meters"]]
    if miss:
        print("\n  NO DATA (Keith must post): %s" % ", ".join(miss))
        print("  -> edit %s, e.g.  {\"claude_credits\":{\"used\":242,\"cap\":250,\"unit\":\"usd\"}}" % MANUAL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
