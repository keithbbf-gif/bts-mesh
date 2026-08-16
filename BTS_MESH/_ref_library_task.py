"""Delegate the published reference-mark library to SGH and GEM, in parallel.

WHY DELEGATE THIS AT ALL
    Rule 1: Cowork verifies and synthesises; it does not do the reading. This is a literature
    sweep for numbers, which is exactly the shape SGH and GEM are for.

WHY THE ANSWERS GET VERIFIED BEFORE THEY GO ANYWHERE NEAR THE TOOL
    A reference line on a plot is enormously persuasive — it invites the eye to place a marker at
    it. So a fabricated value here does not fail loudly, it silently biases a measurement. This
    project has already caught one fabricated DOI (the Au 5d "10.1002/adma.201906478", which was
    hot-carrier plasmonics, not gold valence band). Therefore:
      * every returned DOI is checked against Crossref, and
      * the title Crossref returns is printed so a right-service/wrong-paper answer is visible,
      * "UNKNOWN" is explicitly requested and is an acceptable answer.
    Nothing here writes to the library. It writes a REPORT, which Cowork then adjudicates.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The rails read their credentials from hardcoded Windows paths (`bts_gem.py` line 42 and friends).
# Under the Linux sandbox those paths do not exist, so a perfectly healthy rail reports "NO KEY"
# and looks dead — the same false-negative class as a FUSE read. Resolve them relative to THIS
# file instead, which is inside the tree either way, and populate the env vars the modules check
# first. This is the `bts_paths` resolver problem in miniature.
_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
for _var, _fn in (("GEMINI_API_KEY", "gemini_key.txt"),
                  ("VERTEX_API_KEY", "vertex_key.txt"),
                  ("XAI_API_KEY", "Grok_API_Token-Key.txt")):
    if not os.environ.get(_var):
        _p = os.path.join(_ROOT, ".secrets", _fn)
        if os.path.exists(_p):
            with open(_p, encoding="utf-8") as _fh:
                os.environ[_var] = _fh.read().strip().splitlines()[0].strip()

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "upsjudge", "reference_library_returns.json")

PROMPT = """You are contributing to an OPEN-SOURCE UPS/XPS analysis tool (`upsjudge`). We need a
REFERENCE MARK LIBRARY: published binding-energy values that a physicist can overlay on a
photoemission spectrum to sanity-check an energy scale.

Return values for these materials, measured by UPS/XPS/synchrotron photoemission:

  Au  : 5d5/2 peak, 5d3/2 peak, 5d band falling edge, Fermi edge, work function (polycrystalline)
  ITO : In 4d5/2, In 4d3/2, Sn 4d, O 2s, valence-band maximum, work function
  Ag  : 4d band peak, Fermi edge, work function (polycrystalline)
  Cu  : 3d band peak, work function (polycrystalline)
  Ta  : 4f7/2, 4f5/2 (metallic), Ta2O5 4f7/2, work function
  Si  : 2p3/2 (elemental), SiO2 2p, work function
  C   : 1s adventitious carbon (the standard charge-reference value, and the controversy about it)
  O   : 1s (metal oxide lattice)
  HOPG: pi-band, work function

For EACH value give exactly these fields, one line each, in this format:

  MATERIAL | FEATURE | VALUE_eV | UNCERTAINTY_eV | REFERENCE_LEVEL | DOI | FIRST_AUTHOR_YEAR_JOURNAL | ONE_LINE_CAVEAT

