# WAR GAME — THE RUN MATRIX FOR NEXT SESSION

*Written 2026-08-03 ~04:50 CDT at Keith's instruction: "more wargames with the Stripped corpus…
same setup, but alternating more models (Fable). And then more runs with the additional exhibits."*

**Mesh document. `.md` is correct here — this is Cowork's procedure, not a Keith deliverable.
🔴 NEVER convert this to `.docx` and never hand it to Keith.**

---

## 0. WHAT IS ALREADY SPENT AND WHAT IT BOUGHT

**Ledger: 11 calls, $8.06.** Vertex credit ~$3.46 · xAI cash ~$4.60 · Copilot 0 (all failures free).

| cell | node | result |
|---|---|---|
| R1 Plaintiff | gem | 21,001 B |
| R1 Defence | gem | **OVERWRITTEN 03:44 — round 1's version is gone. Not recoverable.** |
| R1 Defence (swap) | gem | 22,623 B · net **$0–10,000 to DEFENDANT**, 80% conf · *prior material breach* |
| R1 Plaintiff (swap) | sgh | 12,563 B · **$25,000–38,000**, 70% conf · quantum meruit first |
| Bench | sgh | SPLIT · net **$29,643** to Plaintiff · HIGH · "not close" |
| Bench | g43 | **PLAINTIFF $8,180.24** · counterclaims all disallowed · HIGH · "not close" |
| Bench | gw | FAILED — 256K ceiling, record is ~363K real tokens |
| Bench | copg | FAILED ×2 (argv, then cp1252 decode) — **both plumbing, both now fixed and untested live** |

**What it proved:** the case does not depend on who argues it. Both families, arguing for Chambers
independently, ranked **quantum meruit first and breach of contract last**, and landed within
$4,000 of each other.

**What it cost us to learn:** the defence brief got materially better on a second pass over the
identical record. Assume Dennis gets the same benefit.

---

## 1. 🔴 FABLE — READ THIS BEFORE PLANNING AROUND IT

**There is no Claude rail.** `bts_claude.py` is a **wallet estimator** — it projects burn rate from
Keith's pasted figures. It does not call the API and has no model table. A redacted scan of
`.secrets` shows **no Anthropic key**.

⇒ **Fable and Opus are reachable ONLY as Cowork subagents**, in-session, via the `Agent` tool with
`model: "fable"` / `"opus"`. Not from a `.bat`, not from `mesh_fanout`, not unattended.

**And that changes the economics, so state it plainly:**
- Every other rail spends **prepaid or expiring** money. Vertex credit **expires 2026-10-13 unspent**
  *(corrected 2026-08-11 from the unsourced 2026-10-10; the measured date comes from the console
  banner reading 74 days remaining on 2026-07-31. `rails.toml [[clock]]` is the source — do not
  re-copy the date into prose.)*
- A Claude subagent spends **Keith's own allotment — the only budget that actually runs out.**
- ⇒ **Fable/Opus cells are the EXPENSIVE ones here, not the free ones.** Run them last, run them
  deliberately, and only for the comparison they were asked for.

**The isolation rule, which is not optional.** A Claude cell must be a **fresh subagent with no
access to the session transcript** — given the record and the briefs and nothing else. Cowork wrote
every piece of work product in this case; Cowork grading briefs about it is a mirror, not a family.
The briefs themselves are clean (written from the neutral record, which excludes all Cowork output),
so an isolated instance is legitimate. **This session's context is the contamination, not Claude.**

---

## 2. THE MATRIX — STRIPPED CORPUS (51 documents, ~1.62 MB)

Roles: **P** plaintiff · **D** defendant · **J** bench. A family may not judge a brief its family
wrote — the guard enforces this by FAMILY (xai = sgh/gw/g43 · google = gem · openai = copg).

### Tier 1 — cells never run, cheap, on prepaid or expiring money

| # | cell | node | rail | est |
|---|---|---|---|---|
| 1 | **Plaintiff** | **g43** | xAI cash | ~$0.95 |
| 2 | **Defence** | **g43** | xAI cash | ~$0.95 |
| 3 | **Bench** on g43-P vs gem-D | **copg** | prepaid | $0 |
| 4 | **Bench** on gem-P vs g43-D | **copg** | prepaid | $0 |

