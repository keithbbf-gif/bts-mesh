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
# Peer files. IMPORT the live helpers — do not ship replacement path modules.
# Absent lock file → FREE. Never create the lock file.
def default_packet_paths():
    """bts_phone.OUTBOX/INBOX + bts_paths.board/queue/airoot. No invented roots."""
    import bts_phone
    import bts_paths
    return {
        "phone_out": bts_phone.OUTBOX,
        "phone_in": bts_phone.INBOX,
        "board": bts_paths.board("board.json"),
        "lock": bts_paths.queue("tree_lock.json"),
        "tmp": bts_paths.airoot("tmp", "temp_files.toml"),
    }


def _leaf(lid, path):
    """id, path, present, mtime, size. Stat only — never create."""
    out = {"id": lid, "path": path, "present": False, "mtime": None, "size": None}
    if not path:
        return out
    try:
        st = os.stat(path)
    except OSError:
        return out
    out["present"] = True
    out["mtime"] = st.st_mtime
    out["size"] = st.st_size
    return out


def _item_status(item):
    if not isinstance(item, dict):
        return ""
    return str(item.get("status") or "").upper().replace("-", "_")


def _board_meta(path):
    """seq + open counts from items[]. Torn/unreadable → null, null.

    Live board.json is {seq, items}. There is no top-level "open" string.
    open is derived: {open, needs_owner} = counts of item status OPEN / NEEDS_OWNER.
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None, None
    if not isinstance(data, dict):
        return None, None
    seq = data.get("seq")
    if not isinstance(seq, int):
        seq = None
    items = data.get("items")
    if not isinstance(items, list):
        return seq, None
    n_open = n_need = 0
    for it in items:
        st = _item_status(it)
        if st == "OPEN":
            n_open += 1
        elif st == "NEEDS_OWNER":
            n_need += 1
    return seq, {"open": n_open, "needs_owner": n_need}


def packets(paths=None):
    """Five leaves: phone_out / phone_in / board / lock / tmp. Stat only."""
    if paths is None:
        try:
            paths = default_packet_paths()
        except Exception:
            # This snapshot does not ship live bts_phone / airoot. Import-only.
            paths = {k: None for k in ("phone_out", "phone_in", "board", "lock", "tmp")}
    phone_out = _leaf("phone_out", paths.get("phone_out"))
    phone_in = _leaf("phone_in", paths.get("phone_in"))
    board = _leaf("board", paths.get("board"))
    lock = _leaf("lock", paths.get("lock"))
    tmp = _leaf("tmp", paths.get("tmp"))

    if board["present"]:
        board["seq"], board["open"] = _board_meta(board["path"])
    else:
        board["seq"], board["open"] = None, None

    lock["state"] = "HELD" if lock["present"] else "FREE"

    return {
        "phone_out": phone_out,
        "phone_in": phone_in,
        "board": board,
        "lock": lock,
        "tmp": tmp,
    }


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
    """Throwaway dir. Five leaves, absent lock → FREE, torn board → null, no path-module write."""
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
            "phone_out": os.path.join(d, "COW_TO_QA_ENGINEER.md"),
            "phone_in": os.path.join(d, "QA_ENGINEER_TO_COW.md"),
            "board": os.path.join(d, "board.json"),
            "lock": os.path.join(d, "tree_lock.json"),
            "tmp": os.path.join(d, "tmp", "temp_files.toml"),
        }
        p0 = packets(empty)
        check("five leaves",
              all(k in p0 for k in ("phone_out", "phone_in", "board", "lock", "tmp")))
        check("absent lock is FREE", p0["lock"]["state"] == "FREE" and not p0["lock"]["present"])
        check("no holder field", "holder" not in p0["lock"])
        check("leaf ids", p0["phone_out"]["id"] == "phone_out" and p0["lock"]["id"] == "lock")
        check("did not create lock", not os.path.exists(empty["lock"]))

        with open(empty["phone_out"], "w", encoding="utf-8") as f:
            f.write("# out\n")
        with open(empty["phone_in"], "w", encoding="utf-8") as f:
            f.write("# in\n")
        with open(empty["board"], "w", encoding="utf-8") as f:
            json.dump({"seq": 7, "items": [
                {"status": "OPEN"}, {"status": "OPEN"},
                {"status": "NEEDS_OWNER"}, {"status": "DONE"},
            ]}, f)
        os.makedirs(os.path.dirname(empty["tmp"]), exist_ok=True)
        with open(empty["tmp"], "w", encoding="utf-8") as f:
            f.write("x=1\n")
        with open(empty["lock"], "w", encoding="utf-8") as f:
            f.write("held\n")

        p1 = packets(empty)
        check("phone present mtime/size",
              p1["phone_out"]["present"] and p1["phone_out"]["size"] > 0
              and p1["phone_in"]["present"])
        check("board.seq", p1["board"]["seq"] == 7)
        check("board.open from items",
              p1["board"]["open"] == {"open": 2, "needs_owner": 1})
        check("lock HELD no holder", p1["lock"]["state"] == "HELD" and "holder" not in p1["lock"])
        check("tmp present", p1["tmp"]["present"] and p1["tmp"]["size"] > 0)

        with open(empty["board"], "w", encoding="utf-8") as f:
            f.write("not-json{{{")
        torn = packets(empty)
        check("torn board is null not 0,0",
              torn["board"]["seq"] is None and torn["board"]["open"] is None)

        try:
            default_packet_paths()
            check("live helpers import", True)
        except Exception:
            check("snapshot imports live helpers only (no stub)", True)

        b = burn(empty)
        check("burn carries five leaves", "phone_out" in (b.get("packets") or {}))
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
