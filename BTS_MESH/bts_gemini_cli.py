r"""
bts_gemini_cli.py — the cli-gemini lane, with the environment it cannot run without. 2026-08-16.

WHY THIS FILE EXISTS AT ALL
  The gemini CLI needs three environment variables or it exits rc=41 saying so. Those three were
  discovered at 03:31 after four failed attempts and were written into rails.toml — where they are
  correct, documented, and READ BY NOBODY. A configuration recorded in a control document that no
  caller loads is a configuration that only works when a human remembers it, which is the same
  class of defect as a hardcoded literal in a dashboard: right in one place, absent where it runs.

  ⇒ So the env lives in ONE file, gemini_cli_env.json, and every caller loads it from here.

🔴 THE THREE VALUES, AND WHY EACH ONE BIT
  GOOGLE_CLOUD_PROJECT     ADC proves WHO you are; it does not say what to bill. Without this the
                           CLI exits 41 even with a valid sign-in.
  GOOGLE_CLOUD_LOCATION    MUST be "global". us-central1 returned HTTP 404 on all three attempts —
                           with the project id AND with the project number. A 404 here reads like a
                           dead lane and is actually a wrong region, which is why this cost an hour.
  GOOGLE_GENAI_USE_VERTEXAI  routes to Vertex rather than the AI-Studio surface, whose free-tier
                           entitlement on this account is depleted.

⚠ ACCOUNT: joanna.bbf@gmail.com. Every call on this lane draws the $300 Vertex credit — the only
  Google money that exists — and it expires 2026-10-13. keith.bbf is also credentialed on this box
  and is NOT the one to use. State the account inside any finding about this lane.

⚠ AND IT IS AN npm SHIM. `gemini` is a .CMD with no .exe; CreateProcess appends only .exe, so a
  bare list-argv call raises WinError 2 and looks exactly like "not installed". rails.toml recorded
  this lane as "BINARY NOT ON PATH" for four days because of it. Resolve with shutil.which and
  launch through `cmd /c`.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENVFILE = os.path.join(HERE, "gemini_cli_env.json")

FALLBACK = {"GOOGLE_CLOUD_PROJECT": "project-5a33f910-1251-4d6a-bf9",
            "GOOGLE_CLOUD_LOCATION": "global",
            "GOOGLE_GENAI_USE_VERTEXAI": "true"}


class GeminiCliError(RuntimeError):
    pass


def env():
    """The environment this lane needs. File first; the fallback is labelled, not silent."""
    try:
        d = json.load(open(ENVFILE, encoding="utf-8"))
        e = d.get("env") or d
        if not isinstance(e, dict) or "GOOGLE_CLOUD_LOCATION" not in e:
            raise ValueError("no GOOGLE_CLOUD_LOCATION in %s" % ENVFILE)
        return dict(e)
    except Exception:                                                 # noqa: BLE001
        # Deliberately NOT silent: a caller that ends up on the fallback should be able to find out.
        os.environ.setdefault("BTS_GEMINI_CLI_FELL_BACK", "1")
        return dict(FALLBACK)


def argv(prompt, yolo=True):
    exe = shutil.which("gemini")
    if not exe:
        raise GeminiCliError(
            "gemini is not on PATH. It is an npm shim — install with "
            "`npm install -g @google/gemini-cli`. Note that shutil.which finds .CMD and "
            "CreateProcess does not, so 'not installed' and 'cannot be launched' look identical.")
    head = ["cmd", "/c", exe] if exe.lower().endswith((".cmd", ".bat")) else [exe]
    a = head + ["-p", prompt]
    if yolo:
        a += ["--approval-mode", "yolo"]
    return a


def ask(prompt, timeout=300):
    """One prompt through the CLI, with the environment already correct.

    Returns {ok, text, rc}. Decodes bytes explicitly — text=True uses the locale codec, which on
    this box is cp1252 and dies on the CLI's own banner glyphs.
    """
    p = subprocess.run(argv(prompt), capture_output=True, timeout=timeout,
                       env=dict(os.environ, **env()))
    out = (p.stdout or b"").decode("utf-8", "replace")
    err = (p.stderr or b"").decode("utf-8", "replace")
    body = out + err
    if p.returncode != 0 or "must specify" in body.lower():
        return {"ok": False, "rc": p.returncode, "text": None,
                "detail": body.strip().splitlines()[-1][:300] if body.strip() else "no output"}
    # the CLI prints warnings on stderr; the answer is stdout
    return {"ok": True, "rc": 0, "text": out.strip(), "warnings": err.strip()[:200]}


def selftest(verbose=True):
    """A checkable answer, so a lane returning fluent noise is distinguishable from one that works."""
    q = "Answer with ONLY the number, no words: what is 4177 multiplied by 913?"
    want = str(4177 * 913)
    try:
        a = argv(q)
    except GeminiCliError as e:
        print("[FAIL] %s" % e); return 1
    if verbose:
        print("  env: %s" % json.dumps(env()))
        print("  argv resolves: %s" % a[2 if a[0] == "cmd" else 0])
    r = ask(q)
    ok = bool(r.get("ok")) and want in (r.get("text") or "")
    print("  expected %s · %s" % (want, "PASS" if ok else "FAIL — %s" % (r.get("detail") or r.get("text"))[:160]))
    if os.environ.get("BTS_GEMINI_CLI_FELL_BACK"):
        print("  [warn] gemini_cli_env.json was unreadable; ran on the built-in fallback")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv or len(sys.argv) == 1:
        raise SystemExit(selftest())
    print(json.dumps(ask(" ".join(a for a in sys.argv[1:] if not a.startswith("-"))), indent=1))
