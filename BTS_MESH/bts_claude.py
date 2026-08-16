"""
bts_claude.py — the COWORK wallet.  An ESTIMATOR THAT GRADES ITSELF.

THE PROBLEM
  Claude Max is the biggest wallet in the mesh (~$442 this month: $200 sub + $242.64 usage credits)
  and the ONLY one with no ceiling — "Monthly spend limit: Unlimited", auto-reload ON. It is also
  the only one with no programmatic quota endpoint. Cowork cannot read its own meter.

KEITH'S DESIGN (2026-07-12), and it is the right one:
  "Cowork estimates all numbers/burn rates. I occasionally paste the real numbers and you adjust to
   be more accurate. After a few cycles, it should be pretty accurate."

  That is precisely the loop that fixed the SGH cost engine today: guess -> compare against ground
  truth -> correct -> re-verify. It worked there (the first estimate underbilled by 2.7%; after
  calibration the token math reproduces xAI's own figure to the cent).

*** THE ONE RULE THAT SEPARATES THIS FROM THE FAKE BATTERY ***
  The dashboard's old token battery was a random-number generator with a percentage sign on it. An
  estimate is NOT that — PROVIDED it is anchored to real observations, corrected against ground
  truth, and HONEST ABOUT ITS OWN ERROR.

  So this module does something the battery never did: **every time Keith pastes real numbers, it
  scores its own last prediction.** It reports "I predicted $X, actual was $Y, I was off by Z%" and
  carries that error forward as the confidence on the next estimate. After a few cycles you do not
  have to take its accuracy on faith — you can read its track record.

  If it has never been calibrated, it says so and shows NO number. An uncalibrated estimator with a
  confident bar is exactly the thing we are replacing.

WHAT IT ESTIMATES
  Burn rate ($/day) between calibration points, projected to the next reset (usage credits reset on
  the 1st). It does NOT try to count tokens in-session — Cowork cannot see its own token meter, and
  inventing a token count would be fabrication. Dollars-per-day between two real observations is a
  measurement, not a guess, and it is all the projection needs.

USAGE
  python bts_claude.py                       # show current estimate + accuracy history
  python bts_claude.py --calibrate 242.64 --balance 148.24
                                             # paste the real numbers; it grades its last prediction
  python bts_claude.py --calibrate 242.64 --balance 148.24 --week 5 --session 0
"""
import json, os, sys, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "claude_budget.json")

SUB_USD_MONTH = 200.00      # Max 20x subscription — fixed, not part of the variable burn
RESET_DAY = 1               # usage credits reset on the 1st (per Keith's page: "Resets Aug 1")


def _today():
    return datetime.date.today()


def _next_reset(d=None):
    d = d or _today()
    if d.day < RESET_DAY:
        return d.replace(day=RESET_DAY)
    nxt = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=RESET_DAY)
    return nxt


def _load():
    try:
        return json.load(open(LEDGER, encoding="utf-8"))
    except Exception:
        return {"samples": [], "predictions": []}


def _save(d):
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, LEDGER)


# ================================================================================================
def calibrate(spent, balance=None, week_pct=None, session_pct=None, when=None):
    """Keith pastes the REAL numbers. We grade our last prediction against them, then re-fit.

    This is the whole point of the module: it is not asking to be believed, it is showing its
    work. Each calibration produces an accuracy record that the estimate then carries."""
    d = _load()
    now = (when or _today()).isoformat()

    # ---- GRADE THE LAST PREDICTION, if we made one -------------------------------------------
    graded = None
    open_preds = [p for p in d.get("predictions", []) if not p.get("graded")]
    if open_preds:
        p = open_preds[-1]
        pred = p["predicted_spent"]
        err = spent - pred
        pct = (abs(err) / spent * 100.0) if spent else 0.0
        p["graded"] = True
        p["actual_spent"] = round(spent, 2)
        p["error_usd"] = round(err, 2)
        p["error_pct"] = round(pct, 1)
        p["graded_on"] = now
        graded = p

    d.setdefault("samples", []).append({
        "date": now,
        "spent": round(float(spent), 2),
        "balance": (round(float(balance), 2) if balance is not None else None),
        "week_pct": week_pct,
        "session_pct": session_pct,
    })
    _save(d)
    return {"graded": graded, "samples": len(d["samples"])}


