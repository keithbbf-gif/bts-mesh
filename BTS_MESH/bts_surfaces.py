"""
bts_surfaces.py — how much room is left on each SURFACE (ITC/R2, GDX/Drive, ODX/OneDrive, local).

THE PROBLEM KEITH NAMED
  The dashboard's SURFACE CAPACITY panel showed "?" for GDX and ODX. "?" is the honest answer to
  an unmeasured quantity, but it is an annoying one, and these two are exactly the surfaces most
  likely to fill up silently and break a handoff.

WHY THIS IS HARDER THAN `du`
  A folder walk gives you USED. It cannot give you QUOTA — and quota is the half you need in order
  to know whether you are about to hit a wall. The two clouds differ, and the difference is the
  whole design of this module:

    GDX / Google Drive for Desktop  ->  mounts as a VIRTUAL VOLUME (typically G: or E:).
        Windows disk-free on that volume reports the CLOUD quota, not a local disk. So
        shutil.disk_usage() on the Drive letter is a REAL quota reading. We sanity-check it
        against the known Google tiers (15 GB / 100 GB / 200 GB / 2 TB) and only trust it if the
        total looks like a cloud tier rather than a local SSD.

    ODX / OneDrive                  ->  is a FOLDER ON C:. disk_usage() there reports the C: drive.
        *** That number is not the OneDrive quota, and reporting it would be confidently wrong. ***
        This is the trap this module exists to avoid. Instead we read OneDrive's own client state
        (ClientPolicy*.ini, which the sync client writes and keeps current), and fall back to a
        folder walk for USED with quota = null if we cannot find it.

RULE (same as the dashboard's): a measured number, or null. Never a guess dressed as a reading.
"""
import json, os, re, shutil, sys, time

# Google's consumer/Workspace storage tiers, bytes. Used to decide whether a reported volume size
# is a CLOUD quota or just a local disk that happens to be mounted there.
GOOGLE_TIERS_GB = [15, 100, 200, 2048, 5120, 10240, 30720]
TOL = 0.06                      # 6% — Google reports 15 GB as 15.0e9-ish, not 15*2^30


def _gb(b):
    return round(b / (1024 ** 3), 2) if b is not None else None


def _looks_like_google_tier(total_bytes):
    if not total_bytes:
        return False
    gb = total_bytes / (1024 ** 3)
    gb10 = total_bytes / 1e9          # Google markets in decimal GB
    for t in GOOGLE_TIERS_GB:
        if abs(gb - t) / t < TOL or abs(gb10 - t) / t < TOL:
            return True
    return False


def _walk_used(path, cap_files=400000):
    """USED bytes by walking. Slow but always available. Returns (bytes, n_files, complete?)."""
    tot = n = 0
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    tot += os.path.getsize(os.path.join(root, f))
                    n += 1
                except OSError:
                    pass
            if n > cap_files:
                return tot, n, False
    except Exception:
        return None, 0, False
    return tot, n, True


# ------------------------------------------------------------------------------------------------
# GDX — Google Drive for Desktop
# ------------------------------------------------------------------------------------------------
# *** 🔴 THIS FUNCTION REPORTED THE WRONG VOLUME FOR DAYS. FIXED 2026-07-15. ***
#
# The candidate list was  [G:, E:, H:]  and **X: WAS NOT IN IT** — but GDX IS ON X:.
# CLAUDE.md says so in as many words: "GDX is X:\, not E:\ — the wrong letter sat in ROLD for a day."
# Same bug, second file.
#
# And it failed in the WORST possible way. If X: had simply been absent, this would have returned
# "Drive for Desktop not mounted" — honest. Instead **G: EXISTS** (it is the Tera mirror), so the
# scan "found" it, ran disk_usage on it, and rendered **3851 / 7452 GB as "Google Drive"**.
# The truth is **11.71 / 100 GB**. A missing drive says nothing; a WRONG drive says something
# plausible — which is exactly the "confident wrong reading" this file's own docstring warns about.
# The _looks_like_google_tier() sanity check DID catch it and set trusted:false … and the dashboard
# rendered the number anyway. A guard that only adds a footnote is not a guard.
#
# THE FIX, in order of authority:
#   1. drive/v3/about?fields=user(emailAddress),storageQuota  — the AUTHORITATIVE account quota,
#      and it self-identifies WHICH ACCOUNT it measured. No drive letter, no guessing.
#   2. disk_usage on a Drive-for-Desktop letter — X: FIRST, and ONLY if it passes the tier check.
#   3. Otherwise: say we cannot see it. Never a number from an unverified volume.
GDX_CANDIDATES = [r"X:\My Drive", r"X:\\",                       # <- the ACTUAL letter. First.
                  r"G:\My Drive", r"E:\My Drive", r"H:\My Drive",
                  r"G:\\", r"E:\\", r"H:\\"]


