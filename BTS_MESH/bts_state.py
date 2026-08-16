"""
bts_state.py — the mesh's PASSIVE STATE OBSERVER.  (Keith, 2026-07-14)

WHAT THIS IS
  An event-sourced, append-only state feed for the dashboard. It is the OPPOSITE of the old
  watchdog. The watchdog was a DOER — it polled, then handed tasks to nodes (a forcing function).
  This module is a RECORDER: an actor calls emit() to say "this already happened", and the ONLY
  thing that happens is a line gets written. That is all.

  This is the classic write-ahead-log + state-projection pattern:
    * MESH_STATE.events.jsonl  = the append-only event log. SOURCE OF TRUTH. Never rewritten.
    * MESH_STATE.json          = a best-effort PROJECTION the dashboard polls. Always rebuildable
                                 from the .jsonl via rebuild().

WHAT THIS IS NOT — and must never become (do not "improve" it into these):
  * NOT a daemon. There is no loop, no thread, no scheduler, no sleep-and-repeat. One emit() call
    writes one line and returns.
  * NOT a dispatcher. It NEVER calls a node, never sends a task, never spends a cent, never touches
    a rail or the network. It cannot make anything happen; it can only note that something did.
  * NOT a metric generator. No RNG, no invented numbers, no hardcoded "OK". A field with no real
    value is written as None and the dashboard renders it "no data" — never a plausible fake.
  (If a PERIODIC refresh of channel MEASUREMENTS is ever wanted, that is a separate, explicitly
   scheduled bench run Keith controls — bts_chanbench.py — NOT this observer's job.)

THE CORRUPTION DEFENSES (the D: bash mount silently corrupts files — proven 10+ times, see CLAUDE.md)
  1. DURABLE-FIRST. Every emit() APPENDS to the .jsonl BEFORE touching the projection. If anything
     later fails, the event is already safe on disk. The .jsonl is opened O_APPEND and each record
     is a single short line, so a concurrent writer cannot interleave a half line.
  2. NEVER CLOBBER GOOD DATA. Building the projection re-reads MESH_STATE.json. If that read fails
     to parse (a corrupt/truncated mount copy), we do NOT overwrite anything from it — we rebuild()
     the projection from the .jsonl instead. A bad projection can always be regenerated; a lost
     event cannot. So the projection is disposable and the log is sacred.
  3. ATOMIC PROJECTION WRITES. MESH_STATE.json is written to a temp file in the same directory,
     fsync'd, then os.replace()'d (atomic on NTFS + POSIX). A reader that opens mid-write sees
     either the whole old file or the whole new one — never a truncated one.
  4. SERIALIZED. A simple lock file (5 s stale-steal) serializes concurrent emitters so the seq
     counter and projection stay consistent. If the lock can't be taken, we append anyway — losing
     an event is never acceptable, a duplicated seq is.

DASHBOARD CONTRACT (what jack_command.html reads out of MESH_STATE.json)
    {
      "updated": "2026-07-14T18:03:11Z",     # ISO, top-level freshness stamp
      "seq": 42,                              # monotonic event counter
      "nodes": {                             # MESH NODES panel reads this
        "SGH": {"status":"idle","last_event":"api_recv","last_detail":"...",
                "ts":"...","direction":"in","target":"COWORK","ms":1838,"cost_usd":0.0004},
        ...
      },
      "events": [ {seq,ts,actor,target,event,detail,direction,ms,cost_usd}, ... ]  # ring, cap 200
    }                                          # SIGNAL LOG panel tails events[], newest first

CORE API
    emit(actor, target=None, event="", detail="", direction=None, ms=None, cost_usd=None, status=None)
    status_of(node) -> dict
    rebuild()       -> dict        # regenerate MESH_STATE.json from the .jsonl
CLI
    python bts_state.py --selftest                 # full self + negative-control proof
    python bts_state.py --rebuild                  # rebuild projection from the log
    python bts_state.py --show                     # print the current projection
    python bts_state.py --emit ACTOR TARGET EVENT "detail" [out|in]   # manual/DOM emit
"""
from __future__ import annotations
import json, os, time, tempfile, datetime

