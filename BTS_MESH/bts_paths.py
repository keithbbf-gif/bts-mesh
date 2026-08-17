r"""
bts_paths — WHERE THE TREE IS. Resolve it; never hardcode it.
================================================================================
⚠⚠ 2026-07-17: THIS DOCSTRING WAS CORRUPTED BY ITS OWN MIGRATION SWEEP, AND RESTORED. `_migrate_step3_
    paths.py` rewrote D:\Research2 -> V:\Research4 across this file INCLUDING ITS PROSE, which turned
    true statements about the PAST into false ones ("V:\Research4 was hardcoded 1,961 times" — V: did
    not exist then). The ladder itself came out as ["V:\Research4", "V:\Research4"]: the same path
    twice, fallback destroyed. **THE SWEEP ATE THE FILE THAT EXISTS TO SURVIVE THE SWEEP.**
    This is the migration doc's own rule, violated by the migration: HISTORY RECORDS WHAT WAS TRUE
    THEN — rewriting it falsifies the record. Path-rewriting tools must skip prose, or be told to.

THE JOB THIS EXISTS FOR (measured 2026-07-16):
  · `D:\Research2` was hardcoded **1,961 times across 100 code files** (544 .py · 1,412 .bat ·
    4 .vbs · 1 .html). Every one of them is a landmine the moment the tree moves — and it just did.
  · The SAME strings are what pin the rails to Keith's DESKTOP. **PROVEN 2026-07-16: the Linux
    sandbox reaches aiplatform / generativelanguage / api.x.ai / crossref AND reads .secrets through
    the mount — a Vertex call answered in 756 ms with NO DESKTOP, vs 1.3 s via the desktop path.**
    The ONLY thing stopping headless operation was `KEY_FILE = r"D:\Research2\.secrets\..."`, which
    in Linux is not a path at all, just a filename that does not exist.
  ⇒ ONE resolver fixes BOTH: the migration AND Keith's Rule 2 ("run everything in the background").

Keith 2026-07-16: "we need make using FULL/GLOBAL (non-relative) addressing the norm."
  This is that rule in code. Callers ask for a ROLE ("the secrets dir", "the archive"), never a
  letter. The letter is an implementation detail that has now changed twice.

RESOLUTION ORDER — ONE Windows entry, on purpose:
  Windows : V:\Research4   (the live tree, NVMe). NO FALLBACK — see the D:\Research3 note below.
  Sandbox : /sessions/*/mnt/Research4  ->  /sessions/*/mnt/Research2  (pre-cutover sessions only)
  ⚠ THE SANDBOX SESSION NAME CHANGES EVERY SESSION ("focused-affectionate-hopper", etc). That is why
    this globs instead of hardcoding — a literal /sessions/<name>/... is stale the moment you write it.
  ⚠ D:\Research3 is DELIBERATELY NOT in the ladder. After the cutover it is the frozen archive; if a
    script ever resolved to it, it would silently read stale data and look fine. Fail loudly instead.

USE:
    from bts_paths import ROOT, secrets, ai, archive, mesh
    from bts_paths import airoot, board, queue   # V:\Ai peer files, not Research4
    KEY_FILE = secrets("vertex_key.txt")
    python bts_paths.py            -> print what resolved, and why
================================================================================
"""
import os, glob, sys

# ⚠⚠ ONE ENTRY PER PLATFORM, DELIBERATELY. THERE IS NO FALLBACK, AND THAT IS THE POINT.
#
#   Windows: the sweep left this as ["V:\Research4","V:\Research4"] — the same path twice, which is not
#   a ladder, it is a typo that happens to work. Fixed 2026-07-17.
#
#   Sandbox: "/sessions/*/mnt/Research2" was REMOVED 2026-07-17. It was there as a pre-cutover fallback,
#   and it became a live hazard the moment the cutover half-completed: the rename of D:\Research2 ->
#   D:\Research3 FAILED (handle held), so **D:\Research2 STILL EXISTS as a STALE FORK** while every
#   pointer already aims at V:. A session that mounted Research2 and not Research4 would have silently
#   resolved to the fork, read stale data, and LOOKED COMPLETELY FINE.
#
#   That is the same reason D:\Research3 is excluded: **a resolver that silently falls back to a stale
#   tree is worse than one that fails.** A crash names the problem in one line. A silent fallback ships
#   a chapter built on the wrong archive. FAIL LOUDLY.
_WIN = [r"V:\Research4"]
_NIX = ["/sessions/*/mnt/Research4"]


