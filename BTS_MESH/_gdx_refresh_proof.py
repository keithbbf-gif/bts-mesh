#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Prove the GDX refresh token WORKS by using it — not by observing that the field exists.

An hour ago `credentials.json` verified read and write and was still worthless: it was an
online-access token with no refresh capability, and the script announced "7-day clock reset".
The lesson is narrow and worth keeping: **a credential that works now has not been shown to work
tomorrow.** The only proof of a refresh token is a refresh.

This forces an actual token exchange, then calls Drive with the NEW access token.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

CRED = r"V:\Research4\Ai\credentials.json"
TOKEN_URI = "https://oauth2.googleapis.com/token"

d = json.load(open(CRED, encoding="utf-8"))
tr = d.get("token_response", {}) or {}
cid = d.get("client_id") or tr.get("client_id")
csec = d.get("client_secret") or tr.get("client_secret")
rtok = d.get("refresh_token") or tr.get("refresh_token")

print("=" * 70)
print("GDX REFRESH PROOF —", time.strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 70)
print(f"  current token_expiry : {d.get('token_expiry')}")
print(f"  refresh_token        : {'present' if rtok else 'ABSENT'}")

if not rtok:
    print("\n  FAIL — no refresh token to exercise.")
    raise SystemExit(1)

body = urllib.parse.urlencode({
    "client_id": cid, "client_secret": csec,
    "refresh_token": rtok, "grant_type": "refresh_token",
}).encode()
req = urllib.request.Request(
    TOKEN_URI, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})

t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=45) as r:
        j = json.load(r)
        st = r.status
except urllib.error.HTTPError as e:
    j, st = json.loads(e.read().decode("utf-8", "replace") or "{}"), e.code

ms = (time.time() - t0) * 1000
print(f"\n  REFRESH -> HTTP {st}  ({ms:.0f} ms)")
if st != 200 or not j.get("access_token"):
    print(f"  FAIL: {j.get('error')} — {str(j.get('error_description'))[:100]}")
    raise SystemExit(1)

new = j["access_token"]
print(f"  new access_token issued, expires_in {j.get('expires_in')}s")

# Use the NEW token, not the stored one — that is what makes this a proof.
req2 = urllib.request.Request(
    "https://www.googleapis.com/drive/v3/files"
    "?q='1aiMjVZfFtiBGNAlkTwAYiq1Pvuz2F6hA'+in+parents+and+trashed%3Dfalse"
    "&pageSize=3&fields=files(name)",
    headers={"Authorization": "Bearer " + new})
try:
    with urllib.request.urlopen(req2, timeout=30) as r:
        files = json.load(r).get("files", [])
        print(f"  Drive API with the REFRESHED token -> HTTP {r.status}, {len(files)} file(s)")
        for f in files:
            print(f"     - {f['name']}")
except urllib.error.HTTPError as e:
    print(f"  Drive call FAILED HTTP {e.code}")
    raise SystemExit(1)

# Persist the refreshed access token so the stored credential is current.
d["access_token"] = new
d.setdefault("token_response", {})["access_token"] = new
d["token_expiry"] = time.strftime(
    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + int(j.get("expires_in", 3599))))
d["invalid"] = False
json.dump(d, open(CRED, "w", encoding="utf-8"), indent=1)

print(f"\n  PASS — the refresh token works. credentials.json updated, expiry {d['token_expiry']}.")
print("  This can now be run headless on a schedule; no browser until the 7-day")
print("  Testing-mode consent itself lapses.")
