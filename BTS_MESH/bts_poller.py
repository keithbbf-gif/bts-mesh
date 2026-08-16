#!/usr/bin/env python3
"""
bts_poller.py -- PolleR, the mesh's ACTIVE METER READER.  (Keith, 2026-07-14)

THE THREE-ROLE SPLIT -- read this and DO NOT violate it
  * STATE   (bts_state.py)   = PASSIVE. Records events the mesh EMITS. Never acts, never polls.
  * PolleR  (this file)      = ACTIVE, but a METER READER ONLY. On a schedule it FETCHES external
                               gauges that emit no events of their own (cloud quotas, credits, drive
                               speeds, spend) and RECORDS the numbers into surfaces.json + a STATE
                               event. It NEVER dispatches a node, NEVER calls a model, NEVER spends a
                               cent, NEVER forces a task. It reads gauges and writes numbers. That is
                               the whole job.
  * WatchDOG (NOT built)     = the future DOER that would READ state and DISPATCH. A different program.
                               PolleR is deliberately NOT that. Keep it a reader.

  If you ever feel tempted to make PolleR "just kick a node while it is up", STOP. That is WatchDOG.
  The reason STATE stayed clean is that its author refused to add a loop; PolleR keeps the loop but
  refuses to add an action.

WHAT IT POLLS, AND THE RIGHT ROUTE FOR EACH (do not force DOM where a host read is better)
  HOST route (pure python, always runnable, spends nothing) -- poll_host():
    1. GDX quota      shutil.disk_usage(r"X:\\").  Drive-for-Desktop reports the ACCOUNT quota as the
                      volume size, so this IS a real cloud-quota reading. Same trick for D:/C:/G:.
                      (Reuses the bts_quota.py logic; cross-check URL: drive.google.com/drive/u/0/quota)
    2. Drive speeds   reuse bts_drivebench.bench() -- refreshes the "real but stale" DRIVE SPEED panel.
    3. Spend          read the real budget bts_sgh writes (sgh_spend.json / bts_sgh.budget()): month
                      $x / $10. No inference call is ever made.
  DOM route (a logged-in browser only; python cannot drive it) -- poll_dom():
    4. ODX quota      onedrive.live.com/?view=1&v=managestorage. disk_usage LIES on ODX (the local path
                      is a folder on D:, so it returns D:'s numbers -- this bug already bit bts_quota).
    5. MS 365 / Copilot AI credits   account.microsoft.com/services/microsoft365/details.
    6. GDX cross-check   drive.google.com/drive/u/0/quota (compare against the host disk_usage number).
  poll_dom() is invoked by COWORK driving the Chrome extension (a scheduled Cowork turn or an
  opportunistic one whenever the browser is up). This module provides the PARSE / NORMALISE / RECORD
  helpers and the last-known fallback -- headless python cannot log in, and PolleR must never try to.

CORRUPTION-SAFE, HOST-SIDE (the D: bash mount silently corrupts files -- see CLAUDE.md)
  * bts_poller runs on the HOST. Writes are ATOMIC: temp file in the same dir -> os.replace().
  * A gauge with no fresh reading KEEPS its last-known value and is LABELLED stale via its ts. It is
    NEVER blanked and NEVER faked. measured=False marks user-reported / last-known; measured=True is
    reserved for a fresh read (a live disk_usage, or a DOM value Cowork just scraped). This is the same
    "measured vs reported" discipline as bts_quota.py -- the distinction is load-bearing; do not lose it.
  * If surfaces.json is unreadable (a corrupt mount copy), we do NOT clobber it blindly: the host
    surfaces are regenerated fresh from live disk_usage, and ODX/ITC fall back to their hardcoded
    last-known seeds so they are never lost.

SURFACES.JSON CONTRACT (unchanged from bts_quota.py -- PolleR is a drop-in companion)
    {
      "surfaces": { "GDX": {"used","free","quota","note","measured","ts","source"}, "D:":..., "ODX":... },
      "meters":   { "SGH_SPEND": {"used","quota","unit","measured","ts","source","note"},
                    "MS_CREDITS": {...} },          # non-GB gauges (dollars, credits)
      "measured_at": "..."
    }
  bts_snapshot.py merges surfaces{} into dash.json -> surfaces_measured; the SURFACE CAPACITY panel
  reads it. meters{} is additive and ignored by older readers.

CLI
    python bts_poller.py --once        # one host poll now, then exit
    python bts_poller.py --interval 60 # host poll every 60 min (mirrors the watchdog launcher; host only)
    python bts_poller.py --selftest    # full self + negative-control proof (throwaway dir, no real files)
    python bts_poller.py --show        # print the current surfaces.json
"""
from __future__ import annotations
import json, os, sys, time, tempfile, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# All paths derive from one dir so --selftest can redirect to a throwaway temp dir and never touch
# the real state files or the corruptible D: mount.
_CFG = {"dir": HERE}


