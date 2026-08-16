r"""
bts_calibrate — CLOSED-LOOP SPEND CALIBRATION.  Keith's design, 2026-07-16:
  "That means you track tokens and cents internally and I post update periodically
   that you use as feedback signals to recalibrate."

WHY THIS IS THE ONLY METER THAT CAN EXIST
-----------------------------------------
MEASURED 2026-07-16: **all four vendors are UI-ONLY for spend.** There is no endpoint to poll.
  Google Cloud : NO spend method in ANY API version. Checked the DISCOVERY DOC, which is the
                 authoritative contract: v1 = create/move/get/patch/list/IAM only; v1beta + v2beta =
                 SKU price CATALOG only (what a SKU costs, NOT what you spent); v1beta1/v2 = 404.
                 Only documented path = BigQuery billing export (24h lag, storage+query cost).
  Anthropic    : /v1/organizations/usage_report/messages EXISTS but is Console-org / API-key only.
                 Claude MAX subscription + Cowork usage = UI-only. SGH and GEM agree independently.
  xAI          : api.x.ai/v1/api-key -> 200 but KEY METADATA ONLY (team_id, acls, blocked flags).
                 /v1/usage, /v1/billing, /v1/credits, all management-api.x.ai/* -> 404.
  Microsoft    : M365 Family consumer licence. Graph is enterprise-only.
⇒ Polling is impossible. But we DO have a high-frequency internal estimate, and Keith can read the
  real number off a page. Fuse them: **estimate = fast + biased. Console = slow + true.
  ratio = the correction factor.** Classic drift correction. That is this module.

THE BIAS IS REAL AND LARGE — first reconciliation, 2026-07-16:
    our ledger (PRICES x usageMetadata) : $0.037731
    Google's console ($300.00 -> $299.91): $0.09
    ratio                               : **2.39x LOW**
Suspected cause (UNVERIFIED — do not assert): uncounted reasoning/thinking tokens on 2.5-pro, or
minimum billing units, or per-call overhead absent from usageMetadata.

THE RULES THIS ENFORCES
  1. A RAW estimate is a LOWER BOUND, never a measurement. It may never carry a tick.
  2. A CALIBRATED estimate is still an ESTIMATE — it just has a measured correction applied.
  3. Calibration DECAYS. A factor from 3 weeks ago describes a model mix that no longer exists.
     Anything past STALE_DAYS renders STALE. Never let an old factor look fresh.
  4. UNCALIBRATED rails report factor=1.0 and say so. **We do not invent a factor.** That is the
     exact sin of the $299 phantom: an unmeasured number wearing a measured number's clothes.

USE
  python bts_calibrate.py                              -> show the table
  python bts_calibrate.py vertex --actual 0.09         -> Keith posts Google's figure; recalibrate
  python bts_calibrate.py claude --actual 242 --cap 250 -> Keith posts the Claude usage page
  from bts_calibrate import calibrated, factor, report
"""
import os, sys, json, datetime

STATE = r"V:\Research4\Ai\BTS_MESH\calibration.json"
STALE_DAYS = 14          # a factor older than this describes a model mix that has moved on

RAILS = {
    "vertex": {"unit": "usd", "ledger": r"V:\Research4\Ai\BTS_MESH\vertex_usage.json",
               "ledger_key": "spend",
               "source": "console banner: 'Free trial status: $X credit and N days remaining' "
                         "(https://console.cloud.google.com/billing?authuser=2) -> actual = 300 - X"},
    "sgh":    {"unit": "usd", "ledger": r"V:\Research4\Ai\BTS_MESH\sgh_spend.json",
               "ledger_key": "WORK",
               "source": "console.x.ai billing page. NOTE xAI reports cost_in_usd_ticks EXACTLY per "
                         "call, so this rail may already be truth (expected factor ~1.0). "
                         "MEASURE IT — do not assume."},
    "claude": {"unit": "usd", "ledger": None,
               "source": "Claude usage page: credits $ spent + monthly cap + weekly quota %. "
                         "NO ledger — Cowork cannot read its own spend. Keith posts it or it is blank."},
    "gem":    {"unit": "req", "ledger": r"V:\Research4\Ai\BTS_MESH\gem_quota.json",
               "ledger_key": "WORK",
               "source": "AI Studio (auth-gated). Free tier is DEAD (429 prepay) — GEM rides Vertex, "
                         "so its COST lands on the vertex rail, not here."},
}


def _load():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except Exception:
            pass
    return {"_README": "Closed-loop spend calibration. Keith posts the vendor's own figure; we "
                       "compute the correction for our internal estimate. ALL FOUR VENDORS ARE "
                       "UI-ONLY for spend (measured 2026-07-16) — there is nothing to poll, so this "
                       "human-in-the-loop signal is the ONLY ground truth that exists.",
            "rails": {}}


def _save(d):
    json.dump(d, open(STATE, "w", encoding="utf-8"), indent=1)


