# ROLD ARCHITECTURE — the decomposition spec
**Keith-ordered 2026-07-30:** *"Its a Repository of Documents - make a RULES documents, RAILS, LOGINS,
etc.. you decide, research the right way to do it, but make it organized properly."*
**Status: SPEC + partial execution. The rest is a PLUMBING-session job.**

---

## 1. THE DIAGNOSIS — measured 2026-07-30, not asserted

| Symptom | Measurement |
|---|---|
| `Ai\` is a flat dump | **~300 entries in one directory** — governance docs, `.bak` chains, `.zip`, `.png`, `.py`, raw `.dat` |
| The commands file is a monolith | **`00_ROLD_COMMANDS_TidyUp_BootUp.md` = 79,533 bytes** |
| Backup sprawl | **13 `00_AUTONOMOUS_QUEUE.md.bak_*`** · **15 `Dsrt_Citations_running.md.bak_*`** |
| Handoff rot, already documented | 9 `00_NEXT_SESSION_HANDOFF_*` files; the dated scheme rotted **four times** before `BU.MD` fixed it |
| Governance is indistinguishable from data | `CANONICAL_ASSUMPTIONS.md` sits beside `mar08_xy_SEC_table.csv` |

**ROLD is currently a folder, not a repository.** Everything is retrievable only by knowing its name in
advance — which is the exact failure the `BU.MD` fix was created to end, unfixed everywhere else.

## 2. 🔴 THE ORGANISING PRINCIPLE — ONE DOCUMENT, ONE EDIT-TRIGGER

Researched against three established patterns and reduced to the one that fits this repo's failures:

- **Diátaxis** (Procida) — split docs by *user need*: how-to vs reference vs explanation. Correct
  instinct, but it partitions by reader, and here there is one reader.
- **ADR / Architecture Decision Records** (Nygard) — numbered, dated, **immutable**, each recording
  context → decision → consequence. **This is exactly what the SCARS are**, and they are currently
  interleaved with live instructions, which is why they get edited and lost.
- **Single source of truth** — the repo's own hardest-won lesson: *"a filename in prose is a copy of a
  pointer, and copies rot."*

⇒ **THE RULE: a document is defined by what makes it change.**
> **If two things in one file change for different reasons, they are two files.**

| Doc | Changes when… | Mutability |
|---|---|---|
| **RULES** | Keith rules something | append + supersede, never silently rewrite |
| **RAILS** | the infrastructure changes | live, overwritten |
| **ROUTINES** | a *step* changes | live, overwritten |
| **STREAMS** | a stream's method or posture changes | live, one file per stream |
| **SCARS** | a failure is measured | 🔴 **APPEND-ONLY. NEVER EDITED.** |
| **REGISTRIES** | an artefact is created | live, generated where possible |
| **INDEX** | any document above is added or removed | live — **the only pointer anyone memorises** |

The current file violates this on every line: Keith's directives, measured failures, path constants and
checklist steps all share one document with one edit history.

## 3. THE TARGET TREE

```
Ai\ROLD\
  00_INDEX.md              THE entry point. The only path anyone needs to know.
  RULES.md                 THE THREE RULES · security/dissemination canon · Keith's standing rulings
  RAILS.md                 paths, mounts, drive letters, endpoints, desktop-only vs sandbox, .secrets
  ROUTINES.md              BootUP / TidyUP / TidyUP2 — STEPS ONLY, no rules restated, no scars inline
  SCARS.md                 append-only, dated, numbered. Mount corruption, pointer rot, the 4 handoff rots
  STREAMS\
    STREAM_PLUMBING.md
    STREAM_PHYSICS.md
    STREAM_CHAPTER.md
    STREAM_LEGAL.md        ✅ WRITTEN 2026-07-30
  REGISTRIES\              pointers to the existing indexes — do NOT copy them
    (TOOLS_INDEX · DOI_INDEX · PEOPLE_INDEX · MASTER_INDEX · FIGURES_INDEX · FOLDER_ACCESS_RECORD)
  ARCHIVE\                 dated handoffs, .bak chains, superseded files. Read-only. Never consulted for state.
