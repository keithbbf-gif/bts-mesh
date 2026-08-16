#!/usr/bin/env python3
"""
mesh_fanout.py — put ONE question to EVERY node in the mesh, in parallel, and collect the answers.

WHY THIS EXISTS
  Keith, 2026-08-01: *"use multiple AGENTS across different AIs. THAT'S what I mean by delegate.
  GEM is a gem and SGH is a POWERHOUSE - you can't overtax it, like 20 agents and a speed demon -
  MASSIVE RESOURCES behind that. Try the Coders as well - they have a different take on things...
  It's also training to use and maximize the MESH."*

  Claude subagents share one model's priors. Four model families do not. The point of the mesh is
  DISAGREEMENT — a finding that survives grok-4.5, gemini-2.5-pro, grok-build and Copilot is worth
  more than the same finding four times from one family.

WHAT IT DOES
  Sends the same prompt to every reachable node and writes each return to its own file:
      SGH   grok-4.5 via bts_sgh (API)            — paid, fast, adversarial
      GEM   gemini-2.5-pro via bts_vertex (API)   — 1M context, careful, cites well
      GW    grok-build-0.1 via bts_sgh (API)      — coder's take. ⚠ rejects reasoningEffort (S-fixed)
      CoPG  GitHub Copilot CLI (subprocess)       — coder's take, metered in AI credits
  Nothing is aggregated automatically. **Cowork reads all four and verifies host-side** — the whole
  point is to see where they disagree, and an averaging step would hide exactly that.

WHY NATIVE, NOT SANDBOX
  Measured 2026-08-01: the Cowork bash sandbox caps a call at 45 s. A 29 KB slice to gemini-2.5-pro
  took 32.2 s; 119 KB and 165 KB slices both timed out. Anything real must run here.

USAGE
    py -3.14 mesh_fanout.py --prompt-file Q.txt --out V:\\Ai\\Legal\\MESH\\ --tag case_eval
    py -3.14 mesh_fanout.py --prompt-file Q.txt --nodes sgh,gem      # subset
    py -3.14 mesh_fanout.py --selftest                              # no spend
"""
from __future__ import annotations
import argparse, concurrent.futures as cf, json, os, shutil, subprocess, sys, time
from pathlib import Path

MESH = Path(__file__).resolve().parent
DEFAULT_OUT = Path(r"V:\Ai\Legal\MESH")

# GEM's per-task cap defaults to $0.01 — smaller than one call over a large slice. Measured
# 2026-08-01: a sweep returned bundle 1 and refused eight others with reason=PER_TASK_CAP, and
# because a refusal returns ok=False with empty text rather than raising, it left NO artifact.
GEM_TASK_CAP_USD = 15.00

# OA API per-call authorisation. A full ~422k-token record read measured $1.0056 on terra; this
# permits that and leaves room for a larger slice, while staying under bts_oa_api.MAX_CALL_USD
# ($3.50). The module refuses on the ESTIMATE, before the call, so an over-large prompt is declined
# rather than discovered on the invoice.
OA_CALL_CEILING_USD = 2.50


