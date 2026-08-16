"""
bts_oa_api.py — THE OPENAI **API** LANE. Built 2026-08-14.

WHY THIS EXISTS, IN ONE LINE:
  It is THE ONLY LANE WITH A MEASURED 1.05M CONTEXT WINDOW — enough to hold the ~422k-token
  war-game record WHOLE, which no chat rail can do at any tier (rails.toml [[rail]] openai-api).

⚠ DO NOT CONFUSE IT WITH `bts_oa.py`. That is the **codex / ChatGPT-plan** lane: prepaid, MCP in
  both directions, interactive. Its context ceiling is **272,000** and it CANNOT hold the record.
  On 2026-08-14 Cowork quoted the 272,000 figure as though it were this lane's, and argued against
  building the very thing that solves the problem. **Two OA lanes, two ceilings, two ledgers.**
  *(C-16 VERIFY THE REFERENT.)*

WHAT IT IS FOR — the honest division of labour against the rails we already pay for:
  - SGH / grok-4.5 ....... 500k ctx. Measured $1.47 on the same bench job from its own ledger.
  - openai-api / terra ... 1.05M ctx. ~$1.08 on that job. **TERRA UNDERCUTS SGH** and reads MORE.
  - openai-codex ......... prepaid, interactive, 272k. Reasoning-heavy chat, not bulk record work.
  ⇒ This lane is for ONE thing: a large, bounded, scriptable read that must see the whole corpus,
    written to FILE, with every cent on a ledger.

🔴 THE LEDGER IS NOT OPTIONAL, AND THIS ACCOUNT IS WHY.
  Measured from the billing console 2026-08-14: balance **$50.00**, **AUTO-RELOAD IS ON** — at $20
  it tops back up to $50, against a tier cap of $500/month.
  ⇒ **THE ACCOUNT DOES NOT SELF-LIMIT.** Running dry is not the brake; there is no brake. The only
    thing standing between a scripted loop and $500 is MONTHLY_BUDGET_USD below.
  ⇒ This is the exact defect that made `bts_sgh`'s ledger wrong: Keith, 2026-08-03 — *"it renews at
    $10 a time, it already did once, you missed it."* A prepaid top-up that re-ups is a MOVING
    ceiling, and a ledger that assumes a fixed one understates spend forever. **Record the reload.**

🔴 MODEL IDS ARE NOT VERIFIED YET. `MODELS` below carries the names as recorded in rails.toml on
  2026-08-11 from developers.openai.com/api/docs/models. **The exact API id strings have never been
  read back from the account.** `selftest()` does that FIRST, against GET /v1/models, and refuses to
  make a paid call until an id is confirmed present. A price table keyed on a guessed id prices
  nothing. *(Functional proof beats parse proof — CLAUDE.md.)*
"""
import json, os, time, datetime, urllib.request, urllib.error, threading

# ================================================================================================
# endpoint + key
# ================================================================================================
BASE      = "https://api.openai.com/v1"
ENDPOINT  = BASE + "/responses"      # modern surface. /v1/chat/completions kept as a fallback
FALLBACK  = BASE + "/chat/completions"
MODELS_EP = BASE + "/models"
KEY_ENV   = "OPENAI_API_KEY"

# Key lives OUTSIDE the published Ai\ tree, by design. V:\Research4\.secrets is a sibling of Ai\,
# so no R2 publish pass can reach it even if an exclude list misses a filename. Safe by LOCATION.
# ⚠ LABEL BY ACCOUNT. rails.toml: "there will be keys for three vendors and two Google accounts,
#   and an unlabeled store is how a failover picks the dead one."
KEY_FILES = [
    r"V:\Research4\.secrets\openai_api_key.txt",
    r"V:\Research4\.secrets\OpenAI_API_key.txt",
]
KEY_FILE = KEY_FILES[0]

# Resolve through bts_paths too, so this rail works from the LINUX SANDBOX and not only the desktop.
# Without this, bts_sgh raised "NO KEY" in the sandbox while the keys sat perfectly readable —
# which pinned every node call to Keith's desktop and broke Rule 2. Appends only; never regresses.
try:
    import bts_paths as _bp
    for _n in ("openai_api_key.txt", "OpenAI_API_key.txt"):
        _alt = _bp.secrets(_n)
        if _alt not in KEY_FILES:
            KEY_FILES.append(_alt)
except Exception:
    pass

_HERE       = os.path.dirname(os.path.abspath(__file__))
LEDGER_FILE = os.path.join(_HERE, "oa_api_spend.json")

try:
    import bts_paths as _bp_spill
    SPILL_DIR = _bp_spill.working("OA_returns")
except Exception:
    SPILL_DIR = r"V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\OA_returns"
SPILL_OVER_CHARS = 4000
SPILL_HEAD_CHARS = 600