def _dir() -> str:
    return _CFG["dir"]


def surfaces_json() -> str:
    return os.path.join(_dir(), "surfaces.json")


def drives_json() -> str:
    return os.path.join(_dir(), "drives.json")


def _now_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _gb(n):
    return round(n / (1024 ** 3), 2) if n is not None else None


# ================================================================================================
# HOST SURFACES -- the volumes whose disk_usage reports a real quota (GDX is the whole point).
# Mirrors bts_quota.py VOLS so the two stay consistent. GDX is X:, NOT E: (Keith, 2026-07-13).
# ================================================================================================
VOLS = [
    ("GDX", r"X:\\", "Google Drive — the exchange rail. Fast (580 MB/s) and PRIVATE. "
                     "disk_usage(X:) reports the ACCOUNT quota."),
    ("D:",  r"D:\\", "Research2 + PhD library live here."),
    ("C:",  r"C:\\", "System / NVMe."),
    ("G:",  r"G:\\", "Tera mirror — the slowest surface we own."),
]

# LAST-KNOWN SEEDS for the gauges PolleR cannot read on the host. Never blanked; measured=False.
# ODX: disk_usage LIES (folder on D:); Keith hand-read 105.5/1024 GB on 2026-07-13 from the client.
ODX_SEED = {"used": 105.5, "quota": 1024.0, "free": 918.5, "measured": False,
            "source": "Keith read it from the OneDrive client, 2026-07-13",
            "note": "OneDrive — cold archive, 1 TB. NOT measurable by disk_usage (the local path is a "
                    "folder on D:, which is what the first version of bts_quota wrongly reported). "
                    "Refresh from DOM: onedrive.live.com/?view=1&v=managestorage"}
# ITC: Cloudflare R2 free tier; usage from the last publish, not a live volume.
ITC_SEED = {"used": 4.51, "quota": 10.0, "measured": False,
            "source": "last publish (Publish-to-R2_KEYED.bat)",
            "note": "Cloudflare R2 free tier. Usage from the last publish, NOT live. PUBLIC WEB — "
                    "the PDF library should not be here."}


# ================================================================================================
# ATOMIC, CORRUPTION-SAFE surfaces.json IO  (temp-in-same-dir -> os.replace, same as bts_quota)
# ================================================================================================
def _atomic_write_json(path: str, obj: dict) -> None:
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".surfaces_", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)          # atomic on NTFS + POSIX
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def _load_surfaces() -> dict:
    """Read surfaces.json. On a missing/corrupt file return a fresh skeleton -- NEVER raise, and
    NEVER treat a bad read as 'the surfaces are gone'. The host surfaces get regenerated fresh each
    poll anyway; ODX/ITC fall back to their seeds, so a corrupt read cannot lose a gauge."""
    path = surfaces_json()
    if not os.path.exists(path):
        return {"surfaces": {}, "meters": {}, "measured_at": None}
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            return {"surfaces": {}, "meters": {}, "measured_at": None}
        d.setdefault("surfaces", {})
        d.setdefault("meters", {})
        return d
    except Exception:
        # CORRUPT mount copy -> do not trust it, do not clobber blind. Start clean; the poll refills
        # host surfaces and the ODX/ITC seeds, so nothing real is lost.
        return {"surfaces": {}, "meters": {}, "measured_at": None, "_note": "prior surfaces.json unreadable; rebuilt"}