def gdx():
    # ---- 1. AUTHORITATIVE: ask Google, not the filesystem. -------------------------------------
    # This is the only method that (a) reports the real account quota, (b) names the account, and
    # (c) cannot be fooled by a same-lettered local disk.
    try:
        import bts_capacity
        acct = bts_capacity.GOOGLE_ACCOUNTS[0]
        g = bts_capacity.google_drive(acct)
        if g.get("measured") and g.get("quota"):
            return {
                "id": "gdx", "name": "GDX", "what": "Google Drive",
                "account": g.get("account"),                       # <- the disambiguator
                "used_gb": g.get("used"), "total_gb": g.get("quota"), "free_gb": g.get("free"),
                "pct": g.get("pct"), "ok": True, "trusted": True,
                "used_in_drive_gb": g.get("used_in_drive"),
                "used_in_trash_gb": g.get("used_in_trash"),
                "method": "drive/v3/about?fields=storageQuota (AUTHORITATIVE, account-labelled)",
                "note": ("%s — real account quota. Of %s GB used, only %s GB is in Drive; %s GB is "
                         "in TRASH (reclaimable) and the rest is Gmail/Photos. Supersedes the old "
                         "disk_usage(G:\\) reading, which was measuring the LOCAL TERA MIRROR."
                         % (g.get("account"), g.get("used"), g.get("used_in_drive"),
                            g.get("used_in_trash"))),
            }
    except Exception:
        pass   # fall through to the filesystem method

    # ---- 2. FALLBACK: Drive-for-Desktop volume, X: first, tier-checked. ------------------------
    hit = next((p for p in GDX_CANDIDATES if os.path.isdir(p)), None)
    if not hit:
        return {"id": "gdx", "name": "GDX", "what": "Google Drive",
                "used": None, "total": None, "free": None, "method": None,
                "ok": False, "note": "Drive for Desktop not mounted, and no Drive credential "
                                     "available for the API method."}

    drive_root = os.path.splitdrive(hit)[0] + "\\"
    try:
        du = shutil.disk_usage(drive_root)
    except Exception as e:
        return {"id": "gdx", "name": "GDX", "what": "Google Drive", "used": None,
                "total": None, "free": None, "ok": False, "method": None,
                "note": "disk_usage failed on %s: %s" % (drive_root, str(e)[:60])}

    # ---- 3. THE GUARD NOW REFUSES, instead of footnoting. --------------------------------------
    # Previously this returned the numbers with trusted:false and the dashboard drew them anyway.
    # If the volume's size does not match a Google storage tier, it is NOT Google Drive — and a
    # number we know is wrong must not be emitted at all.
    if not _looks_like_google_tier(du.total):
        return {
            "id": "gdx", "name": "GDX", "what": "Google Drive",
            "used_gb": None, "total_gb": None, "free_gb": None, "pct": None,
            "ok": False, "trusted": False, "path": hit,
            "method": "REFUSED — disk_usage(%s) failed the Google-tier check" % drive_root,
            "note": ("%s reports %.0f GB, which matches NO Google storage tier — it is a LOCAL disk, "
                     "not Drive. REFUSING to report it. (This exact mistake rendered the Tera mirror "
                     "as 'Google Drive 3851/7452 GB' for days.) Fix: mount Drive for Desktop, or "
                     "supply a Drive credential so the API method can run."
                     % (drive_root, du.total / 1e9)),
        }

    return {
        "id": "gdx", "name": "GDX", "what": "Google Drive",
        "path": hit,
        "used_gb": _gb(du.used), "total_gb": _gb(du.total), "free_gb": _gb(du.free),
        "pct": round(100.0 * du.used / du.total, 1) if du.total else None,
        "ok": True,
        "method": "disk_usage(%s) — fallback; the API method is authoritative" % drive_root,
        "trusted": True,
        "note": ("Drive-for-Desktop volume reports the CLOUD quota (%.0f GB matches a Google tier). "
                 "⚠ This method cannot name the account and only ever sees the ONE mounted letter."
                 % (du.total / 1e9)),
    }


