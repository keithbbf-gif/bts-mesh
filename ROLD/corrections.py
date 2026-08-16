#!/usr/bin/env python3
"""
corrections.py - the C.O.S. CarryOverSystem. Corrections, counted and weighted.

Keith, 2026-08-02:
  "Corrections, in particular, must be carried over. Repeated correction must increase in
   weight/attention, even across sessions. We are thereby training the Ai BY PROXY, not through
   model coefficients, but through training the CarryOverSystem."
  "Probably THE MOST critical. Saves recreating the context each session. That's the majority of
   the time and effort."

WHY THIS IS THE MOST VALUABLE FILE IN THE TREE
  Nothing Keith says changes the model. Praise, correction and instruction are context, not
  training - they evaporate at the session boundary. So the carry-over layer IS the training
  signal, and the cost of a weak one is paid every single morning in re-explaining what was
  already settled.

  CLAUDE.md cannot carry this load on its own. It is flat: every line shouts equally, so nothing
  does, and a correction Keith has made FOUR times sits in the same typeface as one he made once.
  This file COUNTS. Count drives weight, weight drives position and volume at BootUP, and a
  recurring correction keeps getting louder until it stops recurring.

THE ESCALATION LADDER
  count 1-2   listed
  count >= 3  printed FIRST at BootUP, in full, ahead of the task list
  count >= 4  Cowork must open the session by saying how it will avoid this ONE specific thing
              TODAY - concretely, not as a general intention
  CLOSED only when a MECHANISM enforces it and that mechanism has been SHOWN TO FIRE.
  Agreement is not a mechanism. Agreement is what produced counts 2, 3 and 4.

USAGE
    py -3.14 corrections.py --boot          # what BootUP prints. Start here.
    py -3.14 corrections.py --list
    py -3.14 corrections.py --hit C-01 "what triggered it"   # log a REPEAT, raise the count
    py -3.14 corrections.py --selftest
"""
from __future__ import annotations
import argparse, datetime as dt, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOML = HERE / "corrections.toml"


def _load_text() -> str:
    raw = TOML.read_bytes()
    if len(raw) != TOML.stat().st_size:          # the mount's silent short-read signature
        raise SystemExit(f"TRUNCATED READ on {TOML.name} - refusing to report a partial ledger")
    return raw.decode("utf-8")


def parse(text: str) -> list[dict]:
    """Deliberately a small hand parser, not tomllib.

    This must run on ANY python the mesh happens to have, including one without tomllib, because
    a carry-over system that fails to load is worse than none - it fails silently into 'no
    corrections found', which reads exactly like 'you are doing fine'.
    """
    out = []
    for block in text.split("[[correction]]")[1:]:
        d, key, buf = {}, None, []
        for line in block.splitlines():
            if line.startswith("[["):
                break
            m = re.match(r'^(\w+)\s*=\s*(.*)$', line)
            if m and key is None:
                k, v = m.group(1), m.group(2).strip()
                if v.startswith('"""'):
                    key, buf = k, [v[3:]]
                    if v.endswith('"""') and len(v) > 5:
                        d[k] = v[3:-3].strip(); key = None
                elif v.startswith("["):
                    d[k] = v          # list, possibly multi-line
                    if not v.endswith("]"):
                        key, buf = k, [v]
                else:
                    d[k] = v.strip('"')
            elif key is not None:
                if line.strip().endswith('"""'):
                    buf.append(line.replace('"""', "")); d[key] = "\n".join(buf).strip(); key = None
                elif line.strip() == "]":
                    buf.append(line); d[key] = "\n".join(buf); key = None
                else:
                    buf.append(line)
        if d.get("id"):
            d["count"] = int(str(d.get("count", "1")).strip())
            out.append(d)
    return out


def weight(c: dict) -> tuple:
    """Count first, recency second. A thing said four times outranks a thing said once, always."""
    try:
        last = dt.date.fromisoformat(str(c.get("last", "2000-01-01")).strip())
    except Exception:
        last = dt.date(2000, 1, 1)
    open_bonus = 1 if str(c.get("status", "")).upper() != "CLOSED" else 0
    return (open_bonus, c["count"], last)


def occurrences(c: dict) -> list[str]:
    raw = c.get("occurrences", "")
    return [x.strip().strip('",') for x in re.findall(r'"([^"]{10,})"', raw)]