# ================================================================================================
# prices — USD per 1M tokens. MEASURED 2026-08-11, publisher tier, recorded in rails.toml.
# ================================================================================================
MODELS = {
    "sol":   {"id": "gpt-5.6-sol",   "in": 5.00, "out": 30.00, "ctx": 1_050_000, "max_out": 128_000},
    "terra": {"id": "gpt-5.6-terra", "in": 2.00, "out": 12.00, "ctx": 1_050_000, "max_out": 128_000},
    "luna":  {"id": "gpt-5.6-luna",  "in": 0.20, "out":  1.20, "ctx": 1_050_000, "max_out": 128_000},
}
DEFAULT_TIER = "terra"     # cheapest lane that still beats SGH on the same job ($1.08 vs $1.47)

# ================================================================================================
# budget — the ONLY brake on an auto-reloading account. Raise here, in ONE place.
# ================================================================================================
MONTHLY_BUDGET_USD = 25.00
WARN_AT            = 0.80
MAX_CALL_USD       = 3.50    # one full 422k-in/20k-out bench on SOL is ~$2.71. Above that, stop.
MAX_RPM            = 60

_lock = threading.Lock()


class OaError(RuntimeError):
    pass


def _key() -> str:
    k = os.environ.get(KEY_ENV)
    if k and k.strip():
        return k.strip()
    for p in KEY_FILES:
        try:
            if os.path.exists(p):
                k = open(p, encoding="utf-8").read().strip().strip('"').strip()
                if k:          # skip EMPTY files — never let a blank shadow a good key
                    return k
        except Exception:
            continue
    raise OaError(
        "NO OPENAI KEY. Put it in the %s env var, or in one of:\n  %s\n"
        "Create one at https://platform.openai.com/api-keys .\n"
        "NEVER commit it and never put it under V:\\Research4\\Ai\\ — that tree is published to "
        "ai.dchambers.com." % (KEY_ENV, "\n  ".join(KEY_FILES)))


# ================================================================================================
# ledger — atomic, and it records RELOADS, not just calls
# ================================================================================================
def _month() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m")


class LedgerUnreadable(OaError):
    """The ledger exists and cannot be parsed. NOT the same as 'no ledger yet'."""


