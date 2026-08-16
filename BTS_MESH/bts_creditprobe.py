r"""
bts_creditprobe — SPEND REAL MONEY ON PURPOSE, TO SETTLE ONE QUESTION.
================================================================================
Keith, 2026-07-16: "And you haven't spent a penny of the credit, let's spend some
to check it, it's a NON billable account, so there's zero risk."

THE QUESTION (the last unresolved [G] in GEMINI_TOPOLOGY_CORRECTION_2026-07-15.md):
    *** DOES THE $300 FREE-TRIAL CREDIT ACTUALLY PAY FOR VERTEX / AGENT PLATFORM? ***
No Google page states it. It was once ASSERTED here, then WITHDRAWN as "inferred
from the absence of a third exclusion." The dashboard still labels the rail
"credit-funded" on that withdrawn inference.

WHY A PROBE AND NOT AN ARGUMENT
-------------------------------
Our whole spend to date is $0.0002526 — which ROUNDS TO $0.00 in the console. That
is why "Welcome, jo anna — $0 out of $300 credits used" settles NOTHING: it reads
identically whether the credit is paying or a card is. To see the answer we must
spend enough to CLEAR ROUNDING, then read Billing -> Reports:

    "Other savings"  NEGATIVE   -> the credit paid.        <- what we want to see
    "Usage cost" > 0, savings 0 -> the credit does NOT pay for Agent Platform,
                                   and every Vertex call has been billing something
                                   else. (This is exactly what happened on the old
                                   0142FE account: ~$1 of REAL CARD money while
                                   every docstring here claimed "$300 credit".)

WHY THE RISK IS ZERO (Keith's reasoning, and it is correct)
-----------------------------------------------------------
Billing 010E47-824B53-7202F5 is a FREE TRIAL account that has NOT been Activated.
Google: you are billed only beyond credit + Free Tier, and an un-activated trial
has no card behind it -- it auto-closes at day 90 instead of charging. So the worst
case is a 429/403, NOT a surprise bill. This is the OPPOSITE of the deleted 0142FE
account, which was Paid-from-day-one.

WHAT IT BUYS BESIDES THE ANSWER
-------------------------------
Vertex's real throughput ceiling has NEVER been measured. The "429'd after ~18
calls" figure in the ROLD is the AI STUDIO FREE TIER -- a different rail. This probe
records latency and any 429/RESOURCE_EXHAUSTED per call, so the burn also produces
the first real Vertex rate-limit measurement instead of pure waste.

RUN:  python bts_creditprobe.py [--usd 1.00] [--dry]
      --dry prints the plan and spends NOTHING.
================================================================================
"""
import sys, os, time, json, datetime

sys.path.insert(0, r"V:\Research4\Ai\BTS_MESH")

OUT = r"V:\Research4\Ai\BTS_MESH\_creditprobe_result.json"
LOG = r"V:\Research4\Ai\BTS_MESH\_creditprobe_log.txt"

# gemini-2.5-pro on Agent Platform, per 1M tokens (from GEMINI_TOPOLOGY_CORRECTION §5).
PRICE_IN, PRICE_OUT = 1.25, 10.00

TARGET_USD = 1.00
DRY = "--dry" in sys.argv
if "--usd" in sys.argv:
    TARGET_USD = float(sys.argv[sys.argv.index("--usd") + 1])

# A prompt engineered to produce a LOT of output tokens -- output is 8x the price of
# input, so output is the efficient way to move the meter. It is deliberately a real
# question about our own domain, so the returns are readable rather than noise.
PROMPT = (
    "Write a detailed technical explanation, at least 1200 words, of ultraviolet "
    "photoelectron spectroscopy (UPS) of conjugated polymer thin films. Cover: the "
    "photoemission process and the three-step model; work function and the "
    "secondary-electron cutoff; the He-I 21.22 eV source; binding-energy referencing "
    "to the Fermi edge of a metal; sample charging in insulating films and how bias "
    "is applied to correct it; interface dipoles and energy-level alignment; and the "
    "distinction between the transport gap and the optical gap. Be precise and "
    "quantitative wherever possible."
)

def log(s):
    print(s)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(s + "\n")

