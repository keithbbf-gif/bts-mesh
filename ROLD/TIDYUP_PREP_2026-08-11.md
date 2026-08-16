# TIDYUP PREP — 2026-08-11 (PLUMBING session, evening)
**Not a handoff. This is the INPUT to TidyUP, written before running it, so that
nothing in this session depends on one context window surviving.**
Keith, 2026-08-11: *"Get that set up and prepare for TidyUP, but don't run it yet."*

⚠ **Mesh document. `.md` is correct here — Cowork/nodes are the consumer.** Never convert, never present.

---

## 1. WHAT TO WRITE INTO `V:\Ai\BU.MD`

### THE MACHINE IS GREEN FOR THE FIRST TIME IN THE RECORD
| rail | measured 2026-08-11 21:45 |
|---|---|
| SGH / GW (xAI) | HTTP 200 · 306 ms · **11** models |
| GEM (AI Studio) | HTTP 200 · 244 ms |
| VERTEX | HTTP 200 · 644 ms |
| **GDX** | **HTTP 200 · REFRESHED · 150 ms · consent 0.0 d** — was `invalid_grant` for 8.8 days |
| **OA / OpenAI Codex** | 🟢 **LIVE.** `gpt-5.6-terra` · ~10.3 s · return landed in a file |
| **DRIVE HEALTH** | 🟢 **GREEN ×4 — the first real reading this mesh has ever had** |

**Disks:** ADATA SX8200NP (V:) 25 °C · WD_BLACK SN850X (C:) 42 °C · WD My Passport (D:) 37 °C,
**49,058 power-on hours ≈ 5.6 years**, uncorrected read=0 · SanDisk Cruzer (L:).
⚠ **Two disks return `read=None write=None` even elevated, so their GREEN rests on temperature
alone. GREEN ON A `None` IS NOT GREEN ON A ZERO** — confirm `bts_drive_health` is not treating
"did not answer" as "passed."
⚠ **`max 0 C` on the Passport and the Cruzer is a missing value rendered as a number.** "37 C of
max 0 C" is incoherent, and any comparison against it reads as over-limit or gets skipped.
`bts_kdash_feed` already forbids rendering UNMEASURED as a number; the health tool breaks that rule
internally.

### THE ONE ROOT CAUSE THAT WAS BREAKING FOUR MONITORS
🔴 **`UnicodeEncodeError: 'charmap' codec can't encode '\U0001f534'`.**
`rail_check` · `bts_drive_health` · `bench_drive` · `bts_kdash_feed` all print the red-circle emoji
and box-drawing characters. **Windows falls back to cp1252 the moment stdout is REDIRECTED** —
which is exactly what a scheduler does. Run by hand in a console they work.
⇒ **THE MONITORS WORKED WHENEVER ANYONE WAS WATCHING THEM.**
And `rail_check` and `bts_kdash_feed` **still exited 0 while crashing**, while the native
`BTS Rail Check` task reported `Last Result: 0`. **Green, with no file written.** That is the missing
08-05, 08-06, 08-09, 08-10 and 08-11, the permanent UNKNOWN drive health, and `dash.json` frozen
since 07-29.
**Fixed by forcing `PYTHONUTF8=1` on every child in `bts_runner`.** After it:
`RAIL_HEALTH_2026-08-11.md` written (2,865 B) · `dash.json` refreshed (41,860 B) ·
`verify_conf` **GREEN** (its exit 1 was the crash, not violations) · `bench_drive` ran —
D: **67.5 MB/s**, and the cache detector correctly flagged L: at 6,169 MB/s as
`CACHED — NOT A DISK MEASUREMENT`.
⚠ **`CLAUDE.md` already carries "NO EMOJI IN A `.bat`." The rule was written for cmd and never
carried across to the Python tools' own stdout.** Generalize it.

