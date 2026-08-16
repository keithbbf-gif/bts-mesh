#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
rail_check.py — daily rail health, run NATIVELY on Windows.   2026-07-26

WHY THIS EXISTS
---------------
The Cowork scheduled task `free-tier-allotment-check` produced **seven consecutive days of
"BLOCKED — nothing measured"** (2026-07-19 → 2026-07-26). Its cause was not a bug in its prompt:
`V:\Research4` is not in that task's connected-folder set, so the run cannot reach `.secrets`,
and an unattended run cannot request a folder. The folder set is not a file anyone can edit —
only `SKILL.md` exists on disk — so the task could not fix itself and neither could I.

**The fix is to stop needing the mount.** Run natively on Windows, where `V:` is just a drive
letter, and write the report somewhere everything can read.

It also removes a second failure this project measured the same day: Cowork's Linux sandbox is
**egress-blocked from every `googleapis.com` host** (HTML 403, `server-timing: gfet4t7`, including
*keyless* discovery). A probe run from there reports GEM and Vertex as dead when they are not.
**Rails must be probed from the machine that owns the credentials.**

WHAT IT DOES
------------
Probes SGH, GW, GEM and Vertex; reads the SGH/GW ledgers; checks the GDX 7-day consent fuse; and
writes a dated report to the archive **and** to the ODX surface, so a Cowork session that lacks
`V:` can still read the result.

RULES IT KEEPS
--------------
* **Report only what is measured.** Anything unreachable is `NOT MEASURED`, never inferred.
  This task once reported a **$299 phantom waste** on a billing account that never held a credit,
  by dividing an unverified number by its own token arithmetic. Never again.
* **Price the harm before sounding an alarm.** A number that sounds expensive is not a cost.
* **No paid calls beyond the 1-token pings** (~$0.0003 each). No grounded search, ever.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

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
ODX = r"D:\ODX\OneDrive\BTS_ODX\reports"
MESH = os.path.join(ROOT, "Ai", "BTS_MESH")
CEILING = 10.00                      # our stop on the shared xAI account, not xAI's

# 🔴 ASK THE MODULE, DO NOT COPY THE NUMBER. This ceiling is the ONLY brake on an auto-reloading
# OpenAI account, and a second hand-written copy of it is a copy that rots — the same failure that
# put five different tool counts in one handoff in one session. If bts_oa_api cannot be imported the
# row still renders, against a value labelled as a fallback rather than a reading.
try:
    sys.path.insert(0, MESH)
    from bts_oa_api import MONTHLY_BUDGET_USD as OA_BUDGET
except Exception:                                                     # noqa: BLE001
    OA_BUDGET = 25.00