_HERE = os.path.dirname(os.path.abspath(__file__))

# All paths derive from one dir so --selftest can redirect to a throwaway temp dir and never
# touch the real state files or the corruptible D: mount.
_CFG = {"dir": _HERE}

EVENTS_CAP = 200          # ring-buffer size for events[] in the projection
DETAIL_CAP = 300          # keep records short -> one jsonl line stays well under PIPE_BUF (atomic append)
LOCK_STALE_S = 5.0        # steal a lock older than this

# ── THE CANONICAL ACTOR SET (Keith, 2026-07-14) ────────────────────────────────────────────────
# Every entity that "changes state" and therefore earns a nodes{} entry + a position on the dashboard
# SIGNAL CORE map. NODES are the AIs; SURFACES are the shared stores/edges that also change state
# (GDX changes when a file is written to it, ITC when a publish lands, ODX when a backup runs);
# ROLD/BUS change on session boot / command dispatch; CROSSREF changes on a DOI lookup.
#   This list is DOCUMENTATION + the normaliser's vocabulary. emit() does NOT reject an unknown actor
#   (an honest record of an unexpected actor is better than a dropped event), it just uppercases it so
#   "sgh" and "SGH" are ONE node, never two.
CANON_NODES    = ["COWORK", "SGH", "GEM", "GBW", "COPILOT"]        # the AI agents
CANON_SURFACES = ["ITC", "GDX", "ODX", "CROSSREF"]                 # shared stores / edges / rails
CANON_BUS      = ["ROLD", "BUS"]                                   # the coordination layer
CANON_ACTORS   = CANON_BUS + CANON_NODES + CANON_SURFACES


def _norm_actor(s):
    """Normalise an actor/target NAME to the canonical uppercase token so the projection cannot
    case-split one node into two ('sgh' vs 'SGH'). Unknown names are still accepted (uppercased),
    never dropped — the observer records what actually happened."""
    s = _clean(s)
    return s.upper() if s else s


def _dir() -> str:
    return _CFG["dir"]


def state_json() -> str:
    # The dashboard's state file. Keith named it MESH_STATE.json; on Windows (case-insensitive FS)
    # that IS the pre-existing lowercase mesh_state.json the dashboard already polls, so we use the
    # real on-disk name and this module becomes its SOLE owner (bts_snapshot no longer writes it).
    return os.path.join(_dir(), "mesh_state.json")


def events_jsonl() -> str:
    return os.path.join(_dir(), "MESH_STATE.events.jsonl")


def _lock_path() -> str:
    return os.path.join(_dir(), "MESH_STATE.lock")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ================================================================================================
# atomic projection write (temp-in-same-dir -> fsync -> os.replace)
# ================================================================================================
def _atomic_write(path: str, data: str) -> None:
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".mesh_state_", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)          # atomic on NTFS + POSIX
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ================================================================================================
# best-effort lock (never blocks an event; steals a stale lock after LOCK_STALE_S)
# ================================================================================================
class _Lock:
    """Context manager. ALWAYS enters — if the lock cannot be acquired it proceeds unlocked, because
    losing an event is worse than a rare duplicated seq. Records whether it actually held the lock."""

    def __init__(self):
        self.held = False

    def __enter__(self):
        path = _lock_path()
        for _ in range(60):            # ~3 s of polite retries, then proceed regardless
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                self.held = True
                return self
            except FileExistsError:
                try:
                    age = time.time() - os.path.getmtime(path)
                    if age > LOCK_STALE_S:
                        os.remove(path)      # steal a stale lock
                        continue
                except OSError:
                    pass
                time.sleep(0.05)
        return self                    # proceed unlocked — best effort

    def __exit__(self, *a):
        if self.held:
            try:
                os.remove(_lock_path())
            except OSError:
                pass
        return False


# ================================================================================================
# the event log — SOURCE OF TRUTH. pure append, never rewritten.
# ================================================================================================
def _clean(s) -> str:
    if s is None:
        return ""
    s = str(s).replace("\n", " ").replace("\r", " ").strip()
    return s[:DETAIL_CAP]


