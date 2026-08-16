"""
bts_policy.py — the SPEED <-> COST dial.  One knob, and every rail obeys it.

WHAT KEITH ASKED FOR
  "A Speed vs Cost dial on the CONTROL KNOBS (Model vs BUS[API])."

  There are two ways to spend money for speed in this mesh, and the dial trades BOTH:
    MODEL  — a better/harder model and more reasoning_effort. Reasoning tokens bill as OUTPUT
             ($6/1M), so "think harder" is literally a purchase.
    BUS    — the paid API rail (SGH) and its server-side search ($0.005 per search, and the
             model chooses how many). The free rails (GEM, Crossref, ITC) cost nothing but are
             slower, weaker, or narrower.

  So the dial is not cosmetic. Every position below maps to a CONCRETE routing decision, and the
  projected cost/latency at each stop is MEASURED, not invented (see MEASURED, below).

THE ONE THING THAT MAKES THIS SAFE
  Position 0 spends NOTHING. It is not "cheap", it is FREE — GEM + Crossref only, SGH refused.
  With the account auto-reloading $5 at a time, having a hard "spend nothing" stop matters.

MEASURED 2026-07-12 (all real calls; none of these numbers are estimates)
    SGH plain, low effort .............. $0.00044   ~1,600 ms
    SGH plain, CACHED prefix ........... $0.00191   (94% hit; input leg 75% off)
    SGH grounded (2 searches) .......... $0.02943   ~8,000 ms   <- 67x the plain call
    GEM flash (free tier) .............. $0          ~800 ms
    Crossref (DOI truth) ............... $0          ~200 ms
    Vertex 2.5-pro (on the $300 credit)  $0*        ~2,100 ms   (*until the credit expires ~Oct-10)
    Chrome bridge (RETIRED for SGH) .... $0        30,000-90,000 ms
"""
import json, os, time

_HERE = os.path.dirname(os.path.abspath(__file__))
POLICY_FILE = os.path.join(_HERE, "policy.json")

# ---- measured economics. Update ONLY from a real bts_bench run. --------------------------------
MEASURED = {
    "sgh_plain":    {"usd": 0.00044, "ms": 1600},
    "sgh_cached":   {"usd": 0.00191, "ms": 1600},
    "sgh_grounded": {"usd": 0.02943, "ms": 8000},
    "gem":          {"usd": 0.0,     "ms": 800},
    "crossref":     {"usd": 0.0,     "ms": 200},
    "vertex":       {"usd": 0.0,     "ms": 2100},
    # ---- openai-api, added 2026-08-15. Every figure below is read off oa_api_spend.json, which
    # records the API's own usage block — so these are billed truth, not a price-page estimate.
    "oa_luna":      {"usd": 0.00079, "ms": 5400},     # 969 in / 500 out
    "oa_terra":     {"usd": 0.00728, "ms": 4330},     # 1,630 in / 335 out
    "oa_terra_big": {"usd": 1.00561, "ms": 100360},   # 438,135 in / 10,778 out — THE WHOLE RECORD
    "oa_chained":   {"usd": 0.15598, "ms": 32900},    # a follow-up on that record, not resent
}

# 🔴 THE DIAL HAS ONE AXIS AND THIS RAIL HAS TWO — read this before routing anything to OA.
# Speed<->cost is a per-call axis. openai-api's distinguishing property is not that it is fast or
# cheap; it is that it holds 1,050,000 tokens, and NO DIAL POSITION CAN EXPRESS "this payload is
# 438k tokens." A knob that cannot represent the axis a decision turns on will make that decision
# wrong at every position, confidently. So size is handled by an OVERRIDE, below, not by a stop.
#
# The measured ceilings that make it an override rather than a preference:
#   crossref/gem/vertex ... small structured calls; none is a corpus reader
#   sgh / grok-4.5 ........   500,000 tok   $1.47 on the bench job
#   openai-codex ..........   272,000 tok   prepaid, but it CANNOT hold the record
#   openai-api ............ 1,050,000 tok   $1.08 on the same job — cheaper AND twice the reach
# ⇒ Above ~250k tokens the choice is not economic, it is physical: one lane can read it and the
#   others truncate. A truncated read that answers confidently is the worst outcome available, and
#   it is exactly what "the cheapest lane that fits the dial" would produce.
BIG_READ_TOKENS = 250_000