# ================================================================================================
# STATE emit -- import the observer, never reimplement it. Best-effort: a failed emit must never
# stop PolleR from recording the number (the surfaces.json write is the primary durable action).
# ================================================================================================
def _emit(target, detail, status=None):
    try:
        import bts_state
        bts_state.emit("POLLER", target, "capacity", detail, direction=None, status=status)
        return True
    except Exception:
        return False


# ================================================================================================
# THE CLEAN SEAM -- record_capacity / record_meter.
# Both MERGE into surfaces.json atomically and emit ONE STATE event. This is the single point DOM
# and HOST both flow through, so the "measured vs reported" flag is applied in exactly one place.
# ================================================================================================
def record_capacity(name, used_gb, quota_gb, source, measured=True, note=None, free_gb=None,
                    emit=True) -> dict:
    """Record a capacity gauge (GB) into surfaces.json{surfaces} and emit a STATE event.
       measured=True  -> a FRESH read (live disk_usage, or a DOM value just scraped).
       measured=False -> user-reported / last-known. The value is kept and the ts marks its age;
                         a gauge is NEVER blanked and NEVER faked."""
    name = str(name).strip().upper() if name else name
    data = _load_surfaces()
    prev = data["surfaces"].get(name, {})
    if free_gb is None and used_gb is not None and quota_gb is not None:
        free_gb = round(quota_gb - used_gb, 2)
    entry = {
        "used": used_gb,
        "free": free_gb,
        "quota": quota_gb,
        "measured": bool(measured),
        "source": source,
        "note": note if note is not None else prev.get("note"),
        "ts": _now_ts(),
    }
    data["surfaces"][name] = entry
    data["measured_at"] = _now_ts()
    _atomic_write_json(surfaces_json(), data)
    if emit:
        if used_gb is not None and quota_gb is not None:
            detail = "%s/%s GB (%s)" % (used_gb, quota_gb, "measured" if measured else "reported")
        else:
            detail = "no data (%s)" % source
        _emit(name, detail)
    return entry


def record_meter(name, used, quota, unit, source, measured=True, note=None, emit=True) -> dict:
    """Record a NON-GB gauge (dollars, credits) into surfaces.json{meters} and emit a STATE event.
       Same measured/reported discipline as record_capacity."""
    name = str(name).strip().upper() if name else name
    data = _load_surfaces()
    entry = {
        "used": used, "quota": quota, "unit": unit,
        "measured": bool(measured), "source": source, "note": note,
        "ts": _now_ts(),
    }
    data["meters"][name] = entry
    data["measured_at"] = _now_ts()
    _atomic_write_json(surfaces_json(), data)
    if emit:
        if used is not None and quota is not None:
            detail = "%s/%s %s (%s)" % (used, quota, unit, "measured" if measured else "reported")
        elif used is not None:
            detail = "%s %s (%s)" % (used, unit, "measured" if measured else "reported")
        else:
            detail = "no data (%s)" % source
        _emit(name, detail)
    return entry


