# ROUTINES — BootUP! · TidyUP! · TidyUP2. STEPS ONLY.
> **What makes this file change:** a STEP changes. Not a rule, not a constant, not a failure.
POINTER: Ai\ROLD\RULES.md    (why — do not restate a rule here)
POINTER: Ai\ROLD\RAILS.md    (paths, mounts, endpoints — do not restate a constant here)
POINTER: Ai\ROLD\SCARS.md    (what went wrong before — do not retell a failure here)
POINTER: V:\Ai\BU.MD         (live state; TidyUP! overwrites it)

---

## HOW TO READ A STEP

A step says WHAT TO DO and IN WHAT ORDER. If a step needs a reason, a path or a past failure, it
carries an operator line instead of prose:

PRECEDENCE: POINTER (a file is authoritative) > OVERRIDE (a value set here) > INCLUDEIF (a conditional step) > the step text itself

- `POINTER: <path>` — the authority lives there. Read it; do not copy it here.
- `INCLUDEIF: <host-local fact> -> <path>` — run this step only when the fact holds.
- `OVERRIDE: <key> = <value>` — a value this routine pins, outranking any older copy elsewhere.
- `PRECEDENCE: <ordered list>` — an order that is a rule, not a preference.

Original labels from `Ai\00_ROLD_COMMANDS_TidyUp_BootUp.md` are kept in `[brackets]` on every step so
a counting verification can match old to new. Nothing was dropped; two steps were merged, one target
was corrected (TidyUP step 9 — see the note on it).

---

# 1. BootUP!   — 12 steps (step 4 has 6 sub-items)

Trigger: `BootUP!`, `boot up`, `start session`. Optional argument: `BootUP! <stream>`.

OVERRIDE: boot_pointer = V:\Ai\BU.MD
OVERRIDE: streams = plumbing | physics | chapter | legal | other
POINTER: Ai\ROLD\RULES.md   (what "done means" per stream, and the routing test)

---

### STEP 1 [orig. STEP -1] — KEITH'S SCREEN IS OFF LIMITS. Do this before anything else.

POINTER: Ai\ROLD\RULES.md   (the rule and its wording — do not restate it here)

Do, at the step level:
- Run the test suite **in CoW / Claude Code natively, in-process** — `py -3.14 -m pytest` inside the
  session. No window, no Run dialog, no computer-use launch, no `cmd /k`.
- Nodes run headless: `claude -p …` · `grok -p … --always-approve` · `gemini -p … --approval-mode yolo`.
- R2 publishes via `Ai\BTS_MESH\publish_r2_silent.vbs` (hidden) or the 22:00 scheduled task.
- Rails are probed by the native `BTS Rail Check` task, or by reading its report.
- Anything long → a scheduled task.
- Genuinely desktop-only work ships as a `.bat`/`.vbs` Keith double-clicks **when he chooses** — never
  taken mid-session.

INCLUDEIF: work is genuinely desktop-only (rclone R2 · Origin COM · Pandoc-on-Windows · G: · X:) -> Ai\ROLD\RAILS.md

---

### STEP 2 [orig. STEP 0.5] — A BARE `BootUP!` ASKS WHICH STREAM, THEN STOPS AND WAITS.

Ask: **plumbing / physics / chapter / legal / other.**
Then **STOP. Wait for Keith's answer. Start no work until he answers.**

- Do NOT infer the stream from what looks urgent.
- One stream per session, declared at boot. If work strays, finish the current stream's item and leave
  ONE line in the other stream's row of `V:\Ai\BU.MD`. Do not switch mid-session.
- `BootUP! <stream>` supplies the answer; the question is then skipped, not the declaration.

**TIMING** - the question is asked **after the mounts (step 4) and the boot reads (step 7) land** — it is
numbered here because it governs everything after it. `V:\Ai\BU.MD` states the same order:
*mount → read this → ask which stream → stop and wait.*