### THE BACKGROUND LANE EXISTS — PLM-25 IS CLOSED
**`BTS Queue Runner`** — native Windows task, every minute, `pyw -3.14 bts_runner.py --once`.
Drop a `.bat`/`.py`/`.ps1` into **`V:\Ai\_queue\`** and it runs. `__tNNNN` in the filename sets a
timeout. Logs to `_queue\logs\`, ledger at `_queue\runner_ledger.jsonl`, jobs move to `done\` /
`failed\`, nothing is deleted.
**Proven end to end 2026-08-11:** proof job queued 20:59:01, executed by the scheduler 21:00:01,
`rc=0`, no screen and no click. Six real jobs have since run through it.
⇒ **This is now the default execution route. Cowork does not need Keith's desktop.**

### OA / OPENAI — THE WORKING INVOCATION, MEASURED ACROSS FIVE VARIANTS
```
codex exec --approve-for-me --skip-git-repo-check -C "<root>" "<prompt with ABSOLUTE paths>"
```
- `-s/--sandbox` and `-c sandbox_mode=` both leave the header at `sandbox: read-only`. `--full-auto`
  is **not an argument this version accepts**. Only `--approve-for-me` writes.
- 🔴 **THE HEADER IS NOT THE VERDICT. THE ARTIFACT IS.** `--approve-for-me` wrote successfully while
  the header still said `read-only`.
- 🔴 **AND IT WROTE TO THE WRONG ROOT.** A relative path `Ai\PhD2_DATA_ARCHIVE\...` resolved against
  **`V:\Ai`** — the *first* `writable_roots` entry — not against cwd `V:\Research4`. It created a
  phantom tree and reported success. **BFast's own scar verbatim: verifying content is not verifying
  destination.** Phantom tree staged to `_delme` and removed. ⇒ **Pin `-C`, use absolute paths.**
- **Context ceiling: `272,000` tokens** — MEASURED from `~/.codex/models_cache.json`. Every model this
  ChatGPT account offers (`gpt-5.6-terra`, `-luna`, `gpt-5.5`, `gpt-5.4-mini`) carries the same.
  🔴 **The war-game record is ~422k, so OA CANNOT HOLD IT.** Only `openai-api` (1.05M) could.
- **`gpt-5.6` bare is not offered to a ChatGPT account** and was refused by name.

### SESSION LOGS — ANSWERED
🔴 **`C:\Users\Papa\AppData\Roaming\Claude\local-agent-mode-sessions` NO LONGER EXISTS.** That is why
the between-sessions copy reported *"didn't find the target files in C:"*. Cowork's session storage
moved, and Cowork **can no longer mount it** — refused as *"Cowork's internal session storage…
intentionally not accessible"*; `.claude` is refused as overlapping a protected location.
- Transcripts now live at **`C:\Users\Papa\.claude\projects`**.
- **523 files / 1.6 GB already staged**, newest 2026-07-31. Only **2 files / 126 KB** were missing.
  **Copied, 0 failures.**

---

## 2. SCARS TO APPEND — `SCARS.md` **and** `scars.jsonl`, then `scars.py --rebuild`
**Current count 133** (S-133 written and reconciled this session, 133 == 133, exit 0).

- **S-134 · THE MONITORS WORKED WHENEVER ANYONE WAS WATCHING.** Four tools crashed on an emoji only
  when stdout was redirected; two of them exited 0 anyway and the scheduler recorded success. An
  absent report is indistinguishable from an absent problem — *and here the report was GREEN.*
- **S-135 · A CORRECTLY PLACED KEY WITH AN INVALID VALUE IS STILL BROKEN.** S-132 was a key in the
  wrong table; `model = "gpt-5.6"` was in the right table, parsed, resolved at top level, and was
  refused by the API. **Neither a parse check nor a resolve check asks whether the VALUE is usable.**
- **S-136 · THE RUNNER'S OWN SELFTEST REFUSED IT.** First version built each command from the job's
  path *before* renaming the file, so every job returned `rc=1` — including the one meant to succeed.
  **Verifying a path is not verifying the path you are about to use.** The refusal is the only reason
  a broken runner was not scheduled into service.
- **S-137 · `gdx_fresh_auth.py` DISPOSED OF THE OLD CREDENTIAL BEFORE PROVING IT COULD MAKE A NEW
  ONE.** It moved the live credential aside, *then* discovered `pydrive2` was missing and stopped —
  taking GDX from "expired consent" to "credentials.json not found." Recoverable only because it
  moved rather than deleted. **Order the dependency check first.**

## 3. CORRECTIONS — `corrections.toml`, then validate with `tomli`
- **C-29 · ASSERT THE ARTIFACT, NOT THE REPORT.** Hit three times today: a config "verified by
  re-read" that had four of five keys missing; an `exec exit=0` that wrote nothing; a run header
  saying `read-only` while the write succeeded. **Exit codes, headers and prose all lie in the same
  direction — toward success.**
- **C-13 recurrence** — this file exists because of it.

## 4. REGISTRY / INDEX STATE
**`TOOLS_REGISTRY.json` = 46, parses clean.** `00_TOOLS_INDEX.md` updated in the same pass.
Added today: `bts_oa` · `bts_runner` · `collect_sessions`.
⚠ **`collect_sessions` is `conf="U"` with an `owed`** — now satisfied by its `--plan` and `--copy`
runs; **flip to `V` with `measured="2026-08-11"` at TidyUP.**

## 5. FILES TO STAGE TO `V:\Ai\_delme\`
`Desktop\OA MEASURE.bat` · `OA RUN.bat` · `OA RUN 2.bat` · `OA RUN 3.bat` · `SESSION SCAN.bat` ·
`INSTALL BACKGROUND RUNNER.bat` · `RUN HIDDEN.vbs` · `1 - ELEVATE DRIVE HEALTH.bat` ·
`2 - GDX RECONSENT.bat` — **all spent.** Keith deletes Desktop bats himself; the mount copies but
cannot unlink.

---

# 6. NEXT PLUMBING SESSION — THE `openai-api` RAIL
**Keith, 2026-08-11: *"We didn't get the new rail added. That's OK. We will do another plumbing
session right after this one."***

**THE GATE IS NOW MOSTLY OPEN.** Keith's order was: every existing rail up to date and working,
*then* the API lane. Status of that gate as of tonight:

| gate condition | state |
|---|---|
| OA/Codex has answered once | ✅ **DONE** — `gpt-5.6-terra`, artifact on disk |
| `bts_oa.py` ledger exists | ✅ **DONE** — registry 46, selftest 7/7 |
| OA context ceiling measured | ✅ **DONE** — 272,000 |
| GDX OAuth re-checked | ✅ **DONE** — HTTP 200 REFRESHED, 150 ms |
| drive health | ✅ **GREEN ×4**, with the two caveats in §1 |
| `codex` → `/status` allowance read | 🔴 **STILL NOT DONE** — every number about OA's limits comes off a pricing page, not the account |
| OA token usage reaching the ledger | 🔴 **NOT WIRED.** The shape is learned (`state: MEASURED`, stdout prints `tokens used N`), but no call has recorded `tok_in`/`tok_out` yet |
| GEM `keith.bbf` key created and proven | 🔴 **NOT DONE** — the October cliff |
| `gemini-dom` driven once | 🔴 **NOT DONE** |
| CoPG credit allowance | 🔴 **NOT DONE** |
| `cli-grok` latency | 🔴 **NEVER MEASURED**, and it is the cheapest lane |

**PRICES, MEASURED 2026-08-11 from OpenAI's model page** (per MTok in/out):
`gpt-5.6-sol $5/$30` · `terra $2/$12` · `luna $0.20/$1.20`. One 422k-in bench run ≈ **$2.71 / $1.08 /
$0.11**. SGH's own ledger for the same job was **$1.47 — terra undercuts it.**
⚠ **KEITH SETS UP BILLING. NOBODY ELSE.** Cowork stages to the payment and stops.
⚠ **Label the key file BY ACCOUNT.** When the `keith.bbf` Google key lands there will be keys for
three vendors and two Google accounts; an unlabeled store is how a failover picks the dead one.

## 🔴 FOUND BY TidyUP2, 2026-08-11 — THREE DEFECTS IN TONIGHT'S OWN WORK
1. 🔴 **`bts_runner` EXECUTES HELPER SCRIPTS AS JOBS.** `_tidyup2_checks.py` was placed in
   `V:\Ai\_queue\` for a bat to call; the runner claimed it, renamed it into `running\`, and the bat
   then failed with *"can't open file … No such file or directory."* **The queue root is a job
   inbox, not a place to keep supporting files.** ⇒ Runner must ignore `_`-prefixed files (it already
   skips them when *listing* — the skip is in `_tidyup2_checks.py`'s own convention, not in `tick()`),
   and helpers belong in `BTS_MESH\`, not in the queue.
2. 🔴 **TWO TidyUP2 CHECKS WERE INLINE PYTHON IN A `.bat` AND BOTH WERE EATEN — C-06, on the same
   day the file quoting C-06 was written.** The contradiction hunt returned `[]` for every file,
   including `CLAUDE.md`, which unambiguously contains `2026-10-13`. **A check that returns "no
   problems found" because its own regex was mangled is worse than no check** — it is a false GREEN.
   ⇒ Rewrite as a `.py` in `BTS_MESH\`.
3. ⚠ **Emoji in a `.bat`** — `consolidate__t900.bat` line 12. Harmless in a `rem` under UTF-8, but it
   is the rule this session cited twice. Sweep before staging.

⚠ **And the two `unknown-opcode` RED lines are in `SCARS.md`** — line 1635 `GEM:` and line 2636
`REBUILT:` — **both pre-existing prose, and `SCARS.md` is APPEND-ONLY and must never be edited.**
⇒ **The fix belongs in `verify_pointers.py`: an append-only narrative document must not be scanned
for operators.** `failed=0` throughout — **no pointer is actually broken.**

✅ **TidyUP2 GREEN on:** truncation control (`stat` == bytes read on all five control documents) ·
`SCARS.md` headings **137** == `scars.jsonl` **137** · registry 46 · C.O.S. 29 entries, parses.

**FIRST FIVE JOBS FOR THAT SESSION, in order — all queue-able, none need the screen:**
1. `codex` → `/status`, read the real allowance. Wire `tok_in`/`tok_out` into `bts_oa`.
2. Fix `bts_drive_health`: `None` must not render GREEN; `max 0 C` must not render as a number.
3. Measure `cli-grok`, `cli-gemini`, `cli-claude`, `bfast-handoff` latency — four `UNMEASURED` rows
   in `dash.json`.
4. Re-measure the **GDX quota** — `rails.toml` still carries 100 GB / 11.7 % from **2026-07-13**,
   before the Google AI Plus purchase. **Stale by construction.**
5. **PLM-31**, the live safety defect: the SMART bat's guard says *"do not touch Disk 0"* and
   **Disk 0 is now `WD_BLACK SN850X` — the C: boot drive.** Key it on `SerialNumber`.

⚠ **`dash.json` renders `107 MB/s` against nearly every rail row** — that is V:'s write speed applied
to lanes it does not describe. **Measured one thing, displayed against another.** Check before
trusting any throughput figure on KDash.
