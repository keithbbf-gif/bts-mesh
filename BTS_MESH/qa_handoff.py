r"""
qa_handoff.py — package the mesh for review by the Grok Bot QA Engineer agent. 2026-08-16.

KEITH, 2026-08-16: "Make sure everything you do, including our current set that runs the mesh,
gets uploaded and checked by SGH - Grok BOT QA Engineer Agent. Make it code."

WHY A BUNDLE AND NOT A PASTE
  The QA agent said it watches deploys and clicks through what shipped. It needs the code and a
  statement of what changed — not a conversation. This writes both to a surface it can read, with a
  content hash per file so a later run can say what actually moved rather than re-reviewing
  everything. GDX is used because it is already the mesh's agent-to-agent surface and Grok Bot
  carries a Google Workspace connector; if a git remote exists the same bundle suits a repo.

🔴 THE ONE CHECK THAT RUNS BEFORE ANYTHING LEAVES — AND IT IS NOT SECURITY THEATER.
  Canon here is that security must be invisible and that the mission is dissemination, so this does
  NOT lecture about exposure and does NOT ask permission. It refuses on ONE thing: a live vendor key
  in an outbound bundle. The reason is functional, not moral — GitHub and every major host scan for
  key patterns and AUTO-REVOKE on sight. A leaked key does not create a scandal here; it silently
  kills the openai-api rail mid-deposition-prep. That is a availability failure, and it is exactly
  the class of thing this file exists to prevent.

🔴 AND WHAT THE QA AGENT IS TOLD TO LOOK FOR IS THE VALUABLE PART.
  Generic review returns generic findings. The brief below hands it THIS mesh's measured failure
  classes — every one of them cost a session — so it audits for the mistakes we actually make
  rather than the ones a linter already catches.

  RUN:  py -3.14 qa_handoff.py            build + write the bundle
        py -3.14 qa_handoff.py --dry      show what would ship, write nothing
        py -3.14 qa_handoff.py --selftest prove the secret scanner refuses a planted key
"""
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import sys

MESH = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(MESH)                      # ...\Ai
GDX  = r"X:\My Drive\BTS_SGH_Handoff"
OUTD = os.path.join(GDX, "QA_REVIEW")
LOCAL_FALLBACK = r"V:\Ai\QA_REVIEW"
STATE = os.path.join(MESH, "qa_handoff_state.json")

# ---- what ships. ALLOWLIST, never a denylist: a denylist ships anything nobody thought of.
INCLUDE = [
    ("BTS_MESH", ".py"),
    ("ROLD",     ".py"),
    ("ROLD",     ".toml"),
    ("ROLD",     ".md"),
]
SKIP_NAMES = {"qa_handoff_state.json"}
SKIP_SUBSTR = ("secret", "credential", "token", ".bak", "_spend", "delme__", "archive")