def estimate(record=True):
    """Current burn rate + projection. Returns confidence based on its OWN track record."""
    d = _load()
    s = d.get("samples", [])

    if not s:
        return {"ok": False, "reason": "NEVER_CALIBRATED",
                "note": "No real numbers pasted yet. Showing NOTHING rather than a plausible bar — "
                        "an uncalibrated estimator with a confident percentage is exactly the fake "
                        "battery we are replacing. Run: python bts_claude.py --calibrate <spent>"}

    last = s[-1]
    last_date = datetime.date.fromisoformat(last["date"])
    today = _today()
    reset = _next_reset(today)

    # ---- burn rate: measured between the two most recent REAL observations -------------------
    burn, basis = None, None
    if len(s) >= 2:
        prev = s[-2]
        pd_ = datetime.date.fromisoformat(prev["date"])
        days = (last_date - pd_).days
        # if the reset fell between samples, spent RESET to 0 -> that delta is meaningless
        if days > 0 and last["spent"] >= prev["spent"]:
            burn = (last["spent"] - prev["spent"]) / days
            basis = "measured between the last two calibrations (%d days)" % days
    if burn is None:
        # single sample: spread spend over the days elapsed this billing period
        period_start = reset - datetime.timedelta(days=30)
        days = max(1, (last_date - period_start).days)
        burn = last["spent"] / days
        basis = "single sample — averaged over %d days of the period (WEAK)" % days

    days_to_reset = max(0, (reset - today).days)
    days_since = (today - last_date).days
    projected_now = last["spent"] + burn * days_since
    projected_at_reset = last["spent"] + burn * (days_since + days_to_reset)

    # ---- CONFIDENCE = our own historical error. Not a vibe. -----------------------------------
    graded = [p for p in d.get("predictions", []) if p.get("graded")]
    if graded:
        errs = [abs(p["error_pct"]) for p in graded[-5:]]
        mean_err = sum(errs) / len(errs)
        conf = "±%.0f%% (from %d graded prediction%s)" % (mean_err, len(graded),
                                                          "" if len(graded) == 1 else "s")
    else:
        mean_err = None
        conf = "UNGRADED — no prediction has been checked against reality yet"

    out = {
        "ok": True,
        "last_real": last["spent"],
        "last_real_date": last["date"],
        "days_since_calibration": days_since,
        "balance": last.get("balance"),
        "burn_per_day": round(burn, 2),
        "burn_basis": basis,
        "estimated_spent_now": round(projected_now, 2),
        "projected_at_reset": round(projected_at_reset, 2),
        "reset": reset.isoformat(),
        "days_to_reset": days_to_reset,
        "sub_usd_month": SUB_USD_MONTH,
        "projected_total_month": round(projected_at_reset + SUB_USD_MONTH, 2),
        "samples": len(s),
        "graded": len(graded),
        "mean_error_pct": (round(mean_err, 1) if mean_err is not None else None),
        "confidence": conf,
        "is_estimate": True,          # THE DASHBOARD MUST SAY SO. Always.
        "uncapped": True,             # no spend ceiling, auto-reload ON
    }

    # record this projection so the NEXT calibration can grade it
    if record:
        d.setdefault("predictions", []).append({
            "made_on": today.isoformat(),
            "predicted_spent": out["projected_at_reset"],
            "for_date": reset.isoformat(),
            "graded": False,
        })
        _save(d)
    return out


# ================================================================================================
if __name__ == "__main__":
    a = sys.argv[1:]
    if "--calibrate" in a:
        i = a.index("--calibrate")
        spent = float(a[i + 1])
        get = lambda f: (float(a[a.index(f) + 1]) if f in a else None)
        r = calibrate(spent, balance=get("--balance"),
                      week_pct=get("--week"), session_pct=get("--session"))
        print("CALIBRATED — real numbers recorded (sample #%d)\n" % r["samples"])
        g = r["graded"]
        if g:
            print("  GRADING MY LAST PREDICTION:")
            print("    I predicted : $%.2f" % g["predicted_spent"])
            print("    Actual      : $%.2f" % g["actual_spent"])
            print("    Error       : $%+.2f  (%.1f%%)" % (g["error_usd"], g["error_pct"]))
            print()
        else:
            print("  (no open prediction to grade — this is the baseline sample)\n")

    e = estimate()
    if not e["ok"]:
        print(e["note"])
        sys.exit(0)

    print("COWORK / CLAUDE WALLET   *** ESTIMATE ***")
    print("  last REAL number   : $%.2f   (pasted %s, %d days ago)"
          % (e["last_real"], e["last_real_date"], e["days_since_calibration"]))
    print("  burn rate          : $%.2f/day" % e["burn_per_day"])
    print("                       %s" % e["burn_basis"])
    print("  estimated NOW      : $%.2f" % e["estimated_spent_now"])
    print("  projected @ reset  : $%.2f   (%s, %d days)"
          % (e["projected_at_reset"], e["reset"], e["days_to_reset"]))
    print("  + subscription     : $%.2f" % e["sub_usd_month"])
    print("  PROJECTED MONTH    : $%.2f" % e["projected_total_month"])
    print()
    print("  confidence         : %s" % e["confidence"])
    print("  samples/graded     : %d / %d" % (e["samples"], e["graded"]))
    print()
    print("  ** UNCAPPED WALLET — 'Monthly spend limit: Unlimited', auto-reload ON. **")
    print("  ** This is an ESTIMATE. Paste real numbers to improve it:")
    print("     python bts_claude.py --calibrate <spent> --balance <bal>")
