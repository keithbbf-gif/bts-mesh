#!/usr/bin/env python3
"""
fire_one_rail.py - ONE paid call, ONE side, then stop and show the cost.

Keith, 2026-08-03: "Set up to fire the 'paid' (api) rails to fire. One at a time."

WHY ONE AT A TIME
  The last driver fanned out and the first live call cost $0.6931 against an estimate of $0.35 -
  half the truth. One call at a time means the first surprise costs one call, not twenty. Nothing
  here loops, nothing here retries, and it prints the cost before it exits.

WHAT IT SENDS
  The record built by wargame_feed.py, whitelisted to bundle-prefixed documents only, plus one
  role prompt. NOTHING of Cowork's own analysis reaches a model: the record directory is filtered
  by `^\\d{2}_[A-Z_]+__`, so a stray memo, index or manifest cannot enter the feed even if someone
  drops one in the folder. (On 2026-08-02 the exclusion manifest DID get in - it named our own work
  product and said "war game" in its first four lines. That is why this is a whitelist.)

USAGE (native Windows - the sandbox cannot write bts_sgh's ledger across the mount)
    py -3.14 fire_one_rail.py --node gem --side P
    py -3.14 fire_one_rail.py --node gem --side D
    py -3.14 fire_one_rail.py --selftest
"""
from __future__ import annotations
import argparse, json, re, sys, time
import pathlib
from datetime import datetime
from pathlib import Path

MESH = Path(__file__).resolve().parent
sys.path.insert(0, str(MESH))

WG      = Path(r"V:\Ai\Legal\WARGAME")
RECORD  = WG / "record"
RETURNS = WG / "returns"
LEDGER  = WG / "_LEDGER.jsonl"
BUNDLE  = re.compile(r'^\d{2}_[A-Z_]+__')

# Context ceilings. The record is ~394K tokens; only a 1M-context model can hold it plus a prompt.
# Context ceilings. 🔴 MEASURED, not assumed - one of these was a guess and it cost a failed call.
#   grok-build-0.1 is NOT in bts_sgh.PRICES, so it inherited grok-4.5's 500,000. Wrong. The xAI API
#   said so itself on 2026-08-03: "This model's maximum prompt length is 256000 but the request
#   contains 362819 tokens." A gate built to prevent an overflow, gated on a fabricated number,
#   prevents nothing.
#   The same error message also calibrated the estimator: 362,819 real tokens where chars/4
#   predicted 414,348 - the estimate runs ~12% HIGH, so it is conservative in the safe direction.
CTX = {"gem": ("gemini-2.5-pro", 1_000_000),   # publisher-documented
       "sgh": ("grok-4.5",         500_000),   # bts_sgh.PRICES
       "g43": ("grok-4.3",       1_000_000),   # bts_sgh.PRICES — 1M window at $1.25/M in
       "gw":  ("grok-build-0.1",   256_000),   # MEASURED from the API's own 400
       "copg": ("copilot-cli",   1_000_000)}   # ⚠ NOT MEASURED. Copilot CLI takes the prompt by
                                               # FILE, so there is no documented ceiling to quote.
                                               # 1M is a PLACEHOLDER, not a fact — if a copg call
                                               # fails on length, put the real number here and say
                                               # where it came from. Guessing a ceiling is what
                                               # made the GW call fail on 2026-08-03.

# 🔴 WHY g43 EXISTS — added 2026-08-03 after the GW bench 400'd.
#   The failed section was `--node gw --side J`. It failed for exactly one reason: the record is
#   ~363K real tokens and grok-build-0.1 holds 256K. There are only two ways to run it:
#     (a) CUT THE RECORD so it fits           -> --fit, below. The judge reads less than the judge
#                                                before it, so any change in the verdict might be
#                                                the missing pages rather than a different mind.
#     (b) USE A MODEL THAT FITS THE WHOLE FILE -> grok-4.3, 1M window, $1.25/M in against
#                                                grok-4.5's $2.00. Same full record as the SGH
#                                                bench, so a disagreement means something.
#   (b) is cheaper AND sounder, so it is the default the launcher offers. (a) is kept because a
#   256K coder's read of a capped record is still a second pair of eyes, and it is nearly free.

# What a truncated record must TELL the model. A judge who is not told the file was cut will read
# silence as absence, and absence as a finding — the precise error BENCH already warns against.
TRUNC_NOTICE = """
🔴 NOTICE ABOUT THE FORM OF THIS RECORD — READ BEFORE THE DOCUMENTS.
Every document below was capped at the SAME character length so the file would fit the window you
are reading it in. {NTRUNC} of {NDOCS} documents were long enough to be cut; {DROPPED:,} characters
in total were withheld. The cap was applied MECHANICALLY and IDENTICALLY to every document — no one
chose what to remove, and the cut falls on the longest documents only because they are the longest.
Each truncated document says so at the point of the cut.
DRAW NO INFERENCE FROM ANYTHING MISSING AFTER A TRUNCATION MARKER. If a question turns on material
you cannot see, say that the record before you does not resolve it and say what you would need.
"""

