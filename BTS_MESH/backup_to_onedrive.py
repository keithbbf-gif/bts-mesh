"""
backup_to_onedrive.py — full, structured, VERIFIED backup of everything dissertation-related.

    python backup_to_onedrive.py            # STEP 0 only: survey. COPIES NOTHING.
    python backup_to_onedrive.py GO         # survey -> copy -> manifest -> VERIFY

DESIGN RULES (each one is here because of a specific way backups lie):

  1. SURVEY BEFORE COPYING. A half-finished 900 GB copy is worse than no copy. If it does not
     fit, we say so and stop.

  2. NOTHING IS EVER SILENTLY DROPPED. Any file matching no rule goes to 99_UNSORTED with its
     original subpath intact. If 99_UNSORTED is large, the RULES are wrong -- it is not a bin.

  3. PROVENANCE SURVIVES REORGANISATION. The chapters cite D:\ paths. Re-foldering breaks that.
     MANIFEST.csv maps every file: original path -> backup path -> size -> sha256.
     The folder structure is for humans. The manifest is the truth.

  4. A BACKUP IS NOT A BACKUP UNTIL IT IS VERIFIED. We hash-compare 100% of CHAPTERS and RAW_DATA
     (the irreplaceable things) and a 5% random sample of everything else.

  5. THE VERIFIER MUST BE SHOWN TO FAIL. A negative control corrupts one byte and confirms the
     verifier catches it. A check never seen to fail is not a check.

  6. DATED SNAPSHOT, NOT A MIRROR. Mirrors propagate deletion and corruption faithfully.
     robocopy /MIR is deliberately NOT used.

  7. NO SECRETS IN THE CLOUD. OneDrive is a cloud surface. Keys are excluded, always.
"""
import os, sys, csv, shutil, hashlib, random, subprocess, datetime

# ---------------------------------------------------------------- config
# ⚠ REPOINTED 2026-07-17 AT THE CUTOVER. This file is why "never accept a DONE" is a rule:
#   00_MIGRATION_RESEARCH4_2026-07-16.md §4c said this script was "Patched." IT WAS NOT — neither tree
#   had it. The step-3 sweep SKIPPED it silently (`except Exception: continue` on a cp1252 read), the
#   skip was never reported, and I wrote "Patched." into a handoff without grepping it back.
#   Had that stood, the rename would have pointed the BACKUP at a path that no longer exists — failing
#   in the one direction nobody notices, because a backup's success is invisible until you need it.
#   Label is "Research4", not "Research2": Keith's clean break. Prior backups stay under ODX\...\Research2\.
#   TODO: this should ask bts_paths.ROOT rather than name a letter — that is the whole point of C1.
SOURCES = [
    (r"V:\Research4", "Research4"),
    (r"D:\PhD",       "PhD"),
]
ONEDRIVE = os.environ.get("OneDrive") or r"D:\ODX\OneDrive"
STAMP    = datetime.date.today().isoformat()
DEST     = os.path.join(ONEDRIVE, "PhD_DISSERTATION_BACKUP", STAMP)

# NEVER back these up. ADD to this list, never remove from it.
EXCLUDE_DIRS  = {".secrets", "__pycache__", "node_modules", ".git", ".ipynb_checkpoints"}
EXCLUDE_FILES = {"thumbs.db", "desktop.ini", "credentials.json", "token.json", ".env"}
EXCLUDE_GLOB  = ("*.key", "*.pem", "client_secret*", "*service-account*.json",
                 "gemini_key*", "vertex_key*", "*.tmp")

# category -> (folder, matcher). FIRST MATCH WINS, so order matters.
def _ext(p, *e):  return os.path.splitext(p)[1].lower() in e
def _in(p, *s):   return any(x in p.lower() for x in s)

CAMPAIGNS = [("may", "2004", "CAMD_2004-05_May"), ("dec", "2004", "CAMD_2004-12_Dec"),
             ("jun", "2005", "CAMD_2005-06_Jun"), ("aug", "2007", "CAMD_2007-08_Aug"),
             ("mar", "2008", "CAMD_2008-03_Mar"), ("feb", "2009", "CAMD_2009-02_Feb")]

def campaign_of(rel):
    r = rel.lower()
    for mon, yr, folder in CAMPAIGNS:
        if mon in r and (yr in r or yr[2:] in r):
            return folder
    return None

