#!/usr/bin/env python3
"""
_ch4b_review.py — adversarial review + figure proposals for the 2026-07-13 Chapter 4 state.
Run host-side (the bash sandbox has a 45 s wall; a grok-4.5 reasoning call on this brief does not fit).
Everything goes through bts_sgh.ask() / bts_gem.ask() so the ledger and the spend governor still bind.
UNGROUNDED ONLY — no web_search on the paid rail.
"""
import os, sys, json, time, threading, traceback

HERE = r"V:\Research4\Ai\BTS_MESH"
sys.path.insert(0, HERE)
import bts_sgh, bts_gem

OUT = r"V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\ch4_review_2026-07-13b"
BRIEF = os.path.join(OUT, "CH4_BRIEF_FOR_REVIEW.md")

body = open(BRIEF, encoding="utf-8").read()
assert len(body) > 25000 and "Choi 2000" in body, "BRIEF LOOKS TRUNCATED — abort"

SYSTEM = (
 "You are an ADVERSARIAL REVIEWER of a PhD dissertation chapter in experimental surface physics "
 "(synchrotron ultraviolet photoemission, UPS, of conjugated polymers). You are also an expert in "
 "scientific FIGURE DESIGN.\n"
 "YOUR JOB IS TO BREAK THIS CHAPTER, NOT TO PRAISE IT.\n"
 "WARNING, and read it: on a previous task one of the mesh's reviewers simply endorsed the authors' "
 "framing and flagged nothing. That review was worthless. A reviewer that never disagrees is not a "
 "reviewer. If you genuinely think a claim is right, you must name the part of it you tried HARDEST to "
 "break and say why you failed. Agreement without an attempted refutation will be discarded.\n"
 "RULES:\n"
 "1. NEVER invent a fact, a number, a reference or a DOI. Do not cite literature at all. If unsure, say UNSURE.\n"
 "2. CHECK THE ARITHMETIC AND THE PHYSICS OF EVERY NUMBER YOU ARE GIVEN. Recompute the ones you can. "
 "State plainly if any stated value is numerically wrong.\n"
 "3. Label every finding: [PHYSICS ERROR] / [ARITHMETIC ERROR] / [CIRCULAR] / [OVERREACH] / "
 "[UNCERTAINTY UNDERSTATED] / [CONTRADICTION] / [PRESENTATION].\n"
 "4. Quote the offending sentence, say WHY it fails, and say WHAT WOULD FIX IT.\n"
 "5. Rank findings by how badly they damage the chapter at a defence."
)

PROMPT = (
 "Produce three sections, in this order. Be terse: findings, not summaries. Do not restate the chapter.\n\n"
 "=== A. ADVERSARIAL REVIEW ===\n"
 "Attack it. Where is the physics wrong, the logic circular, the claim over-reached, the uncertainty "
 "understated, the argument internally inconsistent? Recompute the numbers. Quote / why it fails / what "
 "would fix it. Then, at the end of A, a short subsection: 'WHAT I TRIED HARDEST TO BREAK AND COULD NOT'.\n\n"
 "=== B. FIGURES (the author's specific request) ===\n"
 "Propose the figures this chapter needs. The budget is 15-17 figures in ~20 pages. For EACH figure give: "
 "(1) what it shows; (2) which specific CLAIM in the chapter it supports; (3) the data and the AXES "
 "(be concrete: what is on x, what is on y, what traces, what annotations); (4) WHY IT BEATS PROSE — what "
 "a reader cannot get from the text alone.\n"
 "House figure standard (obey it): waterfalls = offset stack, per-trace label, labelled peaks, an E_F line, "
 "arrows; fits shown as Gaussian-decomposition-under-envelope with error-barred intensity/BE-vs-dose panels; "
 "GRAYSCALE-ROBUST ALWAYS (offset, line style, markers, labels - never colour alone); colour ONLY where it "
 "carries information black-and-white cannot. Exemplar: Choi 2000 APL 76 381.\n"
 "ANSWER THIS EXPLICITLY: which of the NEW 2026-07-13 findings MOST needs a figure, and why? Candidates: "
 "the delivered-vs-labelled hv register; the bias ladder; the clipped-vs-real cutoff (Jun-05); the "
 "inflection construction; the Jun-05 fake SEC; the g-vs-a (gain vs monochromator) degeneracy. Rank them.\n\n"
 "=== C. WHAT IS MISSING ===\n"
 "What will an examiner ask for that is NOT in this chapter? Be specific and concrete."
)

status = {}


def run_sgh():
    t = time.time()
    try:
        r = bts_sgh.ask(PROMPT, system=SYSTEM, context=body, priority="WORK",
                        spill=False, reasoning_effort="low")
        txt = r.get("full_text") or r.get("text") or ""
        open(os.path.join(OUT, "REVIEW_SGH.md"), "w", encoding="utf-8").write(txt)
        status["SGH"] = {"ok": r.get("ok"), "reason": r.get("reason"), "chars": len(txt),
                         "secs": round(time.time() - t, 1), "cost_usd": r.get("cost_usd"),
                         "model": r.get("model"), "detail": str(r.get("detail"))[:300],
                         "budget": r.get("budget")}
    except Exception:
        status["SGH"] = {"ok": False, "reason": "EXC", "trace": traceback.format_exc()[-600:]}


def run_gem():
    t = time.time()
    try:
        r = bts_gem.ask(SYSTEM + "\n\n=== THE DOCUMENT ===\n\n" + body +
                        "\n\n=== YOUR TASK ===\n\n" + PROMPT)
        via = r.get("via")
        if not r.get("ok"):
            # AI Studio is dead (403/429). Vertex is the only live Gemini rail. Go there directly.
            import bts_vertex
            r2 = bts_vertex.ask(SYSTEM + "\n\n=== THE DOCUMENT ===\n\n" + body +
                                "\n\n=== YOUR TASK ===\n\n" + PROMPT)
            r2["via"] = "vertex(direct)"
            r2["aistudio_reason"] = r.get("reason")
            r = r2
        txt = r.get("text") or ""
        open(os.path.join(OUT, "REVIEW_GEM.md"), "w", encoding="utf-8").write(txt)
        status["GEM"] = {"ok": r.get("ok"), "reason": r.get("reason"), "chars": len(txt),
                         "secs": round(time.time() - t, 1), "cost_usd": r.get("cost_usd"),
                         "model": r.get("model"), "via": r.get("via"),
                         "aistudio_reason": r.get("aistudio_reason", via),
                         "detail": str(r.get("detail"))[:300], "budget": r.get("budget")}
    except Exception:
        status["GEM"] = {"ok": False, "reason": "EXC", "trace": traceback.format_exc()[-600:]}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print("packet: %d chars" % len(body))
    ts = [threading.Thread(target=run_sgh), threading.Thread(target=run_gem)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    open(os.path.join(OUT, "STATUS.json"), "w", encoding="utf-8").write(
        json.dumps(status, indent=1, default=str))
    print(json.dumps(status, indent=1, default=str))
    print("DONE")
