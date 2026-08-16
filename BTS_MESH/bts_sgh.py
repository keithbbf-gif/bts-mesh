"""
bts_sgh.py — SGH node, xAI Grok API rail.  RETIRES the browser-driven grok.com node.

WHY THIS EXISTS
  SGH has been driven through the Chrome bridge: zip-only uploads, content-filtered code blocks
  (BUILD-7/BUILD-10 were authored and then LOST because the scraper could not read them), and
  send-verification failures. This is a real API. No browser, no scraping, no fake-DONE.

LIVE-VERIFIED 2026-07-12 (two real calls; every number below was measured, not assumed):
  * grok-4.5, 500k context, knowledge cutoff 2026-02-01.
  * ENDPOINT = /v1/responses.  *** /v1/chat/completions IS LEGACY AND CANNOT SEARCH: *** it 422s
    with "unknown variant `web_search`, expected `function` or `live_search`". Do not switch back.
  * Server-side Web Search works and is what makes SGH the mesh's web+X node.
  * Grok has NO realtime knowledge unless a search tool is enabled (docs, verbatim).

*** THE GOVERNOR COUNTS DOLLARS, NOT REQUESTS. ***
  bts_gem.py governs a FREE tier, so it counts requests against a daily allowance. That pattern
  DOES NOT TRANSFER. Grok bills per token, Keith's ceiling is $10/mo, and the account
  *** AUTO-RELOADS $5 AT A TIME *** — so an overspend does not hit a wall, it silently tops up.
  This module's dollar hard-stop is therefore the ONLY thing standing between a runaway loop and
  repeated $5 charges. Treat it as a safety device, not bookkeeping.

MEASURED COSTS (2026-07-12, grok-4.5)
    plain call     $0.000440   -> ~22,700 per $10
    grounded call  $0.029426   ->     ~340 per $10     (67x more expensive)
  A grounded call is dear because search injects ~10k tokens of results into context AND bills
  $0.005 per search. Hence: search is OFF by default and must be opted into explicitly.

*** max_tool_calls DOES NOT BIND. *** Tested: sent max_tool_calls=1, the model still ran 2
  web searches. The API accepts the field and ignores it. The real defences are:
    (a) the monthly dollar hard-stop, and
    (b) the pre-flight INSUFFICIENT_HEADROOM check, which refuses to START a call the remaining
        budget could not absorb even in the worst case.
  There is deliberately NO polling loop in this module. Do not add one.

COST ACCOUNTING — calibrated against xAI's own billed figure
  usage.cost_in_usd_ticks is AUTHORITATIVE (1 tick = 1e-10 USD) and INCLUDES tool fees. Verified:
    grounded call -> 294,260,000 ticks = $0.029426
      = 8152 fresh in x$2 + 1792 cached x$0.50 + 371 out x$6, per 1M   ($0.019426)
      + exactly 2 x $0.005 web_search                                   ($0.010000)
  The token-math fallback reproduces that number independently on both payloads. Two gotchas it
  encodes, both found the hard way:
    1. THE TWO SURFACES USE OPPOSITE REASONING CONVENTIONS.
         /v1/chat/completions : total = prompt + completion + reasoning  (reasoning SEPARATE)
         /v1/responses        : total = input  + output                  (output INCLUDES it)
       Adding reasoning unconditionally double-counts on /v1/responses. total_tokens disambiguates.
    2. THE TOOL-USAGE FIELD IS server_side_tool_usage_details {"web_search_calls": N, ...},
       NOT server_side_tool_usage. The first parser looked for the wrong key and logged
       tool-calls=0 while 2 searches were billed. Do not "simplify" that back.
"""
import json, os, time, datetime, hashlib, urllib.request, urllib.error, threading

MODEL    = "grok-4.5"
ENDPOINT = "https://api.x.ai/v1/responses"   # Responses API. /v1/chat/completions is
# LEGACY and REJECTS the server-side tools: it 422s with "unknown variant `web_search`,
# expected `function` or `live_search`". Learned live 2026-07-12. Do not switch back.
KEY_ENV  = "XAI_API_KEY"
# Key lives OUTSIDE the published Ai\ tree, by design. V:\Research4\.secrets is a sibling of Ai\,
# so no R2 publish pass can reach it even if the exclude list misses a filename. Safe by LOCATION.
#
# TWO candidate files, tried in order. Keith created bts-sgh-API-key.txt first, then xAI issued a
# second key on payment which landed in Grok_API_Token-Key.txt. An EMPTY file must never shadow a
# good one — so we skip blanks and keep looking, rather than taking the first path that exists.
KEY_FILES = [
    r"V:\Research4\.secrets\Grok_API_Token-Key.txt",   # the paid key (xai-..., 2026-07-12)
    r"V:\Research4\.secrets\bts-sgh-API-key.txt",      # first file; was empty on 2026-07-12
]
KEY_FILE = KEY_FILES[0]        # for error messages

# --- 2026-07-30: ALSO resolve the key through bts_paths, so this rail works from the SANDBOX. ----
# The hardcoded V:\ paths above stay FIRST and unchanged, so Windows behaviour cannot regress —
# this only APPENDS candidates. MEASURED: without it the Linux sandbox raised "NO XAI KEY" while
# the keys sat perfectly readable at /sessions/*/mnt/Research4/.secrets, which pinned every node
# call to Keith's desktop and broke Rule 2. With it, SGH answered in 20.8 s with no desktop at all.
# Wrapped: a path-resolution failure must never stop the module importing on a healthy box.
try:
    import bts_paths as _bp
    for _n in ("Grok_API_Token-Key.txt", "bts-sgh-API-key.txt"):
        _alt = _bp.secrets(_n)
        if _alt not in KEY_FILES:
            KEY_FILES.append(_alt)
except Exception:
    pass

