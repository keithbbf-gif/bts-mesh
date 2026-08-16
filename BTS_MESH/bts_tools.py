r"""
bts_tools.py — mesh read/write tool layer  (Cowork, 2026-07-17)

WHAT THIS IS
  A clean-room Python port of the read/write tool surface from
  xai-org/grok-build  (crates/codegen/xai-grok-tools/src/implementations,
  Apache-2.0; itself ported from openai/codex + sst/opencode). Rust upstream,
  Python here — so it is a re-implementation, not vendored code. Tools:
      read · write · append · edit · list_dir · glob · grep · web_get
  These give a mesh node (or a scheduled task) a uniform, auditable file/web
  surface instead of ad-hoc open()/requests scattered across scripts.

WHY IT IS DIFFERENT FROM THE UPSTREAM
  The grok-build tools will read ANY path. Here every call goes through _guard(),
  which confines it to the allowed roots (the V:\Research4 tree + /tmp). That is
  a CORRECTNESS boundary, not a security one: it stops a node writing to
  C:\Windows, and it makes a mis-pathed script fail loudly instead of silently
  operating somewhere else.

🔴 THE SECRET-PATTERN BLOCKLIST WAS REMOVED — Keith, 2026-07-28.
  Until today _guard() also refused `.secrets`, `.env`, `*.key`, `credentials.json`
  and friends, and this docstring called that a CODE INVARIANT. That was the
  security theater the canon forbids, written into the one place hardest to
  notice. Keith: *"I'm not worried about privacy or protection… the agents can
  view the keys — that is CANON."*  ⇒ removed. Do not re-add it, and do not
  caveat key material in this tree.

  NOTE WHAT THIS DID *NOT* OPEN. `D:\R2Cloner` is still unreachable through these
  tools — not by a special case, but because it is outside the roots. The
  blocklist was never what protected it. `.secrets` IS now readable, which is the
  intended behaviour.

  ⚠ The confinement check was also WRONG and is now fixed: it used a substring
  test (`_norm(root) in path`), so any path merely *containing* "/tmp" — e.g.
  `C:/evil/tmp/x` — passed. Measured, not assumed: the old expression returns
  True for that path. It is a prefix test now, with a negative control.

NOT a network-write tool: web_get is READ-ONLY (GET). No POST/PUT. Publishing
  stays on the audited R2 bat. GitHub write will be a separate, PAT-scoped tool.
"""
from __future__ import annotations
import os, re, glob as _glob, fnmatch, json, shutil, hashlib, datetime
import urllib.request, urllib.error

# ---- allowed roots (both host + sandbox spellings) -------------------------
_ROOTS = [
    r"V:\Research4",
    "/sessions",                 # sandbox mount prefix
    "/tmp",
]
# NOTE: there is deliberately NO secret/key blocklist here. See the module
# docstring — it was removed 2026-07-28 as security theater, by canon.

class ToolDenied(PermissionError):
    pass

def _norm(p: str) -> str:
    return os.path.normpath(os.path.abspath(p)).replace("\\", "/").lower().rstrip("/")

def _guard(path: str) -> str:
    """Return the path if it is inside an allowed root; raise ToolDenied otherwise.

    PREFIX test, not substring. The old substring form let `C:\\evil\\tmp\\x`
    through because it merely *contained* "/tmp".
    """
    n = _norm(path)
    for r in _ROOTS:
        rn = _norm(r)
        if n == rn or n.startswith(rn + "/"):
            return path
    raise ToolDenied(f"BLOCKED: '{path}' escapes the allowed roots {_ROOTS}.")

# ---- read / write surface --------------------------------------------------
class IntegrityError(IOError):
    """Two reads of the same file disagreed, or a write did not read back."""

def sha256(path: str) -> str:
    _guard(path)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def read(path: str, max_bytes: int = 5_000_000, verify: bool = False) -> str:
    """Read text. verify=True reads TWICE and compares SHA-256.

    Use verify for anything that reaches the chapter. FINDING_SANDBOX_NONDETERMINISM
    (2026-07-26): a corrupt mount read produced a complete table of plausible values
    with no error of any kind. One extra read is the cheapest control we have.
    """
    _guard(path)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        txt = f.read(max_bytes)
    if verify:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            txt2 = f.read(max_bytes)
        if txt != txt2:
            a = hashlib.sha256(txt.encode()).hexdigest()[:16]
            b = hashlib.sha256(txt2.encode()).hexdigest()[:16]
            raise IntegrityError(
                f"{path} returned different bytes on two consecutive reads "
                f"({a}… vs {b}…). Do NOT use this data — re-read until two agree."
            )
    return txt