def probe(url, headers=None, data=None, timeout=30, limit=400):
    """Return (status, body, ms). ``limit=None`` reads the whole body.

    The truncation default keeps error pages short in the report. **Pass ``limit=None`` whenever
    you intend to SEARCH the body**, because a substring check against a truncated response is a
    false-negative generator: this function's first version clipped the xAI model list at 400 bytes
    and duly reported `grok-build-0.1` as MISSING on the very first run, when it was present about
    two kilobytes in. A daily alarm that cries wolf gets muted, and a muted alarm is worse than none
    — which is exactly how the task this replaces became seven days of ignored noise.
    """
    req = urllib.request.Request(url, data=data, headers=headers or {})
    t0 = time.time()

    def _clip(raw):
        return raw if limit is None else raw[:limit]

    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, _clip(r.read()), (time.time() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, _clip(e.read()), (time.time() - t0) * 1000
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode(), (time.time() - t0) * 1000


def read_text(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def find_key(pattern, *filenames):
    """First token matching `pattern` across the named .secrets files."""
    rx = re.compile(pattern)
    for fn in filenames:
        m = rx.search(read_text(os.path.join(SECRETS, fn)))
        if m:
            return m.group(0)
    if os.path.isdir(SECRETS):
        for fn in sorted(os.listdir(SECRETS)):
            p = os.path.join(SECRETS, fn)
            if os.path.isfile(p):
                m = rx.search(read_text(p))
                if m:
                    return m.group(0)
    return None


def money(path, fields=("WORK", "POLL", "spend_usd")):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None, {}
    if d.get("month") != time.strftime("%Y-%m"):
        return 0.0, d
    return sum(float(d.get(f) or 0.0) for f in fields), d


def main() -> int:
    rows, notes = [], []
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")

    # ---------------- xAI: SGH + GW ----------------
    xai = find_key(r"xai-[A-Za-z0-9]{20,}", "Grok_API_Token-Key.txt", "New Text Document.txt")
    if not xai:
        rows.append(("SGH / GW (xAI)", "NOT MEASURED", "no xai- key found in .secrets"))
    else:
        # limit=None: we search this body, so it must not be truncated.
        st, body, ms = probe("https://api.x.ai/v1/models",
                             headers={"Authorization": "Bearer " + xai}, limit=None)
        ids: list[str] = []
        if st == 200:
            try:
                ids = sorted(m["id"] for m in json.loads(body.decode() or "{}").get("data", []))
            except Exception:
                ids = []
        rows.append(("SGH / GW (xAI)", f"HTTP {st}", f"{ms:.0f} ms · {len(ids)} models visible"))
        # Published per-token prices, straight from the API. Unit: value / 1e4 = USD per 1M tokens,
        # confirmed to 100.00% against a live call's authoritative `cost_in_usd_ticks`.
        try:
            pr = {m["id"]: m for m in json.loads(body.decode() or "{}").get("data", [])}
            for mid in ("grok-build-0.1", "grok-4.5"):
                m = pr.get(mid)
                if m:
                    rows.append((f"  └ {mid} price",
                                 f"${m['prompt_text_token_price'] / 1e4:.2f}/M in · "
                                 f"${m['completion_text_token_price'] / 1e4:.2f}/M out",
                                 f"cached in ${m.get('cached_prompt_text_token_price', 0) / 1e4:.2f}/M"))
        except Exception:
            pass
        # GW is a MODEL on this key, not a separate rail. Confirm it is still listed — its
        # disappearance would silently break every build dispatch, and we would find out by a
        # forge run failing rather than by an alarm.
        present = "grok-build-0.1" in ids
        rows.append(("  └ grok-build-0.1",
                     "present" if present else ("**MISSING**" if ids else "NOT MEASURED"),
                     "GW dispatch depends on this model id"
                     if ids else "model list could not be parsed"))
        if ids and not present:
            notes.append(
                "`grok-build-0.1` is gone from the xAI model list. GW dispatch (`bts_gw.py`) will "
                "404 and fall back to grok-4.5, reporting `fell_back_from` — check for that before "
                "trusting any build output."
            )

    # ---------------- Gemini (AI Studio) ----------------
    gkey = find_key(r"(AIza[A-Za-z0-9_-]{30,}|AQ\.[A-Za-z0-9_-]{20,})", "gemini_key.txt")
    if not gkey:
        rows.append(("GEM (AI Studio)", "NOT MEASURED", "no Google-shaped key found"))
    else:
        st, body, ms = probe(
            "https://generativelanguage.googleapis.com/v1beta/models?key=" + gkey)
        kind = "JSON" if body[:1] in (b"{", b"[") else "HTML"
        detail = f"{ms:.0f} ms · {kind}"
        if st == 429:
            b = body.decode("utf-8", "replace")
            detail += (" · PREPAY DEPLETED (billing state, does NOT reset at midnight)"
                       if "prepay" in b.lower() else " · quota (resets midnight PT) — PASS")
        rows.append(("GEM (AI Studio)", f"HTTP {st}", detail))
        if kind == "HTML" and st == 403:
            notes.append(
                "GEM returned an **HTML** 403 rather than the API's JSON. From Cowork's sandbox "
                "that pattern means the *network* is blocked, not the key. Seeing it **here**, on "
                "the machine that owns the credential, is different and does implicate the key or "
                "the project — but confirm against a keyless endpoint before concluding."
            )

    # keyless control: distinguishes a network block from a credential fault
    st, body, _ = probe("https://www.googleapis.com/discovery/v1/apis?name=generativelanguage")
    rows.append(("  └ keyless control", f"HTTP {st}",
                 "200/JSON ⇒ network fine, so a 403 above is the credential"
                 if st == 200 else "non-200 ⇒ network/egress problem, NOT the keys"))

    # ---------------- Vertex ----------------
    vkey = read_text(os.path.join(SECRETS, "vertex_key.txt")).strip().strip('"')
    if not vkey:
        rows.append(("VERTEX", "NOT MEASURED", "vertex_key.txt missing"))
    else:
        # AUTH STYLE MUST MATCH PRODUCTION. `bts_vertex.py` sends `x-goog-api-key`, which is the
        # canonical header for a Google API key. An earlier version of this probe used
        # `Authorization: Bearer`, got a truthful 401 ("Expected OAuth 2 access token"), and this
        # file recorded "VERTEX DEAD" — twice. Vertex was fine the whole time.
        #
        # A monitor that exercises a rail differently from the way production exercises it does not
        # measure the rail. It measures the monitor. Measured 2026-07-26:
        #     Authorization: Bearer -> 401     ?key= -> 200     x-goog-api-key -> 200
        #
        # thinkingBudget=0 matters too: with maxOutputTokens=8 and thinking unbounded, the reply
        # came back empty with finishReason=MAX_TOKENS because reasoning tokens ate the budget.
        st, body, ms = probe(
            "https://aiplatform.googleapis.com/v1/publishers/google/models/"
            "gemini-2.5-flash:generateContent",
            headers={"x-goog-api-key": vkey, "Content-Type": "application/json"},
            data=json.dumps({
                "contents": [{"role": "user", "parts": [{"text": "Reply with one word: OK"}]}],
                "generationConfig": {"maxOutputTokens": 16,
                                     "thinkingConfig": {"thinkingBudget": 0}},
            }).encode())
        rows.append(("VERTEX", f"HTTP {st}",
                     f"{ms:.0f} ms · x-goog-api-key (same auth as bts_vertex.py)"))

    # ---------------- OpenAI API (bts_oa_api) — the 1.05M-context lane ----------------
    # UNMETERED PROBE, DELIBERATELY. GET /v1/models costs nothing and is the only way to learn the
    # real id strings. A daily monitor must never spend money to prove a rail is up; that is how a
    # health check becomes the biggest line on the bill. The id check is the point: bts_oa_api
    # REFUSES a paid call against an id the account does not list (S-135), so an id disappearing
    # from this list is the alarm, and it would otherwise surface as a war-game run failing.
    okey = read_text(os.path.join(SECRETS, "openai_api_key.txt")).strip().strip('"')
    if not okey:
        rows.append(("OA API (openai-api)", "NOT MEASURED", "openai_api_key.txt missing"))
    else:
        st, body, ms = probe("https://api.openai.com/v1/models",
                             headers={"Authorization": "Bearer " + okey}, limit=None)
        oids: list[str] = []
        if st == 200:
            try:
                oids = sorted(m["id"] for m in json.loads(body.decode() or "{}").get("data", []))
            except Exception:
                oids = []
        rows.append(("OA API (openai-api)", f"HTTP {st}",
                     f"{ms:.0f} ms · {len(oids)} models visible · 1.05M ctx in / 128K max out"))
        # Prices are NOT returned by this endpoint. They are the MEASURED publisher figures from
        # rails.toml, restated here so the row is readable without opening another file — and
        # labelled as their source, because a number with no provenance rots into an assertion.
        for tier, mid, pin, pout in (("terra", "gpt-5.6-terra", 2.00, 12.00),
                                     ("luna",  "gpt-5.6-luna",  0.20,  1.20),
                                     ("sol",   "gpt-5.6-sol",   5.00, 30.00)):
            rows.append((f"  └ {mid}",
                         "present" if mid in oids else ("**MISSING**" if oids else "NOT MEASURED"),
                         f"${pin:.2f}/M in · ${pout:.2f}/M out (rails.toml, publisher tier)"
                         if oids else "model list could not be parsed"))
        if oids and "gpt-5.6-terra" not in oids:
            notes.append(
                "`gpt-5.6-terra` is gone from the OpenAI model list. It is `bts_oa_api.DEFAULT_TIER`, "
                "and `resolve()` REFUSES rather than silently substituting — so every openai-api call "
                "will raise `MODEL ID NOT CONFIRMED` until `MODELS['terra']['id']` is corrected."
            )

    # ---------------- OA API spend, against OUR ceiling (the account has none) ----------------
    # 🔴 THIS ACCOUNT AUTO-RELOADS: $20 -> $50, tier cap $500/mo. Running out of money is NOT the
    # brake. MONTHLY_BUDGET_USD in bts_oa_api.py is the only brake, so it is what this row measures.
    try:
        _oa = json.load(open(os.path.join(MESH, "oa_api_spend.json"), encoding="utf-8"))
        _mo = time.strftime("%Y-%m")
        _calls = [c for c in _oa.get("calls", []) if str(c.get("ts", "")).startswith(_mo)]
        _spent = sum(c.get("usd", 0.0) for c in _calls)
        _unmeasured = sum(1 for c in _calls if not c.get("cost_measured"))
        _reloads = sum(r.get("usd", 0.0) for r in _oa.get("reloads", [])
                       if str(r.get("ts", "")).startswith(_mo))
        rows.append(("OA API month-to-date", f"${_spent:.4f} / ${OA_BUDGET:.2f}",
                     f"{len(_calls)} call(s) · {_unmeasured} with UNMEASURED cost · "
                     f"${_reloads:.2f} reloaded this month · cap is ours, not the account's"))
        if _unmeasured:
            notes.append(
                f"{_unmeasured} openai-api call(s) this month returned no `usage` block, so their "
                f"cost is recorded as $0 and the month-to-date figure UNDERSTATES spend. "
                f"`cost_measured=false` is the field to grep."
            )
    except Exception as e:                                            # noqa: BLE001
        rows.append(("OA API month-to-date", "NOT MEASURED", f"oa_api_spend.json: {e}"))

    # ---------------- spend, against OUR ceiling ----------------
    sgh_spend, _ = money(os.path.join(MESH, "sgh_spend.json"))
    gw_spend, gw = money(os.path.join(MESH, "gw_spend.json"))
    total = (sgh_spend or 0.0) + (gw_spend or 0.0)
    rows.append(("xAI month-to-date", f"${total:.4f} / ${CEILING:.2f}",
                 f"SGH ${sgh_spend or 0:.4f} + GW ${gw_spend or 0:.4f} (shared account)"))
    if gw.get("unpriced"):
        # Historical calls only. GW is priced from 2026-07-27; see bts_gw.price_from_usage().
        ti, to = gw.get("tok_in", 0), gw.get("tok_out", 0)
        lo = (ti * 1.00 + to * 2.00) / 1e6                       # all input fresh, no reasoning
        hi = (ti * 1.00 + to * 2.0 * 2.0) / 1e6                  # + reasoning ~= output
        notes.append(
            f"{gw['unpriced']} GW calls predate pricing and are recorded at $0. Reconstructed from "
            f"{ti:,} prompt + {to:,} completion tokens at $1.00/M in, $2.00/M out: "
            f"**~${lo:.2f}–${hi:.2f}** (range because the cached share and reasoning tokens were "
            f"not logged). The ${total:.4f} figure above EXCLUDES this. Every call from "
            f"2026-07-27 carries its exact cost from `usage.cost_in_usd_ticks`."
        )

    # ---------------- GDX: refresh it, don't just look at it ----------------
    # A monitor that reports a fuse burning down is less useful than one that resets it. The
    # refresh needs no browser; only the 7-day Testing-mode CONSENT does. So the daily run keeps
    # the access token alive and only escalates when the consent itself has lapsed.
    #
    # Note the check is a REFRESH, not a field inspection. On 2026-07-27 a credential with a
    # perfectly good-looking file passed read and write and was an online-only token that expired
    # in an hour. Exercising the refresh is the only thing that distinguishes the two.
    cred = os.path.join(ROOT, "Ai", "credentials.json")
    if not os.path.exists(cred):
        rows.append(("GDX", "NOT MEASURED", "Ai\\credentials.json not found — run gdx_fresh_auth.py"))
    else:
        age_d = (time.time() - os.path.getmtime(cred)) / 86400.0
        try:
            d = json.load(open(cred, encoding="utf-8"))
            tr = d.get("token_response", {}) or {}
            cid = d.get("client_id") or tr.get("client_id")
            csec = d.get("client_secret") or tr.get("client_secret")
            rtok = d.get("refresh_token") or tr.get("refresh_token")
        except Exception as e:
            cid = csec = rtok = None
            notes.append(f"credentials.json unreadable: {type(e).__name__}")

        if not rtok:
            rows.append(("GDX", "**NO REFRESH TOKEN**",
                         "online-only credential — dies within the hour and cannot be renewed"))
            notes.append(
                "`credentials.json` has no refresh token. It was almost certainly minted with "
                "`access_type=online`. Re-run `gdx_fresh_auth.py`, which forces "
                "`access_type=offline` + `approval_prompt=force`."
            )
        else:
            body = urllib.parse.urlencode({
                "client_id": cid, "client_secret": csec,
                "refresh_token": rtok, "grant_type": "refresh_token"}).encode()
            st, raw, ms = probe("https://oauth2.googleapis.com/token", data=body,
                                headers={"Content-Type": "application/x-www-form-urlencoded"},
                                limit=None)
            try:
                j = json.loads(raw.decode("utf-8", "replace"))
            except Exception:
                j = {}
            if st == 200 and j.get("access_token"):
                d["access_token"] = j["access_token"]
                d.setdefault("token_response", {})["access_token"] = j["access_token"]
                d["token_expiry"] = time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(time.time() + int(j.get("expires_in", 3599))))
                d["invalid"] = False
                try:
                    json.dump(d, open(cred, "w", encoding="utf-8"), indent=1)
                except OSError:
                    pass
                rows.append(("GDX", f"HTTP {st} · REFRESHED",
                             f"{ms:.0f} ms · consent {age_d:.1f} d old (browser needed at ~7 d)"))
            else:
                rows.append(("GDX", f"refresh FAILED HTTP {st}",
                             f"{j.get('error', '?')} — consent {age_d:.1f} d old"))
                notes.append(
                    "GDX refresh failed. If the error is `invalid_grant` the Testing-mode consent "
                    "has lapsed and a human must re-consent: run `gdx_fresh_auth.py`."
                )

    # ---------------- MCP rail: bts-fs (added 2026-07-28) ----------------
    # Exercise the rail EXACTLY THE WAY THE CLIENTS DO: read the launch command out of
    # the client config and run THAT — never a path hardcoded here. This file already
    # carries the lesson in its own history ("a monitor that exercises a rail
    # differently from the way production exercises it measures the monitor", the
    # Vertex 401 that was a wrong auth header). If the wiring rots, this catches it;
    # a hardcoded path would keep reporting green while every client saw nothing.
    import subprocess
    mcp_cmd = None
    try:
        _cfg = json.load(open(r"V:\Research4\.mcp.json", encoding="utf-8-sig"))
        # Renamed bts-fs -> BFast on 2026-07-30. Accept BOTH while any client config may still hold
        # the old key: a rail check that hard-fails on a rename reports a DEAD rail that is running.
        _srv = _cfg["mcpServers"]
        _e = _srv.get("BFast") or _srv.get("bts-fs") or next(iter(_srv.values()))
        mcp_cmd = [_e["command"]] + list(_e.get("args", []))
    except Exception as e:
        rows.append(("MCP BFast", "NOT MEASURED", f"could not read .mcp.json: {e}"))

    if mcp_cmd:
        handshake = (
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                        "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                                   "clientInfo": {"name": "rail_check", "version": "1"}}}) + "\n"
            + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n"
            + json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                          "params": {"name": "fs_roots", "arguments": {}}}) + "\n")
        try:
            t0 = time.time()
            proc = subprocess.Popen(mcp_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True,
                                    encoding="utf-8", errors="replace")
            out, _ = proc.communicate(handshake, timeout=60)
            ms = (time.time() - t0) * 1000
            n_tools, roots_txt = 0, ""
            for line in out.splitlines():
                try:
                    m = json.loads(line)
                except Exception:
                    continue
                if m.get("id") == 2:
                    n_tools = len(m.get("result", {}).get("tools", []))
                if m.get("id") == 3:
                    roots_txt = m.get("result", {}).get("content", [{}])[0].get("text", "")
            live = roots_txt.count("OK        ")
            dead = roots_txt.count("UNAVAILABLE")
            if n_tools:
                rows.append(("MCP BFast", f"{n_tools} tools", f"{ms:.0f} ms · {live} roots live"
                                                               + (f" · **{dead} UNAVAILABLE**" if dead else "")))
                if dead:
                    notes.append(
                        f"{dead} MCP root(s) report UNAVAILABLE. Every path under them HARD-ERRORS "
                        f"by design rather than returning an empty result — check `roots.json`."
                    )
            else:
                rows.append(("MCP BFast", "**NO TOOLS**", f"{ms:.0f} ms · handshake gave nothing back"))
                notes.append("The MCP server started but returned no tools. Run "
                             "`V:\\Research4\\Ai\\BTS_MCP\\PROBE_MCP.bat` for the full transcript.")
        except Exception as e:
            rows.append(("MCP BFast", "**DOWN**", f"{type(e).__name__}: {e}"))
            notes.append("The MCP server did not answer a handshake. GW and GEM lose their shared "
                         "filesystem tools until it does: `V:\\Research4\\Ai\\BTS_MCP\\PROBE_MCP.bat`.")

    # Static registration check — is the MCP server still wired into each client's own config?
    # Cheap, and it catches the case where a client update rewrites its config file.
    #
    # 🔴 2026-07-31: THIS CHECK WAS REPORTING A FALSE **NO** ON BOTH CLIENTS, and had been since
    # 2026-07-30. The server was RENAMED bts-fs -> BFast that day; `wire_clients.py` carries
    # NAME = "BFast" plus OLD_NAMES = ["bts-fs"], and its rename pass DELIBERATELY STRIPS the old
    # key from every client config so no node ends up with one server registered twice. This
    # checker went on grepping for the literal "bts-fs" — so the rename's success was reported as
    # the registration's failure, nightly, in the file we read at BootUP!.
    # ⇒ The defect was TWO COPIES OF ONE CONSTANT. The name is now IMPORTED from the module that
    # writes it, so a future rename cannot desynchronise them: one definition, two readers.
    # ⇒ And an OLD name found alone is its own distinct state — STALE, meaning the client never got
    # the rename pass — not the same as missing. A check that cannot tell those apart sends you to
    # fix the wrong thing.
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "BTS_MCP"))
        from wire_clients import NAME as _MCP_NAME, OLD_NAMES as _MCP_OLD
    except Exception:
        _MCP_NAME, _MCP_OLD = "BFast", ["bts-fs"]

    for label, path, tmpl in (
        ("  └ GEM registered", os.path.expandvars(r"%USERPROFILE%\.gemini\settings.json"), '"%s"'),
        ("  └ GW registered", os.path.expandvars(r"%USERPROFILE%\.grok\config.toml"), "mcp_servers.%s"),
    ):
        # read_text() returns "" for a missing file, so check existence separately —
        # otherwise "config not there" and "config there but unwired" both read as NO,
        # and those need different fixes.
        if not os.path.exists(path):
            rows.append((label, "NOT MEASURED", f"no config file at {path}"))
            continue
        body = read_text(path)
        if (tmpl % _MCP_NAME) in body or _MCP_NAME in body:
            rows.append((label, "yes", f"{_MCP_NAME} in {path}"))
        elif any(o in body for o in _MCP_OLD):
            rows.append((label, "**STALE NAME**",
                         f"found {_MCP_OLD} but not {_MCP_NAME} — this client missed the rename "
                         f"pass. Re-run: V:\\Research4\\Ai\\BTS_MCP\\wire_clients.py"))
        else:
            rows.append((label, "**NO**", f"{_MCP_NAME} not in {path}"))

    # ---------------- DRIVE HEALTH — scar S-96 ----------------
    # Until 2026-07-31 this function probed four API rails nightly and ZERO DISKS,
    # which is how a 7.3 TB mirror degraded 17.7 -> 0.6 MB/s over eighteen days
    # unobserved. A rail that answers HTTP 200 was monitored; the disk holding the
    # recovery copy of 606 restored PDFs was not. SMART temperature is one query.
    #
    # 🔴 2026-08-11 — TWO READINGS DISAGREED BY PRIVILEGE, AND THE BLIND ONE WAS WINNING.
    #
    # `Get-StorageReliabilityCounter` answers "Access to a CIM resource was not available
    # to the client" without admin. rail_check runs UNELEVATED, so its own probe returned
    # UNKNOWN x4 — while the elevated `BTS Drive Health` task (02:15 daily, /RL HIGHEST)
    # had a real reading sitting in drive_health.json. Both were correct about their own
    # context, and the mesh carried two truths with the blind one on the dashboard.
    #
    # ==> PREFER THE ELEVATED ARTIFACT WHEN IT IS FRESH. An unelevated probe cannot see
    #     the counters at all, so it is not a second opinion — it is an absence of one.
    # ==> AND CARRY ITS TIMESTAMP. A reading adopted from another process must announce
    #     how old it is, or a stale GREEN becomes indistinguishable from a current one —
    #     which is the whole defect this file exists to prevent.
    #
    _ELEVATED_MAX_AGE_H = 26          # the task runs daily at 02:15; 26 h allows one miss
    try:
        import bts_drive_health as _dh
        _disks, _note = _dh.read_disks()
        _source = "probed live (unelevated)"

        # Adopt the elevated reading if it is fresher than what we can see ourselves.
        try:
            import datetime as _dtm
            _led0 = _dh.load_ledger()
            _last = (_led0.get("readings") or [])[-1] if _led0.get("readings") else None
            if _last and _last.get("disks"):
                _when = _dtm.datetime.fromisoformat(_last["when"])
                if _when.tzinfo is None:
                    _when = _when.replace(tzinfo=_dtm.timezone.utc)
                _age_h = ((_dtm.datetime.now(_dtm.timezone.utc) - _when)
                          .total_seconds() / 3600.0)
                _elev_has_counters = any(x.get("read_unc") is not None
                                         or x.get("write_unc") is not None
                                         for x in _last["disks"])
                _mine_has_counters = any(x.get("read_unc") is not None
                                         or x.get("write_unc") is not None
                                         for x in (_disks or []))
                if _age_h <= _ELEVATED_MAX_AGE_H and _elev_has_counters \
                        and not _mine_has_counters:
                    _disks = _last["disks"]
                    _source = ("from the ELEVATED task's reading, %.1f h old (%s) — this "
                               "process cannot read the counters without admin"
                               % (_age_h, _last["when"][:16]))
                elif _age_h > _ELEVATED_MAX_AGE_H:
                    notes.append("The elevated drive-health reading is %.1f h old (max %d h). "
                                 "`BTS Drive Health` may have stopped — an absent report and "
                                 "an absent problem look identical."
                                 % (_age_h, _ELEVATED_MAX_AGE_H))
        except Exception as _ee:                                   # noqa: BLE001
            notes.append("could not evaluate the elevated drive-health artifact: %s" % _ee)

        if not _disks:
            rows.append(("DRIVE HEALTH", "NOT MEASURED", _note or "no physical disks visible"))
        else:
            _led = _dh.load_ledger()
            _prev = {}
            for _r in reversed(_led["readings"]):
                for _dd in _r.get("disks", []):
                    _prev.setdefault(_dh.key_of(_dd), dict(_dd, when=_r["when"]))
            _worst = "GREEN"
            for _d in _disks:
                _st, _why = _dh.judge(_d, _prev.get(_dh.key_of(_d)))
                _label = "  └ %s" % (_d.get("letters") or _d.get("name") or "?")[:28]
                _detail = ("%s C · uncorrected read=%s write=%s%s"
                           % (_d.get("temp"), _d.get("read_unc"), _d.get("write_unc"),
                              (" · " + "; ".join(_why)) if _why else ""))
                rows.append((_label, _st if _st != "GREEN" else "ok", _detail))
                if _st == "RED":
                    _worst = "RED"
                elif _st in ("AMBER", "UNKNOWN") and _worst == "GREEN":
                    _worst = _st
            rows.insert(len(rows) - len(_disks),
                        ("DRIVE HEALTH", _worst, "%d disk(s) · %s · thresholds warn=%s "
                         "crit=%s C · history in drive_health.json"
                         % (len(_disks), _source, _dh.TEMP_WARN, _dh.TEMP_CRIT)))
            if _worst == "UNKNOWN":
                notes.append("Drive health is UNKNOWN, which is NOT a pass. Measured "
                             "2026-08-11: three of four disks return read=None write=None "
                             "even ELEVATED, and one returns 0 C against a 0 maximum — a "
                             "device answering nothing, not a cold disk. The 'GREEN x4' "
                             "recorded on 2026-08-11 rested on temperature alone.")
            if _worst == "RED":
                notes.append("A DISK IS RED. This is the check that did not exist when G: died "
                             "(S-96) — act on it before it becomes a recovery job.")
    except Exception as _e:                                        # noqa: BLE001
        rows.append(("DRIVE HEALTH", "NOT MEASURED", "bts_drive_health unavailable: %s" % _e))

    # ---------------- QUEUE RUNNER LIVENESS — PLM-37 ----------------
    # The background lane is the most load-bearing monitor in this mesh and it was in no
    # registry at all. It stalled for 43 minutes on 2026-08-12 with work sitting in the
    # queue and NOTHING reported it.
    #
    # 🔴 ITS LIVENESS CANNOT BE READ FROM ITS OWN LEDGER. The ledger is written only when
    # a job runs, so silence means "idle" and "dead" IDENTICALLY. That is the same shape
    # as the four monitors that exited 0 while crashing (S-134): the absence of a report
    # is not the absence of a problem.
    # ==> The unambiguous signal is QUEUED-AND-UNCLAIMED. It needs neither the scheduler
    #     nor the runner, which is the whole requirement — a dead runner cannot report
    #     itself.
    try:
        import runner_doctor as _rd
        _stuck = _rd.stale_pending()
        _claimed = [p.name for p in _rd.RUNNING.glob("*") if p.is_file()]
        if _stuck and not _claimed:
            _oldest = max(w for _, w in _stuck)
            rows.append(("QUEUE RUNNER", "**RED**",
                         "%d job(s) queued and UNCLAIMED, oldest waiting %.0f min. The "
                         "runner is not ticking." % (len(_stuck), _oldest / 60)))
            notes.append("THE QUEUE RUNNER IS NOT TICKING — %d job(s) unclaimed, oldest "
                         "%.0f min. Everything Cowork runs natively goes through this "
                         "lane. Stage and run `runner_doctor.py --start`; if that returns "
                         "an access error it needs elevation, which is Keith's."
                         % (len(_stuck), _oldest / 60))
        elif _stuck:
            rows.append(("QUEUE RUNNER", "ok",
                         "%d queued, %d claimed — working through it" % (len(_stuck),
                                                                        len(_claimed))))
        else:
            rows.append(("QUEUE RUNNER", "ok",
                         "nothing stranded (queue empty or claimed within %ds)"
                         % _rd.PENDING_GRACE_S))
    except Exception as _qe:                                       # noqa: BLE001
        rows.append(("QUEUE RUNNER", "NOT MEASURED",
                     "runner_doctor unavailable: %s" % _qe))

    # ---------------- write it where everything can read it ----------------
    md = [f"# Rail health — {stamp}", "",
          "Run **natively on Windows** by the `BTS Rail Check` scheduled task.",
          "Probed from the machine that owns the credentials, deliberately: Cowork's Linux sandbox",
          "is egress-blocked from googleapis and reports those rails dead when they are not.", "",
          "| rail | result | detail |", "|---|---|---|"]
    md += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    if notes:
        md += ["", "## Notes"] + [f"- {n}" for n in notes]
    md += ["", "Nothing above is inferred. Anything unreachable is recorded as NOT MEASURED."]
    text = "\n".join(md) + "\n"

    wrote = []
    for d in (WORK, ODX):
        try:
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, "RAIL_HEALTH_%s.md" % time.strftime("%Y-%m-%d"))
            open(p, "w", encoding="utf-8").write(text)
            wrote.append(p)
        except OSError as e:
            print(f"could not write {d}: {e}")

    print(text)
    for p in wrote:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
