"""
bts_gem.py — GEM node, Gemini API rail.  RETIRES the browser-driven Gemini node.

WHY THIS EXISTS
  Driving gemini.google.com through the Chrome bridge twice made a WORKING node look dead
  (the Send button is replaced by a Stop button while streaming; the scraper returned empty).
  This is a real API. No browser, no scraping, no fake-DONE.

TESTED 2026-07-12 against a fresh free-tier key:
  * text generation           -> WORKS, free, no card required
  * model "gemini-2.5-flash"  -> 404, RETIRED for new keys. Use gemini-flash-latest.
  * google_search grounding   -> 429 RESOURCE_EXHAUSTED on a zero-usage key.
                                 The FREE tier has NO allocation for the Search tool; it needs a
                                 linked billing account (Tier 1) and then bills per search.
                                 So grounding is OFF by default and must be opted into explicitly.

QUOTA GOVERNOR (Keith's rule: "conserve those on polling so we don't run low for actual traffic")
  Free tier is ~1500 requests/day. A 10-second poll loop would eat 8,640 — 5.7x the budget —
  and starve real work. So:
    * POLL-class calls may never consume more than POLL_SHARE (20%) of the daily budget.
    * WORK-class calls keep going after POLL is exhausted.
    * The counter is DURABLE (gem_quota.json, keyed by UTC date) so a restart cannot reset it.
  There is deliberately NO polling loop in this module. Do not add one.
"""
import json, os, time, datetime, urllib.request, urllib.error, threading

# *** MODEL DRIFT, caught 2026-07-12. *** GOOGLE_CLOUD_SETUP_SCARS_2026-07-12.md says plainly:
#   "gemini-2.5-flash / gemini-2.5-pro on AI Studio -> 404 RETIRED for new keys.
#    Use gemini-flash-lite-latest (THE ONLY ONE THAT KEPT SERVING)."
# ...and this module was still pointed at gemini-flash-latest, which that same table records as
# 429-ing after ~18 calls. The doc was right and the code had drifted away from it.
MODEL       = "gemini-flash-lite-latest"
FALLBACK_MODELS = ["gemini-flash-latest", "gemini-2.0-flash"]
ENDPOINT    = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
KEY_ENV     = "GEMINI_API_KEY"
# TWO RAILS, TWO KEYS — a Google API key can target only ONE API, so we cannot have one key
# that reaches both AI Studio and Vertex. Discovered the hard way 2026-07-12.
#   gemini_key.txt  -> restricted to "Gemini API"        -> AI Studio, FREE tier (this module)
#   vertex_key.txt  -> restricted to "Agent Platform API" -> Vertex, Gemini 2.5 Pro on the $300 credit
KEY_FILE    = r"V:\Research4\.secrets\gemini_key.txt"     # OUTSIDE the published Ai\ tree, by design
QUOTA_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gem_quota.json")

# ⚠ MAX_RPD 1500 IS NOT A MEASURED NUMBER AND GOOGLE NO LONGER PUBLISHES ONE.
# As of 2026-07-15, docs/rate-limits says only "Rate limits ... can be viewed in Google AI Studio"
# and links an AUTHENTICATED dashboard — the numeric per-model table is GONE from the public docs.
# What we actually measured: `gemini-flash-latest` 429'd after ~18 CALLS, not 1500. So this value is
# a LOCAL GOVERNOR (it protects real work from poll traffic), NOT a statement about Google's quota.
# Do not plan a sweep against it. Measure the real ceiling on the new project and correct this.
MAX_RPD     = 1500
MAX_RPM     = 15
POLL_SHARE  = 0.20          # background/status calls get at most 20% of the day

_lock  = threading.Lock()
_calls = []                 # timestamps, for the RPM token bucket


class GemError(RuntimeError):
    pass