**g43 has only ever judged. It has never argued.** That is the largest untouched cell and it is on
the cheaper xAI model. Do these first.

### Tier 2 — finish what failed

| # | cell | node | note |
|---|---|---|---|
| 5 | **Bench** sgh-P vs gem-D | **copg** | ⚠ **Failed twice, both times OUR bug.** argv could not launch an npm `.cmd` shim; then `text=True` died on cp1252 decoding byte `0x8f` at position 168 after Copilot had worked 89 s. **Both fixed, NEITHER VERIFIED LIVE.** This run is also the test of the fix. |
| 6 | **Bench** | **gw** `--fit` | 256K ceiling. `--fit` caps every document uniformly — measured: cap 55,535 chars, 8 of 51 truncated, **40% withheld**, and the cut lands on the maintenance manual, their production, the invoices and the texts. **A second pair of eyes, not a second count.** Say so in any writeup. |

### Tier 3 — the Claude cells Keith asked for. Subagents. Keith's allotment.

| # | cell | model | why |
|---|---|---|---|
| 7 | **Bench** on sgh-P vs gem-D | **fable** | the head-to-head he asked for |
| 8 | **Bench** on sgh-P vs gem-D | **opus** | same input, same pairing — the ONLY way the comparison means anything |
| 9 | **Plaintiff** | **fable** | a third family arguing his case |

### 🔴 BYTE-IDENTICAL INPUT — NOW A MECHANISM, NOT A RULE IN PROSE

Keith, 2026-08-03: *"correct"* — **or the comparison measures the pairing instead of the model.**

Since Fable and Opus are subagents rather than rails, the caller cannot guarantee identical input
the way it can for gem/sgh/g43. Two hand-assembled prompts would differ, and nobody would know which
difference produced the difference in the answer. **So emit the prompt once and feed both from it:**

```
py -3.14 fire_one_rail.py --side J --pbrief sgh --dbrief gem --node gem --emit
```

- **Calls nothing. Spends nothing.** Writes `PROMPT_BENCH_sgh_v_gem.txt` and prints its **sha256**.
- **The hash is the proof**, checkable after the fact rather than asserted before it.
- `--node` only picks the context ceiling on an emit; **recusal is skipped**, because emitting is not
  judging. It prints the author families instead — *"WHOEVER READS THIS FILE MUST NOT BE FROM:
  google, xai"* — so the constraint travels **with the artefact** across the handoff to a subagent
  the tool cannot see.
- **Verified:** two emits produced identical sha256 and the first file was not overwritten
  (`_r2`); a real `--node gem` bench call is still refused with exit 7.

**If two answers came from two different hashes, the comparison is void. Record the hash beside
every Claude result.**

---

## 3. THE MATRIX — EXPANDED CORPUS (+ bundle 09_JASPER_UCC)

**Build first, free:** `py -3.14 wargame_feed.py --expanded`

Adds: **J-09 UCC-1 2020-06-12 Cashmere Valley Bank — equipment schedule** · J-10 UCC-1 2020-05-01
Medicinal Genomics AriaMx PCR · **J-11 UCC-3 2025-01-07 Cashmere TERMINATION** · J-12 FD-24-2382
mediation · Yerokhin divorce decree · Cashmere TWF 2025.

**✅ ALREADY GUARDED:** `Shift Abraxas to Jasper narrative` and `…timeline` are excluded **by name**
in `EXTRA_EXCLUDE` (added 2026-08-03). They are Keith's own argument living **inside** an evidence
bundle, so the bundle-level work-product filter would have passed them straight through. **The
expanded run is exactly where contamination gets in — check by name, every time, and read
`EXCLUSION_MANIFEST.txt` before spending anything.**

| # | cell | node | est |
|---|---|---|---|
| 10 | Plaintiff, expanded | gem | ~$0.75 |
| 11 | Defence, expanded | sgh | ~$1.60 |
| 12 | Bench, expanded | g43 | ~$0.95 |

