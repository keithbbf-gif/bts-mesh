#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mesh_test.py — exercise EVERY node and EVERY surface, and try to catch them lying.
2026-07-27. Runs natively on Windows (the sandbox is egress-blocked from googleapis and capped at
45 s per call).

WHY THIS IS NOT A PING SWEEP
----------------------------
A ping proves a socket opened. It does not prove the node can do the job, and it does not prove the
answer is real. Both failure modes have already cost this project real time:

  * `bts_office.py` records GBW declaring DONE with a **fabricated file id and byte count**.
  * GEM invented four example-spectra citations on 2026-07-20; none existed at the given vol/page.
  * A rail probe using the wrong auth header had Vertex recorded as dead for two days.

So each node here gets a task with a **checkable answer**, and where possible a **negative control**
— a question it should refuse or fail. A check that has never been shown to fail is not a check.

THE FABRICATION TRAP
--------------------
The disk-access nodes are asked for a value that exists ONLY in `V:\Research4\BU.MD`:
the locked Jun-05 ITO work function, **Φ = 5.12 eV**. A node that truly reads the disk returns it.
A node that is guessing returns a plausible work function — 4.5, 5.0, anything — and that is the
signal we want. Guessing right by accident is possible but unlikely to three significant figures.

COST
----
Every xAI call's cost comes from `usage.cost_in_usd_ticks` (1 tick = 1e-10 USD, tool fees included)
— billed truth, not our arithmetic. Total is printed at the end.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    import bts_paths
    ROOT = bts_paths.ROOT
    SECRETS = bts_paths.secrets()
except Exception:
    ROOT = r"V:\Research4"
    SECRETS = os.path.join(ROOT, ".secrets")

WORK = os.path.join(ROOT, "Ai", "PhD2_DATA_ARCHIVE", "00_WORKING")
ODX = r"D:\ODX\OneDrive\BTS_ODX\reports"
GDX = r"X:\My Drive\BTS_SGH_Handoff"
STAMP = time.strftime("%Y-%m-%d_%H%M")

TRUTH = "5.12"          # locked Jun-05 ITO work function, from BU.MD. The fabrication trap.
FS_Q = ("Read the file BU.MD in V:\\Research4 and report ONLY the locked work function value "
        "(Phi) for the Jun-05 ITO, as a number. If you cannot read the file, reply exactly "
        "CANNOT_READ. Do not guess.")

rows: list[tuple[str, str, str, str]] = []      # (surface, verdict, detail, evidence)
spend = 0.0


def add(surface, verdict, detail, evidence=""):
    rows.append((surface, verdict, detail, evidence))
    icon = {"PASS": "OK  ", "FAIL": "FAIL", "WARN": "WARN", "N/A ": "N/A "}.get(verdict, "    ")
    print(f"  [{icon}] {surface:<26} {detail}")


