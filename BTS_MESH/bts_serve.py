"""
bts_serve.py — the dashboard's server.  REPLACES `python -m http.server 8765`.

WHY
  The dashboard needs three things a static file server cannot give it:
    /api/burn   live burn-rate for GEM (requests+tokens, free) and SGH (dollars+tokens, paid)
                plus packets{} — stat of the phone pair, board.json, tree_lock, tmp/temp_files.toml
    /api/bench  run the real mesh <TEST> — the API rails that CORS blocks the browser from timing
    /api/state  cheap heartbeat
  Everything else is served exactly as before (same port, same in-pane YouTube fix — a file://
  dashboard throws YouTube error 153, which is why this server exists at all).

DROP-IN: serve_dashboard.vbs used to launch `python -m http.server 8765`. Point it here instead.
  The static behaviour is identical; the three /api/ routes are additive.

SAFETY
  * Binds 127.0.0.1 ONLY. This process can spend money (/api/bench probes the paid SGH rail), so
    it must never be reachable off-box. Do not change to 0.0.0.0.
  * /api/bench is RATE-LIMITED to one run per BENCH_MIN_INTERVAL seconds. A dashboard left open on
    a fast poll, or a leaned-on <TEST> button, must not turn into a spend loop — SGH auto-reloads
    $5 at a time, so a runaway button is a real (small) financial bug, not just a nuisance.
  * /api/bench?free=1 runs the free rails only and spends nothing.
"""
import json, os, sys, time, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PORT = 8765
BENCH_MIN_INTERVAL = 30          # seconds. The anti-spend-loop guard. Do not lower.

_bench_lock = threading.Lock()
_last_bench = {"ts": 0.0, "result": None}


