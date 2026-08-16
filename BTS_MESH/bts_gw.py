#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
bts_gw.py — THE GW (Grok Build Worker) DISPATCH RAIL.  Created 2026-07-26.

WHAT THIS FIXES
---------------
Until today the mesh had NO outbound path to GBW/GW. The watchdog decided GBW should do
T128/T129/T130/T132, wrote them into `DOM_OUTBOX.md` — and nothing on the far side ever read
that file. `bts_orchestrator.launch_session()` and `bts_conductor` were `return None` stubs.
`bts_launch.py` only ever wrote a SPAWN_QUEUE row that no executor consumed. Every arrow
pointing at GBW terminated in a markdown file or a stub.

MEASURED 2026-07-26 (this is why the module exists):
    GET  https://api.x.ai/v1/models   -> 200, and the list contains **grok-build-0.1**
    POST .../chat/completions  model=grok-build-0.1  -> 200 in 1.43 s from the Linux sandbox

**GW IS AN API MODEL.** It is not browser-only (the `bts_watchdog.py:35` comment), and it is not
only a CLI Keith drives from PowerShell (the `nodes/gbw.json` card). Both descriptions were true
of *a* GW leg and both sent us to a human-in-the-loop rail. The API leg needs no browser, no
PowerShell, no click, and runs from the sandbox in the background — which is exactly what the
Three Rules ask for.

THE CAPABILITY BOUNDARY, STATED HONESTLY
----------------------------------------
The API leg has **no filesystem**. That is NOT the old "GBW cannot read D:\" problem wearing a new
hat — it is a division of labour:

    COWORK owns the I/O  (it has V:\ mounted)   ->   GW owns the BUILDING
    Cowork reads the data and the spec, hands GW everything it needs as text,
    GW returns the artifact, Cowork writes it to disk and verifies it.

So `build()` below does the reading and the writing. GW is asked to do exactly one thing: produce
the code. That keeps the round trip to a single call instead of the GDX ferry the 2026-07-14
disposition (correctly, at the time) judged not worth it.

RULES THIS MODULE OBEYS
-----------------------
* **Never invent a number.** grok-build-0.1 has no published price in this tree, so cost is
  recorded as `None` / "unpriced" and the token counts are recorded exactly as returned.
  A ledger that guesses is worse than a ledger that says UNKNOWN.
* **Hard timeout on every call, no background jobs.** The 2026-07-20 "SGH rail hangs" were leaked
  background jobs exhausting sandbox outbound concurrency, not the rail.
* **Shares the xAI $10/month ceiling with SGH.** Same account, same money. `_ceiling_ok()` reads
  `sgh_spend.json` too, so GW cannot quietly spend SGH's budget.
* **Telemetry is best-effort and can never break a live call** (every emit in try/except), matching
  the contract in `WIRING.md`.

CLI
---
    python bts_gw.py --ping
    python bts_gw.py --spec <spec.md> --out <artifact> [--attach f1 f2 ...] [--fence html]
    python bts_gw.py --task "one-line instruction" --out <artifact>
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ---------------------------------------------------------------- paths / keys
try:
    import bts_paths as _P
    ROOT = _P.ROOT
    _SECRETS = _P.secrets()
    _MESH = _P.mesh()
except Exception:                                    # resolver unavailable -> derive locally
    _MESH = HERE
    ROOT = os.path.dirname(os.path.dirname(HERE))
    _SECRETS = os.path.join(ROOT, ".secrets")

ENDPOINT = "https://api.x.ai/v1/chat/completions"
MODELS_URL = "https://api.x.ai/v1/models"
MODEL = "grok-build-0.1"                             # MEASURED present 2026-07-26
FALLBACK_MODEL = "grok-4.5"                          # same account; used only if GW 404s

# The xAI key. Filename is the one that actually exists in .secrets (verified 2026-07-26);
# the older KEY_FILES lists in bts_sgh.py name variants that may not be present.
KEY_CANDIDATES = [
    os.path.join(_SECRETS, "Grok_API_Token-Key.txt"),
    os.path.join(_SECRETS, "xai_key.txt"),
    os.path.join(_SECRETS, "grok_key.txt"),
]

LEDGER = os.path.join(_MESH, "gw_spend.json")
SGH_LEDGER = os.path.join(_MESH, "sgh_spend.json")
MONTH_CEILING_USD = 10.00                            # OUR stop, not xAI's. Shared with SGH.
DEFAULT_TIMEOUT = 180                                # a build is a long call; still bounded

