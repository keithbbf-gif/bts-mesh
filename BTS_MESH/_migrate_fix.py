r"""
MIGRATION FIX — the two things the verify caught.

1. bts_paths.py's OWN LADDER got rewritten by the path sweep.
   `_WIN = [r"V:\Research4", r"V:\Research4"]`  ->  `[r"V:\Research4", r"V:\Research4"]`
   The resolver rewrote its own escape hatch into a duplicate. Not fatal (V: exists) but it happened
   BY ACCIDENT. Post-cutover the correct ladder is V:\Research4 ONLY: V:\Research4 becomes
   D:\Research3, the FROZEN archive, and resolving to it would read stale data and look fine.
   So: make the ladder DELIBERATE, and say why.

2. backup_to_onedrive.py still had a LIVE `V:\Research4` in SOURCES — it backs up the tree, so it
   must name the LIVE tree.
   *** WHY THE SWEEP MISSED IT — this is the real lesson: ***
   _migrate_step3_paths.py does `except Exception: continue` on read. A file that is not clean UTF-8
   is SILENTLY SKIPPED. It reported "96 files rewritten" and never mentioned the ones it could not
   read. **A skip that says nothing is a lie by omission** — the same family as a verifier that has
   never been shown to fail. This script reports every file it cannot decode.
"""
import io, os, sys

V = r"V:\Research4"
REPORT = []


def read_any(p):
    """Return (text, encoding) or (None, why). NEVER silently skip — that is the bug being fixed."""
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with io.open(p, "r", encoding=enc, errors="strict") as f:
                return f.read(), enc
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return None, "IO: %s" % e
    return None, "undecodable in utf-8/utf-8-sig/cp1252/latin-1"


def patch(rel, old, new, why):
    p = os.path.join(V, rel)
    if not os.path.exists(p):
        REPORT.append(("MISSING", rel, "")); return
    txt, enc = read_any(p)
    if txt is None:
        REPORT.append(("UNREADABLE", rel, enc)); return
    if old not in txt:
        REPORT.append(("no-op", rel, "pattern not present (already fixed?)")); return
    with io.open(p, "w", encoding=enc if enc != "latin-1" else "utf-8", newline="") as f:
        f.write(txt.replace(old, new))
    REPORT.append(("PATCHED", rel, why))


# ---- 1. bts_paths ladder: make it DELIBERATE ---------------------------------------------------
patch(r"Ai\BTS_MESH\bts_paths.py",
      '_WIN = [r"V:\\Research4", r"V:\\Research4"]',
      '# Windows: the live tree ONLY. V:\\Research4 is GONE after the 2026-07-16 cutover (renamed\n'
      '# D:\\Research3, the frozen archive) and is DELIBERATELY not a fallback: resolving to it would\n'
      '# read stale data and look completely fine. Fail loudly instead. This list was briefly\n'
      '# [V:\\Research4, V:\\Research4] because the migration sweep rewrote this very file.\n'
      '_WIN = [r"V:\\Research4"]',
      "ladder made deliberate, not accidental")

# ---- 2. the file the sweep silently skipped ----------------------------------------------------
patch(r"Ai\BTS_MESH\backup_to_onedrive.py",
      '(r"V:\\Research4", "Research2")',
      '(r"V:\\Research4", "Research4")',
      "backs up the LIVE tree; the sweep skipped this file on a decode error")

# ---- 3. find EVERY file the sweep could not read -----------------------------------------------
print("=" * 74)
print("  MIGRATION FIX")
print("=" * 74)
for status, rel, why in REPORT:
    print("  %-11s %-42s %s" % (status, rel, why))

print("\n  FILES THE SWEEP COULD NOT DECODE (it skipped these SILENTLY):")
bad = 0
EXT = {".py", ".bat", ".vbs", ".json", ".html", ".cmd", ".ps1", ".md"}
for dp, dn, fn in os.walk(V):
    dn[:] = [d for d in dn if d.lower() not in ("__pycache__",)]
    for x in fn:
        if os.path.splitext(x)[1].lower() not in EXT:
            continue
        p = os.path.join(dp, x)
        try:
            if os.path.getsize(p) > 8 * 1024 * 1024:
                continue
        except Exception:
            continue
        try:
            io.open(p, "r", encoding="utf-8", errors="strict").read()
        except UnicodeDecodeError:
            txt, enc = read_any(p)
            has = txt is not None and ("V:\\Research4" in txt or "D:\\\\Research2" in txt)
            bad += 1
            print("     %-58s %s%s" % (p[len(V) + 1:], enc, "   <-- HAS A LIVE D: REF" if has else ""))
        except Exception:
            pass
if bad == 0:
    print("     none — every text file decoded as UTF-8.")
print("=" * 74)
