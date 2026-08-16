#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""codex_config_fix.py - set Codex's top-level policy in ~/.codex/config.toml, correctly.

WHY THIS EXISTS
---------------
`CODEX SETUP.bat` appended `model = "gpt-5.6"` to the END of config.toml. But
`codex mcp add bfast` had already written an `[mcp_servers.bfast]` table there.

    In TOML, a bare key after a table header BELONGS TO THAT TABLE.

So the line landed as `mcp_servers.bfast.model` - a key nothing reads - and the
file still parsed clean. `codex doctor` reported `config.toml parse ok` on the
same screen as `model <default>`, and only the second line was the truth. (S-132.)

    "a node once wrote to research4:handoff/ when it meant handoff:, verified
     the bytes, and reported success. VERIFYING CONTENT IS NOT VERIFYING
     DESTINATION."   - BFast roots.json, 2026-07-31

A parse check cannot catch this, because MISPLACEMENT IS NOT MALFORMATION.

WHAT THIS SETS, AND WHY
-----------------------
  model               gpt-5.6
  approval_policy     never            <- Keith's rule 2: background, no intervention.
                                          A rail that stops to ask is a rail that
                                          did not run.
  sandbox_mode        workspace-write  <- NOT danger-full-access. The scoping below
                                          IS the control; prompting is not.
  writable_roots      the three BFast roots, and only those
  network_access      true             <- the rails are HTTP; without this it is a
                                          node that cannot reach anything.

A root that does not exist on this machine is REPORTED and DROPPED, never written
as if present. BFast's own rule: "a missing root must never read as an empty one."

WHAT IT WILL NOT DO
-------------------
* It will not write a result that fails to parse.
* It will not write unless every key RESOLVES at top level on a re-read from disk.
* It will not write if any pre-existing top-level entry (notably `mcp_servers`)
  would be lost.
* It backs up the original, dated, beside itself, every time.

USAGE
  python codex_config_fix.py             # apply, with a backup
  python codex_config_fix.py --check     # report only, write nothing
