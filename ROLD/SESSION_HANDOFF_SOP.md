# SOP — SESSION STRIP, DISTIL, AND HANDOFF
**Written 2026-08-01 at Keith's direction.** *"This session can be stripped and fed to the next one
at the start of the next session. We need a formal process for that. The SOP writer in me, still at
work almost a decade later."*

**Scope:** how a working session ends so the next one starts at full speed without re-deriving
anything. Companion to **PDAiS** (`ROLD\PDAIS.md`), which governs *document* preparation. This SOP
governs *session* preparation.

---

## THE PRINCIPLE
**A session's value is not its transcript. It is the set of durable artefacts it leaves behind.**
A transcript is 200 KB of reasoning to re-read; six fixed-name files are a state you can act on.
⇒ **Never hand the next session a transcript when a distillation will do.**

## THE SEVEN ARTEFACTS — every working session produces these, or says why not
| # | artefact | filename rule | test of a good one |
|---|---|---|---|
| 1 | **Timeline** | `MASTER_TIMELINE.md` | every row carries a source; unverified rows marked 🔶 |
| 2 | **One-page summary for the decision-maker** | `ONE_PAGE_*_SUMMARY.md` | facts and dates only; no adjectives, no argument |
| 3 | **One-page strategy** | `ONE_PAGE_STRATEGY.md` | **names where we LOSE**, not only where we win |
| 4 | **Human todo** | `TODO_<NAME>.md` | contains only what genuinely needs that human |
| 5 | **Machine todo** | `TODO_MESH.md` | prioritised P0–P3, plus **standing prohibitions** |
| 6 | **Document register** | `DOCUMENT_REGISTER.md` | have / need / create, each with its source and route |
| 7 | **Corrections log** | folded into 3 and 5 | **what we believed at the start and no longer do** |

## 🔴 THE FIXED-NAME RULE
**Every artefact above has a FIXED filename. Update in place. Never date it. Never version it.**
> The dated-handoff scheme in this workspace rotted **four times** — 12c → 12d → 07-15 → 07-17 —
> each time directly beneath a warning saying it would, until a glob returned 15 files across two
> directories. **The warning was never the fix. The variable name was the defect.**
> *A filename written into prose is a COPY of a pointer, and copies rot. A fixed name at a fixed
> path is the pointer itself.*
⇒ Dated files are **archive**. If you need history, use version control, not filenames.

## THE PROCEDURE

### 🔴 STEP 0 — **SAPRS: STREAM ARTEFACT PROCUREMENT AND RECORDING STEP**
**Named by Keith, 2026-08-02. This runs CONTINUOUSLY, not at the end.**

> **The rule: the moment work product belonging to ANOTHER stream appears — a finding, a todo, a
> tool, a scar, a governance rule — it is written into that stream's file IMMEDIATELY. Before the
> conversation moves on. Before it is "remembered to do later."**

**One stream is declared per session. Four exist — `plumbing` · `physics` · `chapter` · `legal` —
and work does not respect that boundary.** A legal session surfaces a drive fault. A physics session
surfaces a tooling gap. **Whatever is not written down when it appears is carried in chat, and chat
is not a retention medium.**