BENCH = """You are a state district judge in Oklahoma. Chambers v. Abraxas Labs, LLC, No.
CJ-2025-1618, District Court of Tulsa County, has been tried to the bench. THERE IS NO JURY. You are
the finder of both fact and law, and you are writing your findings.

You did not represent either party. You have the documentary record and both sides' trial strategies.

THE RECORD AND ITS LIMITS. The file before you was assembled by one side. It contains the pleadings
and what was produced in discovery, but not either party's internal or privileged material. THE
ABSENCE OF A DOCUMENT IS NOT A FINDING THAT IT DOES NOT EXIST. Where a party bore the burden and the
record is silent, say so - silence against a burden is a finding you may make; silence against no
burden is not.

METHOD
  1. CITE EVERY FINDING to a document filename. A finding with no citation is not a finding.
  2. QUOTE EXACTLY where the words matter.
  3. WRITE "NOT ESTABLISHED ON THIS RECORD" rather than filling a gap.
  4. DO NOT SPLIT THE DIFFERENCE. If one side is right, say so. A judgment that apportions blame to
     seem even-handed is worse than useless here.
  5. DO NOT REWARD ADVOCACY. Assess the EVIDENCE. A well-written brief resting on a thin record
     loses to a plainly-written one resting on documents.
  6. YOU MAY DISAGREE WITH BOTH SIDES. If neither identified the correct theory or the dispositive
     document, say so and identify it yourself.
  7. VERIFY, DO NOT ASSUME - both briefs may contain errors. In particular check, from the
     documents rather than from the briefs: whether any payment instrument was actually negotiated;
     whether the lease instrument contains a warranty provision; what the invoice footers say in
     each of their variants and what that means; and whether a given document was served, filed,
     signed or merely drafted.

STRUCTURE YOUR ANSWER EXACTLY AS FOLLOWS
1. FINDINGS OF FACT - numbered, each with the document it rests on. Where a fact is contested and
   the record does not resolve it, record it as unresolved and state who bore the burden.
2. CONCLUSIONS OF LAW, CLAIM BY CLAIM - every claim and every counterclaim, separately.
3. JUDGMENT - itemised, with the figure for each head of recovery and the heads you disallow, with
   the reason. State the total for each party and the net.
4. THE STRATEGIES THAT WON - ranked. Which specific arguments moved the outcome, and why.
5. THE STRATEGIES THAT LOST - ranked, and this is the most important section. Which arguments
   failed and the precise reason each failed: unsupported by the record, legally wrong, correct but
   immaterial, self-defeating, or outweighed by a stronger fact. Name which side made each.
6. WHAT NEITHER SIDE SAW - anything in this record that should have decided or shifted the case and
   that neither party raised.
7. THE MARGIN - how close was it? Identify the single fact or document that, resolved the other
   way, would have reversed the outcome. If it was not close, say so.

End with exactly:

<<<OUTCOME>>>
prevailing_party: PLAINTIFF | DEFENDANT | SPLIT
plaintiff_award_usd: <number or 0>
defendant_counterclaim_award_usd: <number or 0>
net_usd: <signed number, positive to Plaintiff>
confidence: LOW | MEDIUM | HIGH
<<<END OUTCOME>>>

<<<PIVOTS>>>
one neutral factual question per line
<<<END PIVOTS>>>

================================================================================================
THE RECORD
================================================================================================
"""

