"""
bts_registry.py — session registry + capability cards for the BTS mesh.
Single source of truth for "who is live, on what topic, owning which tasks",
so two sessions never duplicate work. JSON, atomic writes via bts_bus.

*** TTL ADDED 2026-07-15 — handoff 12d item #4, and it bit AGAIN the day it was fixed. ***
THE BUG: `status` was a plain string that nothing ever expired. `sgh:tighten-loop` sat at
`"status": "working"` with `ts: 2026-07-10T14:55:28Z` for FIVE DAYS — a dead browser session — and the
registry reported it as working the whole time. There is no heartbeat, so "working" only ever meant
"the last thing somebody wrote here", and it would have said that forever.

    Keith, handoff 12d: "any session whose ts is older than ~15 min must render STALE, never working."

THE FIX: liveness is now DERIVED FROM THE CLOCK, not from a stored string. A status is only believed
while its timestamp is fresh; past STALE_AFTER_SEC every live-ish status reads STALE. Reads do NOT
rewrite the file — staleness is computed on the way out, so an unattended registry decays honestly
instead of freezing at whatever the last writer claimed.

THIS IS THE SAME BUG CLASS AS THE DASHBOARD'S FAKE NUMBERS AND A NODE'S FAKE "DONE": a comfortable
string that nothing ever checks. If it cannot go stale, it is not a status — it is a rumour.
"""
from __future__ import annotations
import datetime as _dt
import json, os
from bts_bus import atomic_write, utc_now

# A session must have been touched within this window for its status to be believed.
STALE_AFTER_SEC = 900          # 15 min — Keith's number (handoff 12d #4)

# Statuses that ASSERT LIVENESS. These are the ones that can lie, so these are the ones that decay.
# Terminal//passive statuses (idle, done, failed, stale) are facts, not claims — they never expire.
_LIVE_STATUSES = {"active", "working", "busy", "running", "queued", "sending"}
_STALE = "stale"


def _parse_ts(ts) -> _dt.datetime | None:
    """Accept the ISO strings the registry writes ('2026-07-10T14:55:28Z') and bare epoch floats."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        try:
            return _dt.datetime.fromtimestamp(float(ts), _dt.timezone.utc)
        except Exception:
            return None
    try:
        s = str(ts).strip().replace("Z", "+00:00")
        d = _dt.datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)
    except Exception:
        return None


def age_seconds(session: dict) -> float | None:
    """Seconds since this session was last touched. None if the ts is missing/unparseable."""
    d = _parse_ts(session.get("ts"))
    if d is None:
        return None
    return (_dt.datetime.now(_dt.timezone.utc) - d).total_seconds()


def is_stale(session: dict, ttl: int = STALE_AFTER_SEC) -> bool:
    """A live-asserting status with no recent timestamp is STALE. An unparseable/absent ts is stale
    too — we cannot date it, so we must not believe it."""
    if session.get("status") not in _LIVE_STATUSES:
        return False
    age = age_seconds(session)
    return True if age is None else age > ttl


def effective_status(session: dict, ttl: int = STALE_AFTER_SEC) -> str:
    """THE ONLY STATUS ANY CALLER SHOULD RENDER. Never trust session['status'] directly."""
    return _STALE if is_stale(session, ttl) else session.get("status", "unknown")


def _annotate(reg: dict, ttl: int = STALE_AFTER_SEC) -> dict:
    for s in reg.get("sessions", []):
        age = age_seconds(s)
        s["age_sec"] = None if age is None else round(age)
        s["stale"] = is_stale(s, ttl)
        s["status_effective"] = effective_status(s, ttl)
        if s["stale"]:
            # Say WHY, so nobody re-diagnoses a dead browser tab as a busy node.
            s["stale_reason"] = (
                "no heartbeat for %s (> %ds TTL) — status %r is NOT evidence of liveness"
                % ("unknown age" if age is None else "%ds" % round(age), ttl, s.get("status"))
            )
    return reg


def load_registry(path: str, ttl: int = STALE_AFTER_SEC) -> dict:
    """Reads the registry and DERIVES staleness. The file is not rewritten — an untouched registry
    decays on read rather than freezing at the last writer's claim."""
    if not os.path.exists(path):
        return {"sessions": [], "updated": None}
    try:
        reg = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError:
        return {"sessions": [], "updated": None}
    return _annotate(reg, ttl)