def _make_record(actor, target, event, detail, direction, ms, cost_usd, status, seq) -> dict:
    return {
        "seq": seq,
        "ts": _now_iso(),
        "actor": _norm_actor(actor) or "?",       # canonical uppercase -> nodes{} never case-splits
        "target": _norm_actor(target) or None,
        "event": _clean(event) or "event",
        "detail": _clean(detail) or None,
        "direction": direction if direction in ("in", "out") else None,
        "ms": float(ms) if isinstance(ms, (int, float)) else None,
        "cost_usd": float(cost_usd) if isinstance(cost_usd, (int, float)) else None,
        "status": _clean(status) or None,
    }


def _iter_jsonl():
    """Yield parsed records from the log, skipping any line that will not parse (a corrupt mount
    copy can hand back garbage — we tolerate it and keep going, never crash)."""
    path = events_jsonl()
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def _last_seq() -> int:
    """Highest seq already in the log. The log is authoritative, so seq is derived from it and does
    not depend on the (disposable) projection."""
    last = 0
    for rec in _iter_jsonl():
        s = rec.get("seq")
        if isinstance(s, int) and s > last:
            last = s
    return last


def _append_jsonl(rec: dict) -> None:
    """Append ONE record as ONE short line. O_APPEND + a sub-PIPE_BUF line => atomic under
    concurrency; a second writer cannot split this line."""
    path = events_jsonl()
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    line = json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n"
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND)
    try:
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


# ================================================================================================
# the projection — MESH_STATE.json. best-effort, disposable, rebuildable.
# ================================================================================================
def _derive_status(event: str, direction, explicit) -> str:
    """A node's status is a PROJECTION of its last real event, not an invented label:
        direction 'out' (it just sent)     -> 'working'  (now busy on that exchange)
        direction 'in'  (a reply came back) -> 'idle'     (that exchange is done)
        no direction                        -> 'active'   (something real happened, unclassified)
    An explicit status passed by the caller always wins. The dashboard ages 'working'/'active' to
    'stale' after its TTL, so nothing here can look live forever."""
    if explicit:
        return explicit
    if direction == "out":
        return "working"
    if direction == "in":
        return "idle"
    return "active"


def _apply(proj: dict, rec: dict) -> dict:
    proj.setdefault("nodes", {})
    proj.setdefault("events", [])
    # events ring buffer
    proj["events"].append(rec)
    if len(proj["events"]) > EVENTS_CAP:
        proj["events"] = proj["events"][-EVENTS_CAP:]
    # node projection for actor (and target, if any)
    status = _derive_status(rec.get("event", ""), rec.get("direction"), rec.get("status"))
    actor = rec.get("actor")
    if actor:
        proj["nodes"][actor] = {
            "status": status,
            "last_event": rec.get("event"),
            "last_detail": rec.get("detail"),
            "ts": rec.get("ts"),
            "direction": rec.get("direction"),
            "target": rec.get("target"),
            "ms": rec.get("ms"),
            "cost_usd": rec.get("cost_usd"),
        }
    target = rec.get("target")
    if target:
        # the counterpart node: mirror the exchange from its point of view
        mirror_dir = "in" if rec.get("direction") == "out" else ("out" if rec.get("direction") == "in" else None)
        prev = proj["nodes"].get(target, {})
        proj["nodes"][target] = {
            "status": prev.get("status", "idle") if rec.get("direction") else "active",
            "last_event": rec.get("event"),
            "last_detail": rec.get("detail"),
            "ts": rec.get("ts"),
            "direction": mirror_dir,
            "target": actor,
            "ms": rec.get("ms"),
            "cost_usd": rec.get("cost_usd"),
        }
    proj["seq"] = max(int(proj.get("seq", 0) or 0), int(rec.get("seq", 0) or 0))
    proj["updated"] = rec.get("ts") or _now_iso()
    return proj