_HERE        = os.path.dirname(os.path.abspath(__file__))
LEDGER_FILE  = os.path.join(_HERE, "sgh_spend.json")
SAMPLE_FILE  = os.path.join(_HERE, "sgh_usage_sample.json")

# ---- prices, USD per 1M tokens (docs.x.ai/developers/pricing, fetched 2026-07-12) -------------
PRICES = {
    "grok-4.5": {"in": 2.00, "cached_in": 0.50, "out": 6.00, "ctx": 500_000},
    "grok-4.3": {"in": 1.25, "cached_in": 0.20, "out": 2.50, "ctx": 1_000_000},
}
TOOL_COST = {                      # USD per single invocation
    # the Responses API reports these as SERVER_SIDE_TOOL_* in usage.server_side_tool_usage
    "web_search":     0.005,       # $5 / 1k
    "x_search":       0.005,
    "code_execution": 0.005,
    "attachment_search": 0.010,    # $10 / 1k
    "collections_search": 0.0025,  # $2.50 / 1k
    "SERVER_SIDE_TOOL_WEB_SEARCH":  0.005,
    "SERVER_SIDE_TOOL_X_SEARCH":    0.005,
    "SERVER_SIDE_TOOL_IMAGE_SEARCH": 0.005,   # billed at the Web Search rate (docs)
    "SERVER_SIDE_TOOL_CODE_EXECUTION": 0.005,
    "SERVER_SIDE_TOOL_VIEW_IMAGE":  0.0,      # token-billed, no invocation fee (docs)
    "SERVER_SIDE_TOOL_VIEW_X_VIDEO": 0.0,     # token-billed, no invocation fee (docs)
}
DEFAULT_TOOL_COST = 0.005          # unknown tool -> assume the common rate, never assume free

# ---- budget ------------------------------------------------------------------------------------
MONTHLY_BUDGET_USD = 10.00         # Keith's ceiling. Raise here, in ONE place.
POLL_SHARE         = 0.20          # background/status may spend at most 20% of the month
WARN_AT            = 0.80          # emit a warning once the month passes 80%
MAX_TOOL_CALLS     = 8             # passed to the API, but IT DOES NOT BIND (proven 2026-07-12)
MAX_CALL_USD          = 2.00       # worst case for a GROUNDED call. RAISED from 0.50 on 2026-07-13
                                   # because the old figure was WRONG: two grounded calls that day
                                   # cost $1.32 and $1.61 (not $0.029). The guard must reflect what
                                   # a grounded call ACTUALLY costs, or it silently fails to guard.
MAX_CALL_USD_NOSEARCH = 0.05       # worst case for a plain call (measured: $0.0004-0.019)
MAX_RPM            = 60

# ---- SEARCH GOVERNOR (Keith, 2026-07-13) ------------------------------------------------------
# *** SEARCH ON THIS PAID RAIL IS OFF. ***
#
# WHY. On 2026-07-13 two grounded calls cost $2.93 between them ($1.32 + $1.61) — against a $10
# monthly budget, and against an UNGROUNDED call cost of ~$0.001-0.02. Search is ~50-100x the price
# of the thinking, because the model pulls every search result into the paid context (780k tokens on
# one call). At the rate they were being fired that is $200-500/month.
#
# AND IT BUYS NOTHING WE NEED. Keith, 2026-07-13: "BTS is FREE and we are mostly waiting on you, not
# SGH." The mesh's bottleneck is COWORK, not the nodes. Paying to make a node faster buys no
# throughput. Every job those two calls did has a free lane:
#   - a DOI            -> Crossref API. Free, 207 ms. NEVER ask a model for a DOI.
#   - a literature value -> the 111-PDF local library + the chapter's own reference list.
#   - a web sweep      -> browser-Grok (GBW/SGH chat), the FREE bulk lane: it writes the body to
#                         GDX/ROLD and Cowork reads it back for $0.
#   - a numeric check  -> GEM/Vertex (free tier, and the $300 GCP credit EXPIRES 2026-10-13 unspent).
#
# THE RULE: spending must be NEEDED, not reflexive. search=True is refused outright. To override you
# must pass spend_ok=<usd> — an explicit, per-call, eyes-open dollar authorisation from Keith. There
# is no default value and no way to set it globally: if you cannot say what the search is worth,
# you do not get to buy it.
SEARCH_ON_PAID_RAIL = False        # do NOT flip this to True. Use spend_ok= per call instead.
PER_CALL_CEILING_USD = 0.25        # a call may not be AUTHORISED above this without spend_ok
GROUNDED_TOOL_CALLS  = 2           # if search is ever authorised, keep the leash short

# ---- OUTPUT SPILL (Keith, 2026-07-12) ---------------------------------------------------------
# Large answers get written to LOCAL DISK and only a HEAD comes back in the dict.
#
# WHAT THIS DOES AND DOES NOT SAVE — worth being precise, because it is easy to expect the wrong win:
#   IT DOES NOT save xAI dollars. Output tokens are billed AT GENERATION ($6/1M). Once grok has
#     written 5k tokens you have paid for them, whether they land in a variable, on disk, or in
#     Google Drive. Redirecting the destination changes nothing on the invoice. The only levers
#     that actually cut output cost are reasoning_effort and asking for less — the dial's job.
#   IT DOES save COWORK CONTEXT, which is the resource that was actually bleeding. A 40k-token
#     analysis pulled into the conversation burns 40k of Claude's window. Spilled to ROLD, it
#     burns ~200 and I read only the slice I need.
#
# And the fastest shared surface for THIS rail is the local disk, not GDX: bts_sgh runs on Keith's
# machine, so ROLD is a direct write with no cloud hop. GDX exists for agents that CANNOT see the
# filesystem (browser-Grok, GBW) — mirror there only when the artifact is destined for one of them.
# 2026-07-31: was a hardcoded r"V:\Research4\...\SGH_returns". A hardcoded absolute path does not
# FAIL on the wrong OS — it SUCCEEDS against the wrong object, or silently spills nowhere. This was
# the bts_paths defect in its third module; the key lookups above were converted 07-30, this was
# missed. An audit of every remaining r"V:\..." literal in BTS_MESH ran the same day: this was the
# ONLY functional one left. All others are docstrings, error text, or the _migrate_* archaeology.
try:
    import bts_paths as _bp_spill
    SPILL_DIR = _bp_spill.working("SGH_returns")