# ---------------------------------------------------------------- PRICING
# THE FIRST VERSION OF THIS MODULE RECORDED EVERY CALL AS "unpriced" AND THE LEDGER READ $0.0000.
# That was wrong in the worst available direction: a paid rail that reports as free. Two sources
# of truth existed the whole time and I used neither.
#
# 1. AUTHORITATIVE — the response itself. xAI returns `usage.cost_in_usd_ticks`,
#    1 tick = 1e-10 USD, and it INCLUDES server-side tool fees. `bts_sgh.py` has read this since
#    2026-07-12 (see its header). Prefer it over any arithmetic of ours.
# 2. FALLBACK — `GET /v1/language-models` publishes per-token prices. Unit confirmed by calibrating
#    against bts_sgh's documented table: grok-4.5 is $2.00/M in and $6.00/M out, and the API
#    reports 20000 / 60000. So **API value / 1e4 = USD per 1M tokens.**
#
#      grok-build-0.1:  in 10000 -> $1.00/M   out 20000 -> $2.00/M   cached_in 2000 -> $0.20/M
#
# Cached input is a fifth of fresh input and GW prompts repeat a large brief, so the cached share
# matters: one measured ping had 192 of 193 prompt tokens cached.
USD_PER_TICK = 1e-10
PRICES_USD_PER_M = {                    # fallback only; the ticks field wins when present
    "grok-build-0.1": {"in": 1.00, "cached_in": 0.20, "out": 2.00},
    "grok-4.5":       {"in": 2.00, "cached_in": 0.50, "out": 6.00},
}


