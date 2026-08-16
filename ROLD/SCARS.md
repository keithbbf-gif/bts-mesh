# SCARS — append-only. Dated, numbered, verbatim. NEVER EDITED.
> **What makes this file change:** a failure is MEASURED. Nothing else.
> **Never rewrite an entry.** If an entry is later shown to be wrong, APPEND a correction that
> names the entry it corrects. The wrong entry stays — the fact that we believed it is evidence too.
> This is the ADR/incident-report class (Nygard): context -> what happened -> consequence.
POINTER: Ai\00_ROLD_COMMANDS_TidyUp_BootUp.md   (the monolith these were extracted from; still authoritative until the decomposition is verified)
POINTER: V:\Ai\Streams\PLM_TODOS.md                     (the live plumbing backlog)

---

*Extraction pass 1 — 2026-07-30. Sources: `Ai\00_ROLD_COMMANDS_TidyUp_BootUp.md`, `CLAUDE.md`,
`V:\Research4\BU.MD`, `Ai\ROLD\00_ROLD_ARCHITECTURE.md` §6.6. Read host-side only (the mount is
scar S-05/S-06/S-07/S-30/S-31). **Nothing was deleted from the sources.** Text below is verbatim;
only the entry headings are new.*

---

## S-01 · 2026-07-05 · Three Chrome-bridge denials were Keith being away, not Keith refusing

> If Keith is away and it's denied, note it and queue bridge work; do NOT retry-spam (3 denials on 2026-07-05 = Keith away, not refusal).

*(source: ROLD BOOT UP step 4)*

---

## S-02 · 2026-07-06 · The ROLD commands file was lost to disk truncation and had to be reconstructed

> **⚠ RESTORED 2026-07-06 after disk truncation (see .bak_2026-07-06-* files): reconstructed from Doping-session context; this IS the canonical current version. Post-edit integrity rule: wc -c + tail-check after every edit of this file.**

**Lesson:** Post-edit integrity rule: `wc -c` + tail-check after every edit of this file.

*(source: ROLD, line 83)*

---

## S-03 · 2026-07-06 · A mixed permission dialog let the wrong scope be answered

> **2026-07-06 lesson: Keith must answer the PRIMARY per-site ask, not a broader-scope option in a mixed dialog; a mis-click deny is recoverable same-session by re-granting.**

*(source: ROLD BOOT UP step 4)*

---

## S-04 · 2026-07-10/11 · GDX write silently failed on stale connector auth, and the node said it could write

> **2026-07-10/11 (mesh/dashboard + GDX session):** **GDX write-requires-reauth class** — Grok's Drive write silently failed on stale connector auth (SGH walked back an earlier "yes I can"); Keith re-auth fixed it and the round-trip proved out. Lesson: don't trust an agent's self-reported connector capability — v

**Lesson:** don't trust an agent's self-reported connector capability.

⚠ **THE SOURCE LINE ITSELF IS TRUNCATED MID-WORD** — the monolith ends at line 728 with the
characters `— v`. Recorded here exactly as found; the remainder of that sentence is lost.

*(source: ROLD, line 728 — final line of the file)*

---

## S-05 · 2026-07-12 · MOUNT HIT: `jack_command.html` served pinned at a truncated 63,824 bytes

> 1. **TRUNCATION (known):** `jack_command.html` served **pinned at 63,824 bytes** (host: 1,146 lines) and
>    **never refreshed**, even across size-changing host edits. A patch script was one assertion away from
>    writing the truncated view back and destroying the dashboard.

*(source: ROLD "Classes discovered", 2026-07-12; also CLAUDE.md)*

---

## S-06 · 2026-07-12 · MOUNT HIT: `bts_gdx.py` read back missing a colon → a FALSE SyntaxError

> 2. **CHARACTER-LEVEL CORRUPTION (NEW):** `bts_gdx.py` read through the mount was **missing a colon** —
>    `finally` instead of `finally:`. `ast.parse` therefore reported a **FALSE syntax error** in a file that
>    is perfectly valid on disk. Host-side `Read` **and** `Grep` both confirmed `finally:` at line 196.
>    **I nearly "fixed" a file that was never broken.**

*(source: ROLD "Classes discovered", 2026-07-12; also CLAUDE.md)*

---

## S-07 · 2026-07-12 · MOUNT HIT: `dash.json` / `sgh_spend.json` gave bogus JSON decode errors

> 3. Same corruption hit `dash.json` (a bogus "Unterminated string" at line 255, which is valid on disk).

And, from CLAUDE.md's record of the same session:

> - `dash.json` / `sgh_spend.json` → **bogus JSON decode errors**. Both valid on disk.

**Lesson (stated for S-05/S-06/S-07 together, verbatim):**
> - **A sandbox read is NOT evidence.** `ast.parse` / `json.load` / `grep` run over the mount can produce
>   **false failures AND, in principle, false passes**. Never conclude a file is broken from a sandbox read.
> - **Host-side `Read` / `Grep` are the ONLY ground truth.** Confirm with BOTH before acting on a defect.
> - **NEVER `cp` a critical file through the mount** while this is happening — the copy can carry the
>   corruption into the destination. Mirror host-side (Read → Write), or not at all.
> - **Functional proof beats parse proof:** the modules that matter (`bts_sgh`, `bts_gem`, `bts_vertex`)
>   are trustworthy because they made **real live API calls**, not because a sandbox `ast.parse` liked them.

*(source: ROLD "Classes discovered", 2026-07-12; CLAUDE.md)*

---

## S-08 · 2026-07-12 · 26 of Chapter 4's 36 references were silently eaten — the list truncated at the letter G

> This is the same failure class that silently ate **26 of Ch4's 36 references** (list truncated at the
> letter G). It has now bitten the dissertation, the dashboard, and the verifier itself.

And, from CLAUDE.md:

> This is the same failure class that silently ate **26 of Chapter 4's 36 references** (the list was
> truncated at the letter G, including `[Helander2010]`, which the chapter quotes verbatim). It has now
> bitten the dissertation, the dashboard, and the verifier itself. **After any docx/md build, COUNT
> `cited` vs `listed`.** Two lines. It would have caught the missing 26 instantly.

**Lesson:** After any docx/md build, COUNT `cited` vs `listed`. Two lines.

*(source: ROLD "Classes discovered" 2026-07-12; CLAUDE.md)*

---

## S-09 · 2026-07-12 · BootUP took only one mount and then stalled twice mid-session

> On 2026-07-12 the BootUP took ONLY `V:\Research4` and then had to stop twice mid-session — for the Desktop (to fix the launcher) and for GDX. Exactly the stall this step exists to prevent. **Ask for the whole set in ONE up-front block, before any work starts.**

*(source: ROLD GENERAL ASK step 1)*

---

## S-10 · 2026-07-12 · The dashboard launcher started the plain static server, so every panel silently went stale

> **⚠ THE 2026-07-12 ROOT CAUSE — do not regress this.** The Desktop launcher was starting **`python -m http.server 8765`**, the PLAIN static server. It serves the page but has **no `/api` routes**, so `<TEST>` could not run the python probe (a browser cannot execute python — the button must call a server) and every panel went stale. *That* is why `bts_surfaces.py` measured GDX at 15/100 GB on the command line while the screen still read "? / 100 GB".

*(source: ROLD GENERAL ASK step 4c)*

---

## S-11 · 2026-07-12 · The §4.10 IP pedestal finding was raised then withdrawn — the chapter was right

> - ❌ §4.10 IP pedestal was RAISED THEN WITHDRAWN — the chapter was right; the error was Cowork's
>   (audited a section without reading its title). Do NOT reopen it as a finding.

*(source: ROLD, prior pointer 2026-07-12)*

---

## S-12 · 2026-07-13 · A brand-new Origin reader was written while three existing tools sat unpointed-at — and $2.93 of paid search bought facts already in Ch4's own reference list

> **WHY IT IS HERE AND NOT BURIED:** on 2026-07-13 Cowork wrote a brand-new Origin reader while `BUILD_OPJ_READER.sh`, `origin_export.py` and a fully populated `Ai\OPJ_exports\` tree already existed — nothing pointed at them, so nothing found them. Keith: *"Why that in the ROLD? Why didn't you see it?"* The ROLD indexed the DATA and the ROUTINE but never the TOOLS. The same reflex bought $2.93 of paid web search for facts already sitting in Ch4's own reference list.

**Lesson (verbatim, THE TWO QUESTIONS):**
> - *"Do we already have this?"* → `00_TOOLS_INDEX.md`.
> - *"Would a grep of `V:\Research4` answer this?"* → do the grep.

Also recorded separately:

> **WHY THE SPEND RULE STILL STANDS:** on 2026-07-13 two grounded SGH calls cost **$2.93** doing work the free lanes — and the local disk — could have done. **Spending must be NEEDED, not reflexive.** But do **not** invert it into hoarding-anxiety either: *price the thing before sounding the alarm.*

*(source: ROLD BOOT UP step 5; ROLD RAILS section)*

---

## S-13 · 2026-07-13 · GDX's drive letter was written as `E:` instead of `X:` and the wrong letter sat in the ROLD for a day

> **⚠ THE DRIVE LETTER IS `X:`, NOT `E:` — Keith corrected this 2026-07-13 and the wrong letter sat in this file for a day, sending scripts to a path that does not exist)**

And, from CLAUDE.md:

> Also: **GDX is `X:\`, not `E:\`** — the wrong letter sat in ROLD for a day.

*(source: ROLD GENERAL ASK step 1; CLAUDE.md)*

---

## S-14 · 2026-07-13 · The Ch4-review publish stalled because `D:\R2Cloner` was not in the mount list

> Without this mount Cowork cannot publish, cannot read the bat, and has to hand Keith a `RUN_ME_*.bat` to double-click — which is exactly what stalled the Ch4-review publish on 2026-07-13.

*(source: ROLD GENERAL ASK step 1)*

---

## S-15 · 2026-07-15 · `D:\ODX\OneDrive` cannot be mounted — the step had been failing at every BootUP since it was added

> **🔴 CORRECTION 2026-07-15 — `D:\ODX\OneDrive` CANNOT BE MOUNTED EITHER.** The line above asks for it
> and **it is REFUSED every time** — same protected-location class as `C:\Users\Papa\OneDrive`
> (`...\OneDrive\Documents\WindowsPowerShell`). This step has been failing at every BootUP since it was
> added on 2026-07-14. **Ask for `D:\ODX\OneDrive\BTS_ODX` instead** — it mounts fine and is the folder
> actually wanted. (Bash path: `/mnt/BTS_ODX`.)

*(source: ROLD GENERAL ASK step 1)*

---

## S-16 · 2026-07-15 · GDX mounts for Claude's file tools but NOT into the bash sandbox

> **🔴 ALSO 2026-07-15 — `X:\My Drive\BTS_SGH_Handoff` (GDX) mounts for Claude's file tools but NOT into
> the bash sandbox.** Use `Read`/`Write`/`Edit`/`Grep`/`Glob` on the host path; bash cannot see it. Not a
> problem in practice — `bts_gdx.py` runs natively on Windows — but do not waste time on the bash error.

*(source: ROLD GENERAL ASK step 1)*

---

## S-17 · 2026-07-15 · THE RAILS SECTION OF THE ROLD WAS FALSE ON EVERY ROW FOR TWO DAYS — and seeded a $299 phantom credit

> ### 🔴 THIS SECTION LIED FOR TWO DAYS AND COST HOURS. What it claimed vs what was MEASURED 2026-07-15:
> | it said | truth |
> |---|---|
> | "GEM free tier resets **DAILY**; a 429 means today's is spent" | **FALSE.** The 429 says *"prepayment credits are depleted"* = **billing state**, not quota. Google: *"Your projects aren't automatically downgraded to the Free Tier."* **It stops DEAD and never returns at midnight.** |
> | "$300 Vertex credit, **expires 2026-10-10**, projected waste **$299**" | **FALSE.** That billing account (`0142FE-…`) **NEVER HELD A CREDIT**. `bts_vertex.py` was charging a **real card** (~$1) while every docstring claimed otherwise. The "$299 waste" was an unmeasured $300 divided by `vertex_usage.json`'s **own token arithmetic**. |
> | "flash-lite ~1000/day · flash ~250/day · pro ~100/day" | **UNVERIFIABLE.** Google **no longer publishes** numbers — `docs/rate-limits` links an *authenticated* dashboard. Measured here: `gemini-flash-latest` **429'd after ~18 calls**. |

**Lesson:**
> **THE LESSON, and it is about this file:** the ROLD is **NOT a truth source**. This table is what the
> `free-tier-allotment-check` scheduled task read at 02:05 on 2026-07-15, and it dutifully reported a
> **$299 phantom** on an account with no credit. **Read the routine, then VERIFY the routine.**

*(source: ROLD "THE RAILS")*

---

## S-18 · 2026-07-15 · `[K-96]` — a mislabelled fit parameter, and a pointer that called it "THE ONE GATE" for three days after it was resolved

> ### ✅ `[K-96]` IS CLOSED. IT IS NOT A GATE. STOP LOOKING FOR IT.
> This pointer said *"THE ONE GATE: [K-96]"* for three days **after handoff `12d` recorded it resolved**,
> and CLAUDE.md said the same. **Corrected 2026-07-15.**
> The "96 meV edge width" was the fitted **Fermi-Dirac kT parameter**, mislabelled *"edge width"* by
> `ch4f5_theory_figs_2026-07-06.py` **line 148**. Reproduced exactly: **w = 96.5 meV** → true 10–90%
> width **424 meV**. The gold scan is sound, the sample was at ambient, nothing in the data is wrong.
> Full write-up: `PhD2_DATA_ARCHIVE/00_WORKING/CH4_K96_RESOLVED_2026-07-12.md`.

**Lesson:**
> **⚠ THE LESSON: `c` was superseded by `d` and the pointer never moved.** A pointer that is not updated
> is a pointer that lies. Check the newest `00_NEXT_SESSION_HANDOFF_*` on disk, not the one named here.

*(source: ROLD; CLAUDE.md)*

---

## S-19 · 2026-07-15 · `bts_identity.py` shipped and appeared in NO index — the exact failure the TOOLS INDEX was created to prevent

> **No generator exists.** So obeying the instruction meant editing the JSON while the index silently
> froze — which is precisely how `bts_identity.py` shipped 07-15 and appeared in **no index**, the very
> failure the TOOLS INDEX was created to prevent.

*(source: ROLD "Classes discovered", 2026-07-16 item 3)*

---

## S-20 · 2026-07-15/16 · Hardware and network topology was an item class with no home in any checklist

> 1. **HARDWARE/NETWORK TOPOLOGY is an item class and was NOT on the checklist.** This session produced a
>    full measured truth table (board, M.2 occupancy, every drive, WAN up/down, LAN subnet + DHCP pool,
>    every router's USB/firmware status) — none of which had a home. **→ TidyUP must now sweep hardware
>    and network findings into the handoff + a `project_hardware_truth_*` memory.** Rule: *measured on
>    this box, or a vendor datasheet — never recalled.*

*(source: ROLD "Classes discovered", 2026-07-15/16)*

---

## S-21 · 2026-07-15/16 · Proposed moving 105 GB to fix a bottleneck that was somewhere else — Keith caught three of these, I caught none

> 2. 🔴 **PRICE THE BOTTLENECK BEFORE MOVING THE DATA.** I proposed moving 105 GB of ODX to the NVMe
>    because 67 MB/s "looked slow." **Keith killed it:** OneDrive is WAN-bound at 4.46 MB/s — D: is
>    **15× faster than ODX can ever upload**, so the move changes NOTHING. He caught two more the same
>    way ("D: is slow" — D: at 67 BEATS the 37.75 WAN download; "Firebox VPN 35 Mbps is slow" — his
>    upload IS 35.67). **Compare a device to WHAT ACTUALLY FEEDS IT, not to the fastest device in the
>    room.** I caught none of the three. See `project_hardware_truth_2026-07-15`.

*(source: ROLD "Classes discovered", 2026-07-15/16)*

---

## S-22 · 2026-07-15/16 · TidyUP2 produced two false alarms out of four checks

> 3. ⚠ **A VERIFIER THAT CRIES WOLF IS THE SAME BUG CLASS AS THE FUSE MOUNT.** TidyUP2 this session
>    produced **two false alarms out of four checks**: (a) a `.bat` `if exist` reported the memory file
>    MISSING — it was there, the check misfired on a 221-char path; (b) a grep for `READ FIRST` found
>    "4 pointers, 3 stale" — they were under `### Prior pointer (date)` headings, i.e. the **archive,
>    correctly labelled**. Both = **claiming before reading**, the exact failure `feedback_do_the_homework`
>    names. **→ A T2 check that FAILS must be confirmed host-side with `Read` before it is reported as a
>    finding.** Same rule as the mount: *a tool's failure is not evidence of a defect.*

*(source: ROLD "Classes discovered", 2026-07-15/16)*

---

## S-23 · 2026-07-16 · GEM named the right Google service but invented the path — a 404

> - ⚠ **VERIFY THEIR URLS/DOIS — never ship them.** 2026-07-16: GEM named the right Google service but
>   the WRONG PATH (404); the real one was a `:customMethod`. **401 vs 404 is the test.** Crossref for
>   DOIs, always (207 ms, free, cannot fabricate).

And, from CLAUDE.md:

> ⚠ **Verify every URL/DOI they hand back** (2026-07-16: GEM's billing endpoint 404'd — right service,
> invented path; **401-vs-404 is the test**, and it FALSE-POSITIVES when the auth is bad — the
> **discovery doc** is the only authority on whether an endpoint exists). Crossref for DOIs, always.

*(source: ROLD THE THREE RULES, Rule 1; CLAUDE.md)*

---

## S-24 · 2026-07-16 · Vertex billed 28.5× the visible output — and $0.0296 was paid for a question the free lane answers

> **MEASURED 2026-07-16 — the API punishes exactly what we want GEM for:** one 3-sentence Vertex
> answer returned `in=18 · out=101 · thoughtsTokenCount=2883` ⇒ **thinking_ratio 28.5×**, $0.0299 for
> three sentences — **~97% of the bill was reasoning we never saw.** Google bills thinking AT THE
> OUTPUT RATE ($10/1M on pro). **Over the DOM that same thinking is FREE.**
> ⇒ **ROUTING RULE:** reasoning-heavy / open-ended / bulk → **BTS-DOM (free)**. Short, structured,
>   scriptable, or needs-to-be-in-a-file-now → API. **The API is the FALLBACK, not the default.**
>   `SURFACE_POLICY.md`'s ladder already said BTS *before* paid API — 2026-07-16 I skipped that rung
>   and paid $0.0296 for a docs question the free lane answers.

*(source: ROLD THE THREE RULES, Rule 1)*

---

## S-25 · 2026-07-16 · A PUBLISH IS NOT A SYNC — the public mirror served a 15-day-old file and every verify returned 200