INCLUDEIF: stream == legal -> Ai\ROLD\STREAM_LEGAL.md
POINTER: Ai\ROLD\SCARS.md   (why the stop exists)

---

### STEP 3 [orig. STEP 0] — THE THREE RULES APPLY FROM THE FIRST TASK OF THE SESSION.

POINTER: Ai\ROLD\RULES.md   (full text — outranks everything in this file)

At the step level, before each task this session:
- **3a [0a] DELEGATE FIRST** — ask whether SGH and GEM can do it. If they can, fire BOTH, in parallel,
  BEFORE doing other work. Never fire-then-poll-serially. Verify every URL/DOI they return.
- **3b [0b] BACKGROUND, NO INTERVENTION** — sandbox or scheduled task by default.
- **3c [0c] HAND KEITH A CLICK** — every ask ships a `.bat`, a deep URL, or a direct console link.

---

### STEP 4 [orig. GENERAL ASK, items 1 · 2 · 3 · 4 · 4b · 4c] — THE GENERAL ASK. **ONE BLOCK, UP FRONT, BEFORE ANY WORK STARTS.**

Issue every permission the session could need in a **single front-loaded request block**. Do not
trickle these out. A permission asked mid-session is this step having failed.

- **4a [1] Mounts — all 13, plus situational, in one block.** `V:\Research4` goes FIRST (the access
  record lives inside it). Each is a `request_cowork_directory` grant Keith must Allow.
  POINTER: Ai\ROLD\RAILS.md   (the 13 paths, the situational ones, the bash-mount names, and
  which paths are refused by the platform vs. actually broken — do not re-list them here)
