#!/usr/bin/env python3
"""verify_pointers.py — THE FAILING CHECK for the ROLD pointer architecture.

A pointer architecture is only real if something goes RED when a pointer stops resolving.
SGH, 2026-07-30, adjudicating the design:

    "Those examples all have a real resolver with failure semantics; markdown does not.
     No resolve test -> not a pointer architecture; it's docs."

So this is the resolver. It walks every control document, finds every operator line, and
resolves it. Exit 0 = every pointer resolves. Exit 1 = at least one does not.

WHAT IT CHECKS
  POINTER:    <path>                        -> the path must exist
  INCLUDEIF:  <host-local fact> -> <path>   -> the path must exist (the fact is not evaluated here)
  OVERRIDE:   <key> = <value>               -> must parse as key = value
  PRECEDENCE: <ordered list>                -> must be non-empty
  <ANYTHING ELSE>:                          -> an UNKNOWN OPCODE IS A FAILURE, never a skip.

V:\\Ai\\BU.MD is also checked for POINTER SHAPE, not mere existence. A 46 KB mailbox or
monolith that happens to contain one `POINTER:` line used to close GREEN. That is a false
green. The boot pointer must be short and start with `POINTER:` or the `BOOT POINTER`
banner. tidyup_bu.is_pointer_shaped is the predicate; tidyup_bu.py is the writer.

That last rule is the one that matters. A checker that silently ignores what it does not
understand reports green on a file it never read - which is the same class of defect as the
mount that returned a clean, specific, wrong answer (SCARS S-28).

ANCHORS: a pointer may carry a "#anchor". The anchor is checked too - a heading must exist
whose slug matches - because a pointer into a heading that has been renamed is exactly the
rot this whole scheme exists to prevent. An anchor miss is reported as ANCHOR, and is a
FAILURE, but is listed separately so a rename is not confused with a missing file.

RUNS ON BOTH: Windows (where V:\\Research4 is a drive letter) and the Linux sandbox (where it
is a FUSE mount), by resolving through bts_paths. Paths in the documents are written in
Windows form; they are translated here.

NEGATIVE CONTROL — this is not optional:
    python verify_pointers.py --selftest
plants a document containing a pointer to a file that does not exist and an unknown opcode,
and asserts the checker returns non-zero for both. A verifier that has never been shown to
FAIL is not a verifier (RULES.md).
"""
from __future__ import annotations

import os
import re
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "BTS_MESH"))

try:
    import bts_paths
    ROOT = bts_paths.ROOT
    HOW = bts_paths.HOW
except Exception as e:                                    # fail loudly, never guess a root
    print("FATAL: cannot resolve the research tree via bts_paths: %s" % e)
    sys.exit(2)

if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from tidyup_bu import is_ai_bu, is_pointer_shaped

# V:\Ai is a SIBLING of the research tree, not inside it. On Windows it is a real path; in the
# sandbox it is its own mount. Resolve it the same way the tree is resolved - never hardcode.
def _ai_root() -> str:
    if os.name == "nt":
        return r"V:\Ai"
    import glob as _g
    hits = sorted(_g.glob("/sessions/*/mnt/Ai"))
    return hits[0] if hits else ""


AI_ROOT = _ai_root()

OPCODES = ("POINTER", "INCLUDEIF", "OVERRIDE", "PRECEDENCE")
_OP_RE = re.compile(r"^\s*(?:[-*>]\s*)?(?:\*\*)?([A-Z][A-Z_]{2,15})(?:\*\*)?:\s*(.+?)\s*$")

# Documents whose operator lines are checked. Add here, not in a caller.
CONTROL_DOCS = [
    os.path.join(ROOT, "Ai", "ROLD", "00_INDEX.md"),
    os.path.join(ROOT, "Ai", "ROLD", "RULES.md"),
    os.path.join(ROOT, "Ai", "ROLD", "RAILS.md"),
    os.path.join(ROOT, "Ai", "ROLD", "ROUTINES.md"),
    os.path.join(ROOT, "Ai", "ROLD", "SCARS.md"),
    os.path.join(ROOT, "Ai", "ROLD", "STREAM_LEGAL.md"),
    os.path.join(ROOT, "Ai", "ROLD", "00_ROLD_ARCHITECTURE.md"),
    os.path.join(ROOT, "Ai", "ROLD", "STREAMS", "STREAM_PLUMBING.md"),   # stub -> streams/plumbing.toml
    os.path.join(ROOT, "Ai", "ROLD", "STREAMS", "STREAM_PHYSICS.md"),    # stub -> streams/physics.toml
    os.path.join(ROOT, "Ai", "ROLD", "STREAMS", "STREAM_CHAPTER.md"),    # stub -> streams/chapter.toml
    os.path.join(ROOT, "Ai", "ROLD", "REGISTRIES", "00_REGISTRIES.md"),   # stub -> registries.toml
    os.path.join(ROOT, "Ai", "ROLD", "ARCHIVE", "00_ARCHIVE.md"),         # stub -> archive.toml
]
if AI_ROOT:
    CONTROL_DOCS += [os.path.join(AI_ROOT, "BU.MD"),
                     os.path.join(AI_ROOT, "Streams", "PLM_TODOS.md")]  # tidied 2026-07-31