def _load() -> dict:
    """🔴 A FILE THAT CANNOT BE READ IS NOT A FILE THAT SAYS ZERO.

    Found by the Grok Bot QA Engineer, 2026-08-16, first pass: this function used to swallow every
    exception and return {}. budget() then computed spent=0.0, and ask() read that as permission —
    on an account with auto-reload ON. So a corrupt, locked or half-written ledger did not stop
    spending; it RESET it. The brake failed open, in the one module whose docstring says the brake
    is the only thing there is.

    Now: absent file -> a genuinely empty ledger, which is correct and is the first-run case.
         present but unreadable -> RAISE. Refuse to price, refuse to spend, say why.
    """
    if not os.path.exists(LEDGER_FILE):
        return {"calls": [], "reloads": []}
    try:
        with open(LEDGER_FILE, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:                                            # noqa: BLE001
        raise LedgerUnreadable(
            "%s exists and cannot be read (%s). REFUSING to treat that as $0 spent. "
            "This account auto-reloads, so an unreadable ledger would let a loop run against a "
            "$500 tier cap with the budget control switched off. Fix or move the file, then retry."
            % (LEDGER_FILE, e))
    if not isinstance(d, dict):
        raise LedgerUnreadable("%s did not contain an object" % LEDGER_FILE)
    d.setdefault("calls", [])
    d.setdefault("reloads", [])     # <- the SGH scar: a prepaid top-up is a MOVING ceiling
    return d


def _save(d: dict) -> None:
    # ⚠ os.replace across the FUSE mount raises FileNotFoundError (measured 2026-08-02). That is
    # why paid rails run NATIVELY. Fall back to a direct write rather than losing the record —
    # an unrecorded call is worse than a non-atomic one.
    tmp = LEDGER_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
        os.replace(tmp, LEDGER_FILE)
    except Exception:
        with open(LEDGER_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)


def record_reload(usd: float, note: str = "auto-reload") -> dict:
    """Log a prepaid top-up. Auto-reload is ON ($20 -> $50), so this WILL happen unattended."""
    with _lock:
        d = _load()
        d["reloads"].append({"ts": datetime.datetime.utcnow().isoformat() + "Z",
                             "usd": round(float(usd), 4), "note": note})
        _save(d)
    return budget()


def budget() -> dict:
    d = _load()
    m = _month()
    month_calls = [c for c in d["calls"] if c.get("ts", "").startswith(m)]
    spent = sum(c.get("usd", 0.0) for c in month_calls)
    # 🔴 A CALL WHOSE COST WAS NEVER MEASURED IS NOT A FREE CALL.
    # Found by the Grok Bot QA Engineer 2026-08-16: an answer that came back without a `usage`
    # block is written usd=0.0 and summed here, so it never consumes MONTHLY_BUDGET_USD. Its
    # words: "the meter can look healthy while money is moving."
    # The ledger must keep only BILLED TRUTH, so nothing is invented there. The BRAKE, however, is
    # allowed to be pessimistic — so unpriced calls are counted and charged at the dearest tier as
    # an explicitly labelled worst case, used ONLY to decide whether to refuse.
    unpriced = [c for c in month_calls if not c.get("cost_measured")]
    worst_each = MODELS["sol"]["in"] * 0.4 + MODELS["sol"]["out"] * 0.02
    unpriced_worst = round(len(unpriced) * worst_each, 4)
    reloaded = sum(r.get("usd", 0.0) for r in d["reloads"] if r.get("ts", "").startswith(m))
    return {
        "month": m,
        "spent": round(spent, 4),
        "budget": MONTHLY_BUDGET_USD,
        "left": round(max(0.0, MONTHLY_BUDGET_USD - spent), 4),
        "pct": round(100.0 * spent / MONTHLY_BUDGET_USD, 1) if MONTHLY_BUDGET_USD else 0.0,
        "reloaded_this_month": round(reloaded, 4),
        "unpriced_calls": len(unpriced),
        "unpriced_worst_case": unpriced_worst,
        "warn": (spent + unpriced_worst) >= MONTHLY_BUDGET_USD * WARN_AT,
        # the brake uses the pessimistic figure; the ledger above keeps only measured money
        "exhausted": (spent + unpriced_worst) >= MONTHLY_BUDGET_USD,
    }


def _price(tier: str, tok_in: int, tok_out: int) -> float:
    m = MODELS[tier]
    return (tok_in / 1_000_000.0) * m["in"] + (tok_out / 1_000_000.0) * m["out"]


def _usage(raw: dict):
    """Parse usage from EITHER surface. They use different field names AND different conventions.

    /v1/responses         : input_tokens  / output_tokens  (output INCLUDES reasoning)
    /v1/chat/completions  : prompt_tokens / completion_tokens (+ reasoning counted separately)
    Adding a reasoning field unconditionally double-counts on /v1/responses. This bit bts_sgh.
    Returns (tok_in, tok_out, measured: bool). measured=False means DO NOT TRUST THE COST.
    """
    u = raw.get("usage") or {}
    if "input_tokens" in u or "output_tokens" in u:
        return int(u.get("input_tokens", 0)), int(u.get("output_tokens", 0)), True
    if "prompt_tokens" in u or "completion_tokens" in u:
        ti = int(u.get("prompt_tokens", 0))
        to = int(u.get("completion_tokens", 0))
        det = u.get("completion_tokens_details") or {}
        if "reasoning_tokens" in det:
            to += int(det.get("reasoning_tokens") or 0)
        return ti, to, True
    return 0, 0, False


def _text(raw: dict) -> str:
    if isinstance(raw.get("output_text"), str):
        return raw["output_text"]
    out = []
    for item in raw.get("output") or []:
        for c in item.get("content") or []:
            if isinstance(c.get("text"), str):
                out.append(c["text"])
    if out:
        return "\n".join(out)
    for ch in raw.get("choices") or []:
        msg = ch.get("message") or {}
        if isinstance(msg.get("content"), str):
            out.append(msg["content"])
    return "\n".join(out)


def _post(url: str, body: dict, timeout: int = 900) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + _key(),
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def list_models() -> list:
    """GET /v1/models. Cheap, unmetered, and the ONLY way to learn the real id strings."""
    req = urllib.request.Request(MODELS_EP, headers={"Authorization": "Bearer " + _key()})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8"))
    return sorted(m.get("id", "") for m in d.get("data", []))


def resolve(tier: str = DEFAULT_TIER) -> str:
    """Confirm the model id EXISTS on this account before spending anything on it."""
    want = MODELS[tier]["id"]
    have = list_models()
    if want in have:
        return want
    cand = [m for m in have if tier in m]
    raise OaError(
        "MODEL ID NOT CONFIRMED. rails.toml records '%s' for tier '%s', and the account does not "
        "list it.\n  candidates containing '%s': %s\n  Update MODELS[%r]['id'] to the real string "
        "and re-run selftest. Do NOT price a call against an id the account does not have."
        % (want, tier, tier, cand or "(none)", tier))


def ask(prompt: str, tier: str = DEFAULT_TIER, max_output_tokens: int = 20000,
        spend_ok: float = None, spill_name: str = None, timeout: int = 900,
        previous_response_id: str = None, store: bool = True) -> dict:
    """One call. Refuses if the month's budget is spent or the estimate exceeds MAX_CALL_USD."""
    if tier not in MODELS:
        raise OaError("unknown tier %r — one of %s" % (tier, list(MODELS)))
    b = budget()
    if b["exhausted"]:
        return {"ok": False, "reason": "MONTHLY_BUDGET_EXHAUSTED", "text": None, "budget": b}

    est_in = max(1, len(prompt) // 4)                       # ~4 chars/token, deliberately rough
    est = _price(tier, est_in, max_output_tokens)
    ceiling = spend_ok if spend_ok is not None else MAX_CALL_USD
    if est > ceiling:
        return {"ok": False, "reason": "ESTIMATE_OVER_CEILING", "text": None,
                "estimate_usd": round(est, 4), "ceiling_usd": ceiling, "budget": b}

    model = resolve(tier)
    t0 = time.time()
    body = {"model": model, "input": prompt, "max_output_tokens": int(max_output_tokens),
            "store": bool(store)}
    if previous_response_id:
        # CHAINING. Lets a follow-up reference a 438k-token record WITHOUT resending it.
        # Without this, "a little back and forth" costs ~$1.00 per question instead of cents.
        body["previous_response_id"] = previous_response_id
    try:
        raw = _post(ENDPOINT, body, timeout=timeout)
        surface = "responses"
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        if e.code not in (400, 404):
            raise OaError("HTTP %s from %s: %s" % (e.code, ENDPOINT, detail))
        raw = _post(FALLBACK, {"model": model,
                               "messages": [{"role": "user", "content": prompt}],
                               "max_completion_tokens": int(max_output_tokens)}, timeout=timeout)
        surface = "chat_completions"

    dt = time.time() - t0
    tok_in, tok_out, measured = _usage(raw)
    usd = _price(tier, tok_in, tok_out) if measured else None
    text = _text(raw)

    spill = None
    if text and len(text) > SPILL_OVER_CHARS:
        try:
            os.makedirs(SPILL_DIR, exist_ok=True)
            name = spill_name or ("oa_%s.md" % datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S"))
            spill = os.path.join(SPILL_DIR, name)
            with open(spill, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception:
            spill = None

    with _lock:
        d = _load()
        d["calls"].append({"ts": datetime.datetime.utcnow().isoformat() + "Z",
                           "tier": tier, "model": model, "surface": surface,
                           "tok_in": tok_in, "tok_out": tok_out,
                           "usd": round(usd, 6) if usd is not None else 0.0,
                           "response_id": raw.get("id"),
                           "prev": previous_response_id,
                           "cost_measured": measured, "secs": round(dt, 2),
                           "spill": spill})
        _save(d)

    return {"ok": True, "response_id": raw.get("id"),
            "text": (text[:SPILL_HEAD_CHARS] if spill else text),
            "spill": spill, "full_len": len(text or ""), "tier": tier, "model": model,
            "surface": surface, "tok_in": tok_in, "tok_out": tok_out,
            "usd": usd, "cost_measured": measured, "secs": round(dt, 2),
            "budget": budget()}


def selftest(verbose: bool = True) -> bool:
    """Key -> models -> id resolution -> ONE cheap live call. Prints what it could not prove."""
    ok = True
    try:
        _key()
        if verbose: print("[ok]   key found")
    except OaError as e:
        print("[FAIL] %s" % e); return False
    try:
        have = list_models()
        if verbose: print("[ok]   /v1/models reachable — %d models" % len(have))
    except Exception as e:
        print("[FAIL] /v1/models: %s" % e); return False
    for tier in MODELS:
        try:
            print("[ok]   %-5s -> %s" % (tier, resolve(tier)))
        except OaError as e:
            print("[WARN] %s" % e); ok = False
    if not ok:
        print("\nMODEL IDS UNCONFIRMED. Fix MODELS[...]['id'] before any paid run.")
        return False
    r = ask("Reply with exactly: OK", tier="luna", max_output_tokens=16)
    print("[%s] live call — %s | %s tok in / %s tok out | $%s | %.2fs"
          % ("ok" if r.get("ok") else "FAIL", (r.get("text") or "").strip()[:40],
             r.get("tok_in"), r.get("tok_out"), r.get("usd"), r.get("secs") or 0))
    if not r.get("cost_measured"):
        print("[WARN] usage not returned — COST IS NOT MEASURED. Do not trust the ledger figure.")
    print("       budget: %s" % json.dumps(r.get("budget")))
    return bool(r.get("ok"))


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        raise SystemExit(0 if selftest() else 1)
    if "--budget" in sys.argv:
        print(json.dumps(budget(), indent=1)); raise SystemExit(0)
    if "--models" in sys.argv:
        print("\n".join(list_models())); raise SystemExit(0)
    print(__doc__)
