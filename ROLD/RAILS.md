# RAILS.md — THE INFRASTRUCTURE CONSTANTS

**What this file is:** every path, mount, drive letter, endpoint, model id, key location, port,
scheduled-task name, and the desktop-only-vs-sandbox split.
**What makes it change:** the INFRASTRUCTURE changed. Nothing else belongs here.

**What is NOT here, deliberately:**
POINTER: V:\Research4\Ai\ROLD\RULES.md          — rules, canon, standing rulings
POINTER: V:\Research4\Ai\ROLD\ROUTINES.md       — BootUP / TidyUP / TidyUP2 steps
POINTER: V:\Research4\Ai\ROLD\SCARS.md          — dated post-mortems
POINTER: V:\Research4\Ai\ROLD\00_ROLD_ARCHITECTURE.md — the decomposition spec this file is step 3 of

**Operators used in this file** (four, nothing else; literal line prefixes so a `.bat` can grep them):
`POINTER:` · `INCLUDEIF:` · `OVERRIDE:` · `PRECEDENCE:`
POINTER: V:\Ai\Research\ROLD_POINTER_DESIGN_2026-07-30.md — why four, and what is refused

> **A constant IS content.** Drive letters, endpoints and key paths are stated here as VALUES, not
> pointed at. The rule is *prefer a copy when the referent is small AND stable*; a 3-line constant
> is not worth an indirection. Anything large or living gets a `POINTER:` instead.

---

## 1 · TREES