# 🔴 APPEND-ONLY NARRATIVE — added 2026-08-11. These documents are PROSE BY CONSTRUCTION.
#
# SCARS.md is append-only and must NEVER be edited (ROLD\00_INDEX.md). It therefore accumulates
# English sentences that happen to open with a capitalised word and a colon — measured today,
# line 1635 "**GEM: five of seven case citations do not exist.**" and line 2636 "**REBUILT:**
# `V:\Ai\Legal\WARGAME\...`". Those two lines, and ONLY those two, are why this checker closed
# RED with failed=0. Nothing was broken. The checker was wrong.
#
# A check that cries wolf gets muted, and a muted check is worse than none — the same reasoning
# that already governs the Desktop refusal above.
#
# ⚠ THE EXEMPTION IS NARROW AND IT IS NOT A SKIP OF THE DOCUMENT.
#   - POINTER / INCLUDEIF / OVERRIDE / PRECEDENCE are resolved in these files EXACTLY as
#     everywhere else. SCARS.md carries two real pointers (lines 6-7) and they are still checked.
#   - Only the "unrecognised WORD:" arm is suppressed, and every suppression is COUNTED and
#     PRINTED as narrative-prose=N. It is reported, not hidden. Silently ignoring what it does
#     not understand is the original defect this file exists to prevent (S-28).
#   - selftest() asserts a broken POINTER inside a narrative document STILL goes RED. Without
#     that control this exemption would be indistinguishable from switching the check off.
NARRATIVE_DOCS = frozenset({"scars.md"})


def _is_narrative(doc: str) -> bool:
    return os.path.basename(doc).lower() in NARRATIVE_DOCS


def _cut_commentary(s: str) -> str:
    """A pointer line may carry a trailing gloss. THE PATH ENDS at the first of: two spaces, an
    em/en dash, an opening bracket, or a '#'. Written down here because it is part of the operator
    grammar, not a parser convenience — an operator whose argument has no defined end is an
    operator you cannot check, and an unheckable operator is decoration."""
    s = s.strip().strip("`").strip()
    for sep in ("  ", " — ", " – ", " -- ", " (", "\t"):
        i = s.find(sep)
        if i > 0:
            s = s[:i]
    # Strip quoting AGAIN after the cut: a path written as `V:\x.md` — gloss keeps its CLOSING
    # backtick when the gloss is removed, and the leading one was already eaten. Caught 2026-07-30
    # by this checker on a pointer added the same minute.
    return s.strip().rstrip(".,;").strip("`'\"").strip()


def _translate(raw: str) -> str:
    """A documented Windows path -> a path on THIS machine. Never guesses: an absolute path we
    cannot map is returned unchanged and will simply fail to exist, which is the correct answer."""
    p = _cut_commentary(raw)
    p = p.split("#", 1)[0].strip()
    if not p:
        return ""
    if p.startswith("<") or p.startswith("&lt;"):
        return ""            # <path> is a METAVARIABLE (the grammar block in 00_INDEX), not a path
    if os.name != "nt" and p.startswith("/"):
        return p                                   # already a native path (selftest, sandbox tools)
    low = p.replace("/", "\\").lower()
    if low.startswith("v:\\research4"):
        return os.path.join(ROOT, *[s for s in p.replace("/", "\\")[13:].split("\\") if s])
    if low.startswith("v:\\ai"):
        return os.path.join(AI_ROOT, *[s for s in p.replace("/", "\\")[6:].split("\\") if s]) \
            if AI_ROOT else p
    if re.match(r"^[a-z]:\\", low) or p.startswith("/") or p.startswith("\\\\"):
        return p if os.name == "nt" else ""      # other drive letters: unmappable off Windows
    if low.startswith("desktop\\"):
        # 🔴 DELIBERATE REFUSAL — Keith, 2026-07-30: "I delete all .bat from DT and everything else
        # not explicitly permitted... Nothing else can be considered stable, it's a one and done."
        # The Desktop is a DELIVERY SURFACE, not a repository. A .bat there has a lifetime of one
        # use; only KDash.vbs and Judge-UPS.vbs persist. Resolving Desktop paths would paint this
        # repo permanently RED for files that are SUPPOSED to be gone — and a check that cries wolf
        # gets muted, which is worse than no check at all. DO NOT "FIX" THIS SKIP.
        return ""
    return os.path.join(ROOT, *[s for s in p.replace("/", "\\").split("\\") if s])