def price_from_usage(usage, model):
    """Return (usd, source). ``source`` is 'ticks' (authoritative) or 'table' (our arithmetic).

    Never returns None: a paid call always gets a number, and the number says where it came from
    so a reader can tell a measurement from an estimate.
    """
    ticks = usage.get("cost_in_usd_ticks")
    if ticks is not None:
        try:
            return float(ticks) * USD_PER_TICK, "ticks"
        except (TypeError, ValueError):
            pass
    p = PRICES_USD_PER_M.get(model) or PRICES_USD_PER_M["grok-build-0.1"]
    pin = int(usage.get("prompt_tokens", 0) or 0)
    cached = int((usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0)
    fresh = max(0, pin - cached)
    out = int(usage.get("completion_tokens", 0) or 0)
    reason = int((usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0)
    # Reasoning tokens bill at the OUTPUT rate and sit OUTSIDE completion_tokens on some rails —
    # the uncounted-thinking bug that made Vertex look 2.39x cheaper than it was.
    usd = (fresh * p["in"] + cached * p["cached_in"] + (out + reason) * p["out"]) / 1_000_000.0
    return usd, "table"


def _key():
    for p in KEY_CANDIDATES:
        if os.path.exists(p):
            k = open(p, encoding="utf-8").read().strip().strip('"').replace("\n", "")
            if k:
                return k
    raise RuntimeError(
        "No xAI key found. Looked in:\n  " + "\n  ".join(KEY_CANDIDATES)
    )


# ---------------------------------------------------------------- telemetry
def _emit(actor, target, event, detail="", direction=None, ms=None, cost_usd=None):
    """Best-effort. Telemetry must never break a live call (WIRING.md)."""
    try:
        import bts_state
        bts_state.emit(actor, target=target, event=event, detail=detail[:120],
                       direction=direction, ms=ms, cost_usd=cost_usd)
    except Exception:
        pass


def _signal(payload):
    try:
        with open(os.path.join(_MESH, "BTS_SIGNAL.log"), "a", encoding="utf-8") as fh:
            fh.write("GW|" + json.dumps(payload) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------- ledger
def _load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def month_spend():
    """Combined xAI spend this month — GW + SGH share one account and one ceiling."""
    m = time.strftime("%Y-%m")
    tot = 0.0
    for p in (LEDGER, SGH_LEDGER):
        d = _load(p)
        if d.get("month") == m:
            for f in ("WORK", "POLL", "spend_usd"):
                try:
                    tot += float(d.get(f) or 0.0)
                except (TypeError, ValueError):
                    pass
    return tot


def _ceiling_ok():
    s = month_spend()
    return (s < MONTH_CEILING_USD), s


def _record(tok_in, tok_out, usd, ok=True):
    m = time.strftime("%Y-%m")
    d = _load(LEDGER)
    if d.get("month") != m:
        d = {"month": m, "spend_usd": 0.0, "calls": 0, "unpriced": 0,
             "tok_in": 0, "tok_out": 0, "fails": 0, "hist": []}
    d["calls"] = d.get("calls", 0) + 1
    d["tok_in"] = d.get("tok_in", 0) + int(tok_in or 0)
    d["tok_out"] = d.get("tok_out", 0) + int(tok_out or 0)
    if not ok:
        d["fails"] = d.get("fails", 0) + 1
    if usd is None:
        # NO PUBLISHED PRICE FOR grok-build-0.1 IN THIS TREE. Do not invent one.
        d["unpriced"] = d.get("unpriced", 0) + 1
    else:
        d["spend_usd"] = round(d.get("spend_usd", 0.0) + usd, 6)
    d["hist"] = (d.get("hist", []) + [{"t": int(time.time()), "in": tok_in,
                                       "out": tok_out, "usd": usd}])[-200:]
    try:
        json.dump(d, open(LEDGER, "w", encoding="utf-8"), indent=1)
    except Exception:
        pass
    return d


# ---------------------------------------------------------------- the rail
def models():
    """List model ids the key can see. Free, and the honest way to check GW exists."""
    req = urllib.request.Request(MODELS_URL, headers={"Authorization": "Bearer " + _key()})
    with urllib.request.urlopen(req, timeout=30) as r:
        return sorted(m["id"] for m in json.load(r).get("data", []))


def ask(prompt, system=None, model=MODEL, timeout=DEFAULT_TIMEOUT,
        max_tokens=32000, temperature=None, allow_fallback=True):
    """
    One bounded call to GW. Returns a dict — never raises for a rail-level failure, so a caller
    can branch on `ok` instead of wrapping everything in try/except.

    {ok, text, model, tok_in, tok_out, ms, usd(None=unpriced), reason}
    """
    ok_budget, spent = _ceiling_ok()
    if not ok_budget:
        return {"ok": False, "reason": "CEILING", "text": None,
                "detail": "xAI month-to-date $%.4f >= $%.2f ceiling (shared with SGH)"
                          % (spent, MONTH_CEILING_USD)}

    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    body = {"model": model, "messages": msgs, "max_tokens": max_tokens}
    if temperature is not None:
        body["temperature"] = temperature

    _emit("COWORK", "GBW", "api_send", prompt[:60], direction="out")
    t0 = time.time()
    try:
        req = urllib.request.Request(
            ENDPOINT, data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": "Bearer " + _key(),
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        ms = (time.time() - t0) * 1000.0
        # A 404 means this account cannot see grok-build-0.1 — fall back ONCE, and SAY SO.
        if e.code == 404 and allow_fallback and model != FALLBACK_MODEL:
            out = ask(prompt, system=system, model=FALLBACK_MODEL, timeout=timeout,
                      max_tokens=max_tokens, temperature=temperature, allow_fallback=False)
            out["fell_back_from"] = model
            return out
        _record(0, 0, None, ok=False)
        _emit("GBW", "COWORK", "api_fail", "HTTP %d" % e.code, direction="in", ms=ms)
        return {"ok": False, "reason": "HTTP_%d" % e.code, "text": None,
                "detail": detail, "ms": ms}
    except Exception as e:
        ms = (time.time() - t0) * 1000.0
        _record(0, 0, None, ok=False)
        _emit("GBW", "COWORK", "api_fail", type(e).__name__, direction="in", ms=ms)
        return {"ok": False, "reason": type(e).__name__, "text": None,
                "detail": str(e)[:300], "ms": ms}

    ms = (time.time() - t0) * 1000.0
    ch = (d.get("choices") or [{}])[0].get("message", {}) or {}
    text = ch.get("content") or ""
    u = d.get("usage", {}) or {}
    tok_in, tok_out = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
    usd, src = price_from_usage(u, d.get("model", model))
    _record(tok_in, tok_out, usd)
    _emit("GBW", "COWORK", "api_recv",
          "%s | %s tok | $%.5f (%s)" % (d.get("model", model),
                                        u.get("total_tokens", "?"), usd, src),
          direction="in", ms=ms, cost_usd=usd)
    _signal({"type": "TASK_COMPLETE", "path": None,
             "note": "%s | %s tok | $%.5f (%s) | %.0f ms"
                     % (d.get("model", model), u.get("total_tokens", "?"), usd, src, ms),
             "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return {"ok": True, "text": text, "model": d.get("model", model), "reason": None,
            "tok_in": tok_in, "tok_out": tok_out, "ms": ms, "usd": usd,
            "cost_source": src, "usage": u}


# ---------------------------------------------------------------- build helper
_FENCE = re.compile(r"```[ \t]*([A-Za-z0-9_+-]*)[ \t]*\r?\n(.*?)```", re.S)


def extract_code(text, prefer=None):
    """
    Pull the artifact out of a model reply. Returns (code, lang) or (None, None).
    Takes the LARGEST fenced block (a build reply often has small illustrative snippets
    around the real deliverable), preferring `prefer` language when given.
    """
    blocks = _FENCE.findall(text or "")
    if not blocks:
        return None, None
    if prefer:
        want = [b for b in blocks if b[0].lower() == prefer.lower()]
        if want:
            lang, code = max(want, key=lambda b: len(b[1]))
            return code.strip(), lang
    lang, code = max(blocks, key=lambda b: len(b[1]))
    return code.strip(), (lang or None)


SYSTEM = (
    "You are GW, the Grok Build Worker on KMesh — the build node of a small multi-agent mesh "
    "serving a PhD dissertation in UPS spectroscopy.\n"
    "You produce WORKING CODE, not prose about code.\n"
    "Rules:\n"
    "1. Return the complete artifact in ONE fenced code block. No truncation, no '...rest "
    "unchanged', no placeholder comments standing in for real logic.\n"
    "2. You have NO filesystem. Cowork does the reading and writing and has already given you "
    "every input you need as text. Do not ask for a file; work from what is in the prompt.\n"
    "3. Write UNKNOWN / NOT COMPUTED rather than inventing a value. A blank field is a finding; "
    "a fabricated number is a defect. This mesh has been burned by fabricated data before.\n"
    "4. If a requirement is impossible, wrong, or a bad idea, SAY SO in a short note after the "
    "code block instead of silently building around it. Disagreement is signal.\n"
    "5. Keep any commentary outside the code block to a few lines."
)


def build(spec_path, out_path, attach=None, fence=None, timeout=DEFAULT_TIMEOUT,
          max_tokens=32000):
    """
    Cowork reads the spec (+ any attachments), GW builds, Cowork writes the artifact.
    Returns a dict with the outcome; writes `out_path` only on success.
    """
    spec = open(spec_path, encoding="utf-8", errors="replace").read()
    parts = ["# BUILD ASSIGNMENT\n", spec]
    for a in (attach or []):
        try:
            body = open(a, encoding="utf-8", errors="replace").read()
        except Exception as e:
            body = "<<could not read: %s>>" % e
        parts.append("\n\n# ATTACHED INPUT — %s\n```\n%s\n```\n" % (os.path.basename(a), body))
    parts.append(
        "\n\n# DELIVERABLE\nReturn the COMPLETE contents of `%s` in one fenced block.\n"
        % os.path.basename(out_path))

    r = ask("".join(parts), system=SYSTEM, timeout=timeout, max_tokens=max_tokens)
    if not r.get("ok"):
        return r

    code, lang = extract_code(r["text"], prefer=fence)
    if not code:
        r.update({"ok": False, "reason": "NO_CODE_BLOCK",
                  "detail": (r.get("text") or "")[:400]})
        return r

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(code)

    note = re.sub(r"```.*?```", "", r["text"], flags=re.S).strip()
    r.update({"out": out_path, "bytes": len(code.encode("utf-8")),
              "lang": lang, "note": note[:1500]})
    _signal({"type": "NEW_OUTPUT_READY", "path": out_path,
             "note": "GW built %s (%d B)" % (os.path.basename(out_path),
                                             len(code.encode("utf-8"))),
             "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return r


# ---------------------------------------------------------------- CLI
def _main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="GW (Grok Build Worker) dispatch rail")
    ap.add_argument("--ping", action="store_true", help="prove the rail is up")
    ap.add_argument("--models", action="store_true", help="list visible model ids")
    ap.add_argument("--spec", help="path to a build assignment .md")
    ap.add_argument("--task", help="a one-line instruction instead of a spec file")
    ap.add_argument("--out", help="where Cowork writes the artifact")
    ap.add_argument("--attach", nargs="*", default=[], help="extra input files to inline")
    ap.add_argument("--fence", help="preferred code-fence language, e.g. html")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--max-tokens", type=int, default=32000)
    a = ap.parse_args(argv)

    if a.models:
        for m in models():
            print(("* " if m == MODEL else "  ") + m)
        return 0

    if a.ping:
        r = ask("Reply with exactly one word: OK", max_tokens=10, timeout=60)
        print(json.dumps({k: v for k, v in r.items() if k != "text"}, indent=1))
        print("text:", repr((r.get("text") or "")[:40]))
        print("xAI month-to-date (GW+SGH): $%.4f / $%.2f" % (month_spend(), MONTH_CEILING_USD))
        return 0 if r.get("ok") else 1

    if not a.out or not (a.spec or a.task):
        ap.print_help()
        return 2

    if a.spec:
        r = build(a.spec, a.out, attach=a.attach, fence=a.fence,
                  timeout=a.timeout, max_tokens=a.max_tokens)
    else:
        tmp = os.path.join(_MESH, "_gw_task.tmp.md")
        open(tmp, "w", encoding="utf-8").write(a.task)
        try:
            r = build(tmp, a.out, attach=a.attach, fence=a.fence,
                      timeout=a.timeout, max_tokens=a.max_tokens)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    print(json.dumps({k: v for k, v in r.items() if k not in ("text",)}, indent=1)[:2000])
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
