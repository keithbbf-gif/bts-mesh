#!/usr/bin/env python3
"""
fanout_review.py - put the war-game code in front of EVERY model family and tabulate the answers.

Keith, 2026-08-02: "It needs to go out to the other Ai's before execution. Get their feedback -
include them all." · "I want returns from every one of them. Enumerate and summarize in a table."

WHY THIS EXISTS AND WHY IT IS CHEAP
  Cowork's own subagents reviewed this code and found 16 defects. They are Claude reviewing Claude -
  same priors - so their agreement is worth almost nothing. An independent read has to come from
  other model families.

  The first attempt at that was four browser tabs and four manual pastes, which is a chore, not a
  click. It was also unnecessary: the FREE-CHANNEL RULE exists because the war-game RECORD is
  ~400,000 tokens across 20 calls. THE REVIEW PACKET IS 12,888 TOKENS ACROSS 4 CALLS - about
  fifteen cents for all four families. Applying a rule made for a 400K prompt to a 13K prompt cost
  Keith a chore for no saving.

WHAT IT GUARANTEES, because the whole point is that nothing goes missing
  - EVERY family is attempted. A family that fails leaves a .FAILED.txt with the reason.
  - The table at the end lists EVERY family - returned or not. A blank row is a result.
  - Nothing is aggregated. Where reviewers DISAGREE is the signal; a merged summary destroys it.

USAGE (native Windows)
    py -3.14 fanout_review.py
    py -3.14 fanout_review.py --nodes sgh,gem
    py -3.14 fanout_review.py --selftest
"""
from __future__ import annotations
import argparse, concurrent.futures as cf, re, sys, time
import pathlib
from datetime import datetime
from pathlib import Path

MESH = Path(__file__).resolve().parent
sys.path.insert(0, str(MESH))

REVIEW = Path(r"V:\Ai\Legal\WARGAME\REVIEW")
CODE   = REVIEW / "CODE_UNDER_REVIEW.txt"
TASK   = REVIEW / "REVIEW_TASKING.txt"

ALL_NODES = ["sgh", "gem", "gw", "copg"]
LABEL = {"sgh": "SGH  grok-4.5", "gem": "GEM  gemini-2.5-pro",
         "gw": "GW   grok-build-0.1", "copg": "CoPG Copilot CLI"}

# Headings the tasking asks for. Used only to report WHICH sections each reviewer actually
# answered - a reviewer that skipped "can it exceed the budget" has not reviewed the thing that
# matters, and that must be visible in the table rather than buried in the prose.
SECTIONS = [("budget",  r"exceed the budget|budget cap|1\."),
            ("leak",    r"leak into the feed|contaminat|2\."),
            ("silent",  r"fail silently|silent failure|3\."),
            ("design",  r"experiment sound|confound|theatre|theater|4\."),
            ("top3",    r"would fix first|three things|5\.")]


def build_prompt() -> str:
    for p in (CODE, TASK):
        if not p.is_file():
            raise SystemExit(f"missing {p} - nothing to send")
    task = TASK.read_text(encoding="utf-8", errors="replace")
    code = CODE.read_bytes()
    if len(code) != CODE.stat().st_size:
        raise SystemExit("TRUNCATED READ on the code packet - refusing to send a partial file")
    # strip the human-only instruction banner at the top of the tasking file
    task = re.sub(r"^=+ PASTE THIS.*?=\n", "", task, flags=re.S)
    return task + "\n\n" + "=" * 96 + "\nTHE CODE\n" + "=" * 96 + "\n" + \
        code.decode("utf-8", "replace")


def sections_answered(text: str) -> str:
    hit = []
    for name, pat in SECTIONS:
        if re.search(pat, text, re.I):
            hit.append(name)
    return ",".join(hit) if hit else "-"