def _key() -> str:
    k = os.environ.get(KEY_ENV)
    if k:
        return k.strip()
    # 2026-07-30: the hardcoded V:\ path is tried FIRST (Windows cannot regress); bts_paths only
    # ADDS the sandbox path, so this rail also works with no desktop. See bts_sgh for the measurement.
    _cands = [KEY_FILE, KEY_FILE.replace(".txt", "")]
    try:
        import bts_paths as _bp
        _cands.append(_bp.secrets("gemini_key.txt"))
    except Exception:
        pass
    for p in _cands:
        if os.path.exists(p):
            k = open(p, encoding="utf-8").read().strip().strip('"')
            if k:
                return k
    raise GemError(
        "NO GEMINI KEY. Put it in the %s env var, or in %s .\n"
        "Get one free at https://aistudio.google.com/apikey . NEVER commit it, never put it under V:\\Research4\\Ai\\ (that tree is published)."
        % (KEY_ENV, KEY_FILE))


def _today() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def _load() -> dict:
    try:
        d = json.load(open(QUOTA_FILE))
    except Exception:
        d = {}
    if d.get("date") != _today():                 # new UTC day -> reset
        d = {"date": _today(), "WORK": 0, "POLL": 0, "recent": [], "tok": 0, "hist": []}
    d.setdefault("recent", [])                    # RPM bucket, DURABLE (see BUGFIX below)
    d.setdefault("tok", 0)                        # cumulative tokens today (dashboard BURN RATE)
    d.setdefault("hist", [])
    return d


def _save(d: dict) -> None:
    tmp = QUOTA_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, QUOTA_FILE)                   # atomic


def budget() -> dict:
    d = _load()
    used = d["WORK"] + d["POLL"]
    poll_cap = int(MAX_RPD * POLL_SHARE)
    return {"date": d["date"], "used": used,
            "work_used": d["WORK"], "poll_used": d["POLL"],
            "poll_cap": poll_cap,
            "poll_left": max(0, poll_cap - d["POLL"]),
            "total_left": max(0, MAX_RPD - used),
            "tok": d.get("tok", 0),
            "hist": d.get("hist") or []}


def _coerce_tokens(n) -> int:
    """The two rails report token usage in DIFFERENT SHAPES, and that killed the Vertex rail.

    MEASURED 2026-07-27: AI Studio hands back `tokens` as an int; Vertex hands back a DICT
    (`{"in":…, "out":…, "thinking":…}`). `int(dict)` raises TypeError — and it raised it AFTER the
    API call had already succeeded, in the accounting step, so a perfectly good answer was thrown
    away and every Vertex call reported as a failed rail. GEM has been "dead" this whole time for
    a bookkeeping reason, which is the same false-negative class as the Vertex 401 auth header:
    the tool failed and we recorded it as a property of the thing the tool was pointed at.

    Sum the parts rather than picking one: thinking tokens are billed at the output rate on Vertex
    and are the bulk of the spend, so a meter that ignored them would under-report by ~28x.
    """
    if isinstance(n, dict):
        return sum(int(v) for v in n.values() if isinstance(v, (int, float)))
    try:
        return int(n)
    except (TypeError, ValueError):
        return 0


def _record_tokens(n) -> None:
    """Accumulate token usage for the dashboard BURN RATE panel. GEM is free, so this is a
       VOLUME meter, not a cost meter — that is exactly the contrast the dashboard should show."""
    n = _coerce_tokens(n)
    if not n:
        return
    with _lock:
        d = _load()
        d["tok"] = d.get("tok", 0) + int(n)
        d["hist"] = (d.get("hist") or [])[-59:] + [{"t": int(time.time()), "tok": int(n)}]
        _save(d)


def _reserve(priority: str) -> tuple:
    """Returns (ok, reason). Counts the attempt — a 429 still consumed quota upstream."""
    with _lock:
        d = _load()
        used = d["WORK"] + d["POLL"]
        if used >= MAX_RPD:
            return False, "DAILY_EXHAUSTED"
        if priority == "POLL" and d["POLL"] >= int(MAX_RPD * POLL_SHARE):
            # THE WHOLE POINT: refuse the poll, protect the day's real work.
            return False, "POLL_BUDGET_SPENT"
        d[priority] = d.get(priority, 0) + 1
        _save(d)
    # RPM token bucket — DURABLE.
    # BUGFIX 2026-07-12: this bucket used to live in an in-memory list. Every new PROCESS started
    # with a fresh allowance, so running the verifier as a series of short-lived scripts blew
    # straight past 15/min and got RATE_LIMITED. Exactly the failure I flagged in GBW's code:
    # state that a restart silently resets. The timestamps now live in the same durable file.
    while True:
        with _lock:
            d = _load()
            now = time.time()
            recent = [t for t in d["recent"] if now - t < 60]
            if len(recent) < MAX_RPM:
                recent.append(now)
                d["recent"] = recent
                _save(d)
                return True, "OK"
            wait = 60 - (now - recent[0]) + 0.05
        time.sleep(max(0.05, min(wait, 61)))