def _sgh(prompt: str, model: str = "grok-4.5") -> tuple[str, dict]:
    sys.path.insert(0, str(MESH))
    import bts_sgh
    r = bts_sgh.ask(prompt, priority="WORK", model=model, spill=False)
    txt = r.get("full_text") or r.get("text") or ""
    if not txt and r.get("path"):
        try:
            txt = Path(r["path"]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return txt, r


def _gem(prompt: str) -> tuple[str, dict]:
    sys.path.insert(0, str(MESH))
    import bts_vertex
    try:
        bts_vertex.reset_task("mesh_fanout", cap_usd=GEM_TASK_CAP_USD)
    except Exception:
        pass
    r = bts_vertex.ask(prompt)
    return r.get("text") or "", r


def _gw(prompt: str) -> tuple[str, dict]:
    # grok-build-0.1 — the coder's model. bts_sgh strips reasoningEffort for it (it 400s otherwise,
    # which is why every GW call silently failed for days while GW was recorded LIVE conf=V).
    return _sgh(prompt, model="grok-build-0.1")


def _g43(prompt: str) -> tuple[str, dict]:
    # grok-4.3 — the 1M-context xAI rail, $1.25/M in against grok-4.5's $2.00. Added 2026-08-03
    # because the bench that had to read the WHOLE case record could not fit in grok-build's 256K
    # and there was no reason to pay grok-4.5's rate for a second opinion on the same file.
    return _sgh(prompt, model="grok-4.3")


def _oa(prompt: str) -> tuple[str, dict]:
    """OpenAI API (bts_oa_api) — gpt-5.6-terra. ADDED 2026-08-16, and it is the reason to care.

    🔴 EVERY OTHER NODE IN THIS TABLE TRUNCATES THE RECORD. Measured ceilings:
        grok-4.5 (sgh) .... 500,000 tok      grok-build (gw) ... 256,000 tok
        grok-4.3 (g43) .... 1,000,000 tok    codex ............. 272,000 tok
        openai-api ........ 1,050,000 tok  <- and 438,135 tok in one call is PROVEN, not claimed
    The war-game record is ~422k tokens. A node that truncates it still answers, confidently, about
    the part it saw — which is the worst failure mode available to a fan-out whose entire purpose is
    that several families read the SAME thing. This lane is here so at least one of them provably did.

    COST: terra is $2/$12 per MTok. A full-record read measured $1.0056. spend_ok is set high enough
    to permit exactly that and no more; bts_oa_api refuses on the ESTIMATE, before spending.
    ⚠ ask() returns only a 600-char HEAD when the answer spills to file — so read the spill, or the
    fan-out records a truncated answer and calls it a return. Same trap as _sgh's r['path'].
    """
    sys.path.insert(0, str(MESH))
    import bts_oa_api
    r = bts_oa_api.ask(prompt, tier="terra", max_output_tokens=8000,
                       spend_ok=OA_CALL_CEILING_USD)
    txt = r.get("text") or ""
    if r.get("spill"):
        try:
            txt = Path(r["spill"]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return txt, r


def _copg_argv(tmp: Path) -> list[str]:
    """Build the Copilot CLI argv, resolving the npm shim properly on Windows.

    🔴 THE 2026-08-03 FAILURE, AND IT WAS DIAGNOSED BACKWARDS FOR AN HOUR.
    `--node copg --side J` raised FileNotFoundError / WinError 2, and the launcher had everyone
    braced for a context ceiling on 1.6 MB. It was nothing of the kind. `where copilot` finds
        C:\\Users\\Papa\\AppData\\Roaming\\npm\\copilot
        C:\\Users\\Papa\\AppData\\Roaming\\npm\\copilot.cmd
    - an npm global shim: an extensionless bash script plus a .cmd wrapper, and NO .exe.
    `cmd` resolves `copilot` to `copilot.cmd` through PATHEXT. Python's subprocess with
    shell=False calls CreateProcess, which appends only `.exe`. So it hunted for copilot.exe,
    found none, and raised - while `where copilot` printed two hits and made the tool look
    installed and the code look broken.

    ⇒ "The program is not installed" and "Python cannot launch the program that is installed"
      produce the IDENTICAL error. `where` answers the first question and not the second.

    FIX: resolve with shutil.which (which honours PATHEXT), and if the result is a .cmd or .bat,
    launch it through `cmd /c` - CreateProcess cannot execute a batch file directly either.
    """
    exe = shutil.which("copilot") or "copilot"
    # 🔴 RELATIVE FILENAME, AND THE CALLER MUST SET cwd TO THE FILE'S DIRECTORY. Measured 2026-08-16.
    # An ABSOLUTE path returned "Permission denied and could not request permission from user" —
    # Copilot's file tool is scoped to the working directory, so a path into V:\ from a cwd
    # elsewhere is refused. The same file, named relatively with cwd set, read in 16 s:
    #     "Read _copg_route_probe.txt  |  6 lines read"  ->  3813601
    # ⇒ The refusal was never about permissions in the Windows sense. It was scope, and the error
    #   text pointed at the wrong thing — which is why this read as a dead lane for weeks.
    args = ["-p", "Read the file " + tmp.name + " in the current directory and answer it in full. "
                  "Write nothing but the answer.",
            "--allow-all-tools"]
    if exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe, *args]
    return [exe, *args]


# 🔴 MEASURED 2026-08-16 — cmd metacharacters, the reason inline is not unconditional.
# `cmd /c` interprets & | < > ^ % even after Python quotes the argument list. Legal prose contains
# ampersands and percent signs routinely ("Chambers & Sons", "100%"), so an inline prompt carrying
# them can be silently truncated or mangled — the same class as the `%` and `!` traps that ate a
# .bat twice on 2026-08-02. Detect and route around, never hope.
_CMD_META = set("&|<>^%")


def _copg_argv_inline(prompt: str) -> list[str] | None:
    """Inline delivery. Returns None if the prompt is unsafe for `cmd /c`.

    🔴 NEWLINES ADDED TO THE GUARD 2026-08-16, AFTER THE FIRST REAL FAN-OUT.
    The single-line probe that proved inline delivery ("what is 17 * 23...") carried no newlines.
    The first REAL question did — 966 bytes over ~20 lines — and CoPG replied:
        "No specific question was provided - please state the task or topic."
    `cmd /c` does not carry a multi-line argument through as one string. So the lane answered,
    politely, about nothing, with rc=0 and a file on disk. THE SAME FAILURE SHAPE AS THE
    PERMISSION-DENIED FILE ROUTE IT REPLACED: a rail that fails by answering.
    ⇒ THE PROBE THAT PROVED THE FIX WAS UNREPRESENTATIVE OF THE TRAFFIC. A one-line test cannot
      certify a path that will carry twenty-line prompts, and every real mesh prompt is multi-line.
      Test with the shape of the real load, not the shape that is easy to type.
    """
    if _CMD_META & set(prompt) or "\n" in prompt or "\r" in prompt:
        return None
    exe = shutil.which("copilot") or "copilot"
    args = ["-p", prompt, "--allow-all-tools"]
    if exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe, *args]
    return [exe, *args]


