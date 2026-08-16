r"""
MIGRATION STEP 3 — rewrite V:\Research4 -> V:\Research4, INSIDE V:\Research4 ONLY.
================================================================================
RUN ON THE HOST. Never through the FUSE mount (10 corruption hits; it has faked JSON errors on
healthy files and served a script truncated mid-line). V:\Research4 is NOT touched by this script.

THE ONE JUDGEMENT CALL, and it matters:
  **CODE must RUN. HISTORY must stay TRUE.**
  · CODE (.py .bat .vbs .json .html)  -> REWRITE ALL. It has to work from the new tree.
  · OPERATIONAL docs (an explicit allowlist) -> REWRITE. They INSTRUCT the next session; a stale
    instruction is a bug.
  · HISTORICAL docs (everything else .md) -> **LEAVE `V:\Research4` ALONE.**
    They RECORD what was true THEN. "bts_gem.py at V:\Research4\Ai\... served truncated" is a FACT
    about a path that existed. Rewriting it to V:\Research4 would make the record claim something
    that never happened. **A migration must not edit history.** _MIGRATION_NOTE.md explains the break.

BOTH SPELLINGS. `V:\Research4` and `V:\\Research4` (JSON/Python escapes) are different byte strings.
An earlier audit of mine searched only the escaped form and undercounted by 60x (32 vs 1,961).
Case-insensitive too — Windows does not care, and `V:\Research4` appears in the wild.
"""
import os, re, sys, io

SRC_ROOT = r"V:\Research4"          # we edit the COPY, never the original
OLD_1 = r"V:\Research4"
NEW_1 = r"V:\Research4"
OLD_2 = "D:\\\\Research2"            # the literal 4 chars  D : \ \  as seen in JSON/py source
NEW_2 = "V:\\\\Research4"

CODE_EXT = {".py", ".bat", ".vbs", ".json", ".html", ".cmd", ".ps1", ".yaml", ".yml", ".ini", ".cfg"}

# Documents that TELL THE NEXT SESSION WHAT TO DO -> must point at the live tree.
OPERATIONAL = {
    "claude.md",
    "00_rold_commands_tidyup_bootup.md",
    "00_mesh_charter.md",
    "00_tools_index.md",
    "00_folder_access_record.md",
    "00_task_complete_kmesh.md",
    "surface_policy.md",
    "readme_do_not_publish.md",
    "_readme.md",
}
# Documents that RECORD WHAT HAPPENED -> leave every V:\Research4 in place.
HISTORICAL_HINTS = ("wrapup", "loose_ends", "handoff", "harvest", "session", "reconciled",
                    "proven", "correction", "backlog", "primer", "adjudication", "todo",
                    "findings", "scars", "migration_research4", "stress_test", "notes")

# 🔴 A FROZEN LOCATION OUTRANKS AN OPERATIONAL FILENAME.
# The dry run caught this: matching on filename alone flagged
#   Ai\_BACKUP_pre-BTS-notify_2026-07-10-0330\00_FOLDER_ACCESS_RECORD.md   and
#   Ai\PhD2_DATA_ARCHIVE\00_SESSION_BTS-R1_2026-07-01\00_FOLDER_ACCESS_RECORD.md
# as "operational" and would have REWRITTEN them. Both are FROZEN SNAPSHOTS — a backup and a dated
# session record. Editing a backup falsifies the backup; editing a dated snapshot falsifies the date.
# Neither instructs anybody. **If it lives in a frozen place, it is history, whatever it is called.**
FROZEN_DIRS = ("_backup", "00_session_", "\\backup", "_bak", ".bak_", "_old", "_archive_copy")

def classify(path):
    ext = os.path.splitext(path)[1].lower()
    name = os.path.basename(path).lower()
    low = path.lower()
    frozen = any(m in low for m in FROZEN_DIRS)
    if ext in CODE_EXT:
        # Code in a frozen location is a RECORD of what that code was, not something we run.
        return "frozen-code" if frozen else "code"
    if ext == ".md":
        if frozen:
            return "history"                 # location wins over filename
        if name in OPERATIONAL:
            return "operational"
        return "history"        # DEFAULT TO HISTORY. Falsifying a record is worse than a stale pointer.
    return "skip"

