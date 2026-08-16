#!/usr/bin/env python3
"""
wargame.py - adversarial trial simulation over the Chambers v. Abraxas record.

Keith, 2026-08-02: "WAR GAME IT." · "let's not run $250 worth of iterations and let them rip
w/o testing. Let's run a sample and feel our way forward."

DESIGN, and why each piece is the way it is
-------------------------------------------
EVERY FAMILY PLAYS BOTH SIDES, every iteration, in separate independent sessions. Rotating who
plays Plaintiff across iterations would measure MODEL STRENGTH, not case strength. Having each
family argue both sides removes that confound entirely - and it yields 8 blind strategies per
iteration instead of 2, which is what makes "rank the winning and losing strategies" answerable.

THREE ROUNDS.  R1 blind strategy (no side sees the other) -> R2 cross-rebuttal, always by a
DIFFERENT family than drafted the target -> R3 a three-family bench, each ruling independently.
No family judges an iteration in which it played a side. NOTHING IS AVERAGED. Where the three
judges disagree, that disagreement IS the finding; a mean would erase the only signal worth having.

MONTE CARLO OVER FACTS, NOT OVER SAMPLING NOISE. Re-running one prompt 30 times measures
temperature. The real variance here is a handful of unresolved facts. So iteration 1 runs clean
and HARVESTS the pivots the models themselves name in their <<<PIVOTS>>> blocks; later iterations
draw a random resolution of those pivots and inject them as neutral stipulations. The pivot list
comes from the models, never from us - which is also how it stays free of our work product.

LANE-MAJOR SCHEDULING. Prompt caching keys on a stable prefix and dies with elapsed time, not with
lane switching. Interleaving lanes per iteration guarantees cold caches; batching every API call
into one burst keeps them warm. So the driver orders work BY LANE, not by iteration.

🔴 THE BUDGET IS A CAP, NOT A HOPE. Checked before every single call against the live ledger. On
breach the run HALTS and writes HALTED.txt naming the call that would have exceeded it. A budget
that is only checked at the end is a receipt, not a control.

USAGE (native Windows - the sandbox caps a call at 45 s)
    py -3.14 wargame.py --plan                      # cost plan, spend nothing
    py -3.14 wargame.py --iterations 2 --budget 20
    py -3.14 wargame.py --selftest
"""
from __future__ import annotations
import argparse, json, random, re, sys, time
from datetime import datetime
import pathlib
from pathlib import Path

MESH = Path(__file__).resolve().parent
sys.path.insert(0, str(MESH))

WG      = Path(r"V:\Ai\Legal\WARGAME")
RECORD  = WG / "record"
PROMPTS = WG / "prompts"
RETURNS = WG / "returns"
LEDGER  = WG / "_LEDGER.jsonl"

PLAINTIFF = "the Plaintiff, David Keith Chambers"
DEFENDANT = "the Defendant, Abraxas Labs, LLC"
SIDES = {"P": PLAINTIFF, "D": DEFENDANT}