def route_for_size(tokens: int, bias: int = None) -> dict:
    """Which lane can actually READ this? Answered before the dial gets a say.

    Returns {"lane", "forced", "why"}. `forced=True` means the dial was overridden and the caller
    should not treat that as a policy violation — it is the policy.
    """
    tokens = int(tokens or 0)
    if tokens >= 1_050_000:
        return {"lane": None, "forced": True, "tokens": tokens,
                "why": ("%s tokens exceeds EVERY lane in this mesh, openai-api included (1.05M). "
                        "There is no routing answer — the payload must be split or summarized "
                        "first, and a summary-of-a-summary is a different evidentiary object. "
                        "Do not silently truncate." % f"{tokens:,}")}
    if tokens >= BIG_READ_TOKENS:
        return {"lane": "oa_api", "forced": True, "tokens": tokens,
                "why": ("%s tokens: only openai-api holds this in one pass. SGH truncates above "
                        "500k, openai-codex above 272k, and a truncated corpus read still returns "
                        "a confident answer — measured $1.01 for 438k in on terra." % f"{tokens:,}")}
    return {"lane": None, "forced": False, "tokens": tokens,
            "why": "fits every lane; the speed<->cost dial governs normally."}

# ---- the four stops on the dial ----------------------------------------------------------------
# bias 0 = COST (free, slow, safe) ............ bias 100 = SPEED (paid, fast, sharp)
STOPS = [
    {"max": 25,  "name": "FREE",     "col": "#3ddc84",
     "rails": ["crossref", "gem"], "sgh": False, "search": False,
     "effort": "low", "cache": True, "parallel": True, "funded": "free",
     "why": "Spends NOTHING. Crossref for DOI truth (it is registry truth, and it beat grounded "
            "Gemini Pro at citations), GEM for bulk sweeps (it caught 40/40 planted "
            "impossibilities on the free tier). SGH is refused outright.",
     "per_call": lambda: MEASURED["gem"]["usd"],
     "lat": lambda: MEASURED["gem"]["ms"]},

    {"max": 50,  "name": "THRIFTY",  "col": "#8b7cff",
     "rails": ["crossref", "vertex", "gem", "sgh"], "sgh": True, "search": False,
     "effort": "low", "cache": True, "parallel": True, "prefer": "vertex", "funded": "credit",
     # *** REWRITTEN 2026-07-15. The old text asserted VERTEX is "free-to-us on the $300 credit"
     # and that the credit "EXPIRES 2026-10-10". BOTH WERE FALSE: the account it referred to
     # (0142FE) never held a credit — bts_vertex was charging a real card — and the new account's
     # expiry (~2026-10-13) is COMPUTED, not read. Worse, "free-to-us" is still UNPROVEN even now:
     # no Google page states the $300 covers Agent Platform. per_call: 0.0 below encodes that
     # unproven assumption as a hard number, which is exactly how the $299 phantom was born.
     "why": "Adds SGH but WITHOUT search. Prefers VERTEX first. ⚠ VERTEX IS ONLY FREE-TO-US IF THE "
            "$300 CREDIT ACTUALLY COVERS AGENT PLATFORM — that is INFERRED (from a two-item "
            "exclusion list), NOT stated by Google, and NOT YET VERIFIED. Confirm in Billing→Reports: "
            "'Other savings' negative + Subtotal $0.00 = the credit paid. If it does not, every "
            "Vertex call here is billing Joanna's card at gemini-2.5-pro rates ($1.25/$10 per 1M). "
            "The credit expires ~2026-10-13 [COMPUTED, read Billing→Overview to confirm] and does "
            "not renew. SGH is the fallback at $0.00044/call. Prompt caching on.",
     # per_call 0.0 = "the credit pays". UNPROVEN — see above. Not 'free', just 'not yet measured'.
     "per_call": lambda: 0.0,
     "lat": lambda: MEASURED["vertex"]["ms"]},

    {"max": 75,  "name": "FAST",     "col": "#ffb020",
     "rails": ["sgh", "vertex", "gem", "oa_api"], "sgh": True, "search": True,
     "effort": "low", "cache": True, "parallel": True, "max_tool_calls": 4, "funded": "cash",
     "why": "Turns SEARCH on. This is the expensive step, not the model: a grounded call is "
            "$0.029 — 67x a plain one — because search injects ~10k tokens AND bills $0.005 per "
            "search. Worth it only when the answer needs FRESH web/X knowledge.",
     "per_call": lambda: MEASURED["sgh_grounded"]["usd"],
     "lat": lambda: MEASURED["sgh_grounded"]["ms"]},

    {"max": 100, "name": "MAX",      "col": "#ff4d4d",
     "rails": ["sgh", "vertex", "oa_api"], "sgh": True, "search": True,
     "effort": "high", "cache": True, "parallel": True, "max_tool_calls": 8, "funded": "cash",
     "why": "High reasoning_effort AND search. Reasoning tokens bill as OUTPUT at $6/1M, so this "
            "buys correctness with money. Reserve for adversarial audits and must-be-right "
            "verification — the class of work where Vertex Pro re-derived Ch4's own argument.",
     "per_call": lambda: MEASURED["sgh_grounded"]["usd"] * 2.5,   # high effort ~ more reasoning
     "lat": lambda: MEASURED["sgh_grounded"]["ms"] * 1.6},
]

