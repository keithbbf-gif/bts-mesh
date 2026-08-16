#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Force a FRESH GDX consent, instead of trying to refresh a dead token.

WHY `GDX_REAUTH.bat` FAILED
---------------------------
It calls `bts_gdx.get_drive()`, which calls PyDrive2's `LocalWebserverAuth()`. That method finds
the existing `credentials.json`, tries to **refresh** it first, and raises
`invalid_grant: Token has been expired or revoked` — it never reaches the browser step. So the
"re-auth" script could not re-auth precisely when re-auth was needed, which is the only time anyone
runs it.

The fix is to move the dead credential aside so there is nothing to refresh. Then
`LocalWebserverAuth()` does what its name says: opens a browser, waits for consent on a local
callback, and writes a new credential.

Keith clicks **Allow** in the browser. That is the one step no key can replace — minting a refresh
token requires human consent by design.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time

AI = r"V:\Research4\Ai"
MESH = os.path.join(AI, "BTS_MESH")
CRED = os.path.join(AI, "credentials.json")
SETTINGS = os.path.join(MESH, "settings.yaml")

if MESH not in sys.path:
    sys.path.insert(0, MESH)

print("=" * 74)
print("GDX FRESH CONSENT —", time.strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 74)

# ---- 1. move the dead credential aside (do not delete: it is evidence) ----
if os.path.exists(CRED):
    dead = CRED + ".dead_" + time.strftime("%Y-%m-%d_%H%M")
    shutil.move(CRED, dead)
    print(f"  moved dead credential -> {os.path.basename(dead)}")
else:
    print("  no existing credentials.json (clean slate)")

# ---- 2. fresh browser consent ----
print("\n  A BROWSER WILL OPEN. Click Allow, choosing keith.bbf@gmail.com.")
print("  (Google will warn the app is unverified — it is Keith's own app in Testing mode.")
print("   Advanced -> Go to <app> (unsafe) is the expected path.)\n")

try:
    from pydrive2.auth import GoogleAuth
except ImportError:
    print("  pydrive2 not installed: py -3 -m pip install pydrive2")
    raise SystemExit(2)

# PyDrive2 resolves `client_secrets.json` relative to the CURRENT WORKING DIRECTORY, and that
# file lives in `Ai\`, not `Ai\BTS_MESH\`. Running from the mesh folder produced
# "Invalid client secrets file ... No such file or directory". chdir to where the secret actually
# is, and pass the path explicitly as well so the behaviour does not depend on cwd at all.
os.chdir(AI)
CLIENT_SECRETS = os.path.join(AI, "client_secrets.json")
if not os.path.exists(CLIENT_SECRETS):
    print(f"  MISSING {CLIENT_SECRETS} — this is the OAuth *app* definition, not a user token.")
    print("  Without it no consent is possible. Download it from the Google Cloud console.")
    raise SystemExit(2)

gauth = GoogleAuth(settings_file=SETTINGS if os.path.exists(SETTINGS) else None)
gauth.settings["client_config_file"] = CLIENT_SECRETS

# ---- FORCE OFFLINE ACCESS, OR THIS WHOLE EXERCISE BUYS ONE HOUR ----------------------------
# The first successful run issued a token with `access_type=online`. Google grants NO REFRESH
# TOKEN for online access, so the credential expired 60 minutes later — and the script cheerfully
# printed "7-day clock reset", which was false. A re-auth that cannot be refreshed is not a
# re-auth; it is a session.
#
# `get_refresh_token: True` makes PyDrive2 request access_type=offline. `approval_prompt=force`
# makes Google re-issue the refresh token even when the user has consented before — without it,
# a repeat consent silently returns no refresh token at all, which is exactly how this hid.
gauth.settings["get_refresh_token"] = True
gauth.settings["oauth_scope"] = ["https://www.googleapis.com/auth/drive"]
try:
    gauth.GetFlow()
    gauth.flow.params["access_type"] = "offline"
    gauth.flow.params["approval_prompt"] = "force"