**Where things go:**
| stream | file |
|---|---|
| plumbing | `V:\Ai\Streams\PLM_TODOS.md` |
| legal | `V:\Ai\Legal\TODO_MESH.md` · `TODO_KEITH.md` |
| governance rules that bind every session | `V:\Research4\CLAUDE.md` |
| procedures | `ROLD\` — `RULES.md` · `ROUTINES.md` · `PDAIS.md` · this file |
| failure classes | `ROLD\SCARS.md` **+ `scars.jsonl` in the same pass** |
| tools | `Ai\00_TOOLS_INDEX.md` **+ `BTS_MESH\TOOLS_REGISTRY.json` in the same pass** |

**Write it where it belongs, not where you are.** A plumbing finding does not go in a legal memo with
a note saying "move this later." Later does not come.

⚠ **Measured 2026-08-02, and it is why this step exists:** an entire evening of drive diagnosis —
a boot-drive safety defect in a bat, a sector-size hypothesis that may make a cleanroom unnecessary,
and two wrong conclusions worth recording as scars — lived **only in the chat transcript** through a
legal session. It reached `PLM_TODOS.md` **only because Keith said "include in that stream now."**
Had he not, it would have been stripped with the transcript and lost.

**THE SAPRS CHECK — run it before declaring a session finished, and at every `TidyUP!`:**
1. Did anything from **another stream** come up? Name each item.
2. Is each one **written into that stream's file**, not merely mentioned in this stream's notes?
3. Did a **tool** get built? → **both** the index and the registry, same pass.
4. Did a **belief get overturned** or a failure repeat? → **both** `SCARS.md` and `scars.jsonl`.
5. Did a **rule** emerge that binds future sessions regardless of stream? → `CLAUDE.md`.
6. **Is anything of value still living only in the transcript?** If yes, the session is not finished.

### STEP 1 — STRIP (mechanical)
`V:\Ai\_session_logs\strip_transcript.py`. Prose verbatim; tool arguments, tool results, thinking
blocks and `<system-reminder>` injections removed; tool calls survive as a name-only line.
**Measured: 603 files, 1,712 MB → 22.4 MB (98.69%), 0 failures.**
⚠ **Two controls, both shown to fail before being trusted:** **TRUNCATION** (bytes consumed vs
declared — the mount's silent short-read signature) and **SCHEMA** (a parsed file with no `message`
key is `SCHEMA_ERROR`, never a quiet empty file). `--selftest` plants both.

### STEP 2 — DISTIL (judgement — this is the step that cannot be automated)
From the stripped transcript extract only:
- **Facts established, each with its source.** Not conclusions — facts.
- **Facts RETRACTED**, and why. *The most valuable content in the file.*
- **Decisions made, and the reasoning**, so they are not relitigated.
- **Questions still open**, ranked.
- **Prohibitions** — what must never be done or cited again, with the reason.
⇒ **Write into the seven artefacts. Do not create an eighth document.**

### STEP 3 — VERIFY BEFORE WRITING
No claim enters an artefact on a node's or an agent's say-so. **Host-side `Read`/`Grep` are ground
truth.** Anything unverified is marked 🔶 with what would confirm it.
> Measured 2026-08-01: one agent confidently described a second HPLC that never existed. Another
> produced a Bates range off by one page. Both would have reached a filing.

### STEP 4 — RECORD THE CORRECTIONS, PROMINENTLY
**Every belief overturned goes in the artefact, at the top, with the date and who caught it.**
A handoff that records only what we now believe will re-derive the same errors. One that records
what we *stopped* believing is inoculated.
> 2026-08-01 examples: PJLA "both labs" — retracted · GenTech subpoena — reversed · amendment
> deadline — "available" → **PASSED** · the invoice footer — "our worst document" → **the theory of
> the case**.

### STEP 5 — HANDOFF POINTER
Update `V:\Ai\BU.MD` (fixed path, fixed name) to point at the artefacts. **Never create a new dated
handoff.** BU.MD is a pointer, not a copy.

### STEP 6 — NEXT SESSION
`BootUP!` → read `BU.MD` → read the seven artefacts → **read the corrections first.**
**Do not read the stripped transcript unless an artefact is silent on something you need.**

## THE STOPPING TEST
Ask before ending any session:
1. Could someone with no memory of today act correctly tomorrow from these files alone?
2. Is every claim sourced, or marked 🔶?
3. Is every belief we abandoned today written down as abandoned?
4. Does the human todo contain **only** what needs the human?
5. Is anything named with a date that should have a fixed name?

**If any answer is no, the session is not finished — however tired everyone is.**