def _copg(prompt: str) -> tuple[str, dict]:
    # GitHub Copilot CLI. The prompt goes via FILE, never inline.
    # 2026-07 scar: prompts inlined into a cmd/start wrapper lost their doubled quoting and the
    # calls died silently. 2026-08-02: the docstring describing that scar contained a literal
    # triple-quote and broke this file the same way. Quoting bites twice. Comments only, here.
    # 🔴 STABLE PATH, AND IT IS NOT DELETED. Keith, 2026-08-03: "The input prompt is identical."
    # It was not, and could not be shown to be. The old name was PID-based and a `finally` block
    # unlinked it, so when the 89-second run died on the decode, the EXACT input that produced it
    # went too - a second loss from the same failure, and the quieter one.
    #   - A fixed name means a re-run is byte-identical BY CONSTRUCTION, not by assumption.
    #   - The sha256 is printed, so "identical" becomes a checkable claim.
    #   - If any provider does prefix caching, an unchanged prompt is the only way to earn it.
    #   - And the input to any paid call should outlive the call. Ours did not.
    import hashlib
    tmp = MESH / "_copg_prompt.txt"
    data = prompt.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()[:16]
    prior = tmp.read_bytes() if tmp.exists() else None
    tmp.write_bytes(data)
    print(f"  copg prompt -> {tmp}  ({len(data):,} B  sha256:{digest}"
          + ("  IDENTICAL to the last run)" if prior == data else
             "  DIFFERENT from the last run)" if prior is not None else "  first run)"))
    try:
        # 🔴 CAPTURE BYTES AND DECODE OURSELVES. NEVER text=True HERE.
        # 2026-08-03, the second CoPG failure: the call SUCCEEDED - Copilot worked for 89.3
        # seconds - and then subprocess's own reader thread died decoding the output, because
        # text=True decodes with the LOCALE encoding, which on this box is cp1252:
        #     UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f in position 168
        # Position 168. The answer died in its first line, and 89 seconds of prepaid work was
        # thrown away by our own decoder. A CLI that draws spinners, box characters or any
        # non-Latin-1 glyph will emit bytes cp1252 has no mapping for - that is normal output,
        # not corruption.
        # ⇒ Two failures in a row where COPILOT WAS FINE and the plumbing was not. Decode
        #   explicitly, replace what will not map, and never let an encoding kill a paid call.
        # 🔴 DELIVERY CHANGED 2026-08-16. INLINE FIRST, FILE AS THE FALLBACK — measured, both ways.
        # The file route was introduced to fix a 2026-07 quoting scar, and by 2026-08-16 that fix
        # had become the fault. Measured in the same run, same question, minutes apart:
        #     via FILE   -> "✗ Read _copg_probe.txt ... Permission denied and could not request
        #                    permission from user" — Copilot narrated its failure and answered
        #                    nothing. rc=0, so nothing upstream noticed.
        #     INLINE     -> "391, W". Correct, 8 s, 0.46 credits.
        # ⇒ THE LANE WAS NEVER DEAD. Every CoPG return since the permission behaviour changed has
        #   been the CLI politely describing a file it could not open, and `ok=True` because the
        #   process exited 0. A rail that fails by answering is the hardest kind to notice.
        # ⇒ The file is STILL WRITTEN, because its purpose was never delivery — it is the provenance
        #   record: fixed name, printed sha256, byte-identical re-runs by construction.
        argv = _copg_argv_inline(prompt)
        if argv is None:
            print("  copg: prompt contains cmd metacharacters (& | < > ^ %) — using the FILE route, "
                  "which is currently PERMISSION-DENIED. Expect a narrated non-answer.")
            argv = _copg_argv(tmp)
        # cwd=MESH is LOAD-BEARING for the file route — Copilot's file tool is scoped to the
        # working directory and refuses an absolute path from anywhere else.
        p = subprocess.run(argv, capture_output=True, timeout=900, cwd=str(MESH))
        dec = lambda b: (b or b"").decode("utf-8", "replace")
        out = dec(p.stdout) + (("\n[stderr]\n" + dec(p.stderr)) if p.returncode else "")
        # 🔴 THE LEDGER GETS BOTH STREAMS. FOUND 2026-08-16, AND IT EXPLAINS EVERY UNPRICED CALL.
        # `out` above deliberately drops stderr when the call SUCCEEDS — sensible for an answer, and
        # fatal for the meter, because Copilot prints its footer
        #       AI Credits 0.46 (8s)
        # on stderr. So `bts_cop.record(out)` saw no credits line on exactly the runs that worked,
        # and dutifully logged them UNPRICED. Six of six calls in the ledger read
        # `"UNPRICED": True` with `credits: 0.0`, and BU.MD has carried "cop_spend, 4 calls ALL
        # UNPRICED — the numerator is not being captured, so the cap cannot be derived by division"
        # as an open backlog item. The numerator was arriving every time, down the stream we threw
        # away when nothing went wrong.
        # ⇒ A METER FED ONLY BY THE FAILURE PATH RECORDS NOTHING WHEN EVERYTHING IS FINE.
        priced = dec(p.stdout) + "\n" + dec(p.stderr)
        meta = {"ok": p.returncode == 0, "returncode": p.returncode,
                "stdout_bytes": len(p.stdout or b""), "stderr_bytes": len(p.stderr or b"")}
        if not out.strip():
            meta["reason"] = (f"copilot exited {p.returncode} with "
                              f"{len(p.stdout or b'')} stdout bytes and "
                              f"{len(p.stderr or b'')} stderr bytes")
        try:                                    # never let a call go unpriced — the GW lesson
            import bts_cop
            meta["credits"] = bts_cop.record(priced, task="mesh_fanout")
        except Exception as e:
            meta["ledger_error"] = str(e)
        return out, meta
    finally:
        # NOT unlinked. The prompt is evidence of what was sent, and the next run must
        # be able to prove it sent the same thing. It is overwritten, never removed.
        pass