def ask_aistudio(prompt: str, priority: str = "WORK", grounded: bool = False, retries: int = 3) -> dict:
    """priority: 'WORK' (real mesh traffic) | 'POLL' (background/status — capped, refusable).
       grounded: Google Search. NOT free — needs a linked billing account. Off by default."""
    if priority not in ("WORK", "POLL"):
        raise GemError("priority must be WORK or POLL")
    ok, why = _reserve(priority)
    if not ok:
        return {"ok": False, "reason": why, "text": None, "budget": budget()}

    body = {"contents": [{"parts": [{"text": prompt}]}]}
    if grounded:
        body["tools"] = [{"google_search": {}}]

    delay = 1.0
    for attempt in range(retries):
        req = urllib.request.Request(
            ENDPOINT.format(m=MODEL), data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": _key()})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=90))
            c = d["candidates"][0]
            txt = "".join(p.get("text", "") for p in c["content"]["parts"])
            gm = c.get("groundingMetadata", {}) or {}
            cites = [x.get("web", {}).get("uri", "") for x in gm.get("groundingChunks", [])]
            _tok = d.get("usageMetadata", {}).get("totalTokenCount") or 0
            _record_tokens(_tok)
            return {"ok": True, "reason": "OK", "text": txt.strip(),
                    "grounded": bool(cites), "citations": cites,
                    "tokens": _tok,
                    "budget": budget()}
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code == 429:
                # *** A 429 FROM GOOGLE IS TWO COMPLETELY DIFFERENT FAILURES. ***
                # Collapsing both into "RATE_LIMITED" is what made GEM look merely throttled when
                # it was actually DEAD, and cost real debugging time on 2026-07-12:
                #
                #   RESOURCE_EXHAUSTED           -> a real rate/quota limit. Backing off HELPS.
                #   "prepayment credits are depleted" -> the AI Studio EXPRESS-MODE key has run out
                #                                        of prepay credit. Backing off NEVER helps.
                #                                        Only Keith topping up (or a failover) fixes it.
                #
                # Retrying a billing failure just burns wall-clock and lies in the logs. So we
                # detect it, name it, and hand straight over to the Vertex failover.
                low = msg.lower()
                if "credit" in low or "prepay" in low or "billing" in low:
                    return {"ok": False, "reason": "CREDITS_DEPLETED", "text": None,
                            "detail": "AI Studio express-mode prepay credits are exhausted. "
                                      "This is NOT a rate limit — retrying cannot help. "
                                      "Top up at https://ai.studio/projects , or let the Vertex "
                                      "failover carry it.",
                            "budget": budget()}
                if grounded:
                    # Not a rate limit either — the free tier has NO Search-tool allocation.
                    return {"ok": False, "reason": "GROUNDING_NOT_ENTITLED",
                            "text": None, "detail": "google_search needs a linked billing account (Tier 1)",
                            "budget": budget()}
                if attempt < retries - 1:
                    time.sleep(delay); delay *= 2
                    continue
                return {"ok": False, "reason": "RATE_LIMITED", "text": None,
                        "detail": msg, "budget": budget()}
            return {"ok": False, "reason": "HTTP_%d" % e.code, "text": None,
                    "detail": msg, "budget": budget()}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay); delay *= 2
                continue
            return {"ok": False, "reason": "NETWORK", "text": None,
                    "detail": str(e)[:160], "budget": budget()}
    return {"ok": False, "reason": "TIMEOUT", "text": None, "budget": budget()}