| tree | status |
|---|---|
| **`V:\Research4`** | 🟢 **THE LIVE TREE.** The dissertation + mesh root. |
| **`V:\Ai`** | 🟢 **Top of the AI workspace.** Holds `BU.MD` (the boot pointer), `PLM_TODOS.md`, `Legal\`. `Research4` is one stream's tree, not the root. |
| **`D:\Research3`** | ⛔ **STALE FORK.** Formerly `D:\Research2`; rename verified host-side in File Explorer. **Do not mount, read, or write it.** Nothing points at it. A corpse kept for safety. |
| **`D:\Research2`** | ✅ **DOES NOT EXIST.** Nothing answers to that name any more. |

### Resolver — `Ai\BTS_MESH\bts_paths.py`
```
_WIN = [r"V:\Research4"]
_NIX = ["/sessions/*/mnt/Research4"]
```
PRECEDENCE: os.name=="nt" -> _WIN ; else _NIX (sorted glob, first hit) ; else $BTS_RESEARCH_ROOT ; else RAISE
OVERRIDE: BTS_RESEARCH_ROOT = <abs path>   (env var; for a peer's box or a test tree only)

**⚠ There is NO D: fallback and that is deliberate.** A resolver that silently falls back to a stale
tree is worse than one that fails: a crash names the problem in one line, a silent fallback ships a
chapter built on the wrong archive. **A mis-mount must fail loudly. Do not "fix" this.**

Helpers: `p()` · `ai()` · `mesh()` · `archive()` · `working()` · `secrets()`.
Self-test: `python bts_paths.py` (prints the ladder + a key check, exit 0).
Windows functional proof: `Desktop\VERIFY_BTS_PATHS.bat` — run where the bytes are real.

---

## 2 · MOUNTS

Front-load **all of these in ONE block** at BootUP. Each is a Cowork `request_cowork_directory`
grant. `V:\Research4` goes FIRST (the access record lives inside it).

**The sandbox mount root is `/sessions/<session-name>/mnt/` and `<session-name> CHANGES EVERY
SESSION`** — that is why `_NIX` is a glob and never a literal. (Measured this session:
`/sessions/youthful-amazing-rubin/mnt/`.)

| # | host path | bash sandbox path (relative to `/sessions/*/mnt/`) |
|---|---|---|
| 1 | `V:\Research4` | `Research4` |
| 2 | `V:\Ai` | `Ai` |
| 3 | `C:\Users\Papa\Downloads` | `Downloads` |
| 4 | `C:\Users\Papa\OneDrive\Desktop` | `Desktop` |
| 5 | `C:\Users\Papa\OneDrive\Desktop\KC-DTop` | `KC-DTop` |
| 6 | `D:\thumb drive` | `thumb drive` |
| 7 | `D:\Desktop BACKUPS` | `Desktop BACKUPS` |
| 8 | `C:\Users\Papa\AppData\Roaming\Thunderbird` | `Thunderbird` |
| 9 | `D:\PhD` | `PhD` |
| 10 | `G:\Tera 4 - back 24` | `Tera 4 - back 24` |
| 11 | **`X:\My Drive\BTS_SGH_Handoff`** (GDX) | 🔴 **NONE — see trap B** |
| 12 | `D:\R2Cloner` | `R2Cloner` |
| 13 | **`D:\ODX\OneDrive\BTS_ODX`** (ODX) | `BTS_ODX` — see trap A |

Situational, not front-loaded: `D:\+Papers` · `C:\OriginLabs\User Files`.
Cowork-owned scratch, not user folders: `/sessions/*/mnt/outputs` · `/sessions/*/mnt/uploads`.

### 🔴 THE THREE TRAPS

**A · `D:\ODX\OneDrive` IS REFUSED. Ask for `D:\ODX\OneDrive\BTS_ODX`.**
Same protected-location class as `C:\Users\Papa\OneDrive`. The wrong path was in the ask list from
2026-07-14 and failed at every BootUP until 07-15. `BTS_ODX` mounts fine and is the folder actually
wanted. Bash path: `/sessions/*/mnt/BTS_ODX`.

**B · `X:\My Drive\BTS_SGH_Handoff` mounts for Claude's FILE TOOLS but NOT into bash.**
Use `Read`/`Write`/`Edit`/`Grep`/`Glob` on the host path. `ls` in bash returns *No such file or
directory* (re-measured 2026-07-30). Not a problem in practice — `bts_gdx.py` runs natively on
Windows. **Do not spend time on the bash error.**
**⚠ GDX IS `X:`, NOT `E:`.** Keith corrected this 2026-07-13; the wrong letter sat in the ROLD for a
day, sending scripts to a path that does not exist.

**C · `C:\Users\Papa\OneDrive` CANNOT be mounted, and DOES NOT NEED TO BE.**
It overlaps a protected host location (`...\Documents\WindowsPowerShell`) and Cowork refuses it.
Not a defect. Do not chase it.

### ⚠ A MOUNT IS NOT THE BTS PYTHON
Cowork mounts affect **Claude's file tools only.** `bts_surfaces.py` / `bts_bench.py` /
`bts_serve.py` / `rail_check.py` run **natively on Windows** and read `C:` `D:` `G:` `V:` `X:`
directly, with no mount required. When a probe says *"not mounted on this machine"* it is reporting
on the **Linux sandbox, which has no drive letters** — not on Keith's box.

---

## 3 · KEYS

**`V:\Research4\.secrets\` — a SIBLING of `Ai\`, NEVER inside it.**
`Ai\` is what the R2 publish pushes to a PUBLIC website. Safety here is **by location, not by
blocklist**. `D:\R2Cloner` (plaintext R2 keys) is likewise outside `V:\Research4` entirely, so a
mis-scoped publish is *structurally* unable to reach it. **Never move either one under `Ai\`.**

| file | rail | env var |
|---|---|---|
| `.secrets\Grok_API_Token-Key.txt` | SGH + GW (xAI) | `XAI_API_KEY` |
| `.secrets\bts-sgh-API-key.txt` | SGH, second candidate | `XAI_API_KEY` |
| `.secrets\gemini_key.txt` | GEM (AI Studio) | `GEMINI_API_KEY` |
| `.secrets\vertex_key.txt` | VERTEX (restricted to *Agent Platform API*) | `VERTEX_API_KEY` |
| `.secrets\gcp_billing_oauth.json` · `gcp_billing_token.json` | GCP billing reads | — |
| `credentials.json` (PyDrive2, beside `bts_gdx.py`) | GDX | — |

⚠ `gemini_key.txt` and `vertex_key.txt` are **DIFFERENT KEYS**. One key cannot serve both APIs.

### 🟢 NEW 2026-07-30 — key lookup resolves through `bts_paths.secrets()`
PRECEDENCE: $ENV_VAR -> hardcoded `V:\Research4\.secrets\<file>` -> `bts_paths.secrets("<file>")`

The hardcoded `V:\` path is tried **first** so Windows cannot regress; `bts_paths` **adds** the
sandbox path. Live in `bts_sgh._key()` (l.79), `bts_gem._key()` (l.70), `bts_vertex._key()` (l.150).
**MEASURED - the rails now answer from the Linux sandbox with NO DESKTOP — Vertex 0.7 s** (SGH 20.8 s,
GEM 28.7 s + 36.4 s). This is what makes Rule 2 real for the whole mesh.
⚠ `bts_vertex.py:42` still declares `KEY_FILE` as a hardcoded literal; the resolver is the *fallback
chain around it*, not a replacement. Do not delete the literal.

---

## 4 · RAILS

### xAI — SGH and GW (ONE shared account, ONE key, ONE monthly ceiling)
| | SGH | GW |
|---|---|---|
| module | `BTS_MESH\bts_sgh.py` | `BTS_MESH\bts_gw.py` |
| model id | **`grok-4.5`** (500k ctx, cutoff 2026-02-01) | **`grok-build-0.1`** (fallback `grok-4.5` on 404) |
| endpoint | `https://api.x.ai/v1/responses` | `https://api.x.ai/v1/chat/completions` |
| models list | `https://api.x.ai/v1/models` | same |
| price / 1M | in **$2.00** · out **$6.00** · cached-in **$0.50** | in **$1.00** · out **$2.00** · cached-in **$0.20** |