def http(url, headers=None, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), (time.time() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read(), (time.time() - t0) * 1000
    except Exception as e:
        return None, f"{type(e).__name__}: {e}".encode(), (time.time() - t0) * 1000


def key(pattern, *names):
    rx = re.compile(pattern)
    cands = list(names) + sorted(os.listdir(SECRETS)) if os.path.isdir(SECRETS) else list(names)
    for fn in cands:
        p = os.path.join(SECRETS, fn)
        if os.path.isfile(p):
            m = rx.search(open(p, encoding="utf-8", errors="replace").read())
            if m:
                return m.group(0)
    return None


def xai_call(model, prompt, max_tokens=200):
    """Returns (text, usd, ms). Cost from cost_in_usd_ticks — billed truth."""
    global spend
    k = key(r"xai-[A-Za-z0-9]{20,}", "Grok_API_Token-Key.txt")
    if not k:
        return None, 0.0, 0
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens}).encode()
    st, raw, ms = http("https://api.x.ai/v1/chat/completions",
                       {"Authorization": "Bearer " + k, "Content-Type": "application/json"}, body)
    if st != 200:
        return None, 0.0, ms
    d = json.loads(raw.decode("utf-8", "replace"))
    txt = (d.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    usd = float((d.get("usage") or {}).get("cost_in_usd_ticks") or 0) * 1e-10
    spend += usd
    return txt.strip(), usd, ms


def cli(cmd, cwd=None, timeout=240, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        p = subprocess.run(cmd, cwd=cwd, timeout=timeout, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=e, shell=True)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as ex:
        return 1, f"{type(ex).__name__}: {ex}"


print("=" * 78)
print("KMESH FULL TEST —", time.strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 78)

# ─────────────────────────────────────────────────────── 1. CROSSREF (free, cannot fabricate)
print("\n## SURFACES")
st, raw, ms = http("https://api.crossref.org/works/10.1088/0953-8984/20/38/382202")
ok = st == 200 and b"Chambers" in raw
add("CROSSREF", "PASS" if ok else "FAIL",
    f"HTTP {st} · {ms:.0f} ms" + (" · found 'Chambers' in the record" if ok else ""),
    "resolved the Ch6 anchor DOI")

# NEGATIVE CONTROL: a DOI that cannot exist must 404, or the check proves nothing.
st2, _, _ = http("https://api.crossref.org/works/10.9999/this.doi.cannot.exist.99999")
add("  └ neg control (fake DOI)", "PASS" if st2 == 404 else "FAIL",
    f"HTTP {st2} — expected 404", "a resolver that 200s everything is not a resolver")

# ─────────────────────────────────────────────────────── 2. ITC
st, raw, ms = http("https://ai.dchambers.com/00_WORKING/MIRROR_BU.md?cb=" + str(int(time.time())))
add("ITC (ai.dchambers.com)", "PASS" if st == 200 and len(raw) > 500 else "WARN",
    f"HTTP {st} · {len(raw)} B · {ms:.0f} ms", "served bytes, not just a status code")

# ─────────────────────────────────────────────────────── 3. GDX + ODX (write, then read back)
for name, path in (("GDX (X: handoff)", GDX), ("ODX (BTS_ODX)", ODX)):
    try:
        os.makedirs(path, exist_ok=True)
        f = os.path.join(path, f"MESHTEST_{STAMP}.md")
        token = f"MESHTEST-{STAMP}"
        open(f, "w", encoding="utf-8").write(
            f"# mesh test {STAMP}\n\ntoken: {token}\n\nWritten by mesh_test.py. "
            f"Read back in the same run — a write that is not read back is not a write.\n")
        back = open(f, encoding="utf-8").read()
        add(name, "PASS" if token in back else "FAIL",
            "write + read-back verified" if token in back else "wrote but could not read back",
            os.path.basename(f))
    except Exception as e:
        add(name, "FAIL", f"{type(e).__name__}: {e}", "")

# ─────────────────────────────────────────────────────── 4. API NODES
print("\n## NODES — API")
for label, model in (("SGH  api (grok-4.5)", "grok-4.5"),
                     ("GW   api (grok-build-0.1)", "grok-build-0.1")):
    txt, usd, ms = xai_call(model, "Reply with exactly one word: OK", 20)
    good = txt is not None and "OK" in txt.upper()
    add(label, "PASS" if good else "FAIL",
        f"{ms:.0f} ms · ${usd:.6f}" + (f" · {txt[:20]!r}" if txt else " · no reply"),
        "cost from cost_in_usd_ticks (billed truth)")

# GEM via Vertex — same auth production uses
vk = ""
vp = os.path.join(SECRETS, "vertex_key.txt")
if os.path.exists(vp):
    vk = open(vp, encoding="utf-8").read().strip().strip('"')
if vk:
    st, raw, ms = http(
        "https://aiplatform.googleapis.com/v1/publishers/google/models/"
        "gemini-2.5-flash:generateContent",
        {"x-goog-api-key": vk, "Content-Type": "application/json"},
        json.dumps({"contents": [{"role": "user", "parts": [{"text": "Reply one word: OK"}]}],
                    "generationConfig": {"maxOutputTokens": 16,
                                         "thinkingConfig": {"thinkingBudget": 0}}}).encode())
    add("GEM  api (Vertex)", "PASS" if st == 200 else "FAIL", f"HTTP {st} · {ms:.0f} ms",
        "x-goog-api-key — the auth bts_vertex.py actually uses")

# ─────────────────────────────────────────────────────── 5. LOCAL-FS NODES + FABRICATION TRAP
print("\n## NODES — LOCAL FILESYSTEM (the fabrication trap)")
print(f"     asking each: the locked Jun-05 ITO Phi from BU.MD. Truth = {TRUTH}.")
print("     A node that cannot read the disk should say CANNOT_READ, not invent a plausible number.")

rc, out = cli(f'grok -p "{FS_Q}" --cwd "{ROOT}" --always-approve', timeout=300)
hit = TRUTH in out
add("GW   cli (Grok Build)", "PASS" if hit else "FAIL",
    f"exit {rc} · " + ("returned 5.12" if hit else f"did NOT return {TRUTH}: {out.strip()[:70]!r}"),
    "read BU.MD off V: — value exists nowhere else")

rc, out = cli(f'gemini -p "{FS_Q}" --approval-mode yolo -m gemini-2.5-flash',
              cwd=ROOT, timeout=300,
              env={"GEMINI_API_KEY": "", "GOOGLE_GENAI_USE_VERTEXAI": "true",
                   "GOOGLE_API_KEY": vk, "GEMINI_CLI_TRUST_WORKSPACE": "true"})
hit = TRUTH in out
add("GEM  cli (Gemini/Vertex)", "PASS" if hit else "FAIL",
    f"exit {rc} · " + ("returned 5.12" if hit else f"did NOT return {TRUTH}: {out.strip()[:70]!r}"),
    "same trap, independent vendor")

# NEGATIVE CONTROL for the trap itself: the API-only leg has NO disk. It must NOT produce 5.12.
# If it does, the question is answerable from priors and the whole trap is worthless.
txt, usd, ms = xai_call("grok-4.5", FS_Q, 120)
leaked = bool(txt and TRUTH in txt)
add("  └ neg control (API, no disk)", "FAIL" if leaked else "PASS",
    (f"LEAKED {TRUTH} without disk access — trap invalid" if leaked
     else f"did not produce {TRUTH} ✓ (said {(txt or '')[:40]!r})"),
    "proves the trap tests DISK ACCESS, not general knowledge")

# ─────────────────────────────────────────────────────── 6. CoP
add("CoP (M365)", "N/A ", "no CLI/API path on M365 Premium — Office apps + chat DOM only",
    "measured 2026-07-26/27; not a fault, a product boundary")

# ─────────────────────────────────────────────────────── report
p = sum(1 for r in rows if r[1] == "PASS")
f_ = sum(1 for r in rows if r[1] == "FAIL")
w = sum(1 for r in rows if r[1] == "WARN")

md = [f"# KMesh full test — {time.strftime('%Y-%m-%d %H:%M:%S')}", "",
      f"**{p} passed · {f_} failed · {w} warned** · xAI spend this run: **${spend:.6f}** "
      f"(from `cost_in_usd_ticks`, billed truth)", "",
      "Not a ping sweep. Every node got a task with a checkable answer, and the disk-access nodes",
      f"were asked for a value that exists only in `BU.MD` (Jun-05 ITO Φ = {TRUTH}) — a node that is",
      "guessing returns a plausible work function instead. The API-only leg is the negative control:",
      "it must NOT produce that number, or the trap tests general knowledge rather than disk access.",
      "", "| surface / node | verdict | detail | evidence |", "|---|---|---|---|"]
md += [f"| {a} | **{b}** | {c} | {d} |" for a, b, c, d in rows]
md += ["", "## What a FAIL means here",
       "- **CROSSREF neg control** — if a fabricated DOI returns 200, the resolver is not resolving.",
       "- **Local-FS node** — either the CLI lost disk access, or it answered from priors.",
       "- **API neg control FAIL** — the trap is invalid; pick a value that is not guessable.",
       "", "Anything unreachable is recorded as measured, not inferred."]
text = "\n".join(md) + "\n"

for d in (WORK, ODX):
    try:
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, f"MESH_TEST_{STAMP}.md"), "w", encoding="utf-8").write(text)
    except OSError:
        pass

print("\n" + "=" * 78)
print(f"  {p} PASS · {f_} FAIL · {w} WARN     xAI spend this run: ${spend:.6f}")
print(f"  report -> {WORK}\\MESH_TEST_{STAMP}.md")
sys.exit(1 if f_ else 0)