def _slugs(path: str) -> set:
    out = set()
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("#"):
                    h = line.lstrip("#").strip().lower()
                    h = re.sub(r"[^\w\s-]", "", h)
                    out.add(re.sub(r"[\s_]+", "-", h).strip("-"))
    except Exception:
        pass
    return out


def check(docs=None, verbose=True):
    docs = docs or CONTROL_DOCS
    fails, anchors, unknown, ok, skipped, prose = [], [], [], 0, 0, 0
    for doc in docs:
        if not os.path.exists(doc):
            fails.append((doc, "<the control document itself>", "MISSING DOCUMENT"))
            continue
        # V:\Ai\BU.MD: GREEN requires pointer SHAPE, not existence. A mailbox or
        # monolith with one POINTER: line inside is the false green this closes.
        if is_ai_bu(doc):
            raw = open(doc, "rb").read()
            if not is_pointer_shaped(raw.decode("utf-8", "replace"), size=len(raw)):
                fails.append((doc, "<the boot pointer itself>",
                              "NOT POINTER-SHAPED (need a short file starting with "
                              "POINTER: or BOOT POINTER; a POINTER line inside a "
                              "mailbox/monolith is a FALSE GREEN)"))
                continue
        narrative = _is_narrative(doc)
        in_fence = False
        with open(doc, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if line.lstrip().startswith("```"):
                    in_fence = not in_fence          # fenced blocks still carry real operators
                m = _OP_RE.match(line)
                if not m:
                    continue
                op, arg = m.group(1), m.group(2)
                if op not in OPCODES:
                    if op in ("SUMMARY", "CONFIDENCE", "OPEN_QUESTIONS", "NOTE", "STATUS",
                              "TODO", "OWED", "WARNING", "SRC", "DST", "LOG", "SCOPE"):
                        continue                     # known prose labels, not operators
                    if narrative:
                        # Append-only prose. Counted and printed, never silently dropped.
                        prose += 1
                        continue
                    unknown.append((doc, n, op))
                    continue
                if op == "OVERRIDE":
                    (ok := ok + 1) if "=" in arg else fails.append((doc, arg, "OVERRIDE has no '='"))
                    continue
                if op == "PRECEDENCE":
                    (ok := ok + 1) if arg.strip() else fails.append((doc, arg, "PRECEDENCE empty"))
                    continue
                target = arg.split("->")[-1] if op == "INCLUDEIF" else arg
                real = _translate(target)
                if not real:
                    skipped += 1
                    continue
                if os.path.exists(real):
                    frag = _cut_commentary(target.split("#", 1)[1]) if "#" in target else ""
                    if frag and real.lower().endswith(".md") and frag.lower() not in _slugs(real):
                        anchors.append((doc, target, "anchor '#%s' not found" % frag))
                    else:
                        ok += 1
                else:
                    fails.append((doc, target.strip(), "does not exist: %s" % real))

    if verbose:
        print("=" * 78)
        # ASCII ONLY on this line. A Windows console is cp1252 and turned a middot into a black
        # diamond in POINTERS.txt on 2026-07-30 — the same mojibake class as MCP_WIRE.txt.
        print("  verify_pointers  |  root=%s (%s)" % (ROOT, HOW))
        print("=" * 78)
        for d, t, why in fails:
            print("  FAIL    %-34s -> %s  [%s]" % (os.path.basename(d), t, why))
        for d, t, why in anchors:
            print("  ANCHOR  %-34s -> %s  [%s]" % (os.path.basename(d), t, why))
        for d, n, op in unknown:
            print("  OPCODE  %-34s line %-5s unknown operator '%s:'" % (os.path.basename(d), n, op))
        print("-" * 78)
        print("  resolved=%d  failed=%d  anchor-miss=%d  unknown-opcode=%d  unmappable=%d"
              % (ok, len(fails), len(anchors), len(unknown), skipped))
        if prose:
            print("  narrative-prose=%d  (append-only documents: %s -- prose lines matching the"
                  % (prose, ", ".join(sorted(NARRATIVE_DOCS))))
            print("   operator shape are NOT opcodes. Their real POINTERs above are still checked.)")
        print("  RESULT: %s" % ("RED" if (fails or anchors or unknown) else "GREEN"))
    return len(fails) + len(anchors) + len(unknown)


def selftest() -> int:
    """NEGATIVE CONTROL. Four plants, and the last two are the ones that matter.

    A verifier that has never been shown to FAIL is not a verifier (RULES.md). And an EXEMPTION
    that has never been shown to still catch a real fault is not an exemption — it is the check
    switched off for that file. So the narrative case is tested in BOTH directions.
    """
    d = tempfile.mkdtemp(prefix="ptrtest_")
    good = os.path.join(d, "real.md")
    open(good, "w", encoding="utf-8").write("# real\n")
    missing = os.path.join(d, "definitely_not_here.md")

    doc = os.path.join(d, "doc.md")
    open(doc, "w", encoding="utf-8").write(
        "POINTER: %s\nPOINTER: %s\nWIBBLE: nonsense\n" % (good, missing))

    clean_doc = os.path.join(d, "clean.md")
    open(clean_doc, "w", encoding="utf-8").write("POINTER: %s\n" % good)

    # 3 + 4: an APPEND-ONLY NARRATIVE document. Named SCARS.md so _is_narrative() fires.
    nar_ok = os.path.join(d, "SCARS.md")
    open(nar_ok, "w", encoding="utf-8").write(
        "POINTER: %s\n\n**GEM: five of seven case citations do not exist.**\n"
        "**REBUILT:** something happened here, in English.\n" % good)

    nar_bad_dir = tempfile.mkdtemp(prefix="ptrtest_nar_")
    nar_bad = os.path.join(nar_bad_dir, "SCARS.md")
    open(nar_bad, "w", encoding="utf-8").write(
        "POINTER: %s\n\n**GEM: prose that is not an opcode.**\n" % missing)

    # 5 + 6: V:\Ai\BU.MD shape. Existence of a POINTER line inside a mailbox used
    # to close GREEN. Named .../Ai/BU.MD so is_ai_bu() fires.
    ai_dir = os.path.join(d, "Ai")
    os.makedirs(ai_dir, exist_ok=True)
    mailbox = os.path.join(ai_dir, "BU.MD")
    open(mailbox, "w", encoding="utf-8").write(
        "POINTER: %s\n\n" % good + ("QA mailbox line\n" * 2500))
    ai_ok_dir = tempfile.mkdtemp(prefix="ptrtest_aibu_")
    os.makedirs(os.path.join(ai_ok_dir, "Ai"), exist_ok=True)
    ai_ok = os.path.join(ai_ok_dir, "Ai", "BU.MD")
    open(ai_ok, "w", encoding="utf-8").write("BOOT POINTER -- V:\\Ai\\BU.MD\nPOINTER: %s\n" % good)

    print("--- selftest 1/6: broken pointer + unknown opcode, expecting RED ---")
    n = check([doc])
    clean = check([clean_doc], verbose=False)
    print("--- selftest 3/6: narrative doc, prose only, expecting GREEN ---")
    nar_clean = check([nar_ok])
    print("--- selftest 4/6: narrative doc with a BROKEN POINTER, expecting RED ---")
    nar_broken = check([nar_bad])
    print("--- selftest 5/6: mailbox BU.MD with a valid POINTER line, expecting RED ---")
    mailbox_n = check([mailbox])
    print("--- selftest 6/6: pointer-shaped BU.MD, expecting GREEN ---")
    shaped_n = check([ai_ok])

    print("-" * 78)
    print("  broken doc      = %d  (want >=2)" % n)
    print("  clean doc       = %d  (want 0)" % clean)
    print("  narrative prose = %d  (want 0  -- the exemption works)" % nar_clean)
    print("  narrative FAULT = %d  (want >=1 -- the exemption did NOT disable pointer checking)"
          % nar_broken)
    print("  mailbox BU.MD   = %d  (want >=1 -- shape, not existence)" % mailbox_n)
    print("  shaped BU.MD    = %d  (want 0)" % shaped_n)
    if (n >= 2 and clean == 0 and nar_clean == 0 and nar_broken >= 1
            and mailbox_n >= 1 and shaped_n == 0):
        # ASCII ONLY. An em dash here came back as mojibake in the queue log on the very run
        # that proved this fix - S-134's lesson generalized: anything a scheduler may redirect
        # must be ASCII on stdout, not just free of emoji.
        print("SELFTEST PASS - RED on a broken pointer, GREEN on prose, STILL RED on a")
        print("                broken pointer inside an append-only narrative document,")
        print("                and RED on a mailbox BU.MD that merely CONTAINS a POINTER line.")
        return 0
    print("SELFTEST FAIL — this checker cannot be trusted.")
    return 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else (1 if check() else 0))
