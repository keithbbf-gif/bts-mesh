# ROLD — 00_INDEX. **THE ENTRY POINT. The only path anyone has to memorise.**
*Built 2026-07-30 (PLUMBING). Decomposition spec: `Ai\ROLD\00_ROLD_ARCHITECTURE.md`.
Design rationale + the research behind it: `V:\Ai\Research\ROLD_POINTER_DESIGN_2026-07-30.md`.*

> **What makes THIS file change:** a document is added to or removed from the tree. Nothing else.

## THE FOUR OPERATORS — the whole language. Nothing else is allowed.
```
POINTER:    <path>                     authoritative content lives THERE, not here
INCLUDEIF:  <host-local fact> -> <path>  conditional, on a fact a script can test
OVERRIDE:   <key> = <value>            one named key only, never a rewrite of the referent
PRECEDENCE: <ordered list>             REQUIRED wherever two pointers resolve to one thing
```
**Refused, deliberately:** templating · arbitrary conditionals · deep merge · implicit inheritance ·
any expression language. *(SGH, 2026-07-30: regretting deep merge while keeping override without a
stated conflict algebra is incoherent — hence `PRECEDENCE` is an operator, not a convention.)*

⚠ **Prefer a COPY when the referent is small AND stable.** A pointer to a three-line constant is
ceremony, not architecture. Pointers are for what changes, or what must not be stated twice.

## THE TREE — one document, one edit-trigger
| Document | Changes when… | Mutability |
|---|---|---|
| **`RULES.md`** | Keith rules something | append + supersede, never silently rewritten |
| **`RAILS.md`** | the infrastructure changes | live, overwritten |
| **`ROUTINES.md`** | a *step* changes | live, overwritten |
| **`SCARS.md`** | a failure is **measured** | 🔴 **APPEND-ONLY. NEVER EDITED.** |
| **`STREAMS\`** | a stream's method or posture changes | live, one file per stream |
| **`REGISTRIES\`** | an artefact is created | pointers only — never copies |
| **`ARCHIVE\`** | never consulted for state | read-only |

```
POINTER: Ai\ROLD\RULES.md                 THE THREE RULES · security/dissemination canon · standing rulings
POINTER: Ai\ROLD\RAILS.md                 paths · mounts · drive letters · endpoints · keys · monitors
POINTER: Ai\ROLD\ROUTINES.md              BootUP! · TidyUP! · TidyUP2 — STEPS ONLY
POINTER: Ai\ROLD\SCARS.md                 96 dated, numbered, verbatim measured failures
POINTER: Ai\ROLD\streams\legal.toml          done means COUNSEL OR THE COURT HAS IT
POINTER: Ai\ROLD\STREAM_LEGAL.md          the LEGAL long form — kept: a LAWYER may read this one
POINTER: Ai\ROLD\streams\plumbing.toml       done means IT RUNS
POINTER: Ai\ROLD\streams\physics.toml        done means A NUMBER IS RATIFIED
POINTER: Ai\ROLD\streams\chapter.toml        done means PROSE EXISTS
POINTER: Ai\ROLD\registries.toml            pointers to every index — never copies
POINTER: Ai\ROLD\archive.toml               read-only. NEVER consulted for state
POINTER: Ai\ROLD\rails.toml                 the constants, MACHINE-READ. No Markdown twin, ever
POINTER: Ai\ROLD\scars.jsonl                 96 scars as a query — see scars.py
POINTER: Ai\ROLD\00_ROLD_ARCHITECTURE.md  the decomposition spec + the session-log subsystem (§6)
POINTER: V:\Ai\BFast\BFAST.md              BFast — Bridge File Architecture System, Type I. THE OS
POINTER: V:\Ai\BFast\bfast.py               its entry point + config authority (V:\Ai\BFast\roots.json)
POINTER: Ai\00_MESH_CHARTER.md            roles · nodes · surfaces · channels · tasking + verification SOP
POINTER: Ai\00_TOOLS_INDEX.md             do we already have this? ASK BEFORE WRITING ANY SCRIPT
POINTER: V:\Ai\BU.MD                      BOOT POINTER. POINTER line only. Not a mailbox. Not a monolith.
POINTER: V:\Ai\Streams\PLM_TODOS.md               the PLUMBING backlog, prioritized
POINTER: V:\Ai\Research\ROLD_POINTER_DESIGN_2026-07-30.md   why this repo is shaped this way
```

## STATE vs METHOD — the collision this tree could have created, ruled once
`BU.MD` has a plumbing row; `STREAMS\` will have a `STREAM_PLUMBING.md`. **Two homes for one stream
is a copy, and copies rot.** So:
```
PRECEDENCE: V:\Ai\BU.MD  >  Ai\ROLD\STREAMS\STREAM_*.md      (for anything that is STATE)
OVERRIDE: STREAM_*.md = METHOD AND POSTURE ONLY — how this stream works, what "done" means
OVERRIDE: BU.MD = BOOT POINTER ONLY — one POINTER: line to live state. Not the state itself.
```
An open item lives in **exactly one** of them. The plumbing backlog is `V:\Ai\Streams\PLM_TODOS.md`; it is
pointed at, never duplicated.

## THE CHECK THAT MAKES THIS REAL
```
POINTER: Ai\ROLD\verify_pointers.py        the resolver — walks every POINTER/INCLUDEIF line, exits non-zero; V:\Ai\BU.MD GREEN requires pointer shape
POINTER: Ai\ROLD\tidyup_bu.py              TidyUP STEP 8/9 writer — pointer-shaped copy only; POINTER line only; never Research4\BU.MD
POINTER: Ai\ROLD\scars.py                  the scar record as a QUERY (--rebuild refuses on cited!=listed)
```
> **The Desktop wrapper is NOT pointed at, deliberately.** See the rule below — a `.bat` on the
> Desktop is a disposable artifact with a lifetime of one use. Cowork stages one fresh when it is
> needed. **The `.py` in the tree is the tool; the `.bat` is the delivery.**

## 🔴 THE DESKTOP IS NOT PART OF THIS REPOSITORY — Keith, 2026-07-30
```
OVERRIDE: desktop_bats = ONE AND DONE. Keith deletes every .bat after use.
OVERRIDE: desktop_permanent = KDash.vbs · Judge-UPS.vbs — those two, nothing else
OVERRIDE: desktop_pointers = FORBIDDEN. No control document may POINTER at a Desktop file.
```
*"I delete all .bat from DT and everything else not explicitly permitted… Nothing else can be
considered stable, it's a one and done."*
⇒ **A missing Desktop `.bat` is HOUSEKEEPING, NOT ROT — never report it as a defect.**
⇒ **`verify_pointers.py` REFUSES to resolve `Desktop\…` on purpose.** Checking them would paint the
repo permanently RED for files that are *supposed* to be gone — a check that cries wolf gets muted,
and a muted check is worse than none. **Do not "fix" that skip.**
⇒ Point instead at the durable source: `Ai\ROLD\verify_pointers.py` · `Ai\BTS_MESH\publish_r2_silent.vbs`
· `Ai\upsjudge\…`. Then a step reads *"stage and run X"*, not *"run the bat that was there last week."*
> A pointer architecture is only real if something goes **RED** when a pointer stops resolving.
> The checker fails on an unresolvable referent **and** on an unknown opcode — an unrecognised
> operator must never be silently skipped. **It has been shown to fail**, against a deliberately
> broken pointer; a verifier never shown to fail is not a verifier.

## ⚠ MIGRATION IS NOT FINISHED — READ THIS BEFORE DELETING ANYTHING
```
POINTER: Ai\00_ROLD_COMMANDS_TidyUp_BootUp.md   ⚠ THE 79 KB MONOLITH — STILL AUTHORITATIVE
POINTER: V:\Research4\BU.MD                     ⚠ 68 KB DETAIL BACKLOG — not written at TidyUP
```
**Nothing has been deleted from either.** RULES / RAILS / ROUTINES / SCARS were EXTRACTED, and the
sources are untouched on purpose: the spec requires that every heading in the monolith resolve
somewhere in this tree, **counted before and after**, before a single line is removed.

### ✅ THE HEADING COUNT — RUN 2026-07-31
```
monolith raw '#' matches      96   (70 are prose lines inside the commented THREE RULES banner)
monolith STRUCTURAL headings  26
  - ARCHIVE-class, excluded    5   ('### Prior pointer (date)' — deliberate, correctly labelled)
  - auditable                 21
  - RESOLVED                  21   ✅ ALL THREE ORPHANS CLOSED 2026-07-31