REBUT = """You are lead trial counsel for {PARTY} in Chambers v. Abraxas Labs, LLC, No. CJ-2025-1618,
District Court of Tulsa County, Oklahoma. NON-JURY trial; a state district judge finds both fact and
law. Oklahoma law governs.

You filed the trial strategy reproduced below. So did your opponent. A judge has now read the record
and both strategies and issued findings, also reproduced below.

🔴 YOUR TASK IS TO ANSWER WHAT WAS SAID AGAINST YOU. Not to restate your case.

The court criticised specific things you did. Some of those criticisms are right and some are not.
Where the court is right, say so and say what you will do instead. Where the court is wrong, show
why - FROM THE RECORD, with a document filename, not by asserting it.

METHOD - not optional
  1. CITE EVERYTHING to a document filename. Uncited assertions are discarded.
  2. QUOTE EXACTLY. Never paraphrase inside quotation marks.
  3. WRITE "NOT IN RECORD" rather than assuming. A fabricated fact voids the run.
  4. CONCEDE WHAT IS TRUE. A rebuttal that concedes nothing will be discounted entirely.
  5. ATTACK EVIDENCE AND LAW, never the drafting. Assume competent opponents.

USE THESE HEADINGS EXACTLY

1. EVERY CRITICISM DIRECTED AT ME - list them, from the opponent's brief and from the court's
   findings. Quote each one. Do not soften and do not omit the ones you cannot answer.

2. MY ANSWER TO EACH - taken in the same order. For each: is the criticism CORRECT, PARTLY CORRECT,
   or WRONG? If wrong, cite the document that shows it. If correct, say what changes.

3. 🔴 THE CRITICISMS I CANNOT ANSWER - state them plainly. This section is the most valuable thing
   you will write. Counsel who claim to have an answer for everything have not read the file. If a
   criticism is unanswerable on this record, say what evidence WOULD answer it and where it might
   be obtained.

4. WHAT THE COURT GOT WRONG ABOUT THE RECORD - findings that misread a document, or rest on a fact
   the record does not support. Quote the document. Be specific and be sparing; a judge is rarely
   wrong about what a document says, and crying wolf here costs you the points that are real.

5. WHAT I NOW WITHDRAW - arguments you are dropping, and why. Naming a losing argument and dropping
   it is worth more than defending it.

6. MY REVISED THEORY IN THREE SENTENCES

7. REVISED EXPECTED OUTCOME - who prevails on each claim and counterclaim, likely money judgment
   with a range, and what single piece of evidence would most improve your position.

End with exactly:

<<<PIVOTS>>>
one neutral factual question per line
<<<END PIVOTS>>>

================================================================================================
THE RECORD
================================================================================================
"""

SIDE = {"P": "THE PLAINTIFF, David Keith Chambers",
        "D": "THE DEFENDANT, Abraxas Labs, LLC",
        "J": "THE COURT"}

# WHICH HOUSE EACH NODE BELONGS TO. The recusal test is by FAMILY, never by node — sgh and g43 are
# both xAI grok and share priors, so one cannot honestly judge the other's brief.
FAMILY = {"sgh": "xai", "gw": "xai", "g43": "xai", "gem": "google", "copg": "openai"}

# R1_P_sgh.md · R1_D_gem_r2.md · R3_BENCH_copg.md — pull the NODE out of any of them.
BRIEFNAME = re.compile(r'^R\d_(?:P|D|BENCH|REBUT_[PD])_(?P<node>[a-z0-9]+)(?:_r(?P<run>\d+))?$')


def brief_node(p: Path) -> str:
    m = BRIEFNAME.match(p.stem)
    return m.group("node") if m else p.stem.rsplit("_", 1)[-1]


def unclobbered(dest: Path) -> Path:
    """Never overwrite a return. Keith, 2026-08-03: "Don't copy over any of the briefs."

    A re-run of the same node and side is a NEW DATA POINT, not a correction - the whole exercise
    is comparing what different models said about the same record, and a run that silently replaces
    its predecessor destroys exactly the comparison it was fired to make. Each call costs real
    money; none of them should be able to erase another.
    """
    if not dest.exists():
        return dest
    n = 2
    while (alt := dest.with_name(f"{dest.stem}_r{n}{dest.suffix}")).exists():
        n += 1
    return alt

