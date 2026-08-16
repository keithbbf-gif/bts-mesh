#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sng_ask.py — ask SnG (SGH **and** GEM) the same brief, independently.   2026-07-26

Keith: *"SnG - that's SGH AND GEM ... You should ask them both."*
Two vendors, one question, asked separately on purpose: **where they disagree is the signal.**

WHY THIS RUNS NATIVELY ON WINDOWS AND NOT IN THE SANDBOX
--------------------------------------------------------
Two independent reasons, both MEASURED 2026-07-26:

1. **The 45-second cap.** Every Cowork bash call is killed at 45 s. SGH generates a ~600-word design
   review well past that, so the call always dies mid-flight. Native python has no such cap.

2. **The sandbox's egress to Google is blocked, and I nearly recorded that as "the keys are dead."**
   From the sandbox, *every* `googleapis.com` host returns an **HTML 403** with
   `server-timing: gfet4t7` (the Google Frontend) — including `aiplatform`, which had returned a
   proper **JSON 401** twenty minutes earlier, and including `www.googleapis.com/discovery`, which
   needs no key at all. All four keys in `.secrets` 403 identically, including a classic `AIza…` one.
   A per-key fault cannot do that. **This is the sandbox's IP, not Keith's credentials.**
   ⇒ Step 1 below re-runs those probes **where the bytes are real**. Whatever Windows says is the
   truth; the sandbox result is not evidence. (Standing scar: *a tool's failure is not evidence.*)

OUTPUT (all under 00_WORKING/):
    RAILCHECK_WINDOWS_2026-07-26.txt   ground truth on GEM/Vertex/xAI from Keith's box
    SnG_REPLY_SGH_2026-07-26.md
    SnG_REPLY_GEM_2026-07-26.md
    SnG_COMPARE_2026-07-26.md          where they agree / disagree — read this one first
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

try:
    import bts_paths
    ROOT = bts_paths.ROOT
    SECRETS = bts_paths.secrets()
except Exception:
    ROOT = r"V:\Research4"
    SECRETS = os.path.join(ROOT, ".secrets")

WORK = os.path.join(ROOT, "Ai", "PhD2_DATA_ARCHIVE", "00_WORKING")
BRIEF = os.path.join(WORK, "SnG_BRIEF_SEC_TOOL_2026-07-26.md")
STAMP = "2026-07-26"


def log(*a):
    print(*a, flush=True)


# --------------------------------------------------------------- 1. ground-truth rail check
GKEY_RE = re.compile(r"(AIza[A-Za-z0-9_-]{30,}|AQ\.[A-Za-z0-9_-]{20,})")


def google_keys():
    found, seen = [], set()
    for fn in os.listdir(SECRETS):
        p = os.path.join(SECRETS, fn)
        if not os.path.isfile(p):
            continue
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in GKEY_RE.findall(txt):
            if m not in seen:
                seen.add(m)
                found.append((fn, m))
    return found


def probe(url, headers=None, data=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()[:400], (time.time() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:400], (time.time() - t0) * 1000
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode(), (time.time() - t0) * 1000


def railcheck():
    out = ["RAIL GROUND TRUTH — run NATIVELY ON WINDOWS, %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
           "=" * 78,
           "The sandbox reported HTML 403 for EVERY googleapis host (server-timing: gfet4t7),",
           "including keyless discovery. That pattern is an egress block, not a credential fault.",
           "This file is the check re-run where the bytes are real. THIS is the evidence.", ""]

    # keyless control: if this 403s here too, something bigger is wrong
    st, body, ms = probe("https://www.googleapis.com/discovery/v1/apis?name=generativelanguage")
    kind = "JSON" if body[:1] in (b"{", b"[") else "HTML/other"
    out.append("[control] googleapis discovery (NO key): HTTP %s  %s  %.0f ms" % (st, kind, ms))
    out.append("          -> 200/JSON here means the sandbox block was the problem, not the keys.")
    out.append("")

    keys = google_keys()
    out.append("Google-shaped keys found in .secrets: %d" % len(keys))
    working = []
    for fn, k in keys:
        st, body, ms = probe(
            "https://generativelanguage.googleapis.com/v1beta/models?key=" + k)
        kind = "JSON" if body[:1] in (b"{", b"[") else "HTML"
        note = ""
        if st != 200:
            try:
                j = json.loads(body.decode("utf-8", "replace"))
                note = " | " + str(j.get("error", {}).get("message", ""))[:110]
            except Exception:
                note = " | (HTML error page — not an API response)"
        else:
            working.append((fn, k))
        out.append("  %-28s %-10s HTTP %-4s %-5s %6.0f ms%s"
                   % (fn[:28], k[:6] + "…", st, kind, ms, note))
    out.append("")

    # Vertex
    vk = os.path.join(SECRETS, "vertex_key.txt")
    if os.path.exists(vk):
        k = open(vk, encoding="utf-8").read().strip().strip('"')
        st, body, ms = probe(
            "https://aiplatform.googleapis.com/v1/publishers/google/models/"
            "gemini-2.5-flash:generateContent",
            headers={"Authorization": "Bearer " + k, "Content-Type": "application/json"},
            data=json.dumps({"contents": [{"role": "user", "parts": [{"text": "Reply OK"}]}],
                             "generationConfig": {"maxOutputTokens": 5}}).encode())
        out.append("[VERTEX] aiplatform generateContent: HTTP %s  %.0f ms" % (st, ms))
        out.append("         %s" % body.decode("utf-8", "replace")[:220].replace("\n", " "))
    out.append("")

    # xAI (control — this one worked from the sandbox)
    for fn in ("Grok_API_Token-Key.txt", "New Text Document.txt"):
        p = os.path.join(SECRETS, fn)
        if not os.path.exists(p):
            continue
        m = re.search(r"xai-[A-Za-z0-9]{20,}", open(p, encoding="utf-8", errors="replace").read())
        if not m:
            continue
        st, _, ms = probe("https://api.x.ai/v1/models",
                          headers={"Authorization": "Bearer " + m.group(0)})
        out.append("[xAI/SGH+GW] %-26s models: HTTP %s  %.0f ms" % (fn[:26], st, ms))
        break

    txt = "\n".join(out)
    open(os.path.join(WORK, "RAILCHECK_WINDOWS_%s.txt" % STAMP), "w",
         encoding="utf-8").write(txt + "\n")
    log(txt)
    return working


# --------------------------------------------------------------- 2. ask the nodes
SYS = ("You are {node} on KMesh, a small multi-agent mesh serving a PhD dissertation in UPS "
       "spectroscopy. This is a DESIGN REVIEW, not a literature search. Be concise, opinionated, "
       "and take positions — say what you would NOT do and why. Write UNKNOWN rather than guess on "
       "any factual claim; every software name, URL and DOI you give will be verified against the "
       "source. Answer Q1-Q5 in order, in markdown.")


def ask_sgh(brief):
    import bts_gw
    log("[SGH] asking (grok-4.5)…")
    r = bts_gw.ask(brief, system=SYS.format(node="SGH"), model="grok-4.5",
                   max_tokens=4000, timeout=600)
    return r


def ask_gem(brief, keys):
    """Try each working key, PRO first then flash. Returns a result dict shaped like bts_gw's."""
    if not keys:
        return {"ok": False, "reason": "NO_WORKING_GOOGLE_KEY",
                "detail": "see RAILCHECK_WINDOWS — no key returned 200 from this machine"}
    body = {"contents": [{"role": "user",
                          "parts": [{"text": SYS.format(node="GEM") + "\n\n" + brief}]}],
            "generationConfig": {"maxOutputTokens": 4000}}
    for fn, k in keys:
        for model in ("gemini-2.5-pro", "gemini-flash-latest", "gemini-2.5-flash"):
            url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                   "%s:generateContent?key=%s" % (model, k))
            log("[GEM] trying %s with %s…" % (model, fn))
            t0 = time.time()
            st, raw, ms = probe(url, headers={"Content-Type": "application/json"},
                                data=json.dumps(body).encode(), timeout=600)
            if st == 200:
                try:
                    j = json.loads(raw if len(raw) > 390 else raw)
                except Exception:
                    j = None
                # re-fetch in full (probe truncates at 400 B for the rail check)
                req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=600) as r2:
                    j = json.load(r2)
                txt = "".join(p.get("text", "") for p in
                              j["candidates"][0]["content"].get("parts", []))
                return {"ok": True, "text": txt, "model": model, "key_file": fn,
                        "ms": (time.time() - t0) * 1000,
                        "usage": j.get("usageMetadata", {})}
            log("       HTTP %s" % st)
    return {"ok": False, "reason": "ALL_MODELS_EXHAUSTED", "detail": "no model/key combination answered"}