def _load_projection_or_none():
    """Read MESH_STATE.json. Return the dict, or None if it is missing OR unparseable.
    None means 'do not trust it' — the caller must rebuild() rather than clobber the log."""
    path = state_json()
    if not os.path.exists(path):
        return {"updated": None, "seq": 0, "nodes": {}, "events": []}   # fresh, not corrupt
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict) or "events" not in d or "nodes" not in d:
            return None
        return d
    except Exception:
        return None                    # CORRUPT — signal the caller to rebuild, never overwrite blind


def rebuild() -> dict:
    """Regenerate MESH_STATE.json from the .jsonl (the source of truth) and write it atomically.
    This is the recovery path: a corrupt projection is thrown away and rebuilt from the log."""
    proj = {"updated": None, "seq": 0, "nodes": {}, "events": []}
    for rec in _iter_jsonl():
        _apply(proj, rec)
    if proj["updated"] is None:
        proj["updated"] = _now_iso()
    _atomic_write(state_json(), json.dumps(proj, indent=2))
    return proj


# ================================================================================================
# THE ONE PUBLIC CALL
# ================================================================================================
def emit(actor, target=None, event="", detail="", direction=None,
         ms=None, cost_usd=None, status=None) -> dict:
    """Record that something happened. Appends to the log (durable), then updates the projection
    (best effort). Returns the record. Does nothing else — no network, no dispatch, no spend."""
    with _Lock():
        rec = _make_record(actor, target, event, detail, direction, ms, cost_usd, status,
                           seq=_last_seq() + 1)
        _append_jsonl(rec)             # DURABLE FIRST — the event is now safe no matter what follows
        try:
            proj = _load_projection_or_none()
            if proj is None:
                # projection is corrupt: DO NOT clobber. Rebuild from the log (which already has rec).
                rebuild()
            else:
                _apply(proj, rec)
                _atomic_write(state_json(), json.dumps(proj, indent=2))
        except Exception:
            # projection is disposable; the log already holds the truth. Best-effort recover.
            try:
                rebuild()
            except Exception:
                pass
    return rec


def status_of(node) -> dict:
    """Current projected status for one node, or {'status':'no data'} if we have never seen it."""
    proj = _load_projection_or_none()
    if not proj:
        proj = rebuild()
    return proj.get("nodes", {}).get(node, {"status": "no data"})


# ================================================================================================
# BACKWARD-COMPAT SHIMS
#   The previous bts_state.py exposed snapshot()/write() and was run as `python bts_state.py <root>`
#   to (re)generate mesh_state.json. bts.py ('state' cmd), bts_snapshot.py and play_dashboard.bat
#   still call those names. They now delegate to the event-sourced projection so nothing external
#   breaks — and they NEVER fabricate: they only REBUILD from the append-only log (the source of
#   truth). `root` is accepted and ignored; all paths anchor to this module's own directory.
# ================================================================================================
def snapshot(root: str = None) -> dict:
    """Compat: return the current event-sourced projection (rebuilt from the log)."""
    return rebuild()


def write(root: str = None, out: str = None) -> str:
    """Compat: (re)generate the projection from the log and return its path."""
    rebuild()
    return state_json()