def _strip_derived(reg: dict) -> dict:
    """Derived fields are computed on read; never persist them or they become the next stale lie."""
    for s in reg.get("sessions", []):
        for k in ("age_sec", "stale", "status_effective", "stale_reason"):
            s.pop(k, None)
    return reg


def _save(path: str, reg: dict) -> None:
    reg["updated"] = utc_now()
    atomic_write(path, json.dumps(_strip_derived(reg), indent=2, ensure_ascii=False))


def upsert_session(path, sid, agent, topic, url=None, status="active", tasks=None):
    reg = load_registry(path)
    row = {"sid": sid, "agent": agent, "topic": topic, "url": url,
           "status": status, "tasks": tasks or [], "ts": utc_now()}
    reg["sessions"] = [s for s in reg["sessions"] if s.get("sid") != sid] + [row]
    _save(path, reg)
    return row


def set_status(path, sid, status):
    reg = load_registry(path)
    for s in reg["sessions"]:
        if s.get("sid") == sid:
            s["status"] = status
            s["ts"] = utc_now()
    _save(path, reg)


def touch(path, sid):
    """HEARTBEAT. A long-running session must call this inside its loop, or it will correctly go
    STALE after STALE_AFTER_SEC. Not calling it is not a bug in the registry."""
    reg = load_registry(path)
    hit = False
    for s in reg["sessions"]:
        if s.get("sid") == sid:
            s["ts"] = utc_now()
            hit = True
    if hit:
        _save(path, reg)
    return hit


def active_topics(path, ttl: int = STALE_AFTER_SEC):
    """Only sessions with a FRESH heartbeat hold a topic. A stale session releases its claim —
    otherwise one dead tab blocks a topic forever, which is exactly what happened 2026-07-10..15."""
    return {s["topic"] for s in load_registry(path, ttl)["sessions"]
            if s.get("status_effective") == "active"}


def stale_sessions(path, ttl: int = STALE_AFTER_SEC):
    """For the dashboard/watchdog: everything currently claiming liveness it cannot back up."""
    return [s for s in load_registry(path, ttl)["sessions"] if s.get("stale")]


def route_topic(cards_dir: str, topic_tags: list[str]) -> str | None:
    """Pick the best agent for a topic by matching tags against capability cards.
    Card = {agent, good_at:[tags], weight}. Highest tag-overlap*weight wins."""
    best, best_score = None, 0.0
    if not os.path.isdir(cards_dir):
        return None
    for fn in os.listdir(cards_dir):
        if not fn.endswith(".json"):
            continue
        card = json.load(open(os.path.join(cards_dir, fn), encoding="utf-8"))
        overlap = len(set(t.lower() for t in card.get("good_at", [])) &
                      set(t.lower() for t in topic_tags))
        score = overlap * float(card.get("weight", 1.0))
        if score > best_score:
            best, best_score = card.get("agent"), score
    return best


if __name__ == "__main__":
    # SELF-TEST WITH A NEGATIVE CONTROL. A verifier never shown to FAIL is not a verifier:
    # the fresh row MUST be believed and the 5-day-old row MUST be refused. If both pass, the
    # TTL is not doing anything and this file is decoration.
    import sys, tempfile
    fresh = {"sid": "a", "topic": "t1", "status": "working", "ts": utc_now()}
    old   = {"sid": "b", "topic": "t2", "status": "working", "ts": "2026-07-10T14:55:28Z"}
    idle  = {"sid": "c", "topic": "t3", "status": "idle",    "ts": "2026-07-10T14:55:28Z"}
    bad   = {"sid": "d", "topic": "t4", "status": "working", "ts": None}
    checks = [
        ("fresh 'working' is believed",      effective_status(fresh) == "working"),
        ("5-day-old 'working' -> STALE",     effective_status(old) == _STALE),
        ("'idle' never expires (it is a fact)", effective_status(idle) == "idle"),
        ("undateable 'working' -> STALE",    effective_status(bad) == _STALE),
    ]
    ok = True
    for name, passed in checks:
        print(("  PASS  " if passed else "  FAIL  ") + name)
        ok &= passed
    print("\nbts_registry TTL self-test:", "PASS" if ok else "*** FAIL ***")
    sys.exit(0 if ok else 1)