DEFAULT = {"bias": 40}          # THRIFTY — cheap, no search, caching on


def _stop(bias: int) -> dict:
    for s in STOPS:
        if bias <= s["max"]:
            return s
    return STOPS[-1]


def load() -> dict:
    try:
        d = json.load(open(POLICY_FILE))
    except Exception:
        d = dict(DEFAULT)
    d.setdefault("bias", DEFAULT["bias"])
    return d


def save(bias: int) -> dict:
    bias = max(0, min(100, int(bias)))
    d = {"bias": bias, "ts": int(time.time())}
    tmp = POLICY_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=1)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, POLICY_FILE)
    return resolve(bias)


def resolve(bias: int = None) -> dict:
    """The dial position -> the concrete settings every rail should obey."""
    if bias is None:
        bias = load()["bias"]
    bias = max(0, min(100, int(bias)))
    s = _stop(bias)
    usd, ms = s["per_call"](), s["lat"]()
    return {
        "bias": bias,
        "name": s["name"],
        "col": s["col"],
        "rails": s["rails"],
        "sgh": s["sgh"],
        "search": s["search"],
        "effort": s["effort"],
        "cache": s["cache"],
        "parallel": s["parallel"],
        "max_tool_calls": s.get("max_tool_calls", 4),
        "why": s["why"],
        # projections, from MEASURED values — the whole point of the dial is that you can SEE
        # what a position costs before you turn it.
        "proj_usd_per_call": round(usd, 5),
        "proj_ms": int(ms),
        "proj_calls_per_10usd": (int(10.0 / usd) if usd > 0 else None),
        # THREE funding classes, not two. Collapsing "free" and "credit-funded" into one "free"
        # would be a lie: the $300 credit is real money that EXPIRES 2026-10-13. Calling it free
        # invites exactly the complacency that leaves $300 on the table.
        #   free   -> costs nothing, ever (Crossref, and GEM when AI Studio is healthy)
        #   credit -> costs nothing TO KEITH until Oct-10, then it is gone (Vertex)
        #   cash   -> real dollars out of the $10/mo (SGH)
        "funded": s.get("funded", "cash"),
        "free": s.get("funded") == "free",
    }


def apply_to_ask(kwargs: dict = None, bias: int = None) -> dict:
    """Fold the current dial position into a bts_sgh.ask() kwargs dict.
       Explicit kwargs the CALLER passed always win — the dial is a default, not a cage."""
    p = resolve(bias)
    out = dict(kwargs or {})
    out.setdefault("search", p["search"])
    out.setdefault("reasoning_effort", p["effort"])
    out.setdefault("max_tool_calls", p["max_tool_calls"])
    return out


def sgh_allowed(bias: int = None) -> bool:
    """At bias 0-25 (FREE) the paid rail is refused outright. Spend-nothing is a real stop."""
    return resolve(bias)["sgh"]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(json.dumps(save(int(sys.argv[1])), indent=1))
    else:
        print("SPEED <-> COST dial\n")
        print("  %-4s %-8s %-9s %-8s %-7s %s" % ("bias", "stop", "$/call", "latency", "per $10", "search"))
        for b in (0, 25, 40, 50, 75, 100):
            p = resolve(b)
            per = "unlimited" if p["proj_calls_per_10usd"] is None else "{:,}".format(p["proj_calls_per_10usd"])
            print("  %-4d %-8s $%-8.5f %-8s %-7s %s"
                  % (b, p["name"], p["proj_usd_per_call"], "%d ms" % p["proj_ms"], per,
                     "ON" if p["search"] else "off"))
        cur = resolve()
        print("\n  CURRENT: bias=%d (%s)\n  %s" % (cur["bias"], cur["name"], cur["why"]))