def main():
    if not os.path.exists(BRIEF):
        log("MISSING BRIEF: %s" % BRIEF)
        return 2
    brief = open(BRIEF, encoding="utf-8").read()

    log("\n===== STEP 1: rail ground truth (Windows) =====")
    working = railcheck()

    log("\n===== STEP 2: SGH =====")
    rs = ask_sgh(brief)
    if rs.get("ok"):
        open(os.path.join(WORK, "SnG_REPLY_SGH_%s.md" % STAMP), "w", encoding="utf-8").write(
            "# SGH — reply to the SnG brief, %s\n"
            "*model %s · %.0f ms · asked independently of GEM*\n\n%s\n"
            % (STAMP, rs.get("model"), rs.get("ms") or 0, rs["text"]))
        log("[SGH] OK — %d chars" % len(rs["text"]))
    else:
        log("[SGH] FAILED: %s %s" % (rs.get("reason"), str(rs.get("detail"))[:200]))

    log("\n===== STEP 3: GEM =====")
    rg = ask_gem(brief, working)
    if rg.get("ok"):
        open(os.path.join(WORK, "SnG_REPLY_GEM_%s.md" % STAMP), "w", encoding="utf-8").write(
            "# GEM — reply to the SnG brief, %s\n"
            "*model %s · key %s · %.0f ms · asked independently of SGH*\n\n%s\n"
            % (STAMP, rg.get("model"), rg.get("key_file"), rg.get("ms") or 0, rg["text"]))
        log("[GEM] OK — %d chars" % len(rg["text"]))
    else:
        log("[GEM] FAILED: %s — %s" % (rg.get("reason"), str(rg.get("detail"))[:200]))

    # ---------------------------------------------------------- 4. the comparison stub
    lines = ["# SnG — SGH vs GEM on the SEC tool design, %s" % STAMP, "",
             "Both were asked the **same brief** (`SnG_BRIEF_SEC_TOOL_2026-07-26.md`) "
             "**independently**. Two vendors, one question — **disagreement is the signal.**", "",
             "| node | status | model | chars |", "|---|---|---|---|"]
    for nm, r in (("SGH", rs), ("GEM", rg)):
        lines.append("| %s | %s | %s | %s |" % (
            nm, "OK" if r.get("ok") else "FAILED: %s" % r.get("reason"),
            r.get("model", "—"), len(r.get("text") or "")))
    lines += ["", "> ⚠ **Cowork must now read both and write the comparison by hand.**",
              "> Do NOT average them. Where they disagree on Q1 (packaging), Q2 (the ML claim) or",
              "> Q5 (what we have wrong), that is the finding — record BOTH positions and the reason",
              "> each gives, then verify every factual claim either of them made.",
              "",
              "⚠ **SGH and GBW are the same engine (Grok). SGH vs GEM is the only genuinely",
              "independent pair in this mesh** — two Groks agreeing is one Grok twice."]
    open(os.path.join(WORK, "SnG_COMPARE_%s.md" % STAMP), "w",
         encoding="utf-8").write("\n".join(lines) + "\n")

    log("\nDone. Files in %s" % WORK)
    return 0 if (rs.get("ok") or rg.get("ok")) else 1


if __name__ == "__main__":
    sys.exit(main())