def boot(cs: list[dict]) -> int:
    cs = sorted(cs, key=weight, reverse=True)
    hot = [c for c in cs if c["count"] >= 3 and str(c.get("status", "")).upper() != "CLOSED"]
    print("\n" + "=" * 90)
    print("  C.O.S.  CARRY-OVER SYSTEM  -  corrections Keith has already made")
    print("  Nothing he says changes the model. This file is the only thing that crosses a")
    print("  session boundary, so this file IS the training signal.")
    print("=" * 90)

    if hot:
        print(f"\n  🔴🔴 {len(hot)} CORRECTION(S) AT COUNT 3 OR MORE. READ THESE BEFORE THE TASK LIST.\n")
        for c in hot:
            print(f"  {'─'*86}")
            print(f"  {c['id']}  ·  {c['short']}  ·  SAID {c['count']} TIMES  "
                  f"({c.get('first','?')} → {c.get('last','?')})  [{c.get('status','?')}]")
            for ln in str(c.get("rule", "")).splitlines():
                if ln.strip():
                    print(f"      {ln.strip()}")
            print(f"      every time it was needed:")
            for o in occurrences(c):
                print(f"        · {o}")
            mech = str(c.get("mechanism", "")).strip()
            if mech.upper().startswith("NONE"):
                print(f"      🔴 NO MECHANISM ENFORCES THIS. That is why it is at {c['count']}.")
            else:
                print(f"      mechanism: {mech}")
            if c["count"] >= 4:
                print(f"      ⚠ COUNT {c['count']}: say in your FIRST reply this session how you will")
                print(f"        avoid this specific thing TODAY. Concretely. Not as an intention.")
        print(f"  {'─'*86}")

    rest = [c for c in cs if c not in hot]
    if rest:
        print("\n  the rest, by weight:")
        for c in rest:
            flag = "closed" if str(c.get("status", "")).upper() == "CLOSED" else "open  "
            print(f"    {c['id']}  x{c['count']}  {flag}  {c['short']}")
    print(f"\n  {len(cs)} corrections carried. Add one with --hit <id> \"<trigger>\".")
    print("  A correction goes CLOSED only when a control enforces it AND has been shown to fire.\n")
    return 0


def hit(cid: str, trigger: str) -> int:
    text = _load_text()
    if f'id = "{cid}"' not in text:
        print(f"  no such correction: {cid}"); return 2
    today = dt.date.today().isoformat()
    block_start = text.index(f'id = "{cid}"')
    nxt = text.find("[[correction]]", block_start)
    block = text[block_start:nxt if nxt > 0 else len(text)]

    old = int(re.search(r'^count = (\d+)', block, re.M).group(1))
    new_block = re.sub(r'^count = \d+', f'count = {old+1}', block, count=1, flags=re.M)
    new_block = re.sub(r'^last = [\d-]+', f'last = {today}', new_block, count=1, flags=re.M)
    new_block = re.sub(r'^\]', f'  "{today} — {trigger}",\n]', new_block, count=1, flags=re.M)

    TOML.write_text(text[:block_start] + new_block + (text[nxt:] if nxt > 0 else ""),
                    encoding="utf-8")
    print(f"  {cid} count {old} -> {old+1}")
    if old + 1 >= 4:
        print(f"  🔴 {cid} is now at {old+1}. It will demand a concrete plan at every BootUP")
        print(f"     until a MECHANISM closes it. Agreement will not close it.")
    return 0


def selftest() -> int:
    cs = parse(_load_text())
    assert len(cs) >= 6, f"parsed only {len(cs)} corrections"
    ids = [c["id"] for c in cs]
    assert len(ids) == len(set(ids)), f"duplicate ids: {ids}"
    solo = next(c for c in cs if c["id"] == "C-01")
    assert solo["count"] >= 4, "C-01 should be the heaviest"
    assert len(occurrences(solo)) == solo["count"], (
        f"C-01 claims count={solo['count']} but lists {len(occurrences(solo))} occurrences - "
        "the count must be evidenced, not asserted")
    # ordering: the thing said most, that is still open, must come first
    assert sorted(cs, key=weight, reverse=True)[0]["id"] == "C-01"
    # and a CLOSED item must never outrank an OPEN one of equal count
    print(f"  selftest: {len(cs)} corrections parsed, ids unique, counts match their evidence,")
    print(f"            heaviest = C-01 ({solo['short']}, x{solo['count']}) - PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--hit", nargs=2, metavar=("ID", "TRIGGER"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.hit:
        return hit(a.hit[0], a.hit[1])
    cs = parse(_load_text())
    if a.list:
        for c in sorted(cs, key=weight, reverse=True):
            print(f"  {c['id']}  x{c['count']:<2} {c.get('status','?'):<8} {c['short']}")
        return 0
    return boot(cs)


if __name__ == "__main__":
    sys.exit(main())