> 1. 🔴 **A PUBLISH IS NOT A SYNC. Cloud-verify must diff CONTENT, not expect HTTP 200.**
>    `ai.dchambers.com` served a **2026-07-01** copy of `00_FOLDER_ACCESS_RECORD.md` for **15 days**. The
>    publish bat was never broken — **the MIRROR step was.** This file and the access record had not been
>    copied into `PhD2_DATA_ARCHIVE\00_WORKING\` since 07-01/07-06, so *every* publish that ran (incl.
>    07-13's) **faithfully republished a stale file and returned 200**. TidyUP step 5's "cloud-verify ≥1
>    new file by fetch" passed every time and proved nothing. **→ Step 5 must (a) run the MIRROR first,
>    (b) verify live↔mirror by MD5 with a negative control, (c) fetch and confirm the SERVED BYTES contain
>    something written this session.** Recipe: `BTS_MESH\_tidy_0716b.bat`.

*(source: ROLD "Classes discovered", 2026-07-16)*

---

## S-26 · 2026-07-16 · The sandbox held the ONLY copy of a delivered 2.7 MB deliverable's builder

> 2. **SANDBOX SWEEP (T2-6) IS NOT BOOKKEEPING — it caught a real loss on its first real run.**
>    `/tmp/build` held the **only** copy of `build.js` + 12 `figs*.py` + 21 PNGs that produced the
>    delivered `JMESH_TRAIN_S1_FIREBOX_2026-07-15.docx` (proved by `out.docx` = 2,696,439 bytes =
>    the delivered file, byte for byte). A sandbox wipe would have left a 2.7 MB deliverable that could
>    never be regenerated or corrected. **→ Any session that BUILDS a deliverable in the sandbox must
>    copy the BUILDER + FIGURE SCRIPTS to the archive beside the output, and MD5-verify host-side** (the
>    FUSE `cp` is the exact operation known to corrupt). Rescued to `BTS_MESH\JMESH_TRAIN_S1_build_provenance\`.

*(source: ROLD "Classes discovered", 2026-07-16)*

---

## S-27 · 2026-07-16 · `TOOLS_REGISTRY.json` claimed a generator that does not exist, so obeying it froze the index

> 3. ⚠ **A DOC THAT CLAIMS TO BE GENERATED MUST HAVE A GENERATOR ON DISK — VERIFY, DON'T BELIEVE.**
>    `TOOLS_REGISTRY.json` said *"00_TOOLS_INDEX.md is generated from it — do not hand-maintain, edit HERE."*
>    **No generator exists.** So obeying the instruction meant editing the JSON while the index silently
>    froze — which is precisely how `bts_identity.py` shipped 07-15 and appeared in **no index**, the very
>    failure the TOOLS INDEX was created to prevent. **→ TidyUP2 check 8 (living docs) must confirm that
>    any "generated from X" claim names a real generator; a false claim is worse than no claim, because it
>    tells the next reader to skip the file that actually matters.** Both files corrected 2026-07-16.

*(source: ROLD "Classes discovered", 2026-07-16)*

---

## S-28 · 2026-07-17 · MOUNT HIT #11 — the mount lied about SIZE: under-reported by 39,584 bytes, and a divergence check returned a clean, specific, garbage answer

> **#11 — it lied about SIZE, not just content.** Comparing D: vs V: through the mount, `jack_command.html`
> read **198,146 B** on D:. Host-side robocopy: **237,730 B**. **Under-reported by 39,584.** `CLAUDE.md`
> under-reported by 2,940 the same way. **I ran the divergence check THROUGH the mount — the thing these
> rules forbid — and it returned a clean, specific list of 9 files. It was garbage. Nothing errored.**
> The only tell was an impossible arithmetic: **a copy larger than its source.**

*(source: CLAUDE.md, HITS #11 AND #12)*

---

## S-29 · 2026-07-17 · MOUNT HIT #12 — a FALSE SyntaxError at line 106 nearly ate `bts_paths.py`, the resolver everything depends on

> **#12 — a FALSE SyntaxError in `bts_paths.py`, the resolver everything depends on.** The sandbox reported
> `SyntaxError: '(' was never closed` at **line 106**. Host `Read` shows 106-107 is **perfectly valid** —
> the paren closes on 107. **The mount served the file TRUNCATED AT 106**, so python never saw the next line.
> **"Unclosed paren at the last line" IS the truncation signature.** This is exactly the `bts_gdx.py` missing
> colon, and I was one edit away from "fixing" a healthy file and destroying the resolver at session end.

**Lesson:**
> ⇒ **THE SANDBOX CANNOT VERIFY A FILE IT CANNOT READ.** When it reports a defect in a file you just
> touched, that is not evidence you broke it. Read it host-side. `Desktop\VERIFY_BTS_PATHS.bat` is the
> functional proof, run where the bytes are real.

*(source: CLAUDE.md, HITS #11 AND #12)*

---

## S-30 · 2026-07-17 · The migration's code/history split ate the file that exists to survive the sweep

> 1. 🔴 **THE CODE/HISTORY SPLIT WAS DRAWN AT THE FILE LEVEL. FILES ARE BOTH.**
>    The migration doc's §2 says CODE→rewrite, HISTORY→preserve. But **docstrings and comments ARE history
>    living inside code.** `.py` classified as code, so `_migrate_step3_paths.py` rewrote the prose too —
>    turning true statements about the past into false ones. **`bts_paths.py` ended up claiming
>    *"V:\Research4 was hardcoded 1,961 times"*. V: did not exist then. THE SWEEP ATE THE FILE THAT EXISTS
>    TO SURVIVE THE SWEEP**, and destroyed its fallback ladder (`["V:\Research4","V:\Research4"]` — same
>    path twice). **105 code files were rewritten; ONE was checked.** → **Any path-rewriting tool must skip
>    prose or be told to. Any past-tense comment naming `V:\Research4` is suspect.**

*(source: ROLD "Classes discovered", 2026-07-17)*

---

## S-31 · 2026-07-17 · A handoff recorded `backup_to_onedrive.py` as "Patched." It was not — on either tree

> 2. 🔴 **A HANDOFF THAT RECORDS A FIX NOBODY VERIFIED IS WORSE THAN ONE THAT RECORDS THE BUG.**
>    §4c of the migration doc said `backup_to_onedrive.py` was **"Patched."** **It was not — on either tree.**
>    The step-3 sweep skipped it silently (`except Exception: continue` on a cp1252 read), §4c correctly
>    caught the skip, and then claimed a fix that was never applied. Had it stood, the rename would have
>    pointed **the BACKUP** at a dead path — failing in the one direction nobody notices, because a backup's
>    success is invisible until you need it. → **`feedback_agent_verification` applies to MY dones. Grep the
>    fix back before writing "Patched."** A false DONE stops the next reader from looking.

*(source: ROLD "Classes discovered", 2026-07-17)*

---

## S-32 · 2026-07-17 · A migration rewrote a broken path into a differently-broken one; `Win32_SystemSlot` reported all 7 PCIe slots free including the one holding the GPU

> 3. ⚠ **A MIGRATION CAN REWRITE A BROKEN PATH INTO A DIFFERENTLY-BROKEN ONE.**
>    `phd-work-driver-7min` pointed at `D:\Research2\Ai\R2clone\Publish-to-R2_KEYED.bat` — **already wrong
>    before the migration**; the bat lives at `D:\R2Cloner\`, a separate top-level dir that never moved. A
>    sweep faithfully rewrites the prefix and preserves the error. → **Before rewriting a path, check the
>    path was ever correct.** Also: **`Win32_SystemSlot` is useless** (reported all 7 PCIe slots "Available"
>    including the one holding the GPU) — same class as a FUSE read: clean, specific, wrong, no error.

*(source: ROLD "Classes discovered", 2026-07-17)*

---

## S-33 · 2026-07-17 · SGH fabricated the Au 5d citation `10.1002/adma.201906478` — and five documents then spent four days telling the next session to "replace" a citation that was never inserted

> 3. ✅ **SGH's Au 5d citation — CLOSED-OUT 2026-07-17. THE GUARD WORKED; THE TODO WAS THE BUG.**
>    `10.1002/adma.201906478` is Stofela et al., *Adv. Mater.* **32** (2020) — hot-carrier plasmonics, not a
>    gold valence-band BE reference. Crossref falsified it in **207 ms**; the grounded SGH call cost **$1.32**.
>    **It has ZERO hits in the v3 docx — it never entered the chapter.** "Replace it" was therefore wrong for
>    four days across five files. **Nothing to replace.** The actual gap: §4.3's 5d falling-edge claim
>    (**2.32 ± 0.05 eV, n = 6**) is **UNCITED**.
>    **And "grep the local library first" was RIGHT — the answer was already in it.** `00_DOI_INDEX.md` #25
>    already pointed to **#8 = Lindau 1976** (`10.1103/PhysRevB.13.492`), polycrystalline Au, acquired by
>    Keith **07-14**, digitized the same day → `00_WORKING\ch4_verify\lit\`. **The instruction was followed
>    and its output was never read.** That is the TOOLS_INDEX failure wearing a citation costume.
>    ⚠ **Lindau's `5d₅/₂ = 2.96 ± 0.03 eV` is a PEAK MAXIMUM. 2.32 is an EDGE. Do not equate them.**

*(source: ROLD "CH4 — WHAT IS ACTUALLY OWED"; corroborated in CLAUDE.md)*

---

## S-34 · 2026-07-19 · A node's DOI can be REAL while its title is FABRICATED

> 1. 🔴 **A NODE'S DOI CAN BE REAL WHILE ITS TITLE IS FABRICATED.** GEM/SGH handed back `10.1103/PhysRevB.20.4126`
>    (real) under the invented title *"Fano-type-resonance behavior…"* (真 = "Energy dependence of 3d,4d,5d,4f
>    partial cross sections") and `10.1103/PhysRevLett.42.801` (real) mis-titled + wrong sample class. Crossref
>    "the DOI resolves" is **necessary but NOT sufficient** — verify TITLE + AUTHORS + sample class match the
>    claim, not just that the identifier exists. (One DOI was also fully fabricated: Abbati PRB 16,5472 → GEM
>    conceded UNKNOWN.) → TidyUP2 citation checks must diff the *title*, not only ping the DOI. See
>    [[feedback_agent_verification]].

*(source: ROLD "Classes discovered", 2026-07-19)*

---

## S-35 · 2026-07-19 · A sub-agent cannot read its host/parent session's transcript

> 2. 🔴 **A SUB-AGENT CANNOT READ ITS HOST/PARENT SESSION'S TRANSCRIPT.** `session_info` lists children and the
>    user's *other* open sessions, not the parent that spawned the agent; `read_transcript` on the live session
>    returns "not found." ⇒ **ROLD step 9 (session `.md`) cannot be delegated for the CURRENT live session** —
>    it must be written by the parent, or after the session closes (the backlog-transcription-by-sub-agent
>    pattern only works for COMPLETED sessions). Do not report step 9 done from a sub-agent for the live session.

*(source: ROLD "Classes discovered", 2026-07-19)*

---

## S-36 · 2026-07-19 · An OAuth "deleted project" claim was carried forward on faith for days and was false

> 3. ⚠ **AN OAUTH "DELETED PROJECT" CLAIM DECAYS LIKE A STALE POINTER — RE-TEST, DON'T INHERIT.** The GDX project
>    was labelled "DELETED, dies ~08-14" for days, but on 2026-07-19 its OAuth client **mints tokens fine → the
>    project is ACTIVE.** The real break was the 7-day Testing-mode token fuse, a different thing. A present-tense
>    "X is dead" claim about a credential must be re-verified live (401/invalid_client for a dead client vs
>    invalid_grant for a dead token), never carried forward on faith. The ~08-14 date is now an UNVERIFIED
>    prediction, not current state.

*(source: ROLD "Classes discovered", 2026-07-19)*

---

## S-37 · 2026-07-20 · THE DATED-HANDOFF SCHEME ROTTED FOUR TIMES — the glob returned 15 files across two directories

> **Why:** the dated scheme rotted **FOUR times** (12c→12d, 12d→07-15, →07-17, and on 2026-07-20 this line
> still said `07-17` while `07-19` and `07-20` both existed) — each time directly above a warning saying it
> would. Worse, six duplicate dated handoffs also sat in `00_WORKING\`, so the old glob returned **15 files
> across two directories**, and 07-15/07-17 each existed in BOTH — two candidates for "the newest", free to
> diverge. **The warning was never the fix; the variable filename was the defect.** A fixed name at a fixed
> path is the pointer itself, not a copy of one.

Earlier instance of the same rot, recorded in place:

> **⚠ THIS LINE HAS NOW GONE STALE TWICE.** It said `12c` after `12d` existed, then said `12d` after
> `2026-07-15` existed. **Do not trust this filename — `dir Ai\00_NEXT_SESSION_HANDOFF_*` and take the
> newest.** The pointer is the least reliable thing in this file.

**Lesson:** A filename in prose is a *copy* of a pointer, and copies rot. A fixed name at a fixed path is the pointer itself.

*(source: ROLD "CURRENT POINTER"; CLAUDE.md)*

---

## S-38 · 2026-07-26 · "I called GEM and Vertex dead. They were not." — the sandbox's own egress block read as dead keys

> **1. I called GEM and Vertex dead. They were not.** Every `googleapis.com` host returned HTML 403
> from Cowork's sandbox *including keyless discovery*, which no credential fault can cause. It was the
> sandbox's egress. **GEM answered on the API from Keith's box minutes later.** The negative control
> that cracked it — hitting a keyless endpoint — cost one curl and belonged in the first sweep.

*(source: BU.MD "TWO ERRORS I MADE AND CORRECTED")*

---

## S-39 · 2026-07-26 · SANDBOX NONDETERMINISM — 23 scans over threshold / worst 4.998 eV on the first run, 7 / 3.680 on the next four. Same code, same data.

> **2. I reported the archive's own recorded numbers as "not reproducing".** `sec_prep.py` gave
> 23 scans over threshold / worst 4.998 eV on its first run and **7 / 3.680 on the next four**. Same
> code, same data, nothing changed. The first read through the mount was corrupt — and it looked
> perfectly healthy: complete table, plausible values, no errors. ⇒ **`FINDING_SANDBOX_NONDETERMINISM_2026-07-26.md`**
> ⚠ **`scripts_2026-07-20/` produced the current Ch4 figures and ran in that same environment. Re-run
> and diff before Ch4 is frozen.** Mechanical, cheap now, expensive after submission.

*(source: BU.MD "TWO ERRORS I MADE AND CORRECTED")*

---

## S-40 · 2026-07-26 · "VERTEX DEAD" was recorded THREE TIMES on the strength of a wrong auth header

> `bts_vertex.py` sends **`x-goog-api-key`**, the canonical header for a Google API key. My probe sent
> `Authorization: Bearer`. Google answered truthfully — *"Expected OAuth 2 access token"* — and I
> recorded **"VERTEX DEAD"** in two reports and nearly rewrote a working rail on the strength of it.
>
> Measured, all three styles, same key, same endpoint:
>
> ```
> Authorization: Bearer  -> 401        ?key=  -> 200        x-goog-api-key -> 200   [production]
> ```

**Lesson:**
> **A monitor that exercises a rail differently from the way production exercises it does not
> measure the rail. It measures the monitor.**
>
> This is the **third** instance of one error class in a single session — the sandbox egress block
> read as dead keys, a corrupt mount read as bad archive data, and now a wrong auth header read as a
> dead rail. **A tool's failure is not evidence about the thing the tool was pointed at.** Every one
> was caught by a cheap control (a keyless endpoint, a second run, a second auth style) that should
> have been in the first sweep.

*(source: BU.MD "VERTEX WAS NEVER BROKEN, AND I SAID IT WAS — THREE TIMES")*

---

## S-41 · 2026-07-26 · The rail check's own first run cried wolf — the probe truncated the model list at 400 bytes

> Also fixed: the check's own first run cried wolf, reporting `grok-build-0.1` MISSING because the
> probe truncated the model list at 400 bytes. **A daily alarm that cries wolf gets muted, and a muted
> alarm is exactly how the task it replaced became seven days of ignored noise.**
> `_vertex_auth_probe.py` and `fix_rails.py` are kept as the evidence.

*(source: BU.MD)*

---

## S-42 · 2026-07-26 · The daily rail-health task was blind for seven days because its connected-folder set is not a file anyone can edit

> **The rail check no longer needs a mount.** The Cowork task `free-tier-allotment-check` was blind for
> seven days because `V:\Research4` was not in its connected-folder set, and that set is not a file
> anyone can edit — only `SKILL.md` exists on disk. So the dependency was removed instead:
> `BTS_MESH\rail_check.py` + `RAIL_CHECK.bat` run **natively**, where `V:` is just a drive letter, and
> write to `00_WORKING\` **and** `BTS_ODX\reports\`. The old Cowork task is **disabled**.
> Running natively also fixes the deeper problem: **rails must be probed from the machine that owns
> the credentials**, or the sandbox's egress block reports live rails as dead.

*(source: BU.MD "RAILS")*

---

## S-43 · 2026-07-26 · "GDX blocked, needs re-auth" was too broad — one of three paths was down and I wrote it as all three

> **"GDX blocked, needs re-auth" was too broad and I wrote it.** Nothing Cowork does is waiting on
> it. The re-auth still matters because `bts_gdx.py` is what SGH and GW would use — but it is a
> chore for scripts, not a blocker for the mesh. Permanent fix stays `drive.file` scope + publish to
> Production; Testing mode is *why* it expires every 7 days.

Also recorded in the same block:

> - ⚠ **204 GW calls are unpriced**, so `$3.4593 / $10.00` **understates** true xAI spend by an
>   unknown amount. Not a ceiling check until GW is priced.

*(source: BU.MD "RAILS")*

---

## S-44 · 2026-07-26 · Every doc in the tree called GW browser-only. It was one free `GET /v1/models` away.

> **GW is an API model.** Every doc in this tree called it browser-only or a PowerShell CLI; it was one
> free `GET /v1/models` away the whole time. **Probe before you plan.**
>
> DOM lesson: a **multi-line markdown paste is mangled** in the Gemini input; the *same length* as a
> single paragraph lands intact. Format, not size.

*(source: BU.MD)*

---

## S-45 · 2026-07-27 · A literature sweep run without a verification step had a 100% citation failure rate

> 🔴 **THE VERIFICATION GATE IS NOT CEREMONY — measured 2026-07-27.**
> The same literature sweep was first run through a model with no verification step. It returned ten
> DOIs: **five did not resolve at all, and all five that DID resolve pointed at unrelated papers** —
> "Screening of a Fixed Charge in the Electron Liquid" offered as Michaelson's work-function
> compilation. Its **Au 5d₅/₂ = 84.00 eV and 5d₃/₂ = 87.65 eV are the Au 4f CORE levels**, ~81 eV
> away from the valence band it was asked about. **A 100% citation failure rate**, in output that
> read as confident and perfectly formatted. None of it reached the file, because a DOI is checkable
> and a title match is checkable. Do this mechanically, never by reading carefully.

*(source: BU.MD "The reference library")*

---

## S-46 · 2026-07-27 · Five defects the headless GUI suite caught that no linter could — including 2 eV lost between the screen and the arithmetic

> 1. **The displayed bias never reached Φ.** `_load` pushed the seeded voltage to the slider only.
>    `setValue` to the value already held emits nothing, so on any scan opening at its recorded bias
>    the ruling kept `v_applied = None` and Φ was computed with **V = 0 while the panel displayed
>    "+2.00 V (ratified)" beside it.** Screen and arithmetic disagreeing, silently, by exactly the
>    2 eV the feature exists to stop losing. **Persist first, then display.**
> 2. **`ROOT = r"V:\Research4"` returned 0 scans and 0 problems** off Windows. Clean, silent, wholly
>    wrong — the house failure shape. Now resolved by `_find_root()` (env → walk up → known mounts).
> 3. **The exported PNG cropped its own title**, which is where hv and the bias live. `ImageExporter`
>    on the `PlotItem` clips; on the `scene()` it does not.
> 4. **Eight ITO reference labels printed horizontally over each other into mush.** Labels now render
>    *along* the line and the work-function family collapses to one band.
> 5. `bts_gem` crashed on **every** Vertex call: AI Studio returns `tokens` as an int, Vertex as a
>    **dict**, and `int(dict)` raised in the *accounting* step — after a successful API call. GEM has
>    been reported dead for a bookkeeping reason. Same false-negative class as the Vertex 401 header.

*(source: BU.MD "Defects the headless GUI suite caught that no linter could — 2026-07-27")*

---

## S-47 · 2026-07-27 · The outside review found real physics bugs while 143 tests and 26 invariants were green — `binding_energy()` omitted the bias

> 1. **`binding_energy()` OMITTED THE BIAS.** `BE = (hv − E_an) − KE`, missing `+ V`. A biased sample
>    hands every electron V more kinetic energy, so E_F is measured at `hv − E_an + V`. Dropping V
>    shifts **the entire binding-energy scale** — core levels, VBM, IP, every reference mark — while
>    **Φ stays perfectly correct**, because Φ carries its own bias term. Everything wrong together,
>    by the same amount, looking self-consistent. **143 tests and 26 invariants were green**; the
>    round-trip test passed because BOTH directions dropped V. Fixed, with the negative control that
>    fires on the old code (E_F would read −2.00 eV instead of 0).
> 2. **`Spectrum.v_bias` returned 0.0 for a missing record** — under a docstring warning that zero
>    meant "not recorded" and was not the same as "not applied". A comment describing the hazard
>    directly above the code committing it. Now returns `None`.
> 3. **`hv = _hv(label) or 70` in the loader.** Seventy is not a neutral default — it is the *exact
>    wrong number* from the Jun-05 mistake, where the label was the scan ENDPOINT. **Four of the 64
>    scans were affected: n=9, 12, 16, 18 (Au, Feb-09 and Mar-08).** They now read UNKNOWN.
> 4. Bias in the loader defaulted to 0.0 from brittle substring rules; now the campaign audit is the
>    authority and a region tag may only say *which* scans were biased, never invent the value.

*(source: BU.MD "THE OUTSIDE REVIEW FOUND REAL PHYSICS BUGS — 2026-07-27")*

---

## S-48 · 2026-07-27 · GEM argued one finding confidently and it was simply wrong — and reported NO FINDINGS on the file holding the real bug

> ⚠ **GEM produced one confidently-argued finding that was simply wrong** (claimed
> `BiasRecord.known` returns True for `BiasRecord(2.0, UNKNOWN)` — it returns False, and a test
> already asserted it), and reported **NO FINDINGS on `physics.py`**, the file holding the real
> bug. **SGH and GW are both Grok and are NOT independent of each other.** Weigh accordingly.

*(source: BU.MD)*

---

## S-49 · 2026-07-27 · GEM's auth: two of three options dead, and the real blocker was one key in `settings.json`

> | option | result 2026-07-27 |
> |---|---|
> | 1. Sign in with Google | 🔴 `IneligibleTierError` / `UNSUPPORTED_CLIENT` — **Google has retired "Gemini Code Assist for individuals"** and points at Antigravity |
> | 2. Gemini API key | 🔴 `429 prepayment credits are depleted` — billing state, does NOT reset at midnight |
> | 3. **Vertex AI** | ✅ **works** |
>
> **The blocker was not the environment.** `%USERPROFILE%\.gemini\settings.json` stored
> `security.auth.selectedType = "oauth-personal"`, and the CLI hit the retired-tier check *before*
> reading `GOOGLE_GENAI_USE_VERTEXAI` or `.env` — so env vars appeared to do nothing. Fixed by
> rewriting that key to `vertex-ai` (`_gem_force_vertex.py`) and moving the dead OAuth creds aside.
> Credentials live in `.env` at **both** `V:\Research4\` and `Ai\BTS_MESH\` (the CLI resolves `.env`
> from cwd upward; one copy in the wrong place looks exactly like a dead rail).

*(source: BU.MD "GEM's auth — all three options tested, only one survives")*

---

## S-50 · 2026-07-27 · Six defects in the fitting layer — an unweighted Poisson fit, a `defensible` gate that passed redchi = 4,000, and four more

> * **`fit_peaks` fitted UNWEIGHTED.** Photoemission is a photon count, so the noise is Poisson;
>   unweighted least squares treats a 100-count channel as being as reliable as a 10,000-count one.
>   On a spectrum spanning four orders of magnitude the fit was determined by the tallest channels
>   and ignored the weak features carrying the physics — and every stderr and `redchi` it reported
>   was uninterpretable. Now `weights="poisson"` by default; `weights=None` still works and *says so*.
> * **`defensible` checked only "has stderrs" and "no warnings".** A fit with `redchi` = 4,000 and a
>   residual sweeping smoothly across the peak passed. Now also requires `0.2 ≤ redchi ≤ 5` (a real
>   test only once the weights are right) **and an unstructured residual** — a runs test on residual
>   sign changes, which catches the one failure no scalar metric can see: close everywhere, wrong shape.
> * **Multi-peak fits defaulted every peak to the global argmax**, starting all components stacked on
>   the tallest feature. Now raises unless each peak is given a centre.
> * **`produces_negative_counts` returned `None` unconditionally** while the module computed the
>   answer on every path and threw it away into a warning string. Now real, with `n_negative`.
> * **Shirley convergence was permanently "UNVERIFIED".** True that lmfitxps does not report the
>   residual; it does not stop US measuring it — run at 5× the iteration budget and the difference
>   IS the achieved residual. Now `converged` is True/False, with a negative control at `max_iter=1`.
> * **A bad Tougaard `B` still returned an ordinary result** and `subtract_from` applied it silently.
>   "DO NOT use this background" enforced by nothing is a comment. Now `usable=False` and
>   `subtract_from` raises `UnusableBackgroundError` unless you pass `force=True`.

*(source: BU.MD "THE FITTING LAYER IS NOW DONE TOO")*

---

## S-51 · 2026-07-27 · The adversarial re-verification found the worst bug of the session — `v_applied or 0.0` reproduced the impossible Φ = 7.12 eV the archive already had a name for

> **`Ruling.phi()` ended `- (self.markers.v_applied or 0.0)`.** A bias nobody had established
> silently became zero, and on a Jun-05 ITO cutoff that returns **Φ = 7.12 eV** — *the literal
> number `campaign.py`'s own docstring memorialises as "an impossible Φ = 7.12 eV"*, one of the four
> wrong explanations that cost this archive four days. And `to_row()` wrote it into the CSV **beside
> a blank `V_applied` column**: the same row said the bias was unknown and quoted a work function
> that assumed it was zero. Two code paths, opposite policies — `window._seed` refused to compute Φ
> without a bias while the public core API did it anyway. **Now: no bias, no work function.**
>
> Also found and fixed:
> * **`window.py` fed `v_applied or 0.0` into the EVIDENCE panel.** Measured on the locked scan:
>   `range_bias` — the metric whose *entire purpose* is catching the endpoint trap via `stop = hv+V`
>   — reports **flagged=True under the coerced 0.0 and flagged=False under the true +2.00 V.** The
>   check designed to detect the assumption was being fed the assumption. Evidence is now withheld
>   entirely when no voltage is established.
> * **The R² gate could never fire.** Evaluated on the same 3 points the line was fitted through —
>   1 degree of freedom — it gave min 0.9958 / median 0.9999 over the 64 scans and **0 of 61 below
>   0.98**. Now tested over the wider linear span: **min 0.900, median 0.987, 12 of 61 below 0.98.**
> * **8 of 61 scans reported σ(foot) below 1 meV** — an artefact of a 1-dof fit, not a measurement.
>   A `step/√12` sampling floor added in quadrature; none now fall below 14 meV.
> * `Spectrum.__post_init__` was freezing **the caller's own array** (`np.asarray` returns the same
>   object), under a docstring promising raw data is never mutated. Now copies first.
> * `defensible` read an **untested** residual (`None`) as clean. Two fixes were correct *and
>   untested* — reverting them left the suite green — so both now have negative controls that were
>   proven to fail against the un-fixed code.

*(source: BU.MD "THEN AN ADVERSARIAL RE-VERIFICATION FOUND THE WORST BUG OF THE WHOLE SESSION")*

---

## S-52 · 2026-07-27 · The courier architecture was designed around an absence that `nodes/gbw.json` had already denied

> `nodes/gbw.json` has said this since before 07-14: *"Two legs — (1) chat-worker window via
> chrome-bridge, (2) **Grok Build CLI (terminal, x.ai/cli) run on Keith's machine, working directly
> on files**."* I read that file on 07-26, quoted the browser-only half, and built the courier
> architecture anyway. **SGH told Keith about these tools unprompted on 07-27 and was right.**
> The binary was at `C:\Users\Papa\.grok\bin\grok.exe` the whole time. *Check whether the thing
> exists before designing around its absence.*

*(source: BU.MD "AND IT WAS ALREADY WRITTEN DOWN")*

---

## S-53 · 2026-07-27 · THE FORGE — 204 node calls produced output that failed 3 of 4 gates, and `FORGE.bat` double-launched and was still clobbering restored files an hour later

> 5 rounds, 204 node calls, 0 rail failures, ~23 min. **Its output failed 3 of 4 gates** — 85 ruff
> errors, and `metrics.py` calling `physics.compute_spectral_width`, which does not exist. Three
> authors rewriting eleven files in isolation produced **API drift**, and two repair rounds compounded
> it. **The machine gates stopped 204 calls of confident-looking output from replacing working code.**
>
> ⇒ **The forge's value is the CRITIQUES, not the code.**
>
> **Do not re-run FORGE.bat against a live tree.** It writes into `src/`. It also *double-launched*
> once and was still clobbering restored files an hour later; `taskkill /F /IM python.exe` stopped it.
> Point it at a scratch copy, or run it for critique only.

*(source: BU.MD "THE FORGE")*

---

## S-54 · 2026-07-27 · GEM issued a FALSIFIED verdict from a premise it had itself marked [UNVERIFIED], and its predicted mechanism did not reproduce

> **Rejected after measurement:** GEM's *"lmfitxps is passive-only, do not adopt"* — `ShirleyBG` and
> `TougaardBG` are `lmfit.Model` subclasses with free parameters, so they compose and fit jointly.
> GEM issued a `FALSIFIED` verdict from a premise it had marked `[UNVERIFIED]`.
>
> ⚠ GEM predicted the degeneracy would show as `r(kt,σ) → −1`. **Measured `r = −0.004`** — the
> collapse signature fired instead. GEM's *remedy* was right and its *mechanism* did not reproduce.
> Three independent signatures are checked for exactly this reason.

*(source: BU.MD "THE FORGE")*

---

## S-55 · 2026-07-28 · COWORK FABRICATED A QUOTATION AND ATTRIBUTED IT TO GEM — and manufactured a three-way agreement that never existed. Keith caught it from a single word, two days later.

> ## 🔴🔴 RETRACTED — "THE DECISION, REACHED THREE WAYS INDEPENDENTLY" WAS NOT.
> > **Keith caught this on 2026-07-28, from a single word.** *"I thought everyone agreed a separate
> > app was 'vanity'? That word was a tell for me. How did a word like that end up in three
> > independent reviews?"* He was right, and pulling the thread found two worse things.
>
> **1. "Vanity" was MY word, planted in the prompt.** `upsjudge\SOURCING_BRIEF.md` line 52 reads:
> *"If you think a new tool is vanity, say so."* Both nodes handed it back. **Their agreement on that
> word is an echo of my framing and carries no evidential weight whatsoever.** Never put the
> conclusion's vocabulary in the question.
>
> **2. THE GEM QUOTATION WAS FABRICATED.** The text attributed to GEM above — *"Building a new
> full-stack fitting GUI is vanity… an open-source headless engine is NOT vanity"* — **appears
> nowhere in GEM's output.** `grep -c vanity` over both GEM files returns **0**. I paraphrased its
> position into my own vocabulary and set it in quotation marks. That is the same fabrication class
> this project has caught twice in outside nodes, committed here by me, in the handoff.
>
> **3. THEY DID NOT AGREE. THEY DISAGREED ON THE CENTRAL QUESTION.** What they actually wrote:
> > **SGH:** *"Contribute the SEC layer; do not build another fitting GUI… **open issues against
> > LG4X-V2 and KherveFitting offering SEC-adjudication as a plugin; if both refuse or are dead, your
> > standalone tool is justified by abandonment, not by ego.**"* — and he flagged the premise
> > **"[both UNVERIFIED — check before deciding]"**.
> > **GEM:** *"Build `upsjudge` as a headless library with a thin Qt GUI layer; **DO NOT contribute
> > directly to `LG4X-V2` or `KherveFitting`**"* — on the grounds that both are monolithic GUI
> > applications built around core-level doublet fitting and unusable as modular components.
>
> **SGH's condition was never met.** No issue was ever opened against either project; nobody checked
> whether they would take a plugin. So the standalone build proceeded on an untested premise.

And, recorded separately about how it was caught:

> **Evidence this session that the split is warranted:** rails debugging, chapter physics, library
> consolidation, OCR, and a prompt-integrity failure all shared one context. The integrity failure
> (a fabricated quotation) sat undetected for two days and was caught by Keith noticing a word, not
> by any control. A narrower context is not tidiness — it is how the checks get run at all.

**Lesson:** Never put the conclusion's vocabulary in the question. Agreement on a word you planted is
an echo of your framing and carries no evidential weight. **No control caught this — a human noticing
one word did.**

*(source: BU.MD "RETRACTED"; BU.MD "THREE STREAMS")*

---

## S-56 · 2026-07-28 · An MCP server was built that reimplemented 7 of `bts_tools.py`'s 8 verbs — the 07-13 Origin-reader failure repeated exactly, five days after the index was created to prevent it

> > 🔴 **PROVEN AGAIN 2026-07-28, AND THIS TIME BY SKIPPING THIS VERY STEP.** A session that never
> > ran BootUP! built an MCP server that **reimplemented 7 of `bts_tools.py`'s 8 verbs from
> > scratch** — `bts_tools` had existed since 07-17 and is listed in `00_TOOLS_INDEX.md`. Nobody
> > asked *"do we already have this?"*, because the routine that asks it was never run.
> > **This is the 07-13 Origin-reader failure, repeated exactly, five days after the index was
> > created to prevent it.** ⇒ *The index is not the control. Running BootUP! is the control;
> > the index is just what it reads.* Skipping BootUP! to "save time" switches it off.
> > ⚠ And `TOOLS_REGISTRY.json` was **itself stale** — `bts_tools` was never added to it. **Both
> > files are hand-maintained; no generator exists. When you add a tool, edit BOTH, same commit.**

And, from TidyUP step 4b:

> That drift is not hypothetical: `bts_identity.py` (07-15) never reached the
> index, `bts_tools.py` (07-17) never reached the registry, and on **2026-07-28 the second one cost
> a whole rebuild** — an MCP server that duplicated 7 of its 8 verbs. **A tool nobody points at
> does not exist, and the next session will build it again.**

*(source: ROLD BOOT UP step 5; ROLD TIDY UP step 4b; BU.MD)*

---

## S-57 · 2026-07-28 · `bts_tools.edit(count=-1)` called `str.replace(old, new, 0)` — a silent no-op that reported success, live since 07-17

> **CONSOLIDATING IMMEDIATELY PAID FOR ITSELF — a live bug fell out of it.**
> `bts_tools.edit(count=-1)` ("replace all") called **`str.replace(old, new, 0)`, which replaces
> NOTHING**, then returned `{"replaced": n}`. **A silent no-op reporting success**, live in the
> library since 07-17. Any node that used replaceAll wrote the file back unchanged and was told it
> worked. Found the moment both surfaces were made to share one function. Fixed, with a negative
> control that fails against the old line.

*(source: BU.MD "ONE SHARED MCP FILESYSTEM SERVER")*

---

## S-58 · 2026-07-28 · `bts_tools._guard` confinement was a SUBSTRING test, so `C:/evil/tmp/x` passed

> **Also fixed in `bts_tools._guard`: confinement was a SUBSTRING test**, so `C:/evil/tmp/x`
> passed merely by containing `/tmp`. Measured, not inferred — the old expression returns True for
> that path. It is a prefix test now, with a control.

*(source: BU.MD "ONE SHARED MCP FILESYSTEM SERVER")*

---

## S-59 · 2026-07-28 · `fs_write` threw IntegrityError on every write on Windows — text-mode `open()` translates `\n` to `\r\n`

> **THE SANDBOX SUITE WAS GREEN AND WINDOWS STILL FOUND THREE BUGS. All three were OS-shaped.**
> 1. **`fs_write` threw IntegrityError on every write.** Text-mode `open()` translates `\n`→`\r\n` on
>    Windows, so the bytes on disk never matched the hash of the string passed in. **My own read-back
>    check caught it** — the check existed for corrupt mounts and caught a platform difference
>    instead. Fixed with `newline=""`; regression control added that **cannot fail on Linux**.

*(source: BU.MD "VERIFIED ON WINDOWS")*

---

## S-60 · 2026-07-28 · Grok's `config.toml` was CORRUPTED on the second wiring run — `re.sub` processes escapes in the replacement

> 2. **Grok's `config.toml` was CORRUPTED on the second wiring run** — `re.sub` processes escapes in
>    the *replacement*, so `C:\\Users` collapsed to `C:\Users` and TOML read `\U` as a unicode escape.
>    Run 1 appended (no regex) and was fine; run 2 replaced and took **grok's other MCP server down
>    with it**. Fixed with a lambda replacement. ⇒ *Idempotence is not proven by running once.*

And, on why nobody saw it:

> ⚠ **The wiring transcript was invisible for two runs** because only the probe was captured; the
> corrupted TOML was reported and nobody saw it. `WIRE_AND_PROBE.bat` now tees to `00_WORKING\MCP_WIRE.txt`.

**Lesson:** Idempotence is not proven by running once.

*(source: BU.MD "VERIFIED ON WINDOWS"; BU.MD "CLAUDE CODE INSTALLED")*

---

## S-61 · 2026-07-28 · GEM registered the MCP server but refused to START it — `security.folderTrust.enabled` defaults true and the per-server `trust` flag does not bypass it

> 3. **GEM registered the server but refused to START it** — `security.folderTrust.enabled` defaults
>    **true** and a stdio server is not launched in an untrusted folder. The per-server `"trust": true`
>    flag does **NOT** bypass it (it is gated *behind* folder trust and only suppresses tool-call
>    confirmations). Fixed by disabling folderTrust, merged into the existing `security` object.

*(source: BU.MD "VERIFIED ON WINDOWS")*

---

## S-62 · 2026-07-28 · A console in QuickEdit selection mode SUSPENDS the process, and it looks exactly like a hang. The title bar read `Select`.

> 🔴 **`JUDGE.bat` CAN FREEZE upsjudge AND IT LOOKS EXACTLY LIKE A HANG — measured 2026-07-28.**
> The app printed `loaded 64 reference scans / + 11 Jun-05 gold scans` and then nothing, for
> minutes, with no traceback. **The window title read `Select C:\Windows\system32\cmd.exe`.**
> That `Select` is Windows console QuickEdit: a stray click in the console **suspends the attached
> process** until Esc/Enter. The app was not hung, not crashed, and not broken by the new code —
> it was PAUSED by a mouse click in its own console.
> ⇒ **Launch with `UPS Judge.vbs` on the Desktop, not `JUDGE.bat`** — the .vbs leaves no console
> holding the process. Keep the bat for when you need to see the loader output.
> ⇒ *Diagnostic rule: before debugging a "hang" in a console app, read the TITLE BAR. `Select` is
> the whole answer, and it is invisible in any log because the process never got to write one.*

*(source: BU.MD; also ROLD "Classes discovered" 2026-07-28/29 item 4)*

---

## S-63 · 2026-07-28 · CoP was written off on a premise that expired — five days of a dead lane, and the "do not re-test" note was the thing keeping it dead

> 1. 🔴 **A "DO NOT RE-TEST IT" NOTE INHERITS THE LIFESPAN OF THE FACT UNDERNEATH IT.** BU.MD said
>    *"CoP — settled, stop re-testing it"* on the premise that the Copilot CLI needs a PAID plan.
>    **GitHub changed its billing model on 2026-06-01** and the CLI is included on **FREE**; the
>    measured failure was `"No authentication information found"` — a LOGIN. **Five days of a dead
>    lane, and the note was the thing keeping it dead.** ⇒ **DATE THE PREMISE.** A settled-negative
>    about a VENDOR must carry the date and the reason, and be re-checked when pricing changes.

And, in full, from BU.MD:

> ### 🔴 CoP WAS WRITTEN OFF ON A PREMISE THAT IS NOW FALSE — corrected 2026-07-28
> This file says *"CoP — settled, stop re-testing it"* because the CLI was believed to need a **paid**
> GitHub Copilot plan. **It does not.** GitHub's own install doc: *"GitHub Copilot CLI is available
> with **all Copilot plans**"* — Free included. And on **2026-06-01 Copilot moved OFF "premium
> requests" to token-metered AI Credits**, with a prepaid monthly allowance and **overage OPT-IN
> ONLY** — so there is no separate API bill unless a budget is deliberately set.
> **The measured failure was `"No authentication information found"` — that is a LOGIN, not a plan.**
> ⇒ One click tests it at $0: **`Ai\BTS_MCP\COPILOT_LOGIN_TEST.bat`**. Keith does the sign-in.
> ✅ **Still true and unchanged: M365 Premium grants NO GitHub Copilot entitlement.** Separate SKUs.
> ⚠ *The lesson is not "CoP works". It is that a "settled, do not re-test" note inherits the
> lifespan of the fact it rests on, and vendor billing models change under it. Date the premise.*

*(source: ROLD "Classes discovered" 2026-07-28/29 item 1; BU.MD)*

---

## S-64 · 2026-07-28 · A launcher that prints "LAUNCHED" is not evidence anything launched — `FANOUT_UI.bat` v1: neither node ran

> 2. 🔴 **A LAUNCHER THAT PRINTS "LAUNCHED" IS NOT EVIDENCE ANYTHING LAUNCHED.** `FANOUT_UI.bat` v1
>    inlined each prompt as `start "GW" cmd /c "grok -p ""…"" …"`. **The doubled quotes do not
>    survive `start` + `cmd /c`**: grok parsed the word `in` as a subcommand, gemini printed its
>    help, NEITHER NODE RAN — and the bat cheerfully printed *"Both launched."* Fixed with one
>    `.bat` per node (one quoting level). ⇒ **Verify by ARTIFACT (did `proto\` fill?), never by the
>    launcher's own success message.** Same family as the monitor-vs-production auth-header scar.

*(source: ROLD "Classes discovered", 2026-07-28/29)*

---

## S-65 · 2026-07-28 · `setx PATH "%PATH%;…"` is destructive — it truncates at 1024 chars, silently

> 3. 🔴 **`setx PATH "%PATH%;…"` IS DESTRUCTIVE — never use it.** It **truncates at 1024 chars**
>    (silently), and `%PATH%` at a prompt is USER+SYSTEM already joined, so writing it back to the
>    User variable **permanently duplicates the entire system PATH into the user one**. Use
>    PowerShell `[Environment]::SetEnvironmentVariable('Path', …, 'User')` — User scope only, no
>    length limit. Back the old value up first (`00_WORKING\USER_PATH_BACKUP.txt`).

*(source: ROLD "Classes discovered", 2026-07-28/29)*

---

## S-66 · 2026-07-28 · `hv_judged` was added to `to_json` and not to `from_json` — written to disk, quietly dropped on read

> 5. 🔴 **ADDING ONE FIELD TOUCHES FOUR SERIALISATION POINTS, AND MISSING ONE IS SILENT.**
>    `hv_judged` was added to `to_json` and **not** to `from_json`: written to disk, **quietly
>    dropped on read**. The file looked correct and the app forgot. Invisible to review and to the
>    UI until a reload. ⇒ **The fix is not another per-field test.** `tests/test_gui_smoke.py` now
>    walks `dataclasses.fields(Ruling)` and `(Markers)` and asserts EVERY field survives a JSON
>    round trip — so the NEXT field is covered by a test nobody has to remember to write.

*(source: ROLD "Classes discovered", 2026-07-28/29)*

---

## S-67 · 2026-07-28 · The `RULING_COLUMNS` append-only invariant was written wrong TWICE — both versions forbade the very thing append-only means

> 6. ⚠ **DO NOT OVER-SPECIFY AN APPEND-ONLY INVARIANT.** The `RULING_COLUMNS` guard was written
>    wrong TWICE — first *"hv_judged must be LAST"* (broke when `SECO_peak` was appended), then
>    *"the appended set is exactly these two"* (broke when `source_key`/`rubric_version` were).
>    **Both forbade the very thing append-only means.** Assert only: the original nine untouched
>    AND in order (downstream reads them positionally), plus no duplicate names.

*(source: ROLD "Classes discovered", 2026-07-28/29)*

---

## S-68 · 2026-07-28 · GEM reported its prototype "compiles and runs flawlessly (Exit Code: 0)" having executed only `py_compile`

> 7. ⚠ **A PARSE CHECK IS NOT A RUN — including when a NODE claims otherwise.** GEM reported its
>    prototype *"compiles and runs flawlessly (Exit Code: 0)"* having executed only `py_compile`.
>    Same standard as the false-SyntaxError scars, applied in the other direction: **functional
>    proof beats parse proof, and a node's success claim is a claim, not a measurement.**

*(source: ROLD "Classes discovered", 2026-07-28/29)*

---

## S-69 · 2026-07-28 · Bare `python` on this box is 3.13 with no pytest — and `_pyver_probe.log` had already recorded it on 07-27

> - *(Also recorded, environment-specific:)* bare `python` on this box is **3.13 and has no
>   pytest** — the split install was already in `upsjudge\_pyver_probe.log` (07-27) and I did not
>   read it first; `RUN_TESTS.bat` now pins `py -3.14`.

And, from BU.MD:

> **2. Bare `python` is 3.13 on this box and has no pytest** — it reads exactly like a broken suite
> and is a wrong interpreter. **`_pyver_probe.log` (07-27) already recorded the split install**
> (3.14 = PySide6/scipy/lmfit, 3.13 = numpy/pydrive2) and I did not read it first. `RUN_TESTS.bat`
> pins `py -3.14`. *Same class as the TOOLS_INDEX miss: the answer was on disk.*

*(source: ROLD "Classes discovered" 2026-07-28/29; BU.MD)*

---

## S-70 · 2026-07-28 · 55 LF-only line endings and 12 non-ASCII bytes in this project's `.bat` files produced measured mojibake

> **1. `RUN_TESTS.bat` failed `tests\test_launchers.py`** — 55 LF-only line endings and 12
> non-ASCII bytes. Not pedantry: those same em dashes came back as mojibake in
> `00_WORKING\MCP_WIRE.txt` (`bts-fs wiring ?`). **All four `Ai\BTS_MCP\*.bat` had it too** and are
> now ASCII+CRLF. *Any .bat this project writes must be ASCII and CRLF.*

*(source: BU.MD "TWO THINGS THE SUITE CAUGHT IN MY OWN WORK")*

---

## S-71 · 2026-07-28 · `srdata.nist.gov` returns HTTP 200 for EVERY path including nonsense — the 401-vs-404 endpoint test is useless against it

> And **`srdata.nist.gov` returns HTTP 200 for EVERY path** including
> nonsense, so the 401-vs-404 endpoint test is useless against that host — body only.

Also recorded as a probe artefact that reads as a fault and is not:

> `grok mcp doctor` prints `.mcp.json  not found` when run from anywhere other than the tree root —
> it resolves relative to cwd.

*(source: ROLD "Classes discovered" 2026-07-28/29; BU.MD)*

---

## S-72 · 2026-07-28 · A session ran four streams in one context and degraded badly by the end

> A session that touches rails, physics, tooling and prompt-discipline in one context degrades
> badly by the end — 2026-07-28 was the proof.

And:

> (2026-07-28 ran four streams in one context and degraded badly by the end — that is why.)

*(source: ROLD BOOT UP "FOUR STREAMS"; ROLD STEP 0.5)*

---

## S-73 · 2026-07-29 · Keith's screen was taken ~30 times in two days — every test run a 95-second round trip while he was working

> **NO Run dialog. NO computer-use launches. NO `cmd /k`.** Rule 2 restated as a hard boundary
> because on 2026-07-28/29 it was broken ~30 times — every test run seized his foreground for 95
> seconds while he was working. **The cost was not latency, it was interference.**

And, from BU.MD:

> **NO Run dialog. NO computer-use to launch anything. NO `cmd /k`.** This is Rule 2 stated as a
> boundary instead of a principle, because on 2026-07-28/29 I broke it perhaps thirty times — every
> test run was a 95-second round trip through his desktop while he was trying to work.

*(source: ROLD STEP -1; BU.MD)*

---

## S-74 · 2026-07-29 · The R2 publish took 16 minutes to transfer ZERO bytes — 87 rclone invocations, 970.3 s

> 🔴 **AND THE LOG ANSWERED "WHY IS R2 SLOW" WITH A NUMBER: 16 MINUTES TO TRANSFER ZERO BYTES.**
> Measured 2026-07-29: **87 separate rclone invocations**, 970.3 s total, max single pass 29.7 s,
> `Transferred: 0 B / 0 B` — nothing had changed. One pass alone: **1,061 checks / 2,180 listed in
> 5.5 s.** ⇒ The cost is **process launches × re-listing**, not bandwidth. `--fast-list` speeds ONE
> traversal; it cannot help you start rclone 87 times.

*(source: BU.MD, T2-3)*

---

## S-75 · 2026-07-29 · There are TWO `00_WORKING` directories and four bats write to the unpublished one — four reports reached nobody

> ⚠ **T2-1: THERE ARE TWO `00_WORKING` DIRECTORIES AND MY BATS WRITE TO THE UNPUBLISHED ONE.**
> `V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING` **is** `ai.dchambers.com/00_WORKING/` — that is the
> published subtree root. `V:\Research4\00_WORKING` is a DIFFERENT folder and is **not mirrored**.
> `rail_check.py` writes to the published one (correct); **`PROBE_MCP.bat`, `RUN_TESTS.bat`,
> `WIRE_AND_PROBE.bat` and `INSTALL_CLAUDE_CODE.bat` all write to the unpublished one** — so
> `MCP_PROBE.txt`, `UPSJUDGE_TESTS.txt`, `MCP_WIRE.txt` and `CLAUDE_CODE_INSTALL.txt` exist locally
> and reach nobody. Verified by fetching both: RAIL_HEALTH served, UPSJUDGE_TESTS returned empty.

*(source: BU.MD, T2-1)*

---

## S-76 · 2026-07-29 · `BU_RAILS.MD` — a live pointer to a file that was NEVER CREATED, under a stream name Keith had already killed

> ⚠ **STALE POINTER, FIXED 2026-07-29.** This line used to say the borrowing gets a line in
> **`BU_RAILS.MD`** — a file that was NEVER CREATED, under a stream name (`RAILS`) that Keith had
> already killed in favour of PLUMBING/PHYSICS/CHAPTER. One dead pointer, two ways.

*(source: ROLD BOOT UP "FOUR STREAMS")*

---

## S-77 · 2026-07-29 · ~$500 over on usage credits in one month running Fable uncapped — discipline alone did not hold

> **Two pools, and they are NOT the same thing.** Max-plan usage (5-hour + weekly windows) costs
> nothing extra — weekly sat at **17%** on 07-29. **Usage credits are the OVERFLOW pool and they are
> real money.** Keith went **~$500 over last month** running Fable uncapped; **$142 remains and is
> being SAVED deliberately** — the cap drops to ~$30/mo after this cycle. *"I don't want to spend
> those. I'm saving them for when I need them more."*
>
> - **THE GUARD IS AN ACCOUNT SETTING, NOT DISCIPLINE.** Monthly spend limit → **$0** / auto-reload
>   **OFF**, and Claude hard-stops at the plan ceiling instead of silently drawing credits. Last
>   month proves discipline alone does not hold.

*(source: BU.MD "SPEND POLICY")*

---

## S-78 · 2026-07-29 · Cowork hand-coded for a whole session with three paid rails untouched — and it felt like thrift

> - ⚠ **A PAID RAIL SITTING IDLE IS THE FAILURE, NOT THE SAVING.** Keith, 2026-07-29: *"I can't pay
>   hundreds a month for these and have you let them sit idle... I need YOU for other tasks right
>   now."* On 07-28 I hand-coded upsjudge for a whole session with three paid rails untouched. That
>   is **Rule 1 broken**, and the tell is that it *feels* like thrift.

*(source: BU.MD "SPEND POLICY")*

---

## S-79 · 2026-07-30 · A pointer relocation took four edits across three files — miss any one and BootUP silently reads stale state

> 1. 🔴 **A POINTER RELOCATION MUST BE VERIFIED FROM THE READER'S SIDE, NOT THE WRITER'S.** Moving the
>    boot pointer from `V:\Research4\BU.MD` to `V:\Ai\BU.MD` took **four edits across three files**
>    (CLAUDE.md step 3, the ROLD streams block, a redirect banner on the old file, the new file itself).
>    **Miss any one and BootUP silently reads stale state** — the identical failure mode to the dated
>    handoffs that rotted four times. ⇒ **After moving any pointer, walk the READ path: what does
>    BootUP open first, and what does that file say?** Do not audit the file you just wrote.
>    ⚠ **And two live handoffs is worse than a stale one** — the old file needs an explicit
>    *"NOT updated at TidyUP"* banner, not merely a new file elsewhere.

*(source: ROLD "Classes discovered", 2026-07-30)*

---

## S-80 · 2026-07-30 · Cowork's own session storage is walled off from Cowork — any plan depending on it reading its own transcript is unbuildable

> 2. 🔴 **COWORK'S OWN SESSION STORAGE IS WALLED OFF FROM COWORK.** `request_cowork_directory` on
>    `…\local-agent-mode-sessions` is refused by the platform; transcripts are deliberately
>    unreachable. **Any plan that depends on Cowork reading its own transcript is unbuildable** —
>    and *summarising* one into context defeats its purpose anyway. ⇒ The pattern that works:
>    **a user-run `.bat` MOVES the `.jsonl` somewhere mounted, then a script strips it on disk while
>    Cowork never reads it.** (`Desktop\MOVE Session Transcripts to Legal.bat` + `strip_transcript.py`.)

*(source: ROLD "Classes discovered", 2026-07-30)*

---

## S-81 · 2026-07-30 · The LEGAL session produced ~26 analysis documents and SENT ZERO; a request drafted 07-29 was still unfiled 07-30

> 3. 🔴 **A "DONE MEANS" DEFINITION IS A CONTROL, NOT A DESCRIPTION.** LEGAL's *"a lawyer has it or the
>    court does"* was written **because** the session produced ~26 analysis documents and **sent zero**;
>    a request drafted 07-29 was still unfiled 07-30. ⇒ **When a stream's output accumulates without
>    leaving the building, the "done" test is the wrong one — retune it to the thing that was missing.**
>    Every stream's `done means` should be re-examined against what actually failed to happen.

*(source: ROLD "Classes discovered", 2026-07-30)*

---

## S-82 · 2026-07-30 · ~8 confident errors in one domain in one session — including one that INVERTED the case theory

> 4. 🔴 **DOMAIN DEFERENCE — MEASURED, NOT POLITE.** In one session Keith corrected Cowork, and was
>    right, on: Therapeutic Life Choices' parentage · Abraxas Scientific being a CLIA lab · Metrc
>    sample destruction · the 72-month rent basis · **12A O.S. § 2A-201 (emails DO form a written
>    contract — this INVERTED the case theory)** · the labour figure · the ZIP · the 7% financing.
>    **~8 confident errors in one domain in one session.** ⇒ **On Oklahoma regulatory, UCC and
>    licensing questions, state the basis and defer; do not assert.** And **his corrections are the
>    single highest-value artifact of the session — they do not survive compaction, so write them
>    to disk the moment they are made.**

*(source: ROLD "Classes discovered", 2026-07-30)*

---

## S-83 · 2026-07-30 · `pause` is not a report — REPEATED TWICE IN ONE DAY

> ## 6.6 ⚠ SCAR — REPEATED TWICE IN ONE DAY
>
> **`pause` is not a report. Write a LOG.** The R2 publish bat (earlier 07-30) exited before writing its
> log and the failure was invisible; the transcript bat then **closed before Keith could read the screen**,
> losing the result. ⇒ **Every `.bat` opens its log file FIRST and tees everything to it**, so the outcome
> survives the window closing. Rebuild the copy bat this way.

And, restated in the live backlog:

> ⚠ **And fix the class, not the instance:** every `.bat` this repo owns **opens its log FIRST and
> tees to it** — `pause` is not a report (scar, twice in one day on 07-30).

*(source: `Ai\ROLD\00_ROLD_ARCHITECTURE.md` §6.6; `V:\Ai\Streams\PLM_TODOS.md` PLM-15)*

---

## S-84 · 2026-07-30 · Two bats failed against a VIRTUALIZED `%APPDATA%\Claude` — a folder copy returned only Electron GPU cache

> 🔴 **Claude is a PACKAGED (MSIX/Store) app. `%APPDATA%\Claude` is VIRTUALIZED and effectively empty.**
>
> ⚠ **Two bats failed against the virtual path before this was found.** A folder copy of
> `AppData\Roaming\Claude` returns **only Electron GPU cache** — no session data. The discovery tool is
> `Desktop\FIND Session Transcripts.bat` (read-only) → `V:\Ai\Legal\_transcript_search.txt`.

*(source: `Ai\ROLD\00_ROLD_ARCHITECTURE.md` §6.1)*

---

## S-85 · 2026-07-30 · `COPY Session Logs to Legal.bat` dumped 2,735 files / 1.7 GB of every session ever run into the case folder

> `Desktop\COPY Session Logs to Legal.bat` ran and pulled **2,735 files / 1.7 GB into
> `V:\Ai\Legal\_transcripts\`** — i.e. **every session ever run, of every stream, dumped inside the case
> folder.** It is not case material, it distorts any sweep of `V:\Ai\Legal`, and it must move.

*(source: `Ai\ROLD\00_ROLD_ARCHITECTURE.md` §6.2)*

---

## S-86 · 2026-07-30 · THE MONOLITH DIAGNOSIS — ROLD is a folder, not a repository. Measured.

> | Symptom | Measurement |
> |---|---|
> | `Ai\` is a flat dump | **~300 entries in one directory** — governance docs, `.bak` chains, `.zip`, `.png`, `.py`, raw `.dat` |
> | The commands file is a monolith | **`00_ROLD_COMMANDS_TidyUp_BootUp.md` = 79,533 bytes** |
> | Backup sprawl | **13 `00_AUTONOMOUS_QUEUE.md.bak_*`** · **15 `Dsrt_Citations_running.md.bak_*`** |
> | Handoff rot, already documented | 9 `00_NEXT_SESSION_HANDOFF_*` files; the dated scheme rotted **four times** before `BU.MD` fixed it |
> | Governance is indistinguishable from data | `CANONICAL_ASSUMPTIONS.md` sits beside `mar08_xy_SEC_table.csv` |
>
> **ROLD is currently a folder, not a repository.** Everything is retrievable only by knowing its name in
> advance — which is the exact failure the `BU.MD` fix was created to end, unfixed everywhere else.

*(source: `Ai\ROLD\00_ROLD_ARCHITECTURE.md` §1)*

---

*End of extraction pass 1 (S-01 … S-86, from the monolith + `CLAUDE.md` + `Research4\BU.MD`).
**Live entries continue below — this is an APPEND-ONLY file; do not close it off.**
Next number to assign: **S-89.***

## S-87 · 2026-07-30 · A `.bat` that calls `copilot` without `CALL` ENDS ITSELF, silently, mid-probe
**Measured twice, in two different bats, both times reported by Keith as "popped up and closed".**
`where copilot` returns TWO entries: `…\npm\copilot` and **`…\npm\copilot.cmd`** — the npm shim is a
BATCH FILE. In cmd.exe, invoking one batch file from another **without `call` TRANSFERS CONTROL AND
NEVER RETURNS**: the parent script simply ends. No error, no non-zero exit, no `pause`, window gone.

Both logs stop at the identical line:
```
--- 1. binary + version ---
C:\Users\Papa\AppData\Roaming\npm\copilot
C:\Users\Papa\AppData\Roaming\npm\copilot.cmd
GitHub Copilot CLI 1.0.75.
```
`FIX CoW and CoP MCP.bat` (17:25) and `PROBE CoP.bat` v1 (19:57) died at exactly the same place, and
on the first run this was misread as "the probe returned nothing" — a WRONG DIAGNOSIS that briefly
cast doubt on CoP's MCP wiring, which was never in question.

**It also explains why `VERIFY POINTERS.bat` was unaffected**: `py` is a real `.exe`, not a shim.

**Lesson:** in any `.bat`, **`CALL` every command that might resolve to a `.cmd`/`.bat`** — npm and
pip shims especially (`copilot`, `npx`, `grok`, `gemini`, `claude` if ever installed via npm).
⇒ Corollary to the "open your log FIRST" scar (S-83): **writing the log first is what made this
diagnosable at all.** The log survived the window; without it this was a ghost, twice.

## S-88 · 2026-07-30 · The pointer checker printed mojibake into its own log on the first native run
`verify_pointers.py` printed `verify_pointers  ·  root=…` and the Windows console (cp1252) rendered
the U+00B7 middot as a black diamond in `00_WORKING\POINTERS.txt`. **The run itself was correct —
`root=V:\Research4 (windows)`, resolved=103, failed=0, exit=0, GREEN** — but the transcript of it was
already corrupt on line 3. Same class as the em dashes that came back as `bts-fs wiring ?` in
`MCP_WIRE.txt` on 07-28. **Lesson: anything a Windows console will print or tee must be ASCII —
the rule already existed for `.bat` files and did not get applied to the tools they run.**

## S-89 · 2026-07-30 · "Keith signed in to CoP on 2026-07-29" was recorded as fact and is FALSE for the CLI
`V:\Research4\BU.MD` states: *"CoP Copilot CLI 1.0.75 — ✓ registered … Keith signed in 2026-07-29 on
the **FREE** plan"*, and the same file celebrates that the earlier "CoP needs a PAID plan" note had
cost five days of a dead lane. **Measured 2026-07-30 20:02, `copilot -p …`:**
```
--- 2. registration (expect: bts-fs) ---
Workspace servers:
  bts-fs (local)
