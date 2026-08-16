#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Force Gemini CLI onto Vertex by rewriting its stored auth choice.

WHY ENV VARS WERE NOT ENOUGH
----------------------------
Gemini CLI persists the chosen auth method in `%USERPROFILE%\.gemini\settings.json` as
`selectedAuthType`. Once "Sign in with Google" is stored there, every headless run re-enters the
Code Assist onboarding path and dies on `IneligibleTierError` BEFORE it ever consults
`GOOGLE_GENAI_USE_VERTEXAI` or the `.env` file. Setting the environment therefore looked like it
did nothing — the failure happens upstream of where the environment is read.

This rewrites the stored choice and clears the cached personal-OAuth credential so the CLI cannot
fall back into the dead tier.

Backs up anything it touches. Prints the before/after so the change is auditable.
"""

from __future__ import annotations

import json
import os
import shutil
import time

HOME = os.path.expanduser("~")
GDIR = os.path.join(HOME, ".gemini")
SETTINGS = os.path.join(GDIR, "settings.json")

print("=" * 72)
print("FORCE GEMINI CLI -> VERTEX  ", time.strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 72)
print(f"  config dir: {GDIR}")

if not os.path.isdir(GDIR):
    print("  .gemini directory not found — run `gemini` once first.")
    raise SystemExit(2)

print("\n  contents:")
for f in sorted(os.listdir(GDIR)):
    p = os.path.join(GDIR, f)
    print(f"    {f}{'/' if os.path.isdir(p) else ''}")

settings = {}
if os.path.exists(SETTINGS):
    try:
        settings = json.load(open(SETTINGS, encoding="utf-8"))
    except Exception as e:
        print(f"\n  settings.json unreadable ({type(e).__name__}); starting fresh")
    shutil.copy2(SETTINGS, SETTINGS + ".bak_" + time.strftime("%Y%m%d_%H%M"))

print(f"\n  BEFORE: {json.dumps(settings)[:400]}")

# The key name has moved between versions; write BOTH the flat and nested forms so whichever
# this build reads, it finds Vertex. Writing an unused key is harmless; missing the used one
# costs another round trip.
settings["selectedAuthType"] = "vertex-ai"
sec = settings.setdefault("security", {})
sec.setdefault("auth", {})["selectedType"] = "vertex-ai"

json.dump(settings, open(SETTINGS, "w", encoding="utf-8"), indent=2)
print(f"  AFTER : {json.dumps(settings)[:400]}")

# Move the personal-OAuth credential aside. While it exists the CLI can re-enter the retired
# Code Assist path; without it, Vertex is the only route left.
moved = []
for name in ("oauth_creds.json", "google_accounts.json"):
    p = os.path.join(GDIR, name)
    if os.path.exists(p):
        dead = p + ".dead_" + time.strftime("%Y%m%d_%H%M")
        shutil.move(p, dead)
        moved.append(os.path.basename(dead))

print(f"\n  moved aside: {moved if moved else '(nothing)'}")
print("\n  Done. Vertex credentials come from .env (GOOGLE_API_KEY + "
      "GOOGLE_GENAI_USE_VERTEXAI=true).")