def _read_json(path, default=None):
    try:
        with open(os.path.join(HERE, path), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# ── LIVE PACKETS (phone / board / lock / tmp) ────────────────────────────────
# Peer files. Nodes talk to surfaces directly; CoW is keeper, not the bus.
# These are NOT CHANNELS through cowork. /api/burn only STATs them — no rail
# probe, no rail_check, no dash.json rewrite, no bts_kdash_feed loop.
#
# Live Windows names (diagnosis): V:\Ai\COW_TO_QA_ENGINEER.md + QA_ENGINEER_TO_COW.md,
# board.json, tree_lock|lock, tmp\temp_files.toml. In-repo docs/config copies win
# if present; otherwise the V:\Ai\ constants (and bts_paths.ai when the research
# tree is mounted). Absent lock → FREE.
_LIVE_AI = r"V:\Ai"
_PHONE_COW_TO_QA = "COW_TO_QA_ENGINEER.md"
_PHONE_QA_TO_COW = "QA_ENGINEER_TO_COW.md"
_BOARD_NAME = "board.json"
_TMP_REL = ("tmp", "temp_files.toml")
_LOCK_NAMES = ("tree_lock", "lock")


def _ai_join(*parts):
    """bts_paths.ai() when the research tree resolves; else None. Never raises."""
    try:
        import bts_paths
        return bts_paths.ai(*parts)
    except Exception:
        return None


def _peer_candidates(*rel):
    """docs/config first, then the live V:\\Ai\\ constants, then the Ai sibling, then bts_paths."""
    out = []
    here_ai = os.path.dirname(HERE)
    for base in (
        os.path.join(HERE, "docs"),
        os.path.join(HERE, "config"),
        os.path.join(here_ai, "docs"),
        os.path.join(here_ai, "config"),
    ):
        out.append(os.path.join(base, *rel))
    out.append(os.path.join(_LIVE_AI, *rel))
    out.append(os.path.join(here_ai, *rel))
    p = _ai_join(*rel)
    if p:
        out.append(p)
    return out


def _pick_peer(candidates, canonical):
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return canonical


def _pick_lock():
    """First existing tree_lock or lock; else the live V:\\Ai\\tree_lock name (absent → FREE)."""
    seen = []
    for base in (
        os.path.join(HERE, "docs"), os.path.join(HERE, "config"),
        os.path.join(os.path.dirname(HERE), "docs"),
        os.path.join(os.path.dirname(HERE), "config"),
        _LIVE_AI, os.path.dirname(HERE),
    ):
        for name in _LOCK_NAMES:
            p = os.path.join(base, name)
            seen.append(p)
            if os.path.isfile(p):
                return p
    via_ai = _ai_join("tree_lock")
    if via_ai and os.path.isfile(via_ai):
        return via_ai
    for name in _LOCK_NAMES:
        via_ai = _ai_join(name)
        if via_ai and os.path.isfile(via_ai):
            return via_ai
    return os.path.join(_LIVE_AI, "tree_lock")


def default_packet_paths():
    """Resolved peer-file paths. Override in tests; do not invent a second registry."""
    return {
        "phone_cow_to_qa": _pick_peer(
            _peer_candidates(_PHONE_COW_TO_QA),
            os.path.join(_LIVE_AI, _PHONE_COW_TO_QA)),
        "phone_qa_to_cow": _pick_peer(
            _peer_candidates(_PHONE_QA_TO_COW),
            os.path.join(_LIVE_AI, _PHONE_QA_TO_COW)),
        "board": _pick_peer(
            _peer_candidates(_BOARD_NAME),
            os.path.join(_LIVE_AI, _BOARD_NAME)),
        "lock": _pick_lock(),
        "tmp": _pick_peer(
            _peer_candidates(*_TMP_REL),
            os.path.join(_LIVE_AI, *_TMP_REL)),
    }


def _stat_peer(path):
    """mtime/size only. Missing file is honest absence, not an error."""
    out = {"path": path, "exists": False, "mtime": None, "size": None}
    if not path:
        return out
    try:
        st = os.stat(path)
    except OSError:
        return out
    out["exists"] = True
    out["mtime"] = st.st_mtime
    out["size"] = st.st_size
    return out


def _item_open(item):
    if not isinstance(item, dict):
        return True
    if item.get("open") is False:
        return False
    st = str(item.get("status") or item.get("state") or "open").lower()
    return st not in ("closed", "done", "released", "free")


def _board_fields(path):
    """board.seq + open count. Unreadable / odd shape → 0, 0 (stat still reports mtime/size)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return 0, 0
    if isinstance(data, list):
        return len(data), sum(1 for i in data if _item_open(i))
    if not isinstance(data, dict):
        return 0, 0
    seq = data.get("seq")
    seq = int(seq) if isinstance(seq, int) else 0
    raw = data.get("open")
    if isinstance(raw, int):
        return seq, raw
    if isinstance(raw, list):
        return seq, sum(1 for i in raw if _item_open(i))
    n = 0
    for key in ("items", "tasks", "cards", "entries"):
        v = data.get(key)
        if isinstance(v, list):
            n += sum(1 for i in v if _item_open(i))
        elif isinstance(v, dict):
            n += sum(1 for i in v.values() if _item_open(i))
    return seq, n


def _tmp_open_count(path):
    """open count from tmp/temp_files.toml. Stat-only otherwise — no directory walk."""
    try:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return 0
    if not isinstance(data, dict):
        return 0
    raw = data.get("open")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, list):
        return sum(1 for i in raw if _item_open(i))
    n = 0
    for key in ("files", "file", "temp_files", "temps", "open_files"):
        v = data.get(key)
        if isinstance(v, list):
            n += sum(1 for i in v if _item_open(i))
        elif isinstance(v, dict):
            n += sum(1 for i in v.values() if _item_open(i))
    if n:
        return n
    skip = {"meta", "config", "settings"}
    return sum(1 for k, v in data.items()
               if k not in skip and isinstance(v, (dict, list)))


def _iso_from_mtime(mtime):
    if not mtime:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime))


def _packet_events(phone_out, phone_in, board, lock, tmp, board_seq):
    """Events the existing cockpit renderSignals / fireNewPackets already know how to paint.

    Actor names are the peer files themselves (not a new NODES entry — posOf maps
    unknowns to the hub). CoW is not inserted as a bus hop.
    """
    ev, i = [], 0
    max_mtime = max(
        [x.get("mtime") or 0 for x in (phone_out, phone_in, board, lock, tmp)],
        default=0)
    base = int((max_mtime or 0) * 1000) + int(board_seq or 0) * 1_000_000_000

    def add(actor, target, event, detail, mtime, direction="out"):
        nonlocal i
        i += 1
        ev.append({
            "seq": base + i,
            "ts": _iso_from_mtime(mtime),
            "actor": actor,
            "target": target,
            "event": event,
            "detail": detail,
            "direction": direction,
        })

    if phone_out.get("exists"):
        add("PHONE", "SGH", "note",
            "COW_TO_QA %s B" % (phone_out.get("size") or 0),
            phone_out.get("mtime"))
    if phone_in.get("exists"):
        add("PHONE", "COWORK", "note",
            "QA_TO_COW %s B" % (phone_in.get("size") or 0),
            phone_in.get("mtime"), direction="in")
    if board.get("exists"):
        add("BOARD", "ROLD", "note",
            "seq=%s open=%s" % (board.get("seq") or 0, board.get("open") or 0),
            board.get("mtime"))
    if lock.get("status") == "FREE":
        add("LOCK", "BUS", "STATUS", "FREE", lock.get("mtime"))
    elif lock.get("exists"):
        add("LOCK", "BUS", "STATUS",
            "HELD %s" % (lock.get("holder") or "").strip(),
            lock.get("mtime"))
    if tmp.get("exists"):
        add("TMP", "COWORK", "note",
            "open=%s" % (tmp.get("open") or 0),
            tmp.get("mtime"))
    return ev


def packets(paths=None):
    """Stat the four peer files. Cheap: os.stat + two small reads. No rail I/O."""
    p = paths or default_packet_paths()
    phone_out = _stat_peer(p.get("phone_cow_to_qa"))
    phone_in = _stat_peer(p.get("phone_qa_to_cow"))
    board = _stat_peer(p.get("board"))
    lock = _stat_peer(p.get("lock"))
    tmp = _stat_peer(p.get("tmp"))

    board_seq, board_open = (0, 0)
    if board["exists"]:
        board_seq, board_open = _board_fields(board["path"])
    board["seq"] = board_seq
    board["open"] = board_open

    if lock["exists"]:
        lock["status"] = "HELD"
        holder = ""
        try:
            with open(lock["path"], encoding="utf-8", errors="replace") as f:
                holder = f.readline().strip()[:80]
        except Exception:
            holder = ""
        lock["holder"] = holder or None
    else:
        lock["status"] = "FREE"
        lock["holder"] = None

    tmp["open"] = _tmp_open_count(tmp["path"]) if tmp["exists"] else 0

    mtimes = [x["mtime"] for x in (phone_out, phone_in, board, lock, tmp) if x.get("mtime")]
    out = {
        "phone": {"cow_to_qa": phone_out, "qa_to_cow": phone_in},
        "board": board,
        "lock": lock,
        "tmp": tmp,
        "mtime": max(mtimes) if mtimes else 0,
        "seq": board_seq,
        "events": _packet_events(phone_out, phone_in, board, lock, tmp, board_seq),
    }
    return out


def burn(packet_paths=None):
    """Live burn-rate for both rails.

    The two rails are NOT the same kind of meter, and the dashboard should not pretend they are:
      GEM is FREE  -> the scarce resource is REQUESTS/day. Tokens are a volume stat.
      SGH is PAID  -> the scarce resource is DOLLARS/month. Tokens are what you are buying.
    So GEM reports pct-of-quota and SGH reports pct-of-budget, and each is labelled for what it is.
    """
    out = {"ts": int(time.time())}

    # ---- GEM: free tier, request-limited ----
    g = _read_json("gem_quota.json", {}) or {}
    try:
        import bts_gem
        rpd, poll_share = bts_gem.MAX_RPD, bts_gem.POLL_SHARE
    except Exception:
        rpd, poll_share = 1500, 0.20
    used = (g.get("WORK", 0) or 0) + (g.get("POLL", 0) or 0)
    out["gem"] = {
        "kind": "free", "unit": "req",
        "date": g.get("date"),
        "used": used, "cap": rpd,
        "pct": round(100.0 * used / rpd, 1) if rpd else 0.0,
        "work": g.get("WORK", 0), "poll": g.get("POLL", 0),
        "poll_cap": int(rpd * poll_share),
        "tok": g.get("tok", 0),
        "hist": (g.get("hist") or [])[-40:],
        "cost_usd": 0.0,
    }

    # ---- SGH: paid, dollar-limited ----
    s = _read_json("sgh_spend.json", {}) or {}
    try:
        import bts_sgh
        cap, pshare = bts_sgh.MONTHLY_BUDGET_USD, bts_sgh.POLL_SHARE
    except Exception:
        cap, pshare = 10.00, 0.20
    spent = (s.get("WORK", 0.0) or 0.0) + (s.get("POLL", 0.0) or 0.0)
    ti, to = s.get("tok_in", 0), s.get("tok_out", 0)
    out["sgh"] = {
        "kind": "paid", "unit": "usd",
        "month": s.get("month"),
        "spent": round(spent, 6), "cap": cap,
        "pct": round(100.0 * spent / cap, 2) if cap else 0.0,
        "left": round(max(0.0, cap - spent), 4),
        "calls": s.get("calls", 0),
        "tool_calls": s.get("tool_calls", 0),
        "tok_in": ti, "tok_out": to, "tok_reason": s.get("tok_reason", 0),
        "tok": ti + to,
        "poll_cap_usd": round(cap * pshare, 2),
        "hist": (s.get("hist") or [])[-40:],
        # cost per 1k tokens actually observed — the honest efficiency number
        "usd_per_ktok": round(spent / ((ti + to) / 1000.0), 4) if (ti + to) else None,
        "autoreload": True,   # $5 at a time -> the hard-stop is a safety device, say so
    }
    # Peer-file packets: phone / board / lock / tmp. Stat only — not a rail probe.
    out["packets"] = packets(packet_paths)
    return out


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def log_message(self, *a):
        pass                                   # quiet: this runs hidden via the .vbs

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        p = self.path.split("?")[0]
        q = self.path.split("?")[1] if "?" in self.path else ""

        if p == "/api/burn":
            return self._json(burn())

        if p == "/api/surfaces":
            try:
                import bts_surfaces
                return self._json(bts_surfaces.run())
            except Exception as e:
                return self._json({"ok": False, "error": str(e)[:200]}, 500)

        if p == "/api/policy":
            try:
                import bts_policy
                # ?bias=N  -> set the dial. No arg -> just read it.
                if "bias=" in q:
                    b = int(q.split("bias=")[1].split("&")[0])
                    return self._json(bts_policy.save(b))
                return self._json(bts_policy.resolve())
            except Exception as e:
                return self._json({"ok": False, "error": str(e)[:200]}, 500)

        if p == "/api/capacity":
            # THE <check> BUTTON (Keith, 2026-07-15). Measures every storage surface PER ACCOUNT.
            # Costs NOTHING and spends NOTHING — Drive about.get is free, the rest are folder walks.
            # So it is deliberately NOT rate-limited like /api/bench, which probes paid rails.
            # NOTE: reads token-refresh + walks trees, so it takes a few seconds. That is honest work,
            # not a hang.
            try:
                import bts_capacity
                return self._json(bts_capacity.check())
            except Exception as e:
                return self._json({"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:200])}, 500)

        if p == "/api/state":
            return self._json({"ok": True, "ts": int(time.time()), "port": PORT})

        if p == "/api/bench":
            free = "free=1" in q
            with _bench_lock:
                age = time.time() - _last_bench["ts"]
                # anti-spend-loop: serve the cached run if it is fresh
                if _last_bench["result"] and age < BENCH_MIN_INTERVAL:
                    r = dict(_last_bench["result"])
                    r["cached"] = True
                    r["cache_age_s"] = round(age, 1)
                    r["note"] = ("cached — <TEST> is rate-limited to 1 run per %ds so a "
                                 "held-down button cannot spend money in a loop"
                                 % BENCH_MIN_INTERVAL)
                    return self._json(r)
                try:
                    # <TEST> runs the REAL python probe AND rewrites dash.json, so the whole
                    # dashboard (rails + burn + surfaces) refreshes from one button press.
                    # This is Keith's ask: "make it run the python when I click Test".
                    import bts_snapshot
                    snap = bts_snapshot.run(with_bench=True, free_only=free)
                    r = snap.get("bench") or {"ok": False, "error": snap.get("bench_error")}
                    r["cached"] = False
                    r["snapshot_ts"] = snap["ts"]
                    _last_bench["ts"] = time.time()
                    _last_bench["result"] = r
                    return self._json(r)
                except Exception as e:
                    return self._json({"ok": False, "error": str(e)[:200]}, 500)

        return super().do_GET()


def _whos_on_port(port=PORT):
    """Returns "ours" | "foreign" | "free".

    *** BUG I INTRODUCED AND KEITH CAUGHT, 2026-07-12. ***
    The first version only asked "is ANYTHING listening on 8765?" and, if so, stood down —
    "idempotent". But the thing listening was the OLD `python -m http.server` from the previous
    launcher, which serves the page but has NO /api routes. So bts_serve politely deferred to a
    BROKEN server, and the symptoms were:
        * <TEST> -> "bts_serve.py is not answering"   (no /api/bench)
        * SIGNAL LOG stale                            (no snapshot refresh)
        * INTERNODES never appear                     (they come from /api/bench)
    Deferring to an unknown server is not idempotence, it is surrender. So now we ASK it who it is:
    only a server that answers /api/state is ours. Anything else gets reported, loudly, and the
    launcher kills it.
    """
    import socket, urllib.request, json as _json
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        if s.connect_ex(("127.0.0.1", port)) != 0:
            return "free"
    try:
        r = urllib.request.urlopen("http://127.0.0.1:%d/api/state" % port, timeout=1.5)
        d = _json.loads(r.read().decode())
        return "ours" if d.get("ok") and d.get("port") == port else "foreign"
    except Exception:
        return "foreign"          # something is there, but it cannot answer /api/state -> not us


def _selftest():
    """Throwaway dir. Proves packets shape, absent lock → FREE, board.seq + open, no rail import."""
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix="bts_burn_packets_")
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("  PASS " if cond else "  FAIL ") + name)
        if not cond:
            ok = False

    try:
        empty = {
            "phone_cow_to_qa": os.path.join(d, _PHONE_COW_TO_QA),
            "phone_qa_to_cow": os.path.join(d, _PHONE_QA_TO_COW),
            "board": os.path.join(d, _BOARD_NAME),
            "lock": os.path.join(d, "tree_lock"),
            "tmp": os.path.join(d, "tmp", "temp_files.toml"),
        }
        p0 = packets(empty)
        check("absent lock is FREE", p0["lock"]["status"] == "FREE" and not p0["lock"]["exists"])
        check("absent peers have no mtime", p0["mtime"] == 0 and p0["seq"] == 0)
        check("phone pair keys present",
              "cow_to_qa" in p0["phone"] and "qa_to_cow" in p0["phone"])

        with open(empty["phone_cow_to_qa"], "w", encoding="utf-8") as f:
            f.write("# cow -> qa\n")
        with open(empty["phone_qa_to_cow"], "w", encoding="utf-8") as f:
            f.write("# qa -> cow\n")
        with open(empty["board"], "w", encoding="utf-8") as f:
            json.dump({"seq": 7, "open": [{"id": 1}, {"id": 2, "status": "done"}]}, f)
        os.makedirs(os.path.dirname(empty["tmp"]), exist_ok=True)
        with open(empty["tmp"], "w", encoding="utf-8") as f:
            f.write("[[file]]\npath = \"a.tmp\"\n[[file]]\npath = \"b.tmp\"\nstatus = \"closed\"\n")
        with open(empty["lock"], "w", encoding="utf-8") as f:
            f.write("COWORK\n")

        p1 = packets(empty)
        check("phone mtime/size",
              p1["phone"]["cow_to_qa"]["exists"] and p1["phone"]["cow_to_qa"]["size"] > 0
              and p1["phone"]["qa_to_cow"]["exists"])
        check("board.seq", p1["board"]["seq"] == 7 and p1["seq"] == 7)
        check("board open count skips done", p1["board"]["open"] == 1)
        check("lock HELD + holder", p1["lock"]["status"] == "HELD" and p1["lock"]["holder"] == "COWORK")
        check("tmp open count", p1["tmp"]["open"] == 1)
        check("events for existing peers", len(p1["events"]) >= 4)
        check("fingerprint mtime advanced", p1["mtime"] > 0)

        b = burn(empty)
        check("burn carries packets", isinstance(b.get("packets"), dict) and b["packets"]["seq"] == 7)
        check("burn still has gem+sgh", "gem" in b and "sgh" in b)
        check("no rail_check in this module", "rail_check" not in sys.modules)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("SELFTEST %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    who = _whos_on_port()
    if who == "ours":
        print("bts_serve already running on %d — nothing to do." % PORT)
        raise SystemExit(0)
    if who == "foreign":
        print("!! PORT %d IS HELD BY A FOREIGN SERVER (almost certainly the old "
              "`python -m http.server`)." % PORT)
        print("!! It serves the page but has NO /api routes, so <TEST> cannot run the probe and")
        print("!! the snapshot never refreshes. KILL IT, then relaunch:")
        print("!!     taskkill /F /IM python.exe")
        print("!! (run_dash.bat and the Desktop launcher now do this for you.)")
        raise SystemExit(3)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)   # localhost ONLY — this process can spend
    print("BTS dashboard server -> http://127.0.0.1:%d/jack_command.html" % PORT)
    print("  /api/burn      live GEM + SGH burn rate + peer packets (phone/board/lock/tmp)")
    print("  /api/bench     real mesh <TEST> (add ?free=1 to spend nothing)")
    print("  /api/surfaces  ITC / GDX / ODX / local capacity")
    print("  /api/policy    SPEED<->COST dial (?bias=0..100)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