NODES = {"sgh": _sgh, "gem": _gem, "gw": _gw, "g43": _g43, "copg": _copg, "oa": _oa}


def run(prompt: str, out: Path, tag: str, nodes: list[str]) -> int:
    out.mkdir(parents=True, exist_ok=True)
    print(f"\n{'='*74}\n  mesh_fanout — {len(nodes)} node(s) · prompt {len(prompt)/1024:.1f} KB"
          f"\n  -> {out}\n{'='*74}")
    results, failed = {}, []

    def one(name: str):
        t = time.time()
        try:
            txt, meta = NODES[name](prompt)
        except Exception as e:
            return name, "", {"ok": False, "error": f"{type(e).__name__}: {e}"}, time.time() - t
        return name, txt, meta, time.time() - t

    # Parallel on purpose. Keith: SGH cannot be overtaxed; the wall-clock cost of the whole fan-out
    # should be the SLOWEST node, not the sum.
    with cf.ThreadPoolExecutor(max_workers=len(nodes)) as ex:
        for name, txt, meta, secs in ex.map(one, nodes):
            dest = out / f"{tag}__{name.upper()}.md"
            if not txt.strip():
                # A failure must SAY so and leave a trace. Silence is the defect.
                reason = meta.get("error") or meta.get("reason") or meta.get("detail") or "empty return"
                dest.with_suffix(".FAILED.txt").write_text(
                    f"node={name}\ntag={tag}\nok={meta.get('ok')}\nreason={reason}\nmeta={meta}\n",
                    encoding="utf-8")
                print(f"  {name.upper():5} 🔴 {secs:6.1f}s  FAILED — {reason}")
                failed.append(name); continue
            dest.write_text(txt, encoding="utf-8")
            cost = meta.get("cost_usd")
            print(f"  {name.upper():5} ✅ {secs:6.1f}s  {len(txt):7d} chars"
                  f"{'  $' + format(cost, '.4f') if cost else ''}")
            results[name] = len(txt)

    print(f"\n  {len(results)} of {len(nodes)} returned.")
    if failed:
        print(f"  🔴 failed: {', '.join(failed)} — re-run to retry")
    print("\n  ⚠ NOTHING HERE IS EVIDENCE. Read all returns, find where they DISAGREE, and verify")
    print("    every quote host-side. Agreement across families raises confidence; it is not proof.\n")
    return 1 if failed else 0