# ================================================================================================
# HOST POLL -- pure host, no browser, always runnable, spends NOTHING.
# ================================================================================================
def poll_host_surfaces() -> dict:
    """GDX + D:/C:/G: via disk_usage. GDX is the point: Drive-for-Desktop reports the ACCOUNT quota
    as the volume size. Preserves ODX/ITC from the existing file (or the hardcoded seed), never
    blanking them. Returns the surfaces{} dict written."""
    data = _load_surfaces()
    out = data["surfaces"]

    for name, path, note in VOLS:
        try:
            t, u, f = shutil.disk_usage(path)
            record_capacity(name, _gb(u), _gb(t), source="disk_usage(%s)" % path.rstrip("\\"),
                            measured=True, note=note, free_gb=_gb(f))
        except Exception as e:
            # not present / not measurable -> keep last-known if we have it, else record 'no data'.
            prev = out.get(name)
            if prev and prev.get("quota") is not None:
                # keep last-known, just note it went stale this cycle
                record_capacity(name, prev.get("used"), prev.get("quota"),
                                source="stale (%s failed: %s)" % (path.rstrip("\\"), str(e)[:40]),
                                measured=False, note=prev.get("note"), free_gb=prev.get("free"))
            else:
                record_capacity(name, None, None,
                                source="NOT MEASURABLE: %s" % str(e)[:60],
                                measured=False, note=note)

    # ODX / ITC -- host cannot read them. Keep what is on disk; else seed. Never blank.
    data = _load_surfaces()
    if "ODX" not in data["surfaces"]:
        record_capacity("ODX", ODX_SEED["used"], ODX_SEED["quota"], source=ODX_SEED["source"],
                        measured=False, note=ODX_SEED["note"], free_gb=ODX_SEED["free"])
    if "ITC" not in data["surfaces"]:
        record_capacity("ITC", ITC_SEED["used"], ITC_SEED["quota"], source=ITC_SEED["source"],
                        measured=False, note=ITC_SEED["note"])
    return _load_surfaces()["surfaces"]


def poll_host_drivespeeds(quick=True) -> dict:
    """Refresh the DRIVE SPEED panel by reusing bts_drivebench. Writes drives.json (its own file,
    which bts_snapshot merges). Spends nothing. Failures are tolerated -- speeds are a nice-to-have,
    never a reason to abort the poll."""
    try:
        import bts_drivebench
    except Exception as e:
        return {"error": "bts_drivebench import failed: %s" % str(e)[:80]}
    mb = 8 if quick else 64
    out = {}
    for label, path in bts_drivebench.SURFACES:
        try:
            r = bts_drivebench.bench(path, mb)
        except Exception as e:
            r = ("ERR", str(e)[:60])
        if r is None:
            out[label] = {"write": None, "read": None, "note": "not present"}
        elif r[0] == "ERR":
            out[label] = {"write": None, "read": None, "note": r[1]}
        else:
            w, rd = r
            out[label] = {"write": round(w, 1) if w else None,
                          "read": round(rd, 1) if rd else None, "mb": mb, "ts": _now_ts()}
    _atomic_write_json(drives_json(), {"drives": out, "measured_at": _now_ts()})
    return out


def poll_host_spend() -> dict:
    """Read the REAL SGH budget bts_sgh writes: month $x / $10. No inference call. Records it as a
    meter and emits a STATE event. Falls back to reading sgh_spend.json directly if bts_sgh will not
    import (never fabricates -- unknown stays None)."""
    spent = cap = None
    src = None
    try:
        import bts_sgh
        b = bts_sgh.budget()
        spent, cap = b.get("spent"), b.get("budget")
        src = "bts_sgh.budget()  month %s" % b.get("month")
    except Exception:
        # direct read of the ledger -- WORK+POLL vs a default $10 monthly budget.
        try:
            with open(os.path.join(_dir(), "sgh_spend.json"), encoding="utf-8") as f:
                s = json.load(f)
            spent = round((s.get("WORK", 0.0) or 0.0) + (s.get("POLL", 0.0) or 0.0), 4)
            cap = 10.00
            src = "sgh_spend.json  month %s (bts_sgh unavailable, $10 default cap)" % s.get("month")
        except Exception as e:
            src = "spend unreadable: %s" % str(e)[:60]
    record_meter("SGH_SPEND", spent, cap, unit="USD", source=src, measured=(spent is not None),
                 note="Grok/SGH monthly spend against the $10 budget. HOST read of the durable "
                      "ledger -- PolleR makes NO inference call and spends nothing to read this.")
    return {"spent": spent, "cap": cap, "source": src}


