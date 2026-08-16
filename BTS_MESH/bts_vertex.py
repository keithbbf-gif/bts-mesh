"""
bts_vertex.py — VERTEX rail. Gemini 2.5 Pro on the $300 Google Cloud credit.

WHY THIS EXISTS (and why it is separate from bts_gem.py)
  The $300 Cloud credit CANNOT pay for the Gemini API in AI Studio — Google excludes it explicitly,
  and since March 2026 that exclusion is absolute for accounts opened after 2026-03-02 (ours).
  So Vertex/Agent Platform is the ONLY door the credit opens.

  *** IS FIRST-PARTY GEMINI ON VERTEX ACTUALLY CREDIT-ELIGIBLE? [G], NOT [V]. ***
  No Google page states it affirmatively. The reasoning (good, but still reasoning):
    - The trial doc says "Full access to Google Cloud, WITH SOME RESTRICTIONS" and then ENUMERATES
      the carve-outs. There are exactly two: (a) "Gemini API in AI Studio", (b) "a generative AI
      PARTNER model that is offered as a managed API (model as a service)".
    - (b) is a Vertex concept (Claude/Grok/Mistral/Llama in Model Garden). So Google WAS thinking
      about Vertex when writing the exclusions and carved out ONLY the partner models — a boundary
      drawn precisely enough to imply the other side of it.
    - The Gemini billing page puts "Gemini Enterprise Agent Platform" on the "standard Cloud
      charging cycle", which is exactly what credit pays.
  *** VERIFY, DO NOT ASSUME: make ONE small call, then read Billing -> Reports.
      "Other savings" column = credit draw (plan confirmed). "Usage cost" = the credit is NOT
      covering it. This is a ~$0.01 experiment. Run it before trusting this rail. ***
  NOTE: Vertex has been RENAMED to "Gemini Enterprise Agent Platform" — cloud.google.com/vertex-ai/*
  now 301s. The API host `aiplatform.googleapis.com` is unchanged.

THE GOTCHAS, ALL MEASURED 2026-07-12 (each one cost real time):
  1. Org policy `iam.managed.disableServiceAccountApiKeyCreation` is ON by default and its default
     allowedServices list is ONLY `generativelanguage.googleapis.com`. Vertex calls return
     403 API_KEY_SERVICE_BLOCKED until that constraint is set Not Enforced on the project.
  2. **A Google API key can be restricted to ONE API. Not two.** So a single key cannot serve both
     AI Studio and Vertex. Hence TWO keys, two files. This is the thing that took longest to see.
  3. Vertex "Express Mode" DOES accept a plain API key (x-goog-api-key) — no service account needed.
  4. Billing must be linked to the key's project, and the API enabled. Both are one-time.

LADDER IS INVERTED vs bts_gem.py: there we hoarded the cheap model to protect a tiny free quota.
Here the credit is paying, so we reach for PRO FIRST. That is the entire point of this rail.
"""
import json, os, time, datetime, threading, urllib.request, urllib.error

ENDPOINT   = "https://aiplatform.googleapis.com/v1/publishers/google/models/{m}:generateContent"
MODELS     = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-flash-latest"]   # PRO FIRST
KEY_ENV    = "VERTEX_API_KEY"
KEY_FILE   = r"V:\Research4\.secrets\vertex_key.txt"     # key restricted to AGENT PLATFORM API
USAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vertex_usage.json")

# $/1M tokens. PRICES CHANGE — re-check before trusting the spend estimate.
PRICES = {"gemini-2.5-pro":   (1.25, 10.00),
          "gemini-2.5-flash": (0.30,  2.50),
          "gemini-flash-latest": (0.30, 2.50)}
CREDIT_TOTAL = 300.00

