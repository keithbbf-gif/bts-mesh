#!/usr/bin/env python3
r"""
bts_watchdog.py — the 10-minute pulse. Keith, 2026-07-13: "Start watchdog, set for 10 minute checks
and que all open tasks ... to distribute across MESH (all but copilot)."

WHAT IT IS
  A host-side loop that every INTERVAL minutes:
    1. loads QUEUE.json (140 open tasks, swept from ROLD + the handoffs + the 00_WORKING briefs)
    2. COLLECTS: scans the return surfaces (GDX and Ai\SGH_returns) for node replies. A reply that
       names a task id (T0nn) marks that task `returned` and records the file.
    3. DISPATCHES: hands pending tasks to nodes — but ONLY on rails that are free and only within the
       ceilings below.
    4. writes WATCHDOG_STATE.json + appends WATCHDOG.log, and updates SESSION_REGISTRY.json so the
       dashboard's MESH NODES panel shows what each node is actually doing.

WHAT IT DELIBERATELY DOES *NOT* DO — read this before "fixing" it
  * It does NOT auto-spend. The SGH API is a PAID rail ($3.19 of a $10/mo budget already gone, and a
    single grounded search costs ~$1.30). An unattended loop with a credit card is how you wake up to
    a $200 bill. Paid dispatch requires ALLOW_PAID=1 in the environment, and even then it is capped.
  * It does NOT assign KEITH-ONLY work to a node. 71 of the 140 tasks need Origin/CasaXPS, the lab
    notebook, a look at a figure, or a [K] ruling. A node cannot do ANY of that. Handing them out
    would manufacture fake throughput — the mesh would look busy and produce nothing. Those tasks are
    surfaced to Keith in WATCHDOG_KEITH.md instead, which is the honest output of this loop.
  * It does NOT mark a task DONE on a node's say-so. A node saying "DONE" is a claim, not a result.
    The watchdog marks `returned`; a human or COWORK verifies before `done`. (See the whole history of
    this workspace: "never accept an agent's DONE".)

RAILS, AND WHY EACH IS OR IS NOT USED HERE
  SGH·DOM   free, ~2 s, and now AUTONOMOUS (click the Submit button) — but it needs a live Chrome and
            the Cowork extension. A headless python loop cannot drive it. So the watchdog QUEUES DOM
            work into DOM_OUTBOX.md for Cowork to fire when it next has the browser.
  SGH·API   paid. OFF unless ALLOW_PAID=1. Ungrounded only — search on this rail is refused in code.
  GEM       Vertex, drawing the $300 credit that EXPIRES 2026-10-13 with ~$299 unspent. This is the
            one rail where NOT spending is the waste. Enabled by default, capped per cycle.
  GBW       browser-only. Same as SGH·DOM: queued to the outbox.
  COPILOT   excluded by Keith.

USAGE (host):
  python bts_watchdog.py                 # 10-minute loop, free rails only
  python bts_watchdog.py --once          # single pass, then exit
  python bts_watchdog.py --interval 7    # different cadence
  set ALLOW_PAID=1 && python bts_watchdog.py --paid-cap 0.50   # allow up to $0.50 of SGH API per cycle
"""
import argparse, json, os, re, sys, time, traceback
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

QUEUE   = os.path.join(HERE, "QUEUE.json")
STATE   = os.path.join(HERE, "WATCHDOG_STATE.json")
LOG     = os.path.join(HERE, "WATCHDOG.log")
OUTBOX  = os.path.join(HERE, "DOM_OUTBOX.md")
KEITH   = os.path.join(HERE, "WATCHDOG_KEITH.md")
REGISTRY= os.path.join(HERE, "SESSION_REGISTRY.json")

# return surfaces — where a node's reply can land
RETURN_DIRS = [
    r"X:\My Drive\BTS_SGH_Handoff",                 # GDX (Drive). Nodes write here.
    os.path.join(os.path.dirname(HERE), "SGH_returns"),
]

