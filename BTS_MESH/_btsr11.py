#!/usr/bin/env python3
"""
_btsr11.py — BTS-R11 physics adversarial check, ON THE API RAILS.
Died twice on the DOM rail (CCleaner closed Chrome mid-dispatch; sandbox killed a bg proc).
An API call cannot be killed by a browser tab. Host-side only (sandbox has a 45 s wall).
UNGROUNDED both rails. No web_search on the paid rail — the governor refuses it and we do not override.
"""
import os, sys, json, time, threading, traceback

HERE = r"V:\Research4\Ai\BTS_MESH"
sys.path.insert(0, HERE)
import bts_sgh, bts_gem

OUT = r"V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING"

SYSTEM = (
    "You are an ADVERSARIAL PHYSICS REVIEWER in experimental surface physics (synchrotron "
    "ultraviolet photoemission, UPS; work-function and energy-scale metrology).\n"
    "YOUR JOB IS TO ATTACK THE ARGUMENT BELOW, NOT TO AGREE WITH IT.\n"
    "A reviewer that never disagrees is not a reviewer. If you genuinely think a step is right, "
    "you must name the part you tried HARDEST to break and say why you failed.\n"
    "RULES:\n"
    "1. Label INFERENCE where a claim is yours rather than an established result.\n"
    "2. DO NOT GIVE DOIs. You are ungrounded and will confabulate them. Every DOI we receive is "
    "checked against Crossref, and a fabricated one is worse than a gap. Name authors/journals "
    "only if you are confident, and mark them UNSURE if not.\n"
    "3. Be brutal and be terse. Findings, not summaries."
)

PROMPT = """BTS-R11 - PHYSICS ADVERSARIAL CHECK. YOUR JOB IS TO ATTACK THIS, NOT AGREE WITH IT.

SETUP (synchrotron UPS, CAMD, polycrystalline Au reference): phi_app = hv - W, where
W = KE(Fermi edge) - KE(secondary-electron cutoff). Across an hv series (~20-130 eV) phi_app
drifts by several hundred meV. Measured d(KE_F)/d(hv): 0.971 on the 3m TGM, 1.024 on the 6m TGM.
Einstein forces exactly 1.

THE STANDARD EXPLANATION we now distrust: a multiplicative energy-scale error - monochromator
photon scale (a) or analyzer KE gain (g), which are DEGENERATE (the slope only measures the
product g*a).

WHAT WE HAVE ALREADY RULED OUT, with evidence - do not re-tread it, ATTACK it:
 - DOSE / beam damage: rejected. A same-hv different-dose control (Au at hv=80 eV twice, 140 min
   apart, biased-to-biased so the bias cancels) shows phi_app moving the WRONG WAY for dose, and
   the anti-collinear biased block (70-70-80-60-60, hv anti-correlated with time) rejects it at
   ~2 sigma, sign-robust.
 - SPACE CHARGE: 2-3 orders too small at a 2nd-gen source (Hellmann 2009: ~10 meV at a 3rd-gen
   source).
 - A REAL work-function change from dose IS detected but is only -0.050 +/- 0.014 eV in 9 min -
   5.7x too small.
 - The Fermi edge CANNOT be moved by a change in the SAMPLE's work function (KE_F depends on the
   ANALYZER's phi, not the sample's). Only the SEC moves. We used this to separate a 0.5% scale
   wobble (moves KE_F, not the SEC) from a genuine dose term (moves only the SEC).

WHAT I WANT:

A. Attack the above. Which step is weakest? Is there a reason a SCALE error could legitimately
FLIP SIGN between two monochromators (0.971 vs 1.024) - grating order, c_ff, deviation angle,
zero-order offset? That sign flip is the thing we cannot explain.

B. ESCAPE DEPTH: lambda(KE) sweeps through the universal-curve minimum across 20-130 eV. If the
Au surface is a DEPTH-STACK (oxide/carbon skin over metal), does the MEASURED phi depend on
probing depth? Patch potentials, "pillowing", adsorbate dipole layers. How big can this get, and
does it produce an OFFSET or a SLOPE in phi_app vs hv?

C. What OTHER mechanism could produce a smooth multiplicative-looking drift that neither of us
has named?

D. Which SINGLE measurement most cleanly separates monochromator scale (a) from analyzer gain
(g)? (We believe it is BE(Au 4f7/2) = KE_F - KE(4f7/2) in ONE spectrum: reads 83.96 eV -> the
mono is at fault; reads ~81.6 eV, or the 4f splitting reads 3.56 instead of 3.67 eV -> the
analyzer gain is. Attack that too.)

RULES: label INFERENCE where a claim is yours rather than a paper's. DO NOT give DOIs - you are
ungrounded and will confabulate them; we check every DOI against Crossref and a fabricated one is
worse than a gap. Be brutal. If you think we are right, say WHICH PART you tried hardest to break
and failed at."""

status = {}


def run_sgh():
    t = time.time()
    try:
        r = bts_sgh.ask(PROMPT, system=SYSTEM, priority="WORK",
                        spill=False, reasoning_effort="high")
        txt = r.get("full_text") or r.get("text") or ""
        with open(os.path.join(OUT, "BTS-R11_SGH_2026-07-13.md"), "w", encoding="utf-8") as f:
            f.write("# BTS-R11 — SGH (grok-4.5, ungrounded) — 2026-07-13\n\n" + txt)
        status["SGH"] = {"ok": r.get("ok"), "reason": r.get("reason"), "chars": len(txt),
                         "secs": round(time.time() - t, 1), "cost_usd": r.get("cost_usd"),
                         "model": r.get("model"), "detail": str(r.get("detail"))[:300]}
    except Exception:
        status["SGH"] = {"ok": False, "reason": "EXC", "trace": traceback.format_exc()[-800:]}


def run_gem():
    t = time.time()
    try:
        r = bts_gem.ask(SYSTEM + "\n\n=== YOUR TASK ===\n\n" + PROMPT)
        txt = r.get("text") or ""
        with open(os.path.join(OUT, "BTS-R11_GEM_2026-07-13.md"), "w", encoding="utf-8") as f:
            f.write("# BTS-R11 — GEM (Gemini, ungrounded) — 2026-07-13\n\n" + txt)
        status["GEM"] = {"ok": r.get("ok"), "reason": r.get("reason"), "chars": len(txt),
                         "secs": round(time.time() - t, 1), "cost_usd": r.get("cost_usd"),
                         "model": r.get("model"), "via": r.get("via"),
                         "failover_from": r.get("failover_from"),
                         "detail": str(r.get("detail"))[:300]}
    except Exception:
        status["GEM"] = {"ok": False, "reason": "EXC", "trace": traceback.format_exc()[-800:]}


if __name__ == "__main__":
    print("BTS-R11 dispatch: prompt=%d chars" % len(PROMPT))
    ts = [threading.Thread(target=run_sgh), threading.Thread(target=run_gem)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    with open(os.path.join(OUT, "BTS-R11_STATUS.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(status, indent=1, default=str))
    print(json.dumps(status, indent=1, default=str))
    print("DONE")