# ══ PER-TASK CREDIT CAP — Keith, 2026-07-16 ═══════════════════════════════════════════════════════
# "Let's cap the per task budget on GEM Credit spending at $0.01 for now until we get a better
#  indication on the metering."
#
# WHY, and why it is not paranoia: the old ledger IGNORED thoughtsTokenCount, so every claim about
# this credit lasting was built on a number ~2.4x too small (up to 28.5x on a single call). MEASURED
# 2026-07-16: a THREE-SENTENCE pro answer billed in=18 out=101 thinking=2883 => $0.0299. At ~100
# calls/day that is ~$3/day => the $300 is gone in ~100 days — i.e. INSIDE the credit's own 89-day
# life. Keith: "So we will burn through those credits much faster than you supposed." Correct.
#
# ⚠ THE HONEST DIFFICULTY: **thinking cannot be priced BEFORE the call.** A post-hoc cap only tells
#    you what you already spent. So the cap is enforced TWO ways, and only one of them is a real brake:
#      (1) HARD, PRE-CALL: thinkingConfig.thinkingBudget bounds thinking tokens at the API, so the
#          worst case is BOUNDED rather than discovered. This is the actual control.
#      (2) SOFT, POST-HOC: a running TASK total that REFUSES the next call once the cap is passed.
#          This cannot un-spend the call that crossed it — it stops the bleeding, it is not a fence.
#
# TASK, not session: reset_task() at the start of each unit of work. A cap that never resets becomes
# a wall someone disables; a per-task cap keeps the brake honest.
#
# ⇒ AND THE REAL ANSWER IS ROUTING, NOT THROTTLING (Keith: "But not if you use BTS for DOM and have
#   it write answers over 1 sentence to GDX"). Over the DOM the thinking is FREE. This cap exists to
#   make the API *expensive to misuse*, so the free lane is the obvious choice — it is not a licence
#   to keep using the API more carefully.
PER_TASK_USD = 0.01
_task_spend = 0.0
_task_name = "default"

# thinkingBudget: pro accepts 128..32768; flash accepts 0..24576 (0 = thinking OFF).
# Sized so a single call's worst case stays inside PER_TASK_USD at the model's OUTPUT rate.
THINK_BUDGET_DEFAULT = {"gemini-2.5-pro": 512, "gemini-2.5-flash": 1024, "gemini-flash-latest": 1024}


def reset_task(name="default", cap_usd=None):
    """Start a new task budget. Call this at the top of each unit of work."""
    global _task_spend, _task_name, PER_TASK_USD
    _task_spend = 0.0
    _task_name = name
    if cap_usd is not None:
        PER_TASK_USD = float(cap_usd)
    return {"task": _task_name, "cap_usd": PER_TASK_USD, "spent": 0.0}


def task_budget():
    return {"task": _task_name, "cap_usd": PER_TASK_USD, "spent": round(_task_spend, 6),
            "left": round(PER_TASK_USD - _task_spend, 6)}

# ---- THE CREDIT CLOCK ---------------------------------------------------------------------------
# *** THE $300 DOES NOT RENEW. *** Verified against Google's own docs 2026-07-12: it is a ONE-TIME
# 90-day Welcome credit. "Your Free Trial ends when you spend the $300 credit or 90 days pass."
# Hard deadline. Unspent credit is simply DESTROYED — it does not roll over, and it does not
# refresh daily.
#
# (What DOES reset daily is the AI Studio FREE-TIER request quota — a different rail entirely, and
#  the one whose express prepay credits are currently depleted. Two clocks, do not conflate them.)
#
# So the incentive is inverted from a normal budget: the risk is UNDER-spending, not over-spending.
# Keith, 2026-07-12: "Spend the credits (smoke 'em if you got 'em)."
# *** REPOINTED 2026-07-15 — NEW ACCOUNT. *** The old billing accounts (01E877-…, 0142FE-…) and
# their projects were DELETED by Keith. THE OLD ONE NEVER HAD A CREDIT ON IT AT ALL: this module
# spent ~$1 of REAL MONEY off a card while every docstring here claimed it was drawing a $300
# credit. The $50 cap was the only thing that stopped it. That is the scar on this file.
#   NOW: billing account 010E47-824B53-7202F5, project project-5a33f910-1251-4d6a-bf9, under JOANNA.
#   Console 2026-07-15: "Free trial status: $300.00 credit and 90 days remaining."
#
# *** SAFETY PROPERTY THAT MAKES THIS RAIL SPENDABLE: the account is a FREE TRIAL account, which is
# NON-BILLABLE BY CONSTRUCTION. *** Google: "You will not be billed for any Google Cloud usage
# during your Free Trial" / "Free trial account indicates that your account isn't billed" /
# "you won't be charged unless you manually upgrade to a paid account".
#   ⛔ THEREFORE: **DO NOT CLICK "ACTIVATE" / "Upgrade to paid".** That converts non-billable ->
#      billable and puts Joanna's card behind every overage. The whole safety of this rail is that
#      the worst case is an ERROR, not a charge.
CREDIT_START   = "2026-07-15"     # Joanna's trial start
CREDIT_EXPIRES = "2026-10-13"     # ⚠ [U] COMPUTED (start + 90d), NOT READ FROM THE CONSOLE.
                                  # Terms §1.3 says the earlier of "$300 spent" or "3 MONTHS" —
                                  # and Google uses "3 months" and "90 days" interchangeably even
                                  # though they are not the same duration. READ the real date off
                                  # Billing -> Overview and correct this line. Do not trust it.