except Exception:
    SPILL_DIR = r"V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\SGH_returns"
SPILL_OVER_CHARS = 4000        # answers longer than this go to disk
SPILL_HEAD_CHARS = 600         # how much comes back inline

_lock = threading.Lock()


class SghError(RuntimeError):
    pass


# ================================================================================================
# key
# ================================================================================================
def _key() -> str:
    k = os.environ.get(KEY_ENV)
    if k and k.strip():
        return k.strip()
    for p in KEY_FILES:
        if os.path.exists(p):
            k = open(p, encoding="utf-8").read().strip().strip('"').strip()
            if k:                      # skip EMPTY files — do not let a blank shadow a good key
                return k
    raise SghError(
        "NO XAI KEY. Put it in the %s env var, or in one of:\n  %s\n"
        "Get one at https://console.x.ai/team/default/api-keys .\n"
        "NEVER commit it, never put it under V:\\Research4\\Ai\\ (that tree is published to "
        "ai.dchambers.com)." % (KEY_ENV, "\n  ".join(KEY_FILES)))


def key_present() -> bool:
    try:
        _key(); return True
    except SghError:
        return False


# ================================================================================================
# durable spend ledger — keyed by UTC MONTH (the budget is monthly, so the reset is monthly)
# ================================================================================================
def _month() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")


def _load() -> dict:
    try:
        d = json.load(open(LEDGER_FILE))
    except Exception:
        d = {}
    if d.get("month") != _month():
        d = {"month": _month(), "WORK": 0.0, "POLL": 0.0,
             "calls": 0, "tool_calls": 0, "recent": [], "unpriced": 0,
             "tok_in": 0, "tok_out": 0, "tok_reason": 0, "hist": [],
             "tok_cached": 0, "usd_saved": 0.0}
    for k, v in (("WORK", 0.0), ("POLL", 0.0), ("calls", 0),
                 ("tool_calls", 0), ("recent", []), ("unpriced", 0),
                 ("tok_in", 0), ("tok_out", 0), ("tok_reason", 0), ("hist", []),
                 ("tok_cached", 0), ("usd_saved", 0.0)):
        d.setdefault(k, v)
    return d


def _save(d: dict) -> None:
    # 🔴 FALLBACK ADDED 2026-08-15. DO NOT REMOVE.
    # os.replace across the Cowork FUSE mount raises FileNotFoundError (measured 2026-08-02) — the
    # same family as the mount refusing to unlink. The atomic path stays FIRST and unchanged, so
    # native Windows behaviour cannot regress. But WITHOUT a fallback the failure mode is the worst
    # one available: the API call has ALREADY BEEN BILLED by the time _save runs, so the raise
    # loses the record of money that is already spent. A non-atomic write is strictly better than
    # an unrecorded charge. This is the defect behind "paid rails run NATIVELY" — not a repeal of
    # that rule, a repair of the thing it was written around. Proven first in bts_oa_api.py.
    tmp = LEDGER_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(d, f, indent=1)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, LEDGER_FILE)    # atomic — a crash mid-write cannot corrupt the ledger
    except Exception:
        with open(LEDGER_FILE, "w") as f:
            json.dump(d, f, indent=1)


def budget() -> dict:
    d = _load()
    spent = d["WORK"] + d["POLL"]
    poll_cap = MONTHLY_BUDGET_USD * POLL_SHARE
    return {
        "month": d["month"],
        "spent": round(spent, 4),
        "work_spent": round(d["WORK"], 4),
        "poll_spent": round(d["POLL"], 4),
        "budget": MONTHLY_BUDGET_USD,
        "left": round(max(0.0, MONTHLY_BUDGET_USD - spent), 4),
        "pct": round(100.0 * spent / MONTHLY_BUDGET_USD, 1) if MONTHLY_BUDGET_USD else 0.0,
        "poll_cap": round(poll_cap, 4),
        "poll_left": round(max(0.0, poll_cap - d["POLL"]), 4),
        "calls": d["calls"],
        "tool_calls": d["tool_calls"],
        "unpriced_calls": d["unpriced"],     # calls we could NOT price exactly -> ledger is a bound
        "warn": spent >= MONTHLY_BUDGET_USD * WARN_AT,
        "tok_in": d["tok_in"], "tok_out": d["tok_out"], "tok_reason": d["tok_reason"],
        "tok_total": d["tok_in"] + d["tok_out"],
        "tok_cached": d.get("tok_cached", 0),
        "cache_hit_pct": round(100.0 * d.get("tok_cached", 0) / d["tok_in"], 1) if d["tok_in"] else 0.0,
        "usd_saved": round(d.get("usd_saved", 0.0), 6),
        "hist": d.get("hist") or [],
    }


def _rpm_gate():
    while True:
        with _lock:
            d = _load()
            now = time.time()
            recent = [t for t in d["recent"] if now - t < 60]
            if len(recent) < MAX_RPM:
                recent.append(now)
                d["recent"] = recent
                _save(d)
                return
            wait = 60 - (now - recent[0]) + 0.05
        time.sleep(max(0.05, min(wait, 61)))