def main():
    est_per_call = (250 * PRICE_IN + 2000 * PRICE_OUT) / 1e6
    n_calls = max(1, int(round(TARGET_USD / est_per_call)))

    log("=" * 78)
    log("CREDIT PROBE  %s" % datetime.datetime.now().isoformat(timespec="seconds"))
    log("  target spend      : $%.2f" % TARGET_USD)
    log("  est $/call        : $%.5f  (~250 in @ $%.2f/1M, ~2000 out @ $%.2f/1M)"
        % (est_per_call, PRICE_IN, PRICE_OUT))
    log("  planned calls     : %d" % n_calls)
    log("  billing account   : 010E47-824B53-7202F5 (Joanna, FREE TRIAL, not activated)")
    log("  project           : project-5a33f910-1251-4d6a-bf9")
    log("  risk              : none -- un-activated trial has no card; worst case is 429/403")
    log("=" * 78)
    if DRY:
        log("--dry -> spending NOTHING. Exiting.")
        return 0

    import bts_vertex

    results, spend, tin, tout, errors = [], 0.0, 0, 0, 0
    t_start = time.time()

    for i in range(n_calls):
        t0 = time.time()
        try:
            # *** BUG, 2026-07-16: this first read `bts_vertex.ask(PROMPT, spend_ok=...)`.
            # bts_vertex.ask() HAS NO spend_ok PARAMETER -- that is bts_sgh's governor arg. Result:
            # 49 instant TypeErrors in 0.1s, $0 spent. Signature is
            #     ask(prompt, grounded=False, retries=3, images=None, model=None)
            # Two rails, two different signatures; do not assume they match.
            # model= is explicit: bts_vertex's ladder is PRO-FIRST by default, and Pro is what we
            # WANT here -- it is 4x flash ($1.25/$10 vs $0.30/$2.50 per 1M), so it clears the
            # console's rounding fastest, which is the entire point of this probe.
            r = bts_vertex.ask(PROMPT, model="gemini-2.5-pro")
        except Exception as e:
            # Keep the MESSAGE. The first version stored only reason="EXC" and threw the text away,
            # so 49 identical failures said nothing about why. An error you cannot read is not a result.
            r = {"ok": False, "reason": "EXC: " + type(e).__name__ + ": " + str(e)[:160], "text": None}
        dt = time.time() - t0

        ok = bool(r.get("ok"))
        u = r.get("usage") or {}
        ci = u.get("prompt_token_count") or u.get("input_tokens") or 0
        co = u.get("candidates_token_count") or u.get("output_tokens") or 0
        c = r.get("cost_usd")
        if c is None:
            c = (ci * PRICE_IN + co * PRICE_OUT) / 1e6

        if ok:
            spend += c; tin += ci; tout += co
        else:
            errors += 1

        results.append({"i": i, "ok": ok, "reason": r.get("reason"),
                        "ms": round(dt * 1000), "in": ci, "out": co,
                        "usd": round(c, 6), "model": r.get("model")})
        log("  [%2d/%2d] %-4s %5dms  in=%-5d out=%-5d  $%.5f  cum=$%.4f  %s"
            % (i + 1, n_calls, "OK" if ok else "FAIL", dt * 1000, ci, co, c, spend,
               "" if ok else str(r.get("reason"))[:90]))

        # STOP EARLY on a rate limit -- that is a FINDING (the first real Vertex
        # ceiling measurement), not a failure to paper over.
        if not ok and str(r.get("reason", "")).upper().find("EXHAUST") >= 0:
            log("  *** RATE LIMITED after %d successful calls -- this is the measurement. ***" % (i - errors + 1))
            break
        # BAIL on a wall of identical instant failures. The first run of this script fired all 49
        # TypeErrors in 0.1s because of a bad signature -- a fast failure loop is a BUG, not a probe.
        if errors >= 3 and (len(results) - errors) == 0:
            log("  *** 3 failures, 0 successes -- aborting. This is a code fault, not a billing answer. ***")
            log("  *** reason: %s" % str(r.get("reason"))[:160])
            break
        if spend >= TARGET_USD:
            log("  target reached.")
            break

    elapsed = time.time() - t_start
    summary = {
        "when": datetime.datetime.now().isoformat(timespec="seconds"),
        "calls_attempted": len(results),
        "calls_ok": len(results) - errors,
        "errors": errors,
        "tokens_in": tin, "tokens_out": tout,
        "spend_est_usd": round(spend, 6),
        "elapsed_s": round(elapsed, 1),
        "billing_account": "010E47-824B53-7202F5",
        "project": "project-5a33f910-1251-4d6a-bf9",
        "_THIS_IS_AN_ESTIMATE": (
            "spend_est_usd is OUR OWN token arithmetic (PRICES x usage), the same class of number "
            "that produced the $299 phantom. It is NOT a read of Google's billing. Its ONLY job is "
            "to be BIG ENOUGH TO SEE in the console. GROUND TRUTH = Billing -> Reports, ~24h lag: "
            "'Other savings' NEGATIVE = the $300 paid for Agent Platform (question answered YES); "
            "'Usage cost' > 0 with no savings = the credit does NOT cover Vertex (answered NO, and "
            "the dashboard's 'credit-funded' label is wrong and must come off)."),
        "results": results,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)

    log("-" * 78)
    log("  calls OK          : %d / %d   (errors %d)" % (len(results) - errors, len(results), errors))
    log("  tokens            : %d in / %d out" % (tin, tout))
    log("  ESTIMATED spend   : $%.4f   <- our arithmetic, NOT Google's" % spend)
    log("  elapsed           : %.1fs" % elapsed)
    log("  wrote             : %s" % OUT)
    log("")
    log("  NEXT (Keith, ~24h): Billing -> Reports, account 010E47-824B53-7202F5")
    log("     'Other savings' NEGATIVE  -> credit PAYS for Vertex. Label is right.")
    log("     'Usage cost' > 0, no savings -> credit does NOT. Strip 'credit-funded'.")
    log("=" * 78)
    return 0

if __name__ == "__main__":
    sys.exit(main())