# SPEND_CAP was 50.00 — a sane default when we did not trust the estimator, but it is now the
# BINDING CONSTRAINT: it would strand $250 of a credit that expires anyway. Raised to the full
# credit. It stays a hard stop (the token-price estimate below is ours, not Google's authoritative
# figure, unlike xAI's cost_in_usd_ticks), but it no longer throws money away by being timid.
SPEND_CAP    = 300.00     # HARD STOP == the credit. Unspent credit is destroyed on expiry.
_lock = threading.Lock()


class VertexError(RuntimeError):
    pass


def _key():
    k = os.environ.get(KEY_ENV)
    if k: return k.strip()
    # 2026-07-30: hardcoded V:\ path FIRST (Windows cannot regress), bts_paths ADDS the sandbox
    # path so this rail runs with no desktop. Measured: Vertex answered in 0.7 s from the sandbox.
    _cands = [KEY_FILE]
    try:
        import bts_paths as _bp
        _cands.append(_bp.secrets("vertex_key.txt"))
    except Exception:
        pass
    for _p in _cands:
        if os.path.exists(_p):
            k = open(_p, encoding="utf-8").read().strip().strip('"')
            if k: return k
    raise VertexError(
        "NO VERTEX KEY. Put the key restricted to *Agent Platform API* in %s "
        "(this is a DIFFERENT key from gemini_key.txt — one key cannot serve both APIs)." % KEY_FILE)


def _load():
    try: d = json.load(open(USAGE_FILE))
    except Exception: d = {}
    d.setdefault("tokens_in", 0); d.setdefault("tokens_out", 0); d.setdefault("spend", 0.0)
    return d


def _save(d):
    tmp = USAGE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, USAGE_FILE)          # atomic; survives a restart (bts_gem's RPM bucket did NOT)