def _charge(priority: str, usd: float, n_tools: int, exact: bool, usage: dict = None) -> None:
    with _lock:
        d = _load()
        d[priority] = d.get(priority, 0.0) + usd
        d["calls"] += 1
        d["tool_calls"] += n_tools
        if not exact:
            d["unpriced"] += 1
        u = usage or {}
        ti = u.get("input_tokens") or u.get("prompt_tokens") or 0
        to = u.get("output_tokens") or u.get("completion_tokens") or 0
        od = u.get("output_tokens_details") or u.get("completion_tokens_details") or {}
        tr = od.get("reasoning_tokens", 0) if isinstance(od, dict) else 0
        d["tok_in"] += int(ti); d["tok_out"] += int(to); d["tok_reason"] += int(tr)
        # cache accounting: cached input bills at $0.50/1M instead of $2.00/1M
        pdet = u.get("input_tokens_details") or u.get("prompt_tokens_details") or {}
        tc = pdet.get("cached_tokens", 0) if isinstance(pdet, dict) else 0
        d["tok_cached"] = d.get("tok_cached", 0) + int(tc)
        p = PRICES.get(MODEL, PRICES["grok-4.5"])
        d["usd_saved"] = d.get("usd_saved", 0.0) + int(tc) * (p["in"] - p["cached_in"]) / 1e6
        # rolling history for the dashboard BURN RATE sparkline (last 60 calls)
        d["hist"] = (d.get("hist") or [])[-59:] + [{"t": int(time.time()),
                                                    "usd": round(usd, 6),
                                                    "tok": int(ti) + int(to)}]
        _save(d)


# ================================================================================================
# usage parsing + costing
# ================================================================================================
USD_PER_TICK = 1e-10       # see CALIBRATED below


def _price_usage(usage: dict, model: str) -> tuple:
    """-> (usd, n_tool_calls, exact:bool). NEVER underestimates.

    CALIBRATED against a real grok-4.5 response, 2026-07-12 (first live call):
        prompt_tokens 214 (cached 128) | completion_tokens 2 | reasoning_tokens 32
        total_tokens 248  == 214 + 2 + 32   -> REASONING IS ADDITIVE, NOT FOLDED INTO completion.
        86*$2 + 128*$0.50 + (2+32)*$6, per 1M  =  $0.000440
        xAI reported  cost_in_usd_ticks = 4,400,000  ->  1 tick = 1e-10 USD.
    Both facts confirm each other in one equation, so neither is an assumption.

    *** cost_in_usd_ticks IS AUTHORITATIVE. *** xAI tells us what it actually billed, so we do not
    estimate when we do not have to. The token math below is only the FALLBACK for a response that
    omits the field. My original fallback used max(completion, reasoning) and UNDERBILLED by 2.7%
    on the very first live call — which is why the authoritative field wins and why the fallback
    now adds reasoning rather than maxing it.
    """
    p = PRICES.get(model, PRICES["grok-4.5"])
    if not isinstance(usage, dict) or not usage:
        return 0.0, 0, False

    # ---- number of server-side tool invocations (billed per call) ------------------------------
    n_tools = 0
    tool_usd = 0.0
    tools_known = False

    # GROUND TRUTH (observed live 2026-07-12, /v1/responses): the field is
    #   "server_side_tool_usage_details": {"web_search_calls": 2, "x_search_calls": 0, ...}
    #   "num_server_side_tools_used": 2
    # NOT "server_side_tool_usage". My first parser looked for the wrong key and logged
    # tool-calls=0 while 2 searches were actually billed. Do not "simplify" this back.
    DETAIL_RATES = {
        "web_search_calls":        0.005,
        "x_search_calls":          0.005,
        "code_interpreter_calls":  0.005,
        "file_search_calls":       0.0025,
        "document_search_calls":   0.0025,
        "image_generation_calls":  0.0,     # billed per image, not per invocation
        "mcp_calls":               0.0,     # token-billed only (docs)
    }
    det = usage.get("server_side_tool_usage_details")
    if isinstance(det, dict) and det:
        for name, cnt in det.items():
            if isinstance(cnt, (int, float)) and cnt:
                n_tools += int(cnt)
                tool_usd += int(cnt) * DETAIL_RATES.get(name, DEFAULT_TOOL_COST)
        tools_known = True
    else:
        sst = usage.get("server_side_tool_usage") or usage.get("server_side_tools")
        if isinstance(sst, dict) and sst:
            for name, cnt in sst.items():
                if isinstance(cnt, (int, float)):
                    n_tools += int(cnt)
                    tool_usd += int(cnt) * TOOL_COST.get(name, DEFAULT_TOOL_COST)
            tools_known = True
        elif isinstance(usage.get("num_server_side_tools_used"), (int, float)):
            n_tools = int(usage["num_server_side_tools_used"])
            tool_usd = n_tools * DEFAULT_TOOL_COST
            tools_known = True

    # ---- AUTHORITATIVE: xAI's own billed figure -------------------------------------------------
    ticks = usage.get("cost_in_usd_ticks")
    if isinstance(ticks, (int, float)) and ticks >= 0:
        # Does this already include tool fees? Unknown on a zero-tool call. Be safe: if tools ran
        # and the reported cost is BELOW pure token cost + tool fees, add the shortfall.
        usd = float(ticks) * USD_PER_TICK
        if n_tools:
            pt = usage.get("prompt_tokens") or 0
            ct = usage.get("completion_tokens") or 0
            cd = usage.get("completion_tokens_details") or {}
            pd = usage.get("prompt_tokens_details") or {}
            cached = (pd.get("cached_tokens") or 0) if isinstance(pd, dict) else 0
            rt = (cd.get("reasoning_tokens") or 0) if isinstance(cd, dict) else 0
            tok_only = (max(0, pt - cached) * p["in"] + cached * p["cached_in"]
                        + (ct + rt) * p["out"]) / 1_000_000.0
            if usd < tok_only + tool_usd - 1e-12:
                usd = tok_only + tool_usd     # ticks excluded tool fees -> add them
        return usd, n_tools, True

    # ---- FALLBACK: compute from tokens ----------------------------------------------------------
    def g(*names):
        for n in names:
            if isinstance(usage.get(n), (int, float)):
                return usage[n]
        return None

    pt = g("prompt_tokens", "input_tokens")
    ct = g("completion_tokens", "output_tokens")
    if pt is None or ct is None:
        return 0.0, 0, False

    pd = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    cd = usage.get("completion_tokens_details") or usage.get("output_tokens_details") or {}
    cached = (pd.get("cached_tokens") or 0) if isinstance(pd, dict) else 0
    reasoning = (cd.get("reasoning_tokens") or 0) if isinstance(cd, dict) else 0

    fresh_in = max(0, pt - cached)

    # *** THE TWO xAI SURFACES USE OPPOSITE REASONING CONVENTIONS. Both observed live 2026-07-12:
    #   /v1/chat/completions : total = prompt + completion + reasoning  -> reasoning is SEPARATE
    #   /v1/responses        : total = input  + output                  -> output INCLUDES reasoning
    # Adding reasoning unconditionally DOUBLE-COUNTS on /v1/responses. Use total_tokens as the
    # discriminator instead of hardcoding either convention.
    tot = usage.get("total_tokens")
    if isinstance(tot, (int, float)) and reasoning:
        out = ct + reasoning if abs((pt + ct + reasoning) - tot) <= abs((pt + ct) - tot) else ct
    else:
        out = ct + reasoning

    usd = (fresh_in * p["in"] + cached * p["cached_in"] + out * p["out"]) / 1_000_000.0 + tool_usd
    exact = tools_known or not usage.get("_tools_requested")
    return usd, n_tools, exact