def selftest() -> int:
    assert set(NODES) == {"sgh", "gem", "gw", "g43", "copg", "oa"}, "node table changed"
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.md"; p.write_text("x")
        assert p.read_text() == "x"
    print("  selftest: node table intact, write path OK, nothing spent — PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file"); ap.add_argument("--prompt")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--tag", default="q")
    # `oa` added to the DEFAULT set 2026-08-16. It costs ~$0.007 on a small question and ~$1.00 on a
    # full-record read — i.e. it prices itself to the job, so including it by default does not make
    # ordinary fan-outs expensive. Leaving it opt-in would have meant the one lane that can read the
    # whole record was absent from every fan-out nobody remembered to configure, which is how the
    # DOM lanes ended up idle at 0% while Cowork did the work itself. (C-01.)
    ap.add_argument("--nodes", default="sgh,gem,gw,copg,oa")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.prompt_file:
        prompt = Path(a.prompt_file).read_text(encoding="utf-8", errors="replace")
    elif a.prompt:
        prompt = a.prompt
    else:
        print("need --prompt or --prompt-file"); return 2
    nodes = [n.strip().lower() for n in a.nodes.split(",") if n.strip() in NODES]
    return run(prompt, Path(a.out), a.tag, nodes)


if __name__ == "__main__":
    sys.exit(main())