--- 3. THE HANDSHAKE ---
Error: No authentication information found.
[exit=1]
```
**Registration is real. Authentication is not.** So the lane has been counted as live in the handoff
for a day on the strength of a sign-in that either never applied to the CLI, did not persist, or
expired — and nothing measured it, because `copilot mcp list` (which was the "proof") reports
REGISTRATION and never performs a handshake. The handoff itself warned about exactly this
distinction — *"Registered ≠ connected. Ask CoP to call `fs_roots` to close that gap"* — and then
the summary table above it recorded the lane as ✓ anyway.

**Lesson:** *the caveat and the claim were in the same document, and the claim won.* A lane is LIVE
only when a tool call returns data. Anything else is a status label. Same class as S-40 (VERTEX
declared dead three times on a wrong header) inverted: here a rail was declared alive on a wrong test.
⇒ Fix in `rail_check.py`: probe CoW and CoP with a real `fs_roots` call, not a registration listing.

**Also confirmed, third time in three days (S-88 class):** copilot's own error text renders as
`ΓÇó` in the log — a UTF-8 bullet through a cp1252 console. **Not our bug, but the same trap**, and
proof it hits third-party output too, so any log we tee must be treated as ASCII-only.

## S-90 · 2026-07-30 · CoPG could not connect for a day because WINDOWS TEXT-MODE STDIO ate the MCP framing
**Symptom:** `failed to initialize MCP client: connection closed: initialize response`, then
`Tools: Server failed to connect`. **Everything obvious was proven innocent first** — CoPG's
`mcp-config.json` was correct (full `Python313\python.exe` path, right args, `"tools": ["*"]`, no
`COPILOT_HOME`); that interpreter ran the server directly at **2/2 roots live, exit 0**; the server
negotiated protocol correctly (asked `2025-06-18`, echoed `2025-06-18`, supports five versions);
`notifications/initialized` was accepted and `tools/list` returned all 13 tools; and stdout was
proven to FLUSH with stdin still open, so buffering was excluded by measurement, not by argument.

**The fault was in the transport, and it was ours.** `send()` does
`sys.stdout.write(json.dumps(msg) + "\n")` on a **text-mode** stream. On Windows that rewrites every
MCP framing newline to **CRLF**. Second, and likelier fatal: `log()` wrote an em dash to stderr under
the locale encoding — **if the pipe encoding cannot represent a character the write RAISES, and a
crash inside the startup banner kills the server before it can answer `initialize`, which is
indistinguishable to the client from "connection closed".**

**THE FIX** — `_pin_stdio()` reconfigures stdin/stdout/stderr to **utf-8 with LF newlines** before the
first frame moves, and logs which streams it pinned.
**PROVEN ON WINDOWS 2026-07-30 20:42**, through CoPG, not asserted:
```
[bts-fs] stdio pinned utf-8/LF: stdin, stdout, stderr
* fs_roots (MCP: bts-fs)
OK  rw  research4   V:\Research4
OK  rw  handoff     X:\My Drive\BTS_SGH_Handoff
[copilot exit=0]
```
**⇒ ALL FOUR LANES ARE NOW LIVE — CoW · GW/SGH · GEM · CoPG.**

**Lessons, three:**
1. **This is SCAR S-59 one layer up.** That was `fs_write` throwing IntegrityError because text-mode
   `open()` did `\n`->`\r\n` to the PAYLOAD; this is the same translation applied to the FRAMING.
   The fix was the same word both times: `newline`. *When a defect recurs a layer up, the first fix
   was too narrow.*
2. **"The config is correct" is not "the connection works."** Four separate correct-looking proofs
   (config, interpreter, protocol, tool list) all passed while the lane was dead. Only an end-to-end
   call through the real client settles it.
3. **Every test I ran closed stdin immediately**, so every test flushed on exit and looked healthy.
   *A test that cannot reproduce the client's conditions is not evidence about the client.*

**⚠ Residual, fixed the same hour:** pinning stderr to UTF-8 made the mojibake *worse* on a cp437
console (`ΓÇö`, `┬╖` in `COPG_FIX.txt`) — correct bytes, wrong console. `log()` and the `fs_roots`
banner are now ASCII-only at the source, per S-88.

## S-91 · 2026-07-30 · **THE AU 5d DOI WAS NEVER FABRICATED. IT IS REAL, AND MISATTRIBUTED.** Corrects S-33.
Building the three-lineage citation checker, I wrote its negative control asserting that
`10.1002/adma.201906478` would FAIL, because this project's record has called it a **fabricated**
citation since 2026-07-17. **The selftest failed — and the instrument was right.**
```
PASS  10.1002/adma.201906478   3 lineages agree ·
      "a noble transition alloy excels at hot carrier generation in the near infrared"