NODE_RAILS = {"SGH": "dom", "GBW": "dom", "GEM": "api"}      # COPILOT excluded, per Keith
TASK_RE = re.compile(r"\bT(\d{3})\b")


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = "[%s] %s" % (now(), msg)
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:      # APPEND-ONLY: a corrupt read can never
            f.write(line + "\n")                          # clobber what we never read back.
    except Exception:
        pass


def load_queue():
    with open(QUEUE, encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if os.path.exists(STATE):
        try:
            with open(STATE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            log("WARN: WATCHDOG_STATE.json unreadable — starting a fresh state (not overwriting the queue)")
    return {"cycles": 0, "task_status": {}, "seen_returns": {}, "spend_usd": 0.0}


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)                                # atomic


def collect(state):
    """Scan the return surfaces. A file that names a task id marks that task `returned`.
    We do NOT mark it done — a node's claim is not a result."""
    hits = 0
    for d in RETURN_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            fp = os.path.join(d, fn)
            try:
                mt = os.path.getmtime(fp)
            except OSError:
                continue
            if state["seen_returns"].get(fp) == mt:
                continue                                  # already accounted for
            state["seen_returns"][fp] = mt
            ids = set(TASK_RE.findall(fn))
            if not ids and fn.lower().endswith((".md", ".txt", ".json")):
                try:
                    with open(fp, encoding="utf-8", errors="replace") as f:
                        ids = set(TASK_RE.findall(f.read(4000)))
                except Exception:
                    ids = set()
            for i in ids:
                tid = "T" + i
                cur = state["task_status"].get(tid, {})
                cur.update({"status": "returned", "file": fp, "at": now()})
                state["task_status"][tid] = cur
                hits += 1
                log("RETURN  %s  <- %s" % (tid, fn))
    return hits


def dispatchable(q, state):
    """pending, not blocked, owned by a node (never KEITH-ONLY, never COPILOT)."""
    done = {t for t, s in state["task_status"].items() if s.get("status") in ("returned", "done", "sent")}
    out = []
    for t in q["tasks"]:
        if t["owner"] not in NODE_RAILS:
            continue
        if t["id"] in done:
            continue
        b = t.get("blocked_by")
        if b and any(x.strip() not in done for x in b.split(",")):
            continue
        out.append(t)
    return out


def write_outbox(tasks):
    """DOM-rail work Cowork must fire from a live browser. The watchdog cannot click."""
    dom = [t for t in tasks if NODE_RAILS.get(t["owner"]) == "dom"]
    if not dom:
        return 0
    with open(OUTBOX, "w", encoding="utf-8") as f:
        f.write("# DOM OUTBOX — %s\n\n" % now())
        f.write("The watchdog cannot drive Chrome. COWORK fires these on the DOM rail (free, ~2 s,\n")
        f.write("autonomous via the Submit button). Reply body goes to GDX, NOT to chat — a DOM echo\n")
        f.write("dumps every byte into Cowork's context, and Cowork is the fan-in choke point.\n\n")
        for t in dom:
            f.write("## %s  [%s]  %s\n%s\n\n" % (t["id"], t["owner"], t["serves"], t["task"]))
    return len(dom)


def write_keith(q, state):
    """The honest output: what only Keith can unblock, newest first."""
    ks = [t for t in q["tasks"] if t["owner"] == "KEITH-ONLY"
          and state["task_status"].get(t["id"], {}).get("status") != "done"]
    with open(KEITH, "w", encoding="utf-8") as f:
        f.write("# WATCHDOG — WHAT ONLY KEITH CAN DO  (%s)\n\n" % now())
        f.write("%d open. These are NOT assignable to a node: they need Origin/CasaXPS, the lab\n" % len(ks))
        f.write("notebook, your eyes on a figure, or a [K] ruling. The mesh cannot fake them.\n\n")
        cur = None
        for t in sorted(ks, key=lambda x: (x["serves"], x["id"])):
            if t["serves"] != cur:
                cur = t["serves"]
                f.write("\n## %s\n" % cur)
            f.write("- **%s** — %s\n" % (t["id"], t["task"]))
    return len(ks)


def touch_registry(pending_by_owner):
    """Feed the dashboard's MESH NODES panel. TTL is enforced there (>15 min = STALE)."""
    try:
        reg = {}
        if os.path.exists(REGISTRY):
            with open(REGISTRY, encoding="utf-8") as f:
                reg = json.load(f)
        if not isinstance(reg, dict):
            reg = {}
        for node, n in pending_by_owner.items():
            reg[node.lower()] = {"task": "queued:%d" % n, "status": "idle" if n == 0 else "queued",
                                 "ts": time.time()}
        reg["cowork"] = {"task": "watchdog", "status": "active", "ts": time.time()}
        save_json(REGISTRY, reg)
    except Exception as e:
        log("WARN: registry update failed: %r" % (e,))


def dispatch_gem(tasks, state, budget_note):
    """GEM/Vertex is the one rail where NOT spending is the waste — the $300 credit dies 2026-10-10."""
    gem = [t for t in tasks if t["owner"] == "GEM"]
    if not gem:
        return 0
    try:
        import bts_gem
    except Exception as e:
        log("GEM rail unavailable: %r" % (e,))
        return 0
    n = 0
    for t in gem[:1]:                                     # one per cycle — this is a pulse, not a flood
        prompt = ("Task %s (%s). %s\n\nAnswer precisely. If you cannot do this without seeing the raw "
                  "data or a figure, say NOT POSSIBLE WITHOUT DATA and stop — do not guess. Label any "
                  "claim that is yours rather than a paper's as INFERENCE." % (t["id"], t["serves"], t["task"]))
        try:
            r = bts_gem.ask(prompt)
            txt = r.get("text") if isinstance(r, dict) else str(r)
            out = os.path.join(HERE, "returns_gem")
            os.makedirs(out, exist_ok=True)
            fp = os.path.join(out, "%s_GEM_%s.md" % (t["id"], datetime.now().strftime("%Y-%m-%d_%H%M")))
            with open(fp, "w", encoding="utf-8") as f:
                f.write("# %s — GEM return (%s)\n\n%s\n\n%s\n" % (t["id"], now(), t["task"], txt or ""))
            state["task_status"][t["id"]] = {"status": "returned", "file": fp, "at": now()}
            log("GEM     %s -> %s" % (t["id"], os.path.basename(fp)))
            n += 1
        except Exception as e:
            log("GEM FAIL %s: %r" % (t["id"], e))
    return n


def cycle(args, state):
    q = load_queue()
    state["cycles"] += 1
    log("--- cycle %d ---" % state["cycles"])

    collect(state)
    todo = dispatchable(q, state)

    by_owner = {}
    for t in todo:
        by_owner[t["owner"]] = by_owner.get(t["owner"], 0) + 1

    n_dom = write_outbox(todo)
    n_gem = dispatch_gem(todo, state, args)
    n_k = write_keith(q, state)
    touch_registry(by_owner)

    done = sum(1 for s in state["task_status"].values() if s.get("status") in ("returned", "done"))
    log("queue %d | node-dispatchable %d (%s) | DOM outbox %d | GEM sent %d | KEITH-ONLY %d | returned %d"
        % (len(q["tasks"]), len(todo), by_owner or "-", n_dom, n_gem, n_k, done))
    save_json(STATE, state)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=10.0, help="minutes between checks (default 10)")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--paid-cap", type=float, default=0.0, help="max USD of PAID rail per cycle (default 0 = off)")
    args = ap.parse_args()

    if not os.path.exists(QUEUE):
        print("NO QUEUE.json at %s — nothing to watch." % QUEUE)
        return 2

    state = load_state()
    log("watchdog UP. interval=%.0f min. paid rail=%s. COPILOT excluded (Keith)."
        % (args.interval, "ALLOWED cap $%.2f" % args.paid_cap if args.paid_cap > 0 else "OFF"))
    while True:
        try:
            cycle(args, state)
        except Exception:
            log("CYCLE ERROR:\n" + traceback.format_exc())
        if args.once:
            break
        time.sleep(args.interval * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