def credit_clock():
    """Days left, burn rate, and the pace required to actually USE the credit before it dies.

    *** READ THIS BEFORE QUOTING ANY NUMBER THIS FUNCTION RETURNS. ***
    `spend` is OUR OWN TOKEN ARITHMETIC (PRICES x usageMetadata). It has NEVER been reconciled
    against Google's billing. On 2026-07-15 a scheduled report divided an unverified $300 by this
    estimate, called the result "$299 about to be WASTED", and made it a headline — on an account
    that turned out to hold NO CREDIT AT ALL. Every number below is an ESTIMATE, not a measurement.
    THE ONLY GROUND TRUTH IS Billing -> Reports in the console.
    `projected_waste` in particular is a projection of a projection. Do not sound an alarm with it.

    The useful framing (when the credit is real): not "how much have I spent" but "how much must I
    spend PER DAY to avoid throwing the rest away" — a credit you did not spend is a credit you
    lost. That is only true if the credit exists and covers this rail. VERIFY BOTH FIRST."""
    import datetime as _dt
    d = _load()
    spent = d.get("spend", 0.0)
    left = max(0.0, CREDIT_TOTAL - spent)

    today = _dt.date.today()
    start = _dt.date.fromisoformat(CREDIT_START)
    exp = _dt.date.fromisoformat(CREDIT_EXPIRES)
    days_left = (exp - today).days
    days_used = max(1, (today - start).days)          # avoid /0 on day one
    total_days = max(1, (exp - start).days)

    burn_per_day = spent / days_used                   # what we ARE burning
    need_per_day = (left / days_left) if days_left > 0 else 0.0   # what we WOULD need to burn
    projected_spend = spent + burn_per_day * max(0, days_left)
    projected_waste = max(0.0, CREDIT_TOTAL - projected_spend)

    return {
        "total": CREDIT_TOTAL,
        "spent": round(spent, 4),
        "left": round(left, 2),
        "pct_used": round(100.0 * spent / CREDIT_TOTAL, 3),
        "expires": CREDIT_EXPIRES,
        "days_left": days_left,
        "days_used": days_used,
        "total_days": total_days,
        "pct_time": round(100.0 * (total_days - days_left) / total_days, 1),
        "burn_per_day": round(burn_per_day, 4),
        "need_per_day": round(need_per_day, 2),
        "projected_waste": round(projected_waste, 2),
        "renews": False,          # IT DOES NOT RENEW. One-time, 90 days, then destroyed.
        "note": ("ONE-TIME credit, expires %s. It does NOT renew daily. Unspent credit is "
                 "DESTROYED. To use it all you must burn $%.2f/day; you are burning $%.4f/day, "
                 "so you are on track to WASTE $%.2f."
                 % (CREDIT_EXPIRES, need_per_day, burn_per_day, projected_waste)),
    }


def budget():
    d = _load()
    return {"tokens_in": d["tokens_in"], "tokens_out": d["tokens_out"],
            "est_spend_usd": round(d["spend"], 4),
            "credit_left_est": round(CREDIT_TOTAL - d["spend"], 2),
            "spend_cap": SPEND_CAP}


def _image_parts(images):
    """Local image paths -> Gemini inline_data parts. Base64 of the RAW BYTES, read binary.

    WHY THIS IS SAFE TO TRUST: PNG is a self-checking container — every chunk carries a CRC32. So
    after reading we verify the signature and walk the chunks. If the bytes were corrupted in
    transit (the D: mount has served mangled copies repeatedly), the CRC fails and we RAISE rather
    than quietly shipping garbage to a model and calling the result a figure review."""
    import base64, binascii, mimetypes, struct
    parts = []
    for p in images or []:
        with open(p, "rb") as f:
            b = f.read()
        mime = mimetypes.guess_type(p)[0] or "image/png"
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            i, n = 8, 0
            while i + 8 <= len(b):
                ln = struct.unpack(">I", b[i:i+4])[0]
                typ = b[i+4:i+8]
                data = b[i+8:i+8+ln]
                crc = struct.unpack(">I", b[i+8+ln:i+12+ln])[0]
                if binascii.crc32(typ + data) & 0xFFFFFFFF != crc:
                    raise VertexError("PNG CRC FAIL in %s at chunk %s — the bytes are CORRUPT, "
                                      "refusing to send them." % (p, typ))
                n += 1
                i += 12 + ln
                if typ == b"IEND":
                    break
            if n < 2:
                raise VertexError("PNG %s has no chunks — truncated." % p)
        parts.append({"inline_data": {"mime_type": mime,
                                      "data": base64.b64encode(b).decode("ascii")}})
    return parts