# ================================================================================================
# SELFTEST + NEGATIVE CONTROL
# ================================================================================================
def _selftest() -> int:
    tmp = tempfile.mkdtemp(prefix="bts_state_selftest_")
    _CFG["dir"] = tmp
    ok = True

    def check(label, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(("  PASS " if cond else "  FAIL ") + label)

    print("bts_state --selftest  (dir = %s)" % tmp)

    # (1) emit 5 events from 2 fake actors
    emit("ALPHA", "BETA", "api_send", "kick 1", direction="out")
    emit("BETA", "ALPHA", "api_recv", "reply 1", direction="in", ms=1234.5, cost_usd=0.0004)
    emit("ALPHA", "BETA", "api_send", "kick 2", direction="out")

    # (2) KILL the projection mid-way: write garbage into MESH_STATE.json (simulate a corrupt mount)
    with open(state_json(), "w", encoding="utf-8") as f:
        f.write('{"nodes": {"trunc')          # truncated / invalid JSON
    print("  -- injected CORRUPT MESH_STATE.json (negative control) --")

    # (3) emit again AFTER the corruption
    emit("BETA", "ALPHA", "api_recv", "reply 2", direction="in", ms=1500.0, cost_usd=0.0005)
    emit("ALPHA", None, "note", "standalone event", direction=None)

    # (a) no event lost: all 5 in the jsonl
    recs = list(_iter_jsonl())
    check("all 5 events durable in .jsonl (got %d)" % len(recs), len(recs) == 5)
    seqs = [r.get("seq") for r in recs]
    check("seq monotonic + unique %s" % seqs, seqs == [1, 2, 3, 4, 5])

    # NEGATIVE CONTROL: the corrupt projection must NOT have destroyed the log, and emit() must have
    # recovered by rebuilding rather than overwriting.
    proj = _load_projection_or_none()
    check("corrupt projection was recovered (not left corrupt)", proj is not None)
    check("recovered projection has all 5 events", proj and len(proj.get("events", [])) == 5)

    # (b) rebuild() restores a valid projection straight from the log
    with open(state_json(), "w", encoding="utf-8") as f:
        f.write("garbage not json at all")     # corrupt it AGAIN
    rebuilt = rebuild()
    check("rebuild() restores a valid projection", isinstance(rebuilt, dict) and rebuilt.get("seq") == 5)
    check("rebuilt nodes include ALPHA + BETA",
          "ALPHA" in rebuilt.get("nodes", {}) and "BETA" in rebuilt.get("nodes", {}))
    check("rebuilt event order preserved",
          [e["detail"] for e in rebuilt["events"]] ==
          ["kick 1", "reply 1", "kick 2", "reply 2", "standalone event"])

    # (c) a truncated read never crashes a reader
    with open(state_json(), "w", encoding="utf-8") as f:
        f.write('{"nodes": {"ALPHA": {"status": "work')   # truncated mid-string
    crashed = False
    try:
        p = _load_projection_or_none()          # a defensive reader
        _ = (p or {}).get("nodes", {})
    except Exception:
        crashed = True
    check("truncated read does not crash the reader", not crashed)

    # status_of recovers off the corrupt file above (it rebuilds internally)
    st = status_of("BETA")
    check("status_of('BETA') returns a real status (%s)" % st.get("status"),
          st.get("status") in ("idle", "active", "working"))
    check("status_of(unknown) is 'no data', never a fake", status_of("NOBODY")["status"] == "no data")

    # cleanup
    try:
        for fn in os.listdir(tmp):
            os.remove(os.path.join(tmp, fn))
        os.rmdir(tmp)
    except OSError:
        pass
    _CFG["dir"] = _HERE

    print("\nSELFTEST %s" % ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


# ================================================================================================
if __name__ == "__main__":
    import sys
    a = sys.argv[1:]
    if not a or a[0] == "--selftest":
        raise SystemExit(_selftest())
    if a[0] == "--rebuild":
        p = rebuild()
        print("rebuilt MESH_STATE.json from %d log events -> seq=%s" % (len(p["events"]), p["seq"]))
        raise SystemExit(0)
    if a[0] == "--show":
        print(json.dumps(_load_projection_or_none() or {}, indent=2))
        raise SystemExit(0)
    if a[0] == "--emit":
        # python bts_state.py --emit ACTOR TARGET EVENT "detail" [out|in]
        args = a[1:]
        actor = args[0] if len(args) > 0 else "COWORK"
        target = args[1] if len(args) > 1 and args[1] not in ("-", "None") else None
        event = args[2] if len(args) > 2 else "note"
        detail = args[3] if len(args) > 3 else ""
        direction = args[4] if len(args) > 4 and args[4] in ("in", "out") else None
        r = emit(actor, target, event, detail, direction=direction)
        print("emitted seq=%s  %s->%s  %s  %s" % (r["seq"], r["actor"], r["target"], r["event"], r["detail"]))
        raise SystemExit(0)
    if not a[0].startswith("--"):
        # legacy: `python bts_state.py <root>` -> rebuild the projection (old write() behaviour).
        print("wrote", write(a[0]))
        raise SystemExit(0)
    print(__doc__)