```

**`00_MESH_CHARTER.md` stays where it is** and is *pointed at*, not moved or copied — it is already a
correctly-factored document and the ROLD already treats it as a pointer.

## 4. MIGRATION RULES — how not to make it worse

1. 🔴 **MOVE, then leave a one-line pointer.** Never copy. **Two copies of a rule is the disease.**
2. 🔴 **Never delete the monolith until `00_INDEX.md` resolves every section of it.** Diff the section
   headings before and after; **count them.** *(Same discipline as `cited` vs `listed` — that check
   would have caught 26 missing references.)*
3. **Host-side reads only.** The mount silently truncates and corrupts — **12 measured hits**, one of
   which nearly ate `bts_paths.py`. Do the migration with `Read`/`Write`/`Edit`, never `cp` over the mount.
4. **Scars migrate verbatim, with their dates.** They are evidence, not prose. Do not tidy their wording.
5. **One commit per document class**, so a bad move is revertible. `Ai\` is a git repo — use it.
6. **`.bak` chains and dated handoffs → `ARCHIVE\` in bulk.** They are not state and must never be read
   for state. 28 backup files currently sit at the same level as live governance.

## 5. WHAT IS DONE, AND WHAT IS OWED

**DONE 2026-07-30 (legal session, context-limited):**
- ✅ `ROLD\STREAM_LEGAL.md` — the LEGAL stream, fully specified, pointing at `V:\Ai\Legal\` and
  copying nothing into the PhD tree
- ✅ `ROLD\00_ROLD_ARCHITECTURE.md` — this spec
- ✅ LEGAL added as the fourth stream in the commands file + Step 0.5 + a TidyUP step 10

**OWED — next PLUMBING session, in this order:**
1. `00_INDEX.md` — write it FIRST; it is the target every later move points into
2. `SCARS.md` — extract every dated scar from the monolith **verbatim**, number them
3. `RAILS.md` — extract all path/mount/endpoint/desktop-only constants
4. `RULES.md` — extract THE THREE RULES + the security canon + standing rulings
5. `ROUTINES.md` — what remains of the commands file: steps only
6. `STREAM_PLUMBING/PHYSICS/CHAPTER.md` — same shape as `STREAM_LEGAL.md`
7. `REGISTRIES\` — pointer stubs, no copies
8. `ARCHIVE\` — sweep the 28 `.bak` files and 9 dated handoffs
9. **Verify:** every heading in the 79 KB monolith resolves somewhere in the new tree. **Count them.**
10. Update `CLAUDE.md` and `BU.MD` to point at `ROLD\00_INDEX.md`
11. Audit and resolve **`V:\Research4\Ai\Legal\`** — it is not the case tree and should not exist

---

# 6. 📼 SESSION-LOG SUBSYSTEM — Keith-ordered 2026-07-30. **PLUMBING job, own sub-project.**
*"Sort transcripts into stream subfolders — make a full read and resort part of the next Plmbg session.
Make the Stripper tool a part of the next PLMBG session (maybe run it on all session logs while
sorting? pair with full log file in same folder?)"*

## 6.1 WHERE THE LOGS ACTUALLY LIVE — solved 2026-07-30, after two failed bats

🔴 **Claude is a PACKAGED (MSIX/Store) app. `%APPDATA%\Claude` is VIRTUALIZED and effectively empty.**
The real store is:

```
%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\
    598a803e-…\ccd03d6b-…\local_<SESSIONID>\
        audit.jsonl                              <- tool-call audit log (big; NOT prose)
        .claude\projects\C--Users-…-outputs\
            <uuid>.jsonl                         <- 🔴 THE CONVERSATION
            agent-a<hex>.jsonl                   <- subagent conversations