def ask(prompt, grounded=False, retries=3, images=None, model=None):
    """model: force a starting model instead of the PRO-FIRST default ladder.

    *** ADDED 2026-07-15 — this parameter did not exist, and its absence was a silent cost bug. ***
    bts_gem.py declares `VERTEX_FAILOVER_MODEL = "gemini-2.5-flash"` with the comment
    "cheap. NEVER default to Pro on a volume rail" — but it had NO WAY to pass it here, so the
    constant was DEAD CODE and every GEM failover silently ran PRO. Proven live 2026-07-15:
    bts_gem.ask() -> via=vertex, model=gemini-2.5-pro. The code said flash and did Pro for days.
    Pro is 4x flash ($1.25/$10 vs $0.30/$2.50 per 1M) — harmless while a credit is paying and
    expiring anyway, a real bug the moment the credit dies and it bills a card.
    """
    d = _load()
    if d["spend"] >= SPEND_CAP:
        return {"ok": False, "reason": "SPEND_CAP_EXCEEDED", "text": None, "budget": budget()}

    # ---- PER-TASK CAP (Keith, 2026-07-16: cap GEM credit spend at $0.01/task) --------------------
    # SOFT brake: refuses the NEXT call once the task is over budget. It cannot un-spend the call
    # that crossed the line — thinking is only priceable after the fact. The HARD brake is the
    # thinkingBudget set below. Both exist because neither alone is sufficient.
    global _task_spend
    if _task_spend >= PER_TASK_USD:
        return {"ok": False, "reason": "PER_TASK_CAP",
                "text": None,
                "detail": ("task %r has spent $%.4f of its $%.4f cap. Vertex bills THINKING at the "
                           "OUTPUT rate — one 3-sentence pro answer measured $0.0299 (out=101, "
                           "thinking=2883, ratio 28.5x). USE THE FREE LANE: send this over BTS/DOM, "
                           "where the thinking costs nothing, and have it write the answer to GDX. "
                           "To raise deliberately: bts_vertex.reset_task(name, cap_usd=<usd>)."
                           % (_task_name, _task_spend, PER_TASK_USD)),
                "free_lanes": ["bts_dom_gemini", "browser_grok", "crossref", "local_pdf_library"],
                "task": task_budget(), "budget": budget()}

    parts = _image_parts(images) + [{"text": prompt}]   # images FIRST, question LAST
    body = {"contents": [{"role": "user", "parts": parts}]}
    if grounded:
        body["tools"] = [{"googleSearch": {}}]      # NOTE: Vertex uses googleSearch, AI Studio uses google_search

    if model:
        # Start at the requested model, keep the rest of the ladder as fallback (dedup, order kept).
        ladder = [model] + [m for m in MODELS if m != model]
    else:
        ladder = list(MODELS)
    mi, delay = 0, 1.0
    for attempt in range(retries * len(ladder)):
        model = ladder[min(mi, len(ladder) - 1)]
        # ---- HARD BRAKE: bound the thinking BEFORE the call --------------------------------------
        # This is the only control that actually limits cost, because thoughtsTokenCount cannot be
        # known in advance and is billed at the OUTPUT rate. Unbounded, pro spent 2883 thinking
        # tokens on a 3-sentence answer (28.5x the visible output, $0.0299 for 3 sentences).
        # Sized per-model so one call's worst case fits inside PER_TASK_USD.
        tb = THINK_BUDGET_DEFAULT.get(model)
        if tb is not None:
            body["generationConfig"] = dict(body.get("generationConfig", {}))
            body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": tb}
        req = urllib.request.Request(ENDPOINT.format(m=model), data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "x-goog-api-key": _key()})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=120))
            c = r["candidates"][0]
            txt = "".join(p.get("text", "") for p in c["content"]["parts"])
            um = r.get("usageMetadata", {}) or {}
            # ══ THE 2.39x GAP, FOUND AND FIXED 2026-07-16 ═══════════════════════════════════════
            # Keith: "maybe the GEM is more because it charges tokens for compute also".
            # He was right, and it is a BUG, not a mystery. This line used to be:
            #     ti = promptTokenCount ; to = candidatesTokenCount ; cost = ti*pi + to*po
            # *** thoughtsTokenCount IS NOT INCLUDED IN candidatesTokenCount. *** It is a SEPARATE
            # field, and Google bills reasoning/thinking tokens AT THE OUTPUT RATE. So every
            # thinking token 2.5-pro spent was invisible to this ledger and free in our arithmetic.
            #
            # MEASURED, one live call (2026-07-16):
            #     promptTokenCount 18 · candidatesTokenCount 94 · thoughtsTokenCount 1985
            #     totalTokenCount 2097  ==  18 + 94 + 1985   <- proves thoughts are NOT in candidates
            #     counted-as-was: $0.000963      truth: $0.020813      = 21.6x LOW on that call
            # The aggregate gap measured against Google's console was 2.39x (ours $0.037731 vs
            # $0.09) — the same bug, diluted across calls that thought less. Per-call it ranges from
            # ~1x (no thinking) to >20x (pro reasoning hard on a short answer).
            #
            # ⚠ THIS IS WHY THE DOM LANE MATTERS (Keith, 2026-07-16: "do we get GEM compute for
            #   free? We do over DOM — again, use BTS — DO NOT just fall back on API"). Over
            #   gemini.google.com the thinking is FREE; over this API it is billed as output at
            #   $10/1M. A reasoning-heavy question is the WORST case to send here and the BEST case
            #   to send over BTS. Route accordingly — the API is not the default, it is the fallback.
            ti = um.get("promptTokenCount", 0)
            to = um.get("candidatesTokenCount", 0)
            th = um.get("thoughtsTokenCount", 0)          # billed as OUTPUT. Never omit it again.
            pi, po = PRICES.get(model, (1.25, 10.0))
            cost = ti/1e6*pi + (to + th)/1e6*po
            with _lock:
                d = _load()
                # tokens_out now includes THINKING, because that is what is billed. Keeping them
                # apart in the ledger would re-create the very blind spot this fix closes.
                d["tokens_in"] += ti; d["tokens_out"] += (to + th)
                d["tokens_think"] = d.get("tokens_think", 0) + th   # kept split for diagnosis only
                d["spend"] += cost
                _save(d)
            _task_spend += cost
            gm = c.get("groundingMetadata", {}) or {}
            cites = [x.get("web", {}).get("uri", "") for x in gm.get("groundingChunks", [])]
            return {"ok": True, "reason": "OK", "text": txt.strip(), "model": model,
                    "citations": cites, "grounded": bool(cites),
                    "tokens": {"in": ti, "out": to, "thinking": th},
                    "task": task_budget(),
                    # thinking_ratio makes the invisible cost VISIBLE at the call site: >1 means most
                    # of what you paid for was reasoning you never saw. A high number here is the
                    # signal to route that question over BTS/DOM instead, where thinking is free.
                    "thinking_ratio": round(th / to, 1) if to else None,
                    "cost_usd": round(cost, 6), "budget": budget()}
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:200]
            if e.code == 403 and "API_KEY_SERVICE_BLOCKED" in msg:
                return {"ok": False, "reason": "KEY_NOT_SCOPED_FOR_VERTEX", "text": None,
                        "detail": "This key is not restricted to Agent Platform API. "
                                  "One key = one API; you need the SECOND key.", "budget": budget()}
            if e.code == 429:
                if mi < len(ladder) - 1:
                    mi += 1; continue
                time.sleep(delay); delay *= 2; continue
            return {"ok": False, "reason": "HTTP_%d" % e.code, "text": None,
                    "detail": msg, "budget": budget()}
        except Exception as ex:
            if attempt < retries - 1:
                time.sleep(delay); delay *= 2; continue
            return {"ok": False, "reason": "NETWORK", "text": None,
                    "detail": str(ex)[:160], "budget": budget()}
    return {"ok": False, "reason": "ALL_MODELS_EXHAUSTED", "text": None, "budget": budget()}


if __name__ == "__main__":
    import sys
    print("VERTEX budget:", budget())
    if len(sys.argv) > 1:
        r = ask(" ".join(sys.argv[1:]))
        print("[%s / %s] %s" % (r["reason"], r.get("model"), r.get("text") or ""))
        print("cost:", r.get("cost_usd"), "| budget:", r["budget"])