```
It resolves in **Crossref, OpenAlex and Semantic Scholar**. It is a genuine *Advanced Materials*
paper — **about something else entirely.** The node did not invent an identifier. It attached a real
identifier to a claim the paper does not support.

**This is a WORSE failure class than fabrication, and the whole citation-checking industry passes
it.** Every existence check in the world — ours, `xRef`, CiteMe, Citely, the CourtListener-based
legal tools — resolves this DOI and reports it green. **Only reading the source catches it.** That is
precisely the gap Clearbrief sells against in law ("does the cited document support this claim"),
and it is why an existence check must never be described as verifying a citation.

**Three corrections to the record follow:**
1. **S-33 is mislabelled.** "SGH fabricated a DOI" is false. Say **MISATTRIBUTED**. The catch was
   still correct and still valuable — the citation never entered the chapter — but the diagnosis
   was wrong for thirteen days, and the wrong diagnosis teaches the wrong control.
2. **The 'fabricated DOI' framing made us over-trust existence checking.** We reached for the
   control that would NOT have caught our actual failure.
3. **The strongest available check is the quote/claim-support check**, and we do not have one.
   For the chapter it is mechanical: we hold the digitised PDFs — search the source for the claim.

**Lesson:** *the negative control was written to confirm the record, and it refuted the record
instead. That is what a negative control is for.* A test that can only agree with you is not a test.

## S-92 · 2026-07-30 · The citation checker reported two REAL DOIs as non-existent — a timeout read as a 404
First live run over 63 DOIs from `00_DOI_INDEX.md`: `10.1002/anie.201302396` and
`10.1016/j.elspec.2017.05.008` came back **FAIL — "authority does not resolve it"**. Both are real.
`_get()` collapsed *timed out* and *does not exist* into the same `False`.

**The tell was in the tool's own output**: it printed *"but OPENALEX/S2 claims it exists"* on both
lines. A citation present in two independent indices and absent from the registry is possible but
rare; two of them in one run is a network story, not a bibliography story.
Fixed: 404 is a verdict, unreachable is **NOT MEASURED**, with retry/backoff on 429/5xx.
**Re-run: 63 checked, 63 PASS, 0 FAIL.**

**Lesson:** *a test that cannot tell "no" from "no answer" does not discriminate — and by the root
principle, a test that does not discriminate has not been run.* This is the same class as the
registry that returns HTTP 200 for every path, and the same class as reporting a rail dead from an
egress-blocked sandbox (S-40).

## S-93 · 2026-07-30 · "We have no claim-support check" was WRONG — one was built, used once, and abandoned
S-91 states *"the strongest available check is the quote/claim-support check, and we do not have
one."* **Keith corrected this within the hour, and he was right.** A search found:

**`00_WORKING\CH5_CITATION_QUOTES_ROLD_2026-07-05.md` — 62 KB · 96 claim–citekey pairs · 69 citekeys**,
in a structure that is exactly the right one:
```
CLAIM  ...        QUOTE  "<verbatim from the paper>"        LOC  pp. 1084-1085        VERDICT  SUPPORTS
```
Verdict distribution: **SUPPORTS 66 · PARTIAL 22 · NOT LOCATED 8 · CONTRADICTS 0.** Page-anchored,
verbatim, and the only file in the tree carrying that structure.

**Its state:** built **2026-07-05 by four parallel extraction agents** over `pdftotext` sidecars in
`+Papers\_txt\`, **for Chapter 5 only**, and never touched again. **No Ch4 equivalent exists. The
`_txt\` sidecar directory no longer exists.** A correction to one of its entries (`okudaira1998`
"SOURCE NOT HELD" — false) was written into *other* files and never back into this one.

**Three separate errors on my part, worth separating:**
1. **I said we had nothing.** We had the artefact, the schema, and 96 worked examples.
2. **I looked in the wrong place.** `verify_citations.py`, `dsrt_tools\`, `TOOLS_INDEX` — the
   built thing was a DOCUMENT, not a script, so no tool search could ever have found it.
   *The TOOLS_INDEX has no equivalent for one-off artefacts, and this is what that gap costs.*
3. **There is no tool** — that part of S-91 stands. It was agents plus a sidecar directory, run once.
   **Keith remembers a tool because the OUTPUT looks like one.** An unrepeatable process that
   produces a good artefact is indistinguishable from a tool until you try to run it again.

⇒ **The work is not "build a claim-support check." It is: generalise a schema we already proved,
automate its production, and extend it to Ch4.** That is a much smaller job, and it starts from 96
worked examples rather than from nothing.
⇒ ⚠ **`SGH_returns\BTS-R7_SGH_CH4redraft_citations_2026-07-06.csv` has an `excerpt` column** — but it
is a NODE asserting a quote, with no page locator and one column-shifted row. **That is the input to
a check, never the check.** `DOM_OUTBOX.md` T014 is parked for exactly this reason: *"a request for
an exact quote + page. An ungrounded node will confabulate it."*

## S-94 · 2026-07-30 · A RENAME IS CHEAP IN THE TREE AND EXPENSIVE IN THE WIRING. Name it right first.
**Keith's lesson, stated after the fact:** *"The lesson here is pick better names to start with."*

`bts-fs` -> `BFast` touched 47 references across 13 files in the tree — trivial, all mechanical. Then
it hit the part that is not in the tree: **five client configs across four vendors.** The rewire ran,
the 67-test gate passed, every lane saw the new name — **and every lane also kept the old one:**
```
CoW    bts-fs (Python313) Connected   +   BFast (Python314) Connected
GW     bts-fs                          +   BFast
CoPG   user scope: bts-fs              +   workspace scope: BFast
```
**One server, two names, two interpreters, two scopes.** Every model is then shown **26 tools where
there are 13** — on every call, forever — and *"which process wrote this file"* stops having one
answer, which is the only question the audit log exists to answer.

Removing the old key is not symmetrical with adding it: the JSON clients are a one-line `pop`, but
Grok's config is TOML and **the last regex that touched it took grok's OTHER server down (S-60)**. So
the cleanup needed its own script, its own line-based (non-regex) removal, and its own negative
control asserting an unrelated server survives byte-identically — `Ai\BTS_MCP\drop_old_mcp_key.py`.

**⇒ THE RULE. Before a name is wired into anything, spend the ten minutes.**
Say it aloud. Check what it reads as. Check the redundancy (`bts-fs` rendered to models as
`bts-fs-fs_roots` — "fs" twice, on every call). **A name that is only in your own files is free to
change. A name that has been handed to four vendors' config files is a migration.**
⚠ And the corollary, learned the same day: **the deprecation is a separate, riskier job than the
rename** — plan both, or the rename lands and the duplicate stays forever because nobody budgeted
for the removal.

## S-95 · 2026-07-30 · A CHORE WE AUTOMATED, MANAGED AND SCHEDULED AROUND FOR WEEKS DID NOT NEED TO EXIST
`gdx-token-watch` ran **every Friday**. `rail_check` refreshed the token **on every launch**. The
backlog carried "kill the GDX 7-day fuse" as a standing PLUMBING item with a designed fix
(`drive.file` + publish to Production). **All of it was managing the auth of a tool nobody needed.**

The fuse affected exactly one consumer — `bts_gdx.py`'s OAuth. Three routes to the same folder were
already live and expiry-free: the Drive MCP connector, `X:` as a drive letter, and (as of tonight)
BFast's `handoff` root. **Every node is on this machine.** A folder that is already a drive letter
does not need a network protocol to reach it.

Four fixes were designed and priced before that was noticed, and each died on its own merits —
`drive.file` hides files it did not create · `/auth/drive` is RESTRICTED and needs an annual security
assessment · service-account keys are blocked by org policy · gcloud's ADC client is refused the
Drive scope outright. **Four dead ends is a signal, not bad luck.**

**Lesson:** *before automating a recurring chore, ask what breaks if the thing generating it is
DELETED.* We asked "how do we keep this token alive" for weeks and never once asked "who is still
calling this?" A weekly task and a per-launch refresh made the chore cheap enough to stop noticing —
**automation is how a pointless task survives.**
⚠ **And date the premise:** this closure rests on *"all nodes are local, 2026-07-30."* It reopens the
day one is not. Remote access to KMesh is TABLED, not refused.

## S-96 · 2026-07-31 · The recovery mirror cooked itself under two routers, and the slide took 18 days unnoticed
**Measured, in this order:**
```
2026-07-13  G: write 17.7 MB/s   (native bench)
2026-07-31  G: write  0.6 MB/s   (native bench)   — 29x slower
2026-07-31  G: write  5.7 MB/s   (sandbox, 8 MB, fsync'd; read 203 MB/s; SHA-256 matched)
2026-07-31  Keith moved the drive's OWN cable to a different port (the printer's), and moved the
            PRINTER to the drive's old port. It did not re-enumerate; "USB device has malfunctioned".
            ⚠ It did NOT drop spontaneously. ⚠ The CABLE was NOT changed - see corrections.
2026-07-31  Keith: enclosure "very hot", ~105-110F case exterior. TWO ROUTERS SITTING ON TOP OF IT,
            cover closed. Routers removed, cover opened, enclosure powered off.