### 🔴 THE ONLY QUESTION THAT MATTERS IN THE EXPANDED RUN

**Does anyone reach the transfer theory from the filings alone, without being told it?**

- Does any brief cite **J-09** unprompted?
- Does anyone notice the equipment schedule is dated **ten days after delivery**, against a lease
  whose **¶V keeps title with the lessor until final payment**?
- Does anyone connect the **UCC-3 termination of January 2025** to the timing of the refiling?
- **Does the DEFENCE brief see the exposure before we do?** That is the single most useful answer
  available from the whole exercise.

**If three families independently find it, it is real. If none do, the documents do not carry it
yet — and that is worth far more before a pleading than after one.**

---

## 4. RUNNING ORDER, AND WHY

1. **`wargame_feed.py --expanded`** — free, and read the manifest.
2. **Tier 1** (#1–4) — cheapest, largest untouched cell, and #3/#4 are free.
3. **Tier 2 #5** — proves the two Copilot fixes live.
4. **Expanded #10–12** — the transfer question.
5. **Tier 3 #7–9 LAST** — the only cells that spend the budget that runs out.

**Total, all tiers: ~$5.20 of API money plus whatever the Claude cells cost.**

⚠ **Do not change the tools mid-matrix.** The prompt-order fix for prefix caching (record first,
role last — currently the shared prefix between two calls is under 1%) is worth doing, but it
**invalidates every comparison across the boundary.** Do it before the matrix or after it, never
inside it.

---

## 5. WHAT IS NOW GUARDED, AND WHAT EACH GUARD COST TO LEARN

| guard | the failure that produced it |
|---|---|
| **Whitelist** `^\d{2}_[A-Z_]+__` on the record | `EXCLUSION_MANIFEST.txt` entered the feed — the file documenting the contamination control **became** the contamination |
| **`EXTRA_EXCLUDE` by NAME** | plaintiff narrative hiding inside an evidence bundle, invisible to a bundle-level filter |
| **Exactly one brief per side, pairing named** | the bench glob returned **two plaintiff briefs and one defence brief** and would have ruled on it, looking entirely normal |
| **Recusal by FAMILY, not model name** | `g43` could have judged an `sgh` brief. Same house, same priors |
| **`brief_node()` parses re-run suffixes** | `R1_D_gem_r2.md` rsplit to `"r2"`, which is in no family, so **GEM was cleared to judge GEM** |
| **No return overwrites another** (`_r2`, `_r3`) | round 1's defence brief was **destroyed at 03:44** by the run that was measuring against it |
| **Exceptions write `.FAILED.txt` + ledger** | a raised failure left **no trace at all**, while an HTTP failure left a file |
| **Prompt at a fixed path, kept, sha256 printed** | the PID-named prompt was unlinked in `finally`, so the input to an 89-second run died with it |
| **`shutil.which` + `cmd /c` for `.cmd` shims** | WinError 2 is **identical** for "not installed" and "installed but unlaunchable." `where` answers only the first |
| **Bytes + explicit utf-8 decode** | `text=True` → cp1252 → `UnicodeDecodeError` at position 168, and 89 s of prepaid work vanished |

**Eight of these ten were found by looking at something else.** None was found by a test written in
advance. ⇒ **Read the directory listing and the ledger before every run.** The failures that cost
most were the ones that looked normal.

---

## 6. OPEN, AND NOT WAR-GAME WORK

- 🔴 **§ 3236(A):** sixty RFAs drafted against a **thirty** cap. Farley's call — cut, or confer and
  move. **Nothing serves until this is decided.**
- 🔶 **Confirm the 6 July expert deadline** against the original scheduling order.
- **PJLA (Michigan) and Cashmere (Washington) UIDDA** must start early — 1–2 weeks each, and PJLA is
  wanted before the 26 August deposition.
- **John's packet:** 43 `.docx` exist in `V:\Ai\Legal\DOCX\`. **He should get about ten.** Not built.
- **Post-Monday:** Fettkether / cheque 5619772 search (`--from "918legal|fettkether"`).