def _signal(kind: str, note: str, path: str = None) -> None:
    """Emit onto the ROLD bus so the dashboard's SIGNAL LOG reflects REAL traffic.

    WHY THIS WAS MISSING AND WHY IT MATTERS (Keith, 2026-07-12: "the SIGNAL LOG doesn't look live
    either, it shows replies from 3 hours ago"): the API rails call xAI/Google directly and never
    touched the bus, so BTS_SIGNAL.log only ever recorded the old browser-bridge era. The log was
    not broken — it was honestly reporting that no bus traffic existed. Now the rails emit, so the
    log shows what the mesh is ACTUALLY doing.

    Never let telemetry break a real call: any failure here is swallowed."""
    try:
        import bts_bus as B
        log = os.path.join(_HERE, "BTS_SIGNAL.log")
        B.append_signal(log, "SGH", B.make_envelope(kind, note[:180], path=path))
    except Exception:
        pass


def _data_uri(path: str) -> str:
    """Local image -> base64 data URI, with a PNG INTEGRITY CHECK first.

    The D: mount has served corrupted copies of files at least seven times today. A corrupted PNG
    would still base64-encode fine and the model would still answer — it would just be reviewing
    garbage while sounding certain. PNG carries a CRC32 per chunk, so corruption is DETECTABLE:
    walk the chunks, check every CRC, and RAISE rather than ship bad bytes."""
    import base64, binascii, mimetypes, struct
    with open(path, "rb") as f:
        b = f.read()
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        i, n = 8, 0
        while i + 8 <= len(b):
            ln = struct.unpack(">I", b[i:i+4])[0]
            typ = b[i+4:i+8]
            data = b[i+8:i+8+ln]
            crc = struct.unpack(">I", b[i+8+ln:i+12+ln])[0]
            if binascii.crc32(typ + data) & 0xFFFFFFFF != crc:
                raise SghError("PNG CRC FAIL in %s (chunk %s) — bytes are CORRUPT, not sending."
                               % (path, typ))
            n += 1
            i += 12 + ln
            if typ == b"IEND":
                break
        if n < 2:
            raise SghError("PNG %s truncated (only %d chunks)." % (path, n))
    mime = mimetypes.guess_type(path)[0] or "image/png"
    return "data:%s;base64,%s" % (mime, base64.b64encode(b).decode("ascii"))


def _spill(text: str, prompt: str, model: str) -> dict:
    """Write a long answer to ROLD; return {path, head, chars, spilled}."""
    if not text or len(text) <= SPILL_OVER_CHARS:
        return {"spilled": False, "path": None, "head": text, "chars": len(text or "")}
    try:
        os.makedirs(SPILL_DIR, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        tag = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:6]
        fn = os.path.join(SPILL_DIR, "SGH_%s_%s.md" % (stamp, tag))
        with open(fn, "w", encoding="utf-8") as f:
            f.write("<!-- SGH (%s) via bts_sgh.py — %s -->\n" % (model, stamp))
            f.write("<!-- PROMPT: %s -->\n\n" % prompt[:300].replace("\n", " "))
            f.write(text)
            f.flush(); os.fsync(f.fileno())
        return {"spilled": True, "path": fn, "head": text[:SPILL_HEAD_CHARS],
                "chars": len(text)}
    except Exception as e:
        # spilling must NEVER lose the answer — on failure, hand back the full text.
        return {"spilled": False, "path": None, "head": text, "chars": len(text),
                "spill_error": str(e)[:120]}


# ================================================================================================
# the call
# ================================================================================================
# Models on the xAI rail that ACCEPT `reasoning_effort`. Everything else must not be sent it.
# Deny-list rather than allow-list on purpose: a NEW reasoning model should work by default, and a
# non-reasoning model announces itself loudly with HTTP 400 rather than failing silently.
_NO_EFFORT_MODELS = ("grok-build",)


def _MODEL_TAKES_EFFORT(model: str) -> bool:
    return not any(m in (model or "") for m in _NO_EFFORT_MODELS)


