#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Which auth style does aiplatform actually accept? Settle it by measurement.

Written 2026-07-26 because I was one edit away from "fixing" `bts_vertex.py`, which already uses
the `x-goog-api-key` header — the canonical way to send a Google API key. My rail probe used
`Authorization: Bearer`, got 401, and I recorded "VERTEX DEAD". If `x-goog-api-key` returns 200
then Vertex was never broken and the fault was entirely in my probe.

That distinction matters more than the result: a monitor that tests a rail differently from the way
production uses it does not measure the rail, it measures the monitor.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    import bts_paths
    SECRETS = bts_paths.secrets()
except Exception:
    SECRETS = r"V:\Research4\.secrets"

KEY = open(os.path.join(SECRETS, "vertex_key.txt"), encoding="utf-8").read().strip().strip('"')
URL = ("https://aiplatform.googleapis.com/v1/publishers/google/models/"
       "gemini-2.5-flash:generateContent")
BODY = {"contents": [{"role": "user", "parts": [{"text": "Reply with exactly one word: OK"}]}],
        "generationConfig": {"maxOutputTokens": 8}}


def call(label, url, headers):
    req = urllib.request.Request(url, data=json.dumps(BODY).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8", "replace")
            st = r.status
    except urllib.error.HTTPError as e:
        raw, st = e.read().decode("utf-8", "replace"), e.code
    except Exception as e:
        raw, st = f"{type(e).__name__}: {e}", None
    ms = (time.time() - t0) * 1000

    reply, usage = None, {}
    if st == 200:
        try:
            j = json.loads(raw)
            cand = (j.get("candidates") or [{}])[0]
            parts = (cand.get("content") or {}).get("parts") or []
            reply = "".join(p.get("text", "") for p in parts)
            usage = j.get("usageMetadata", {}) or {}
            if not reply:
                reply = f"(no text; finishReason={cand.get('finishReason')})"
        except Exception as e:
            reply = f"(200, unparsed: {type(e).__name__})"
    print(f"  {label:<34} HTTP {st!s:<5} {ms:6.0f} ms  {('reply=' + repr(reply)) if reply else ''}")
    if st == 200 and usage:
        print(f"       usage: {json.dumps(usage)}")
    elif st != 200:
        print(f"       {raw[:150].replace(chr(10), ' ')}")
    return st


print("=" * 74)
print("VERTEX AUTH PROBE —", time.strftime("%H:%M:%S"), "| key shape:", KEY[:3] + "… len", len(KEY))
print("=" * 74)
r1 = call("Authorization: Bearer <key>", URL, {"Authorization": "Bearer " + KEY})
r2 = call("?key=<key>", URL + "?key=" + KEY, {})
r3 = call("x-goog-api-key: <key>  [PRODUCTION]", URL, {"x-goog-api-key": KEY})

print()
if r3 == 200:
    print("  VERDICT: bts_vertex.py's existing header WORKS. Vertex was never broken.")
    print("           The 401 came from my probe using Bearer. Fix the MONITOR, not the rail.")
elif r2 == 200:
    print("  VERDICT: only ?key= works. bts_vertex.py must move the key to the query string.")
else:
    print("  VERDICT: no API-key style is accepted; a real OAuth credential is required.")