HARD RULES — these matter more than coverage:
 1. REFERENCE_LEVEL must be "E_F" (Fermi) or "vacuum". Getting this wrong shifts every number by
    the work function, ~4-5 eV. If the source does not say, write UNKNOWN.
 2. Say whether the value is a PEAK MAXIMUM or an EDGE/ONSET. These are different quantities and
    conflating them is a real, published error. Put it in FEATURE.
 3. If you are not certain of the DOI, write UNKNOWN. **A wrong DOI is far worse than no DOI** —
    it will be Crossref-checked and a fabrication will be caught and attributed to you.
 4. Prefer: NIST XPS Database (SRD 20), the Moulder/Briggs handbooks, Phys. Rev. B, Surf. Sci.,
    J. Electron Spectrosc. Prefer PRIMARY measurements over review compilations, and say which.
 5. Work functions are sample-history dependent (polycrystalline vs single crystal, clean vs air-
    exposed). State the condition or write UNKNOWN.
 6. Do not pad. A short list of solid values beats a long list with three inventions in it.

Output ONLY the pipe-delimited lines plus, at the end, a short section headed CAVEATS."""


def crossref(doi: str) -> tuple[bool, str]:
    """Return (exists, title). The ONLY authority on whether a DOI is real."""
    doi = doi.strip().strip('.,;')
    if not doi or doi.upper() == "UNKNOWN":
        return False, "(none given)"
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            d = json.load(r)["message"]
        t = (d.get("title") or ["(untitled)"])[0]
        cs = d.get("container-title") or [""]
        return True, f"{t}  [{cs[0]}, {d.get('issued',{}).get('date-parts',[['?']])[0][0]}]"
    except Exception as e:                                  # 404 = not a real DOI
        return False, f"{type(e).__name__}: {str(e)[:60]}"


def main() -> int:
    results: dict[str, object] = {}
    lock = threading.Lock()

    def run(name: str, fn) -> None:
        t0 = time.time()
        try:
            r = fn()
        except Exception as e:                              # a dead rail is data, not a crash
            r = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        with lock:
            results[name] = {**(r if isinstance(r, dict) else {"text": str(r)}),
                             "elapsed_s": round(time.time() - t0, 1)}
        print(f"  {name}: {'ok' if r.get('ok', True) else 'FAILED'} "
              f"in {time.time()-t0:.1f}s", flush=True)

    def sgh():
        import bts_sgh
        # Grounded search is explicitly authorised: this is a literature sweep, which is the one
        # job that genuinely needs the web. Ceiling is small and deliberate.
        # The governor prices the WORST case (max tool calls all firing), not the expected one, so
        # the authorisation has to clear that ceiling or the call is refused outright — which is
        # the governor working correctly, not a fault. $2 worst case against a $6.54 remaining
        # month budget, for the one task that genuinely needs the web.
        return bts_sgh.ask(PROMPT, search=True, spend_ok=2.00,
                           reasoning_effort="high", spill=False)

    def gem():
        import bts_gem
        return bts_gem.ask(PROMPT)

    print("dispatching SGH + GEM in parallel …", flush=True)
    ts = [threading.Thread(target=run, args=(n, f), daemon=True)
          for n, f in (("SGH", sgh), ("GEM", gem))]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=600)

    # ---- verify every DOI both of them handed back --------------------------------------------
    print("\nverifying DOIs against Crossref …", flush=True)
    checked: dict[str, dict] = {}
    for node, r in results.items():
        text = str(r.get("text") or r.get("answer") or r.get("reply") or "")
        for line in text.splitlines():
            if line.count("|") < 6:
                continue
            parts = [p.strip() for p in line.split("|")]
            doi = next((p for p in parts if p.lower().startswith("10.")), "")
            if not doi or doi in checked:
                continue
            ok, title = crossref(doi)
            checked[doi] = {"exists": ok, "title": title, "from": node}
            print(f"  {'✓' if ok else '✗ FABRICATED?'}  {doi}  {title[:70]}", flush=True)

    payload = {"prompt": PROMPT, "returns": results, "doi_check": checked,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with open(os.path.abspath(OUT), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)

    bad = [d for d, v in checked.items() if not v["exists"]]
    print(f"\n{len(checked)} DOI(s) checked · {len(bad)} did NOT resolve")
    print(f"→ {os.path.abspath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