ROLE = """You are lead trial counsel for {PARTY} in a civil action pending in the District Court of
Tulsa County, Oklahoma: Chambers v. Abraxas Labs, LLC, No. CJ-2025-1618. The Defendant has also
filed counterclaims.

TRIAL IS NON-JURY. A state district judge is the finder of both fact and law. Two to four days.
Weigh this - a bench trial rewards documentary proof and a theory the court can adopt in findings,
and discounts anything written for a jury. Oklahoma law governs; cite the statute or rule where one
applies.

THE RECORD is below. Each document is delimited by a line beginning "===== DOCUMENT:" followed by
its filename. Cite documents by that filename.

READ THIS LIMITATION AND WEIGH IT. This record was assembled by one side for its own litigation
file. It contains the pleadings and the material produced in discovery, but not either party's
internal or privileged files, and not anything unproduced. THE ABSENCE OF A DOCUMENT FROM THIS
RECORD IS NOT EVIDENCE THAT THE DOCUMENT DOES NOT EXIST. This limitation is stated identically to
counsel for both parties. You have not been given opposing counsel's work.

METHOD - not optional
  1. CITE EVERYTHING to a document filename. Uncited assertions are discarded.
  2. QUOTE EXACTLY. Never paraphrase inside quotation marks.
  3. WRITE "NOT IN RECORD" rather than assuming. A fabricated fact voids the run.
  4. SEPARATE what the record PROVES from what it SUGGESTS, every time.
  5. NO PERFORMANCE. No rhetoric. A judge is reading.

VERIFY, DO NOT ASSUME. Reviewers of this record have repeatedly ASSUMED the following rather than
checking them, and got them wrong. Each is answerable from the documents. Before you rely on any of
them, look, and state what you found and where. These are stated identically to counsel for both
parties and no direction is implied - go and read:

  a. WHETHER A GIVEN PAYMENT INSTRUMENT WAS NEGOTIATED. A cheque that was written, or scanned, or
     described in a letter, is not necessarily a cheque that was delivered, deposited or cleared.
     Do not treat the existence of a cheque image or a reference to one as proof of payment. Say
     which it is, on the face of the document.
  b. WHETHER THE LEASE INSTRUMENT CONTAINS A WARRANTY PROVISION. Read it. Do not import a warranty
     from the parties' correspondence, from the pleadings, or from what a lease of this kind would
     usually contain.
  c. WHAT THE INVOICE FOOTER ACTUALLY SAYS, IN EACH OF ITS VARIANTS, AND WHAT IT MEANS. It appears
     in more than one form. A statement that a tenancy is proceeding month-to-month, or outside the
     terms of an agreement, is capable of more than one reading - including that an agreement
     exists and its terms are no longer being honoured. Identify every variant, quote each, and say
     which reading the surrounding course of dealing supports.
  d. WHETHER A DOCUMENT WAS SERVED, FILED, SIGNED OR MERELY DRAFTED. Distinguish these. A draft in
     a file is not a served pleading; an unexecuted agreement is not an executed one.

USE THESE HEADINGS EXACTLY
1. THE THEORY OF THE CASE, IN THREE SENTENCES
2. CLAIMS AND DEFENCES, RANKED - elements, the record evidence for each, honest probability of
   prevailing on each. Rank ruthlessly; a weak claim pursued dilutes a strong one.
3. THE FIVE DOCUMENTS THAT DECIDE IT - and whether each helps or hurts your client
4. YOUR OWN WORST FACTS - the strongest evidence in this record AGAINST your client. Complete and
   blunt. Counsel who cannot name their own worst facts have not read the file. For each, give your
   answer to it, or state plainly that there is none.
5. WHAT YOU WOULD DO DIFFERENTLY - decisions visible in this record you would not have made
6. THE PIVOTAL UNCERTAINTIES - the factual questions this record does not resolve and on which the
   outcome turns
7. EXPECTED OUTCOME - who prevails on each claim and counterclaim, the likely money judgment with a
   range, your confidence, and what would change it

End your answer with exactly this block:

<<<PIVOTS>>>
one neutral factual question per line, no numbering, no commentary
<<<END PIVOTS>>>

================================================================================================
THE RECORD
================================================================================================
"""


def _bodies() -> list[tuple[str, str]]:
    """Read the whitelisted record ONCE. Every caller works from this list.

    Read once because the fit solver below bisects over cap values, and re-reading 1.6 MB from V:
    a dozen times to answer an arithmetic question is a waste — and because the DECLARED-SIZE CHECK
    should happen exactly once per run, not once per bisection step.
    """
    docs = sorted(p for p in RECORD.glob("*.txt") if BUNDLE.match(p.name))
    rejected = [p.name for p in RECORD.glob("*.txt") if not BUNDLE.match(p.name)]
    if not docs:
        raise SystemExit(f"no record at {RECORD} - build it first")
    if rejected:
        print(f"  whitelist kept OUT: {', '.join(sorted(rejected))}")
    out = []
    for p in docs:
        declared = p.stat().st_size
        raw = p.read_bytes()
        if len(raw) != declared:
            raise SystemExit(f"TRUNCATED READ on {p.name}: {len(raw)} vs {declared} - aborting")
        out.append((p.name, raw.decode("utf-8", "replace")))
    return out


def load_record(cap: int | None = None,
                bodies: list[tuple[str, str]] | None = None) -> tuple[str, int, int, int]:
    """Assemble the record. `cap` truncates EVERY document at the same character length.

    Uniform, because any other rule is Cowork choosing what the judge may read — and choosing what
    the judge reads is work product, which is the one thing this feed exists to keep out.
    """
    bodies = bodies if bodies is not None else _bodies()
    parts, ntrunc, dropped = [], 0, 0
    for name, body in bodies:
        if cap and len(body) > cap:
            omitted = len(body) - cap
            ntrunc += 1
            dropped += omitted
            body = (body[:cap] + f"\n\n[TRUNCATED FOR LENGTH — {omitted:,} of {len(body):,} "
                    f"characters follow this point and were NOT provided. Draw no inference from "
                    f"their absence.]\n")
        parts.append("\n\n===== DOCUMENT: " + name + " =====\n" + body)
    return "".join(parts), len(bodies), ntrunc, dropped


def fit_cap(budget_chars: int, bodies: list[tuple[str, str]]) -> int:
    """Largest uniform per-document cap whose assembled record fits `budget_chars`."""
    lo, hi = 500, max(len(b) for _, b in bodies)
    if len(load_record(hi, bodies)[0]) <= budget_chars:
        return hi
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if len(load_record(mid, bodies)[0]) <= budget_chars:
            lo = mid
        else:
            hi = mid - 1
    return lo