# ------------------------------------------------------------------------------------------------
# ODX — OneDrive.  The trap: it is a folder on C:, so disk_usage() would report the C: drive.
# ------------------------------------------------------------------------------------------------
# OneDrive quota could NOT be probed on Keith's machine (ClientPolicy.ini yielded no QuotaTotal).
# The dashboard has carried a declared 1024 GB since an earlier session, consistent with an
# M365 Family/Personal 1 TB allocation. We use it — but we LABEL IT AS DECLARED, never as measured,
# and trusted=False keeps that visible on screen. If odx_probe.py ever finds the real key, the
# probed value wins and this constant becomes dead weight.
ODX_DECLARED_QUOTA_GB = 1024
ODX_DECLARED_NOTE = ("QUOTA IS DECLARED, NOT PROBED — 1 TB assumed (M365 Family/Personal). "
                     "OneDrive's ClientPolicy.ini did not expose QuotaTotal on this machine. "
                     "USED is genuinely measured by walking the folder. Verify the cap in "
                     "OneDrive tray icon -> Settings -> Account.")


def _onedrive_from_clientpolicy():
    """OneDrive's sync client writes ClientPolicy*.ini with the account's real quota. This is the
       only local source of TRUE OneDrive quota that does not require an OAuth token."""
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "OneDrive", "settings")
    if not os.path.isdir(base):
        return None
    best = None
    for root, dirs, files in os.walk(base):
        for f in files:
            if not f.lower().startswith("clientpolicy") or not f.lower().endswith(".ini"):
                continue
            try:
                txt = open(os.path.join(root, f), encoding="utf-16", errors="ignore").read()
                if not txt.strip():
                    txt = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            # keys seen in the wild: QuotaTotal / QuotaUsed  (bytes)
            m_t = re.search(r"^\s*QuotaTotal\s*=\s*(\d+)", txt, re.M | re.I)
            m_u = re.search(r"^\s*QuotaUsed\s*=\s*(\d+)", txt, re.M | re.I)
            if m_t:
                cand = {"total": int(m_t.group(1)),
                        "used": int(m_u.group(1)) if m_u else None,
                        "src": os.path.join(root, f)}
                if not best or (cand["total"] or 0) > (best["total"] or 0):
                    best = cand
    return best


def odx():
    folder = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer") \
             or os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive")
    exists = os.path.isdir(folder)

    pol = _onedrive_from_clientpolicy()
    if pol and pol.get("total"):
        used = pol.get("used")
        if used is None and exists:
            used, _, _ = _walk_used(folder)
        return {"id": "odx", "name": "ODX", "what": "OneDrive",
                "path": folder,
                "used_gb": _gb(used), "total_gb": _gb(pol["total"]),
                "free_gb": _gb(pol["total"] - used) if used is not None else None,
                "pct": round(100.0 * used / pol["total"], 1) if used else None,
                "ok": True, "trusted": True,
                "method": "ClientPolicy.ini",
                "note": "Quota read from OneDrive's own sync-client state (%s)."
                        % os.path.basename(pol["src"])}

    # Fallback: USED is measurable; QUOTA is not probeable on this build.
    # *** DO NOT substitute disk_usage(C:) here. That is the C: drive, not the OneDrive quota. ***
    # We fall back to the DECLARED 1 TB, flagged trusted=False so the screen never claims it
    # was measured. A labelled assumption beats both a silent guess and a useless "?".
    if exists:
        used, n, complete = _walk_used(folder)
        tot = ODX_DECLARED_QUOTA_GB * (1024 ** 3)
        return {"id": "odx", "name": "ODX", "what": "OneDrive",
                "path": folder,
                "used_gb": _gb(used),
                "total_gb": float(ODX_DECLARED_QUOTA_GB),
                "free_gb": _gb(tot - used) if used is not None else None,
                "pct": round(100.0 * used / tot, 1) if used else None,
                "ok": True,
                "trusted": False,                       # used=measured, quota=DECLARED
                "quota_declared": True,
                "method": "USED: folder walk (%d files%s) | QUOTA: declared %d GB"
                          % (n, "" if complete else ", TRUNCATED", ODX_DECLARED_QUOTA_GB),
                "note": ODX_DECLARED_NOTE}
    return {"id": "odx", "name": "ODX", "what": "OneDrive", "used_gb": None, "total_gb": None,
            "free_gb": None, "ok": False, "trusted": False, "method": None,
            "note": "OneDrive folder not found."}


# ------------------------------------------------------------------------------------------------
# ITC / R2 — the published archive. Free tier is 10 GB; we measure the SOURCE tree we publish.
# ------------------------------------------------------------------------------------------------
def itc():
    pub = [r"V:\Research4\Ai\PhD2_DATA_ARCHIVE", r"V:\Research4\Ai\BTS_MESH", r"D:\PhD"]
    tot, files, complete = 0, 0, True
    for p in pub:
        if os.path.isdir(p):
            b, n, c = _walk_used(p)
            tot += (b or 0); files += n; complete &= c
    R2_FREE = 10 * (1024 ** 3)
    return {"id": "itc", "name": "ITC", "what": "Cloudflare R2",
            "used_gb": _gb(tot), "total_gb": _gb(R2_FREE), "free_gb": _gb(R2_FREE - tot),
            "pct": round(100.0 * tot / R2_FREE, 1),
            "ok": True, "trusted": True,
            "method": "walk of the published subtree (%d files)" % files,
            "note": "R2 free tier is 10 GB. This is the SOURCE we publish, so it is an upper "
                    "bound on what is stored at the edge."}