"""
from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import sys
from pathlib import Path

try:
    import tomllib  # Python >= 3.11
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # the mesh already depends on this elsewhere
    except ModuleNotFoundError:
        tomllib = None

CFG = Path.home() / ".codex" / "config.toml"

# MEASURED 2026-08-11 from ~/.codex/models_cache.json, which is the ACCOUNT'S OWN
# list, fetched by codex itself. This ChatGPT account offers exactly:
#     gpt-5.6-terra (priority 2) . gpt-5.6-luna (3) . gpt-5.5 (7) .
#     gpt-5.4-mini (23) . codex-auto-review (hidden)
# ALL FIVE carry context_window = 272,000.
#
# 🔴 `gpt-5.6` BARE IS NOT ONE OF THEM. It was set here and by CODEX SETUP.bat, it
# landed at top level exactly as intended, `codex doctor` printed `model gpt-5.6`
# and `config.toml parse ok` - and the first real call died at the API with
#     "The 'gpt-5.6' model is not supported when using Codex with a ChatGPT account."
#
# S-132 was about a key in the WRONG TABLE. This is the same lesson one level in:
# A CORRECTLY PLACED KEY WITH AN INVALID VALUE IS STILL BROKEN, and neither a parse
# check nor a resolve check can see it, because both only ask WHERE the key is.
# ==> validate_model() below asserts the VALUE against the account's own cache.
SCALARS = {
    "model": "gpt-5.6-terra",
    "approval_policy": "never",
    "sandbox_mode": "workspace-write",
}

MODELS_CACHE = Path.home() / ".codex" / "models_cache.json"

# The three BFast roots. Order matters only for readability.
ROOTS = [
    r"V:\Ai",
    r"V:\Research4",
    r"X:\My Drive\BTS_SGH_Handoff",
]

MANAGED_TABLE = "sandbox_workspace_write"


def parse(text: str):
    if tomllib is None:
        return None
    return tomllib.loads(text)


def toml_literal(s: str) -> str:
    """Single-quoted TOML literal string - no escape processing, so Windows
    backslashes survive verbatim. Refuse anything containing a single quote."""
    if "'" in s:
        raise ValueError(f"path contains a single quote, cannot express literally: {s}")
    return f"'{s}'"


def strip_managed(lines: list[str]) -> list[str]:
    """Remove our scalar keys wherever they appear, and drop the whole
    [sandbox_workspace_write] table so it can be rewritten cleanly."""
    out: list[str] = []
    in_managed = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("["):
            in_managed = s.split("#")[0].strip() in (f"[{MANAGED_TABLE}]",)
            if in_managed:
                continue
        if in_managed:
            continue
        if "=" in s and s.split("=")[0].strip() in SCALARS:
            continue
        out.append(ln)
    return out


def validate_model(slug: str) -> tuple:
    """-> (ok, detail). Assert the VALUE against the account's own model cache.

    A parse check asks 'is this file well formed'. A resolve check asks 'is the key
    where I meant it'. NEITHER asks 'is this value one the account can actually
    use' - and that is the question the first live call failed on.

    If the cache is absent we return UNKNOWN, never OK. An unreadable authority is
    not a passing grade.
    """
    if not MODELS_CACHE.exists():
        return None, f"models_cache.json absent at {MODELS_CACHE} - CANNOT VALIDATE"
    try:
        import json
        data = json.loads(MODELS_CACHE.read_text(encoding="utf-8"))
    except Exception as e:
        return None, f"models_cache.json unreadable ({e}) - CANNOT VALIDATE"
    slugs = [m.get("slug") for m in data.get("models", []) if m.get("slug")]
    if not slugs:
        return None, "models_cache.json carries no slugs - CANNOT VALIDATE"
    ctx = {m.get("slug"): m.get("context_window") for m in data.get("models", [])}
    if slug in slugs:
        return True, f"{slug} offered by this account - context_window {ctx.get(slug):,}"
    return False, (f"{slug!r} is NOT offered by this account. Available: "
                   f"{', '.join(slugs)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    a = ap.parse_args()

    ok, detail = validate_model(SCALARS["model"])
    tag = {True: "ok ", False: "!! ", None: "?? "}[ok]
    print(f"  MODEL VALIDATION\n    {tag}{detail}")
    if ok is False:
        print("\n  ! refusing to write a model this account cannot use.\n")
        return 2
    print()

    if not CFG.exists():
        print(f"  no config at {CFG} - run CODEX SETUP.bat first")
        return 2
    if tomllib is None:
        print("  ! python < 3.11: tomllib unavailable, cannot validate. Refusing.")
        return 2

    original = CFG.read_text(encoding="utf-8")
    before = parse(original)
    print(f"  config : {CFG}")
    print(f"  parses : yes   ({len(original.encode('utf-8')):,} bytes)")
    print()

    # --- what is wrong today -------------------------------------------------
    print("  CURRENT")
    for k, v in SCALARS.items():
        cur = before.get(k)
        mark = "ok " if cur == v else "-> "
        print(f"    {mark}{k:<16} {cur!r}" + ("" if cur == v else f"   want {v!r}"))
    for tname, tval in before.items():
        if isinstance(tval, dict):
            for sname, sval in tval.items():
                if isinstance(sval, dict):
                    for k in SCALARS:
                        if k in sval:
                            print(f"    !  MISPLACED {k!r} inside [{tname}.{sname}] - "
                                  f"valid TOML, wrong table, read by nothing")
    sww = before.get(MANAGED_TABLE, {})
    print(f"    {'ok ' if sww.get('writable_roots') else '-> '}"
          f"{MANAGED_TABLE + '.writable_roots':<16} {sww.get('writable_roots')!r}")
    print(f"    {'ok ' if sww.get('network_access') else '-> '}"
          f"{MANAGED_TABLE + '.network_access':<16} {sww.get('network_access')!r}")

    # --- which roots actually exist -----------------------------------------
    print("\n  ROOTS")
    live: list[str] = []
    for r in ROOTS:
        ok = Path(r).is_dir()
        print(f"    {'present' if ok else 'MISSING'}  {r}")
        if ok:
            live.append(r)
    if not live:
        print("\n  ! none of the roots exist on this machine - REFUSING to write.\n")
        return 2
    if len(live) != len(ROOTS):
        print("    (missing roots are DROPPED, not written. A root that does not exist")
        print("     must never be recorded as if it did.)")

    want_ok = (all(before.get(k) == v for k, v in SCALARS.items())
               and sww.get("writable_roots") == live
               and sww.get("network_access") is True)
    if want_ok:
        print("\n  already correct - nothing to change.\n")
        return 0
    if a.check:
        print("\n  NEEDS CHANGE - run without --check to apply.\n")
        return 1

    # --- rebuild: scalars first, then surviving content, then our table ------
    kept = strip_managed(original.splitlines())
    head = [f'{k} = "{v}"' for k, v in SCALARS.items()]
    tail = [
        "",
        f"[{MANAGED_TABLE}]",
        "writable_roots = [",
        *[f"    {toml_literal(r)}," for r in live],
        "]",
        "network_access = true",
    ]
    body = "\n".join(head + [""] + [l for l in kept if l.strip()] + tail) + "\n"

    after = parse(body)
    if after is None:
        print("\n  ! result would not parse - REFUSING to write.\n")
        return 2
    for k, v in SCALARS.items():
        if after.get(k) != v:
            print(f"\n  ! {k!r} would not resolve at top level - REFUSING.\n")
            return 2
    if after.get(MANAGED_TABLE, {}).get("writable_roots") != live:
        print("\n  ! writable_roots would not resolve as written - REFUSING.\n")
        return 2
    lost = set(before) - set(after)
    if lost:
        print(f"\n  ! would LOSE top-level entries {sorted(lost)} - REFUSING.\n")
        return 2

    backup = CFG.with_name(f"config.toml.bak-{_dt.date.today().isoformat()}")
    shutil.copy2(CFG, backup)
    CFG.write_text(body, encoding="utf-8")

    # re-read FROM DISK. Never verify from the variable you just built.
    v2 = parse(CFG.read_text(encoding="utf-8"))
    print(f"\n  backup : {backup.name}")
    print("  APPLIED, verified by re-reading the file from disk:")
    for k in SCALARS:
        print(f"    {k:<16} {v2.get(k)!r}")
    print(f"    writable_roots   {v2[MANAGED_TABLE]['writable_roots']}")
    print(f"    network_access   {v2[MANAGED_TABLE]['network_access']}")
    print(f"    mcp_servers      {sorted(v2.get('mcp_servers', {}))}   (preserved)")
    print("\n  confirm with: codex doctor\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