- **4b [2] Desktop-control — ONE `request_access` call:** `["Run","File Explorer","Command Prompt"]`.
  This is the R2-publish permission set; front-load it so a publish never stalls.
  POINTER: Ai\ROLD\RULES.md   (Keith's standing authorization to run the bat)
- **4c [3] Network fetch — ONE `web_fetch`** of a known file on `https://ai.dchambers.com` (cache-busted).
  This front-loads the fetch permission used for post-publish cloud-verify AND confirms the mirror is live.
  In the same block, state the session's standing intents ONCE in the BootUP status message: R2 publish
  bat runs · living-doc edits (ROLD/PIN/access record/memory) · `/tmp` builds · agent fan-outs — so no
  later action reads as a new escalation.
- **4d [4] Chrome bridge (BTS) first-use approval** — open the Grok PhD2 project tab once and have Keith
  approve the ONE extension prompt. The grant is per-session and cannot be pre-stored.
  Negative control: three denials means Keith is away, not refusing. Note it, queue bridge work, do NOT
  retry-spam.
- **4e [4b] Connectors (MCP) — Google Drive:** *verify*, do not re-request. Connector OAuth persists
  across sessions. If disconnected, surface the Connect button; Keith does the sign-in leg.
- **4f [4c] Dashboard server:** launch via a launcher that runs `bts_serve.py` — never `python -m http.server`.
  POINTER: Ai\ROLD\RAILS.md   (launcher paths, `/api` routes, bind address)

---

### STEP 5 [orig. 5] — READ THE TOOLS INDEX **BEFORE** BUILDING THE TASK LIST.

Read `Ai\00_TOOLS_INDEX.md`. This comes BEFORE the todo list, because the todo list will send you off
to *build* things we already have.

**THE TWO QUESTIONS — ask both before writing any script or firing any node:**
- *"Do we already have this?"* → `Ai\00_TOOLS_INDEX.md`.
- *"Would a grep of `V:\Research4` answer this?"* → **do the grep.**

PRECEDENCE: CROSSREF + LOCAL (`00_TOOLS_INDEX.md`, grep `V:\Research4`) → Cowork's own web search → GEMINI → BTS → paid SGH (`spend_ok=<usd>`)
OVERRIDE: doi_source = Crossref   (never ask a model for a DOI)
POINTER: Ai\ROLD\SCARS.md   (why this step is here and what skipping it has cost — 07-13, 07-28)

---

### STEP 6 [orig. 5b] — PROBE THE MCP RAIL. VERIFY, DO NOT ASSUME.

Run `Ai\BTS_MCP\PROBE_MCP.bat` → `00_WORKING\MCP_PROBE.txt`. Re-wire with
`Ai\BTS_MCP\WIRE_AND_PROBE.bat` (wires all five surfaces, then measures).

POINTER: Ai\ROLD\RAILS.md   (which client reads which config key, which surfaces are inert, which
check commands are invalid on this box)
POINTER: Ai\ROLD\SCARS.md   (the three failures that each present as "the server is broken")

---

### STEP 7 [orig. 6, first of two] — READ THE BOOT SET AND BUILD THE TASK LIST.

Read, in order:
1. Memory index.
2. `V:\Research4\CLAUDE.md` and this ROLD repository.
3. **`V:\Ai\BU.MD`** — the live state and stream index.
4. `Ai\00_FOLDER_ACCESS_RECORD.md`.
5. KEITH_ADJUDICATION / LOOSE_ENDS.

Then build the task list from the declared stream's row.

OVERRIDE: boot_pointer = V:\Ai\BU.MD   (fixed name, fixed path — no glob, no date, no "newest")
OVERRIDE: V:\Research4\BU.MD = DETAIL BACKLOG ONLY. Read on demand; never treated as live state; never written at TidyUP.
POINTER: Ai\ROLD\SCARS.md   (why the dated `00_NEXT_SESSION_HANDOFF_*` scheme is ARCHIVE and is not read for current state)

---

### STEP 8 [orig. 6, second of two] — DRAIN GROK FIRST.

Check the Grok thread for un-ferried DONE+READY batches. **Ferry them before starting new work.**

---

### STEP 9 [orig. 7] — CHECK SCHEDULED-TASK STATE.

Confirm each task is on/off **as intended** (watchdog, nightly publish, rail check, allotment check).
POINTER: Ai\ROLD\RAILS.md

---

### STEP 10 [orig. 8] — CONFIRM DATE AND TIME. Never assume it.

---

### STEP 11 [orig. 9] — FOR ANY CAMPAIGN / DATA QUESTION: READ THE PROVENANCE DOC FIRST.

Open the trip FOUNDATION / provenance doc **before** answering anything about a campaign or dataset.
PRECEDENCE: CHAPTER (current version) + PIN > per-dataset memos

---

### STEP 12 [orig. 10] — MEH-PPV THEORY SESSIONS: OPEN THE READING LIST FIRST.

INCLUDEIF: session topic is MEH-PPV theory -> V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\00_NEXT_SESSION_READING_LIST_MEHPPV_2026-07-05.md
Read it with its companion `CRITICAL_PARAMETERS_ENUMERATION_SEED_2026-07-05.md`. The work order is at
the bottom of the reading list; follow it.

---

# 2. TidyUP!   — 14 steps + SAPRS

Trigger: `TidyUP!`. Runs at the END of every session. Step 14 (TidyUP2) is mandatory, not optional.
**🔴 STEP 1b (SAPRS) is also mandatory** — added 2026-08-02, and it is the check that catches work
belonging to a stream other than the one declared at boot.

### STEP 1 [orig. 1] — SWEEP THE ENTIRE CONVERSATION FROM THE START.

Extract all work products, deliverables, and — crucially — **unstarted / unfinished / interrupted
tasks**. Record them in the LOOSE_ENDS / next-session record.

**COVERAGE — the sweep (steps 1–7) must touch every one of these classes:**
Citations/DOIs · PDFs · figures · raw/processed DATA · tables/CSVs · PEOPLE (step 5) · KEITH
RULINGS/LOCKS → `CANONICAL_ASSUMPTIONS.md` + memory · PROVISIONAL values awaiting Keith → flag files
(never silently canonized) · SCRIPTS/code used for any figure or number → kept beside their outputs ·
GOTCHAS/lessons → `_TOOLKIT_BTS/GOTCHAS` + memory · SECURITY items → top of the handoff ·
SCHEDULED-TASK state changes · TEMP/JUNK list (`chk_*`, `*.tmp`, ferry temps, stray zips) → deletion
list for Keith, **never auto-delete** · GROK-PROSE quarantine status · IP/publications items → PIN docs ·
INSTRUMENT/notebook metadata gaps → human-only list · EMAIL/correspondence finds · TOOL/ENVIRONMENT
changes → access record + toolkit README · HARDWARE/NETWORK topology findings (measured on this box or
a vendor datasheet, never recalled) · SESSION WRAPUP doc.

### 🔴 STEP 1b — **SAPRS: STREAM ARTEFACT PROCUREMENT AND RECORDING STEP.** *(Keith, 2026-08-02.)*

**MANDATORY. A `TidyUP!` is not complete until SAPRS passes.** Full procedure:
`ROLD\SESSION_HANDOFF_SOP.md` STEP 0.

**The rule, standing and continuous — not only at TidyUP:** the moment work product belonging to
**another stream** appears, it is written into **that stream's file immediately**, before the
conversation moves on. One stream is declared per session; **work does not respect that boundary.**

| stream / class | destination |
|---|---|
| plumbing | `V:\Ai\Streams\PLM_TODOS.md` |
| legal | `V:\Ai\Legal\TODO_MESH.md` · `TODO_KEITH.md` |
| rules binding every session | `V:\Research4\CLAUDE.md` |
| procedures | `ROLD\RULES.md` · `ROUTINES.md` · `PDAIS.md` · `SESSION_HANDOFF_SOP.md` |
| **failure classes** | `ROLD\SCARS.md` **AND `scars.jsonl`, same pass** |
| **tools** | `Ai\00_TOOLS_INDEX.md` **AND `BTS_MESH\TOOLS_REGISTRY.json`, same pass** |

**THE SIX CHECKS — answer all six out loud:**
1. Did anything from another stream come up? **Name each item.**
2. Is each written into **that stream's file**, not just mentioned in this stream's notes?
3. Tool built? → index **and** registry.
4. Belief overturned, or a failure repeated? → `SCARS.md` **and** `scars.jsonl`.
5. Rule that binds future sessions regardless of stream? → `CLAUDE.md`.
6. 🔴 **Is anything of value still living only in the transcript?** If yes, **the session is not
   finished.**

⚠ **Why this exists — measured 2026-08-02.** A LEGAL session produced an evening of drive work: a bat
whose safety guard points at the **boot drive** because it keys on a disk number, a sector-size
hypothesis that may make a cleanroom unnecessary, and two wrong conclusions worth recording as scars.
**All of it lived only in chat** and reached `PLM_TODOS.md` only because Keith said *"include in that
stream now."* Otherwise it would have been stripped with the transcript and lost. **Write it where it
belongs, not where you are. Later does not come.**

### STEP 2 [orig. 2] — GROK DRAIN.

Ferry every DONE+READY batch. Log any SENT-but-unferried with its rid. Leave Grok deliberately idle —
no make-work.

### STEP 3 [orig. 3] — ARCHIVE EVERYTHING NEW.

Citations → `Dsrt_Citations_running.md` · PDFs → `+Papers` (+ manifest) · figures → `figures/` + the
FIGURE REGISTER (step 4) · new data → archive intake folder with an md5 manifest · tables updated with
a `.bak`.

**COUNTING CHECK — after ANY docx/md build, count `cited` vs `listed`.** Two lines. A mismatch is a
truncated reference list, not a rounding error. Do not skip it because the build "looked fine".

### STEP 4 [orig. 3c] — FIGURE REGISTER: WRITE THE ROW **AS PRODUCED**, NOT AT TIDYUP.

Every figure written to disk gets a row in
`PhD2_DATA_ARCHIVE\00_WORKING\APPENDIX_F_FIGURE_REGISTER.md` **in the same turn it is made**:
label `Chap.Section-F-xx` | file | one-line caption | STATUS (**CURRENT** / **SUPERSEDED** → by what /
**DISQUALIFIED** → why). A figure with no register row is not done.
Curation: *hide* cosmetic-superseded iterations (axis tweaks, restyles, "add reference spectra"),
keeping only the final of that chain; *keep* iterations carrying distinct analytical content.
Appendix F .docx is generated FROM this register.
OVERRIDE: pre_2026_07_18_figures = recover context from the generating session (read_transcript, matched by figure DATE) or the contemporaneous handoff - cheaper source first

### STEP 5 [orig. 3b] — PEOPLE CLASS.

Collaborators / groupmates / co-authors / committee / beamline staff encountered in any session material
→ `PhD2_DATA_ARCHIVE\00_WORKING\PEOPLE_INDEX.md` (name | role/affiliation | connection to work | source/date).

### STEP 6 [orig. 4] — SYSTEMATIC INDEX REFRESH.

MASTER_INDEX · FIGURES_INDEX · REFERENCE_SAMPLES table · folder-access record Last-confirmed dates ·
the ROLD repository if a new item class appeared this session.

### STEP 7 [orig. 4b] — TOOLS: IF THIS SESSION BUILT ANYTHING REUSABLE, EDIT **BOTH** FILES IN THE SAME TURN.

`Ai\00_TOOLS_INDEX.md` **AND** `BTS_MESH\TOOLS_REGISTRY.json`. Both are hand-maintained; **no generator
exists**, so editing one leaves the other silently stale.
POINTER: Ai\ROLD\SCARS.md

### STEP 8 [orig. 5] — R2 PUBLISH + CLOUD-VERIFY. **CLAUDE RUNS IT, NOT KEITH.**

a. **MIRROR FIRST** — copy this session's changed control files into `PhD2_DATA_ARCHIVE\00_WORKING\`
   host-side (Read → Write). A publish is not a sync; an unmirrored file republishes stale forever.
   🔴 **`V:\Ai\BU.MD` → `00_WORKING\MIRROR_BU.md` IS MANDATORY AND IS ALWAYS LAST**, because step 9
   rewrites BU.MD after this step runs. **It lives outside the published tree, so it is the one file
   that is never carried automatically.** *(Found stale by a full day on 2026-08-02 — the boot
   pointer, the single file whose loss costs the most, was the only one with no off-machine copy.)*
   ⚠ **Check WHICH FILES SHOULD BE MIRRORED, not which ones you mirrored.** Verifying your own list
   against itself is a check that can only ever pass.
b. Run the native Windows bat. Prefer the hidden/scheduled route (BootUP step 1): `publish_r2_silent.vbs`
   or the 22:00 `R2 Publish Nightly` task.
   POINTER: Ai\ROLD\RAILS.md   (bat path, passes, exclude list, verify URL)
c. ⛔ **Do NOT rclone from the sandbox.** Native Windows reads only.
d. **VERIFY live↔mirror by MD5, WITH A NEGATIVE CONTROL** (a file that should NOT match must not match).
e. **Cloud-verify SERVED BYTES:** `web_fetch` a file written THIS session and confirm its *content* —
   HTTP 200 is not verification.

### STEP 9 [orig. 6] — OVERWRITE THE BOOT POINTER.

OVERRIDE: tidyup_target = V:\Ai\BU.MD
Overwrite `V:\Ai\BU.MD`: current stream, cross-stream blockers, the four stream rows (what is open in
each), rulings owed by Keith, first actions, open flags.
**Fixed name, fixed path. NEVER create a new dated handoff.**

### 🔴🔴 BU.MD CARRIES OPERATIONAL STATE ONLY. NO ANALYSIS. — Keith, 2026-08-03
*"Don't load anything on BU that will contaminate the session. Keep our questions, comments,
evaluations, etc. about the case isolated from the BU at the start."*

**BU.MD is read at EVERY BootUP by whatever model is running.** Anything in it is inherited before a
single source document is seen — the exact contamination `sweep_corpus.py` exists to prevent, in the
one file guaranteed to be read first. On 3 Aug it had accumulated a day of conclusions, several of
them wrong, and had to be cut from 28,783 B to 11,206 B.

**IN:** the clock and deadlines · what is staged and unrun · what is owed by Keith · state of the
machine · counts · pointers · procedural rules.
**OUT, to the stream's own tree:** conclusions, theories, findings, damages figures, reviewer
opinions, "what this session established", "the case as it now stands", corrections about the
subject matter. Legal → `V:\Ai\Legal\CASE_ANALYSIS_<date>.md`, reached via `Legal\_INDEX.md`.

⚠ **THE TEST, applied to every line before it is written here:** *would a fresh reader who must form
an independent view be worse off for having read this?* If yes, it belongs in the stream tree.
⚠ **A POINTER IS NOT A SAFE COMPROMISE.** *"Analysis exists at X, don't open it yet"* is an
advertisement with a soft fence, and it leaks that the matter is heavily worked, which licenses
deference. The stream index already reaches the analysis in one hop. **The read-boundary belongs on
the TASK** — see `Legal\COLD_READ\TASKING.txt`, which held.
⚠ **Bare facts are NOT exempt.** *"Chambers never signed the NDA"* was a hard fact in a delivered
document on 2 Aug and was false. The category *verified fact, safe to carry forward* is the category
that failed. If a fact is load-bearing it is in the record; let the reader find it.
⚠ **Operational protection is written as STATE, not as knowledge:** not *"the NDA was signed, don't
serve that request"* but *"the seven requests are being rebuilt; nothing serves until that task
closes."* Same guard, no conclusion.
**Do NOT write `V:\Research4\BU.MD`** — it is DETAIL BACKLOG ONLY and is not updated at TidyUP.

> ⚠ **CORRECTED HERE.** The source step said *"Write `00_NEXT_SESSION_INSTRUCTIONS_<date>.md`"*, and the
> source's own CURRENT POINTER section still named `V:\Research4\BU.MD`. Both were superseded by Keith
> on 2026-07-20 (fixed name) and 2026-07-30 (relocation to `V:\Ai\`). The target above is the live one.

POINTER: Ai\ROLD\SCARS.md   (after moving any pointer, walk the READER's path)

### STEP 10 [orig. 7] — UPDATE MEMORY FILES.

New gotchas, feedback, rulings. Superseded memory gets a SUPERSEDE NOTICE, never silent deletion.

### STEP 11 [orig. 8] — TELL KEITH: what's done · what's owed **by him** · what BootUP will resume.

### STEP 12 [orig. 9] — SESSION TRANSCRIPT → MARKDOWN.

OVERRIDE: session_log_home = V:\Ai\_session_logs\<stream>\<date>_<sessionid>\
OVERRIDE: PhD2_DATA_ARCHIVE\SESSION_MD\ = ARCHIVE ONLY. Never written again. Never the read target.
POINTER: V:\Ai\_session_logs\00_SESSION_INDEX.md   (517 sessions, one table, greppable)

Session transcripts are stripped and filed to **`V:\Ai\_session_logs\`**, stream-sorted and indexed.
`strip_transcript.py` does the work; prose is verbatim, tool payloads and thinking blocks removed.

> ### 🔴 RULED BY KEITH 2026-08-01 — ONE HOME, AND IT IS NOT THE PUBLISHED TREE.
> This step used to write `Date_Time_SessionID.md` into `PhD2_DATA_ARCHIVE\SESSION_MD\` (111 files).
> **That folder is INSIDE the R2-published subtree** — so every session transcript was going to the
> public mirror, including any that touched the case. Meanwhile P0-01 built `V:\Ai\_session_logs\`
> (517 sessions, not published, `legal\` isolated with 36).
> **Two homes for one thing is a copy, and copies rot** — the same defect that rotted the dated
> handoff scheme four times. `SESSION_MD\` is now ARCHIVE: never written, never read for state.

**Verify before marking done:** the pair moved together (`.jsonl` + `STRIPPED_*.md`), and the index
row exists. A `.jsonl` without its stripped twin is how the next session ends up re-reading 1.7 GB.
⛔ Cannot be delegated to a sub-agent **for the CURRENT live session** — the parent writes it, or it
is written after the session closes.
POINTER: Ai\ROLD\SCARS.md

### STEP 13 [orig. 10] — LEGAL SWEEP.

INCLUDEIF: this session's stream was `legal` -> Ai\ROLD\STREAM_LEGAL.md
The case tree is `V:\Ai\Legal\`, **not** `V:\Research4` — a normal sweep will not see it.
a. Update `V:\Ai\Legal\_INDEX.md` — every document produced this session, in its section.
b. Update `HANDOFF_<date>.md`: what changed, what is now known STALE, open items **with dates**.
c. **DEADLINE CHECK** — recompute days remaining to every court date. Any long-lead item (out-of-state
   subpoena, records request, OCR backlog) that is **not yet STARTED** goes at the TOP of the handoff.
   POINTER: Ai\ROLD\STREAM_LEGAL.md   (the dates themselves)
d. **THE UNSENT LIST** — name every drafted-but-unsent letter, request and filing, explicitly, in the
   handoff **and out loud to Keith**. A draft on disk is an unfinished task, not a deliverable.
e. Record every **correction Keith made** to a stated fact or theory → the reasoning log, written to
   disk the moment it is made.
f. Session transcripts: **NOTHING TO DO HERE. This step is retired as of 2026-08-01.**
   OVERRIDE: session_log_home = V:\Ai\_session_logs\<stream>\<date>_<sessionid>\
   POINTER: V:\Ai\_session_logs\00_SESSION_INDEX.md   (517 sessions, one table)
   > The old step said *"run `Desktop\MOVE Session Transcripts to Legal.bat` → strips to
   > `V:\Ai\Legal\_transcripts\` + writes `_TRANSCRIPT_POINTER.md`."* **All three are retired.**
   > That bat is what put 2,735 files / 1.7 GB of session logs INTO the case tree, where they
   > poisoned every corpus sweep that globbed it — session logs are not case material. P0-01
   > closed 2026-08-01: 603 stripped (1,712 MB → 22.4 MB, 84,282 turns, 0 failures), 88 duplicates
   > removed with 0 distinct turns lost, 517 pairs filed by stream. The case tree now holds none.
   > Legal-stream sessions are isolated at `_session_logs\legal\` — 36 of them.
   > ⚠ **The bat must never be re-staged in that form.**
g. ⛔ Publish NOTHING from `V:\Ai\Legal\` to R2 unless Keith names the file.

### STEP 14 — RUN TidyUP2. MANDATORY. TidyUP! is not complete until it has run.

---

# 3. TidyUP2   — 10 steps (9 checks + the append)

The mandatory final verification pass of every TidyUP!. Run **all** checks, **in order**.

### CHECK 1 — RE-READ THE SESSION FROM THE START.
Walk the conversation/task chronology. Every claim, number, file and promise made this session must have
an on-disk artifact and a record entry.

### CHECK 2 — REFERENCED-FILE EXISTENCE SWEEP.
Every filename cited in chapter drafts, figure lists, indexes and memos written this session must exist
at the stated path. Broken pointers → fix, or write an erratum.

### CHECK 3 — NUMBER-CONSISTENCY SWEEP.
Counts and headline values in the wrapup, memory and `V:\Ai\BU.MD` must match reality. **Recount; do not
trust prose.** Includes the `cited` vs `listed` count from TidyUP step 3 for every docx/md built.

### CHECK 4 — STALE-CONSTANT SWEEP.
Constants written this session (PIN etc.) checked against the LATEST resolution memos. Newest dated
resolution wins. Memory can re-import retired values.
PRECEDENCE: newest dated resolution memo > chapter > memory

### CHECK 5 — INTERNAL-MEMORY RECONCILIATION.
Read the memory files relevant to this session; fix contradictions against today's rulings. `MEMORY.md`
index lines must match file contents.

### CHECK 6 — SANDBOX SWEEP.
`/tmp` + scratch. Work products existing ONLY in the sandbox get copied to the archive or are explicitly
listed as abandoned; leftovers → junk list.
**If this session BUILT a deliverable in the sandbox, copy the BUILDER and the FIGURE SCRIPTS to the
archive beside the output, and MD5-verify host-side.**

### CHECK 7 — ERRATA PROPAGATION.
Any list or table already delivered to Keith (including Desktop copies) later found wrong gets an ERRATA
banner or a companion errata file. Never leave a known-wrong deliverable in place.

### CHECK 8 — LIVING-DOC CHECK.
ROLD repository · PIN · CANONICAL_ASSUMPTIONS · access record · FIGURES_INDEX · PEOPLE_INDEX ·
Dsrt_Citations_running · FUTURE_SEARCH_TASKS — each either updated this session or verified as
not-needing-update.
**Plus:** any file claiming *"generated from X"* must name a generator that actually exists on disk.

### CHECK 9 — PUBLISH + CLOUD-VERIFY TidyUP2's OWN CHANGES.
Then report findings to Keith as a numbered **T2-x** list.

### 🔴 CHECK 9b — RE-RUN CHECKS 2, 3 AND 8 AFTER 6, 7 AND 10 HAVE MADE THEIR EDITS.
*(Added 2026-08-03 from S-122.)* Checks 2, 3 and 8 run **before** checks 6, 7 and 10 change anything,
so they certify a state that no longer exists by the time the pass reports. On 3 Aug TidyUP2 wrote
*"PLAIN now holds exactly the three documents and nothing else"*, then created a fourth file in that
folder during check 7, then reported clean. **A check that changes the thing it checked must
re-check it.** Also: **any artefact TidyUP2 itself creates is indexed in the same turn** — the same
pass produced an ERRATA that no control document pointed at.

### CHECK 10 — APPEND ANY NEW CLASS DISCOVERED THIS SESSION.

APPEND-ONLY. Every new datatype, record, bookkeeping class or failure class encountered this session gets
appended so the next TidyUP2 checks it too.

OVERRIDE: classes_discovered_log = Ai\ROLD\SCARS.md
POINTER: Ai\ROLD\SCARS.md   (**this IS the "Classes discovered" list. Append there. Do not start a second log.**)

---

## NEGATIVE CONTROLS AND COUNTING CHECKS — the steps that actually catch things

Listed here only as an index; each is a step above and lives there.

| control | step |
|---|---|
| Count `cited` vs `listed` after any docx/md build | TidyUP 3 · TidyUP2 check 3 |
| MD5 live↔mirror **with a negative control**, then fetch and read SERVED BYTES | TidyUP 8d–8e |
| Verify by ARTIFACT (did the output folder fill?), never by a launcher's own success message | TidyUP 8 · BootUP 6 |
| Three Chrome-bridge denials = Keith is away, not refusal — note and queue, do not retry-spam | BootUP 4d |
| A failing check must be confirmed **host-side with `Read`** before it is reported as a finding | TidyUP2, all checks |
| Referenced-file existence loop over everything written this session | TidyUP2 check 2 |
| Every `Ruling`/`Markers` field survives a JSON round trip | POINTER: Ai\ROLD\SCARS.md |