def _ledger_estimate(rail):
    """Our internal running estimate for this rail, or None if it has no ledger."""
    cfg = RAILS.get(rail) or {}
    p = cfg.get("ledger")
    if not p or not os.path.exists(p):
        return None
    try:
        d = json.load(open(p, encoding="utf-8"))
        return d.get(cfg.get("ledger_key"))
    except Exception:
        return None


def record(rail, actual, est=None, note=""):
    """Keith posts the vendor's real figure -> recompute this rail's correction factor."""
    d = _load()
    r = d["rails"].setdefault(rail, {"samples": []})
    if est is None:
        est = _ledger_estimate(rail)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    ratio = (actual / est) if (est and est > 0) else None
    r["samples"].append({"t": now, "est": est, "actual": actual, "ratio": ratio, "note": note})
    # Use the LATEST ratio, not a mean: pricing and model mix change, and an average would drag a
    # current factor toward a stale regime. Keep the history for the trend, act on the newest.
    if ratio:
        r["factor"] = round(ratio, 4)
        r["last_reconciled"] = now
    r["source"] = (RAILS.get(rail) or {}).get("source", "")
    _save(d)
    return r


def factor(rail):
    """(factor, state) — state in {'ok','stale','uncalibrated'}. NEVER invents a factor."""
    d = _load()
    r = (d.get("rails") or {}).get(rail)
    if not r or not r.get("factor"):
        return 1.0, "uncalibrated"
    try:
        age = (datetime.datetime.now()
               - datetime.datetime.fromisoformat(r["last_reconciled"])).days
    except Exception:
        return r["factor"], "stale"
    return r["factor"], ("ok" if age <= STALE_DAYS else "stale")


def calibrated(rail, raw=None):
    """Apply the measured correction. Returns a dict that CANNOT be mistaken for a measurement."""
    if raw is None:
        raw = _ledger_estimate(rail)
    f, st = factor(rail)
    return {"rail": rail, "raw": raw,
            "calibrated": (round(raw * f, 6) if isinstance(raw, (int, float)) else None),
            "factor": f, "state": st,
            "_is_estimate": True,
            "_note": ("CALIBRATED ESTIMATE — still an estimate, with a measured correction applied."
                      if st == "ok" else
                      "STALE factor (>%dd) — the model mix has probably moved. Ask Keith to re-post."
                      % STALE_DAYS if st == "stale" else
                      "UNCALIBRATED — raw ledger, known to run LOW (vertex measured 2.39x low). "
                      "This is a LOWER BOUND. Do not decide on it.")}


def report():
    d = _load()
    out = []
    out.append("=" * 84)
    out.append("  SPEND CALIBRATION — all four vendors are UI-ONLY; Keith's posts are the only truth")
    out.append("=" * 84)
    out.append("  %-8s %-12s %-12s %-8s %-12s %s" % ("rail", "our est", "calibrated", "factor", "state", "last reconciled"))
    out.append("  " + "-" * 80)
    for rail in RAILS:
        c = calibrated(rail)
        r = (d.get("rails") or {}).get(rail) or {}
        raw = c["raw"]
        out.append("  %-8s %-12s %-12s %-8s %-12s %s" % (
            rail,
            ("%.4f" % raw) if isinstance(raw, (int, float)) else "-- none --",
            ("%.4f" % c["calibrated"]) if c["calibrated"] is not None else "--",
            "%.2fx" % c["factor"],
            c["state"].upper(),
            r.get("last_reconciled", "never")))
    out.append("")
    out.append("  vertex: reconciled 2026-07-16 — ours $0.037731 vs Google $0.09 = 2.39x LOW.")
    out.append("  claude: NO ledger exists. Cowork cannot read its own spend. Keith posts, or it is blank.")
    out.append("  TO RECALIBRATE:  python bts_calibrate.py <rail> --actual <number>")
    out.append("=" * 84)
    return "\n".join(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(report()); sys.exit(0)
    rail = args[0]
    if rail not in RAILS:
        print("unknown rail %r — known: %s" % (rail, ", ".join(RAILS))); sys.exit(2)
    actual = None
    if "--actual" in args:
        actual = float(args[args.index("--actual") + 1])
    if actual is None:
        print(json.dumps(calibrated(rail), indent=1)); sys.exit(0)
    # --est: pass the estimate EXPLICITLY when the ledger has already been reconciled-in.
    # (2026-07-16: vertex_usage.json's `spend` was SET to Google's 0.09, so reading the ledger here
    #  would compare 0.09 against 0.09 and record a factor of 1.00x — silently erasing the 2.39x
    #  finding it exists to capture. A calibrator that reads a value it already corrected measures
    #  nothing but its own echo.)
    est = float(args[args.index("--est") + 1]) if "--est" in args else None
    note = args[args.index("--note") + 1] if "--note" in args else ""
    r = record(rail, actual, est=est, note=note)
    print("  recorded: %s actual=%s est=%s -> factor %sx"
          % (rail, actual, r["samples"][-1]["est"], r.get("factor")))
    print()
    print(report())