# ================================================================================================
# THE FAILOVER — GEM keeps serving even though AI Studio is out of credit
# ================================================================================================
# STATE OF PLAY, measured 2026-07-12:
#   AI Studio (this key) -> 429 "Your prepayment credits are depleted."  DEAD on every model.
#   Vertex    (the OTHER key, $300 credit) -> gemini-2.5-pro answered 200.  ALIVE.
#
# GEM's JOB in the mesh is "free, high-volume verification" — the rail that caught 40/40 planted
# impossibilities. That job does not care WHICH Google endpoint serves it. So rather than leave the
# node dead, we fail over to Vertex, which is the parked task "GEM -> Vertex failover" from the
# 2026-07-12 handoff.
#
# TWO THINGS THIS MUST NOT PRETEND:
#   1. Vertex is NOT free. It draws the $300 Cloud credit, which EXPIRES ~2026-10-13. So the
#      failover picks a FLASH model, never Pro — Pro is for verification that must be right, and
#      spending Pro money on routine volume would burn the credit for nothing.
#   2. The dashboard must SAY it is on the failover. A green "GEM: OK" that is silently spending
#      credit is exactly the kind of comfortable lie this mesh keeps getting bitten by. Every
#      response carries via="vertex" and the reason the primary died.

# *** THIS CONSTANT WAS DEAD CODE UNTIL 2026-07-15. ***
# It was declared, commented, and NEVER REFERENCED. _ask_impl called bts_vertex.ask(prompt, grounded=...)
# with no model, so Vertex ran its OWN ladder — which is PRO-FIRST by design. Result: every GEM failover
# silently served gemini-2.5-PRO while this line said flash. Proven live 2026-07-15:
#   bts_gem.ask('Reply with exactly one word: OK') -> via=vertex, model=gemini-2.5-pro
# The comment below was true as INTENT and false as BEHAVIOUR for as long as the failover existed.
# bts_vertex.ask() now takes model=, and _ask_impl passes this. The constant is live.
#
# WHY FLASH: this is the VOLUME rail — GEM's job is high-count verification (the sweep that checked 141
# claims). Pro is 4x flash ($1.25/$10 vs $0.30/$2.50 per 1M). While a credit is paying and expiring
# anyway, Pro costs nothing real; the day the credit dies it bills a card at 4x for routine traffic.
# Flash is the safe default. For work that must be RIGHT, call bts_vertex.ask() directly — it is
# PRO-FIRST and that is deliberate.
VERTEX_FAILOVER_MODEL = "gemini-2.5-flash"   # cheap. NEVER default to Pro on a volume rail.
# *** HTTP_403 ADDED 2026-07-13. *** AI Studio stopped returning 429 "credits depleted" and started
# returning a bare 403 (PERMISSION_DENIED / consumer disabled). That reason was NOT in this set, so
# ask() dutifully reported the 403 and NEVER FAILED OVER — the free/credit rail looked dead while
# Vertex sat there alive. A dead primary must always be able to reach the failover; the set below is
# "the primary cannot serve this call", not "the primary is rate limited".
_FAILOVER_REASONS = {"CREDITS_DEPLETED", "RATE_LIMITED", "HTTP_404", "HTTP_403",
                     "HTTP_401", "HTTP_429", "GROUNDING_NOT_ENTITLED"}