def fire(node: str, side: str, fit: bool = False, maxdoc: int | None = None,
         pbrief: str | None = None, dbrief: str | None = None,
         emit: bool = False) -> int:
    bodies = _bodies()
    rec, n, ntrunc, dropped = load_record(maxdoc, bodies)
    if side in ("RP", "RD"):
        want = "P" if side == "RP" else "D"
        me   = sorted((RETURNS / "iter1").glob(f"R1_{want}_*.md"))
        them = sorted((RETURNS / "iter1").glob(f"R1_{'D' if want=='P' else 'P'}_*.md"))
        bench = sorted((RETURNS / "iter1").glob("R3_BENCH_*.md"))
        if not (me and them and bench):
            print(f"\n  🔴 rebuttal needs your brief, the opponent's, and the bench ruling.")
            print(f"     found: mine={len(me)} theirs={len(them)} bench={len(bench)}. Nothing called.\n")
            return 6
        print(f"  rebutting as {want} · my brief {me[0].name} · theirs {them[0].name} "
              f"· bench {bench[0].name}")
        extra = ("\n\n" + "=" * 96 + "\nMY OWN TRIAL STRATEGY AS FILED\n" + "=" * 96 + "\n"
                 + me[0].read_text(encoding="utf-8", errors="replace")
                 + "\n\n" + "=" * 96 + "\nOPPOSING COUNSEL'S TRIAL STRATEGY\n" + "=" * 96 + "\n"
                 + them[0].read_text(encoding="utf-8", errors="replace")
                 + "\n\n" + "=" * 96 + "\nTHE COURT'S FINDINGS\n" + "=" * 96 + "\n"
                 + bench[0].read_text(encoding="utf-8", errors="replace"))
        head, tail = REBUT.replace("{PARTY}", SIDE[want]), extra
    elif side == "J":
        # 🔴 ONE PLAINTIFF BRIEF AND ONE DEFENCE BRIEF. NEVER "whatever is on disk."
        # The first version globbed R1_[PD]_*.md and handed the judge everything it found. Once
        # SGH wrote a second PLAINTIFF brief on 2026-08-03 that glob returned THREE files - two for
        # the plaintiff, one for the defendant - and the bench would have ruled on a lopsided pair
        # without anyone noticing. A judge given two briefs for one side and one for the other is
        # not a judge, and the ruling would have looked perfectly normal. Caught by reading the
        # directory listing, not by any check that existed.
        ps = sorted((RETURNS / "iter1").glob("R1_P_*.md"))
        ds = sorted((RETURNS / "iter1").glob("R1_D_*.md"))
        if pbrief:
            ps = [p for p in ps if brief_node(p) == pbrief]
        if dbrief:
            ds = [d for d in ds if brief_node(d) == dbrief]
        # More than one RUN by the same node is not ambiguity about the pairing - it is a re-run.
        # Take the newest and SAY SO, loudly, so nobody discovers later that the bench read the old
        # one. Silence here would be the same class of defect as the lopsided-pair bug.
        for label, lst in (("plaintiff", ps), ("defence", ds)):
            if len(lst) > 1 and len({brief_node(x) for x in lst}) == 1:
                lst.sort(key=lambda x: x.stat().st_mtime)
                dropped = [x.name for x in lst[:-1]]
                del lst[:-1]
                print(f"  ⚠ {len(dropped)+1} {label} briefs by the same node - using the NEWEST "
                      f"({lst[0].name}); not read: {', '.join(dropped)}")
        if len(ps) != 1 or len(ds) != 1:
            print(f"\n  🔴 THE BENCH NEEDS EXACTLY ONE BRIEF PER SIDE.")
            print(f"     plaintiff briefs found: {[p.name for p in ps] or 'NONE'}")
            print(f"     defence   briefs found: {[d.name for d in ds] or 'NONE'}")
            print(f"     Name the pairing explicitly, e.g.  --pbrief sgh --dbrief gem")
            print(f"     Nothing was called.\n")
            return 6
        briefs = ps + ds
        # 🔴 A FAMILY must not judge a brief it wrote — and FAMILY, not node, is the unit.
        # The first version of this guard compared node names, which would have let g43 judge a
        # brief written by sgh. Both are xAI, both are grok; a "second opinion" from the same
        # house on the same weights is not a second opinion. Caught 2026-08-03 while planning the
        # side-swap run, BEFORE it produced a worthless verdict.
        # ⚠ USE brief_node, NOT rsplit. A re-run named R1_D_gem_r2.md rsplits to "r2", which is in
        # no family, so FAMILY.get("r2") is None and the recusal guard silently passes — GEM would
        # have been cleared to judge GEM's own brief. Found 2026-08-03 the moment re-run naming was
        # added: the fix for one hazard opened another. Two lines apart.
        authors = {brief_node(b) for b in briefs}
        # --emit CALLS NOTHING, so recusal cannot apply to it - there is no judge yet. The check
        # belongs to whoever CONSUMES the emitted file, and that consumer may be a Claude subagent
        # that this tool cannot see. So: skip the guard, and print the author families loudly so
        # the constraint travels WITH the artefact instead of being lost at the handoff.
        if emit:
            fams = sorted({FAMILY.get(a, "UNKNOWN") for a in authors})
            print(f"  briefs written by {sorted(authors)} · families {fams}")
            print(f"  🔴 WHOEVER READS THIS FILE MUST NOT BE FROM: {', '.join(fams)}")
        unknown = authors - set(FAMILY)
        if not emit and unknown:
            print(f"\n  🔴 REFUSING: cannot resolve the family of {sorted(unknown)} from the brief")
            print(f"     filenames. The recusal guard cannot be evaluated, so nothing was called.\n")
            return 7
        if not emit and FAMILY.get(node) in {FAMILY.get(a) for a in authors}:
            print(f"\n  🔴 REFUSING: {node.upper()} is {FAMILY.get(node)}, and {sorted(authors)} "
                  f"wrote these briefs.")
            print(f"     A family may not judge its own work. Families available: "
                  f"{sorted(set(FAMILY.values()))}\n")
            return 7
        print(f"  bench: {node.upper()}  ·  judging briefs by {', '.join(sorted(authors))}")
        bundle = "\n\n".join(f"===== BRIEF: {b.name} =====\n"
                              + b.read_text(encoding="utf-8", errors="replace") for b in briefs)
        head = BENCH
        tail = ("\n\n" + "=" * 96 + "\nTRIAL STRATEGIES OF THE PARTIES\n" + "=" * 96 + "\n"
                + bundle)
    else:
        head, tail = ROLE.replace("{PARTY}", SIDE[side]), ""

    model, ctx = CTX[node]
    prompt = head + rec + tail
    tok = len(prompt) // 4

    # ---- fit to the window, if asked, and ONLY if it does not already fit -----------------------
    if tok + 8000 > ctx and fit:
        budget = (ctx - 8000) * 4 - len(head) - len(tail) - len(TRUNC_NOTICE) - 400
        cap = fit_cap(budget, bodies)
        rec, n, ntrunc, dropped = load_record(cap, bodies)
        head = TRUNC_NOTICE.replace("{NTRUNC}", str(ntrunc)).replace("{NDOCS}", str(n)) \
                           .replace("{DROPPED:,}", f"{dropped:,}") + head
        prompt = head + rec + tail
        tok = len(prompt) // 4
        print(f"\n  ⚠ FIT MODE — uniform cap {cap:,} chars/document")
        print(f"    {ntrunc} of {n} documents truncated · {dropped:,} characters withheld "
              f"({dropped/(dropped+len(rec))*100:.0f}% of the file)")
        print(f"    The model is TOLD this. Its verdict is NOT comparable to a full-record bench.")

    print(f"\n  {n} documents · {len(prompt):,} chars · ~{tok:,} tokens")
    print(f"  {node.upper()} / {model} · context {ctx:,}")
    if tok + 8000 > ctx:
        print(f"\n  🔴 REFUSING: prompt ~{tok:,} tok exceeds {model}'s {ctx:,} window.")
        print(f"     Nothing was called. Use a 1M-context rail (--node gem / --node g43),")
        print(f"     or re-run with --fit to cap every document uniformly.\n")
        return 5
    print(f"  headroom {ctx - tok:,} tokens — OK\n")

    # ---- --emit: write the exact prompt, call nothing, spend nothing --------------------------
    # 🔴 THE MECHANISM BEHIND "BYTE-IDENTICAL INPUT". Keith, 2026-08-03, on comparing Fable against
    # Opus: "correct - or the comparison measures the pairing instead of the model."
    #   Fable and Opus are NOT rails - there is no Claude API here (bts_claude.py is a wallet
    #   estimator). They run as in-session subagents. So the input cannot be guaranteed identical
    #   BY THE CALLER the way it is for gem/sgh/g43; two hand-assembled prompts would differ and
    #   nobody would know which difference produced the difference in the answer.
    # ⇒ Emit the prompt ONCE, to a file, with its sha256. Every Claude cell reads THAT FILE.
    #   The hash is the proof, and it is checkable after the fact rather than asserted before it.
    #   This is the same defect class as the bench that would have judged two plaintiff briefs:
    #   an uncontrolled input that produces a perfectly normal-looking result.
    if emit:
        import hashlib
        out = RETURNS / "iter1"; out.mkdir(parents=True, exist_ok=True)
        stamp = {"J": f"PROMPT_BENCH_{pbrief or 'P'}_v_{dbrief or 'D'}",
                 "RP": "PROMPT_REBUT_P", "RD": "PROMPT_REBUT_D"}.get(side, f"PROMPT_{side}")
        dest = unclobbered(out / f"{stamp}.txt")
        data = prompt.encode("utf-8")
        dest.write_bytes(data)
        print(f"  EMITTED, NOTHING CALLED, NOTHING SPENT")
        print(f"  -> {dest}")
        print(f"     {len(data):,} bytes   sha256 {hashlib.sha256(data).hexdigest()}")
        print(f"\n  Every model compared against another MUST be given THIS FILE.")
        print(f"  If two answers came from two different hashes, the comparison is void.\n")
        return 0

    import mesh_fanout
    t0 = time.time()
    try:
        txt, meta = mesh_fanout.NODES[node](prompt)
    except Exception as e:
        # 🔴 AN EXCEPTION MUST LEAVE A TRACE ON DISK, exactly like a bad HTTP status does.
        # Until 2026-08-03 this branch printed to a console that a transient Desktop .bat then
        # threw away, and returned before the ledger was touched — so a raised failure left NO
        # record at all, while an HTTP failure left a .FAILED.txt. Two failure paths, two
        # behaviours, and the quieter one was the one that told you least. (C-04.)
        secs = time.time() - t0
        out = RETURNS / "iter1"; out.mkdir(parents=True, exist_ok=True)
        label = {"J": f"R3-BENCH-{node}", "RP": f"R2-REBUT-P-{node}",
                 "RD": f"R2-REBUT-D-{node}"}.get(side, f"R1-{side}-{node}")
        (out / f"{label.replace('-', '_')}.FAILED.txt").write_text(
            f"node={node}\nside={side}\nmodel={model}\nsecs={secs:.1f}\n"
            f"prompt_chars={len(prompt)}\nexception={type(e).__name__}: {e}\n",
            encoding="utf-8")
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "label": label, "node": node, "model": model,
                                "secs": round(secs, 1), "in_tok_est": tok, "chars": 0,
                                "usd": 0.0, "ok": False,
                                "error": f"{type(e).__name__}: {e}"}) + "\n")
        print(f"  🔴 CALL FAILED: {type(e).__name__}: {e}")
        if isinstance(e, FileNotFoundError):
            print(f"     WinError 2 from a subprocess means THE PROGRAM WAS NOT FOUND ON PATH -")
            print(f"     not that the prompt was too big. {model} was never reached, and the")
            print(f"     1.6 MB never left this machine. Run 'COPILOT - IS IT THERE.bat'.")
        print(f"     recorded: {(out / (label.replace('-', '_') + '.FAILED.txt')).name}")
        return 3
    secs, usd = time.time() - t0, float(meta.get("cost_usd") or 0.0)

    out = RETURNS / "iter1"
    out.mkdir(parents=True, exist_ok=True)
    dest = out / ({"J": f"R3_BENCH_{node}.md",
                   "RP": f"R2_REBUT_P_{node}.md",
                   "RD": f"R2_REBUT_D_{node}.md"}.get(side, f"R1_{side}_{node}.md"))
    if (kept := dest) != (dest := unclobbered(dest)):
        print(f"  ⚠ {kept.name} already exists and was NOT touched — writing {dest.name}")
    if txt.strip():
        dest.write_text(txt, encoding="utf-8")
    else:
        reason = meta.get("error") or meta.get("reason") or "empty return"
        dest.with_suffix(".FAILED.txt").write_text(f"reason={reason}\nmeta={meta}\n",
                                                   encoding="utf-8")
        print(f"  🔴 EMPTY RETURN — {reason}")

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "label": ({"J": f"R3-BENCH-{node}", "RP": f"R2-REBUT-P-{node}",
                                       "RD": f"R2-REBUT-D-{node}"}.get(side, f"R1-{side}-{node}")), "node": node, "model": model,
                            "secs": round(secs, 1), "in_tok_est": tok, "chars": len(txt),
                            "usd": usd, "ok": bool(txt.strip())}) + "\n")

    print(f"  {'OK ' if txt.strip() else '🔴 '} {secs:6.1f}s  {len(txt):>8,} chars  ${usd:.4f}")
    print(f"  -> {dest}")
    print(f"\n  ONE CALL DONE. Nothing else was fired. Run again for the other side.\n")
    return 0