%LOCALAPPDATA%\Packages\…\LocalCache\Local\claude-cli-nodejs\Cache\   <- MCP logs (timestamped)
%LOCALAPPDATA%\claude-cli-nodejs\Cache\                              <- MCP logs (unpackaged)
```

⚠ **Two bats failed against the virtual path before this was found.** A folder copy of
`AppData\Roaming\Claude` returns **only Electron GPU cache** — no session data. The discovery tool is
`Desktop\FIND Session Transcripts.bat` (read-only) → `V:\Ai\Legal\_transcript_search.txt`.

**Worked example — the 2026-07-30 legal session** (`local_e15a3be5-72e6-4f19-a26c-9090d45faf77`):
conversation = `4da1e761-c2ba-4818-83e5-73fadce4194c.jsonl` (**11 MB**) · `audit.jsonl` (26 MB) ·
~25 `agent-*.jsonl` subagents · dozens of small MCP logs.

## 6.2 🔴 CURRENT STATE IS WRONG — FIX FIRST

`Desktop\COPY Session Logs to Legal.bat` ran and pulled **2,735 files / 1.7 GB into
`V:\Ai\Legal\_transcripts\`** — i.e. **every session ever run, of every stream, dumped inside the case
folder.** It is not case material, it distorts any sweep of `V:\Ai\Legal`, and it must move.

### 🔴 EXECUTION ORDER — KEITH, 2026-07-30. **STRIPPER → STRIP → SORT-AND-MOVE-WITH-THE-PAIR.**
*"stripper.py comes before session sorts so stripper > strip > sort and move w/stripped version."*

| # | Step | Why this order |
|---|---|---|
| **1** | **FIX AND VERIFY `strip_transcript.py`** against one real file (§6.5) | It has never run. Stripping 2,735 files on an unverified schema produces 2,735 empty `.md` and wastes the pass |
| **2** | **DEDUPE in place** — `sessions\` / `cli-pkg\` / `cli\` overlap; identical timestamped MCP logs appear more than once. Hash and collapse | Do it before stripping so nothing is stripped twice |
| **3** | **STRIP IN PLACE**, batched and resumable, skip-if-exists | Each `STRIPPED_<uuid>.md` is created **beside** its `<uuid>.jsonl` |
| **4** | **SORT AND MOVE THE PAIR TOGETHER** into `V:\Ai\_session_logs\<stream>\<date>_<sessionid>\` | **The raw log and its stripped version travel as one unit and are never separated.** Classify per §6.4 |
| **5** | Build `00_SESSION_INDEX.md`; register the stripper in `00_TOOLS_INDEX.md` **and** `TOOLS_REGISTRY.json` | |

⚠ **ONE PASS OVER 1.7 GB, NOT TWO.** The earlier draft of this spec had move-then-strip; Keith
corrected it. Stripping first means the sort moves a finished pair, and a mis-sort later costs a
rename rather than a re-strip.
⚠ **`V:\Ai\Legal\_transcripts\` is the current (wrong) home** — the move in step 4 is what empties it.
Nothing about session logs belongs under `Legal\`.

## 6.3 TARGET LAYOUT — stripped `.md` PAIRED WITH its raw log, per Keith

```
V:\Ai\_session_logs\
  00_SESSION_INDEX.md        <- id · date · stream · title · turns · sizes · one-line subject
  plumbing\ physics\ chapter\ legal\ unsorted\
      <date>_<sessionid>\
          <uuid>.jsonl              raw conversation      ) SAME FOLDER —
          STRIPPED_<uuid>.md        prose, verbatim       ) that is the pairing Keith asked for
          audit.jsonl               tool audit
          agents\                   agent-*.jsonl + their stripped .md
  _mcp_logs\                 <- timestamped MCP logs, out of the way, by date
```

## 6.4 CLASSIFYING A SESSION INTO A STREAM

No stream is recorded in the file — **it must be inferred, and that requires reading.** Cheapest
reliable signal, in order: (1) an explicit `BootUP! <stream>` in the first user turn; (2) paths touched
(`V:\Ai\Legal` → legal · `upsjudge`/`BTS_MESH`/`.bat` → plumbing · `CH4`/`docx`/citations → chapter ·
SECO/Φ/onset/`.dat` → physics); (3) first-user-turn keywords. **Anything ambiguous goes to `unsorted\`
— do not guess.** 126+ sessions exist; most predate the streams and will legitimately be `unsorted`.

## 6.5 THE STRIPPER — `V:\Ai\Legal\strip_transcript.py`, **WRITTEN BUT NEVER SUCCESSFULLY RUN**

Move it to `V:\Ai\_session_logs\` (it is a tool, not case material) and **register it in BOTH
`00_TOOLS_INDEX.md` AND `TOOLS_REGISTRY.json`** — TidyUP step 4b, the drift that cost a rebuild on 07-28.

Owed work:
1. 🔴 **Verify the schema against a real file.** It was written blind. Confirm `message.role` /
   `message.content` block shapes, and that `type` values are what it expects.
2. **Confirm what `audit.jsonl` actually contains** — audit records or prose. Determines whether it is
   stripped or merely archived.
3. **Batch it.** 1.7 GB / 2,735 files is not one invocation. Per-session, resumable, skip-if-exists.
4. **Report compression per file** (already implemented) — a near-empty output means no prose was found,
   which is the signal that the schema assumption is wrong.
5. Keep the design rule: **STRIP, NEVER SUMMARIZE.** Prose verbatim on both sides; drop only tool
   payloads, thinking blocks, system reminders and exact consecutive duplicates. *(Keith rejected
   one-line summarisation explicitly: "Loses all nuance and this isn't physics.")*

## 6.6 ⚠ SCAR — REPEATED TWICE IN ONE DAY

**`pause` is not a report. Write a LOG.** The R2 publish bat (earlier 07-30) exited before writing its
log and the failure was invisible; the transcript bat then **closed before Keith could read the screen**,
losing the result. ⇒ **Every `.bat` opens its log file FIRST and tees everything to it**, so the outcome
survives the window closing. Rebuild the copy bat this way.

---

⚠ **Do not start this mid-session or with a low context budget.** It is a whole-repo refactor with a
counting verification at the end. It is a PLUMBING deliverable — **done means it runs**, and here that
means: **every pointer resolves and nothing was lost.**