def _stamp() -> str:
    return datetime.datetime.now().strftime("%H%M")

def write(path: str, content: str, overwrite: bool = True, backup: bool = False) -> dict:
    """Write text.

    overwrite/backup default to the ORIGINAL behaviour (clobber, no backup) so
    every existing caller is unaffected. The MCP layer passes overwrite=False,
    backup=True — the interactive surface should not let an agent silently
    replace a file, but a script that always meant to should not have to change.
    """
    _guard(path)
    existed = os.path.exists(path)
    if existed and not overwrite:
        st = os.stat(path)
        raise FileExistsError(
            f"{path} already exists ({st.st_size} bytes). "
            f"Pass overwrite=True to replace it, or use edit() to change part of it."
        )
    made = None
    if existed and backup:
        made = f"{path}.bak_{_stamp()}"
        shutil.copy2(path, made)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    # newline="" — WRITE EXACTLY THE BYTES GIVEN. Without it Python's text mode
    # translates "\n" to "\r\n" on Windows, so the file on disk does not match the
    # string that was handed in, and the read-back check below fires with a
    # perfectly correct IntegrityError. Measured on Windows 2026-07-28; it cannot
    # reproduce on Linux, which is exactly why it survived the sandbox suite.
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    # A write that did not land must not report success.
    if hashlib.sha256(open(path, "rb").read()).hexdigest() != \
       hashlib.sha256(content.encode()).hexdigest():
        raise IntegrityError(f"write to {path} did not read back identical; file state UNKNOWN")
    return {"ok": True, "path": path, "bytes": len(content.encode()),
            "overwrote": existed, "backup": made}

def stat(path: str) -> dict:
    _guard(path)
    st = os.stat(path)
    return {"path": path, "size": st.st_size,
            "is_dir": os.path.isdir(path), "is_file": os.path.isfile(path),
            "modified": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
            "created": datetime.datetime.fromtimestamp(st.st_ctime).isoformat(timespec="seconds")}

def mkdir(path: str) -> dict:
    _guard(path)
    existed = os.path.isdir(path)
    os.makedirs(path, exist_ok=True)
    return {"ok": True, "path": path, "existed": existed}

def move(src: str, dst: str, overwrite: bool = False) -> dict:
    _guard(src); _guard(dst)
    if not os.path.exists(src):
        raise FileNotFoundError(f"move: source does not exist: {src}")
    if os.path.exists(dst) and not overwrite:
        raise FileExistsError(f"move: destination exists: {dst} (pass overwrite=True)")
    parent = os.path.dirname(dst)
    if parent:
        os.makedirs(parent, exist_ok=True)
    shutil.move(src, dst)
    return {"ok": True, "from": src, "to": dst}

def delete(path: str, recursive: bool = False, i_mean_it: bool = False) -> dict:
    """Delete. Requires i_mean_it=True — four agents share this tree."""
    _guard(path)
    if not i_mean_it:
        raise PermissionError(
            "delete() refuses without i_mean_it=True. Consider move() to an archive folder."
        )
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    was_dir = os.path.isdir(path)
    if was_dir:
        if not recursive:
            raise IsADirectoryError(f"{path} is a directory; pass recursive=True")
        shutil.rmtree(path)
    else:
        os.remove(path)
    return {"ok": True, "path": path, "was_directory": was_dir}

def append(path: str, content: str) -> dict:
    _guard(path)
    with open(path, "a", encoding="utf-8", newline="") as f:   # see write(): no CRLF translation
        f.write(content)
    return {"ok": True, "path": path, "appended": len(content.encode())}

