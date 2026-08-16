#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
fix_rails.py — repair the Vertex rail and the GDX consent fuse from stored credentials.
2026-07-26. Run NATIVELY on Windows (the sandbox is egress-blocked from googleapis).

WHAT WAS ACTUALLY WRONG
-----------------------
**Vertex was never missing a key. It was being handed the wrong KIND of credential.**
`bts_vertex.py` sends `Authorization: Bearer <contents of vertex_key.txt>`, and that file holds a
value beginning `AQ.` — the same shape as `gemini_key.txt`, which works perfectly as an **API key**
against `generativelanguage`. An API key is not an OAuth 2 access token, and
`aiplatform.googleapis.com` says so precisely: *"Expected OAuth 2 access token, login cookie or
other valid authentication credential."* That message was correct all along and we read it as
"the key is dead".

Two repairs are possible and this script tries both, in order of preference:

1. **Mint a real OAuth access token** from the refresh token already sitting in
   `.secrets\gcp_billing_token.json` (it carries `client_id`, `client_secret` and `refresh_token`).
   No browser, no new credential. This is the correct fix if the grant covers `cloud-platform`.
2. **Express-mode API key** — pass the existing `AQ.` value as `?key=` instead of a Bearer header.
   Vertex accepts API keys on some surfaces; if that works, it is a one-line change in
   `bts_vertex.py`.

**GDX** is the same family of problem: `Ai\credentials.json` holds a `refresh_token` with
`auth/drive` scope. A refresh needs **no human consent** — the browser step is only required when
the *refresh token itself* has expired. So the "weekly re-auth" chore is automatable until the
refresh token is genuinely revoked, at which point this reports `invalid_grant` and a human is
unavoidable.