new-tree headings            212   + ~21 rails.toml section names
```
**The three orphans and how each was closed:**
1. **`## STANDING AUTHORIZATION — run the R2 publish bat`** — orphan **and a dangling pointer**:
   `ROUTINES.md` pointed at a rule in `RULES.md` that did not exist there. → now **`RULES.md` R16**.
2. **`## New path permissions / grants (2026-07-10)`** — its only unique content was the
   `BTS_NOTIFY_CONTRACT_v1.md` pointer → now **`rails.toml [[channel]] bts-notify`**. Rest is a
   dated session record ⇒ ARCHIVE-class.
3. **`## New path permissions / grants (2026-07-05)`** — pure dated session record, everything else
   already covered by ROUTINES step 4b and RAILS §2 ⇒ ARCHIVE-class.
**Plus two sub-rows that were NOT headings and would have died silently:** the CLOCKS table's
*Gemini RPD resets midnight Pacific* and *old-project soft-delete ~2026-08-14* → now
**`rails.toml [[clock]]`**. The second is **fourteen days out**.

⚠ **The monolith's last line is truncated mid-word on disk** — `…self-reported connector capability
— v`. Its content survives in full as `SCARS.md` **S-04**, so nothing is lost, but **a byte-level
diff of that file will never come out clean.** Do not treat that as a migration failure.

**✅ BUILT 2026-07-31:** `STREAMS\` (3 files) · `REGISTRIES\` · `ARCHIVE\` · `rails.toml` ·
`scars.jsonl` + `scars.py`. **Owed before deletion is licensed:**
`REGISTRIES\` stubs · the `ARCHIVE\` sweep (28 `.bak` files, 9 dated handoffs) ·
`V:\Research4\Ai\Legal\` (should not exist).

🔴 **And a finding from the extraction, which bears on the counting:** the monolith's **last line is
itself truncated mid-word** on disk — it ends `...don't trust an agent's self-reported connector
capability — v`. Confirmed host-side with both `Read` and `Grep`. That file's own header records an
earlier *"RESTORED 2026-07-06 after disk truncation"*. **Treat its tail as suspect when counting.**