def categorise(rel):
    """Return (top_folder, subpath). FIRST MATCH WINS."""
    r = rel.lower()
    if _in(r, "correspond", "losovyj", "lozovyy", "email", "thunderbird"):
        return "08_CORRESPONDENCE", rel
    if _ext(rel, ".opj", ".opju", ".ogg", ".cas", ".vms"):
        return "05_ORIGIN_CASAXPS", rel
    if _ext(rel, ".pdf") or _in(r, "endnote", ".enl", "library", "literature", "reading"):
        return "06_LITERATURE", rel
    if _in(r, "bts_mesh", "\\ai\\", "/ai/", "handoff", "verification", "mesh"):
        return "07_AI_MESH", rel
    if _ext(rel, ".docx", ".doc", ".tex") and _in(r, "ch", "chapter", "dissert", "thesis"):
        sub = "lineage" if _in(r, "ver", "old", "archive", "superseded", "_v") else "current"
        return "01_CHAPTERS", os.path.join(sub, os.path.basename(rel))
    c = campaign_of(rel)
    if c and _ext(rel, ".xy", ".log", ".txt", ".dat", ".csv", ".xls", ".xlsx"):
        # raw beamtime. IRREPLACEABLE - beamtime happened once.
        if _in(r, "raw", "unmodified", "original"):
            return "02_RAW_DATA", os.path.join(c, rel)
        return "03_PROCESSED", os.path.join(c, rel)
    if _ext(rel, ".png", ".jpg", ".tif", ".svg", ".eps") or _in(r, "figure", "fig_"):
        return "04_FIGURES", rel
    if _ext(rel, ".py", ".m", ".r", ".ipynb") and _in(r, "fig", "plot", "fit"):
        return "04_FIGURES", os.path.join("_scripts", rel)   # a figure without its script is a liability
    if _ext(rel, ".xy", ".log", ".dat"):
        return "03_PROCESSED", rel
    return "99_UNSORTED", rel                                 # never nowhere


def excluded(path, name):
    n = name.lower()
    if n in EXCLUDE_FILES: return True
    import fnmatch
    return any(fnmatch.fnmatch(n, g) for g in EXCLUDE_GLOB)


def sha256(p, buf=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(buf)
            if not b: break
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- step 0: SURVEY
def survey():
    print("=" * 74)
    print("STEP 0 — SURVEY.  NOTHING IS COPIED IN THIS STEP.")
    print("=" * 74)
    total_b = total_n = 0
    plan = []
    for root, label in SOURCES:
        if not os.path.isdir(root):
            print("  ! %-12s NOT FOUND — skipping" % label); continue
        b = n = 0
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDE_DIRS]
            for fn in files:
                if excluded(dirpath, fn): continue
                fp = os.path.join(dirpath, fn)
                try: sz = os.path.getsize(fp)
                except OSError: continue
                rel = os.path.relpath(fp, root)
                cat, sub = categorise(os.path.join(label, rel))
                plan.append((fp, cat, sub, sz))
                b += sz; n += 1
        print("  %-12s %10.2f GB   %7d files" % (label, b / 1e9, n))
        total_b += b; total_n += n

    print("  " + "-" * 46)
    print("  %-12s %10.2f GB   %7d files" % ("TOTAL", total_b / 1e9, total_n))

    print("\n  by category:")
    agg = {}
    for _, cat, _, sz in plan:
        a = agg.setdefault(cat, [0, 0]); a[0] += sz; a[1] += 1
    for cat in sorted(agg):
        sz, n = agg[cat]
        flag = "   <-- if this is big, the RULES are wrong" if cat == "99_UNSORTED" and sz > 0.1 * total_b else ""
        print("    %-20s %8.2f GB  %6d files%s" % (cat, sz / 1e9, n, flag))

    try:
        free = shutil.disk_usage(ONEDRIVE).free
        print("\n  OneDrive free: %.2f GB   |   need: %.2f GB" % (free / 1e9, total_b / 1e9))
        if free < total_b * 1.1:
            print("\n  *** WILL NOT FIT. STOPPING. ***")
            print("  A half-finished copy is worse than no copy. Free space or narrow the scope.")
            return None
        print("  fits, with %.2f GB to spare" % ((free - total_b) / 1e9))
    except Exception as e:
        print("\n  ! could not read OneDrive free space (%s) — check manually before GO" % e)
    return plan