def _ask_impl(prompt: str, priority: str = "WORK", grounded: bool = False,
        retries: int = 3, allow_failover: bool = True, images: list = None) -> dict:
    """GEM, with automatic Vertex failover. Same signature as before — callers need no changes.

    images: optional list of local PNG/JPEG paths. AI Studio cannot be fed them through this
            module (it is a text rail here), so ANY image call goes straight to Vertex, which is
            natively multimodal. Passing images therefore implies via='vertex'."""
    if images:
        # A vision call has no text-only fallback worth pretending about: go where the eyes are.
        try:
            import bts_vertex
        except Exception:
            return {"ok": False, "reason": "NO_VISION_RAIL", "text": None,
                    "detail": "images= requires bts_vertex", "via": "none", "budget": budget()}
        # *** THE DEAD-CONSTANT BUG, SECOND HALF — fixed 2026-07-16. ***
        # The failover path at the bottom of this function was fixed to pass model=; THIS one was
        # missed, so every VISION call still took bts_vertex's PRO-FIRST ladder — silently
        # contradicting this module's own constant ("NEVER default to Pro on a volume rail").
        # Two call sites, one fix applied. That is how a fixed bug stays alive.
        # Pro is 4x flash ($1.25/$10 vs $0.30/$2.50 per 1M) AND bills THINKING at the output rate —
        # measured 2026-07-16: out=101, thoughts=2883 => 28.5x, $0.0299 for a 3-sentence answer.
        # Flash is natively multimodal; it is the right default here.
        # ⇒ If a vision task genuinely needs Pro (a hard figure read), call bts_vertex.ask() DIRECTLY
        #   with model="gemini-2.5-pro". Make it a CHOICE, never an accident.
        v = bts_vertex.ask(prompt, grounded=grounded, images=images, model=VERTEX_FAILOVER_MODEL)
        v["via"] = "vertex"
        v["note"] = ("VISION CALL — routed direct to Vertex (AI Studio rail is text-only here), on %s. "
                     "For a hard figure read, call bts_vertex.ask(model='gemini-2.5-pro') directly."
                     % VERTEX_FAILOVER_MODEL)
        if v.get("ok"):
            _record_tokens(v.get("tokens") or 0)
        return v

    # 🔴 VERTEX-FIRST UNTIL 2026-10-13. KEITH'S RULING, 2026-08-12: "Use the Vertex credit."
    #
    # WHY THE ORDER IS INVERTED FROM WHAT LOOKS SENSIBLE. The AI-Studio tier is free and
    # the Vertex credit is "paid", so preferring the free lane feels obviously right. It is
    # obviously WRONG here: $286.07 of that credit EXPIRES ON A DATE CERTAIN and is
    # destroyed unspent, while the free tier does not expire at all. Measured on the
    # billing console 2026-08-12: $10.96 spent in twelve days, chart flat since Aug 3,
    # Google's own forecast $11.24 for the whole month. At that burn roughly $286 of $300
    # evaporates on 2026-10-13.
    #
    # ⇒ BURN THE EXPIRING RESOURCE FIRST. Leaving a dated credit idle to protect a lane
    #   that costs nothing and never expires is the same defect as an idle prepaid rail -
    #   the mesh's own rule: idle prepaid capacity is WASTED MONEY, not savings.
    #
    # ⇒ THIS INVERTS ON 2026-10-13. After the credit dies, AI Studio becomes the default
    #   again and Vertex needs purchased credit. That flip is in rails.toml [[clock]]
    #   "Vertex $300 credit expiry" - it must NOT live only in this comment.
    #
    # joanna.bbf holds the credit and NOTHING ELSE; keith.bbf is for everything else.
    # ⚠ AND NOBODY CLICKS "ACTIVATE" ON joanna.bbf: Keith, 2026-08-12 - "Activating that
    #   account destroys the free credits." The banner's "use any remaining credits" wording
    #   reads like preservation and is not.
    _CREDIT_EXPIRY = datetime.date(2026, 10, 13)
    if allow_failover and datetime.date.today() <= _CREDIT_EXPIRY:
        try:
            import bts_vertex
            v = bts_vertex.ask(prompt, grounded=grounded, model=VERTEX_FAILOVER_MODEL)
            if v.get("ok"):
                v["via"] = "vertex"
                v["note"] = ("VERTEX-FIRST by Keith's ruling 2026-08-12 — burning the $300 "
                             "credit before it expires %s. Reverts to AI-Studio-first after "
                             "that date." % _CREDIT_EXPIRY.isoformat())
                _record_tokens(v.get("tokens") or 0)
                return v
            # Credit gone or Vertex down: fall through to AI Studio, and SAY which happened.
            _vertex_first_failed = v.get("reason")
        except Exception as e:                                      # noqa: BLE001
            _vertex_first_failed = "VERTEX_IMPORT_OR_CALL: %s" % str(e)[:80]
    else:
        _vertex_first_failed = None

    r = ask_aistudio(prompt, priority=priority, grounded=grounded, retries=retries)
    if r.get("ok"):
        r["via"] = "aistudio"
        if _vertex_first_failed:
            r["vertex_first_failed"] = _vertex_first_failed
            r["note"] = ("Vertex was tried FIRST and failed (%s); AI Studio answered. If "
                         "this persists the credit may be exhausted or the rail down — "
                         "check, do not assume." % _vertex_first_failed)
        return r

    if not allow_failover or r.get("reason") not in _FAILOVER_REASONS:
        r["via"] = "aistudio"
        return r

    try:
        import bts_vertex
    except Exception:
        return r                                    # no vertex module -> report the real failure

    primary = r.get("reason")
    try:
        # model=VERTEX_FAILOVER_MODEL — the fix for the dead-constant bug above. Without it,
        # bts_vertex runs its PRO-FIRST ladder and this volume rail quietly costs 4x.
        v = bts_vertex.ask(prompt, grounded=grounded, model=VERTEX_FAILOVER_MODEL)
    except Exception as e:
        r["failover_error"] = str(e)[:120]
        r["via"] = "aistudio"
        return r

    if not v.get("ok"):
        # BOTH rails down. Say so honestly — do not bury it as a GEM error.
        return {"ok": False, "reason": "BOTH_RAILS_DOWN", "text": None,
                "detail": "AI Studio: %s | Vertex: %s" % (primary, v.get("reason")),
                "via": "none", "budget": budget()}

    v["via"] = "vertex"
    v["failover_from"] = primary
    # *** REWRITTEN 2026-07-15. Old text: "draws the $300 Cloud credit (expires ~2026-10-10)".
    # That credit did not exist on the account this was billing — bts_vertex was charging a card. ***
    v["note"] = ("SERVED BY VERTEX (%s), NOT THE FREE TIER. AI Studio returned %s — that is a "
                 "BILLING STATE, not a quota; it does not reset. ⚠ NOT PROVEN FREE: it is only "
                 "inferred that the $300 covers Agent Platform. Verify in Billing→Reports "
                 "('Other savings' negative + Subtotal $0.00 = the credit paid)."
                 % (v.get("model") or "?", primary))
    _record_tokens(v.get("tokens") or 0)
    return v


