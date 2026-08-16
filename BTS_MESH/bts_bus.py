"""
bts_bus.py — BTS notification bus (contract v1.1).
Implements the two hardening rules from BTS_NOTIFY_CONTRACT_v1.md:
  (a) atomic write-temp-then-rename for every payload/handoff file
  (b) append-only, author-prefixed signal log with a per-reader cursor
Pure stdlib. Safe for two writers (Grok side / Claude side) sharing one log.
"""
from __future__ import annotations
import json, os, tempfile, time, datetime

VALID_TYPES = {
    "NEW_OUTPUT_READY",   # producer staged content at `path`; consumer reads+integrates
    "QUESTION_FOR_YOU",   # producer needs consumer input; consumer answers back into ROLD
    "NEEDS_INPUT",        # blocked; needs a human decision -> surface to Keith
    "TASK_COMPLETE",      # batch done; log + advance queue
    "ACK",                # consumer acknowledges it processed a prior signal
    "SPAWN_SESSION",      # mesh: request the orchestrator launch+seed a new session
    "STATUS",             # non-blocking progress (coalesced; keep latest per sid)
    "ERROR",              # a node hit an error -> dead-letter + discovery
}
REQUIRE_PATH = {"NEW_OUTPUT_READY", "QUESTION_FOR_YOU"}


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_envelope(type_, note, path=None, ts=None, **extra) -> dict:
    if type_ not in VALID_TYPES:
        raise ValueError(f"bad type {type_!r}; valid: {sorted(VALID_TYPES)}")
    if type_ in REQUIRE_PATH and not path:
        raise ValueError(f"type {type_} requires a `path`")
    if not note or not str(note).strip():
        raise ValueError("note is required (one sentence)")
    env = {"type": type_, "path": path, "note": str(note), "ts": ts or utc_now()}
    env.update(extra)
    return env


def validate_envelope(env: dict) -> None:
    if env.get("type") not in VALID_TYPES:
        raise ValueError(f"bad/absent type: {env.get('type')!r}")
    if env["type"] in REQUIRE_PATH and not env.get("path"):
        raise ValueError(f"type {env['type']} requires `path`")
    for k in ("note", "ts"):
        if not env.get(k):
            raise ValueError(f"missing `{k}`")


def atomic_write(path: str, data: str) -> None:
    """Write to a temp file in the same dir, fsync, then os.replace (atomic).
    A reader opening `path` never sees a partial file."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)   # atomic on POSIX + NTFS
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def append_signal(log_path: str, agent: str, env: dict) -> None:
    """Append one author-prefixed JSON line. open('a') writes are atomic for
    small records on local FS, so two writers won't interleave a single line."""
    validate_envelope(env)
    agent = (agent or "?").upper()[:8]
    line = f"{agent}|{json.dumps(env, ensure_ascii=False, separators=(',', ':'))}\n"
    d = os.path.dirname(os.path.abspath(log_path)) or "."
    os.makedirs(d, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def _parse_line(line: str):
    line = line.rstrip("\n")
    if not line or "|" not in line:
        return None
    agent, _, payload = line.partition("|")
    try:
        env = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return {"agent": agent, "env": env}


def read_new_signals(log_path: str, cursor_path: str, mine: str | None = None):
    """Return signals appended since last read. Advances the cursor.
    `mine` (agent code) filters OUT the caller's own lines so a side never
    consumes its own signals."""
    if not os.path.exists(log_path):
        return []
    start = 0
    if os.path.exists(cursor_path):
        try:
            start = int(open(cursor_path).read().strip() or "0")
        except ValueError:
            start = 0
    out, idx = [], 0
    with open(log_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if idx < start:
                continue
            rec = _parse_line(line)
            if rec is None:
                continue
            if mine and rec["agent"].upper() == mine.upper():
                continue
            out.append(rec)
    atomic_write(cursor_path, str(idx + 1) if os.path.getsize(log_path) else "0")
    return out