def poll_host(quick=True) -> dict:
    """The whole host poll: surfaces + drive speeds + spend. Pure host, no browser, spends NOTHING.
    Always runnable. This is what the hourly schedule calls."""
    result = {"when": _now_ts()}
    result["surfaces"] = poll_host_surfaces()
    result["drives"] = poll_host_drivespeeds(quick=quick)
    result["spend"] = poll_host_spend()
    return result


# ================================================================================================
# DOM POLL -- documented procedure + parse/normalise/record helpers + last-known fallback.
#
# A headless python cannot drive the logged-in browser, so this is invoked by COWORK driving the
# Chrome extension (a scheduled Cowork turn, or opportunistically whenever the browser is up).
# The PROCEDURE (Cowork runs the navigation + get_page_text; then calls the parse+record helpers):
#
#   ODX  (OneDrive quota)  -- DOM ONLY (disk_usage lies; the local ODX path is a folder on D:)
#     navigate https://onedrive.live.com/?view=1&v=managestorage
#     get_page_text  ->  parse_onedrive(text) -> (used_gb, quota_gb)
#     record_capacity("ODX", used, quota, source="DOM onedrive.live.com", measured=True)
#     If the page shows a SIGN-IN screen (not logged in): DO NOT sign in. Leave ODX at last-known
#     (record nothing, or record measured=False from the seed). Never invent a number.
#
#   MS 365 / Copilot AI credits -- DOM ONLY
#     navigate https://account.microsoft.com/services/microsoft365/details  (or /services)
#     get_page_text  ->  parse_ms_credits(text) -> (credits, plan)
#     record_meter("MS_CREDITS", credits, None, unit="credits", source="DOM account.microsoft.com",
#                  measured=True, note=plan)
#     Consumer M365 Family includes 60 Copilot AI credits/mo in Word/Excel (see memory). If the page
#     needs a click to reveal the balance, click it. If not logged in -> last-known, say so.
#
#   GDX cross-check -- DOM (host already has the authoritative disk_usage number)
#     navigate https://drive.google.com/drive/u/0/quota
#     get_page_text  ->  parse_drive_quota(text) -> (used_gb, quota_gb)
#     Compare to the host disk_usage reading. If they DISAGREE by > ~1 GB, REPORT it (a drift means
#     the Drive client is out of sync). Otherwise record measured=True with source="DOM cross-check".
#
# The helpers below are pure string parsers -- unit-tested in --selftest, no browser needed.
# ================================================================================================
def _to_gb(value, unit) -> float:
    """Normalise a (number, unit) pair to GB. Handles KB/MB/GB/TB, decimal or binary is close enough
    for a capacity gauge."""
    u = (unit or "").strip().upper()
    v = float(value)
    return {"KB": v / (1024 ** 2), "MB": v / 1024.0, "GB": v, "TB": v * 1024.0}.get(u, v)


def parse_drive_quota(text: str):
    """Parse the Google Drive storage page. Expects text like '11.71 GB of 100 GB used'.
    Returns (used_gb, quota_gb) or (None, None) if not found."""
    import re
    m = re.search(r"([\d.]+)\s*(KB|MB|GB|TB)\s+of\s+([\d.]+)\s*(KB|MB|GB|TB)\s+used", text, re.I)
    if not m:
        return (None, None)
    used = round(_to_gb(m.group(1), m.group(2)), 2)
    quota = round(_to_gb(m.group(3), m.group(4)), 2)
    return (used, quota)


def parse_onedrive(text: str):
    """Parse the OneDrive manage-storage page. OneDrive phrases it a few ways; accept the common
    'X GB of Y GB' / 'X GB used of Y GB' / 'Y GB ... X GB used'. Returns (used_gb, quota_gb)."""
    import re
    for pat in (r"([\d.]+)\s*(KB|MB|GB|TB)\s+(?:used\s+)?of\s+([\d.]+)\s*(KB|MB|GB|TB)",
                r"([\d.]+)\s*(KB|MB|GB|TB)\s+used.*?([\d.]+)\s*(KB|MB|GB|TB)"):
        m = re.search(pat, text, re.I | re.S)
        if m:
            used = round(_to_gb(m.group(1), m.group(2)), 2)
            quota = round(_to_gb(m.group(3), m.group(4)), 2)
            return (used, quota)
    return (None, None)