def ask(prompt: str, priority: str = "WORK", grounded: bool = False,
        retries: int = 3, allow_failover: bool = True, images: list = None) -> dict:
    """Public GEM entry. Identical signature/behaviour to before — this is a thin wrapper that also
    writes a PASSIVE state-feed record (bts_state.py) around the real call for the dashboard.

    It reports the TRUE rail the answer came back on (result['via'] = 'aistudio' | 'vertex'), NEVER a
    hardcoded 'free tier'. That hardcoded label is exactly the lie that made Cowork tell Keith the
    free tier was back on 2026-07-14 while ask() had silently failed over to the paid Vertex credit.
    Cost is only asserted where it is KNOWN ($0 on the free AI-Studio rail); on Vertex it is left as
    'no data' rather than invented. Telemetry never breaks the call (all failures swallowed)."""
    import time as _t
    _t0 = _t.time()
    try:
        import bts_state
        bts_state.emit("COWORK", "GEM", "api_send",
                       (prompt[:60] + "...") if len(prompt) > 60 else prompt, direction="out")
    except Exception:
        pass
    r = _ask_impl(prompt, priority=priority, grounded=grounded, retries=retries,
                  allow_failover=allow_failover, images=images)
    try:
        import bts_state
        via = (r or {}).get("via") or "unknown"
        if r and r.get("ok"):
            tok = r.get("tokens")
            detail = "via %s | %s tok" % (via, tok if tok is not None else "?")
        else:
            detail = "%s | via %s" % ((r or {}).get("reason") or "FAILED", via)
        bts_state.emit("GEM", "COWORK", "api_recv", detail, direction="in",
                       ms=round((_t.time() - _t0) * 1000, 1),
                       cost_usd=(0.0 if via == "aistudio" else None))
    except Exception:
        pass
    return r


if __name__ == "__main__":
    import sys
    b = budget()
    print("GEM budget %s: used %d/%d | POLL %d/%d" %
          (b["date"], b["used"], MAX_RPD, b["poll_used"], b["poll_cap"]))
    if len(sys.argv) > 1:
        r = ask(" ".join(sys.argv[1:]))
        print(("[%s] " % r["reason"]) + (r["text"] or ""))