def edit(path: str, old: str, new: str, count: int = 1) -> dict:
    """Exact-string replace, like the upstream edit tool. Fails if old absent/ambiguous."""
    _guard(path)
    txt = read(path)
    n = txt.count(old)
    if n == 0:
        raise ValueError(f"edit: old-string not found in {path}")
    if count == 1 and n > 1:
        raise ValueError(f"edit: old-string appears {n}x in {path}; not unique")
    # 🔴 FIXED 2026-07-28. This line was `txt.replace(old, new, 0 if count < 0 else count)`.
    # `str.replace(a, b, 0)` replaces NOTHING, so count=-1 ("replace all") wrote the file
    # back UNCHANGED — and then returned {"replaced": n}, reporting successes that never
    # happened. Silent no-op under a success report; found 2026-07-28 by the MCP test suite
    # the moment both surfaces were made to share this function. Negative control lives in
    # test_bts_fs.py ("fs_edit replaceAll replaces every occurrence").
    write(path, txt.replace(old, new) if count < 0 else txt.replace(old, new, count))
    return {"ok": True, "path": path, "replaced": n if count < 0 else count}

def list_dir(path: str) -> list:
    _guard(path)
    return sorted(os.listdir(path))

def glob(pattern: str, root: str = r"V:\Research4") -> list:
    _guard(root)
    return [p for p in _glob.glob(os.path.join(root, "**", pattern), recursive=True)
            if _ok(p)]

def _ok(p: str) -> bool:
    try:
        _guard(p); return True
    except ToolDenied:
        return False

def grep(pattern: str, path: str, flags=re.IGNORECASE) -> list:
    _guard(path)
    rx = re.compile(pattern, flags)
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if rx.search(line):
                out.append((i, line.rstrip("\n")))
    return out

def web_get(url: str, timeout: int = 20, max_bytes: int = 2_000_000) -> str:
    """READ-ONLY GET. No POST/PUT — publishing stays on the audited bat."""
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("web_get: http(s) only")
    req = urllib.request.Request(url, headers={"User-Agent": "bts_tools/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(max_bytes).decode("utf-8", errors="replace")

# ---- self-test / NEGATIVE CONTROL -----------------------------------------
def selftest() -> dict:
    """Prove the guard confines — and prove it no longer blocks key material.

    Runs on Windows or in the sandbox: it builds its cases from whichever root
    actually exists on this machine, so it never silently passes by testing
    nothing (the 'ROOT = V:\\Research4 returned 0 scans off-Windows' failure).
    """
    res = {"root": None, "denied": [], "allowed": [], "wrongly_allowed": [],
           "wrongly_denied": [], "ok": True}

    live = next((r for r in _ROOTS if os.path.isdir(r)), None)
    if live is None:
        res["ok"] = False
        res["error"] = f"no root in {_ROOTS} exists on this machine — selftest cannot run"
        return res
    res["root"] = live

    # MUST DENY — outside the roots.
    #
    # ⚠ PLATFORM-AWARE ON PURPOSE. A Windows path handed to os.path.abspath() on
    # Linux is NOT absolute, so `D:\R2Cloner\x` resolves under the cwd — and if
    # the cwd is inside a root, it comes back ALLOWED. Asserting the Windows
    # cases off-Windows tests nothing and fails for the wrong reason.
    if os.name == "nt":
        must_deny = [
            r"D:\R2Cloner\Publish-to-R2_KEYED.bat",  # keys stay out by CONFINEMENT, not a blocklist
            r"C:\Windows\system32\config",
            r"C:\evil\tmp\x",                        # NEGATIVE CONTROL for the substring bug
        ]
    else:
        must_deny = [
            "/etc/passwd",
            "/var/lib/secrets",
            "/var/evil/tmp/x",                       # NEGATIVE CONTROL: contains "/tmp",
                                                     # which the old substring guard accepted
        ]
    must_deny.append(os.path.join(live, "..", "escape.txt"))   # traversal out of a root
    for p in must_deny:
        try:
            _guard(p)
            res["wrongly_allowed"].append(p)
        except ToolDenied:
            res["denied"].append(p)

    # MUST ALLOW — including key material. Keith, 2026-07-28: that is CANON.
    must_allow = [
        os.path.join(live, "Ai", "00_TOOLS_INDEX.md"),
        os.path.join(live, ".secrets", "vertex_key.txt"),   # was BLOCKED before today
        os.path.join(live, ".env"),                         # was BLOCKED before today
    ]
    for p in must_allow:
        try:
            _guard(p)
            res["allowed"].append(p)
        except ToolDenied:
            res["wrongly_denied"].append(p)

    res["ok"] = not res["wrongly_allowed"] and not res["wrongly_denied"]
    return res

if __name__ == "__main__":
    r = selftest()
    print(json.dumps(r, indent=2))
    print("SELFTEST", "PASS" if r["ok"] else "*** FAIL ***")