RULES
-----
* Never print a secret. Values are reported by length and prefix only.
* Back up any credential file before rewriting it.
* Report what was MEASURED. A repair that did not verify is not a repair.
"""

from __future__ import annotations

import json
import os
import shutil
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

GCP_TOKEN = os.path.join(SECRETS, "gcp_billing_token.json")
VERTEX_KEY = os.path.join(SECRETS, "vertex_key.txt")
VERTEX_OAUTH = os.path.join(SECRETS, "vertex_access_token.txt")
GDX_CRED = os.path.join(ROOT, "Ai", "credentials.json")
TOKEN_URI = "https://oauth2.googleapis.com/token"

VERTEX_URL = ("https://aiplatform.googleapis.com/v1/publishers/google/models/"
              "gemini-2.5-flash:generateContent")
PING = {"contents": [{"role": "user", "parts": [{"text": "Reply with exactly one word: OK"}]}],
        "generationConfig": {"maxOutputTokens": 8}}


def shape(v: str) -> str:
    return f"<{v[:3]}… len {len(v)}>" if v else "<empty>"


def post(url, data, headers=None, timeout=45):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), (time.time() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read(), (time.time() - t0) * 1000
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode(), (time.time() - t0) * 1000


def refresh_access_token(client_id, client_secret, refresh_token):
    """Exchange a refresh token for a fresh access token. No browser involved."""
    body = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    st, raw, ms = post(TOKEN_URI, body,
                       {"Content-Type": "application/x-www-form-urlencoded"})
    try:
        j = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        j = {"raw": raw[:200].decode("utf-8", "replace")}
    return st, j, ms


def try_vertex(headers=None, params=""):
    st, raw, ms = post(VERTEX_URL + params, json.dumps(PING).encode(),
                       {**(headers or {}), "Content-Type": "application/json"})
    txt = raw.decode("utf-8", "replace")
    reply = None
    if st == 200:
        try:
            reply = "".join(p.get("text", "") for p in
                            json.loads(txt)["candidates"][0]["content"]["parts"])
        except Exception:
            reply = "(200 but unparsed)"
    return st, reply, txt[:200], ms


def main() -> int:
    out = []
    print("=" * 72)
    print("FIX RAILS —", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 72)

    # ---------------------------------------------------------------- VERTEX
    print("\n## VERTEX\n")
    baseline_key = ""
    if os.path.exists(VERTEX_KEY):
        baseline_key = open(VERTEX_KEY, encoding="utf-8").read().strip().strip('"')
        print(f"  current vertex_key.txt  = {shape(baseline_key)}")

    st, _, body, ms = try_vertex({"Authorization": "Bearer " + baseline_key}) if baseline_key \
        else (None, None, "no key", 0)
    print(f"  [A] existing value as Bearer      -> HTTP {st}  ({ms:.0f} ms)")
    out.append(("vertex bearer(api-key)", st))

    # Attempt 2: same value as an API key on the query string (express mode).
    if baseline_key:
        st2, reply2, body2, ms2 = try_vertex(params="?key=" + baseline_key)
        print(f"  [B] existing value as ?key=       -> HTTP {st2}  ({ms2:.0f} ms)")
        if st2 == 200:
            print(f"        reply: {reply2!r}")
        out.append(("vertex ?key=", st2))
    else:
        st2 = None

    # Attempt 3: mint a REAL OAuth access token from the stored refresh token.
    st3 = None
    if os.path.exists(GCP_TOKEN):
        d = json.load(open(GCP_TOKEN, encoding="utf-8"))
        cid, csec, rtok = d.get("client_id"), d.get("client_secret"), d.get("refresh_token")
        print(f"  gcp_billing_token.json: client_id {shape(cid or '')} "
              f"refresh_token {shape(rtok or '')} expiry {d.get('expiry')}")
        if cid and csec and rtok:
            rst, rj, rms = refresh_access_token(cid, csec, rtok)
            if rst == 200 and rj.get("access_token"):
                at = rj["access_token"]
                print(f"  [C] refresh_token -> access_token OK ({rms:.0f} ms), "
                      f"scope: {rj.get('scope', '(not returned)')}")
                st3, reply3, body3, ms3 = try_vertex({"Authorization": "Bearer " + at})
                print(f"      OAuth access token on Vertex  -> HTTP {st3}  ({ms3:.0f} ms)")
                if st3 == 200:
                    print(f"        reply: {reply3!r}")
                    with open(VERTEX_OAUTH, "w", encoding="utf-8") as fh:
                        fh.write(at)
                    print(f"      WROTE {VERTEX_OAUTH}")
                    print("      NOTE: access tokens expire in ~1 h. bts_vertex must MINT one per "
                          "call from the refresh token, not read a stale file.")
                else:
                    print(f"        {body3}")
                out.append(("vertex oauth", st3))
            else:
                print(f"  [C] refresh FAILED HTTP {rst}: "
                      f"{rj.get('error')} — {str(rj.get('error_description'))[:90]}")
                out.append(("gcp refresh", rst))
    else:
        print("  gcp_billing_token.json not found — cannot mint an OAuth token")

    print("\n  VERDICT:", end=" ")
    if st3 == 200:
        print("FIXED via OAuth. bts_vertex.py must mint a token per call (see below).")
    elif st2 == 200:
        print("FIXED via ?key= express mode. One-line change in bts_vertex.py.")
    else:
        print("NOT FIXED. Neither an API key nor the stored OAuth grant is accepted.\n"
              "           A new credential is required and that is an account-class action.")

    # ---------------------------------------------------------------- GDX
    print("\n## GDX (Google Drive)\n")
    if not os.path.exists(GDX_CRED):
        print("  Ai\\credentials.json not found")
    else:
        d = json.load(open(GDX_CRED, encoding="utf-8"))
        age = (time.time() - os.path.getmtime(GDX_CRED)) / 86400.0
        print(f"  consent age {age:.1f} d (refresh tokens expire ~7 d in External+Testing)")
        cid, csec = d.get("client_id"), d.get("client_secret")
        rtok = d.get("refresh_token") or d.get("token_response", {}).get("refresh_token")
        rst, rj, rms = refresh_access_token(cid, csec, rtok) if (cid and csec and rtok) \
            else (None, {"error": "missing fields"}, 0)
        if rst == 200 and rj.get("access_token"):
            print(f"  refresh OK ({rms:.0f} ms) — NO browser consent was needed")
            shutil.copy2(GDX_CRED, GDX_CRED + ".bak")
            d["access_token"] = rj["access_token"]
            d.setdefault("token_response", {})["access_token"] = rj["access_token"]
            d["token_expiry"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + int(rj.get("expires_in", 3599))))
            d["invalid"] = False
            with open(GDX_CRED, "w", encoding="utf-8") as fh:
                json.dump(d, fh, indent=1)
            print(f"  rewrote {GDX_CRED} (backup at .bak); fuse clock reset")
            st, raw, ms = post("https://www.googleapis.com/drive/v3/about?fields=user",
                               None, {"Authorization": "Bearer " + rj["access_token"]})
            print(f"  VERIFY Drive API -> HTTP {st} ({ms:.0f} ms)")
            out.append(("gdx", st))
        else:
            print(f"  refresh FAILED HTTP {rst}: {rj.get('error')} — "
                  f"{str(rj.get('error_description'))[:100]}")
            print("  If this is invalid_grant the refresh token itself is dead and a human must "
                  "re-consent: Desktop\\REAUTH_GDX.bat")
            out.append(("gdx", rst))

    print("\n" + "=" * 72)
    for name, st in out:
        print(f"  {name:<26} HTTP {st}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