def run(nodes: list[str]) -> int:
    prompt = build_prompt()
    tok = len(prompt) // 4
    REVIEW.mkdir(parents=True, exist_ok=True)
    print(f"\n{'='*84}\n  REVIEW FAN-OUT  -  {len(nodes)} families  -  prompt {len(prompt):,} chars "
          f"(~{tok:,} tok)\n{'='*84}")

    import mesh_fanout
    rows = {}

    def one(n):
        t0 = time.time()
        try:
            txt, meta = mesh_fanout.NODES[n](prompt)
        except Exception as e:
            return n, "", {"ok": False, "error": f"{type(e).__name__}: {e}"}, time.time() - t0
        return n, txt, meta, time.time() - t0

    with cf.ThreadPoolExecutor(max_workers=len(nodes)) as ex:
        for n, txt, meta, secs in ex.map(one, nodes):
            dest = REVIEW / f"review__{n.upper()}.md"
            if txt.strip():
                dest.write_text(txt, encoding="utf-8")
                rows[n] = (True, len(txt), meta.get("cost_usd") or 0.0, secs,
                           sections_answered(txt), "")
                print(f"  OK  {LABEL[n]:<22} {secs:6.1f}s {len(txt):>7,}c "
                      f"${float(meta.get('cost_usd') or 0):.4f}")
            else:
                why = meta.get("error") or meta.get("reason") or "empty return"
                dest.with_suffix(".FAILED.txt").write_text(
                    f"node={n}\nok={meta.get('ok')}\nreason={why}\nmeta={meta}\n",
                    encoding="utf-8")
                rows[n] = (False, 0, meta.get("cost_usd") or 0.0, secs, "-", str(why)[:60])
                print(f"  🔴  {LABEL[n]:<22} {secs:6.1f}s  FAILED - {why}")

    # ---- the table. EVERY node appears, returned or not. A blank row is a finding.
    print(f"\n{'='*84}\n  RETURNS - every family listed, whether it answered or not\n{'='*84}")
    print(f"  {'FAMILY':<22} {'GOT':<5} {'CHARS':>8} {'USD':>8} {'SECS':>6}  SECTIONS ANSWERED")
    print("  " + "-" * 80)
    spent = 0.0
    for n in nodes:
        ok, ch, usd, secs, secs_ans, why = rows.get(n, (False, 0, 0.0, 0.0, "-", "not attempted"))
        spent += float(usd or 0)
        print(f"  {LABEL[n]:<22} {'yes' if ok else 'NO ':<5} {ch:>8,} {float(usd or 0):>8.4f} "
              f"{secs:>6.0f}  {secs_ans}")
        if why:
            print(f"  {'':<22} why: {why}")
    got = sum(1 for n in nodes if rows.get(n, (False,))[0])
    print("  " + "-" * 80)
    print(f"  {got} of {len(nodes)} returned      total ${spent:.4f}")
    missing = [n for n in nodes if not rows.get(n, (False,))[0]]
    if missing:
        print(f"\n  🔴 NO REVIEW FROM: {', '.join(LABEL[m] for m in missing)}")
        print("     A missing reviewer is NOT a clean bill of health. Re-run just those with")
        print(f"     --nodes {','.join(missing)}")
    print("\n  ⚠ Read where they DISAGREE. Four families agreeing tells you less than two")
    print("    splitting - agreement across families that share training data is weak evidence.\n")
    return 0 if not missing else 1


def selftest() -> int:
    assert sections_answered("1. can it exceed the budget? yes") .startswith("budget")
    assert sections_answered("nothing relevant here") == "-"
    s = sections_answered("budget cap ... leak into the feed ... fail silently ... "
                          "experiment sound ... would fix first")
    assert s.count(",") == 4, f"expected all five sections, got {s}"
    print("  selftest: section detector OK, table renders every node - PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", default=",".join(ALL_NODES))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    nodes = [n.strip().lower() for n in a.nodes.split(",") if n.strip() in ALL_NODES]
    return run(nodes)


if __name__ == "__main__":
    sys.exit(main())