def _resolve():
    """Return (root, how). Never guesses — if nothing is found it raises."""
    if os.name == "nt":
        for p in _WIN:
            if os.path.isdir(p):
                return p, "windows"
    else:
        for pat in _NIX:
            hits = sorted(glob.glob(pat))
            if hits:
                return hits[0], "sandbox-glob"
    # An override for anything exotic (a peer's box, a test tree).
    env = os.environ.get("BTS_RESEARCH_ROOT")
    if env and os.path.isdir(env):
        return env, "env:BTS_RESEARCH_ROOT"
    raise RuntimeError(
        "bts_paths: cannot find the research tree.\n"
        "  tried (windows): %s\n  tried (sandbox): %s\n"
        "  Set BTS_RESEARCH_ROOT to override.\n"
        "  NOTE: D:\\Research3 is EXCLUDED on purpose — it is the frozen archive after the "
        "2026-07-16 migration. Resolving to it would read stale data and look fine." %
        (_WIN, _NIX))


try:
    ROOT, HOW = _resolve()
except RuntimeError:
    # Snapshot / sandbox with no Research4: Research4 helpers stay fail-loud on use.
    # airoot / board / queue do not need that tree.
    ROOT, HOW = None, "unresolved"

# V:\Ai is the live peer-file root (letters, _board, _queue, tmp). Distinct from
# ROOT (V:\Research4). Join only — never create the path.
_AI_ROOT = r"V:\Ai"


def _need_root():
    if not ROOT:
        raise RuntimeError(
            "bts_paths: cannot find the research tree. Set BTS_RESEARCH_ROOT.")
    return ROOT

def p(*parts):      return os.path.join(_need_root(), *parts)
def ai(*parts):     return os.path.join(_need_root(), "Ai", *parts)
def mesh(*parts):   return os.path.join(_need_root(), "Ai", "BTS_MESH", *parts)
def archive(*parts):return os.path.join(_need_root(), "Ai", "PhD2_DATA_ARCHIVE", *parts)
def working(*parts):return os.path.join(_need_root(), "Ai", "PhD2_DATA_ARCHIVE", "00_WORKING", *parts)

def secrets(*parts):
    """The keys. SAFE BY LOCATION: a SIBLING of Ai\\, never inside it — the R2 publish pushes Ai\\ to a
    PUBLIC website, so an exclude list is a blocklist and this is not. Never move it under Ai\\."""
    return os.path.join(_need_root(), ".secrets", *parts)


def airoot(*parts):
    """V:\\Ai\\... — letters, tmp, and the peer-file tree. Join only; never create."""
    return os.path.join(_AI_ROOT, *parts)


def board(*parts):
    """V:\\Ai\\_board\\...  e.g. board('board.json')."""
    return airoot("_board", *parts)


def queue(*parts):
    """V:\\Ai\\_queue\\...  e.g. queue('tree_lock.json')."""
    return airoot("_queue", *parts)


if __name__ == "__main__":
    print("=" * 72)
    print("  bts_paths")
    print("=" * 72)
    print("  os.name   : %s" % os.name)
    print("  ROOT      : %s" % ROOT)
    print("  resolved  : %s" % HOW)
    print()
    for name, fn in (("ai", ai), ("mesh", mesh), ("archive", archive),
                     ("working", working), ("secrets", secrets)):
        try:
            d = fn()
            print("  %-9s %-52s %s" % (name, d, "OK" if os.path.isdir(d) else "*** MISSING ***"))
        except RuntimeError as e:
            print("  %-9s %s" % (name, e))
    print()
    for name, fn, arg in (("airoot", airoot, ()),
                          ("board", board, ("board.json",)),
                          ("queue", queue, ("tree_lock.json",))):
        d = fn(*arg)
        print("  %-9s %-52s %s" % (name, d, "exists" if os.path.isfile(d) or os.path.isdir(d) else "join-only"))
    print()
    try:
        k = secrets("vertex_key.txt")
        print("  key check : %-52s %s" % (k, "OK" if os.path.isfile(k) else "*** MISSING ***"))
    except RuntimeError:
        print("  key check : (research tree unresolved)")
    print()
    print("  ladder (win)    : %s" % _WIN)
    print("  ladder (sandbox): %s" % _NIX)
    print("  D:\\Research3 is EXCLUDED on purpose (frozen archive; would read stale and look fine).")
    sys.exit(0)