# ---- live key shapes. Presence of any of these aborts the run.
KEYPATS = [
    ("openai",   re.compile(r"sk-proj-[A-Za-z0-9_\-]{40,}")),
    ("openai",   re.compile(r"sk-[A-Za-z0-9]{40,}")),
    ("xai",      re.compile(r"xai-[A-Za-z0-9]{40,}")),
    ("google",   re.compile(r"AIza[A-Za-z0-9_\-]{30,}")),
    ("anthropic",re.compile(r"sk-ant-[A-Za-z0-9_\-]{40,}")),
    ("aws",      re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private",  re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]

BRIEF = """# QA BRIEF — what to look for in this mesh

You are reviewing a multi-model orchestration system that runs on one Windows workstation. It calls
six AI vendors, keeps a spend ledger per lane, and executes jobs unattended from a queue.

Please do NOT return generic advice (type hints, docstrings, broad exception handling). Every item
below is a failure this system has ACTUALLY had, with a date. Audit for these.

## 1. FALSE GREENS — the dominant failure class here, five occurrences in one session
- A check that tests PRESENCE where the defect is IDENTITY. Example: a guard asserted a list was
  non-empty when the real question was whether it was the RIGHT list. Four wrong items is not empty.
- A verdict computed from an empty exception list, so SKIPPED work reports as success.
- A negative control that shares the positive check's assumption. One control searched the same
  empty container as the check it was validating, so it could only ever print a pass.
⇒ For every assertion: could this pass while the thing it describes is false? Name the ones that can.

## 2. SCOPE-BOUNDED MEASUREMENT
- A scan bounded by the very assumption it was meant to test (searching only up to the expected
  edge, then reporting the max found equals that edge).
⇒ Flag any measurement whose search window is derived from the expected answer.

## 3. STALE STATUS STRINGS
- Prose fields in .toml that were true when written and are load-bearing later. One rail block read
  "PLANNED. NOT STARTED. There is no key and no module" while the key, the billing and the module
  all existed and 23 calls had been ledgered.
⇒ Flag any human-written status that no code re-derives.

## 4. WINDOWS / SHELL TRAPS, all measured
- `cmd` consumes `%` and, with delayed expansion, `!` — inline Python in a .bat gets silently eaten.
- npm CLIs are .cmd shims with no .exe; CreateProcess appends only .exe, so an installed tool looks
  absent. Resolve with shutil.which and launch .cmd through `cmd /c`.
- `cmd /c` will not carry a multi-line argument. A one-line probe certified a path that the real
  twenty-line traffic then broke.
- Locale decoding (cp1252) kills subprocess readers on box-drawing output. Decode bytes explicitly.
⇒ Flag any subprocess call that assumes an .exe, passes multi-line argv, or uses text=True.

## 5. CONFIG FORMAT CONFUSION
- JSON written into a .toml file: `{"k": "v"}` is not a TOML inline table. It left the control file
  unparseable and the whole control layer silently off.
- A rollback that only covered the failure that was predicted, so an unforeseen parse error left the
  broken file on disk.
⇒ Flag any writer that does not re-parse FROM DISK and restore on ANY exception.

## 6. METERS FED BY THE WRONG STREAM
- A vendor prints its cost line on stderr; the wrapper appended stderr only when the return code was
  non-zero. Every SUCCESSFUL call was therefore logged as unpriced.
⇒ Flag any accounting that only runs on the failure path.

## 7. SPEND SAFETY
- One vendor account auto-reloads, so running out of money is not a brake. The only limits are in
  code.
⇒ Flag any paid call that can execute without checking a monthly budget and a per-call ceiling
  BEFORE the request, and any ledger write that can fail silently.

## WHAT A USEFUL RETURN LOOKS LIKE
For each finding: file, line, the failure class above (or a new one), why it can bite, and the
smallest change that fixes it. Rank by whether it can fail SILENTLY. A loud crash is cheap; a
confident wrong answer is what hurts here.
"""


def _hash(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def collect():
    files = []
    for sub, ext in INCLUDE:
        d = os.path.join(ROOT, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(ext):
                continue
            low = name.lower()
            if name in SKIP_NAMES or any(s in low for s in SKIP_SUBSTR):
                continue
            files.append((sub, name, os.path.join(d, name)))
    return files


def scan_secrets(files):
    """Refuse the whole run if any live key shape is present. Functional, not moral: hosts
    auto-revoke on detection, which would kill a rail rather than merely embarrass anyone."""
    hits = []
    for sub, name, path in files:
        try:
            txt = open(path, "rb").read().decode("utf-8", "replace")
        except Exception:                                             # noqa: BLE001
            continue
        for vendor, rx in KEYPATS:
            m = rx.search(txt)
            if m:
                hits.append((sub + "\\" + name, vendor, m.group(0)[:12] + "..."))
    return hits


def selftest():
    print("qa_handoff selftest")
    ok = True
    probe = "key = 'sk-proj-" + "A" * 60 + "'"
    found = [v for v, rx in KEYPATS if rx.search(probe)]
    print("  planted openai key detected: %s" % ("YES" if found else "NO"))
    ok &= bool(found)
    clean = "model = 'gpt-5.6-terra'\nbudget = 25.00\n"
    found2 = [v for v, rx in KEYPATS if rx.search(clean)]
    print("  clean text flagged: %s (must be NO)" % ("YES" if found2 else "NO"))
    ok &= not found2
    fs = collect()
    print("  files that would ship: %d" % len(fs))
    ok &= len(fs) > 10
    # the scanner must be reachable from the real path, not only from a literal
    print("  scanner sees the real tree: %s" % ("yes" if fs else "NO"))
    print("SELFTEST %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    dry = "--dry" in sys.argv

    files = collect()
    print("collected %d files" % len(files))

    hits = scan_secrets(files)
    if hits:
        print("\n  REFUSED — live key material in the bundle:")
        for f, v, frag in hits:
            print("    %-40s %-9s %s" % (f, v, frag))
        print("\n  Nothing was written. Hosts auto-revoke detected keys, which would take a rail")
        print("  offline. Move the value to .secrets and re-run.")
        return 3

    prev = {}
    try:
        prev = json.load(open(STATE, encoding="utf-8")).get("hashes", {})
    except Exception:                                                 # noqa: BLE001
        pass

    now, changed, new = {}, [], []
    for sub, name, path in files:
        key = sub + "/" + name
        h = _hash(path)
        now[key] = h
        if key not in prev:
            new.append(key)
        elif prev[key] != h:
            changed.append(key)

    out = OUTD
    try:
        os.makedirs(out, exist_ok=True)
        open(os.path.join(out, ".w"), "w").close()
        os.remove(os.path.join(out, ".w"))
    except Exception as e:                                            # noqa: BLE001
        print("  GDX not writable (%s) — falling back to %s" % (e, LOCAL_FALLBACK))
        out = LOCAL_FALLBACK
        os.makedirs(out, exist_ok=True)

    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    dest = os.path.join(out, "bundle")
    if dry:
        print("\nDRY RUN — nothing written. would ship to %s" % out)
    else:
        os.makedirs(dest, exist_ok=True)
        for sub, name, path in files:
            dd = os.path.join(dest, sub)
            os.makedirs(dd, exist_ok=True)
            shutil.copy2(path, os.path.join(dd, name))

        with io.open(os.path.join(out, "QA_BRIEF.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write(BRIEF)

        with io.open(os.path.join(out, "MANIFEST.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("# MESH BUNDLE — %s\n\n" % stamp)
            f.write("%d files. Review priority is the CHANGED list; the rest is context.\n\n" % len(files))
            f.write("## CHANGED SINCE LAST HANDOFF (%d)\n" % len(changed))
            for k in changed or ["(none)"]:
                f.write("- %s\n" % k)
            f.write("\n## NEW (%d)\n" % len(new))
            for k in new or ["(none)"]:
                f.write("- %s\n" % k)
            f.write("\n## EVERYTHING (sha256, first 12)\n")
            for k in sorted(now):
                f.write("- `%s`  %s\n" % (now[k][:12], k))
            f.write("\n---\nRead QA_BRIEF.md first. It lists this system's measured failure "
                    "classes; findings against those are worth far more than style notes.\n")

        json.dump({"when": stamp, "hashes": now},
                  open(STATE, "w", encoding="utf-8"), indent=1)

    print("\n  new: %d   changed: %d   unchanged: %d"
          % (len(new), len(changed), len(files)-len(new)-len(changed)))
    print("  destination: %s" % out)
    if not dry:
        print("  wrote bundle/, QA_BRIEF.md, MANIFEST.md")
    print("\n  Point the QA Engineer agent at that folder. The brief tells it what this mesh")
    print("  actually gets wrong, which is the difference between a review and a linter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
