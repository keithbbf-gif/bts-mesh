#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Which GDX credential, if any, still refreshes? Try them all before asking a human.

Three credential files exist in `Ai\`: `credentials.json` (full auth/drive scope, known dead),
`credentials.json.expired`, and `credentials_drivefile.json` — the staged *permanent* fix using the
narrow `drive.file` scope. A refresh needs no browser; only a dead refresh token does.

Checking all of them first is the difference between "the rail needs a human" and "the rail needed
a human, for one of its three credentials, and I never looked at the other two."
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

AI = r"V:\Research4\Ai"
TOKEN_URI = "https://oauth2.googleapis.com/token"
CANDIDATES = ["credentials_drivefile.json", "credentials.json", "credentials.json.expired"]


def refresh(cid, csec, rtok):
    body = urllib.parse.urlencode({
        "client_id": cid, "client_secret": csec,
        "refresh_token": rtok, "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(
        TOKEN_URI, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            return e.code, {}
    except Exception as e:
        return None, {"error": f"{type(e).__name__}: {e}"}


def drive_check(token):
    req = urllib.request.Request(
        "https://www.googleapis.com/drive/v3/about?fields=user,storageQuota",
        headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, {"body": e.read()[:160].decode("utf-8", "replace")}
    except Exception as e:
        return None, {"error": str(e)[:120]}


print("=" * 74)
print("GDX CREDENTIAL PROBE —", time.strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 74)

alive = []
for fn in CANDIDATES:
    p = os.path.join(AI, fn)
    if not os.path.exists(p):
        print(f"\n{fn}: not present")
        continue
    age = (time.time() - os.path.getmtime(p)) / 86400.0
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print(f"\n{fn}: unreadable ({type(e).__name__})")
        continue

    tr = d.get("token_response", {}) or {}
    cid = d.get("client_id") or tr.get("client_id")
    csec = d.get("client_secret") or tr.get("client_secret")
    rtok = d.get("refresh_token") or tr.get("refresh_token")
    scope = tr.get("scope") or d.get("scope") or d.get("scopes") or "(not recorded)"

    print(f"\n{fn}")
    print(f"  age {age:.1f} d · scope: {scope}")
    if not (cid and csec and rtok):
        print("  MISSING client_id / client_secret / refresh_token — cannot refresh")
        continue

    st, j = refresh(cid, csec, rtok)
    if st == 200 and j.get("access_token"):
        print(f"  refresh OK — no browser needed. expires_in {j.get('expires_in')}s")
        dst, dj = drive_check(j["access_token"])
        who = (dj.get("user") or {}).get("emailAddress", "?")
        print(f"  Drive API HTTP {dst} · user {who}")
        if dst == 200:
            alive.append((fn, j["access_token"], scope))
    else:
        print(f"  refresh FAILED HTTP {st}: {j.get('error')} — "
              f"{str(j.get('error_description'))[:80]}")

print("\n" + "=" * 74)
if alive:
    print("USABLE CREDENTIALS:")
    for fn, _, sc in alive:
        print(f"  {fn}   scope {sc}")
    print("\nA working credential exists. No human consent required —")
    print("point bts_gdx.py at it rather than re-authorising.")
else:
    print("NO credential refreshes. Human consent is genuinely required:")
    print(r"  V:\Research4\Ai\GDX_REAUTH.bat")
