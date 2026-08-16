r"""
verify_gemini_cli.py — is the cli-gemini lane LIVE? One tiny prompt, one honest answer.

Called by `Desktop\FIX GEMINI CLI.bat` after a browser consent, and runnable any time.

🔴 WHY THIS IS A .py AND THE BAT ONLY CALLS IT — CLAUDE.md, twice-measured 2026-08-02:
   NEVER INLINE PYTHON IN A .bat. `cmd` eats `%` in format strings and, with delayed expansion,
   eats `!` mid-line — producing a SyntaxError pointing at text that was never in the source.
   The durable artifact is the .py in the tree; the .bat is a delivery wrapper with a lifetime of
   one use.

WHAT "LIVE" MEANS HERE, AND IT IS NOT "IT RAN":
   S-100 — a rail that handshakes is not a node that works. This asks a question with a CHECKABLE
   answer (17 x 23 = 391, and tungsten is W) so a lane that returns fluent nonsense, a login
   prompt, or a help screen is distinguishable from one that actually reached a model.
"""
import shutil
import subprocess
import sys

PROMPT = "Answer in ONE line, nothing else: what is 17 * 23, and the chemical symbol for tungsten?"
EXPECT = ("391", "W")


def main() -> int:
    exe = shutil.which("gemini")
    if not exe:
        print("  NOT ON PATH. shutil.which('gemini') found nothing.")
        print("  Install:  npm install -g @google/gemini-cli")
        return 1
    print("  binary: " + exe)

    # npm shims are .cmd with NO .exe. CreateProcess appends only .exe, so a bare list-argv call
    # raises WinError 2 and looks exactly like 'not installed'. This trap is documented in
    # mesh_fanout._copg_argv for copilot; gemini and codex are the same shape.
    argv = (["cmd", "/c", exe] if exe.lower().endswith((".cmd", ".bat")) else [exe]) \
        + ["-p", PROMPT, "--approval-mode", "yolo"]

    try:
        p = subprocess.run(argv, capture_output=True, timeout=300)
    except Exception as e:                                            # noqa: BLE001
        print("  FAILED TO LAUNCH: " + str(e))
        return 1

    # Decode bytes ourselves. text=True decodes with the LOCALE codec (cp1252 here) and a CLI that
    # draws spinners or box glyphs will kill the reader thread mid-answer — that once threw away
    # 89 seconds of prepaid work on the Copilot lane.
    body = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    ok = all(e in body for e in EXPECT)

    print("  rc=" + str(p.returncode))
    print("  ----------------------------------------------------------------")
    for line in body.strip().splitlines()[-12:]:
        print("  " + line[:150])
    print("  ----------------------------------------------------------------")

    if ok:
        print("\n  LIVE — cli-gemini answered correctly. The lane is closed.")
        print("  Record in rails.toml: state=LIVE, conf=V, measured=today.")
        return 0

    low = body.lower()
    print("\n  NOT LIVE.")
    if "403" in body or "permission" in low:
        print("  403 / permission — the credential reached Google and was refused. That is the")
        print("  AI-Studio entitlement, not the network. Same depleted free-tier path BU.MD")
        print("  records as the October cliff.")
    elif "must specify" in low or "google_cloud_project" in low:
        print("  The CLI still has no credential. The ADC sign-in did not complete, or it")
        print("  completed under a DIFFERENT account. Check:  gcloud auth list")
        print("  It must be joanna.bbf@gmail.com — the only account holding credit.")
    elif "quota" in low or "429" in low:
        print("  Quota/rate limit. The credential works; the allowance does not.")
    else:
        print("  Unrecognised failure. The last lines above are the evidence; do not guess past")
        print("  them. An absent explanation is not an absent problem.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