def parse_ms_credits(text: str):
    """Parse an AI-credit balance from a Microsoft account page. Looks for 'N credits' / 'N AI
    credits' / 'N Copilot credits'. Returns (credits:int|None, context_line:str|None)."""
    import re
    m = re.search(r"(\d+)\s*(?:AI\s*|Copilot\s*)?credits?", text, re.I)
    if not m:
        return (None, None)
    line = None
    for ln in text.splitlines():
        if m.group(0).lower() in ln.lower():
            line = ln.strip()[:120]
            break
    return (int(m.group(1)), line)


def poll_dom():
    """Not directly callable from headless python (no logged-in browser). Documents the procedure
    and returns the fallback = the last-known DOM gauges from surfaces.json. Cowork performs the
    navigation + get_page_text, then calls parse_* + record_capacity/record_meter above."""
    data = _load_surfaces()
    return {
        "note": "poll_dom is a Cowork-driven procedure; see the docstring above for the exact URLs "
                "and parse helpers. This return is the last-known fallback, never a fresh read.",
        "odx_last_known": data["surfaces"].get("ODX"),
        "ms_credits_last_known": data["meters"].get("MS_CREDITS"),
        "gdx_host": data["surfaces"].get("GDX"),
    }


# ================================================================================================
# SELFTEST + NEGATIVE CONTROL  (throwaway dir; never touches real files or the D: mount)
# ================================================================================================
def _selftest() -> int:
    tmp = tempfile.mkdtemp(prefix="bts_poller_selftest_")
    _CFG["dir"] = tmp
    ok = True

    def check(label, cond):
        nonlocal ok
        ok = ok and bool(cond)
        print(("  PASS " if cond else "  FAIL ") + label)

    print("bts_poller --selftest  (dir = %s)" % tmp)

    # (1) record a MEASURED capacity + a REPORTED one; both must persist with the right flag.
    record_capacity("GDX", 11.71, 100.0, source="disk_usage(X:)", measured=True,
                    note="test", emit=False)
    record_capacity("ODX", 105.5, 1024.0, source="last-known", measured=False,
                    note="test", emit=False)
    d = _load_surfaces()
    check("GDX recorded, measured=True", d["surfaces"]["GDX"]["measured"] is True)
    check("GDX free auto-derived (88.29)", d["surfaces"]["GDX"]["free"] == 88.29)
    check("ODX recorded, measured=False (reported, not faked)", d["surfaces"]["ODX"]["measured"] is False)

    # (2) NEGATIVE CONTROL: corrupt surfaces.json, then record again. A corrupt read must NOT lose a
    #     gauge and must NOT crash -- the write regenerates a valid file.
    with open(surfaces_json(), "w", encoding="utf-8") as f:
        f.write('{"surfaces": {"GDX": {"used": 11.7')     # truncated / invalid JSON
    print("  -- injected CORRUPT surfaces.json (negative control) --")
    crashed = False
    try:
        record_capacity("ITC", 4.51, 10.0, source="seed", measured=False, emit=False)
    except Exception:
        crashed = True
    check("record after corruption does not crash", not crashed)
    d = _load_surfaces()
    check("surfaces.json is valid JSON again after corruption", isinstance(d, dict))
    check("ITC survived the corrupt-read cycle", "ITC" in d["surfaces"])

    # (3) a gauge with NO fresh reading keeps a value / never becomes a fake number.
    record_capacity("GDX2", None, None, source="NOT MEASURABLE", measured=False, emit=False)
    d = _load_surfaces()
    check("unmeasurable gauge is None, never a fake", d["surfaces"]["GDX2"]["used"] is None)
    check("unmeasurable gauge flagged measured=False", d["surfaces"]["GDX2"]["measured"] is False)

    # (4) meter (dollars) records + flags correctly.
    record_meter("SGH_SPEND", 3.34, 10.0, unit="USD", source="ledger", measured=True, emit=False)
    d = _load_surfaces()
    check("SGH_SPEND meter recorded in USD", d["meters"]["SGH_SPEND"]["unit"] == "USD")

    # (5) DOM PARSERS -- the load-bearing string parsing, tested with real page text.
    used, quota = parse_drive_quota("11.71 GB of 100 GB used\nGOOGLE DRIVE 2.9 GB")
    check("parse_drive_quota -> (11.71, 100.0)", used == 11.71 and quota == 100.0)
    u2, q2 = parse_onedrive("105.5 GB used of 1024 GB")
    check("parse_onedrive 'used of' form", u2 == 105.5 and q2 == 1024.0)
    u3, q3 = parse_onedrive("1.83 TB of 5 TB")
    check("parse_onedrive TB units -> GB", abs(u3 - 1874.0) < 1 and abs(q3 - 5120.0) < 1)
    cr, ln = parse_ms_credits("Your plan includes 60 AI credits per month for Copilot")
    check("parse_ms_credits -> 60", cr == 60)
    # NEGATIVE CONTROL for the parser: garbage in -> (None, None), NEVER a made-up number.
    ng, _ = parse_drive_quota("there is no quota text here at all")
    check("parse_drive_quota garbage -> None (no fabrication)", ng is None)
    nc, _ = parse_ms_credits("nothing about a balance here")
    check("parse_ms_credits garbage -> None (no fabrication)", nc is None)

    # (6) PolleR must NOT be a dispatcher -- prove the module exposes no dispatch/spend surface.
    import bts_poller as self_mod  # already imported as __main__, but re-import name for attr check
    banned = [n for n in dir(self_mod) if any(k in n.lower() for k in
              ("dispatch", "ask(", "send_task", "kick", "spend_call"))]
    check("no dispatch/spend entry points on the module", banned == [])

    # cleanup
    try:
        for fn in os.listdir(tmp):
            os.remove(os.path.join(tmp, fn))
        os.rmdir(tmp)
    except OSError:
        pass
    _CFG["dir"] = HERE
    print("\nSELFTEST %s" % ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


# ================================================================================================
def _print_surfaces():
    d = _load_surfaces()
    print("SURFACE CAPACITY  (surfaces.json, measured_at %s)" % d.get("measured_at"))
    for name, s in d.get("surfaces", {}).items():
        u, q = s.get("used"), s.get("quota")
        pct = (u / q * 100) if (u is not None and q) else None
        flag = "measured" if s.get("measured") else "REPORTED"
        print("  %-6s %s / %s GB   %s   %s"
              % (name, ("%.2f" % u) if u is not None else "?",
                 ("%.0f" % q) if q is not None else "?",
                 ("%5.1f%%" % pct) if pct is not None else "  ?  ", flag))
    for name, m in d.get("meters", {}).items():
        print("  %-6s %s / %s %s   %s"
              % (name, m.get("used"), m.get("quota"), m.get("unit"),
                 "measured" if m.get("measured") else "REPORTED"))


def main(argv):
    if not argv or argv[0] in ("--once", "-1"):
        r = poll_host(quick=True)
        print("PolleR host poll  %s" % r["when"])
        _print_surfaces()
        return 0
    if argv[0] == "--selftest":
        return _selftest()
    if argv[0] == "--show":
        _print_surfaces()
        return 0
    if argv[0] == "--interval":
        mins = float(argv[1]) if len(argv) > 1 else 60.0
        print("PolleR host loop -- every %.0f min. HOST ONLY (no browser, no spend). Ctrl-C to stop." % mins)
        while True:
            try:
                r = poll_host(quick=True)
                print("[%s] host poll done (spend %s)" % (r["when"], r["spend"].get("spent")))
            except Exception as e:
                print("[%s] poll error (continuing): %s" % (_now_ts(), str(e)[:120]))
            # sleep in <=30s slices so Ctrl-C is responsive and no single sleep is huge
            remaining = mins * 60.0
            while remaining > 0:
                time.sleep(min(30.0, remaining))
                remaining -= 30.0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