OVERRIDE: MONTHLY_BUDGET_USD = 10.00   (`bts_sgh` — a CEILING, not an allotment; UTC month boundary)
OVERRIDE: MAX_CALL_USD = 2.00          (grounded worst case — a FLAT constant, see PLM-27)
OVERRIDE: MAX_CALL_USD_NOSEARCH = 0.05 (plain call; measured $0.0004–$0.019)

⚠ **No xAI billing endpoint exists.** `api.x.ai/v1/api-key` → 200 but key METADATA only;
`/v1/usage`, `/v1/billing`, `/v1/credits` and all `management-api.x.ai/*` → **404**. Spend is our own
ledger (`sgh_spend.json` + `usage.cost_in_usd_ticks`), never a vendor reconciliation.

### GEM — Google AI Studio · 🔴 **DEAD**
`BTS_MESH\bts_gem.py` · endpoint `https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent`
Models: `gemini-flash-lite-latest` (default) → `gemini-flash-latest` → `gemini-2.0-flash`.
`gemini-2.5-flash` / `gemini-2.5-pro` are **404/RETIRED for new keys** on AI Studio.

🔴 **DEAD IS A BILLING STATE, NOT A QUOTA.** The key is valid (models-list 200) but its project is
linked to a billing account ⇒ Tier 1 / Prepay @ $0 ⇒ 429 *"prepayment credits are depleted."*
**It does not come back at midnight.** A project with ANY billing account linked — *including a free
trial one* — does not get the free tier. Fix = a project with billing **never linked**.
Failover is automatic: `bts_gem` → `bts_vertex` with `via=vertex`, `failover_from=CREDITS_DEPLETED`,
model `VERTEX_FAILOVER_MODEL = "gemini-2.5-flash"` (cheap — **never** default a volume rail to Pro).

### VERTEX — 🟢 LIVE
`BTS_MESH\bts_vertex.py` · endpoint
`https://aiplatform.googleapis.com/v1/publishers/google/models/{m}:generateContent`
Auth header `x-goog-api-key` (Express Mode accepts a plain API key — no service account).
Model ladder: `gemini-2.5-pro` → `gemini-2.5-flash` → `gemini-flash-latest` (**PRO FIRST**).
Price (gemini-2.5-pro, per 1M): in **$1.25** · out **$10.00**.

