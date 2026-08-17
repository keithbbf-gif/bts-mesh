#!/usr/bin/env python3
"""tidyup_bu.py — THE TidyUP WRITER for V:\\Ai\\BU.MD. STEP 8 and STEP 9, bound.

WHY THIS FILE EXISTS
--------------------
TidyUP STEP 8 and STEP 9 lived as prose in ROUTINES.md. Agents followed them by hand:

  STEP 8  copy V:\\Ai\\BU.MD -> 00_WORKING\\MIRROR_BU.md   (always, last, mandatory)
  STEP 9  overwrite V:\\Ai\\BU.MD with a monolith of operational state

That is two smash holes. Measured 2026-08-17 on the live tree (not invented here):

  * V:\\Ai\\BU.MD was a 46 KB QA mailbox, not a pointer.
  * MIRROR_BU.md was already stale (20 KB vs 46 KB).
  * A blind STEP 8 copy would publish the mailbox over the last good mirror.
  * A STEP 9 monolith emit would clobber the mailbox and land a report on V:\\Ai\\BU.MD.
  * V:\\Research4\\BU.MD is a live READ path (mesh_test.py, bts_paths.p()) and is
    NEVER written at TidyUP.

Contract (ROUTINES.md STEP 8 / STEP 9, RULES.md R5):

  * V:\\Ai\\BU.MD is a POINTER file: short, starts with POINTER: or the BOOT POINTER banner.
  * STEP 8 copies a pointer-shaped file only. Mailbox/monolith => SKIP. Leave MIRROR_BU.
  * STEP 9 writes a POINTER line only. Never a monolith. Never V:\\Research4\\BU.MD.
  * If V:\\Ai\\BU.MD is already a mailbox/monolith, STEP 9 REFUSES. Move it first.

This module is the writer. verify_pointers.py is the checker (shape, not mere existence).
Do not run TidyUP from here. --selftest plants files under tempfile and touches nothing live.

USAGE
    python tidyup_bu.py --selftest
    python tidyup_bu.py --step8 [--src PATH] [--dst PATH] [--pointer-source PATH]
    python tidyup_bu.py --step9 --target PATH [--path PATH]
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile

# Short. A 46 KB mailbox with one POINTER: line inside is NOT a pointer file.
POINTER_MAX_BYTES = 2048
POINTER_MAX_LINES = 8
POINTER_BANNER = "BOOT POINTER"
_POINTER_LINE = re.compile(r"^POINTER:\s*(\S.+?)\s*$")


def _norm(path: str) -> str:
    return os.path.normpath(os.path.abspath(path)).replace("\\", "/").lower().rstrip("/")


def is_research4_bu(path: str) -> bool:
    """V:\\Research4\\BU.MD (any spelling). Live READ path. Never a TidyUP write target."""
    return _norm(path).endswith("/research4/bu.md")


def is_ai_bu(path: str) -> bool:
    """V:\\Ai\\BU.MD (any spelling). The boot pointer. POINTER-shaped or RED."""
    return _norm(path).endswith("/ai/bu.md")


def _first_content_lines(text: str):
    body = text.lstrip("\ufeff")
    return [ln.strip() for ln in body.splitlines() if ln.strip()]


def pointer_target(text: str) -> str:
    """Return the first POINTER: referent, or ''."""
    for ln in _first_content_lines(text):
        m = _POINTER_LINE.match(ln)
        if m:
            return m.group(1).strip().strip("`\"'")
    return ""


def is_pointer_shaped(text: str, size: int | None = None) -> bool:
    """True only when the FILE is a pointer, not when a pointer line exists somewhere in it.

    A 46 KB QA report that happens to contain `POINTER: V:\\somewhere` is the false green
    this predicate exists to close. Existence of a POINTER opcode is not shape.
    """
    n = size if size is not None else len(text.encode("utf-8"))
    if n > POINTER_MAX_BYTES or n == 0:
        return False
    lines = _first_content_lines(text)
    if not lines or len(lines) > POINTER_MAX_LINES:
        return False
    i = 0
    head = lines[0].lstrip("#").strip()
    if head.upper().startswith(POINTER_BANNER):
        i = 1
        if i >= len(lines):
            return False
    if not _POINTER_LINE.match(lines[i]):
        return False
    # Exactly one POINTER: line. Extra POINTER: lines are a second home, and copies rot.
    ptrs = [ln for ln in lines if ln.startswith("POINTER:")]
    return len(ptrs) == 1 and bool(pointer_target(text))


def format_pointer(target: str) -> str:
    """The only legal emit for V:\\Ai\\BU.MD. ASCII. Banner + one POINTER line."""
    tgt = (target or "").strip()
    if not tgt:
        raise ValueError("POINTER target is empty")
    if "\n" in tgt or "\r" in tgt:
        raise ValueError("POINTER target must be a single path, not a monolith")
    text = "%s -- V:\\Ai\\BU.MD\nPOINTER: %s\n" % (POINTER_BANNER, tgt)
    if not is_pointer_shaped(text):
        raise ValueError("format_pointer produced a non-pointer; that is a writer bug")
    return text


def _read_raw(path: str) -> tuple[bytes, str]:
    raw = open(path, "rb").read()
    return raw, raw.decode("utf-8", "replace")


def _pointer_targets_path(text: str, path: str) -> bool:
    tgt = pointer_target(text)
    if not tgt:
        return False
    # Compare as written and as absolute. A Windows path on Linux will not abspath
    # the same way; also compare the normalized tail.
    a, b = _norm(tgt), _norm(path)
    if a == b:
        return True
    return os.path.normpath(tgt).replace("\\", "/").lower() == \
        os.path.normpath(path).replace("\\", "/").lower()


def step8_mirror(src: str, dst: str, pointer_source: str | None = None) -> dict:
    """STEP 8: copy a pointer-shaped file onto MIRROR_BU. Otherwise SKIP.

    Smash hole this binds: a blind copy of V:\\Ai\\BU.MD (mailbox/monolith) over
    00_WORKING\\MIRROR_BU.md. Skip is the safe behaviour. Self-clobber (pointer
    whose target IS dst) is also skipped.
    """
    if is_research4_bu(dst):
        return {"ok": False, "action": "refused",
                "reason": "never write V:\\Research4\\BU.MD"}
    candidates = []
    if pointer_source:
        candidates.append(pointer_source)
    candidates.append(src)
    seen = set()
    for cand in candidates:
        key = _norm(cand)
        if key in seen:
            continue
        seen.add(key)
        if not os.path.isfile(cand):
            continue
        raw, text = _read_raw(cand)
        if not is_pointer_shaped(text, size=len(raw)):
            continue
        if _pointer_targets_path(text, dst):
            return {"ok": True, "action": "skipped",
                    "reason": "pointer target is MIRROR_BU; copy would clobber the referent",
                    "from": cand, "to": dst}
        parent = os.path.dirname(dst)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.copy2(cand, dst)
        return {"ok": True, "action": "copied", "from": cand, "to": dst,
                "bytes": os.path.getsize(dst)}
    return {"ok": True, "action": "skipped",
            "reason": "no pointer-shaped source; mailbox/monolith is not copied over MIRROR_BU"}


def step9_write(path: str, target: str) -> dict:
    """STEP 9: write a POINTER line only. Never a monolith. Never Research4\\BU.MD.

    Smash holes this binds:
      * monolith emit onto V:\\Ai\\BU.MD
      * overwrite of a mailbox already sitting at V:\\Ai\\BU.MD
      * any write to V:\\Research4\\BU.MD
    """
    if is_research4_bu(path):
        return {"ok": False, "action": "refused",
                "reason": "never write V:\\Research4\\BU.MD (detail backlog; live READ path)"}
    try:
        text = format_pointer(target)
    except ValueError as e:
        return {"ok": False, "action": "refused", "reason": str(e)}
    if os.path.isfile(path):
        raw, existing = _read_raw(path)
        if not is_pointer_shaped(existing, size=len(raw)):
            return {"ok": False, "action": "refused",
                    "reason": "V:\\Ai\\BU.MD is a mailbox or monolith; move it first, "
                              "then write the POINTER line. Refusing clobber."}
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    back = open(path, "rb").read()
    if back.decode("utf-8") != text:
        return {"ok": False, "action": "refused", "reason": "write did not read back"}
    if not is_pointer_shaped(text, size=len(back)):
        return {"ok": False, "action": "refused", "reason": "emit was not pointer-shaped"}
    return {"ok": True, "action": "wrote", "path": path, "bytes": len(back),
            "target": target}


def selftest() -> int:
    """NEGATIVE CONTROLS. A writer never shown to refuse is not a bind."""
    print("=" * 78)
    print("  tidyup_bu --selftest")
    print("=" * 78)
    passed = []
    d = tempfile.mkdtemp(prefix="tidyup_bu_")

    good_tgt = os.path.join(d, "state.md")
    open(good_tgt, "w", encoding="utf-8").write("# live state\n")

    mailbox = os.path.join(d, "mailbox_BU.md")
    open(mailbox, "w", encoding="utf-8").write(
        "POINTER: %s\n" % good_tgt + ("QA mailbox line\n" * 2500))
    passed.append(("46KB-class mailbox with a POINTER line is NOT pointer-shaped",
                   not is_pointer_shaped(open(mailbox, encoding="utf-8").read(),
                                         size=os.path.getsize(mailbox))))

    short_ok = format_pointer(good_tgt)
    passed.append(("format_pointer is pointer-shaped", is_pointer_shaped(short_ok)))
    passed.append(("format_pointer starts with banner then POINTER:",
                   short_ok.splitlines()[0].startswith(POINTER_BANNER)
                   and short_ok.splitlines()[1].startswith("POINTER:")))

    # STEP 8: mailbox must not clobber MIRROR_BU
    mirror = os.path.join(d, "MIRROR_BU.md")
    open(mirror, "w", encoding="utf-8").write("LAST GOOD MIRROR\n")
    r8 = step8_mirror(mailbox, mirror)
    passed.append(("STEP 8 skips a mailbox source", r8.get("action") == "skipped"))
    passed.append(("STEP 8 left MIRROR_BU untouched",
                   open(mirror, encoding="utf-8").read() == "LAST GOOD MIRROR\n"))

    # STEP 8: pointer-shaped source copies
    src_ptr = os.path.join(d, "ptr.md")
    other = os.path.join(d, "other_state.md")
    open(other, "w", encoding="utf-8").write("x\n")
    open(src_ptr, "w", encoding="utf-8", newline="").write(format_pointer(other))
    r8c = step8_mirror(src_ptr, mirror)
    passed.append(("STEP 8 copies a pointer-shaped source", r8c.get("action") == "copied"))
    passed.append(("STEP 8 copy is still pointer-shaped",
                   is_pointer_shaped(open(mirror, encoding="utf-8").read(),
                                     size=os.path.getsize(mirror))))

    # STEP 8: dedicated pointer source wins over mailbox; self-clobber skips
    dedicated = os.path.join(d, "dedicated.md")
    mirror2 = os.path.join(d, "MIRROR2.md")
    open(mirror2, "w", encoding="utf-8").write("KEEP\n")
    open(dedicated, "w", encoding="utf-8", newline="").write(format_pointer(mirror2))
    r8s = step8_mirror(mailbox, mirror2, pointer_source=dedicated)
    passed.append(("STEP 8 skips pointer-to-self (would clobber referent)",
                   r8s.get("action") == "skipped" and "clobber" in r8s.get("reason", "")))
    passed.append(("STEP 8 self-clobber left dest untouched",
                   open(mirror2, encoding="utf-8").read() == "KEEP\n"))

    dest3 = os.path.join(d, "MIRROR3.md")
    open(dest3, "w", encoding="utf-8").write("OLD\n")
    ded2 = os.path.join(d, "dedicated2.md")
    open(ded2, "w", encoding="utf-8", newline="").write(format_pointer(other))
    r8d = step8_mirror(mailbox, dest3, pointer_source=ded2)
    passed.append(("STEP 8 copies dedicated pointer source when src is a mailbox",
                   r8d.get("action") == "copied"))
    passed.append(("STEP 8 dedicated copy replaced dest with the pointer file",
                   is_pointer_shaped(open(dest3, encoding="utf-8").read(),
                                     size=os.path.getsize(dest3))))

    # STEP 9: refuse Research4\\BU.MD
    r4 = os.path.join(d, "Research4", "BU.MD")
    os.makedirs(os.path.dirname(r4), exist_ok=True)
    open(r4, "w", encoding="utf-8").write("detail backlog\n")
    r9r = step9_write(r4, good_tgt)
    passed.append(("STEP 9 refuses Research4\\BU.MD",
                   r9r.get("action") == "refused" and not r9r.get("ok")))
    passed.append(("STEP 9 left Research4\\BU.MD untouched",
                   open(r4, encoding="utf-8").read() == "detail backlog\n"))

    # STEP 9: refuse mailbox clobber
    ai_bu = os.path.join(d, "Ai", "BU.MD")
    os.makedirs(os.path.dirname(ai_bu), exist_ok=True)
    shutil.copy2(mailbox, ai_bu)
    before = open(ai_bu, "rb").read()
    r9m = step9_write(ai_bu, good_tgt)
    passed.append(("STEP 9 refuses to clobber a mailbox",
                   r9m.get("action") == "refused"))
    passed.append(("STEP 9 left the mailbox bytes in place",
                   open(ai_bu, "rb").read() == before))

    # STEP 9: write pointer onto empty / missing path
    fresh = os.path.join(d, "Ai_fresh", "BU.MD")
    r9w = step9_write(fresh, good_tgt)
    passed.append(("STEP 9 writes POINTER line only on a free path",
                   r9w.get("action") == "wrote" and r9w.get("ok")))
    got = open(fresh, encoding="utf-8").read()
    passed.append(("STEP 9 emit is pointer-shaped and not a monolith",
                   is_pointer_shaped(got) and len(got.encode("utf-8")) < 500
                   and "QA mailbox" not in got))

    # STEP 9: rewrite an existing pointer
    r9b = step9_write(fresh, other)
    passed.append(("STEP 9 rewrites an existing pointer-shaped file",
                   r9b.get("action") == "wrote" and pointer_target(
                       open(fresh, encoding="utf-8").read()) == other))

    # STEP 9: refuse a monolith target (newlines)
    r9n = step9_write(os.path.join(d, "Ai_x", "BU.MD"), "a\n\n# monolith\n" * 50)
    passed.append(("STEP 9 refuses a multiline/monolith target",
                   r9n.get("action") == "refused"))

    print()
    print("-" * 78)
    for label, good in passed:
        print("  %s  %s" % ("OK  " if good else "FAIL", label))
    bad = [l for l, g in passed if not g]
    print("SELFTEST PASS - STEP 8/9 cannot smash the mailbox or Research4 BU.MD."
          if not bad else "SELFTEST FAIL - %d check(s) cannot be trusted." % len(bad))
    return 1 if bad else 0


def _print_result(r: dict) -> int:
    print("  action=%s  ok=%s" % (r.get("action"), r.get("ok")))
    for k, v in r.items():
        if k in ("action", "ok"):
            continue
        print("  %s=%s" % (k, v))
    return 0 if r.get("ok") else 1


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()

    def _arg(flag, default=None):
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                return argv[i + 1]
        return default

    if "--step8" in argv:
        src = _arg("--src", "")
        dst = _arg("--dst", "")
        if not src or not dst:
            print("STEP 8 needs --src and --dst. Refusing to guess live paths.")
            return 2
        return _print_result(step8_mirror(src, dst, _arg("--pointer-source")))
    if "--step9" in argv:
        path = _arg("--path", "")
        target = _arg("--target", "")
        if not path or not target:
            print("STEP 9 needs --path and --target. Refusing to guess live paths.")
            return 2
        return _print_result(step9_write(path, target))
    print("usage: tidyup_bu.py --selftest | --step8 --src P --dst P "
          "[--pointer-source P] | --step9 --path P --target P")
    return 2


if __name__ == "__main__":
    sys.exit(main())