def local():
    try:
        du = shutil.disk_usage(r"D:\\")
        return {"id": "local", "name": "LOCAL", "what": "D: drive",
                "used_gb": _gb(du.used), "total_gb": _gb(du.total), "free_gb": _gb(du.free),
                "pct": round(100.0 * du.used / du.total, 1), "ok": True, "trusted": True,
                "method": "disk_usage(D:)", "note": "The working drive."}
    except Exception as e:
        return {"id": "local", "name": "LOCAL", "what": "D: drive", "ok": False,
                "trusted": False, "used_gb": None, "total_gb": None, "free_gb": None,
                "method": None, "note": str(e)[:80]}


# ------------------------------------------------------------------------------------------------
# TB1 — TeraBox.  Added 2026-07-15 (Keith: "I don't see TB1 in the mesh").
# ------------------------------------------------------------------------------------------------
def tb1():
    """TB1 is a SURFACE, so it gets a row — even while unconfigured. A surface that is missing from
    the panel is invisible; a surface that is PRESENT and says why it is dark is information.

    ⚠ There is NO TeraBox API (verified 2026-07-15, rclone docs: "TeraBox backend requires
    authentication using your account's COOKIE, because TeraBox does not provide an official API").
    Official rclone has no terabox backend — only unofficial forks, all wanting the session cookie
    in rclone.conf in PLAINTEXT. A session cookie is not a scoped key: it IS the account. Do not.
    The ONLY clean path is the official PC client's local folder -> ordinary file tools, like ODX.
    Set bts_capacity.TB1_PATH once it exists.
    """
    try:
        import bts_capacity
        t = bts_capacity.tb1()
    except Exception as e:
        return {"id": "tb1", "name": "TB1", "what": "TeraBox", "ok": False, "trusted": False,
                "used_gb": None, "total_gb": None, "free_gb": None, "method": None,
                "note": "bts_capacity unavailable: %s" % str(e)[:60]}

    if not t.get("measured"):
        return {"id": "tb1", "name": "TB1", "what": "TeraBox", "ok": False, "trusted": False,
                "account": t.get("account"),
                "used_gb": None, "total_gb": None, "free_gb": None, "pct": None,
                "quota_declared": True,
                "method": "NOT CONFIGURED",
                "note": "%s %s" % (t.get("error", ""), t.get("note", ""))}

    return {"id": "tb1", "name": "TB1", "what": "TeraBox", "ok": True,
            "account": t.get("account"), "path": t.get("path"),
            "used_gb": t.get("used"), "total_gb": t.get("quota"), "free_gb": t.get("free"),
            "pct": t.get("pct"),
            "trusted": False,            # USED is measured; QUOTA is DECLARED. Never conflate.
            "quota_declared": True,
            "method": t.get("method"),
            "note": "USED is a walk of the LOCAL mirror. QUOTA (1024 GB) is DECLARED — no API "
                    "exists to probe it. ⚠ If the PC client is upload-only rather than two-way "
                    "sync, the local walk is NOT what is in the cloud."}


def run():
    return {"ts": int(time.time()),
            "when": time.strftime("%Y-%m-%d %H:%M:%S"),
            "surfaces": [itc(), gdx(), odx(), tb1(), local()]}


if __name__ == "__main__":
    r = run()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "surfaces.json")
    json.dump(r, open(out, "w"), indent=1)
    print("SURFACE CAPACITY   %s\n" % r["when"])
    for s in r["surfaces"]:
        u, t = s.get("used_gb"), s.get("total_gb")
        bar = ""
        if s.get("pct") is not None:
            n = int(s["pct"] / 5)
            bar = "[" + "#" * n + "." * (20 - n) + "] %5.1f%%" % s["pct"]
        val = ("%8.2f / %-8s GB" % (u, t if t is not None else "?")) if u is not None else "        ?"
        flag = "" if s.get("trusted") else "  <- UNTRUSTED"
        print("  %-6s %-14s %s %s%s" % (s["name"], s["what"], val, bar, flag))
        print("         %s" % s["note"])
    print("\nwrote %s" % out)