def ask(prompt: str,
        priority: str = "WORK",
        search: bool = False,          # web_search. REFUSED unless spend_ok is given. See SEARCH GOVERNOR.
        x_search: bool = False,        # X only. Same governor.
        spend_ok: float = None,        # explicit per-call dollar authorisation from Keith. No default.
                                       # Required for ANY grounded call, and for any call whose worst
                                       # case exceeds PER_CALL_CEILING_USD.
        reasoning_effort: str = None,   # "low" | "high". HIGH BILLS MORE — reasoning tokens are output.
                                        # None -> take it from the SPEED<->COST dial (bts_policy).
        system: str = None,
        images: list = None,           # local PNG/JPEG paths -> sent as input_image parts (base64
                                       # data URIs). grok-4.5 is multimodal; the API rail is
                                       # UNGROUNDED and therefore CANNOT browse, so an image must be
                                       # CARRIED, not linked. A URL in the prompt would be invisible.
        context: str = None,           # STABLE PREFIX -> this is what gets cached. See below.
        cache_key: str = None,         # sticky-routing key. Auto-derived from context if omitted.
        model: str = MODEL,
        max_tool_calls: int = MAX_TOOL_CALLS,
        spill: bool = True,            # long answers -> ROLD, only a head comes back. See SPILL_DIR.
        retries: int = 3) -> dict:
    """
    priority: 'WORK' (real mesh traffic) | 'POLL' (background/status — capped, refusable)
    search:   enables xAI server-side Web Search. Grok has NO realtime knowledge without it.
              Billed $0.005 per invocation and THE MODEL CHOOSES HOW MANY. Capped by max_tool_calls.
    """
    _default_effort = (reasoning_effort is None)
    if reasoning_effort is None:
        reasoning_effort = "low"

    if priority not in ("WORK", "POLL"):
        raise SghError("priority must be WORK or POLL")

    # ---- SEARCH GOVERNOR (Keith, 2026-07-13) ---------------------------------------------------
    # Grounded search on the paid rail is REFUSED. It cost $2.93 in two calls on 2026-07-13 and every
    # job it did has a free lane (Crossref for DOIs, the local PDF library for values, browser-Grok
    # for bulk web work, GEM/Vertex for numeric checks). Spending must be NEEDED, not reflexive.
    # The ONLY way through is an explicit per-call dollar authorisation from Keith: spend_ok=<usd>.
    if (search or x_search) and not SEARCH_ON_PAID_RAIL and spend_ok is None:
        return {"ok": False, "reason": "SEARCH_REFUSED_ON_PAID_RAIL", "text": None,
                "detail": "Grounded search on the paid SGH rail is off (measured $1.32-$1.61 per "
                          "call). Use a FREE lane: Crossref for a DOI, the local 111-PDF library for "
                          "a literature value, browser-Grok (GBW) for a web sweep, GEM/Vertex for a "
                          "numeric check. If the search is genuinely NEEDED, ask Keith and pass "
                          "spend_ok=<usd> with the amount he authorised.",
                "free_lanes": ["crossref", "local_pdf_library", "browser_grok", "gem_vertex"],
                "budget": budget()}

    # A plain call is ~$0.001-0.02, so the ceiling only ever bites on something unusual — which is
    # exactly when a human should look at it. Same escape hatch, same explicit authorisation.
    _worst = MAX_CALL_USD if (search or x_search) else MAX_CALL_USD_NOSEARCH
    if spend_ok is None and _worst > PER_CALL_CEILING_USD:
        return {"ok": False, "reason": "PER_CALL_CEILING", "text": None,
                "detail": "worst case $%.2f exceeds the $%.2f per-call ceiling; pass spend_ok=<usd> "
                          "to authorise explicitly" % (_worst, PER_CALL_CEILING_USD),
                "budget": budget()}
    if spend_ok is not None and _worst > float(spend_ok):
        return {"ok": False, "reason": "SPEND_OK_TOO_LOW", "text": None,
                "detail": "worst case $%.2f exceeds the authorised spend_ok=$%.2f"
                          % (_worst, float(spend_ok)),
                "budget": budget()}

    # ---- THE SPEED<->COST DIAL ------------------------------------------------------------------
    # bts_policy holds one number (bias 0-100) that every rail obeys. At bias<=25 ("FREE") the paid
    # rail is REFUSED OUTRIGHT — spend-nothing is a real stop on the dial, not a suggestion, and
    # with the account auto-reloading $5 at a time that matters.
    # The dial only supplies DEFAULTS: anything the caller passed explicitly still wins.
    try:
        import bts_policy
        _pol = bts_policy.resolve()
        if not _pol["sgh"]:
            return {"ok": False, "reason": "DIAL_IS_FREE_ONLY", "text": None,
                    "detail": "SPEED<->COST dial is at bias=%d (%s): the paid SGH rail is off. "
                              "Raise the dial above 25 to allow it."
                              % (_pol["bias"], _pol["name"]),
                    "budget": budget()}
        if _default_effort and reasoning_effort == "low":
            reasoning_effort = _pol["effort"]
    except SghError:
        raise
    except Exception:
        pass                       # no policy file -> behave exactly as before

    b = budget()
    if b["left"] <= 0:
        return {"ok": False, "reason": "MONTHLY_BUDGET_EXHAUSTED", "text": None, "budget": b}
    if priority == "POLL" and b["poll_left"] <= 0:
        # THE WHOLE POINT: refuse the poll, protect the month's real work.
        return {"ok": False, "reason": "POLL_BUDGET_SPENT", "text": None, "budget": b}

    # PRE-FLIGHT WORST-CASE GUARD. Because max_tool_calls does not bind (see below) and the
    # account AUTO-RELOADS $5 at a time, an unbounded agentic call is the one thing that could
    # quietly bill past the budget. So refuse to even START a call unless the remaining budget
    # could absorb a bad one. Measured 2026-07-12: a grounded call ran $0.029 (2 searches,
    # ~10k input tokens). MAX_CALL_USD is the ceiling we assume such a call could reach.
    worst = MAX_CALL_USD if (search or x_search) else MAX_CALL_USD_NOSEARCH
    if b["left"] < worst:
        return {"ok": False, "reason": "INSUFFICIENT_HEADROOM", "text": None,
                "detail": "only $%.4f left; a %s call could cost up to $%.2f"
                          % (b["left"], "grounded" if (search or x_search) else "plain", worst),
                "budget": b}

    # ---- PROMPT CACHING -------------------------------------------------------------------------
    # xAI caches AUTOMATICALLY — we saw cached_tokens>0 on the very first call, before any of this
    # existed. So the job is not "turn caching on", it is "maximise the HIT RATE". Two levers:
    #
    #   1. PREFIX ORDER. The cache matches from the START of the input and stops at the first
    #      difference. So the STABLE part must come FIRST and the VARIABLE part LAST. Put the
    #      question before the chapter text and you cache nothing. Hence: system, then context,
    #      then prompt — always in that order.
    #   2. STICKY ROUTING. Cache entries live per-server. prompt_cache_key (Responses API; the
    #      equivalent of the x-grok-conv-id header on chat/completions) routes repeat requests to
    #      the SAME server, so the entry is actually there to hit.
    #
    # Economics: cached input is $0.50/1M vs $2.00/1M -> 75% off the input leg. For a ~10k-token
    # chapter context re-sent on every verification call, that is the single biggest saving on SGH.
    inp = []
    if system:
        inp.append({"role": "system", "content": system})
    if context:
        inp.append({"role": "user", "content": context})     # STABLE -> cacheable prefix
    if images:
        # Responses API multimodal content parts. IMAGES ARE CARRIED, NOT LINKED — this rail has no
        # search tool enabled, so it cannot fetch a URL; handing it a link would produce a confident
        # review of an image it never saw. Every PNG is CRC-checked before it is encoded.
        content = [{"type": "input_image", "image_url": _data_uri(p)} for p in images]
        content.append({"type": "input_text", "text": prompt})
        inp.append({"role": "user", "content": content})
    else:
        inp.append({"role": "user", "content": prompt})       # VARIABLE -> always last

    # Responses API: "input", not "messages".
    body = {"model": model, "input": inp, "reasoning_effort": reasoning_effort}

    # 🔴 NOT EVERY MODEL ON THIS RAIL IS A REASONING MODEL. Fixed 2026-07-31.
    # `grok-build-0.1` (the GW node) rejects the parameter outright:
    #     HTTP 400 invalid-argument — "Model grok-build-0.1 does not support parameter reasoningEffort"
    # so EVERY call to GW through this module had always failed. GW was nevertheless recorded as
    # `state = "LIVE"`, `conf = "V"`, measured 2026-07-30 — because the xAI RAIL had been measured
    # and the NODE never had. A rail that answers is not a node that works.
    # Found only when Keith asked "what is checking GW?" — the answer was nothing, and one call
    # settled it. ⇒ A node's liveness must be proven by CALLING THAT NODE, not its neighbour.
    if not _MODEL_TAKES_EFFORT(model):
        body.pop("reasoning_effort", None)

    # Derive a stable key from whatever is stable. Same context -> same key -> same server -> hit.
    if not cache_key:
        stable = (system or "") + "\x00" + (context or "")
        if stable.strip():
            cache_key = "bts-" + hashlib.sha1(stable.encode("utf-8")).hexdigest()[:24]
    if cache_key:
        body["prompt_cache_key"] = cache_key

    tools = []
    if search:
        tools.append({"type": "web_search"})
    if search or x_search:
        tools.append({"type": "x_search"})
    if tools:
        body["tools"] = tools
        max_tool_calls = min(max_tool_calls, GROUNDED_TOOL_CALLS)
        # *** WARNING: max_tool_calls DID NOT BIND when tested 2026-07-12. ***
        # Sent max_tool_calls=1; the model still issued 2 web_search calls (web_search_calls: 2).
        # It is passed for forward-compat, but DO NOT RELY ON IT as a cost guard. The real
        # defences are (a) the monthly dollar hard-stop in budget()/ask(), and (b) MAX_CALL_USD
        # below, which refuses to START a call the remaining budget could not absorb.
        body["max_tool_calls"] = max_tool_calls

    # PASSIVE STATE FEED (bts_state.py) — record the exchange for the dashboard. This is a RECORD,
    # not a dispatch: it appends one line and returns. Wrapped so telemetry can never break a call.
    _st_t0 = time.time()
    try:
        import bts_state
        bts_state.emit("COWORK", "SGH", "api_send",
                       (prompt[:60] + "...") if len(prompt) > 60 else prompt, direction="out")
    except Exception:
        pass

    _rpm_gate()
    delay = 1.0
    for attempt in range(retries):
        req = urllib.request.Request(
            ENDPOINT, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + _key()})
        try:
            raw = json.load(urllib.request.urlopen(req, timeout=180))

            # First live response: dump it, so the usage parser can be corrected against ground
            # truth instead of against my guess. See COST HONESTY in the header.
            if not os.path.exists(SAMPLE_FILE):
                try:
                    json.dump({"model": model, "usage": raw.get("usage"),
                               "keys": sorted(raw.keys())},
                              open(SAMPLE_FILE, "w"), indent=1)
                except Exception:
                    pass

            # Responses API: text lives in output[].content[].text where type == "output_text".
            # Keep the legacy choices[] path as a fallback so this still works if we ever point
            # ENDPOINT back at a chat-completions-style surface.
            txt, msg = "", {}
            out_items = raw.get("output") or []
            if out_items:
                chunks = []
                for it in out_items:
                    if not isinstance(it, dict):
                        continue
                    for c in (it.get("content") or []):
                        if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                            chunks.append(c.get("text") or "")
                txt = "".join(chunks)
            if not txt and raw.get("output_text"):
                txt = raw["output_text"] if isinstance(raw["output_text"], str) \
                      else "".join(raw["output_text"])
            if not txt:
                ch  = (raw.get("choices") or [{}])[0]
                msg = ch.get("message") or {}
                txt = msg.get("content") or ""

            usage = dict(raw.get("usage") or {})
            usage["_tools_requested"] = bool(tools)
            usd, n_tools, exact = _price_usage(usage, model)

            if not exact:
                # Could not price it exactly. Book a DEFENSIVE OVERESTIMATE — never underbill,
                # or the ledger drifts optimistic and the budget silently blows.
                worst = (len(prompt) / 3.0 * PRICES[model]["in"]
                         + 4000 * PRICES[model]["out"]) / 1_000_000.0
                worst += (max_tool_calls * DEFAULT_TOOL_COST) if tools else 0.0
                usd = max(usd, worst)

            _charge(priority, usd, n_tools, exact, raw.get("usage") or {})

            cites = []
            for c in (raw.get("citations") or msg.get("citations") or []):
                cites.append(c if isinstance(c, str) else c.get("url", ""))

            txt = txt.strip()
            sp = _spill(txt, prompt, model) if spill else {
                "spilled": False, "path": None, "head": txt, "chars": len(txt)}

            out = {"ok": True, "reason": "OK",
                   # text is the HEAD when spilled — the full answer is at ["path"].
                   "text": sp["head"],
                   "full_text": None if sp["spilled"] else txt,
                   "spilled": sp["spilled"],
                   "path": sp["path"],
                   "chars": sp["chars"],
                   "model": model,
                   "cost_usd": round(usd, 6),
                   "cost_exact": exact,
                   "tool_calls": n_tools,
                   "citations": [c for c in cites if c],
                   "searched": bool(tools),
                   "usage": raw.get("usage"),
                   "budget": budget()}
            if sp.get("spill_error"):
                out["spill_error"] = sp["spill_error"]

            _signal("NEW_OUTPUT_READY" if sp["spilled"] else "TASK_COMPLETE",
                    "grok-4.5 %s | $%.5f | %d tok | %s"
                    % ("SEARCH" if tools else "plain", usd,
                       (raw.get("usage") or {}).get("total_tokens") or 0,
                       (prompt[:60] + "...") if len(prompt) > 60 else prompt),
                    path=sp["path"])
            try:
                import bts_state
                bts_state.emit("SGH", "COWORK", "api_recv",
                               "grok-4.5 %s | $%.5f | %d tok"
                               % ("SEARCH" if tools else "plain", usd,
                                  (raw.get("usage") or {}).get("total_tokens") or 0),
                               direction="in",
                               ms=round((time.time() - _st_t0) * 1000, 1),
                               cost_usd=round(usd, 6))
            except Exception:
                pass
            return out

        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code == 429:
                if attempt < retries - 1:
                    time.sleep(delay); delay *= 2; continue
                return {"ok": False, "reason": "RATE_LIMITED", "text": None,
                        "detail": msg, "budget": budget()}
            if e.code in (401, 403):
                return {"ok": False, "reason": "AUTH_FAILED", "text": None,
                        "detail": "key rejected (%d). Check the key in %s" % (e.code, KEY_FILE),
                        "budget": budget()}
            if e.code == 404:
                return {"ok": False, "reason": "MODEL_NOT_FOUND", "text": None,
                        "detail": "model %r rejected: %s" % (model, msg), "budget": budget()}
            if e.code == 402:
                return {"ok": False, "reason": "NO_CREDIT", "text": None,
                        "detail": msg, "budget": budget()}
            return {"ok": False, "reason": "HTTP_%d" % e.code, "text": None,
                    "detail": msg, "budget": budget()}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay); delay *= 2; continue
            return {"ok": False, "reason": "NETWORK", "text": None,
                    "detail": str(e)[:200], "budget": budget()}

    return {"ok": False, "reason": "TIMEOUT", "text": None, "budget": budget()}


