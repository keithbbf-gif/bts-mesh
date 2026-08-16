# GLOSSARY — WHAT WORDS MEAN *HERE*

> **What makes this file change:** a term is used in this workspace in a sense that differs from
> its common one, or Keith corrects a term. Nothing else.

## 🔴 WHY THIS FILE EXISTS

On 2026-08-13 Cowork read **UPS** as *uninterruptible power supply* and built a complete causal
story on it — that Keith runs a UPS, that a mains blip puts the machine on battery, that Task
Scheduler's *Stop On Battery Mode* therefore silences the queue runner.

**UPS here means ULTRAVIOLET PHOTOELECTRON SPECTROSCOPY. It is the subject of the dissertation.**

The fiction reached `runner_doctor.py`, `BU.MD`, `PLM_TODOS.md`, `rails.toml` and a Desktop menu,
and was printed to Keith twice as *the* diagnosis with a fix attached. **Every piece of
disambiguating evidence was already loaded**: `CLAUDE.md` says *"NEXT SESSION = CHAPTER 4 / UPS
PHYSICS"*, PLM-06 is about `upsjudge`, and the Desktop tool is the **UPS judge**.

⚠ **And it took two corrections to kill.** *"This is a PC, not a laptop"* was answered by inventing
a USB-connected UPS that Windows would see as a battery — **defending the fiction instead of
dropping it.** Only *"I have no UPS"* ended it.

⇒ **A WRONG EXPANSION OF AN ACRONYM DOES NOT ANNOUNCE ITSELF.** It makes every later inference
confidently wrong, and it recruits new evidence in its own defence. *(C-16, count 4.)*

**THE RULE: before building anything on a short domain term, look it up here. If it is not here and
it matters, ask — one line costs less than a diagnosis.**

---

## PHYSICS / DISSERTATION

| term | means here | NOT |
|---|---|---|
| **UPS** | **Ultraviolet Photoelectron Spectroscopy.** The dissertation's core technique. `Judge-UPS.vbs`, `upsjudge`, "UPS physics", PLM-06's ribbon prototypes are all this. | ⛔ uninterruptible power supply. **There is no UPS device. The PC runs on AC only — measured: `BatteryChargeStatus=NoSystemBattery`.** |
| **XPS** | X-ray Photoelectron Spectroscopy. | — |
| **MEH-PPV** | The polymer under study. | — |
| **Ch4 / Ch5** | Dissertation chapters, not code chapters. | — |
| **K-96** | The 96 meV figure that turned out to be a mislabeled FD `kT` parameter, not an edge width. **Closed 2026-07-15 — not a gate.** | — |
| **EDC** | Energy Distribution Curve. | — |
| **Origin / OPJ** | OriginLab 2024 and its project files. The KE→BE chain lives in the exports. | — |

## MESH / INFRASTRUCTURE

| term | means here |
|---|---|
| **batteries** | 🔴 **The usage/spend METERS rendered on KDash** — `SGH·$`, `GEM·$`, `CLA·Q`, `CoP·¢`. *(Keith, 2026-08-13.)* Nothing to do with electrical batteries. |
| **rails** | The lanes to a model or surface: `xai`, `vertex`, `bfast`, `cli-grok`, `gemini-dom`. |
| **surfaces** | Storage the mesh writes to: `V: Ai`, GDX, ITC, ODX, JDX. |
| **nodes** | The model instances: SGH (Grok), GEM (Gemini), GW, CoPG, CoW. |
| **DOM rail** | A model driven through its **web app in Keith's logged-in browser** — prepaid, no marginal cost. Opposed to the API. |
| **ROLD** | The governance repository at `V:\Research4\Ai\ROLD`. |
| **GDX / JDX / ODX / ITC** | Google Drive exchange · Joanna's Drive (candidate) · OneDrive archive · the public R2 mirror `ai.dchambers.com`. |
| **KDash** | The dashboard — `bts_serve.py` + `jack_command.html`, launched by `KDash.vbs`. |
| **the queue** | `V:\Ai\_queue\` — drop a `.py`/`.bat` in, the native `BTS Queue Runner` executes it. |
| **C.O.S.** | CarryOverSystem — `corrections.toml`. Counts how often Keith has had to repeat a correction. |
| **PLM-nn** | An item in the plumbing backlog, `V:\Ai\Streams\PLM_TODOS.md`. |
| **S-nnn / C-nn** | A scar (`SCARS.md`) · a correction (`corrections.toml`). |
| **SAPRS** | Stream Artefact Procurement and Recording Step — the mandatory TidyUP check that cross-stream work is filed where it belongs. |
| **PDAiS** | The document-preparation pipeline; **stage 5** is chronological ordering by extracted document date. |
| **BFast** | The MCP filesystem server at `V:\Ai\BFast` — one surface, four clients. |

## LEGAL

| term | means here |
|---|---|
| **the case tree** | `V:\Ai\Legal\` — **never** `V:\Research4`, which is published. |
| **Abraxas / Jasper / Cashmere / Vadim** | Parties and entities in the active matter. |
| **CLASR** | Claim Location And Support Record — the citation-support engine (PLM-29, unbuilt). |

---

---

## KEITH'S STATED PREFERENCES ABOUT TOOLS AND SURFACES

*(Not vocabulary, but the same class of thing: facts about the operator that change what Cowork
should do, and that would otherwise live only in a transcript.)*

| stated | when | consequence |
|---|---|---|
| **"I hate that cloud interface"** — the Google Cloud console | 2026-08-13 | **Do not route him there when another path exists.** Prefer a measurement Cowork can take, a CLI, or a direct deep link to the exact page. If the console is genuinely required, say why in one line and give the exact URL — never *"go and look around in there."* ⚠ He had already searched it for a credits page and found none, **because the balance is in AI Studio's prepay system, not Cloud Billing** — so that hunt was doomed before it started. |
| **"Ask for permissions, not executions from me"** | 2026-08-11 | Cowork runs the job; Keith grants access. His clicks are money, credentials and elevation. |
| **"One is better"** — one Desktop launcher, not six | 2026-08-02 | `BTS.bat` is the single menu. Six icons became clutter inside one session. |
| **"I don't read .md"** | 2026-08-01 | Editable → `.docx`. Read-only → `.pdf`. Markdown is internal only. |
| **Reports = outcome, not reasoning** | 2026-08-12 | *"You are telling me a lot I don't need to know… it's wasting time and tokens, yours and mine."* The working goes to `SCARS.md` / `PLM_TODOS.md`; Keith gets **what changed · what it means · what he must do.** *(C-13, count 2.)* |

---

⚠ **ADDING A TERM IS CHEAP AND NOT ADDING ONE IS EXPENSIVE.** The cost of a missing entry is not
confusion — Cowork does not *feel* confused when it guesses wrong. The cost is a confident wrong
answer that then defends itself.
