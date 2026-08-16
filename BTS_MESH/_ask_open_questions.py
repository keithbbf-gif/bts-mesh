"""Two genuinely open questions, sent to SGH. Neutral framing — SWOT, no seeded verdict.

Keith, 2026-07-28: *"You hardly query SGH, my quota goes woefully unused… a great employee -
terrible manager."* Measured at the time: $3.65 of a $10 month, $6.35 unused.

Both questions below were left unanswered by ME doing the work instead of asking:

  Q1 — the KherveFitting plugin question. SGH's original R0 answer made the standalone build
       CONDITIONAL on asking the existing projects first: *"open issues against LG4X-V2 and
       KherveFitting offering SEC-adjudication as a plugin; if both refuse or are dead, your
       standalone tool is justified by abandonment, not by ego"* — flagged
       *"[both UNVERIFIED — check before deciding]"*. Nobody ever checked.

  Q2 — MEH-PPV photoemission values. The tool's reference library has ONE MEH-PPV entry and it is
       this project's own manuscript. A literature sweep found nothing else verifiable.

⚠ PROMPT DISCIPLINE — the reason these are worded the way they are.
An earlier brief asked *"if you think a new tool is vanity, say so."* Both nodes returned the word
"vanity", and the echo was written up as independent agreement. **Never put the conclusion's
vocabulary in the question.** The form Keith specified: *"Evaluate X — give SWOT analysis and
overall conclusion."* Name the options, not the answer.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
for _v, _f in (("XAI_API_KEY", "Grok_API_Token-Key.txt"),
               ("GEMINI_API_KEY", "gemini_key.txt"), ("VERTEX_API_KEY", "vertex_key.txt")):
    if not os.environ.get(_v):
        _p = os.path.join(_ROOT, ".secrets", _f)
        if os.path.exists(_p):
            with open(_p, encoding="utf-8") as _fh:
                os.environ[_v] = _fh.read().strip().splitlines()[0].strip()

Q1 = """Evaluate two options for shipping a secondary-electron-cutoff (SECO) adjudication layer for
UPS spectra. Give a SWOT analysis of EACH, then an overall conclusion.

  Option A — ship it as a standalone open-source Python package (`upsjudge`): library core plus a
             Qt GUI for click-to-place cutoff/Fermi markers, verdicts, factor flags, CSV/JSON
             export. MIT-licensed, wrapping lmfit/lmfitxps/scipy rather than reimplementing them.
  Option B — contribute the same SECO layer as a plugin or PR to an existing project:
             `LG4X-V2` (Julian Hochhaus) or `KherveFitting` (Gwilherm Kerherve).

For each option: Strengths, Weaknesses, Opportunities, Threats. Then one overall conclusion naming
which you would choose, and THE ONE FACT THAT WOULD REVERSE IT.

Establish and state, with evidence:
 1. Current LICENCE of LG4X-V2 and of KherveFitting.
 2. Current MAINTENANCE state of each: last commit date, open/closed issue ratio, whether the
    maintainer responds to feature proposals, whether either has a plugin or extension mechanism.
 3. Whether either project has ANY existing secondary-electron-cutoff / work-function
    determination feature, or an open issue requesting one.
 4. Whether a GPL-3 dependency would force a derived work to GPL, and what that means for a tool
    intended to be citable and reusable by other groups.

Mark anything you could not verify as UNVERIFIED. Do not guess a licence or a commit date."""

Q2 = """Find published PHOTOEMISSION (UPS/XPS) values for MEH-PPV
(poly[2-methoxy-5-(2'-ethylhexyloxy)-1,4-phenylenevinylene]).

Wanted, each as one pipe-delimited line:
MATERIAL | FEATURE | VALUE_eV | UNCERTAINTY | REFERENCE_LEVEL (E_F or vacuum) | SUBSTRATE +
FILM PREP | DOI | FIRST_AUTHOR YEAR JOURNAL | ONE-LINE CAVEAT

  - HOMO onset / leading edge below E_F, measured by UPS
  - ionisation potential (IP)
  - film work function
  - the extent in binding energy of the first occupied (pi) band
  - any deeper valence features resolved

Three specific papers are believed to contain these and could not be read (all Schlaf group,
in-situ electrospray deposition). Say what each REPORTS if you can reach it:
  - Lagel 2005, J. Appl. Phys. 98, 023509  — 10.1063/1.1949276  (MEH-PPV / ITO)
  - Yi 2007, J. Appl. Phys. 102, 023710    — 10.1063/1.2756516  (MEH-PPV on Au and HOPG)
  - Wang 2015, J. Chem. Phys. 142, 024704  — 10.1063/1.4905502  (MEH-PPV / P3HT)

HARD RULES:
 1. Every DOI will be checked against Crossref and its returned TITLE compared to the paper you
    name. A DOI that resolves to a different paper counts as a fabrication.
 2. If unsure of a DOI write UNKNOWN and give the full citation. UNKNOWN is an expected answer.
 3. Organic HOMO onsets are substrate- and preparation-dependent. State substrate and prep for
    every value or write UNKNOWN. Where the literature spans a range, give the RANGE.
 4. Distinguish ONSET/EDGE from PEAK MAXIMUM explicitly.
 5. Flag any value that is CYCLIC VOLTAMMETRY or an optical gap rather than photoemission. The
    widely-quoted "MEH-PPV HOMO = -5.3 eV" is believed to be CV, not UPS — confirm or refute.
 6. Do not pad. Few solid values beat many with inventions."""


def main() -> int:
    import bts_sgh

    out: dict[str, dict] = {}
    lock = threading.Lock()

    def ask(tag: str, prompt: str, spend: float) -> None:
        t0 = time.time()
        try:
            r = bts_sgh.ask(prompt, search=True, spend_ok=spend, spill=False)
        except Exception as e:                       # a dead rail is data
            r = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        with lock:
            out[tag] = {**r, "elapsed_s": round(time.time() - t0, 1)}
        print(f"  {tag}: ok={r.get('ok')} {len(str(r.get('text') or ''))} chars "
              f"in {time.time()-t0:.0f}s {str(r.get('reason') or r.get('error') or '')[:90]}",
              flush=True)

    ts = [threading.Thread(target=ask, args=a, daemon=True)
          for a in (("Q1_kherve_vs_standalone", Q1, 2.0), ("Q2_mehppv_values", Q2, 2.0))]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=240)

    here = os.path.dirname(os.path.abspath(__file__))
    for tag, r in out.items():
        if r.get("text"):
            with open(os.path.join(here, f"ANSWER_{tag}.md"), "w", encoding="utf-8") as fh:
                fh.write(str(r["text"]))
    with open(os.path.join(here, "_open_questions.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("written to BTS_MESH/ANSWER_*.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