def main():
    dry = "--go" not in sys.argv
    counts = {"code": [0, 0], "operational": [0, 0], "history": [0, 0],
              "frozen-code": [0, 0], "skip": [0, 0]}
    changed, hist_left = [], 0
    pat1 = re.compile(re.escape(OLD_1), re.IGNORECASE)
    pat2 = re.compile(re.escape(OLD_2), re.IGNORECASE)

    for dirpath, dirnames, filenames in os.walk(SRC_ROOT):
        dirnames[:] = [d for d in dirnames if d.lower() not in (".git", "node_modules", "__pycache__")]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            kind = classify(full)
            # SKIP BEFORE READING. The first version classified, then read EVERY file anyway —
            # including every PDF, .xy spectrum and .opj in a 31.58 GB tree — just to discover it did
            # not care. Decide first, read second.
            if kind == "skip":
                continue
            try:
                if os.path.getsize(full) > 8 * 1024 * 1024:   # no source file is 8 MB; that is data
                    continue
                with io.open(full, "r", encoding="utf-8", errors="strict") as f:
                    txt = f.read()
            except Exception:
                continue                      # binary / undecodable -> not ours to touch
            n = len(pat1.findall(txt)) + len(pat2.findall(txt))
            if not n:
                continue
            counts[kind][0] += 1
            counts[kind][1] += n
            if kind in ("code", "operational"):
                # LAMBDA, not a string. re.sub treats the replacement as a TEMPLATE, so a literal
                # Windows path detonates: "V:\Research4" -> `\R` is read as an escape ->
                # re.PatternError: bad escape \R. A lambda returns the string verbatim.
                # (Same family as the earlier [regex]::Escape + -SimpleMatch bug: the tool's idea of
                # a "string" is not yours. Backslashes are where this always goes wrong.)
                new = pat2.sub(lambda _m: NEW_2, txt)
                new = pat1.sub(lambda _m: NEW_1, new)
                if not dry:
                    with io.open(full, "w", encoding="utf-8", newline="") as f:
                        f.write(new)
                changed.append((kind, n, full[len(SRC_ROOT) + 1:]))
            else:
                hist_left += n

    print("=" * 78)
    print("  STEP 3 — path rewrite  %s" % ("(DRY RUN — pass --go to write)" if dry else "*** WRITING ***"))
    print("  %s  ->  %s   (inside %s only)" % (OLD_1, NEW_1, SRC_ROOT))
    print("=" * 78)
    for k in ("code", "operational", "history", "frozen-code"):
        print("  %-12s %4d files  %5d refs   %s" % (
            k, counts[k][0], counts[k][1],
            "REWRITTEN" if k in ("code", "operational")
            else "LEFT ALONE (history must stay true)" if k == "history"
            else "LEFT ALONE (code inside a backup/snapshot = a record of that code)"))
    print()
    print("  refs rewritten : %d" % (counts["code"][1] + counts["operational"][1]))
    print("  refs preserved : %d  (history %d + frozen code %d)"
          % (counts["history"][1] + counts["frozen-code"][1],
             counts["history"][1], counts["frozen-code"][1]))
    print()
    print("  TOP CODE FILES TOUCHED:")
    for kind, n, rel in sorted([c for c in changed if c[0] == "code"], key=lambda x: -x[1])[:14]:
        print("     %4dx  %s" % (n, rel))
    print()
    print("  OPERATIONAL DOCS TOUCHED:")
    for kind, n, rel in sorted([c for c in changed if c[0] == "operational"], key=lambda x: -x[1]):
        print("     %4dx  %s" % (n, rel))
    print("=" * 78)
    if dry:
        print("  DRY RUN. Nothing written. Re-run with --go to apply.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