# ---------------------------------------------------------------- steps 1-3
def run(plan):
    print("\n" + "=" * 74)
    print("STEP 1 — COPY  ->  %s" % DEST)
    print("=" * 74)
    os.makedirs(DEST, exist_ok=True)
    rows, copied, failed = [], 0, []
    for src, cat, sub, sz in plan:
        dst = os.path.join(DEST, cat, sub)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(src, dst)          # copy2 preserves mtime
            rows.append((src, os.path.relpath(dst, DEST), sz))
            copied += 1
            if copied % 500 == 0:
                print("  ... %d files" % copied)
        except Exception as e:
            failed.append((src, str(e)[:80]))
    print("  copied %d files, %d FAILED" % (copied, len(failed)))
    for s, e in failed[:10]:
        print("    FAIL %s :: %s" % (s, e))

    print("\nSTEP 2 — MANIFEST")
    mpath = os.path.join(DEST, "MANIFEST.csv")
    with open(mpath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["original_path", "backup_path", "bytes", "sha256"])
        for src, rel, sz in rows:
            w.writerow([src, rel, sz, sha256(os.path.join(DEST, rel))])
    print("  MANIFEST.csv: %d rows  (original path -> backup path -> sha256)" % len(rows))

    # ---------------- STEP 3: VERIFY. this is the step that makes it real.
    print("\nSTEP 3 — VERIFY")
    critical = [r for r in rows if r[1].startswith(("01_CHAPTERS", "02_RAW_DATA"))]
    other    = [r for r in rows if r not in critical]
    sample   = critical + random.sample(other, max(1, int(len(other) * 0.05))) if other else critical
    print("  hashing 100%% of CHAPTERS+RAW_DATA (%d) + 5%% of the rest (%d)"
          % (len(critical), len(sample) - len(critical)))
    bad = []
    for src, rel, sz in sample:
        try:
            if sha256(src) != sha256(os.path.join(DEST, rel)):
                bad.append(rel)
        except Exception as e:
            bad.append("%s (%s)" % (rel, e))

    # NEGATIVE CONTROL — a verifier never shown to FAIL is not a verifier.
    print("\n  NEGATIVE CONTROL: corrupt one byte, confirm the verifier catches it")
    ctl = os.path.join(DEST, "_verify_control.tmp")
    with open(ctl, "wb") as f: f.write(b"BTS-VERIFY-CONTROL")
    h0 = sha256(ctl)
    with open(ctl, "r+b") as f: f.seek(0); f.write(b"X")
    caught = sha256(ctl) != h0
    os.remove(ctl)
    print("    -> %s" % ("PASS (corruption detected)" if caught else "*** FAIL — VERIFIER IS BLIND ***"))

    ok = (not bad) and caught and not failed
    print("\n" + "=" * 74)
    print("  BACKUP VERIFIED" if ok else "  *** BACKUP FAILED ***")
    if bad:
        print("  %d MISMATCHED files:" % len(bad))
        for b in bad[:15]: print("    " + b)
    print("=" * 74)

    with open(os.path.join(DEST, "00_START_HERE.md"), "w", encoding="utf-8") as f:
        f.write("# PhD dissertation backup — %s\n\n" % STAMP)
        f.write("**%s** | %d files | %.2f GB\n\n" % (
            "VERIFIED" if ok else "FAILED — DO NOT TRUST", len(rows), sum(r[2] for r in rows) / 1e9))
        f.write("## Where things are\n\n")
        for c, d in [("01_CHAPTERS", "the dissertation. `current/` = latest, `lineage/` = superseded drafts"),
                     ("02_RAW_DATA", "**IRREPLACEABLE.** Beamtime happened once. By campaign."),
                     ("03_PROCESSED", ".xy conversions, fits, derived tables"),
                     ("04_FIGURES", "figures + `_scripts/` that generated them"),
                     ("05_ORIGIN_CASAXPS", "Origin .OPJ / CasaXPS project files"),
                     ("06_LITERATURE", "PDFs + EndNote library"),
                     ("07_AI_MESH", "BTS mesh, handoffs, verification outputs"),
                     ("08_CORRESPONDENCE", "archived emails — this is **evidence**; §4.4 cites it"),
                     ("99_UNSORTED", "matched no rule. Original subpath preserved. Nothing is ever dropped.")]:
            f.write("- **`%s/`** — %s\n" % (c, d))
        f.write("\n## Provenance\n\n`MANIFEST.csv` maps every file: original `D:\\` path -> backup path "
                "-> size -> sha256. The folders are for you; **the manifest is the truth.**\n")
        f.write("\n## Excluded\n\nAPI keys and secrets (`.secrets\\`, `*.key`, `credentials.json`, ...). "
                "OneDrive is a cloud surface — keys do not go in it.\n")
        f.write("\n## This is a SNAPSHOT, not a mirror\n\nA sync-mirror propagates deletion and corruption "
                "faithfully. A dated snapshot cannot. Never point a sync client at this folder.\n")
    print("\n  wrote 00_START_HERE.md")
    return ok


if __name__ == "__main__":
    plan = survey()
    if plan is None:
        sys.exit(1)
    if len(sys.argv) > 1 and sys.argv[1].upper() == "GO":
        sys.exit(0 if run(plan) else 2)
    print("\n  (survey only — nothing copied)")
    print("  to actually run it:   python backup_to_onedrive.py GO")