```
**Reads survived throughout; writes collapsed.** That asymmetry is the tell: writes draw more current
and generate more heat, and both drives and USB-SATA bridge chips throttle or retry under thermal
stress. **A cable either works or it does not — heat soak degrades gradually**, and an 18-day slide
from 17.7 to 0.6 is a cooking story, not a connector story. Keith checked the cable first anyway,
which was correct: cheapest hypothesis, 30 seconds, and it eliminated the alternative.

**Working diagnosis: the DISK is probably fine and the ENCLOSURE BRIDGE is the casualty.** 105-110F
on the case exterior implies roughly 50-58C internal — within HDD spec, at the top of it, sustained;
the bridge board is typically the least thermally tolerant part in the box. ⚠ **CORRECTION, same hour, by Keith:** Cowork claimed *"enumerates, then drops out of Explorer on
its own — the bridge's signature failure."* **THAT NEVER HAPPENED.** It did not drop spontaneously;
it simply never came back after the port swap. **Cowork built a diagnosis on a symptom that did not
occur** — the same defect as summing a cumulative counter (PLM-08) and reading the wrong dict key
(PLM-26): a confident story from a misread observation. The bridge remains a *candidate*, not a
finding. ⇒ Recovery may still be a different dock; do not write the contents off on a USB error.

⚠ **SECOND CORRECTION, minutes later — Cowork was wrong AGAIN about the same event.** It then
claimed the cable had been swapped too, and lectured that "two variables changed at once, the test
lost its power to discriminate." **The cable never moved.** Keith moved the drive's own cable to a
different port and put the PRINTER on the drive's old port.

🟢 **THAT IS A PROPERLY CONTROLLED A/B SWAP, AND BETTER THAN WHAT COWORK PROPOSED.** One variable
changed for the drive (the port), and **the printer is the control on the old port**:
  * printer WORKS on the drive's old port  -> that port is good -> the drive failed on a different
    port with its own cable ⇒ fault is the enclosure/drive.
  * printer FAILS there too                -> the port is dead ⇒ the drive may be innocent.

## S-97 · 2026-07-31 · I CHECKED THE WRONG GOOGLE ACCOUNT AND CALLED A PROJECT NON-EXISTENT
> 🔴 **CORRECTED AT TidyUP2, SAME SESSION, BY CHECK 4 (stale-constant sweep). The title above is the
> corrected one. The original read "A PROJECT ID IN THE RECORD DOES NOT EXIST" — that was WRONG, and
> the error was mine, not the record's. Read the correction block at the end before anything else.**
>
> **The project exists.** It is under **`joanna.bbf@gmail.com`**, a separate identity. `gcloud` is
> authenticated as `keith.bbf@gmail.com`. It was never going to be in that list.
> **The measurement below is accurate. The conclusion drawn from it was not.**
**Measured**, read-only, on Keith's box:
```
gcloud projects list --filter="lifecycleState:DELETE_REQUESTED"   -> EMPTY
gcloud projects list                                              -> exactly TWO, both ACTIVE
    gen-lang-client-0129519884      206234795642   Default Gemini Project   (gcloud's default)
    project-af3277c0-5279-4670-86c  475026348209   My First Project         (the GDX OAuth client)
```
**The handoff records the $300 Vertex credit against `project-5a33f910-1251-4d6a-bf9`.**
That ID **is not in the account.** It is not pending deletion — it is simply not there.

🔴 **THE TRAP IS THAT THE VERTEX RAIL WORKS.** Measured at 0.7 s from the sandbox the same day. So
the rail was never going to fail and tell us. **A wrong identifier attached to a WORKING service is
invisible until someone spends money against it.** This is **S-17, the $299 phantom**, in a different
coat: a real number recorded against the wrong account.

⇒ **A CREDENTIAL OR ACCOUNT IDENTIFIER IS NOT VERIFIED BY THE SERVICE ANSWERING.** A successful call
proves *a* project works, never *that* project. Verify identity against the provider's own list.
⇒ **Settle it before pricing the 2026-10-13 expiry**, or the top-up decision gets priced against a
project that does not exist: `gcloud billing projects describe <id>`.

**What made it visible is the part worth keeping.** The 2026-08-14 soft-delete row was a stray line
in a CLOCKS table that nearly died in the monolith migration — rescued into `rails.toml [[clock]]`
during the 07-31 heading count, one of two sub-rows that "would have died silently." Settling it cost
one read-only bat. **The clock itself was a non-event; checking it was not.** The argument for
counting every heading before deleting the monolith is no longer theoretical.

---
### 🔴 CORRECTION — TidyUP2 CHECK 4, same session. THE PROJECT EXISTS. I QUERIED THE WRONG ACCOUNT.
**`00_HARVEST_2026-07-16.md` had the answer on disk the whole time, in a table headed
"Accounts — THE CURRENT TRUTH":**
```
Live billing account   010E47-824B53-7202F5  — "Joanna", FREE TRIAL, not activated
Project                project-5a33f910-1251-4d6a-bf9  ("My First Project"), number 614387154970
Identity               joanna.bbf@gmail.com  — a consumer Gmail, NOT in any Workspace org
Credit                 $300.00 -> $299.89 measured 07-16
```
**`gcloud` is authenticated as `keith.bbf@gmail.com`.** Two different Google identities. The project
was never going to appear in that list, and its absence was **evidence about my query, not about the
project.**

⚠ **AND THE TRAP HAD A SECOND FLOOR: BOTH accounts contain a project named "My First Project".**
Keith's is `project-af3277c0-5279-4670-86c` / `475026348209`. Joanna's is
`project-5a33f910-1251-4d6a-bf9` / `614387154970`. **Same display name, different everything.** The
matching name is exactly what would let a careless reader "confirm" the wrong project.

🔴 **THEREFORE THE CLOCK IS NOT SETTLED EITHER.** I reported the 2026-08-14 soft-delete as a measured
NON-EVENT. `DELETE_REQUESTED` was empty **for Keith's account only**. The deleted billing accounts
(`0142FE-A0C041-4BE7E3`, `01E877-…`, removed 07-15) and anything under Joanna were never queried.
**"Settled" was withdrawn the same session it was granted.**

⇒ **AN ABSENCE IS ONLY EVIDENCE IF THE SEARCH COVERED THE PLACE THE THING WOULD BE.** `gcloud
projects list` answers *"projects visible to the authenticated principal"* — never *"projects that
exist."* **A null result inherits the scope of its query, and I reported it stripped of that scope.**
This is the same defect as summing a cumulative counter (PLM-08) and reading a key that never existed
(PLM-26): the measurement was clean, the referent was wrong. **Third instance of this class.**

⇒ **STANDING: BEFORE ANY `gcloud` FINDING, PRINT `gcloud config list` AND STATE THE ACCOUNT IN THE
FINDING ITSELF.** The bat already printed it — section 3 said `account = keith.bbf@gmail.com` — and
**I read past it.** The evidence that would have stopped this was in the output I was quoting from.
⇒ **A MULTI-IDENTITY ESTATE IS THE DEFAULT HERE, NOT AN EDGE CASE:** keith.bbf@gmail.com ·
joanna.bbf@gmail.com · dchamberss@gmail.com (xAI billing). Three identities already.

## S-130 · 2026-08-08 · **FIVE OF SEVEN CITATIONS FROM ONE RAIL WERE FABRICATED — AND BOTH LOAD-BEARING ONES WERE INVENTED**

Keith: *"Did you delegate this? See what the CREW can find as well."* The same Oklahoma
collection-law question went to **SGH** (grok-4.5) and **GEM** (gemini-2.5-pro). Every citation they
returned was then checked against Justia, CourtListener and OSCN. **The result is the strongest
measurement this mesh has of what an unverified rail return is worth.**

**GEM: five of seven case citations do not exist.** *D.W.G., Inc. v. Freshko, Inc.* · *Lawton
Orthodontics, PLLC v. Ragin* · *Atchison, T. & S.F. Ry. Co. v. Young* · *Fellers v. Addy* · *GJP,
Inc. v. H2O, Inc.* **Every one occupies a citation slot held by a real, unrelated decision** —
2021 OK 1 is a lawyer-discipline case, 2011 OK 17 is a divorce, 1997 OK CIV APP 83 is a Corporation
Commission appeal. ⇒ 🔴 **THE TWO ITS ENTIRE RECOMMENDATION RESTED ON WERE BOTH INVENTED**, and each
was invented to hold *exactly* what the argument needed: one that a goodwill handover with no
document is a fraudulent transfer, the other that Medicaid payments cannot be garnished.
**SGH invented statutory text instead** — a § 2034 quotation that is not Oklahoma's statute — and
both rails garbled *Pulis* in different directions (1977 OK 236 · 1977 OK 120; it is **1977 OK 36**).

⇒ 🔴 **THE FABRICATIONS WERE NOT RANDOM — THEY WERE LOAD-BEARING AND FLATTERING.** The invented cases
were the ones that made the answer work. **A fabrication rate is not the right measure; WHERE the
fabrications fall is.** They fall exactly where a model wants a case to exist.
⇒ ⚠ **AND FLUENCY INVERTED WITH RELIABILITY.** GEM's return was the better-written, better-organized,
more confident document, with pinpoint paragraph cites and block quotations. **It was the one that
was mostly false.** SGH hedged with "confirm" and "UNKNOWN" and was closer to the truth.
⇒ **BOTH MISSED THE ONE CASE THAT DECIDES THE QUESTION** — *Mattingly*, 2020 OK CIV APP 19, which
adopts reverse veil piercing in Oklahoma. Both asserted the doctrine is unadopted, reasoning from
pre-2020 authority. **A rail can be confidently, unanimously wrong about the current state of the
law**, and unanimity across families is not corroboration when both are trained on the same stale
majority view.

**WHAT MAKES THIS A SCAR RATHER THAN A COMPLAINT: THE EXERCISE WAS STILL WORTH IT, AND THE VALUE CAME
FROM THE VERIFICATION PASS, NOT THE RETURNS.** Checking a citation GEM offered **for the opposite
proposition** turned up *Sproles v. Gulfcor*, 1999 OK CIV APP 81 — real, and holding that a judgment
creditor **may litigate the liability of those behind a dissolved entity in post-judgment execution
in the same case**. That may remove a joinder problem the file has treated as fixed for a week.
⇒ **The rails are idea generators. They are not sources.** Fire them, harvest the leads, and then
verify every one — including, and especially, the ones offered *against* the proposition, because
that is where this one was hiding.
⇒ **STANDING: no citation from any rail reaches a document that leaves this office without being
checked against Justia, CourtListener or OSCN.** *(Same family as the July DOI fabrication — but that
one was caught before insertion, and this measurement shows why that control has to hold.)*

## S-129 · 2026-08-08 · **THE INDEX SAID 71 AND THE DIRECTORY HELD 74 — AND THE THREE MISSING ONES WERE THE EXHIBITS THE QUESTION TURNED ON**

`wargame_feed.py` writes `00_INDEX.txt` **only at build time.** `record_trim.py` and
`record_add_exhibits.py` then both MUTATE the directory, and **neither regenerates the index.** So
from 3 Aug to 8 Aug the war-game record carried an index that said *"71 documents"* over a directory
holding **74**, omitting **all six exhibits added on 3 Aug** — the PJLA certificate, both OMMA
license records, the Instagram capture, the annotated map, the LinkedIn and Facebook captures — plus
the RFA responses. **Every one of the omissions bears on the transfer requests**, which is the
question the record was assembled to answer.

⇒ **THIS IS `S-117` / `C-12` MOVED ONE LAYER OUT, AND THAT IS WHY IT SURVIVED.** S-117 was about a
bundle being *present and hollow*. The fix was to verify coverage by content. But nobody applied that
test to the **derived index**, because an index is not evidence and so it did not feel like something
that could be wrong. **A coverage claim is exactly the thing that must be checked, precisely because
everything downstream trusts it instead of counting.**
⇒ ⚠ **The failure is silent in the worst direction.** A reader handed a short index does not error.
It answers — fluently, confidently — about a record that does not contain what it was asked about.
On 3 Aug we paid $0.29 for exactly that shape of answer and the file that would have shown it was
sitting in the same directory.
⇒ **FIXED, NOT JUST NOTED:** `BTS_MESH\record_reindex.py`. `--check` reports drift, writes nothing,
and **exits non-zero so a stale index goes RED at TidyUP.** Shown to fail first — it went RED on both
`record\` and `record_core\`, rebuilt both, and re-checked green.
⇒ **AND THE ADJACENT DEFECT WAS REAL TOO:** `wargame_feed.py --narrow` and `--expanded` wrote to the
**same directory**, so building either destroyed the other. That is how the narrow set was lost on
3 Aug. BU.MD carried *"do not rebuild either set until it is fixed"* for five days, which is a
warning standing in for a patch that takes ten minutes. **Now two directories plus an overwrite guard
that refuses on a populated target and names what it would have destroyed — negative control run,
both modes returned rc=3, both directories byte-identical afterwards.**

## S-128 · 2026-08-08 · **THE SESSION FOUND THE WRONG OPPOSING COUNSEL, SAID SO AT LENGTH, AND EDITED NOTHING**

Every document in the serve package named **Travis K. Dennis** of Plainview Legal Group at
515 S. University Blvd — counsel who signed the **March 2023** Answer. Abraxas has been represented
since at least **February 2026** by **Haley J. Dennis, OBA #32766**, same firm, **330 W. Gray St.
Suite 100**, `hdennis@plainviewlegal.com`, who signed the 2026-02-05 discovery requests and the
2026-03-18 production. Keith supplied the reason it was easy to miss: *"Travis is Haley's husband.
She inherited the case."*

**The 6 August session found this. It named the defect, listed the affected documents, and explained
why it mattered. Then it edited none of them.** Two days later all six were still wrong: three
deposition notices, the inspection request, the RFA certificate of service, two letters to opposing
counsel, the preservation letters and the action memo. **A certificate of service naming the wrong
attorney at a superseded address is a service defect**, and these were drafts about to be signed by
counsel and served.

⇒ 🔴 **THE SCAR IS NOT THE WRONG NAME. IT IS THAT FINDING A DEFECT FELT LIKE FIXING IT.** The
session did the hard part — noticing — and then skipped the trivial part, and the prose it produced
about the defect read exactly like a repair. *(C-05, now at count 3.)*
⇒ **A DEFECT REPORTED IN CHAT AND A DEFECT REPAIRED ON DISK ARE INDISTINGUISHABLE IN A TRANSCRIPT.**
Only a grep tells them apart. **STANDING: for every defect a session reports, TidyUP greps the
artifact to confirm the fix landed.** Reported is not repaired.
⇒ **AND THE GENERAL RULE THE CASE FACT PRODUCED (`C-20`):** who the other side's lawyer is *today*
is a record fact. **Re-derive it from the newest filing, every time** — never from an earlier
document, a summary, or working context. The document that establishes such a fact is usually the
**oldest** one in the corpus, which is exactly the one a name search surfaces first.
⇒ Same session also left **three promises unwritten** (the C-16 variant, Travis Dennis's move to
OHCA, the corrected §N5) and an addendum section, **§N5, standing as settled fact after its
conclusion had been withdrawn in the same conversation** — it still instructed *"stop citing the
proximity of those two dates"* when the settled position was the opposite. All four repaired 8 Aug.

## S-127 · 2026-08-03 · **WE TOLD THE CLIENT A FACT ABOUT HIS OWN CONDUCT AND NEVER ASKED HIM**

`DEFEATING_THE_NDA_2026-08-03` asserted **"CHAMBERS NEVER SIGNED IT"** as a settled fact, in a
section heading, and was handed to Chambers. When the Adobe Sign certificate surfaced, Keith's
reaction was not surprise: *"And yes. The NDA was esigned — so what."*

**He knew.** He signed it. The one person in the loop who could have settled the question in a
single sentence was the person the false document was delivered to, and **nobody asked him.**

⇒ 🔴 **THE CHEAPEST VERIFICATION IN A CLIENT MATTER IS THE CLIENT.** Cowork searched the corpus,
reasoned from the pleadings, and built an argument three layers deep on a premise a one-line question
would have destroyed. **Free, instant, and more authoritative than any document search** — because
he was there.
⇒ **AND THE FAILURE MODE IS SPECIFIC: facts about KEITH'S OWN CONDUCT** — what he signed, sent,
received, paid, agreed to — **are the class where the corpus is the WORST source and he is the best.**
The corpus holds what was produced; he holds what happened.
⇒ **STANDING: before asserting anything about what Keith did or did not do, ask him.** Not after the
document is built. Not as verification of a conclusion already drafted. Before.
⇒ ⚠ **Note the second-order cost: the finding was then over-dramatised** to Keith as though the
signature itself were the discovery, when the only live issues were ever the fee-shifting clause and
the disclosure question. **A fact the client already knows is not news; treating it as news wastes
his attention and misstates the risk.**

## S-126 · 2026-08-03 · **THREE ROUNDS SPENT ARGUING THE END DATE OF A SCHEDULE THAT NEVER RAN**

Fable said Chambers' invoice charges *"$535.03 monthly charges 23 months past the April 2023 zero
balance on his own amortisation schedule."* Cowork relayed it. Keith pushed back on the pleading
posture; Cowork conceded that and then **queried whether the zero date was April 2023 or late 2023**,
staging a task to *"find the actual amortisation table before quoting either date."*

**Keith: *"Amort table was irrelevant 90 days in — the lease was fully breached."***

**There is no zero date, because the schedule never ran.** An amortisation table describes how a
**performing** party pays down a balance. Abraxas stopped performing within about ninety days of
delivery, having paid **$1,500** against a **$19,700+** instrument. Everything the table says after
that point is a description of a hypothetical.

⇒ 🔴 **COWORK ARGUED THE PRECISION OF A NUMBER WITHOUT ASKING WHETHER THE NUMBER APPLIED.** Getting
the date right and getting the date's *relevance* right are different questions, and only the second
one mattered. **Verifying harder is not the same as verifying the right thing** — the whole
sub-argument was downstream of an unexamined premise that the schedule governed at all.
⇒ **AND IT WAS INHERITED, NOT REASONED.** The premise arrived inside a reviewer's sentence and was
adopted whole while its *conclusion* was being disputed. **Disputing a claim's conclusion while
silently accepting its framing is how a wrong frame survives being challenged.** *(S-125 is the
same defect one layer up.)*
⇒ **STANDING: before refining a figure, ask what turns on it.** If the answer is *"nothing, because
the instrument it comes from was voided by the other side's own breach"*, the refinement is waste
dressed as diligence.

## S-125 · 2026-08-03 · **A REVIEWER WAS RIGHT ABOUT ONE THING, SO COWORK STOPPED CHECKING THE NEXT — AND RELAYED A CLAIM THAT CONTRADICTED ITS OWN VERIFIED FINDING**

Fable's cold read found the NDA signature error (S-123), which was **verified and correct**. In the
same summary it wrote that Chambers' March 2025 invoice is footed *"Rentals are month-to-month
outside terms of a lease agreement"* — *"a written concession there is no lease, **on the document
he sues on the lease to enforce**."*

**Cowork relayed that to Keith without opening the Petition.** Keith: *"actually, the lease is the
LAST thing we are suing for. Quantum Meruit is the first claim."*

**He is right.** `Petition 2025.pdf` — **COUNT I QUASI-CONTRACT / QUANTUM MERUIT / UNJUST
ENRICHMENT · COUNT II CONVERSION · COUNT III BREACH OF CONTRACT.** The contract claim is pleaded
**last**. So the footer is not a self-inflicted wound at all — *"no lease, month-to-month use, pay
for what you used"* **is Count I**. And `BU.MD` **already said so**: *"The invoice footer is NOT a
wound — it is the quantum-meruit theory, and it matches their own ¶36/¶37."*

⇒ 🔴 **BEING RIGHT ABOUT ONE THING DOES NOT MAKE A SOURCE AUTHORITATIVE ABOUT THE NEXT.** Fable had
just been correct on a hard, checkable, high-stakes fact. Cowork generalised from that to the rest of
the summary and stopped verifying. **The whole premise of a cross-check is that the checker can also
be wrong** — a reviewer earns trust per-claim, never in bulk.
⇒ **AND IT OVERWROTE A FINDING WE HAD ALREADY VERIFIED.** The prior conclusion was on disk, in the
boot pointer, correct. A new outside claim displaced it silently because it was newer and its author
had just scored. **When an incoming claim contradicts something already recorded as verified, that
collision is the alarm — resolve it against the source document, do not let recency win.**
⇒ **Third C-08 instance in one day**, and the worst-shaped one: the first two quoted numbers Cowork
had not measured; this one contradicted a measurement Cowork had already made.

## S-124 · 2026-08-03 · **"I DON'T MIND SPENDING SOME CREDITS" IS AUTHORISATION TO SPEND, NOT AN INSTRUCTION TO PROCEED NOW**

Keith, in order: *"I want to open the NEXT session with Fable 5 and have it read the case corpus."*
Then, after a costing question: *"I want Fable's fresh take on the case file w/Jasper additions… I
don't mind spending some credits on it, $10-20 I'm not worried about."*

**Cowork dispatched the subagent immediately.** Keith: *"I wanted Fable setup for the next session,
not this one."*

**Both sentences were about the same work; only one of them was about timing, and it said NEXT
SESSION.** The second removed the *budget* objection Cowork had raised, and Cowork treated a removed
objection as a green light — reading enthusiasm about cost as impatience about schedule.

⇒ 🔴 **AUTHORISATION AND INSTRUCTION ARE DIFFERENT ACTS.** *"I don't mind paying for it"* answers
**may I**. It does not answer **when**. When the only prior statement about timing says *next
session*, that stands until it is withdrawn — and it was never withdrawn, it was simply not repeated.
⇒ **STANDING: when Keith has fixed a time for a piece of work, a later message about its COST does
not move it.** If the timing now seems open, ask — one line, before spending 627,190 tokens.
⇒ ⚠ **AND THE RESULT DOES NOT LAUNDER THE PROCESS.** The run found a delivered document to be wrong
on its central fact (S-123), which is worth many times what it cost. **That is luck arguing for a bad
habit.** The next unauthorised run finds nothing and the tokens are simply gone. *(C-14.)*

## S-123 · 2026-08-03 · **WE TOLD KEITH HE NEVER SIGNED A CONTRACT HE HAD E-SIGNED, AND THE PROOF WAS IN THE OTHER SIDE'S OWN EXHIBIT**

`DEFEATING_THE_NDA_2026-08-03` — **built and delivered to Keith** — states in a section heading:
**"AND THE FACT THAT DECIDES IT IS SETTLED: CHAMBERS NEVER SIGNED IT,"** concludes *"Signature
question answered — Chambers never signed it. Ground One runs at full strength,"* and proposes
serving: *"Admit that Plaintiff never signed the March 12, 2020 Non-Disclosure Agreement."*

**He signed it.** Inside `Abraxas- Exhibit B1 - Vadim Yerokhin- emails P1.pdf` — **Defendant's own
production, already in our record** — is a complete Adobe Sign certificate:
> *"Document e-signed by Keith Chambers (deltatherapeutics@gmail.com) · Signature Date: 2020-03-13 -
> 3:14:36 AM GMT - Time Source: server - IP address: 108.210.32.78"*

with the creation, send, view and completion events all timestamped and IP-logged. **Clause X is a
two-way prevailing-party attorney's-fee clause.**

⇒ 🔴 **THE PROPOSED RFA WOULD HAVE BEEN A DISASTER.** It formally invites the opponent to prove
execution from a document they already possess — converting a fact they have not used into one they
have been asked to establish.
⇒ **WE READ THEIR PLEADING AS AN INCONSISTENCY INSTEAD OF READING THE EXHIBIT.** Their Answer calls
the lease *"unexecuted"* and the NDA *"executed"* — we treated the pairing as a tell. **It was simply
accurate.** An opponent's distinction that looks careless is more often a distinction you have not
checked. *(Same family as S-110: a document describing an act taken as proof of the act.)*
⇒ **THE SIGNATURE PAGE IS NOT WHERE THE ANSWER LIVES.** For an e-signed document the proof is the
**audit certificate**, usually appended pages later, often OCR'd badly, and easy to scroll past.
**Search for the certificate, not the signature line.**
⇒ **HOW IT WAS FOUND, AND THIS IS THE ARGUMENT FOR THE WHOLE METHOD:** a reader with **no access to
any of our analysis** was handed the record and asked what it made of it. It found in one pass a
falsehood that had survived being written, reviewed, converted to Word and handed to the client.
**Nothing inside our own work product was ever going to catch it — every document downstream
inherited the premise.**

## S-122 · 2026-08-03 · **THE VERIFICATION PASS FALSIFIED ITS OWN CONTROL DOCUMENT AND CERTIFIED IT CLEAN IN THE SAME HOUR**

TidyUP2's first pass found that `DOCX\PLAIN\` held five versions of one memo, staged four of them,
and wrote into `BU.MD`: *"`DOCX\PLAIN\` NOW HOLDS EXACTLY THE THREE DOCUMENTS JOHN GETS AND NOTHING
ELSE."* True when written.

**The same pass then created a fourth file in that folder** — the ERRATA — and reported the whole
TidyUP2 as complete without revisiting the sentence. **The verification pass invalidated its own
finding as a side effect of acting on a different finding**, and nothing connected the two.

Worse, **the ERRATA was indexed nowhere.** Not in `BU.MD`, not in `Legal\_INDEX.md`. A
known-wrong-deliverable warning existed on disk with no pointer reaching it — **the exact S-119
shape**, created one pass after S-119 was written about it.

⇒ 🔴 **A CHECK THAT CHANGES THE THING IT CHECKED MUST RE-CHECK IT.** Checks 2 and 3 ran BEFORE checks
6 and 7 made edits; the counts and existence sweeps were never re-run against the state those edits
produced. **Ordering the checks is not the same as closing the loop.**
⇒ **STANDING: TidyUP2 runs checks 2, 3 and 8 a SECOND time, after 6, 7 and 10 have made their
changes** — or it certifies a snapshot that no longer exists.
⇒ **STANDING: any artefact created by TidyUP2 itself gets indexed in the same turn it is created.**
An errata nobody can find is worse than no errata, because its existence is mistaken for a warning
having been given.
⇒ **This is why the second pass exists, and it earned its keep:** three findings on the second run,
**all three created by the first.**

## S-121 · 2026-08-03 · **THE PAID RETURN LANDED AT 13:31 AND NOBODY WAS WATCHING FOR IT. COWORK ALMOST CLOSED THE SESSION ON TOP OF IT.**

The whole point of the afternoon was Keith's instruction: *"We need a way to cross-check you. I
cannot, I don't have the knowledge."* A tool was built for it, a record was audited and enlarged for
it, a bat was staged for it. **Keith ran it. SGH's critique — 21,569 characters, 22,227 bytes —
wrote to `RFA_REVIEW\returns\` at 13:31.**

> ⚠ **This line originally read "22,227-character," which is the BYTE count.** SGH's prose carries
> multibyte curly quotes, so bytes exceed characters by 658. Caught on the SECOND TidyUP2 pass,
> **one hour after S-120 was written about quoting a number nobody measured** — and the ledger row
> had `"chars": 21569` in it the whole time. `stat -c%s` is not `len()`. *(S-120, again.)*

**Cowork then ran an entire TidyUP without opening it** — updating the boot pointer, the legal index,
the scars, the corrections, and reporting to Keith that the review was still *"staged and unrun"*.
It was found by **TidyUP2 check 3**, a number-consistency sweep, which noticed the record held 74
documents instead of 78, traced that to `record_trim.py` having been applied, and only then looked in
the returns directory.

**And it mattered.** The review contradicts the drafter on the central allocation, calls two of the
seven *"sucker RFAs"* whose probable true answer helps the defence, and identifies three set-aside
rejections as wrong. **A session that closed twenty minutes earlier would have handed Keith a memo
its own commissioned reviewer had already refuted.**

⇒ 🔴 **AN ASYNCHRONOUS RETURN HAS NO ARRIVAL EVENT. Nothing announces it.** A bat Keith runs in his
own console writes to disk in a directory Cowork is not looking at, and the *absence* of a report is
indistinguishable from the absence of a run.
⇒ **STANDING: when a bat is staged that produces a return, the return directory is checked at the
NEXT TURN and at every TidyUP, before anything is reported as pending.** `ls returns\` costs nothing.
⇒ **Do not report "not yet run" from memory of having staged it.** Staging and running are separate
events with separate evidence, and only one of them leaves a file.
⇒ **Note what actually caught it: a COUNTING check, not a semantic one.** Nobody would have thought
to ask *"did the review return?"* — the recount forced the question by producing a number that could
not be explained. **This is the argument for the counting checks in full.**

## S-120 · 2026-08-03 · **THE PRE-RUN ESTIMATE WAS PRINTED AS THE MEASURED COST, IN THREE DOCUMENTS, WITH THE LEDGER SITTING RIGHT THERE**

The `RFA REVIEW.bat` menu said *"approx $1.70"* — a legitimate **estimate**, written before the call,
to let Keith decide whether to spend. The call ran. `_LEDGER.jsonl` recorded
`"usd": 0.290019` · `320.1s` · `in_tok_est 390,349`.

**Cowork then wrote "$1.70" into the deliverable's own header as the cost**, and into
`Legal\_INDEX.md`, and into the body of **S-117 — a scar whose entire subject is asserting things
without checking the source.** Three documents, one number, **5.9× wrong**, and the correct figure
was one line of the ledger the same tool had just appended.

⇒ 🔴 **AN ESTIMATE AND A MEASUREMENT ARE DIFFERENT KINDS OF FACT, AND THE ONLY THING SEPARATING THEM
IS THAT THE EVENT HAS HAPPENED.** Once it has, the estimate is superseded and quoting it is not
approximation — it is reporting a number nobody measured.
⇒ **STANDING: after any paid call, read the ledger row before writing the cost anywhere.** The tool
already records `usd`, `secs` and `in_tok_est`. **Never carry a menu figure into a deliverable.**
⇒ **Same family as C-08 (cite from the document, never from context)** — but the "context" here was
**Cowork's own earlier output**, which is the version of the defect least likely to feel like one.
*(Found by TidyUP2 check 1. The claim had already been presented to Keith.)*

## S-119 · 2026-08-03 · **THE CANONICAL FILENAME HELD THE OLDEST DRAFT. FOLLOWING THE POINTER CORRECTLY GOT YOU THE WRONG DOCUMENT.**

`DOCX\PLAIN\` held **five** builds of the memo John Farley is meant to receive: the plain name, then
`v2`, `v3`, `v4`, `v5`. Five iterations in thirty-five minutes is normal drafting and is not the
defect. **The defect is which one wore the clean name.**

`BU.MD` and `Legal\_INDEX.md` both name it **without a version** — *"Requests for admission - the last
seven"* — and that file was the **11:40 build, 1,683 words, the FIRST draft**, written before Keith
corrected the possession request, the receipt request, the staff-time framing and the transfer
allocation. The current document was `v5`, 1,401 words, 12:15. **So a reader who followed the control
document exactly as written would have opened the one version containing every error Keith had
already caught** — and it would have looked right, because it was where the pointer said.

⇒ 🔴 **A VERSION SUFFIX SILENTLY DEMOTES THE UNSUFFIXED FILE TO "OLDEST", WHILE EVERY POINTER STILL
NAMES IT.** The moment you write `v2`, the plain name stops meaning *current* and starts meaning
*first* — and nothing announces the change.
⇒ **STANDING: the clean name is the CURRENT document, always.** Iterate under suffixes if you must,
but **promote the winner to the clean name and stage the rest the same turn.** Done here: v2–v4 and
the original staged to `V:\Ai\_delme\delme__2026-08-03__*`, v5 promoted, `PLAIN\` now holds exactly
the three documents Keith said John gets and nothing else.
⇒ **Same family as the dated-handoff rot that recurred four times** (S-89): a filename in prose is a
*copy* of a pointer, and copies rot. **Caught by TidyUP2 check 2**, the existence sweep — which found
the path existed, and only then noticed *what* was at it. **Existence is not currency.**

## S-118 · 2026-08-03 · **THE CARRY-OVER SYSTEM WAS DEAD ALL DAY. UNESCAPED QUOTES IN ONE STRING, AND `corrections.toml` STOPPED PARSING.**

`corrections.toml` is the C.O.S. — the file that exists *because* nothing Keith says changes the
model, so the carry-over layer **is** the training signal. On 3 Aug an occurrence string in C-06 was
written as a TOML **basic string containing unescaped double quotes**:
`errored with "'o' is not recognized"`. TOML ends the string at the first inner quote. **The file
stopped parsing at 08:xx and was not caught until 13:35.**

**For those hours the entire escalation mechanism was silently off.** The four corrections at
count ≥ 3 — **C-01 CLAUDE SOLO (4)**, **C-06 NEVER INLINE A PROGRAM IN A SHELL (4)**, **C-03 A
CLICK, NEVER A CHORE (3)**, **C-07 PROPORTION (3)** — are specified to print FIRST at BootUP, before
the task list. A BootUP in that window would have printed **nothing at all** and nobody would have
noticed, because the absence of a warning looks exactly like the absence of a problem.

⇒ 🔴 **A CONTROL DOCUMENT THAT CANNOT BE READ IS WORSE THAN ONE THAT DOES NOT EXIST**, because
everyone downstream believes it is working. **Parse `corrections.toml` at every TidyUP and refuse to
close the session if it fails.** One line of `tomli.load`.
⇒ **Note the shape:** C-06 is *"never inline a program in a shell"* — a scar about punctuation being
eaten by a parser — and **it was the entry whose own punctuation broke its file.** Third time a
document about a hazard has demonstrated the hazard (S-114 was a docstring about a quoting scar that
contained a triple-quote).
⇒ **And the sandbox reported it honestly.** `tomli` raised `Unclosed array (line 134)` and the rule
says a sandbox parse failure is NOT evidence — so it was confirmed host-side with `Read` before
anything was touched. **The rule worked in the direction that matters: it forced verification, it did
not excuse dismissal.**

## S-117 · 2026-08-03 · **THE BUNDLE EXISTED, SO THE GUARD PASSED. THE DOCUMENTS THE QUESTION TURNED ON WERE NOT IN IT.**

`rfa_review.py` was written with a deliberate guard: refuse to fire if bundle `09_JASPER_UCC` is
absent, because five of the seven proposed requests concern the alleged transfer to Jasper and
Abraxas Scientific. **The guard passed.** The bundle was there — twelve files.

**It was hollow.** The bundle held only the *PDF* members of the source folder. **Jasper's PJLA
Certificate L26-171 — the one document carrying the `AL-SOP-##` identifiers that request 27 is
entirely about — was not in it**, nor were the OMMA licences, the Instagram continuity, the LinkedIn
employee move, or the annotated map. Every image exhibit had been invisible to **every** war-game run
to date. The certificate was sitting in `Downloads\L26-171.pdf`.

The tasking told the reviewer to *"WRITE 'NOT IN RECORD' rather than assuming."* **SGH would have
done exactly that, correctly, and the call would have bought a confident answer to the wrong
question.** *(Costed at $0.29 when it finally ran — see S-120 on the $1.70 estimate that three
documents repeated as though it were measured.)*

⇒ 🔴 **A PRESENCE CHECK IS NOT A COVERAGE CHECK.** Coverage is verified by asking, for each
proposition at issue, **WHICH FILE PROVES IT** — never by trusting that a bundle named after the
topic contains the topic.
⇒ **This was found by accident.** It surfaced only because Keith asked what else could be *cut*, and
answering that required grepping the documents for what they contained. **The audit that mattered was
a side effect of a question about something else** — which is the whole argument for asking.

## S-116 · 2026-08-03 · **AN UNMEASURED CLAIM SURVIVED BECAUSE IT WAS THE CAUTIOUS ONE**

Cowork told Keith that a per-document character cap must not be used on the war-game record, because
it would truncate `Abraxas_Labs_SOPs_MAIN.docx`, *"which requests 27 and 30 turn on"* — and built a
fit-drop rule and a selftest around that reasoning.

**The principle was right. The specific claim was never measured.** When Keith asked what else could
be cut, a grep showed the `AL-SOP` identifier appears **exactly twice in 105,781 bytes** — table of
contents line 163 and section heading line 2374, both *"AL-SOP-04 SAMPLING SOPs."* The file excerpts
to 22,000 bytes losing nothing. The same pass found the Business Plan had **zero** hits on Jasper,
Abraxas Scientific, autosampler, needle or lost profits, and the QA Policy had **zero on everything**
— 49,377 bytes defended by nobody, because nobody looked.

⇒ 🔴 **NOTE THE ASYMMETRY, WHICH IS THE ACTUAL LESSON.** The unmeasured assertion was the
*protective* one. *"We must keep this"* reads as diligence, so it draws no challenge and survives a
full exchange — where *"we can cut this"* would have been questioned immediately. **Caution is not
evidence, and it is the claim least likely to be checked.**
⇒ **STANDING: grep the file before ruling on its importance**, in either direction. *(C-11.)*

## S-115 · 2026-08-02 · **`BU.MD` POINTED AT FOUR DESKTOP BATS — DIRECTLY BENEATH ITS OWN RULE FORBIDDING EXACTLY THAT**

`BU.MD` carries this at the top, in its third section, unchanged for weeks:
> *"🚫 The Desktop is a DELIVERY surface, not a repository. Every `.bat` is **one and done** — Keith
> deletes them… **No control document may point at one.**"*

**Then, seven hundred words later in the same file, TidyUP wrote:** *"Run
`1 - MESH Deploy 3 Tasks.bat`"* and *"Desktop: three numbered bats in run order + `4 - REBUILD scars
index.bat`."* **Four pointers at ephemera, written into the boot pointer, underneath the rule that
forbids it.**

**Caught by TidyUP2 check 2 — an existence sweep of every path the new `BU.MD` names.** All four were
already gone; Keith had run and deleted them the same night, exactly as the rule predicts.

🔴 **AND THE REAL LOSS WAS HIDDEN BEHIND IT:** the existence sweep also revealed that
`V:\Ai\Legal\MESH\` holds **four prompt files and ZERO returns.** **The three mesh tasks were never
fired** — including **TASK_B, the licence timeline, which is what confirms the 23 Oct 2020 OMMA date
that may zero their entire lost-profits counterclaim.** A dangling pointer to a launcher concealed an
unfired job.

⇒ **Same shape as the dated-handoff rot (R5): the warning sat directly above the defect and did not
prevent it. A rule in prose is not a control.**
⇒ **CONTROL DOCUMENTS NAME DURABLE ARTEFACTS ONLY** — scripts (`sweep_corpus.py`, `mesh_fanout.py`)
and inputs (`MESH\*.txt`), **never the wrapper that launches them.** A bat is a delivery vehicle;
re-stage it when needed.
⇒ **And verify by ARTIFACT, never by launcher:** *"the bat was staged"* is not *"the job ran."*
**Check for the RETURNS.**

---

## S-114 · 2026-08-02 · THE DOCSTRING DOCUMENTING A QUOTING SCAR CONTAINED A TRIPLE-QUOTE AND BROKE THE FILE THE SAME WAY

`mesh_fanout.py` line 78. The docstring recorded the S-60 lesson — *prompts inlined into a
cmd/start wrapper lose their doubled quoting and die silently* — and to illustrate it embedded
`grok -p ""…"""`. **That `"""` terminated the docstring early. `SyntaxError: unterminated
triple-quoted string literal.`** The file documenting a quoting failure failed on quoting.

**What saved it:** the bat runs `--selftest` **before** the paid call and gates on `errorlevel`.
Keith saw `SELFTEST FAILED - nothing spent.` **The guard worked exactly as designed and cost $0.**

⇒ **Illustrative examples of syntax hazards go in COMMENTS, never in the string literal they are
about.** And ⇒ **every generated `.py` gets `ast.parse` before it ships**, not after a user reports it.

---

## S-113 · 2026-08-02 · COWORK MISIDENTIFIED THE DEAD DRIVE **TWICE IN ONE NIGHT**, BOTH TIMES BY REACHING A CONCLUSION AHEAD OF THE IDENTIFIER

**First:** advised a head-stack swap and a donor `ST8000NM0055` from the drop history alone —
without weighing the prior session's finding that the volume was *"unreadable at 512-byte sectors…
not empty space."*
**Second, worse:** read a `bts_drive_health` report showing `WD My Passport 25E2 · 3726 GB · GREEN`
and announced *"your drive is alive."* **It was a different disk.** The same output said
**`G:\ is not present`** — because it is unplugged, in a drawer — and the capacities differ by more
than 4 TB. **Both facts were on screen and neither was checked.**

⇒ **CHECK SERIAL AND CAPACITY BEFORE THE STORY.** A drive is identified by `SerialNumber`, never by
drive letter, never by disk number, never by "the external one."
⇒ **And the cheap reversible hypothesis is tested first.** A 4Kn-passing bridge costs nothing;
a head-stack swap consumes a donor and is irreversible. *(→ PLM-32.)*

---

## S-112 · 2026-08-02 · THE BAT'S SAFETY WARNING NAMES A DISK NUMBER. DISK 0 IS NOW THE BOOT DRIVE.

`SMART NOW while on SATA.bat` ends: *"STILL DO NOT initialize, format, or create a volume on
**Disk 0**."* It was written when the 8 TB enumerated as Disk 0. **On 2026-08-02, Disk 0 is the
`WD_BLACK SN850X` — the C: boot drive.** Followed literally, the protective instruction now points
at the system disk.

⇒ **Same defect as the dated-handoff rot (S-“pointer”/R5): an UNSTABLE identifier standing in for a
STABLE one.** Disk numbers shift with what is plugged in; **serial numbers do not.**
⇒ **Any destructive-adjacent guard must key on `SerialNumber` and PRINT the serial it is
protecting.** *(→ PLM-31.)*

---

## S-111 · 2026-08-02 · "NOT IN THE CORPUS" WAS REPORTED AS "NOT IN THE RECORD" — AND THE RETRACTION PROPAGATED INTO FOUR DOCUMENTS BEFORE ANYONE CHECKED

An agent searched **only `V:\Ai\Legal\CORPUS`** and truthfully reported that the sole PJLA document
there is a 13 Mar 2020 bulletin to `Keith@ORACLabs.com`. **Cowork converted that into "the finding is
unsupported — retract it"** and wrote the retraction into `CRITICAL_SELF_INFLICTED`, `TODO_MESH`,
`DOCUMENT_REGISTER` and `ADDING_PARTIES`.

**The finding was never built from the corpus.** Its sources are the **PJLA public registry** and
**Certificate L26-171, obtained by Keith** — neither of which lives in `CORPUS\`. **And the two facts
never conflicted:** PJLA wrote to Keith about ORACL in 2020; Yerokhin is the PJLA contact of record
for Abraxas **and** Jasper in 2023–2026.

🔴 **What was nearly discarded:** one man as accreditation contact for **both** labs, a **14-day**
certificate hand-off, a **16-month** overlap, and **Jasper's accredited scope citing `AL-SOP-##`
numbers that appear in an Abraxas-titled document** — currently the strongest Yerokhin→Jasper
evidence in the case. Recovered only because Keith said *"you clearly haven't read all the case
documents yet."*

⇒ **SCOPE OF THE CLAIM MUST EQUAL SCOPE OF THE MEASUREMENT.** A negative finding must state what was
searched **and what was not**: *"not in `CORPUS\`"* ≠ *"not in the record."* Registry, OSCN, SOS,
county UCC and Keith's own separately-obtained documents all live outside it.
⇒ **And a retraction is a CLAIM.** It needs the same evidence as the finding it overturns — and it
must not be propagated until it has it.

---

## S-110 · 2026-08-02 · A DOCUMENT DESCRIBING AN ACT WAS TWICE TAKEN AS PROOF THE ACT OCCURRED — TWICE IN ONE HOUR, ON THE SAME FACT PATTERN

**(1)** Abraxas cheque no. 5619772, $535.03, produced as an image → Cowork wrote *"we are suing for
money we were paid"* and called it the worst item in the case. **Keith: never cashed, on counsel's
advice.** Tendered ≠ received.
**(2)** Bates 000048, *"**Attached is a check** for a total of $3,015.39"* → Cowork treated it as a
tender we refused, and built a §3-311 accord-and-satisfaction argument on it. **Keith: it was a
rejected settlement proposal and the cheque was never sent.** Described ≠ enclosed ≠ mailed.

⇒ **THE CORPUS RECORDS WHAT WAS WRITTEN, NOT WHAT WAS DONE.** Authorship ≠ transmission ≠ receipt ≠
negotiation. **Every "payment", "notice", "tender" and "delivery" needs a TRANSMISSION FACT** — a
bank debit, a cancelled instrument, a delivery receipt, a recipient's acknowledgement.
✅ **Applied to the other side it is the case:** ¶41's *"notices in writing"*, their $3,015.39
"payment", and the *"attached is a check"* letter **all fail the same test.**

---

## S-109 · 2026-08-02 · TWENTY-FOUR `.md` FILES WERE HANDED TO KEITH BEFORE ANYONE ASKED ABOUT FORMAT — AND THE FIX WAS THEN MISAPPLIED THE SAME WAY

**Keith:** *"Never, ever hand me a file in .md again. I hate that format… **I don't read .md**."*
An entire session of deliverables went to a man who does not read the format. **Nobody asked on
file one.**

**And the correction repeated the error class.** Told "convert to Word," Cowork batch-converted
**everything** — including `SESSION_HANDOFF_SOP` and `PDAIS`, which are **Cowork's own procedures**
and belong to the mesh. **Keith:** *"Some of those files are not for me… **USE THE CORRECT FORMAT
FOR THE CORRECT PURPOSE.** I guess you need to make yourself a table for that."*

⇒ **ASK WHO CONSUMES IT BEFORE CHOOSING A FORMAT.** Consumer first, nature second.
⇒ Keith: `.docx` (editable) / `.pdf` (final) · mesh structured state: `.toml` > `.json` · mesh
narrative: `.md` · corpus: `.txt` · court: per rules. **Full table now at the top of `CLAUDE.md`.**
⇒ **A rule applied without asking who it serves reproduces the failure it was written to fix.**

---

## S-108 · 2026-08-01 · THE HANDOFF'S OWN CONSTANTS WENT STALE **INSIDE THE TIDYUP THAT WROTE THEM**

**`V:\Ai\BU.MD` stated `verify_pointers 129` and `scars 106`. TidyUP2 CHECK 4 measured 130 and 107.**
Wrong within the hour, in the one file the next session boots from.

**Nothing external changed.** The same TidyUP wrote those numbers at step 9, then appended scar S-107
and a `POINTER` line at step 14 — invalidating its own handoff. There was no window in which the file
was correct.

⇒ **A COUNT WRITTEN INTO PROSE IS A COPY, AND COPIES ROT** — the same defect as the dated-handoff
scheme (four times), the `bts-fs` constant typed into its own reader (S-105), and the CoP365 demotion
written as prose while the renderer went on counting six nodes. **Here the copy and its source were in
the same document, minutes apart.**

⇒ **THE ORDER IS THE DEFECT, NOT THE CARELESSNESS.** Any routine that writes a summary *before* it
finishes changing the things summarised will do this every single time. Either the count is emitted
last, or it is not written down at all.

**The fix, and it is the honest one:** `BU.MD` now carries a line telling the reader **not to trust
those four numbers** and to run the tools instead — the tools are the source, the line is a
convenience. A number you cannot keep current should be labelled as untrustworthy rather than
silently maintained.

⚠ **And note which check caught it: CHECK 4, STALE-CONSTANT SWEEP — a step that exists solely because
this has happened before.** It found the defect in the routine that runs it.

### 🔴 IT THEN HAPPENED AGAIN, IMMEDIATELY, BECAUSE OF THIS ENTRY.
Correcting `BU.MD` to 130/107 and **writing this scar** took the scar count to **108** — making the
just-corrected number stale **in the same pass, from the same cause.** Twice in one routine.

**That is not an amusing coincidence; it is the proof.** The first correction treated the *instance*
(wrong number → right number) and left the *mechanism* untouched (a count copied into prose ahead of
further edits). A fix that leaves the mechanism running will be undone by the next edit, and here the
next edit was the fix itself.

⇒ **THE COUNTS ARE NOW DELETED FROM `BU.MD`, NOT CORRECTED.** The boot section names the four tools
and says to run them. **A number nobody can keep current should not be written down at all** — the
only version of this fix that survives contact with the next TidyUP.
⇒ **General form, and it is the whole session in one line: fixing the instance is not fixing the
class, and you can tell which you did by whether it breaks again the next time you touch it.**

## S-107 · 2026-08-01 · MY OWN DEDUPE TOOL REPORTED 53.9% OF THE CORPUS REDUNDANT. THE TRUE FIGURE WAS 15.8%. IT WAS CALLING SIX DIFFERENT TAX YEARS DUPLICATES OF EACH OTHER.

**Built `dedupe_corpus.py` to stop a node reading the same document three times and weighting it
triple. Ran it. It confidently proposed removing more than half the corpus.**

```
TAXES__2015-FedTaxReturn   <- near 0.99 dup of  TAXES__2017_TaxReturn
TAXES__2018_TaxReturn(1)   <- near 0.96 dup of  TAXES__2017_TaxReturn
TAXES__2021_TaxReturn      <- near 0.97 dup of  TAXES__TaxReturn-2024
TAXES__2020TaxReturn       <- near 0.95 dup of  TAXES__TaxReturn-2024
```

**Those are different years.** Tax forms are ~95% identical boilerplate: the vocabulary IS the form,
and the figures that distinguish one year from another are a rounding error in a cosine. The
containment guard — token count within 5%, 70% shared vocabulary — is *exactly what a 2015 return and
a 2017 return look like*, so it did not save it.

⇒ **I HAD WRITTEN THE WARNING INTO THE TOOL'S OWN DOCSTRING** — *"a high cosine is NOT proof of
duplication; two filings by the same lawyer about the same instrument score high"* — **and then
shipped a threshold that fails it.** Knowing the failure mode is not the same as defending against it.

⇒ **THE TELL WAS THE MAGNITUDE, AND IT IS GENERALISABLE: A METHOD THAT QUADRUPLES ITS OWN ANSWER IS
NOT A METHOD.** Exact hashing said 15.8%. The similarity pass said 53.9%. When two measurements of
the same quantity differ by 3.4×, the sophisticated one is not the better one — it is the one making
an assumption the simple one does not.

⇒ **AND THE ONLY REASON IT WAS CAUGHT: THE TOOL PRINTED ITS DROP LIST INSTEAD OF ACTING ON IT.**
Had `--dry-run` not been the default, six years of tax returns would have been "de-duplicated" before
anyone saw a filename. **PRINT THE DROP LIST. DO NOT ACT ON IT.**

**The fix:** near-duplicate detection is now **OFF by default** (`--near 0.0`), with this measurement
written into the flag's own help text, and it prints a warning when switched on. Exact hashing is
provable and stays.

⚠ **A footnote that is itself a small scar.** The first draft of this entry began a line
`**FIXED:**` — and `verify_pointers.py` immediately went **RED** with `unknown-opcode=1`, because an
ALL-CAPS word followed by a colon at the start of a line *is* the operator grammar. **Prose in a
control document is not free-form; it shares a namespace with the operators.** The checker caught it
in the same TidyUP that wrote it, which is the checker working exactly as designed — an unrecognised
operator must never be silently skipped.

⚠ **A second, quieter error in the same tool, found only because Keith set the rule:** the keep-one
selection sorted by `(-length, name)`. For BYTE-IDENTICAL files that degenerates to **alphabetical** —
a selection rule that looks principled and is arbitrary. It now keeps the **newest by mtime**.

## S-106 · 2026-07-31 · THE PUBLISH WROTE ITS LOG INTO THE TREE IT WAS PUBLISHING, AND ONE FAILED FILE SILENTLY DISABLED THE ENTIRE DELETE PASS

**Measured across THREE consecutive publishes tonight. Same error, same file, every time:**
```
ERROR : TIDYUP_PUBLISH.txt: can't copy - source file is being updated
        (size changed from 348556 to 349784)
ERROR : not deleting files as there were IO errors
ERROR : not deleting directories as there were IO errors
```
The wrapper writes its log to `…\PhD2_DATA_ARCHIVE\00_WORKING\TIDYUP_PUBLISH.txt` — **inside the
published subtree.** rclone opens it, the wrapper appends to it mid-copy, the size changes, the copy
fails, three retries fail identically.

⇒ **THE DAMAGE IS NOT THE ONE FILE. ONE IO ERROR SUPPRESSES THE WHOLE `sync`.** rclone refuses to
delete anything when any transfer errored — correctly, conservatively. So the confined delete pass,
**the only thing that prunes the mirror, has never once run.** **That is why TidyUP2 CHECK 9 has
never passed.** Not credentials, not the network, not R2: a self-reference.

⚠ **And the publish reported `exit=0` every time.** Content really did move; the top-level result
was honest about what it measured and silent about what it skipped. *A step that succeeds at its
main job can be failing at its other one, and an exit code will not tell you.*

⇒ **WHY IT SURVIVED SO LONG IS THE INSTRUCTIVE PART: THE FIX KEPT GETTING DELETED.** The wrapper is
a **disposable Desktop `.bat`** (Keith deletes them all; only `KDash.vbs` and `Judge-UPS.vbs`
persist). Every session that noticed the error fixed it *in the bat*, and the fix went in the bin
with the bat. **A defect in a disposable artifact is immortal.** ⇒ The correction had to move to a
durable surface: the logs now live in **`V:\Ai\_logs\`**, outside the published tree, with a
`README_LOGS_MOVED.md` left in `00_WORKING` explaining why nothing may write a log there again.

⚠ Three logs were sitting in the published subtree — `TIDYUP_PUBLISH.txt` (369,978 B),
`PUBLISH_TIDYUP.txt` (358,943 B), `R2_PUBLISH_LAST.log` (323,362 B) — **~1 MB of console spam
published to a public website nightly**, one of which was breaking the publish that carried it.

⇒ **STANDING: NEVER WRITE A LOG INSIDE A TREE THAT IS BEING SYNCED.** The observer must not sit
inside the thing it observes. Same family as S-98 (editing the derived file while the source stayed
authoritative) and S-105 (a constant copied into its own reader): **a thing that refers to itself is
where the silent failures live.**

## S-105 · 2026-07-31 · THE NIGHTLY RAIL CHECK REPORTED A RENAME'S SUCCESS AS A REGISTRATION FAILURE — FOR TWO DAYS, IN THE FILE WE READ AT BOOTUP

**`RAIL_HEALTH_2026-07-31.md` said `GEM registered: **NO**` and `GW registered: **NO**`.**
Yesterday both were ✓. I opened this session by flagging it as a regression from the BFast move.

**It was not a regression. It was the checker.**

On 2026-07-30 the MCP server was renamed `bts-fs` → **`BFast`**. `wire_clients.py` holds
`NAME = "BFast"` and `OLD_NAMES = ["bts-fs"]`, and its rename pass **deliberately strips the old key
from every client config** so no node ends up with one server registered twice. `rail_check.py`
went on grepping for the literal `"bts-fs"` and `"mcp_servers.bts-fs"`.

⇒ **The rename removed exactly the string the checker was looking for. The cleanup WAS the alarm.**
Both clients were correctly wired the whole time; the daily health report has been lying since.

⇒ **THE DEFECT IS TWO COPIES OF ONE CONSTANT.** The name was defined in the module that WRITES the
config and typed again, by hand, into the module that READS it. Renaming updated the writer. Nothing
could have kept the reader in step, because nothing connected them. `rail_check` now **imports
`NAME` and `OLD_NAMES` from `wire_clients`** — one definition, two readers, and a future rename
cannot desynchronise them.

⚠ **And the two states were being collapsed.** "Old name present, new name absent" means *this
client missed the rename pass*; "neither present" means *unregistered*. They need opposite fixes and
both rendered as `**NO**`. There is now a distinct **`STALE NAME`** result that names the remedy.

⇒ **THIS IS THE THIRD SHAPE OF ONE FAILURE IN ONE SESSION, AND THAT IS THE REAL ENTRY:**
S-98 edited a DERIVED file while the SOURCE stayed authoritative · the CoP365 demotion tonight was
written as PROSE in `rails.toml` while the renderer went on counting six nodes from the data · and
this is a CONSTANT copied by hand across two modules. **Every one is the same mistake — a fact
stored in two places, where updating one is indistinguishable from updating both.**
⇒ **BEFORE CHANGING A NAME, GREP FOR IT. The readers do not announce themselves.**
⚠ **And note what it cost even though nothing was broken:** a false RED in the boot-time health file
sent this session's first report to Keith with a phantom regression in it. **A check that cries wolf
gets muted, and a muted check is worse than none** — the ROLD already says so about Desktop bats.
Here the wolf was the checker's own vocabulary.

## S-104 · 2026-07-31 · "CONTENTS ALREADY RECOVERED AND MERGED" WAS TRUE OF THE TWO FILES SOMEONE LOOKED AT, AND WAS WRITTEN ABOUT THE WHOLE DIRECTORY

**`V:\Ai\BU.MD` licensed a deletion on a check that covered 2 of 6 files.** The handoff's loose-end
1 read: *"Delete the two literal-backslash directories inside `BTS_MESH\` … **Contents already
recovered and merged, so they are now pure garbage.**"* It shipped with a staged native `.bat`,
because the mount creates those directories but will not delete them.

**Measured tonight before staging that bat — file by file, with `cmp`:**

| file | claimed | actual |
|---|---|---|
| 2 academic PDFs in `…\+Papers` | merged | ✅ **byte-identical** in the real tree |
| `_oagrab_manifest.json` | merged | 🔴 **DIFFERS from the real copy** |
| `SGH_2026-07-31_194710_47d96b.md` | merged | 🔴 **EXISTS NOWHERE ELSE** |
| `SGH_2026-07-31_195011_781fa9.md` | merged | 🔴 **EXISTS NOWHERE ELSE** |
| `SGH_2026-07-31_195103_781fa9.md` | merged | 🔴 **EXISTS NOWHERE ELSE** |

**19.8 KB of SGH returns from 19:47–19:51 tonight, plus a manifest, one double-click from gone.**
All four recovered under new names, sha256 verified on both sides, before anything was deleted.

⇒ **THIS IS S-97 INVERTED, AND THAT IS THE POINT.** S-97 says *an ABSENCE inherits the scope of its
query.* This is a **PRESENCE** check with the same defect: someone confirmed the two files they had
noticed (S-103 records exactly that `ls`, and it was correct), then wrote the conclusion **over the
directory** rather than over the two files. The sentence that reached the next session was not
*"the two PDFs are merged"* — it was *"contents are merged."* **The quantifier widened in the
writing-up, and nothing downstream could tell.**

⇒ **THE SCOPE OF A CLAIM MUST BE THE SCOPE OF ITS MEASUREMENT — SAY WHAT YOU COUNTED.**
*"2 of 2 files compared, identical"* is a finding. *"Contents already merged"* is a summary of a
finding with the sample size deleted, and by the time it is a licence to delete, the sample size is
the only thing that mattered.

⚠ **And note WHEN the stray files were written: 19:47–19:51, the same evening, AFTER the state that
the "already merged" claim described.** A directory that a live bug is still writing into cannot be
certified as fully recovered at any instant — the certification expires the moment the bug fires
again. **The delete step was queued while its own precondition was still being invalidated.**
⇒ **FIX THE WRITER BEFORE YOU CLEAN UP AFTER IT.** `bts_sgh.SPILL_DIR` — the hardcoded
`r"V:\Research4\…"` literal that creates these directories under Linux (S-101) — was routed through
`bts_paths` tonight, so the source is closed. An audit of every remaining `r"V:\…"` literal in
`BTS_MESH\` ran in the same pass: **`SPILL_DIR` was the last functional one.** The rest are
docstrings, error text, and the `_migrate_*` archaeology.

## S-103 · 2026-07-31 · I RAISED THE ALARM THREE TIMES BEFORE RUNNING THE CHEAP CHECK THAT DOWNGRADED IT
**One TidyUP2 pass. Three escalations, each retracted minutes later by a check costing seconds.**

1. Found two academic PDFs in a junk directory → reported **"that's not spilled chatter, that's lost
   research."** → `ls` of the real folder: **both already there, byte-identical.** Not lost.
2. Found the folder manifests disjoint → reported **"the only DOI record for both, nearly
   destroyed."** → `grep 00_DOI_INDEX.md`: **both DOIs already indexed.** Provenance never at risk.
3. Published **"cost of the entire exercise: about $0.02"** → CHECK 3 the same evening: it was the
   xAI ledger alone, omitted GEM, and used a raw figure **without the 6.3× correction established
   hours earlier in that same session.** True figure ~$0.078, ~4× understated.

🔴 **NO HARM REACHED KEITH, AND THAT IS NOT THE SAME AS NO DEFECT.** Each retraction happened before
he acted. But the first two were stated to him at full volume — *"lost research," "nearly destroyed"*
— and had he moved on either, he would have chased nothing. **The verification I eventually ran was
available before I spoke, and cost one command.**

⇒ **ANNOUNCE AT THE CONFIDENCE YOU HAVE MEASURED, NOT THE CONFIDENCE THE FINDING WOULD DESERVE IF
TRUE.** A discovery is exciting in proportion to its severity, and severity is exactly what has not
been checked yet. The urge to report scales with the thing that most needs verifying first.
⇒ **THIS IS S-97's SHAPE ONE LEVEL IN.** There, a null result was reported without its scope. Here, a
positive result was reported without its confirmation. **Both are claims outrunning their evidence.**
⇒ **AND ITEM 3 IS THE WORST OF THE THREE,** because it shipped: a document *criticising uncorrected
spend estimates* carried one, onto Keith's Desktop, in a section listing that session's findings.
**Writing the rule down is not the same as being governed by it** — the same lesson as S-98 and S-99,
now for the third time in one day.

## S-102 · 2026-07-31 · WE GOVERNED THE WRONG DIRECTION — the risk was never overspend, it was 94.5% EXPIRY
**Measured from Google's own billing export** (`BTS_MESH\gcp_billing_2026-07.csv`, authoritative):
```
Vertex AI   $2.910922   the ONLY service line     tax $0.00
elapsed 16 days -> $0.182/day -> projected $16.37 of $300 by 2026-10-13
🔴 PROJECTED UNUSED AT EXPIRY: $283.63  =  94.5%
to consume the credit would take 22x the current burn rate
```
**What we built around this:** a spend ledger, a calibration factor, a burn-rate panel, warning
thresholds, a `projected_waste` field, and repeated sessions of reconciliation work.
**What was actually true the whole time: the credit is unspendable at our rate.** Every governor
guarded a boundary we were never within two orders of magnitude of crossing, while the real event —
$283 evaporating on a fixed date — sat in the CLOCKS table as a line nobody costed.

⇒ **A GOVERNOR IS A CLAIM ABOUT WHICH DIRECTION IS DANGEROUS, AND THAT CLAIM NEEDS MEASURING TOO.**
We measured spend obsessively and never once measured *spend against remaining time*. One division.
⇒ Related and equally wrong-way-round: the estimator is **6.3x low** (ours $0.46, Google $2.91) after
a 07-16 sample said 2.39x. **Two samples 2.6x apart are not a calibration curve.** And the gap is
**PRICING, NOT COUNTING** — our token counts reach 86% of the real bill at pro/long-context rates, so
the tokens are roughly right and the price table is wrong. The standing "uncounted thinking tokens"
hypothesis is INSUFFICIENT on its own.
⇒ **DELETE THE DOLLAR ESTIMATE, KEEP THE TOKEN COUNTER, READ THE CONSOLE.** Do not tune the factor.
⚠ Unsettled: the export shows `Other savings = $0.00` while the console says $297.09/$300, so the
money WAS credit-funded. Our 07-16 note that "Other savings = the credit draw" is therefore wrong
somewhere. **Do not cite that rule again until it is settled.**

## S-101 · 2026-07-31 · A HARDCODED WINDOWS PATH MADE A DIRECTORY NAMED `V:\Research4\...` INSIDE THE TREE
`bts_sgh.SPILL_DIR` is the literal string `V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\SGH_returns`.
Run from the **Linux sandbox**, that is not a path — it is a filename. `os.makedirs` duly created a
directory *called* `V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\SGH_returns`, one entry, inside
`BTS_MESH\`. Every spilled answer landed there.

🔴 **IT HAD BEEN HAPPENING FOR FIVE DAYS.** A second such directory sits beside it —
`V:\Research4\Ai\PhD2_DATA_ARCHIVE\papers\Grok_on_this\+Papers`, **dated 2026-07-26**. Nothing
noticed, because **the spill reported success**: it wrote a file, returned a path, and the path
string looked exactly right in the log.

⇒ **THIS IS THE `bts_paths` DEFECT, STILL UNFIXED IN ITS THIRD MODULE.** The known cure exists
(`bts_paths` resolves per-OS) and `SPILL_DIR` never got it. A hardcoded absolute path does not fail
on the wrong OS — **it succeeds against the wrong object**, which is strictly worse.
⇒ **AUDIT EVERY `r"V:\..."` LITERAL IN `BTS_MESH\` AND ROUTE IT THROUGH `bts_paths`.**
⇒ And the tell to remember: **a directory whose name contains a colon or a backslash is proof that a
Windows path was used as a filename.** One `ls` would have caught five days of it.

## S-100 · 2026-07-31 · A NODE WAS "LIVE, conf=V" FOR TWO DAYS AND HAD NEVER ONCE BEEN CALLED
**GW** (`grok-build-0.1`) was recorded `state = "LIVE"`, `conf = "V"`, `measured = 2026-07-30`.
The first genuine call, tonight, failed instantly:
```
HTTP 400 invalid-argument — "Model grok-build-0.1 does not support parameter reasoningEffort"
```
`bts_sgh.ask()` sends `reasoning_effort` unconditionally. **Every call to GW through this module had
always failed.** The node could not have worked on the day it was marked working.

**Why it looked live:** GW shares the **xAI rail** with SGH, and that rail *was* measured — 1530 ms,
`conf="V"`. The evidence was real and it was about the neighbour.
⇒ **A RAIL THAT ANSWERS IS NOT A NODE THAT WORKS.** Node liveness must be proven by calling **that
node** and reading **its** output. Shared-transport evidence proves transport.
⇒ Fixed with `_MODEL_TAKES_EFFORT()` — a deny-list, not an allow-list, so a *new* reasoning model
works by default and a non-reasoning one announces itself with a 400 rather than failing silently.
⇒ **NOTHING IN THE MESH WOULD HAVE FOUND THIS.** No check calls a node. It surfaced only because
Keith asked *"what is checking GW?"* — and the answer was nothing. **Four rails remain UNMEASURED and
two nodes (CoPG, CoP365) have never been exercised from here at all.** Same shape, still open.

## S-99 · 2026-07-31 · THE CORRECTION INHERITED THE DEFECT IT CORRECTED — and a checker scoped to where I was looking
**Three steps, one session, the same error each time in a different place.**

**1.** Cowork ran `gcloud projects list`, found no `project-5a33f910-…`, and wrote a `[[discrepancy]]`
saying the project **"DOES NOT EXIST"** — tagged **`conf = "V"`**. Wrong: the query ran as
`keith.bbf@gmail.com`; the project is Joanna's.

**2.** TidyUP2 CHECK 4 caught it. Cowork corrected the fact and wrote *"it is under
`joanna.bbf@gmail.com`"* — tagged **`conf = "V"` again**, while reading it out of
`00_HARVEST_2026-07-16.md`, a **15-day-old document**. **Nothing was measured.** `bts_vertex.py`
cannot settle it either: its endpoint is `publishers/google/models/…` and **carries no project ID at
all**, so the API key alone determines what gets billed, and that is opaque from this box.

🔴 **BEING WRONG ABOUT THE FACT MADE ME CAREFUL ABOUT THE FACT AND CARELESS ABOUT THE TAG.** The
correction was written in a hurry to be right, and a confidence tag applied by the same habit that
produced the error is not a check on the error. **`conf` was decoration in the very entry created to
record a confidence failure.**

**3.** Cowork then wrote `verify_conf.py` — and pointed it at **`rails.toml` alone**. Keith:
> *"Check all, that's the purpose of TU2."*

**That scope was the same defect a third time.** A checker aimed only where I happened to be looking
produces an absence that reflects the search, not the world — which is *precisely* what S-97 is
about. Re-scoped to glob every `.toml` recursively, it found **6 violations, and 5 were in
`registries.toml`** — a file I had no suspicion of and would never have pointed it at.
**The hand-picked scope would have returned GREEN and been believed.**

⇒ **A CHECKER'S SCOPE IS PART OF ITS RESULT.** "No violations found" means nothing until you say
where it looked. Glob the tree; let new files be covered the day they appear, not the day someone
remembers them.
⇒ **WHEN A CORRECTION IS WRITTEN, RE-RUN THE CHECKS AGAINST THE CORRECTION ITSELF.** It was authored
under exactly the conditions that produce errors: hurry, embarrassment, and the belief that the
lesson has already been learned.
⇒ **THE SCHEMA WAS STATED IN THE HEADER OF THE FILE THAT DEFINES IT AND ENFORCED NOWHERE.** Same
shape as S-98's docstring warning. **Twice in one session, prose was mistaken for a control.**

**SETTLED, PARTLY:** Keith confirmed in-session that the project is under Joanna. That is recorded as
**`provenance = "HUMAN"`**, not as an instrument reading — he is authoritative about his own accounts;
a document is not. ⚠ **The 2026-08-14 soft-delete clock remains UNMEASURED** — ownership is not the
same question as what is pending deletion, and nothing has queried Joanna's estate.

---
### ✅ CLOSED THE SAME EVENING — MEASURED UNDER BOTH IDENTITIES. 17:58, `GCP_JOANNA.txt`.
```
--- 0. ACTIVE ACCOUNT ---            joanna.bbf@gmail.com     <- printed FIRST, per the new rule
--- 1. PENDING DELETION ---          (empty)
--- 2. ALL PROJECTS ---              project-5a33f910-1251-4d6a-bf9 / 614387154970 / ACTIVE
--- 3. BILLING ACCOUNTS ---          010E47-824B53-7202F5   OPEN: True
--- 4. THE CREDIT PROJECT ---        billingEnabled: true
```
**The project exists, is ACTIVE, and is billing-linked. Nothing is pending deletion under EITHER
account. The 2026-08-14 clock is a genuine non-event** — and this time the claim carries its scope.

🟢 **THE CONTROL WORKED ON ITS FIRST OUTING.** The erratum bat printed the active account as step 0,
**before any finding**, because S-97 said to. The original bat printed the same fact in section 3 and
Cowork read past it. **Same information, different position, opposite outcome.** ⇒ *Order is part of
a control's design, not cosmetics: put the scope-defining fact where it cannot be scrolled past.*

⚠ **AND THE FIX ARMED THE MIRROR-IMAGE TRAP.** `gcloud auth login joanna…` made **JOANNA the ACTIVE
gcloud account**. Every subsequent gcloud command now answers for *her* estate until someone switches
back — the identical failure pointed the other way. **Recorded as `live_hazard` in `rails.toml`**, and
the standing rule (state the account inside the finding) covers it in either direction.

## S-98 · 2026-07-31 · A WARNING IN A DOCSTRING IS NOT A CONTROL — Cowork edited the DERIVED file, hours after writing the rule
**The rule was written by Cowork, in `scars.py`, at the top of the same file:**
> ⚠ `SCARS.md` REMAINS THE SOURCE OF TRUTH while both exist. This file is a derived INDEX, not a
> replacement, and `--rebuild` regenerates it. **Do not hand-edit `scars.jsonl`.**

**Hours later, at TidyUP, Cowork appended S-97 straight to `scars.jsonl`.**

🔴 **THE NEAR-MISS IS THE POINT.** `--rebuild` regenerates the JSONL *from* `SCARS.md`. The scar
would have been **erased by the next rebuild — silently, and with the rebuild's own
`cited == listed` check PASSING**, because that check compares the Markdown to itself and never
looks at the JSONL it is about to overwrite. **A control that passes while the loss occurs is worse
than no control**: it certifies the wreck.

**It was caught by LUCK, and the luck is worth naming.** The hand-written record also used the wrong
key (`clas` instead of `class`), which threw a `KeyError` on the next query. **A correctly-shaped
hand-edit would have been invisible until the rebuild ate it.** Cowork did not detect its own
violation; a typo did.

⇒ **THIS IS THE `TOOLS_INDEX` DEFECT WEARING THE OTHER FACE.** There, a file *claimed* a generator
that did not exist, so people edited the source and the index rotted. Here, a generator *does* exist
and the derived file carries **no in-band marking at all** — JSONL has no comment syntax, so nothing
in `scars.jsonl` says "I am derived." **Both failures are the same missing thing: the direction of
generation is not enforced anywhere a writer will encounter it.**

**FIXED, SAME SESSION —** `scars.py` now runs a `drift()` check on **every** invocation, not just
`--rebuild`: it counts `## S-` headings against JSONL lines and **exits 3 rather than answer a
question from a record known to be inconsistent.** Shown to fail: a well-formed hand-edit was planted
in the JSONL and the check named it correctly, including which direction the drift ran.

⇒ **THE STANDING RULE, GENERALISED:** *when a file is derived, the check belongs in the READER, not
in a comment.* Documentation is advice to whoever reads it; only code is advice to whoever doesn't.
And **the author of a rule gets no exemption from it** — Cowork wrote this one and broke it the same
day, which is the whole reason the control now exists in code.

🟢 **READ OUT 2026-07-31: THE PRINTER PRINTED.** The old port carries data. ⇒ **The port branch is
eliminated; the fault is the ENCLOSURE or the DISK.** Caveat kept for honesty: a printer is USB 2.0,
so this proves the port's 2.0 lanes. It does not fully exclude damaged SuperSpeed pairs on that
port — a strong result, not an airtight one, and it does not change the next step.

**Current state** — powered off, cooling, routers removed, cover open. **NEXT, ONCE COLD:** power on in the
ORIGINAL port. Enumerates -> reads only, copy anything unique off FIRST. Does not enumerate -> the
enclosure bridge or the disk, and the cheap test is a different dock before anything is written off.

**THE LESSON IS ABOUT COWORK, NOT THE HARDWARE.** Three wrong claims about one five-minute event —
a spontaneous disconnect that never happened, a cable swap that never happened, and a
"contaminated test" that was in fact well controlled. **Each was asserted confidently from an
imagined detail rather than from what Keith actually said.** Same family as summing a cumulative
counter (PLM-08) and reading the wrong dict key (PLM-26).
⇒ **When the observation is someone else's, QUOTE IT BACK BEFORE REASONING FROM IT.** Cowork cannot
see the machine; every physical fact in this scar arrived through one narrow channel, and it
mis-transcribed that channel three times in a row.

**THE REAL SCAR IS NOT THE HARDWARE. NOTHING WAS WATCHING.**
The 17.7 -> 0.6 slide happened across eighteen days and was noticed only because Cowork added V: to
the drive table for an unrelated reason and re-ran the benchmark. **There is no drive-health monitor
in this mesh at all**, and the one signal that would have caught it early — **SMART temperature** —
is not read by anything. `rail_check` probes four API rails daily and zero disks.
⇒ **The monitor registry (PLM-13) must include DRIVE HEALTH, and temperature specifically.** A rail
that answers HTTP 200 is monitored; the disk holding the recovery copy of 606 restored PDFs was not.

**And a physical rule, because it cost a 7.3 TB mirror:** ⛔ **NOTHING SITS ON TOP OF AN ENCLOSURE.**
It has no fan, its only cooling is the case surface, and covering it converts a passive heatsink into
an oven. The routers had been there for weeks.

---

## S-131 · 2026-08-11 · **THE FILE NAMED `RECORD_ALL.txt` WAS `record_core`. TWO PAID BENCH OPINIONS RULED ON 51 OF 74 DOCUMENTS.**

**Measured host-side, both directions** (`Grep` on the bundle, `Glob` on the directory — not from the
mount alone, per S-05/S-06/S-07):

    RECORD_ALL.txt      51 documents   — byte-identical document set to record_core\
    record\             74 documents
    missing entirely    26  =  ALL 18 of 09_JASPER_UCC  +  ALL 8 of 05_EMAILS

**What no judge in this war game has ever seen:** the Cashmere UCC-1 equipment schedule · the UCC-3
termination of 2025-01-07 · the Divorce Decree · the Calahan v Yerokhin mediation · PJLA Certificate
L26-171 with the `AL-SOP` scope · the OMMA license expiry · the Instagram / LinkedIn / Facebook
successor evidence · the annotated map · **and every one of Vadim Yerokhin's emails.**

⇒ **The two bench opinions disagree by 3.6× — `$8,180` versus a net `$29,643`, both self-reporting
HIGH confidence — and both were reached with the entire asset-transfer and successor case removed
from the record.** Neither opinion *failed* to reach Abraxas Scientific. It could not. The documents
were not in the file. Every exhibit staged for Blocks C, D and H of the August 26 deposition is in
the missing 18.

**THE NAME WAS DOING THE WORK A CHECK SHOULD HAVE DONE.** `RECORD_ALL` asserts completeness in the
filename, so nothing downstream ever counted it. This is C-12 / S-117 exactly — *presence is not
coverage* — with one turn of the screw: **there, the bundle was present and hollow; here, the bundle
was named for the whole and contained a part.** A name is a claim, and a claim in a filename is the
one least likely to be tested, because reading it feels like verifying it.

⇒ **THE CONTROL: a bundle states its own document count in its first line, and the consumer asserts
that count against the source directory before the bundle is used.** `record_reindex.py --check`
already does this for `00_INDEX.txt`. Nothing did it for the bundle that is actually fed to the
paid nodes. **Wire the same check into the feed, and make a bundle that cannot state its provenance
unusable rather than merely suspect.**

### And the second finding, which is smaller and sharper
`record_trim.py` excerpted three documents in place. **The trimming is good work and is not the
scar** — each excerpt carries a header naming the original, the regex that kept it, the line counts,
the reason, and inline `[... N lines omitted ...]` markers, and it instructs the reader to say so
rather than infer across a gap. That is how excerpting should be done.

**But one rule was written for one of two pleaded faults.** The Agilent maintenance manual was cut
`173,840 → 39,955` bytes by `/autosampler|needle|tray|vial|arm|self.?test|ALS/i`. The counterclaim
pleads the autosampler **and** *"a leak due to a faulty valve."* Term counts, live versus original:

    autosampler   51 / 49      needle   62 / 60      <- the fault the rule was written for
    valve         37 / 119     seal     52 / 97      <- the fault it was not
    replace       10 / 50      lamp      1 / 34

⇒ **An excerpting rule is a theory of the case, and it must be checked against every element it will
be asked about — not against the one that prompted it.** Restored from `_orig\` in the rebuild.

**REBUILT:** `V:\Ai\Legal\WARGAME\RECORD_FULL_2026-08-11.txt` — 74 documents, 1,687,767 chars,
~421,941 tokens, sha256 `c026296d31ba2163`, read back and re-counted after writing. The old bundle
is left in place unaltered, because the two existing opinions are only interpretable against the
record they actually read.

---

## S-132 · 2026-08-11 · **THE KEY WAS WRITTEN, IT WAS VALID TOML, AND IT LANDED IN THE WRONG TABLE. `doctor` SAID "parse ok" ON THE SAME SCREEN AS "model default."**

`CODEX SETUP.bat` finished with `echo model = "gpt-5.6">>config.toml`. But step 4,
`codex mcp add bfast`, had already written `[mcp_servers.bfast]` into that file.

**In TOML a bare key after a table header belongs to that table.** So the append landed as
`mcp_servers.bfast.model` — a key nothing reads — and the file parsed perfectly. `codex doctor`
printed both of these, four lines apart, and only the second was the truth:

    config.toml parse       ok
    model                   <default> · openai

⇒ **A PARSE CHECK CANNOT CATCH MISPLACEMENT, BECAUSE MISPLACEMENT IS NOT MALFORMATION.** The
validator answers *"is this well-formed?"* and the question that mattered was *"is this where I
meant to put it?"* Those look like the same check and are not.

**This is BFast's own scar, in a new costume.** `roots.json` has carried the sentence since
2026-07-31: *"a node once wrote to `research4:handoff/` when it meant `handoff:`, verified the bytes,
and reported success. **Verifying content is not verifying destination.**"* The bytes were written.
They were valid. They were in the wrong container. Same defect, different file format, four hundred
lines away from where the warning is written down — **and the warning did not fire, because it lives
in a config file for a different tool.**

⇒ **THE CONTROL: never append a top-level key to a file that may already contain tables.** Read,
place the scalar keys FIRST, write the tables after, and **assert the key RESOLVES at top level after
the write** — not that it is present somewhere in the text. `codex_config_fix.py` does exactly that
and refuses to write when the assertion fails or when any pre-existing top-level entry would be lost.

⚠ **And note which half of the tool caught it.** `codex doctor` reported the true state plainly and
for free. The setup script reported `Default model set to gpt-5.6.` — **a claim about what it
intended, printed before anything had been verified.** A script that narrates its intent as an
outcome is a script that will lie the first time it is wrong.

## S-133 · 2026-08-11 · **THE FIX FOR S-132 WAS WRITTEN, REGISTERED, DESCRIBED AT LENGTH, AND NEVER APPLIED — AND THE HANDOFF RECORDED IT AS "VERIFIED BY RE-READ."**

Hours after S-132 was recorded, `codex_config_fix.py` was written to close it. The tool is correct:
it places the scalar keys first, refuses to write a result that would not parse, refuses unless every
key **resolves** at top level on a re-read **from disk**, and refuses if any pre-existing top-level
entry would be lost. It was registered in both `00_TOOLS_INDEX.md` and `TOOLS_REGISTRY.json` in the
same pass. `BU.MD` then recorded, in the PLUMBING queue:

> *"Policy set and verified by re-read: `model gpt-5.6` · `approval_policy never` ·
> `sandbox_mode workspace-write` · writable roots = the three BFast roots · `network_access true`."*

**Read host-side at the next BootUP, `%USERPROFILE%\.codex\config.toml` was 95 bytes:**

    model = "gpt-5.6"

    [mcp_servers.bfast]
    command = "python"
    args = ['V:\Ai\BFast\bfast.py']

**One of the five keys landed. `approval_policy`, `sandbox_mode`, `writable_roots` and
`network_access` are absent, and `[sandbox_workspace_write]` does not exist.** The dated backup
`config.toml.bak-2026-08-11` holds the *original* misplaced-key state, so the fix ran, or began to —
`mtime` 14:45 on the backup, **14:48 on the config** — and something overwrote it three minutes
later. The likeliest candidate is the spent `CODEX FIX MODEL.bat`, which addressed the model line
only. **The sequence is inferred; the end state is measured.**

⇒ **This is `S-128` / `C-05` — REPORTED IS NOT REPAIRED — committed against the same session's own
work, hours after that session recorded the same lesson about someone else's.** On 6 Aug a session
found the wrong-counsel defect, described it at length, listed the affected files and edited none of
them. Here a session found a config defect, **wrote a whole tool for it**, and did not confirm the
tool's output.

⇒ **And it is `S-131` in a second costume, on the same day.** *Reading the description felt like
verifying the file.* There, a bundle named `RECORD_ALL.txt` held 51 of 74 documents and two paid
bench opinions ruled on the short set. Here, a queue entry saying *"set and verified by re-read"* was
read four times by two routines and never once compared to five bytes of TOML. **The richer and more
specific the description, the less likely anyone is to check it** — `RECORD_ALL` was a filename,
this was a full itemized list with the verification method stated, and the itemization is what made
it credible.

⇒ **THE CONTROL, and it is one line, not a habit:** a session that writes a repair tool **runs it and
pastes the re-read in the same turn**, or records the defect as OPEN. **"Verified by re-read" is a
claim about an artifact, so it is subject to the artifact rule: assert it.** `grep` the config, count
the keys, and put the count in the handoff — *four of five keys present* is a sentence that cannot be
written without looking.

⚠ **Third-order note, because it is the part that would have bitten hardest:** the missing key is
`approval_policy = "never"`. Without it Codex **prompts**, so the first scripted `codex exec` would
have stopped and waited — on Keith's screen, which is off limits — and the rail would have looked
hung rather than unconfigured. **A policy that is absent does not fail loudly; it fails as an
interactive prompt nobody is sitting in front of.**

## S-134 · 2026-08-11 · **THE MONITORS WORKED WHENEVER ANYONE WAS WATCHING THEM. FOUR TOOLS DIED ON AN EMOJI, AND TWO OF THEM EXITED 0 WHILE DOING IT.**

`rail_check.py`, `bts_drive_health.py`, `bench_drive.py` and `bts_kdash_feed.py` all print `🔴` and
box-drawing characters. Windows falls back to **cp1252 the moment stdout is REDIRECTED**, so every
one of them raised

    UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f534'

**Run by hand in a console they work perfectly.** Redirection is exactly what a scheduled task does.

⇒ **THE FAILURE MODE SELECTED FOR BEING UNOBSERVED.** Any interactive check confirmed health; only
the unattended runs died, and nobody is present by definition.

**And the reporting was worse than the crash.** `rail_check` and `bts_kdash_feed` **still exited 0**,
and the native `BTS Rail Check` task recorded **`Last Result: 0`** — success — for **five consecutive
days that produced no file**: 08-05, 08-06, 08-09, 08-10, 08-11. The consequences had all been
recorded separately as their own mysteries: drive health permanently `UNKNOWN`, `dash.json` frozen at
2026-07-29, `verify_conf` "failing" with exit 1, and `RAIL_HEALTH` days simply missing. **Four open
items, one cause.**

⇒ **THE CONTROL:** every child process gets `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` — now forced
by `bts_runner` for everything it launches. After that single change all four ran, `verify_conf`
returned **GREEN** (its exit 1 had been the crash, never a schema violation), and
`RAIL_HEALTH_2026-08-11.md` and a fresh `dash.json` both appeared within a minute.

⚠ **`CLAUDE.md` ALREADY CARRIED THIS RULE AND IT DID NOT REACH.** *"NO EMOJI IN A `.bat` — cmd's
codepage cannot render them and mangles the line."* Written for cmd, **never carried across to the
Python tools' own stdout**, which meets the identical codepage on the identical machine. **A rule
scoped to the instance instead of the class is a rule that will be needed again.**

## S-135 · 2026-08-11 · **A CORRECTLY PLACED KEY WITH AN INVALID VALUE IS STILL BROKEN, AND NO STRUCTURAL CHECK CAN SEE IT**

S-132 was a key in the **wrong table**. `codex_config_fix.py` was written to fix exactly that, and it
did: `model = "gpt-5.6"` sat at top level, parsed, and **resolved** on a re-read from disk. Every
check the tool makes passed. Then the first real call died at the API:

> `The 'gpt-5.6' model is not supported when using Codex with a ChatGPT account.`

The account's own `~/.codex/models_cache.json` — fetched by Codex itself — offers `gpt-5.6-terra`,
`gpt-5.6-luna`, `gpt-5.5`, `gpt-5.4-mini`. **Bare `gpt-5.6` is not among them and never was.**

⇒ **A parse check asks "is this file well formed." A resolve check asks "is the key where I meant
it." NEITHER ASKS "is this value one the account can actually use."** `doctor` printed
`config.toml parse ok` and `model gpt-5.6` on the same screen — both true, both useless.
⇒ **THE CONTROL:** `codex_config_fix.validate_model()` now asserts the value against the account's
own cache and **refuses to write a model the account cannot use.** An absent cache returns
**UNKNOWN, never OK** — an unreadable authority is not a passing grade.
⚠ **The same read closed a standing unknown:** every model on the account carries
`context_window = 272000`, so **OA cannot hold the ~422k-token war-game record.** That question had
been open as "UNKNOWN under chatgpt auth" and was answered by a file already on disk.

## S-136 · 2026-08-11 · **THE RUNNER'S OWN SELFTEST REFUSED TO CERTIFY IT, AND THAT REFUSAL IS THE ONLY REASON A BROKEN MONITOR WAS NOT SCHEDULED INTO SERVICE**

`bts_runner.py` resolved each job's command **before** renaming the file into `running\` to claim it.
So `cmd` was handed a path that no longer existed, and **every job returned `rc=1` in 0.1 s —
including the one the selftest expects to SUCCEED.**

The installer refused to register the task: *"REFUSING TO SCHEDULE A RUNNER THAT FAILS ITS OWN
SELFTEST."* Fixed, re-run, and the second attempt returned **`rc=0` for the good job and `rc=7`
preserved exactly for the deliberately failing one.**

⇒ **VERIFYING A PATH IS NOT VERIFYING THE PATH YOU ARE ABOUT TO USE.** Same family as BFast's
*"verifying content is not verifying destination"* — the object checked and the object used were not
the same object.
⇒ **And the general point, which is why this is a scar and not a bug report:** a monitor that has
never been shown to FAIL is decoration. This one had a negative control that planted a deliberate
failure, and **the deliberate failure is what caught the real one** — the passing case looked
identical to the broken case, because both were `rc=1`.

⚠ **A second defect surfaced in the same run and was fixed with it:** a name collision on the move
out of `running\` was swallowed by a bare `except OSError: pass`, leaving `_selftest_ok.bat` in
**both** `running\` and `failed\`. It would have reported as STALE forever and read as a hung
process. **A silently swallowed move is how a queue grows ghosts.**

## S-137 · 2026-08-11 · **`gdx_fresh_auth.py` DISPOSED OF THE WORKING CREDENTIAL BEFORE PROVING IT COULD CREATE A REPLACEMENT**

Its order of operations was:

1. move the live credential to `credentials.json.dead_2026-08-11_2137`
2. announce that a browser will open
3. **discover `pydrive2` was not installed, and stop**

GDX went from *"expired consent, refresh returns invalid_grant"* to *"`Ai\credentials.json` not
found"* — **strictly worse**, and caused by the repair rather than the fault. It survived only
because the rule *"Cowork never deletes, it stages"* meant the file was **moved**, not removed.

The root cause was mundane and is worth recording precisely: **`pydrive2` was installed under Python
3.13 while `gdx_fresh_auth.py` runs under 3.14.** The dependency existed on the machine and was
invisible to the interpreter that needed it.

⇒ **THE CONTROL: check every dependency BEFORE touching the thing being replaced.** A repair script
must not destroy its own fallback in step 1. Import first, move second.
⚠ **And "installed" is interpreter-scoped, not machine-scoped.** `pip list` on the wrong version is
the same false negative as a mount that reads the wrong file — the answer is confidently about
something other than what was asked.


## S-138 · 2026-08-12 · **FOUR CHECKS CRIED WOLF ON HEALTHY FILES IN A SINGLE SESSION, AND EVERY ONE LOOKED LIKE A REAL DEFECT**

The session's whole purpose was fixing checks that reported success while broken. It found the
mirror-image failure four times, and each was persuasive:

1. **`verify_pointers` closed RED on two lines of English.** `SCARS.md` line 1635 `**GEM:**` and
   2636 `**REBUILT:**` matched the operator grammar. `failed=0` throughout — **no pointer was ever
   broken**, and the repo had been reported RED on that basis.
2. **The C.O.S. schema check flagged 29 of 29 entries**, because it compared each against
   *whichever entry happened to have the most keys* rather than against a declared schema. 29 of 29
   findings is noise, and the noise **hid the one real fault** (C-29 carrying `detail` where the
   other 28 carry `rule`).
3. **A C-29 assertion reported the correction had not landed**, because it sliced 400 characters
   after the key and five explanatory comment lines had pushed `rule =` past the window.
4. **A truncation control flagged six healthy JSON files**, including `TOOLS_REGISTRY.json`, which
   it then declared "unreadable" — killing an entire section of the sweep. It compared
   `len(read_text().encode())` against `stat().st_size`, and on Windows `read_text` performs
   **universal newline translation**: a healthy CRLF file reads back shorter by exactly its line
   count. **That is the decoder working, not the mount lying.**

**In all four the CHECK was wrong and the FILE was fine.** Each was confirmed host-side before
anything was changed, which is the only reason four healthy files were not "repaired" into damage.

⇒ **`CLAUDE.md`'s rule holds in BOTH directions.** It says a check reporting a fault in a file you
just touched is not evidence you broke it. **It equally is not evidence when the file is one you did
NOT touch.** A verifier is an instrument, and an instrument that has just been modified is the least
trustworthy thing in the room.
⇒ **And truncation control must compare BYTES TO BYTES.** `read_bytes()` vs `stat()`. Any path that
decodes first is measuring the decoder.

## S-139 · 2026-08-12 · **A TEST FIXTURE WITH AN ABSOLUTE DATE DOES NOT DECAY INTO UNCERTAINTY — IT DECAYS INTO ASSERTING THE OPPOSITE**

`bts_kdash_feed.selftest()` built a fixture containing `measured = 2026-07-31` for a monitor with
`cadence_h = 24`, and asserted its status was **GREEN**.

That was true on 2026-07-31. From 2026-08-01 onward an 11-day-old reading against a 1-day cadence is
correctly **RED** — so the selftest was asserting that the feed's staleness logic was **broken**, and
failing because the logic was **right**.

**Eleven days passed before anyone saw it**, because the same tool crashed on a red-circle emoji
whenever stdout was redirected (S-134). Fixing the encoding is what surfaced this. **One repair
exposing another is the normal shape of a system whose instruments have been wrong for a while, not
a surprise and not a regression.**

⇒ **A FIXTURE WITH A HARDCODED DATE TESTS "IS IT STILL THAT DATE" AS MUCH AS IT TESTS THE LOGIC.**
Fixture dates are now computed relative to `date.today()`, and the fix is verified by running the
selftest with the clock moved **200 days forward** — because a test that only passes today is the
defect being fixed.
⇒ **An expiring test is worse than no test.** No test is a known gap. An expired test is a green
light that has quietly reversed polarity.

## S-140 · 2026-08-12 · **"GREEN ×4 — THE FIRST REAL DRIVE READING THIS MESH HAS EVER HAD" WAS GREEN ON `None`s**

`bts_drive_health` scored uncorrected error counters with `if isinstance(v, int) and v > 0: RED`.
A counter of `None` — the device did not answer — **fell through every branch and left the status
GREEN**. So *"this disk reports zero uncorrected errors"* and *"this disk did not answer the
question"* rendered identically, as a pass.

Measured against the actual elevated reading of 2026-08-11 21:36, re-judged honestly:

| disk | temp | read_unc | write_unc | honest verdict |
|---|---|---|---|---|
| ADATA SX8200NP | 25 C | `None` | `None` | UNKNOWN |
| WD_BLACK SN850X | 42 C | `None` | `None` | UNKNOWN |
| WD My Passport | 37 C of **max 0 C** | 0 | `None` | UNKNOWN |
| SanDisk Cruzer | **0 C of max 0 C** | `None` | `None` | UNKNOWN |

**All four are UNKNOWN. None was ever GREEN.** Three disks report no error counters at all *even
elevated*, and the Cruzer reports `0 C` against a `0` maximum — **a device answering nothing, which
scored as a real reading made it the coldest and healthiest disk in the rack.**

⇒ **A MISSING VALUE THAT ARRIVES AS A NUMBER IS THE WORST KIND**, because every downstream
comparison treats it as evidence. `max 0 C` had already been noticed and written down as incoherent;
`temp 0` had not, because 0 is a plausible temperature in a way that a 0 maximum is not.
⇒ The file's own header claimed it *"does not treat a MISSING reliability counter as a good
reading."* **It did, for that field, for as long as the field existed.** A stated principle is not an
implemented one.

## S-141 · 2026-08-12 · **A DUPLICATE KEY TOOK `rails.toml` OFF THE AIR, SELF-INFLICTED WHILE FIXING THAT SAME BLOCK**

Correcting the stale GDX quota, an `owed` key was added to the `[[surface]]` block — which **already
had an `owed` twenty lines further down, on a long line a `Grep` had elided from the output**.
`tomllib` refuses a duplicate key outright, so `rails.toml` did not parse for roughly twenty minutes.

That is **S-118 exactly** (*"the file you wrote it to must still parse"*), committed while repairing
the very entry it broke, by the session whose subject was checks that lie.

It was caught by `maint_sweep` on the next run and fixed in one edit. **The cost was bounded only
because a parse gate existed.**

⇒ **EDIT A TOML BLOCK BY READING THE WHOLE BLOCK FIRST.** Never append near a key you have not seen.
A duplicate key is invisible to the eye, fatal to the parser, and produces no diff-level signal.
⇒ **A `Grep` that elides long lines is not a read of the file.** It is a read of the lines it chose
to show, and the omitted ones are disproportionately the long prose fields where duplicates hide.
⇒ **Every control document now passes a parse gate before anything is allowed to read it**, and the
gate refuses rather than warns.

## S-142 · 2026-08-12 · **THE BACKGROUND LANE STALLED REPEATEDLY AND ITS OWN LEDGER WAS STRUCTURALLY INCAPABLE OF SAYING SO**

`BTS Queue Runner` — installed 2026-08-11, load-bearing the same day — ran to **23:32**, then went
**43 minutes with two jobs sitting unclaimed**. It woke at 00:15, cleared both, **stalled again by
00:21**, ran at 00:53, stalled again, ran at 02:26. Every verification in the session ran through
this lane. **Nothing reported any of it.**

🔴 **ITS LIVENESS CANNOT BE READ FROM ITS LEDGER, BY CONSTRUCTION.** The ledger is written *only when
a job runs*. Silence therefore means *"idle"* and *"dead"* **identically**, and no threshold on that
signal can separate them. This is S-134's shape in a new place: the absence of a report is not the
absence of a problem — here the absence was guaranteed.

⇒ **THE SIGNAL IS QUEUED-AND-UNCLAIMED**: work present in the queue root with nothing in `running\`.
One `stat` call, and it needs **neither the scheduler nor the runner**, which is the entire
requirement — **a dead runner cannot report itself.**
⇒ **AND THE FIRST DIAGNOSIS WAS WRONG IN THE COMFORTABLE DIRECTION.** "The machine slept after
midnight" was assumed. It is false: the Cowork sandbox was reading and writing `V:` continuously
through every stall, and that mount is served by the same machine. **The box was awake.** A
per-minute task not firing per minute is a different problem — most likely a stuck instance under
Task Scheduler's default *"do not start a new instance"* rule, where **one hang mutes the lane
indefinitely.**
⇒ **The evidence that refuted the guess was already in hand and had been for an hour.** Before
accepting an explanation that assigns the fault to nobody, ask what you were already observing.


## S-143 · 2026-08-12 · **THE RECORD ASSERTED A FALSE ARCHITECTURE, PLANNING RAN ON IT FOR DAYS, AND ONLY THE HUMAN WHO BUILT IT COULD SEE THE ERROR**

`rails.toml` and `BU.MD` both stated, in bold, as a measured fact:

> *"joanna.bbf HOLDS THE ONLY GOOGLE API KEY THAT EXISTS. Every Gemini and Vertex call this mesh has
> ever made ran on it, and its credit dies 2026-10-13."*

**It is false.** The actual architecture, from Keith, who built it with Cowork:

| account | purpose | project |
|---|---|---|
| `joanna.bbf@gmail.com` | **the CREDIT key** — Vertex, the $300 | `project-5a33f910-1251-4d6a-bf9` |
| `keith.bbf@gmail.com` | **the DAILY FREE CREDITS** (AI Studio) — **broken, never fixed** | `475026348209` |

**The evidence was on disk the whole time and nobody read it.** `.secrets\gemini_keys-all but.txt`
records verbatim `Project name: projects/475026348209` — a keith.bbf project — and the credentials
console shows two Gemini keys created there on 2026-07-12.

⇒ **THE CLAIM CONFLATED THE KEY WITH THE CREDIT**, and once written in bold with a date it was
never re-examined. Everything downstream inherited it: the October plan, the "Needs Keith" list, the
JDX concentration argument, and a repeated instruction to *create* a keith.bbf key **that already
existed**.

⚠ **AND THE CORRECTION COULD ONLY COME FROM KEITH.** No check in this mesh could have caught it —
`verify_pointers` resolves paths, `tidyup2_full` recounts numbers, `maint_sweep` ages constants.
**None of them can tell whether a sentence about how something WORKS is true.** A false structural
claim, stated confidently and dated, is invisible to every instrument built this session.

⇒ **THE CLASS: A STRUCTURAL ASSERTION IS NOT A MEASUREMENT, AND NOTHING AUTOMATED WILL EVER CHECK
IT.** Numbers can be recounted, paths resolved, dates aged. *"X holds the only key"* is a claim
about the world's shape, and its only检 check is a human who knows the shape. **Mark such claims as
`[U]` until the person who built the thing has confirmed them — and never let one wear the same
bold-and-dated formatting as a measured fact.**

⇒ **SECOND, AND MORE USEFUL:** Keith said *"you should know all of this, you set it up with me."*
He is right, and the failure is exactly the one C-05 names: **the session that knew it ended, and
only the WRONG version reached disk.** Cowork's memory IS the file. When a human explains an
architecture, that explanation is the single most perishable artifact in the session and must be
written down in the same turn, verbatim, attributed.

## S-144 · 2026-08-12 · **A DEFERRAL JUSTIFIED BY A SURPLUS INHERITS THAT SURPLUS'S EXPIRY DATE**

The keith.bbf AI-Studio free-tier path broke and was deliberately not fixed. The reason was sound:
*"we have an excess of the free credits."* **True when said.**

But the surplus that justified the deferral is the **$300 Vertex credit, which dies 2026-10-13** —
so the justification expires on a specific date, and **that date was never written next to the
deferral.** The consequence compounds: on 2026-10-14 the paid lane is gone AND the fallback is a
broken rail, and it must then be diagnosed **with no working rail left to compare it against**.

⇒ **EVERY "we can live without this for now" IS A DECISION WITH A CLOCK ON IT.** Record WHAT makes
it acceptable and WHEN that stops being true. A deferral whose justification is undated cannot be
reviewed, because nothing ever prompts the review.


## S-145 · 2026-08-13 · **S-134 INVERTED: THE TOOL WORKED IN THE HARNESS AND DIED IN FRONT OF THE HUMAN — AND IT DIED ON THE LINE NAMING THE CAUSE**

`runner_doctor.py` was written on 2026-08-12 to diagnose the queue runner. Keith ran it from
`Desktop\BTS.bat` on 2026-08-13. It printed the full task dump, reached the line that states the
verdict, and threw:

    UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f534'

**The verdict never printed.** He got a task dump and a traceback where the answer should have been —
`POWER MANAGEMENT: Stop On Battery Mode, No Start On Batteries` and the settings checklist.

**IT HAD PASSED EVERY TEST.** It ran clean a dozen times that session — *from the queue*, where
`bts_runner` forces `PYTHONUTF8=1` on every child. **The harness was supplying the thing the tool
depended on**, so the dependency was invisible until something else called it.

⇒ **THIS IS S-134 WITH THE SYMPTOM REVERSED.** There, four monitors ran fine by hand and crashed the
moment a scheduler redirected stdout — *"the monitors worked whenever anyone was watching."* Here the
tool works whenever the harness runs it and breaks the one time a human does. **Same root, opposite
face: THE ENCODING OF THE PARENT IS NOT A PROPERTY OF THE TOOL,** and a tool tested only under one
parent has not been tested.

⇒ **AND IT WAS SELF-INFLICTED BY THE SESSION THAT FIXED S-134.** `CLAUDE.md` carries *"NO EMOJI IN A
.bat"*; that session explicitly generalised it — *"the rule was written for cmd and never carried
across to the Python tools' own stdout"* — and then wrote a red circle into a `print()` in a new
tool the same day. **Generalising a rule in prose is not applying it.**

**MEASURED THE SAME HOUR: 42 tools in `BTS_MESH\` and `ROLD\` print non-ASCII**, including
`corrections.py`, `scars.py`, `verify_pointers.py` and `verify_conf.py` — the C.O.S. and the
verifiers. **Every one is a bat away from this crash.**

⇒ **THE FIX IS AT THE CALLER, NOT IN 42 FILES.** Rewriting the prose of 42 tools is churn that will
rot; pinning the environment is one line. Every `.bat` this repo stages now sets `PYTHONUTF8=1`,
`PYTHONIOENCODING=utf-8` and `chcp 65001` **before** invoking Python. `BTS.bat` re-staged 2026-08-13.
⚠ **Emoji still removed from `runner_doctor.py`'s `print()` calls** — belt and braces, because the
one tool whose job is diagnosing a broken lane must not itself depend on a healthy environment.


## S-146 · 2026-08-13 · **A MISREAD ACRONYM BECAME A DIAGNOSIS, REACHED FIVE ARTIFACTS, AND DEFENDED ITSELF AGAINST THE FIRST CORRECTION**

`Judge-UPS.vbs` sits on the Desktop as one of two permanent items. Cowork read **UPS** as
*uninterruptible power supply* and built a complete causal chain on it: Keith runs a UPS -> a mains
blip puts the machine on battery -> Task Scheduler's `Stop On Battery Mode` stops the task -> that is
why the queue runner went silent for 43 minutes.

**UPS here is ULTRAVIOLET PHOTOELECTRON SPECTROSCOPY. It is the subject of the dissertation.**

The fiction was written into **five live artifacts** - `runner_doctor.py`, `BU.MD`,
`PLM_TODOS.md`, `rails.toml` and a Desktop menu - and printed to Keith **twice** as *the* diagnosis
with a fix attached (untick two Task Scheduler boxes).

🔴 **EVERY PIECE OF DISAMBIGUATING EVIDENCE WAS ALREADY IN CONTEXT.** `CLAUDE.md` states *"NEXT
SESSION = CHAPTER 4 / UPS PHYSICS"*. PLM-06 is *"upsjudge - run the two ribbon prototypes"*. The
tool is the **UPS judge**. Nothing had to be looked up.

⚠ **AND IT SURVIVED THE FIRST CORRECTION BY RECRUITING NEW EVIDENCE.** Keith: *"This is a PC, not a
laptop, it can only run on AC."* Instead of dropping the premise, Cowork **invented a mechanism to
save it** - that a USB-connected UPS presents to Windows as a battery, so the condition could still
fire - and went to measure that. Only *"I have no UPS"* ended it.
⇒ **A WRONG PREMISE DOES NOT FAIL LOUDLY. IT ABSORBS CONTRADICTION.** The measurement that killed
it (`BatteryChargeStatus=NoSystemBattery`) was one command and could have been run before the first
word of diagnosis was written.

⇒ **MECHANISM: `ROLD\GLOSSARY.md`**, created the same hour. What words mean HERE, physics and mesh
both. *(C-16, count 4.)* **Look up a short domain term before building on it; if it is not there and
it matters, ask.**

⚠ **AND WHAT IT COST BEYOND THE ERROR:** PLM-37 is still unsolved, and an afternoon of confident
wrong causation was spent instead of the one honest sentence - *the scheduler's own history log is
disabled, so this stall cannot be diagnosed at all.*

## S-147 · 2026-08-15 · **THE NEGATIVE CONTROL SHARED THE POSITIVE CHECK'S DEFECT, SO IT CERTIFIED NOTHING — AND IT PRINTED A ✅ SAYING SO**

**MEASURED.** `oa_dash_close__t900.py` verified that the newly-wired `openai-api` rail had reached
the dashboard. It read `dash.json` and looked for the rail at `dash["rails"]`. It found **zero
rails**, and reported:

> `- 0 rails in dash.json`
> `- 🔴 openai-api IS NOT IN dash.json. The edit did not reach the dashboard.`

**THAT WAS FALSE.** The rail was in `dash.json`, **status GREEN, latency 700 ms**, exactly as
intended — nested under `dash["kmesh"]["rails"]`, because `bts_kdash_feed` writes its block under a
mesh-id key and *says so on its own last line*: `written -> dash.json (key: 'kmesh')`. The feed's
stdout in the very same log listed `openai-api  api  700 ms`. **The evidence contradicting the
finding was four lines above the finding.**

🔴 **AND HERE IS THE PART WORTH THE SCAR.** The same job carried a NEGATIVE CONTROL, written
deliberately, under the rule that a verifier never shown to fail is not a verifier:

> looked up a rail name that cannot exist: found 0
> ✅ the lookup returns empty for a fictional rail, so a HIT above is real

**The control passed. It was worthless.** It searched the SAME empty list, at the SAME wrong nesting
level, as the check it was validating. A lookup against an empty container returns empty for a real
name and a fictional one alike — so the control could only ever print ✅, no matter what was true.
**It did not discriminate; it agreed.**

⇒ **A NEGATIVE CONTROL MUST NOT SHARE THE POSITIVE CHECK'S ASSUMPTIONS. If it does, it is not a
control — it is the same check run twice, and its agreement is a measurement of nothing.** The
control here tested *"does a fake name return empty?"* when the only question that mattered was
*"am I looking in the right container?"* — and that assumption was invisible to both halves.

⇒ **THE SHAPE, GENERALIZED:** the control must vary the thing that could be wrong. A control that
varies the INPUT while holding the DEFECT constant proves the code is deterministic and nothing
else. The cheap discriminator was available and obvious: **assert the container is non-empty before
searching it.** Zero rails in a dashboard feed is not a search result, it is a PATH failure — the
identical distinction `find_in_mail.py` already draws when it refuses to conclude anything from
"ZERO MAIL STORES FOUND."

⇒ **This is C-30's other half.** C-30 says a check that cries wolf is not evidence. This one says a
check that says ✅ is not evidence either **when it was structurally incapable of saying anything
else.** The false RED was caught in minutes because a RED gets read. **The ✅ beside it would never
have been questioned at all.**

*(Class: verification, false-negative, self-inflicted. Same family as S-138 — four checks crying
wolf — and the inverse of it.)*

### ⚠ ADDENDUM, SAME NIGHT, INSIDE THE FIX — **IT RECURRED WITHIN THE HOUR, ONE LAYER UP**

The repair job for this scar stopped hardcoding the container name and searched generically instead:
*"any dict holding a list called `rails`."* It matched **`dash["policy"]["rails"]`** — which is
`bts_policy`'s list of rail **NAMES**, four plain strings — and crashed on `r.get("name")`.

**And the guard written specifically to prevent S-147 reported:**

> `✅ 4 rails present, so a miss below would be a real miss`

🔴 **THE GUARD TESTED PRESENCE WHILE THE DEFECT WAS IDENTITY. Four of the wrong thing is not empty.**
*"Is this container non-empty?"* and *"is this the right container?"* are different questions, and
**only the second was ever at issue** — in the original failure as much as in the repair. The fix
answered the question the scar had *described* rather than the one it was *about*.

⇒ **WRITING A SCAR DOWN IS NOT APPLYING IT.** This one was composed, reasoned through and committed
to `SCARS.md`, and then reproduced in the next file written — because the lesson was recorded as a
sentence about empty lists rather than as a **discriminator in code**. The discriminator is one line:
*a rail RECORD is a dict carrying a name; a rail NAME is a string.* Validate the **shape of the
members**, never the length of the list.

⇒ **AND THE CONTROL RULE GENERALIZES:** one control varying one assumption is one assumption tested.
The final version carries three — vary the **PATH**, vary the **SHAPE**, vary the **NAME** — because
each earlier failure lived in a dimension the previous control held constant.