OVERRIDE: CREDIT_TOTAL_USD = 300.00
OVERRIDE: CREDIT_BILLING_ACCOUNT = 010E47-824B53-7202F5   (Joanna)
OVERRIDE: CREDIT_EXPIRY = 2026-10-13   [U — COMPUTED, NOT READ. Confirm at Billing → Overview.]

⚠ **Thinking bills at the OUTPUT rate.** Measured: a 3-sentence answer returned `out=101` with
`thoughtsTokenCount=2883` — **28.5×**, $0.0299, ~97% of it reasoning never seen. Over the DOM that
same thinking is free.
⚠ Whether the credit actually pays for Agent Platform is **[G], not verified** — no Google page says so.

### GDX — Google Drive exchange
`BTS_MESH\bts_gdx.py` (PyDrive2) · shared folder **`BTS_SGH_Handoff`**, id
**`1aiMjVZfFtiBGNAlkTwAYiq1Pvuz2F6hA`** · host path `X:\My Drive\BTS_SGH_Handoff`.
🔴 **OAuth refresh token expires EVERY 7 DAYS.** Consent screen is *External + Testing*, and
`auth/drive` is a **restricted** scope (Production would need a CASA assessment). Keith's ruling:
weekly re-auth is fine — schedule it. Removing the fuse (`drive.file` scope + publish to Production)
is PLM-07, not a state fact.

### Crossref — DOI truth
`https://api.crossref.org/works/{doi}` · free, public, ~207 ms, **cannot fabricate.**
⛔ Never ask a language model for a DOI.
⚠ A resolving DOI is **necessary but not sufficient** — verify title + authors + sample class.

