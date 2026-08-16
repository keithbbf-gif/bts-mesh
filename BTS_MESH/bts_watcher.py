"""
bts_watcher.py — event-driven watcher on a ROLD dir (the SGH_returns bus dir).
Fires a callback the instant a signal file lands, instead of the 10-min poll.
Uses the `watchdog` library if installed; otherwise falls back to a lightweight
mtime poll so it runs anywhere Python does.

watch(dirpath, on_change, interval=2.0, stop_event=None, timeout=None, once=False)
  on_change(path, event_type) is called for each create/modify.
  stop_event : threading.Event to stop cleanly.
  timeout    : max seconds to run (None = forever).
  once       : return as soon as the FIRST change is delivered.
Returns the backend used: "watchdog" or "poll".
"""
from __future__ import annotations
import os, time

def _expired(deadline):
    return deadline is not None and time.time() >= deadline

def watch(dirpath, on_change, interval=2.0, stop_event=None, timeout=None, once=False):
    os.makedirs(dirpath, exist_ok=True)
    deadline = (time.time() + timeout) if timeout else None
    delivered = {"n": 0}
    def deliver(path, ev):
        on_change(path, ev); delivered["n"] += 1

    try:
        from watchdog.observers import Observer               # type: ignore
        from watchdog.events import FileSystemEventHandler    # type: ignore
        class H(FileSystemEventHandler):
            def on_any_event(self, e):
                if not e.is_directory and e.event_type in ("created", "modified", "moved"):
                    deliver(getattr(e, "dest_path", None) or e.src_path, e.event_type)
        obs = Observer(); obs.schedule(H(), dirpath, recursive=False); obs.start()
        try:
            while True:
                if stop_event is not None and stop_event.is_set(): break
                if _expired(deadline): break
                if once and delivered["n"]: break
                time.sleep(min(interval, 0.2))
        finally:
            obs.stop(); obs.join()
        return "watchdog"
    except Exception:
        def snapshot():
            out = {}
            for fn in os.listdir(dirpath):
                fp = os.path.join(dirpath, fn)
                try: out[fp] = os.path.getmtime(fp)
                except OSError: pass
            return out
        seen = snapshot()
        while True:
            if stop_event is not None and stop_event.is_set(): break
            if _expired(deadline): break
            time.sleep(interval)
            cur = snapshot()
            for fp, m in cur.items():
                if fp not in seen or seen[fp] != m:
                    deliver(fp, "created" if fp not in seen else "modified")
            seen = cur
            if once and delivered["n"]: break
        return "poll"