# ================================================================================================
if __name__ == "__main__":
    import sys
    b = budget()
    print("SGH (%s) budget %s: $%.4f / $%.2f spent (%.1f%%) | left $%.4f | "
          "POLL left $%.4f | calls %d, tool-calls %d"
          % (MODEL, b["month"], b["spent"], b["budget"], b["pct"],
             b["left"], b["poll_left"], b["calls"], b["tool_calls"]))
    if b["unpriced_calls"]:
        print("  !! %d call(s) could not be priced exactly — ledger is an UPPER BOUND."
              % b["unpriced_calls"])
    if b["warn"]:
        print("  !! WARNING: past %d%% of the monthly budget." % int(WARN_AT * 100))
    if not key_present():
        print("  !! NO KEY at %s (or $%s)" % (KEY_FILE, KEY_ENV))
        sys.exit(2)

    if len(sys.argv) > 1:
        use_search = "--search" in sys.argv
        args = [a for a in sys.argv[1:] if a != "--search"]
        r = ask(" ".join(args), search=use_search)
        print("[%s] %s" % (r["reason"], (r.get("text") or "")))
        if r.get("ok"):
            print("\n-- cost $%.6f%s | tools %d | %s"
                  % (r["cost_usd"], "" if r["cost_exact"] else " (UPPER BOUND, unpriced)",
                     r["tool_calls"], "searched" if r["searched"] else "no search"))
            for c in r.get("citations", [])[:8]:
                print("   ", c)

# EOF — bts_sgh.py
# Calibration record (2026-07-12, first live grok-4.5 call):
#   usage: prompt 214 (cached 128) | completion 2 | reasoning 32 | total 248
#   -> total = prompt + completion + reasoning, so REASONING IS ADDITIVE to output billing.
#   -> xAI's cost_in_usd_ticks = 4,400,000 == $0.000440 == the token math. 1 tick = 1e-10 USD.
#   Both facts confirm each other. cost_in_usd_ticks is AUTHORITATIVE; token math is the fallback.
