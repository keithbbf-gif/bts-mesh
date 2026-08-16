#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""toml_guard.py - refuse a TOML write that would not parse, and NAME the duplicate key.

PLM-43. Measured 2026-08-11: an `owed` key was added to a `[[surface]]` block that already
had one twenty lines further down, on a long line a `Grep` had elided from its output.
`rails.toml` did not parse for about twenty minutes - the S-118 failure, self-inflicted
while repairing the very entry it broke.

A duplicate key is INVISIBLE TO THE EYE and FATAL TO tomllib, and `tomllib`'s own message
("Cannot overwrite a value at line N") names a LINE, not the KEY or the other occurrence -
so the reader still has to hunt. This names both.

    from toml_guard import safe_write, find_duplicates
    safe_write(path, new_text)      # writes only if it parses; raises with detail if not
"""
import re
import tomllib


def find_duplicates(text: str):
    """Return [(key, [line numbers])] for keys repeated inside the same table block."""
    dupes, table, seen = [], None, {}
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith("[[") or (s.startswith("[") and s.endswith("]")):
            table, seen = "%s#%d" % (s, n), {}
            continue
        m = re.match(r"^([A-Za-z_][\w.-]*)\s*=", s)
        if not m:
            continue
        k = m.group(1)
        if k in seen:
            dupes.append((k, [seen[k], n], table))
        else:
            seen[k] = n
    return dupes


def validate(text: str):
    """Return (ok, message). Never guesses: reports what it actually found."""
    try:
        tomllib.loads(text)
        return True, "parses"
    except Exception as e:
        d = find_duplicates(text)
        if d:
            bits = ["duplicate key '%s' at lines %s in %s" % (k, ln, t) for k, ln, t in d]
            return False, "%s || %s" % (e, "; ".join(bits))
        return False, str(e)


def safe_write(path, text):
    """Validate, back up, write, re-read from DISK, and RESTORE if the re-read fails.

    🔴 THE RESTORE WAS MISSING UNTIL 2026-08-16, AND THAT IS THE WHOLE POINT OF THE FUNCTION.
    It validated the string, copied a .guard.bak, wrote, re-parsed from disk — all correct — and
    then, on failure, raised and walked away, leaving the broken file in place and the backup
    untouched. A writer whose safety net is a file nobody restores is a writer with no safety net.

    Found twice, independently, on the same day:
      · at 03:45 this session, when a JSON-shaped line went into rails.toml. toml_guard REFUSED it,
        bts_kdash_feed crashed, and bts_health went RED reporting two findings that had nothing to
        do with either — the whole control layer describing symptoms of a file it could no longer
        read. The rollback that existed in the calling script was unreachable for the same reason:
        it covered a rail-COUNT mismatch and a PARSE error jumped straight past it.
      · by the Grok Bot QA Engineer, in its first pass over the bundle, ranked fifth by silent lie:
        "safe_write re-parses from disk (good) but on a failed re-parse it raises and leaves the
        broken file. The .guard.bak is never restored."

    ⇒ A ROLLBACK MUST COVER THE FAILURE YOU DID NOT PREDICT. Not just the one you thought of.
    """
    ok, msg = validate(text)
    if not ok:
        raise ValueError("REFUSED to write %s: %s" % (path, msg))
    import pathlib, shutil
    p = pathlib.Path(path)
    bak = p.with_suffix(p.suffix + ".guard.bak")
    had_backup = False
    if p.exists():
        shutil.copy2(p, bak)
        had_backup = True
    try:
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        ok2, msg2 = validate(p.read_bytes().decode("utf-8"))
        if not ok2:
            raise ValueError("WROTE AND IT DOES NOT PARSE FROM DISK: %s" % msg2)
    except Exception as e:                                            # noqa: BLE001
        # ANY failure past this point — parse, encoding, disk full, a truncated write — puts the
        # original back. The mount has lied about file contents thirteen times; the one thing that
        # must never happen here is leaving a control file that cannot be read.
        if had_backup:
            try:
                shutil.copy2(bak, p)
                raise ValueError("%s || ORIGINAL RESTORED from %s — %s is unchanged."
                                 % (e, bak.name, p.name)) from None
            except ValueError:
                raise
            except Exception as e2:                                   # noqa: BLE001
                raise ValueError("%s || 🔴 AND THE RESTORE ALSO FAILED (%s). %s IS BROKEN ON DISK. "
                                 "The backup is at %s." % (e, e2, p, bak)) from None
        raise ValueError("%s || no backup existed (the file was new), so %s has been removed."
                         % (e, p.name)) from None
    return True


def selftest():
    good = 'a = 1\n[[x]]\nb = 2\n'
    bad = '[[x]]\nowed = "one"\nk = 3\nowed = "two"\n'
    checks = [
        ("clean toml validates", validate(good)[0]),
        ("a duplicate key is REFUSED", not validate(bad)[0]),
        ("and the KEY is named, not just a line number",
         "owed" in validate(bad)[1]),
        ("and BOTH line numbers are given", "[2, 4]" in validate(bad)[1]),
        ("find_duplicates is silent on clean input", not find_duplicates(good)),
    ]
    for label, okk in checks:
        print("  %s  %s" % ("OK  " if okk else "FAIL", label))
    bad_n = [l for l, g in checks if not g]
    print("SELFTEST PASS - it refuses a duplicate and names it."
          if not bad_n else "SELFTEST FAIL - %d" % len(bad_n))
    return 1 if bad_n else 0


def check_files(paths) -> int:
    """Validate NAMED FILES. Exit non-zero if any has a duplicate key or will not parse.

    🔴 THIS DID NOT EXIST UNTIL 2026-08-16, AND ITS ABSENCE WAS A FALSE-GREEN TRAP.
    `__main__` ran `selftest()` unconditionally and IGNORED argv entirely. So
    `py toml_guard.py rails.toml` printed "SELFTEST PASS - it refuses a duplicate and names it."
    and exited 0 — WITHOUT EVER OPENING rails.toml. The output names the right behaviour in the
    present tense and says nothing about your file, which is the most convincing way to be useless.

    CLAUDE.md has said since 2026-08-03: "VALIDATE corrections.toml AT EVERY TidyUP AND REFUSE TO
    CLOSE THE SESSION IF IT FAILS... Same for rails.toml and registries.toml." The obvious command
    for that rule could not perform it, and would have reported success either way.

    FOUND BY A NEGATIVE CONTROL, and only by that. A validation run planted a duplicate key in a
    COPY of rails.toml and REQUIRED the guard to refuse it. The guard returned 0 — so the control
    fired, and what it caught was not a bad TOML file but a checker that had never been reading any
    file at all. Both runs in that job had been the selftest. (S-147: vary the defect, not the input.)
    """
    import pathlib
    rc = 0
    for arg in paths:
        p = pathlib.Path(arg)
        if not p.exists():
            print("  MISSING  %s" % p)
            rc = 2
            continue
        ok, msg = validate(p.read_bytes().decode("utf-8", "replace"))
        print("  %s  %s%s" % ("OK   " if ok else "REFUSE", p, "" if ok else "\n           %s" % msg))
        if not ok:
            rc = 1
    return rc


if __name__ == "__main__":
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--selftest" in sys.argv or not args:
        sys.exit(selftest())
    sys.exit(check_files(args))