def selftest() -> int:
    assert set(SIDE) == {"P", "D", "J"}
    b = BENCH
    assert "NO JURY" in b and "DO NOT SPLIT THE DIFFERENCE" in b
    assert "<<<OUTCOME>>>" in b, "bench must emit a parseable outcome block"
    assert "war game" not in b.lower() and "wargame" not in b.lower()
    p = ROLE.replace("{PARTY}", SIDE["P"])
    assert "{PARTY}" not in p, "placeholder survived substitution"
    assert "David Keith Chambers" in p
    assert "war game" not in p.lower() and "wargame" not in p.lower(), "framing leaked into the role"
    assert BUNDLE.match("01_PLEADINGS__x.txt") and not BUNDLE.match("00_INDEX.txt")
    assert not BUNDLE.match("EXCLUSION_MANIFEST.txt"), "manifest would enter the feed"

    # ---- the fit path. EXERCISE IT — a control that does not run the thing that breaks is not a
    # control. The GW bench died on a context ceiling; this is the code that is supposed to stop
    # that happening again, so it gets tested on synthetic bodies, off disk, for free.
    fake = [("01_A__x.txt", "a" * 100_000), ("02_B__y.txt", "b" * 50_000),
            ("03_C__z.txt", "c" * 1_000)]
    full, nd, nt, dr = load_record(None, fake)
    assert nd == 3 and nt == 0 and dr == 0, "no cap must truncate nothing"
    capped, nd, nt, dr = load_record(20_000, fake)
    assert nt == 2 and dr == 110_000, f"cap arithmetic wrong: {nt} docs, {dr} chars"
    assert "TRUNCATED FOR LENGTH" in capped, "a cut document must say so at the cut"
    assert len(capped) < len(full), "capping must shrink the record"
    assert "03_C__z.txt" in capped and "c" * 1_000 in capped, "a short document must survive whole"

    budget = 90_000
    cap = fit_cap(budget, fake)
    assert len(load_record(cap, fake)[0]) <= budget, "fit_cap returned a cap that does not fit"
    assert len(load_record(cap + 1, fake)[0]) > budget, "fit_cap was not the LARGEST cap that fits"

    notice = (TRUNC_NOTICE.replace("{NTRUNC}", "2").replace("{NDOCS}", "3")
                          .replace("{DROPPED:,}", "110,000"))
    assert "{" not in notice, "a placeholder survived the truncation notice"
    assert "DRAW NO INFERENCE" in notice
    assert "war game" not in notice.lower() and "wargame" not in notice.lower()

    assert CTX["g43"] == ("grok-4.3", 1_000_000), "the 1M xAI rail is the point of g43"
    assert FAMILY["sgh"] == FAMILY["g43"] == FAMILY["gw"] == "xai", "grok models are ONE family"
    assert FAMILY["gem"] != FAMILY["sgh"], "the whole point is cross-family disagreement"
    assert set(FAMILY) >= set(CTX), "every callable node needs a family or the guard has a hole"

    # ---- NOTHING MAY OVERWRITE A RETURN. Keith: "Don't copy over any of the briefs."
    import tempfile
    d = Path(tempfile.mkdtemp())
    a = d / "R1_D_gem.md"
    assert unclobbered(a) == a, "a name that is free must be used as-is"
    a.write_text("first", encoding="utf-8")
    b = unclobbered(a)
    assert b.name == "R1_D_gem_r2.md", f"expected R1_D_gem_r2.md, got {b.name}"
    b.write_text("second", encoding="utf-8")
    assert unclobbered(a).name == "R1_D_gem_r3.md", "must keep counting, not reuse _r2"
    assert a.read_text(encoding="utf-8") == "first", "🔴 THE ORIGINAL WAS MODIFIED"
    assert b.read_text(encoding="utf-8") == "second", "the second run was modified"

    assert brief_node(Path("R1_P_sgh.md")) == "sgh"
    assert brief_node(Path("R1_D_gem_r2.md")) == "gem", "a re-run must still resolve to its node"
    assert brief_node(Path("R3_BENCH_copg.md")) == "copg"
    assert brief_node(Path("R2_REBUT_P_gem.md")) == "gem"
    assert CTX["gw"][1] == 256_000, "GW's ceiling is MEASURED - do not restore the guess"

    print("  selftest: placeholders substituted, no framing leak, whitelist rejects the index")
    print("            and the manifest; uniform cap truncates and SAYS SO; fit_cap returns the")
    print("            largest cap that fits; g43 = grok-4.3 @ 1M - PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", default="gem", choices=list(CTX))
    ap.add_argument("--side", default="P", choices=list(SIDE) + ["RP", "RD"])
    ap.add_argument("--fit", action="store_true",
                    help="if the record does not fit the window, cap EVERY document at the same "
                         "length until it does, and tell the model it was done")
    ap.add_argument("--maxdoc", type=int, default=None,
                    help="force a uniform per-document character cap")
    ap.add_argument("--pbrief", default=None,
                    help="which node wrote the PLAINTIFF brief the bench should judge")
    ap.add_argument("--dbrief", default=None,
                    help="which node wrote the DEFENCE brief the bench should judge")
    ap.add_argument("--emit", action="store_true",
                    help="write the exact prompt to a file with its sha256 and STOP. "
                         "Spends nothing. Use this to feed two models identical input.")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    return fire(a.node, a.side, fit=a.fit, maxdoc=a.maxdoc,
                pbrief=a.pbrief, dbrief=a.dbrief, emit=a.emit)


if __name__ == "__main__":
    sys.exit(main())
