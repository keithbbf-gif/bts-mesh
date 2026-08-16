r"""
MIGRATION VERIFY — is V:\Research4 actually self-contained and runnable?
Run on the HOST. Answers three questions, and each one can FAIL loudly:
  1. Any LIVE V:\Research4 refs left in runnable code?   (must be 0)
  2. Does the rewritten python still compile?             (must be 0 failures)
  3. Are history + backups still PRESERVED?               (must be >0 — if this hits 0, the rewrite
     ate the historical record, which is worse than a stale pointer)
#3 is the NEGATIVE CONTROL: a "0 refs left everywhere" result would look like success and mean the
opposite. A check that can only pass is not a check.
"""
import os, re, io, sys, py_compile

ROOT = r"V:\Research4"
EXT = {".py", ".bat", ".vbs", ".json", ".html", ".cmd", ".ps1"}
FROZEN = ("_backup", "00_session_", ".bak_", "_old", "__pycache__")
pat1 = re.compile(re.escape(r"V:\Research4"), re.I)
pat2 = re.compile(re.escape("D:\\\\Research2"), re.I)


def scan():
    live_code, frozen_refs, hist_refs = [], 0, 0
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d.lower() != "__pycache__"]
        low_dp = dp.lower()
        frozen = any(m in low_dp for m in FROZEN)
        for x in fn:
            p = os.path.join(dp, x)
            ext = os.path.splitext(x)[1].lower()
            if ext not in EXT and ext != ".md":
                continue
            try:
                if os.path.getsize(p) > 8 * 1024 * 1024:
                    continue
                t = io.open(p, encoding="utf-8", errors="strict").read()
            except Exception:
                continue
            n = len(pat1.findall(t)) + len(pat2.findall(t))
            if not n:
                continue
            if frozen:
                frozen_refs += n
            elif ext == ".md":
                hist_refs += n
            else:
                live_code.append((n, p[len(ROOT) + 1:]))
    return live_code, frozen_refs, hist_refs


def main():
    print("=" * 74)
    print("  MIGRATION VERIFY — %s" % ROOT)
    print("=" * 74)

    live, froz, hist = scan()
    print("\n  1. LIVE V:\\Research4 refs in RUNNABLE code  (must be 0)")
    if live:
        for n, rel in sorted(live, key=lambda x: -x[0])[:20]:
            print("       *** %4dx  %s" % (n, rel))
        print("     FAIL — %d refs in %d files still point at the OLD tree." % (sum(n for n, _ in live), len(live)))
    else:
        print("     PASS — 0. No runnable code points at V:\\Research4.")

    print("\n  2. Does the rewritten python still COMPILE?")
    bad = tot = 0
    for dp, dn, fn in os.walk(os.path.join(ROOT, "Ai", "BTS_MESH")):
        if any(m in dp.lower() for m in ("_backup", "__pycache__")):
            continue
        for x in fn:
            if not x.endswith(".py"):
                continue
            tot += 1
            try:
                py_compile.compile(os.path.join(dp, x), doraise=True)
            except Exception as e:
                bad += 1
                print("       *** %-28s %s" % (x, str(e).replace("\n", " ")[:80]))
    print("     %s — BTS_MESH: %d python files, %d failed" % ("PASS" if bad == 0 else "FAIL", tot, bad))

    print("\n  3. NEGATIVE CONTROL — is the RECORD still intact? (must be > 0)")
    print("     history .md refs preserved : %d" % hist)
    print("     frozen/backup refs preserved: %d" % froz)
    if hist > 0 and froz > 0:
        print("     PASS — history and backups still say V:\\Research4, which is what was TRUE then.")
    else:
        print("     *** FAIL — the rewrite ate the historical record. That is worse than a stale pointer.")

    print("\n  4. Does the tree stand alone?")
    for rel in (".secrets\\vertex_key.txt", "CLAUDE.md", "Ai\\BTS_MESH\\bts_paths.py",
                "Ai\\BTS_MESH\\bts_vertex.py", "Ai\\BTS_MESH\\jack_command.html",
                "Ai\\00_ROLD_COMMANDS_TidyUp_BootUp.md"):
        p = os.path.join(ROOT, rel)
        print("     %-44s %s" % (rel, "OK" if os.path.exists(p) else "*** MISSING ***"))
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