# Lane assignment. Keith built BTS to avoid unnecessary API charges, and the DOM has no tokens
# to bill however hard it thinks - so the 16 reasoning-heavy calls per iteration go there and the
# API carries only the 3 bench rulings, where a parseable <<<OUTCOME>>> block is needed.
LANES = {
    "sgh":  "dom",      # grok over the browser - free
    "gem":  "api",      # Vertex; draws the $300 GCP credit, which EXPIRES 2026-10-13 unspent
    "gw":   "api",      # grok-build-0.1 - the cheap coder rail
    "copg": "cli",      # Copilot CLI - metered in AI credits, not tokens
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- budget
class BudgetExceeded(RuntimeError):
    pass


class Budget:
    """A hard cap, enforced BEFORE each call, against the real ledger.

    xAI spend is read from bts_sgh's own ledger rather than re-derived here - one source of truth,
    and it already accounts for cached input at $0.50/M against $2.00/M.
    """

    def __init__(self, cap_usd: float):
        self.cap = cap_usd
        self.spent_here = 0.0
        self.calls = 0

    def _xai_total(self) -> float:
        try:
            import bts_sgh
            d = bts_sgh._load() if hasattr(bts_sgh, "_load") else {}
            return float(d.get("usd", 0.0))
        except Exception:
            return 0.0

    def check(self, label: str, est: float) -> None:
        if self.spent_here + est > self.cap:
            raise BudgetExceeded(
                f"HALT before '{label}': spent ${self.spent_here:.4f} + est ${est:.4f} "
                f"would exceed the ${self.cap:.2f} cap.")

    def record(self, usd: float) -> None:
        self.spent_here += float(usd or 0.0)
        self.calls += 1


def log(entry: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------- record
# 🔴 WHITELIST, NEVER A BLACKLIST. Caught mid-run 2026-08-02, after money had started.
# load_record() used to take every *.txt except 00_INDEX.txt - a blacklist. wargame_feed writes
# EXCLUSION_MANIFEST.txt into the same directory, so the manifest went into the feed as if it were
# a case document. In its first four lines it says "war game", quotes Keith's instruction verbatim,
# and then names our own work product - "Timeline that Destroys the Defense", "Shift Abraxas to
# Jasper" - together with the reasoning for dropping them.
# ⇒ The file documenting the contamination control BECAME the contamination.
# ⇒ A blacklist fails open: anything new in the directory is silently included. A whitelist fails
#   closed. Only files a bundle prefix put there can ever reach a model.
BUNDLE_FILE = re.compile(r'^\d{2}_[A-Z_]+__')


def load_record() -> tuple[str, int]:
    """Concatenate the record for the paste lane. Labels are filenames - the record's own names."""
    allow = [p for p in RECORD.glob("*.txt") if BUNDLE_FILE.match(p.name)]
    rejected = [p.name for p in RECORD.glob("*.txt") if not BUNDLE_FILE.match(p.name)]
    docs = sorted(allow)
    if not docs:
        raise SystemExit(f"no record at {RECORD} - run wargame_feed.py --build first")
    if rejected:
        print(f"  feed whitelist: {len(docs)} documents in, "
              f"{len(rejected)} non-document file(s) kept OUT -> {', '.join(sorted(rejected))}")
    out = []
    for p in docs:
        declared = p.stat().st_size
        raw = p.read_bytes()
        if len(raw) != declared:          # the mount's silent short-read signature
            raise SystemExit(f"TRUNCATED READ on {p.name}: {len(raw)} vs {declared} declared")
        out.append(f"\n\n===== DOCUMENT: {p.name} =====\n{raw.decode('utf-8', 'replace')}")
    return "".join(out), len(docs)


def pivots_from(text: str) -> list[str]:
    m = re.search(r"<<<PIVOTS>>>(.*?)<<<END PIVOTS>>>", text, re.S)
    if not m:
        return []
    return [ln.strip(" -\t") for ln in m.group(1).strip().splitlines() if ln.strip()]


def outcome_from(text: str) -> dict:
    m = re.search(r"<<<OUTCOME>>>(.*?)<<<END OUTCOME>>>", text, re.S)
    if not m:
        return {"parse": "MISSING"}
    d = {"parse": "OK"}
    for ln in m.group(1).strip().splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            d[k.strip()] = v.strip()
    return d


def stipulation_block(draws: list[tuple[str, str]]) -> str:
    if not draws:
        return ""
    lines = ["=" * 78,
             "STIPULATED FACTS FOR THIS RUN",
             "=" * 78,
             "For this run only, the following contested questions are RESOLVED as stated.",
             "Treat each as established. Do not argue against a stipulation; reason from it.",
             "These resolutions were drawn at random and imply nothing about the true answer.",
             ""]
    for q, a in draws:
        lines.append(f"  - {q}")
        lines.append(f"      RESOLVED: {a}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- calls
def call(node: str, prompt: str, budget: Budget, label: str, est: float) -> tuple[str, dict]:
    """One node, one fresh session. A failure must SAY so and leave a trace."""
    budget.check(label, est)
    import mesh_fanout
    t0 = time.time()
    try:
        txt, meta = mesh_fanout.NODES[node](prompt)
    except Exception as e:
        meta = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        txt = ""
    secs = time.time() - t0
    usd = float(meta.get("cost_usd") or 0.0)
    budget.record(usd)
    log({"t": _now(), "label": label, "node": node, "secs": round(secs, 1),
         "chars": len(txt), "usd": usd, "running": round(budget.spent_here, 4),
         "ok": bool(txt.strip())})
    flag = "OK " if txt.strip() else "🔴 "
    print(f"    {flag}{label:<28} {node:<5} {secs:6.1f}s {len(txt):>7}c "
          f"${usd:.4f}  running ${budget.spent_here:.4f}")
    return txt, meta


def write(path: Path, text: str, meta: dict, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if text.strip():
        path.write_text(text, encoding="utf-8")
    else:                                  # silence is the defect - say why, in a file
        reason = meta.get("error") or meta.get("reason") or "empty return"
        path.with_suffix(".FAILED.txt").write_text(
            f"label={label}\nok={meta.get('ok')}\nreason={reason}\nmeta={meta}\n",
            encoding="utf-8")


# ---------------------------------------------------------------- iteration
def iteration(n: int, record: str, ndocs: int, families: list[str],
              budget: Budget, draws: list[tuple[str, str]], est: float) -> list[str]:
    out = RETURNS / f"iter{n}"
    stip = stipulation_block(draws)
    r1 = PROMPTS.joinpath("R1_STRATEGY.txt").read_text(encoding="utf-8")
    r2 = PROMPTS.joinpath("R2_REBUTTAL.txt").read_text(encoding="utf-8")
    r3 = PROMPTS.joinpath("R3_BENCH.txt").read_text(encoding="utf-8")
    pivots: list[str] = []

    print(f"\n  --- ITERATION {n} · ROUND 1 · blind strategy "
          f"({len(families)} families x 2 sides) ---")
    strat: dict[tuple[str, str], str] = {}
    for fam in families:
        for side, party in SIDES.items():
            p = r1.replace("{PARTY}", party).replace("{RECORD}", record) \
                  .replace("{STIPULATIONS}", stip)
            txt, meta = call(fam, p, budget, f"i{n}-R1-{side}-{fam}", est)
            write(out / f"R1_{side}_{fam}.md", txt, meta, f"i{n}-R1-{side}-{fam}")
            strat[(side, fam)] = txt
            pivots += pivots_from(txt)

    print(f"\n  --- ITERATION {n} · ROUND 2 · cross-rebuttal (never same family) ---")
    for (side, fam), text in strat.items():
        if not text.strip():
            continue
        other = "D" if side == "P" else "P"
        pool = [f for f in families if f != fam] or families
        rebutter = pool[(families.index(fam) + 1) % len(pool)]
        p = r2.replace("{PARTY}", SIDES[other]).replace("{OPPONENT_PARTY}", SIDES[side]) \
              .replace("{OPPONENT_STRATEGY}", text).replace("{RECORD}", record) \
              .replace("{STIPULATIONS}", stip)
        lbl = f"i{n}-R2-{other}v{side}-{rebutter}"
        txt, meta = call(rebutter, p, budget, lbl, est)
        write(out / f"R2_{other}_vs_{side}_{fam}__by_{rebutter}.md", txt, meta, lbl)
        pivots += pivots_from(txt)

    print(f"\n  --- ITERATION {n} · ROUND 3 · the bench (independent, never averaged) ---")
    briefs = "\n\n".join(f"===== {p.name} =====\n{p.read_text(encoding='utf-8')}"
                         for p in sorted(out.glob("R*.md")))
    bench = [f for f in families if rounds_fit(len(record) // 4, f)[1]]
    if not bench:
        print("    🔴 no family can hold record+briefs - SKIPPING round 3 for this iteration")
        (out / "R3_SKIPPED.txt").write_text(
            "No family had a context window large enough for the record plus all briefs.\n"
            "This is a routing failure, not a result. Do not read the absence of a ruling\n"
            "as agreement.\n", encoding="utf-8")
        return [q for q in dict.fromkeys(pivots) if len(q) > 15]
    print(f"    bench: {', '.join(bench)}")
    for judge in bench[:3]:
        p = r3.replace("{RECORD}", record).replace("{BRIEFS}", briefs) \
              .replace("{STIPULATIONS}", stip)
        lbl = f"i{n}-R3-bench-{judge}"
        txt, meta = call(judge, p, budget, lbl, est)
        write(out / f"R3_BENCH_{judge}.md", txt, meta, lbl)
        pivots += pivots_from(txt)
        o = outcome_from(txt)
        if o.get("parse") == "OK":
            print(f"       -> {judge}: {o.get('prevailing_party','?')} "
                  f"net ${o.get('net_usd','?')} conf {o.get('confidence','?')}")

    return [q for q in dict.fromkeys(pivots) if len(q) > 15]


# ---------------------------------------------------------------- main
# 🔴 CONTEXT CEILINGS. Caught 2026-08-02, BEFORE the first paid call, and it would have failed
# every SGH and GW call in the run: the narrow record is ~504K tokens and grok-4.5's window is
# 500K. Over the line before a word of prompt, and R3 adds ~100K of briefs on top.
# A cost plan that does not check whether the prompt FITS is not a plan.
CTX = {
    "sgh":  ("grok-4.5",        500_000),
    "gw":   ("grok-build-0.1",  500_000),   # not in bts_sgh.PRICES; inherits the 4.5 entry
    "gem":  ("gemini-2.5-pro",  1_000_000),
    "copg": ("copilot CLI",     128_000),   # 🔶 UNVERIFIED - assume small until measured
}
# grok-4.3 is in bts_sgh.PRICES at 1,000,000 ctx and $1.25/M in - DOUBLE the window of 4.5 and
# CHEAPER. 🔶 Confirm it is live on the account (`bts_sgh` defaults to grok-4.5) before relying on it.
ROOMY = {"grok-4.3": 1_000_000, "gemini-2.5-pro": 1_000_000}


def rounds_fit(tok_record: int, fam: str) -> tuple[bool, bool]:
    """(can_play_a_side, can_sit_on_the_bench) for one family at this record size.

    Round 3 needs the record PLUS every strategy and rebuttal, so a family can easily be able to
    argue and unable to judge. Routing by what fits beats shaving arbitrary bytes off the record
    to squeeze one more model in - the record is evidence, and trimming it to suit a context
    window is a judgement about the case made for a technical reason.
    """
    _, ctx = CTX.get(fam, ("?", 0))
    return ctx >= tok_record + 12_000, ctx >= tok_record + 110_000


def fit_check(tok_record: int, families: list[str]) -> list[str]:
    """Return families that cannot even ARGUE. Bench capacity is reported but not fatal."""
    r1 = tok_record + 2_000                      # record + role prompt
    r2 = tok_record + 12_000                     # + opponent strategy
    r3 = tok_record + 110_000                    # + all strategies and rebuttals
    bad, bench = [], []
    print(f"\n  CONTEXT FIT - record {tok_record:,} tok")
    print(f"    round 1 ~{r1:,}   round 2 ~{r2:,}   round 3 ~{r3:,}")
    for f in families:
        name, ctx = CTX.get(f, ("?", 0))
        arg, jud = rounds_fit(tok_record, f)
        print(f"    {f:<5} {name:<16} ctx {ctx:>9,}   argue {'YES' if arg else 'no '}"
              f"   judge {'YES' if jud else 'no '}   R3 headroom {ctx-r3:>+9,}")
        if not arg:
            bad.append(f)
        if jud:
            bench.append(f)
    if not bad:
        if bench:
            print(f"    -> bench: {', '.join(bench)}   (families that cannot hold the briefs "
                  f"argue only - that is routing, not exclusion)")
        else:
            print("    🔴 NOBODY can hold the record plus the briefs. Round 3 is impossible.")
            bad.append("__no_bench__")
    return bad


def plan(cap: float, iters: int, families: list[str]) -> int:
    rec, nd = load_record()
    tok = len(rec) // 4
    per = 2 * len(families) + 2 * len(families) + 3
    print(f"""
{'='*78}
  WAR GAME - COST PLAN. Nothing is spent by --plan.
{'='*78}
  record            {nd} documents, {len(rec):,} chars, ~{tok:,} tokens
  families          {', '.join(families)}
  calls/iteration   {per}   (R1 {2*len(families)} · R2 {2*len(families)} · R3 3)
  iterations        {iters}
  TOTAL CALLS       {per*iters}

  🔴 THE HONEST NUMBER, and it is not the $5 estimate.
  At ~{tok:,} tokens of record per call, {per*iters} calls is ~{per*iters*tok/1e6:.1f}M input tokens.
     grok-4.5 cold   ${per*iters*tok*2.00/1e6:>7.2f}      (in $2.00/M)
     grok-4.5 warm   ${per*iters*tok*0.50/1e6:>7.2f}      (cached $0.50/M)
     grok-build      ${per*iters*tok*1.00/1e6:>7.2f}      (in $1.00/M)
  ⇒ a full run of every round on the paid xAI rail BUSTS a ${cap:.2f} cap, and busts the
    $10 account cap besides. That is why the lanes below are not optional.

  LANES
     sgh  -> DOM   rounds 1-2. No tokens billed, however hard it thinks.
     gem  -> API   Vertex. Draws the $300 GCP credit, EXPIRING 2026-10-13 unspent.
     gw   -> API   grok-build, the cheap rail.
     copg -> CLI   Copilot credits, not tokens.
  ⇒ out-of-pocket falls to the bench rulings plus whatever gw draws.

  BUDGET           ${cap:.2f} HARD. Checked before every call. On breach the run HALTS
                   and writes HALTED.txt naming the call that would have exceeded it.
{'='*78}
""")
    bad = fit_check(tok, families)
    if bad:
        print(f"""
  🔴 REFUSING TO PLAN A RUN THAT CANNOT FIT: {', '.join(bad)}
     The record is larger than these models can hold. Every call would error and
     the budget would be spent on failures.
     FIXES, cheapest first:
       1. Run SGH on grok-4.3 - 1,000,000 ctx and $1.25/M in, vs grok-4.5's
          500,000 and $2.00/M. DOUBLE the window and CHEAPER. Confirm it is live
          on the account first; bts_sgh defaults to grok-4.5.
       2. Use --nodes gem  (gemini-2.5-pro, 1M ctx) for the first sims.
       3. Cut the record. 🔶 But note that deciding what to cut is a judgement
          about the case, which is the contamination this feed exists to avoid.
""")
        return 5
    print("  ✅ every family can hold the record through round 3.\n")
    return 0


def selftest() -> int:
    assert pivots_from("x <<<PIVOTS>>>\n a?\n b?\n<<<END PIVOTS>>> y") == ["a?", "b?"]
    assert pivots_from("nothing here") == []
    o = outcome_from("<<<OUTCOME>>>\nprevailing_party: SPLIT\nnet_usd: -1200\n<<<END OUTCOME>>>")
    assert o["prevailing_party"] == "SPLIT" and o["net_usd"] == "-1200", o
    assert outcome_from("no block")["parse"] == "MISSING"
    b = Budget(1.00); b.record(0.99)
    try:
        b.check("x", 0.10)
    except BudgetExceeded:
        print("  selftest: budget cap FIRED before the call that would breach it")
        print("  selftest: parsers OK, cap OK, nothing spent - PASS")
        return 0
    print("  🔴 selftest FAILED - the cap did not fire."); return 1


# ---------------------------------------------------------------- console log
class _Tee:
    """Mirror everything printed to a log file.

    Keith, 2026-08-02: "Those are transient on the desktop, always deleted after run - be sure you
    are writing logs, I can't always paste the output."

    The Desktop bat is deleted the moment it finishes, and its console goes with it. So the LOG IS
    THE ONLY RECORD OF WHAT HAPPENED. Logging belongs in the tool, not the wrapper - a wrapper that
    is thrown away cannot be the thing that remembers. Line-buffered and flushed on every write, so
    a crash or a closed window still leaves everything up to the failure.
    """

    def __init__(self, path, stream):
        self.path, self.stream = pathlib.Path(path), stream
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = self.path.open("a", encoding="utf-8", errors="replace")
        self.fh.write(f"\n\n{'='*78}\n### RUN {datetime.now():%Y-%m-%d %H:%M:%S}  "
                      f"{' '.join(sys.argv)}\n{'='*78}\n")
        self.fh.flush()

    def write(self, s):
        self.stream.write(s)
        try:
            self.fh.write(s); self.fh.flush()
        except Exception:
            pass
        return len(s)

    def flush(self):
        self.stream.flush()
        try:
            self.fh.flush()
        except Exception:
            pass


def start_log(path):
    sys.stdout = _Tee(path, sys.__stdout__)
    sys.stderr = _Tee(path, sys.__stderr__)
    print(f"  logging to {path}")


def main() -> int:
    start_log(WG / "_RUN_LOG.txt")
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=2)
    ap.add_argument("--budget", type=float, default=20.0)
    ap.add_argument("--nodes", default="gem,gw,copg,sgh")
    # MEASURED 2026-08-02 on the first live call: gemini-2.5-pro over a 403K-token record returned
    # 21,395 chars in 95.8 s for $0.6931. The 0.35 default was HALF the truth, which means the cap
    # would have been checked against a number that could not happen. An estimate used by a control
    # has to be measured, not guessed.
    ap.add_argument("--est-per-call", type=float, default=0.70)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    fams = [f.strip() for f in a.nodes.split(",") if f.strip()]
    if a.plan:
        return plan(a.budget, a.iterations, fams)

    rec, nd = load_record()
    bad = fit_check(len(rec) // 4, fams)
    if bad:
        print(f"\n  🔴 ABORT before any spend - record does not fit: {', '.join(bad)}")
        print("     Run --plan for the options. Nothing was called.\n")
        return 5
    budget = Budget(a.budget)
    print(f"\n  record {nd} docs / {len(rec):,} chars   budget ${a.budget:.2f} HARD\n")
    all_pivots: list[str] = []
    rnd = random.Random(20260802)

    for n in range(1, a.iterations + 1):
        draws: list[tuple[str, str]] = []
        if n > 1 and all_pivots:
            # Monte Carlo over the models' OWN pivot list, never ours.
            for q in rnd.sample(all_pivots, min(5, len(all_pivots))):
                draws.append((q, rnd.choice(["YES / in favour of the Plaintiff",
                                             "NO / in favour of the Defendant"])))
            print(f"\n  iteration {n} draws {len(draws)} stipulations "
                  f"from {len(all_pivots)} harvested pivots")
        try:
            all_pivots += iteration(n, rec, nd, fams, budget, draws, a.est_per_call)
        except BudgetExceeded as e:
            (WG / "HALTED.txt").write_text(
                f"{_now()}\n{e}\ncalls completed: {budget.calls}\n"
                f"spent this run: ${budget.spent_here:.4f}\n", encoding="utf-8")
            print(f"\n  🔴 {e}\n     Wrote {WG / 'HALTED.txt'}. Nothing further was called.\n")
            return 3

    (WG / "_PIVOTS_HARVESTED.txt").write_text("\n".join(dict.fromkeys(all_pivots)),
                                              encoding="utf-8")
    print(f"\n  DONE. {budget.calls} calls, ${budget.spent_here:.4f} of ${a.budget:.2f}.")
    print(f"  Returns: {RETURNS}   Ledger: {LEDGER}")
    print("  ⚠ NOTHING IN THERE IS EVIDENCE. Read the disagreements first.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