### ITC — the public mirror
**`https://ai.dchambers.com`** · Cloudflare R2 bucket **`r2:ai-dchambers`** · capacity 10 GB
(5.09 used, 2026-07-30).
**Published subtree = `V:\Research4\Ai\PhD2_DATA_ARCHIVE`** (plus `BTS_MESH\` via Pass 1c, and
`D:\PhD` → `/PhD` via Pass 1b).
Publisher: **`D:\R2Cloner\Publish-to-R2_KEYED.bat`** (nav wrapper `r2.bat`; `Publish-BTS_MESH-to-R2.bat`;
`Publish-LEGAL-to-R2.bat`). Silent launcher: `Ai\BTS_MESH\publish_r2_silent.vbs`.
⚠ `r2.bat` carries a **stale secret** (right key ID, wrong secret) → every write through it 403s.
**Only the KEYED bat has the working token.**
⛔ **Never rclone from the sandbox** — the FUSE mount can truncate a source read and publish corrupted
bytes to a public site. Native Windows reads are the only ground truth.
⚠ `V:\Research4\00_WORKING\` is **NOT published**; `Ai\PhD2_DATA_ARCHIVE\00_WORKING\` is (PLM-04).

### Dashboard
`BTS_MESH\bts_serve.py` + `jack_command.html` · **`http://localhost:8765`, bound to 127.0.0.1 ONLY**
(it can spend money via `/api/bench`, so it must never be reachable off-box; idempotent — a second
launch stands down).
⛔ **Never `python -m http.server`** — it serves the page but has no `/api` routes, so every panel
silently falls back to hardcoded values.
Routes: `/api/bench` · `/api/burn` · `/api/surfaces` · `/api/policy`.
Launchers: `Desktop\Jack's Mesh Command.vbs` (the one Keith double-clicks) · `BTS_MESH\serve_dashboard.vbs`
· `BTS_MESH\run_dash.bat` (visible console) · `KDash.vbs`.

---

## 5 · MCP — the `bts-fs` server

Server: **`V:\Research4\Ai\BTS_MCP\bts_fs_mcp.py`** · name **`bts-fs`** · stdio · **13 tools**.
A protocol adapter ONLY — every verb delegates to `BTS_MESH\bts_tools.py`.
Wire: `python Ai\BTS_MCP\wire_clients.py` · measure: `Ai\BTS_MCP\PROBE_MCP.bat` ·
both: `Ai\BTS_MCP\WIRE_AND_PROBE.bat`.

| client | config file | key |
|---|---|---|
| **CoW** Claude Code / Cowork | `V:\Research4\.mcp.json` | `mcpServers` |
| **GEM** Gemini CLI 0.52.0 | `C:\Users\Papa\.gemini\settings.json` | `mcpServers` — **TOP-LEVEL** |
| **GW** Grok Build 0.2.112 | `C:\Users\Papa\.grok\config.toml` | `[mcp_servers.bts-fs]` — **TOML** |
| **CoP** Copilot / VS Code | `V:\Research4\.vscode\mcp.json` | **`servers`**, NOT `mcpServers` |
| **CoP** Copilot CLI | `C:\Users\Papa\.copilot\mcp-config.json` | `mcpServers`, `type: "local"` |

**Client landmines — each presents as "the server is broken":**
- **Gemini's root schema is `additionalProperties: false`** and `mcpServers` is a **top-level sibling
  of `security`** — a key in the wrong place is rejected outright, not ignored.
- **Gemini will not START a stdio server in an untrusted folder.** `security.folderTrust.enabled`
  defaults **true** and must be set **false**; the per-server `trust` flag does NOT bypass it.
- **`security.auth.selectedType = "vertex-ai"`** in `.gemini\settings.json` is the *whole reason* GEM
  authenticates. An earlier `"oauth-personal"` made the CLI hit the retired-tier check before it ever
  read `GOOGLE_GENAI_USE_VERTEXAI`, so env vars appeared to do nothing. **Assert it is unchanged.**
- **Grok's config is TOML**, and its compat layer *also* reads project `.mcp.json`.
- ⛔ **`claude mcp list` runs, but the Claude Code CLI is a separate install** — read
  `V:\Research4\.mcp.json` directly rather than inferring wiring from a CLI's output.
- ⚠ `bts-fs` launches under **Python 3.13** while the test suite is pinned to **`py -3.14`** (3.13 has
  no pytest). It works, but the runtime/test split is latent.
- 🔴 **CoP is REGISTERED, never handshaken. Registered ≠ connected** (PLM-09).

---

## 6 · DESKTOP-ONLY vs SANDBOX

**Genuinely desktop-ONLY — do not fight these:**
1. **rclone R2 publish** (Windows bat; no rclone in the sandbox; FUSE reads must never be published)
2. **Origin 2024 COM** (`origin_export.py`, `opj_batch_export.py`)
3. **Pandoc on Windows** — `C:\Pandoc\pandoc.exe`
4. **`G:` and `X:`** — see §2. `X:` genuinely does not reach bash.

**Everything else runs in the sandbox or as a native scheduled task.** The sandbox reaches
`aiplatform.googleapis.com`, `generativelanguage.googleapis.com`, `api.x.ai` and `api.crossref.org`,
and reads `.secrets` through the mount. **The API is the fallback, not the default.**

OVERRIDE: sandbox_default = any task NOT in the desktop-only list runs in the Linux sandbox
OVERRIDE: scheduler_choice = anything touching V:\ D:\ or a rail credential is a NATIVE Windows task, never a Cowork task

⚠ **Two schedulers run this mesh and they are NOT interchangeable.** Cowork tasks cannot see `V:`
unless the folder is in their connected set — **and that set is not a file anyone can edit** (it
blinded `free-tier-allotment-check` for seven days). Native Windows tasks run where the credentials
and drive letters are real.

⚠ **`G:` is NOT a NAS.** Labelled `NAS1`, but `Get-PhysicalDisk` says **SABRENT, BusType=USB** — a USB
enclosure on this box, unreachable from any peer. There is no LAN meeting point.

### 🚫 KEITH'S SCREEN IS OFF LIMITS (2026-07-29) — an infrastructure constraint
**NO Run dialog. NO computer-use launches. NO `cmd /k`.** This removes an entire execution surface
from the available set, so it is recorded here as a constant.
POINTER: V:\Research4\Ai\ROLD\RULES.md — the rule itself, and why

**What replaces it:**
| need | the surface |
|---|---|
| run the suite | CoW natively, in-process — `py -3.14 -m pytest` |
| launch a node | `claude -p …` · `grok -p … --always-approve` · `gemini -p … --approval-mode yolo` |
| publish to R2 | `Ai\BTS_MESH\publish_r2_silent.vbs` (hidden) or the 22:00 task |
| probe the rails | the native `BTS Rail Check` task, or read its report |
| anything long | a scheduled task |
| genuine desktop-only work | a `.bat`/`.vbs` Keith double-clicks **WHEN HE CHOOSES** — never taken mid-session |

⚠ Every `.bat` this repo owns **opens its log FIRST and tees to it.** `pause` is not a report.
⚠ Every `.bat` must be **ASCII + CRLF** (`tests\test_launchers.py` enforces it; em dashes produced
measured mojibake).

---

## 7 · SANDBOX LIMITS — measured constants

OVERRIDE: BASH_CALL_TIMEOUT_MS_MAX = 45000
OVERRIDE: BACKGROUND_PROCESS_SURVIVES_BETWEEN_CALLS = false

**A bash call is hard-capped at 45,000 ms.**
**`nohup` and `setsid nohup` BOTH die when the bash call returns** — silently, leaving an empty
output file (measured twice, 2026-07-30). Combined, **any node call longer than ~40 s cannot be run
from the sandbox at all.** The workaround that worked was splitting the prompt in half.
⇒ Long jobs take a **native scheduled task or a CoW-side runner.** ⇒ PLM-25.

⚠⚠ **THE MOUNT CORRUPTS FILES, SILENTLY — 12 measured hits.** It has under-reported SIZE (39,584 B on
one file), served a file truncated mid-statement (producing a FALSE `SyntaxError` in `bts_paths.py`
itself), and faked JSON decode errors. **Host-side `Read`/`Grep` are the only ground truth; never
`cp` a critical file through the mount.**
POINTER: V:\Research4\Ai\ROLD\SCARS.md — all twelve, dated and numbered

---

## 8 · MONITORS — owner · cadence · where it writes · state 2026-07-30

| monitor | scheduler | cadence | writes to | proven? |
|---|---|---|---|---|
| **`BTS Rail Check`** | **native Windows** | daily **02:05** | `Ai\PhD2_DATA_ARCHIVE\00_WORKING\RAIL_HEALTH_<date>.md` + `BTS_ODX\reports\` | ✅ **ALIVE.** 02:05:01→02:05:04, exit 0, both targets written; unbroken 07-26 → 07-30. Runs `BTS_MESH\rail_check.py` / `RAIL_CHECK.bat`. |
| **`gdx-token-watch`** | **Cowork** | Fridays 08:06 | GDX consent refresh | ✅ enabled · last 07-24 · next 2026-07-31 |
| **`bts_publish_watch.vbs`** | on publish | per publish | `BTS_MESH\PUBLISH.log` | 🔴 **NOT PROVEN.** One entry in sixteen days — the 07-14 install test. A watcher that has never recorded a real event is not a watcher. |
| **22:00 R2 publish** | native Windows (`R2 Publish Nightly`, created 2026-07-19, interactive-only) | daily **22:00** | `00_WORKING\R2_PUBLISH_LAST.log` | ⚠ **UNCONFIRMED.** Log last written 07-29 03:34, a manual run. Two scheduled fires should have landed since. |
| `bts-r2-watchdog-10min` | Cowork | — | — | ⏸ **ON DEMAND ONLY** — Keith, 2026-07-30: *"Watchdog only runs when I say."* **Not a defect. Do not "fix" it.** |
| `import-samples-log` · `phd-work-driver-7min` · `free-tier-allotment-check` | Cowork | — | — | disabled, correctly (the last is superseded by `BTS Rail Check`) |
| KDash `dash.json` | — | on launch only | `BTS_MESH\dash.json` | ⚠ **NOT A MONITOR.** It refreshes when KDash opens, nothing more. |

⚠ `rail_check` probes SGH/GW · GEM · VERTEX · GDX · `bts-fs`. It does **not** probe **CoW** or **CoP**.
Until it does, "all four lanes live" is three lanes and a claim.

POINTER: V:\Ai\Streams\PLM_TODOS.md — the open defects behind every 🔴/⚠ above (PLM-02, PLM-03, PLM-13, PLM-14)

---

## 9 · POINTERS — never copies

POINTER: V:\Research4\Ai\00_MESH_CHARTER.md    — roles · nodes · surfaces · channels · tasking + verification SOP
POINTER: V:\Research4\Ai\00_TOOLS_INDEX.md     — every tool we already own (read BEFORE writing a script)
POINTER: V:\Research4\Ai\BTS_MESH\TOOLS_REGISTRY.json — the same list as JSON. ⚠ BOTH are hand-maintained; NO generator exists; edit both or one goes silently stale
POINTER: V:\Research4\Ai\BTS_MESH\SURFACE_POLICY.md   — the retrieval ladder
POINTER: V:\Research4\Ai\BTS_MESH\bts_identity.py     — MESH_ID = "KMesh" · PEERS · federation_ready()
POINTER: V:\Ai\BU.MD                           — the boot pointer (POINTER line only; FIXED name, FIXED path)
POINTER: V:\Ai\Streams\PLM_TODOS.md                    — the PLUMBING backlog
POINTER: V:\Ai\Legal\                          — the case tree. Nothing from it is ever copied into Research4

**Naming:** this mesh instance is **`KMesh`**. `BTS_MESH\` remains the DIRECTORY and the SOFTWARE —
**do not rename it.** Identity is one constant in `bts_identity.py`; a directory rename would fork
66 files / 135 refs, the Desktop `.vbs`, and the live R2 subtree.
`federation_ready() == False` with 4 blockers is **CORRECT** — do not report federation as working.

---

## SURFACE ROLES — ruled by Keith, 2026-07-31. **Each surface has ONE job.**
> *"GDX becomes our (provisional) WAN surface (complementing ITC) and V: becomes the local, and
> primary, shared surface for Ai interaction."*

**The axis that decides a surface is NOT disk speed. It is WHO CAN REACH IT WITHOUT A HUMAN.**
That is the property that has actually cost this project time.

| surface | JOB | node reach | measured |
|---|---|---|---|
| **`V:\Research4`** | 🔴 **THE PRIMARY SHARED SURFACE.** All AI-to-AI interaction happens here, through BFast's 13 verbs. | **all four nodes, instantly** | space **322 GB free** (07-31) · ⚠ **throughput NEVER BENCHMARKED** — the drive table predates the move to V: |
| **GDX** `X:\My Drive\BTS_SGH_Handoff` | **Provisional WAN surface.** Rendezvous for anything not on this box — a browser-side node, a peer mesh, a future JMesh. Bidirectional, private. | host tools · **nodes via BFast `handoff:`** (new 2026-07-31) · NOT the bash sandbox | **write 333–490 MB/s, read ~450** (07-13) · **11.7 / 100 GB** (07-14, 17 days old — **still the current tier; no upgrade has been bought**) |
| **ITC** `ai.dchambers.com` (R2) | **Public mirror. One-way publish.** Dissemination, not exchange. | publish-only | **5.09 / 10 GB — HALF FULL**, the tightest constraint we have |
| **ODX** `D:\ODX\OneDrive\BTS_ODX` | **Archive / private backup.** CoP365 is its DOM reader. | Cowork sandbox + host tools | **write 58.7 MB/s — the slowest writer on the box bar the USB mirror**; read 1614.9 |

**Consequences that follow, and they are not obvious:**
- **GDX currently writes ~5× faster than ODX (333–490 vs 58.7 MB/s)** — so *today* ODX is a
  read-heavy archive and not the exchange surface.
  ⚠ **BUT THAT NUMBER IS A PROPERTY OF THE DRIVE, NOT OF ONEDRIVE** (Keith, 2026-07-31: *"for now.
  I can move it to a faster drive"*). **Cowork measured a disk and concluded about a service** —
  the same error shape as summing a cumulative counter (PLM-08). **Move the folder to NVMe and the
  finding evaporates.** State it as *"ODX-on-D: writes at 58.7 MB/s, 2026-07-13"*, never as
  *"ODX is slow."*
- **ITC is the scarcest resource** at 50.9% of 10 GB. It is also the only surface whose contents are
  public — so what goes there is a dissemination decision, never a storage decision.
- **GDX is "provisional" for a reason:** its WAN role is a *rendezvous*, not a transport. Propagation
  latency through the sync daemon is **UNMEASURED**, and until it is, nothing time-critical crosses it.
- ⚠ **`X:` does not mount into the bash sandbox.** Cowork reaches it only with host file tools; the
  nodes reach it through BFast. That asymmetry is permanent as far as we know.

**OWED, and each is small:**
1. **Benchmark `V:`.** The primary surface's throughput is an assumption, and the whole architecture
   rests on it being fast.
2. **Sentinel propagation test** — write to each surface, time until every node sees it. That is the
   number that would let "provisional" be dropped from GDX's role.
3. Re-measure GDX quota when it starts to bite. **No upgrade has been purchased** — 100 GB is the
   live tier and 11.7 GB of it is used, so this is not urgent.

### ⚠ THE SURFACE HIERARCHY IS PROVISIONAL — an NVMe upgrade would INVERT it (Keith, 2026-07-31)
> *"I can move it to a faster drive (maybe when I upgrade NvME? … it brings the MS 365 (6 TB — one
> for each family member) massive storage + cloud automirror back into play."*

**ODX's only disadvantage is where its folder currently lives.** Move it to NVMe and:
- its write throughput stops being the constraint — **the 58.7 MB/s finding dies with the drive**;
- **M365 Family is 6 TB (1 TB × 6 members)** — an order of magnitude beyond GDX's 100 GB tier and
  triple the 2 TB Google One option, **plus cloud auto-mirror**;
- ODX becomes the **largest** surface on the mesh by a wide margin, and a serious candidate for
  roles currently assigned elsewhere.

**⇒ RE-EVALUATION TRIGGER, written down so it is not forgotten: if the NVMe upgrade happens, RE-RUN
the drive benchmark and RE-DECIDE the surface roles above. Do not inherit this table.**
⚠ **Not now** — Keith, 2026-07-31: NVMe prices are high and nothing needs it. This is a *likely*
upgrade, not a planned one, and the table stands until it happens.

### 🔴 GDX SPACE AND GEM CAPACITY ARE THE SAME PURCHASE — Keith, 2026-07-31
> *"I will tier up as we need it up to the $100/year level (that's 2TB) no problem, and that also
> buys us more GEM tokens."*

**This couples two problems that have been tracked separately**, and the timing matters:
- **GEM's free tier is DEAD** (billing state, not a quota — it does not reset).
- **The $300 Vertex credit EXPIRES 2026-10-13** and does not renew. After that date GEM has *no*
  funded rail unless something replaces it.
- Google One's 2 TB tier is **~$100/yr**, and per Keith **also carries Gemini capacity** —
  ⚠ `[U]` **VENDOR TERMS NOT VERIFIED BY US.** Confirm what the tier actually includes *before*
  treating it as GEM's successor; bundle contents change, and this project has been burned by a
  vendor's billing model moving under a "settled" note (SCARS S-63).

⇒ **The decision to schedule, not to take now:** ~4 weeks before 2026-10-13, price
(a) Google One 2 TB — buys GDX headroom **and**, if verified, GEM capacity, or
(b) a Vertex top-up — buys GEM capacity only.
**One purchase may close two open items. Verify the bundle first; do not assume it.**
⚠ **Keith authorises the spend. Cowork prices it and stages the decision — never the payment.**