except Exception as e:                                  # pragma: no cover
    print(f"  WARNING: could not force offline access ({type(e).__name__}); "
          f"a refresh token may not be issued.")

print(f"  client_secrets: {CLIENT_SECRETS}")
print("  requesting OFFLINE access (refresh token) — access_type=offline, approval_prompt=force")
try:
    gauth.LocalWebserverAuth()
except Exception as e:
    print(f"\n  CONSENT FAILED: {type(e).__name__}: {e}")
    print("  If the browser never opened, run this from a normal desktop session")
    print("  (a local callback port must be reachable).")
    raise SystemExit(1)

# ---- 3. persist and PROVE it ----
gauth.SaveCredentialsFile(CRED)
print(f"\n  wrote {CRED}")

from pydrive2.drive import GoogleDrive                                   # noqa: E402

drive = GoogleDrive(gauth)
FOLDER = "1aiMjVZfFtiBGNAlkTwAYiq1Pvuz2F6hA"                             # BTS_SGH_Handoff
lst = drive.ListFile({"q": f"'{FOLDER}' in parents and trashed=false",
                      "maxResults": 5}).GetList()
print(f"  VERIFY read : {len(lst)} file(s) visible in BTS_SGH_Handoff")
for f in lst[:3]:
    print(f"     - {f['title']}")

f = drive.CreateFile({"title": "GDX_REAUTH_PROOF_%s.md" % time.strftime("%Y-%m-%d_%H%M"),
                      "parents": [{"id": FOLDER}]})
f.SetContentString(
    "# GDX re-auth proof\n\n"
    "Written by `gdx_fresh_auth.py` immediately after a fresh consent, %s.\n\n"
    "The previous `GDX_REAUTH.bat` could not do this: PyDrive2 tried to refresh the dead token\n"
    "and raised `invalid_grant` before reaching the browser. Moving the dead credential aside\n"
    "first is what lets `LocalWebserverAuth()` actually open a consent window.\n\n"
    "Fuse clock reset. Testing-mode consent expires again in ~7 days; the permanent fix is the\n"
    "`drive.file` scope plus publishing the OAuth app to Production.\n"
    % time.strftime("%Y-%m-%d %H:%M:%S"))
f.Upload()
print(f"  VERIFY write: {f['title']}  id={f['id']}")

# ---- 4. THE CHECK THAT MATTERS: did we actually get a refresh token? ------------------------
# Read and write passing proves the token works NOW. It says nothing about tomorrow. Without a
# refresh token this credential dies in ~60 minutes and every script depending on it breaks
# silently. The first run passed both verifications and was still worthless by teatime, so this
# check is the one that decides whether the re-auth succeeded.
saved = json.load(open(CRED, encoding="utf-8"))
tr = saved.get("token_response", {}) or {}
rtok = saved.get("refresh_token") or tr.get("refresh_token")
print(f"\n  scope        : {tr.get('scope', '(not recorded)')}")
print(f"  token_expiry : {saved.get('token_expiry')}")

if rtok:
    print(f"  refresh_token: PRESENT (len {len(rtok)})")
    print("\n  GDX RE-AUTH OK — read, write, AND refresh token all confirmed.")
    print("  Testing-mode consent expires in ~7 days; the token can be refreshed until then")
    print("  with no browser. Permanent fix: drive.file scope + publish the app to Production.")
    raise SystemExit(0)

print("  refresh_token: *** ABSENT ***")
print("\n  RE-AUTH INCOMPLETE. Google issued an ONLINE-only token: it works right now and")
print(f"  expires at {saved.get('token_expiry')} — roughly an hour — and CANNOT be refreshed.")
print("  Re-run this script; it now forces access_type=offline + approval_prompt=force.")
print("  If the refresh token is still absent, the OAuth client itself is configured for")
print("  online access and must be fixed in the Google Cloud console.")
raise SystemExit(1)
