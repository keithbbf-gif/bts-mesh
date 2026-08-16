#!/usr/bin/env python3
"""
bts_capacity.py — the <check> button's engine. MEASURE every storage surface, per ACCOUNT.

Keith, 2026-07-15: "a small button near the drive capacity that lets me <check> and it checks
OneDrive, GoogleDrive (find a way to address each google drive even if they are in different
account - disambiguate), ITC and TB1."

────────────────────────────────────────────────────────────────────────────────────────────────
WHY THIS EXISTS ALONGSIDE bts_quota.py (which is NOT dead — read this before deleting either)
────────────────────────────────────────────────────────────────────────────────────────────────
bts_quota.py measures GDX with a genuinely clever trick: the Google Drive DESKTOP CLIENT mounts
the account at X:, and reports the ACCOUNT QUOTA as the volume size — so shutil.disk_usage("X:\\")
yields 11.71 / 100 GB, which is CORRECT. Keep it; it needs no credentials.

But it has one hard limit, and it is exactly the thing Keith asked to solve:
    *** ONE MOUNTED DRIVE LETTER = ONE ACCOUNT. ***
It physically cannot see joanna.bbf's or ranny.bbf's Drive, because they are not mounted here and
never will be. There is no drive letter for "somebody else's Google account".

THE DISAMBIGUATION ANSWER (measured 2026-07-15, not researched — it took one API call):
    GET drive/v3/about?fields=user(emailAddress,displayName),storageQuota
    -> {"user":{"emailAddress":"keith.bbf@gmail.com"}, "storageQuota":{...}}
**Each OAuth credential IS an account, and the API stamps every response with its own email.**
So N accounts = N credential files. There is no trick, no shared endpoint, nothing to research —
you cannot enumerate someone's Google accounts, you can only hold a credential for each.
The email in the response IS the disambiguator. Never label a row by guesswork; label it by that.

It also returns a breakdown disk_usage() cannot see:
    usage            = ALL Google services (Drive + Gmail + Photos)   <- what the quota bills
    usageInDrive     = Drive files only
    usageInDriveTrash= trash still counting against you
Measured on keith.bbf 2026-07-15: 11.71 total / 2.90 in Drive / 2.43 IN TRASH. So ~8.8 GB is
Gmail+Photos and 2.43 GB is recoverable by emptying trash. The X: trick shows only the 11.71.

────────────────────────────────────────────────────────────────────────────────────────────────
HONESTY RULES (this dashboard's whole discipline; see bts_quota.py's ODX scar)
────────────────────────────────────────────────────────────────────────────────────────────────
* Every row carries `measured: true|false`. A DECLARED number is never rendered as a measurement.
* A wrong number that looks plausible is worse than "unknown". ODX was once reported as
  1364/3726 GB — that was D: wearing an ODX label, because disk_usage() on a FOLDER returns the
  VOLUME. Do not reintroduce that.
* If a surface cannot be reached, say so and say WHY. Never estimate.
"""
from __future__ import annotations
import json, os, shutil, time, urllib.parse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
SECRETS = r"V:\Research4\.secrets"
AI_DIR = r"V:\Research4\Ai"

GB = 1024 ** 3
def _gb(n):
    try:
        return round(float(n) / GB, 2)
    except Exception:
        return None


# ── GOOGLE DRIVE — per account, self-identifying ────────────────────────────────────────────────
# Add a (client_secrets, credentials) pair here for each account you hold a credential for.
# joanna.bbf / ranny.bbf get a line each once their OAuth exists. Until then they are NOT listed —
# an account we cannot reach is not a row with a "?", it is simply absent.
GOOGLE_ACCOUNTS = [
    {"label": "GDX", "client_secrets": os.path.join(AI_DIR, "client_secrets.json"),
     "credentials": os.path.join(AI_DIR, "credentials.json"),
     "note": "The exchange rail. Folder BTS_SGH_Handoff = 1aiMjVZfFtiBGNAlkTwAYiq1Pvuz2F6hA."},
]


def _google_access_token(client_secrets_path, credentials_path):
    cs = json.load(open(client_secrets_path, encoding="utf-8"))
    cs = cs.get("installed") or cs.get("web") or cs
    cr = json.load(open(credentials_path, encoding="utf-8"))
    data = urllib.parse.urlencode({
        "client_id": cs["client_id"], "client_secret": cs["client_secret"],
        "refresh_token": cr["refresh_token"], "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    return json.load(urllib.request.urlopen(req, timeout=30))["access_token"]


def google_drive(acct):
    """Real quota for ONE Google account. The returned email IS the disambiguator."""
    out = {"id": acct["label"], "kind": "google-drive", "measured": False,
           "account": None, "note": acct.get("note", "")}
    try:
        at = _google_access_token(acct["client_secrets"], acct["credentials"])
        u = ("https://www.googleapis.com/drive/v3/about"
             "?fields=user(emailAddress,displayName),storageQuota")
        d = json.load(urllib.request.urlopen(
            urllib.request.Request(u, headers={"Authorization": "Bearer " + at}), timeout=30))
        q = d.get("storageQuota", {}) or {}
        limit = q.get("limit")
        out.update({
            "measured": True,
            "account": d.get("user", {}).get("emailAddress"),   # <- the disambiguator
            "display_name": d.get("user", {}).get("displayName"),
            "quota": _gb(limit) if limit else None,             # absent => unlimited (Workspace)
            "used": _gb(q.get("usage")),
            "used_in_drive": _gb(q.get("usageInDrive")),
            "used_in_trash": _gb(q.get("usageInDriveTrash")),
            "method": "drive/v3/about?fields=storageQuota — the AUTHORITATIVE account quota",
        })
        if out["quota"] and out["used"] is not None:
            out["free"] = round(out["quota"] - out["used"], 2)
            out["pct"] = round(100.0 * out["used"] / out["quota"], 1)
        # The distinction bts_quota.py's X:-mount trick cannot show:
        out["breakdown_note"] = (
            "used = ALL Google services (Drive+Gmail+Photos). used_in_drive = files only. "
            "used_in_trash still counts against the quota — emptying trash reclaims it.")
    except urllib.error.HTTPError as e:
        out["error"] = "HTTP %s — %s" % (e.code, e.read().decode()[:120])
    except FileNotFoundError as e:
        out["error"] = "no credential on file: %s" % os.path.basename(str(e.filename or ""))
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, str(e)[:120])
    return out


# ── ODX (OneDrive) ──────────────────────────────────────────────────────────────────────────────
ODX_PATH = r"D:\ODX\OneDrive"

def odx():
    """USED is genuinely measured by walking the folder. QUOTA is NOT measurable locally.

    ⚠ DO NOT use shutil.disk_usage() here. D:\\ODX\\OneDrive is a FOLDER ON D:, so disk_usage
    returns the D: VOLUME's numbers — that is how this surface once got reported as 1364/3726 GB,
    which was D: wearing an ODX label. The real quota lives behind Microsoft Graph (/me/drive ->
    quota{total,used,remaining}), which needs an app registration + OAuth we do not have.
    """
    out = {"id": "ODX", "kind": "onedrive", "path": ODX_PATH,
           "quota": 1024.0, "quota_measured": False,
           "quota_source": "DECLARED — assumed 1 TB (M365 Family). NOT probed.",
           "note": "Cold archive. Quota needs Microsoft Graph /me/drive (app registration + OAuth) "
                   "— not built. USED below is real."}
    try:
        total, n = 0, 0
        for root, _dirs, files in os.walk(ODX_PATH):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f)); n += 1
                except OSError:
                    pass
        out.update({"measured": True, "used": _gb(total), "files": n,
                    "method": "folder walk (%d files) — USED is measured, QUOTA is not" % n})
        out["free"] = round(out["quota"] - out["used"], 2)
        out["pct"] = round(100.0 * out["used"] / out["quota"], 1)
    except Exception as e:
        out.update({"measured": False, "error": "%s: %s" % (type(e).__name__, str(e)[:100])})
    return out


# ── ITC (Cloudflare R2) ─────────────────────────────────────────────────────────────────────────
ITC_SRC = r"V:\Research4\Ai\PhD2_DATA_ARCHIVE"

def itc():
    """USED = walk of the published subtree — an UPPER BOUND on what is at the edge, not a probe
    of R2 itself. The true figure needs the Cloudflare API + the R2 keys, which live in
    D:\\R2Cloner in PLAINTEXT and must never be read, printed, or handed to a node."""
    out = {"id": "ITC", "kind": "r2", "quota": 10.0, "quota_measured": False,
           "quota_source": "R2 free tier = 10 GB-month, PER ACCOUNT (not per bucket).",
           "note": "PUBLIC WEB (ai.dchambers.com). Overage is $0.015/GB-month and egress is free, "
                   "so capacity here is a non-problem worth pennies — DISCLOSURE is the real risk."}
    try:
        total, n = 0, 0
        for root, _dirs, files in os.walk(ITC_SRC):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f)); n += 1
                except OSError:
                    pass
        out.update({"measured": True, "used": _gb(total), "files": n,
                    "method": "walk of the published SOURCE subtree (%d files) — upper bound, "
                              "not a live R2 probe" % n})
        out["free"] = round(out["quota"] - out["used"], 2)
        out["pct"] = round(100.0 * out["used"] / out["quota"], 1)
    except Exception as e:
        out.update({"measured": False, "error": "%s: %s" % (type(e).__name__, str(e)[:100])})
    return out


# ── TB1 (TeraBox) ───────────────────────────────────────────────────────────────────────────────
# Account: keith.bbf@gmail.com (bound 2026-07-15).
# NOT CONFIGURED YET. Probed 2026-07-15: no TeraBox process running, no uninstall registry entry,
# and request_access could not resolve the app name. The PC client's folder path is unknown.
#
# ══ CORRECTION 2026-07-15 — AN EARLIER VERSION OF THIS COMMENT SAID "THERE IS NO TERABOX API".
#    THAT WAS FALSE, AND SGH CAUGHT IT. ══
# I sourced "no official API" from RCLONE's docs ("TeraBox backend requires authentication using
# your account's COOKIE, because TeraBox does not provide an official API"). That is rclone's
# JUSTIFICATION FOR COOKIE AUTH — a third party's excuse, which I repeated as the vendor's fact.
# SGH's grounded search found the vendor's own page and it was right:
#
#   *** TeraBox Open Platform Integration Document — https://www.terabox.com/integrations/docs
#       OAuth: authorization-code mode AND device-code mode (QR scan in the app)
#       access_token  valid 2 DAYS      refresh_token valid 30 DAYS
#       /oauth/tokeninfo returns api_domain + upload_domain (sharded upload API) ***
#
# ⇒ TB1 can have a PROPER credentialed rail: real OAuth tokens, revocable, no session cookie, no
#   unofficial third-party binary. The objection I raised (a plaintext cookie IS the account) does
#   not apply to the official API. DO NOT use the rclone forks — they exist only because rclone
#   never integrated the Open Platform.
# ⚠ The 2-day access / 30-day refresh window means TB1 needs periodic re-auth, like GDX. Budget for
#   it; do not discover it when a backup silently stops.
#
# THE LESSON (this is why the comment stays this long): the FREE grounded node beat Cowork's own
# search on Cowork's own homework. Ask the mesh before asserting a vendor has no API.
#
# STILL TRUE: no node (SGH/GEM/CoP) has a TeraBox connector, so TB1 is a VAULT, not a rendezvous.
# The Drive folder keeps that job.
# STILL OPEN: SGH reports the PC client is "selective auto-backup (upload-focused), NOT a full
#   bidirectional mirror" [Bytesbin — third-party, unverified]. Matters less now that the API
#   exists, but if TB1_PATH is ever used, a local walk may NOT reflect what is in the cloud.
# ══ MEASURED FROM TERABOX'S OWN AUTHENTICATED API, 2026-07-15 — and it demolishes the "1 TB" claim.
# Called from inside the logged-in page (Chrome MCP -> javascript_tool -> fetch with credentials).
# NO cookie was extracted, NO rclone fork, NO OAuth registration — the session never left the browser.
#
#   GET /api/quota?checkfree=1  ->  200
#     init_quota_type              : "permanent_30g_temp_994g"      <- the vendor's own words
#     time_limit_quota_expire_time : 1786740481 = 2026-08-14 20:48 UTC  (~30 DAYS)
#     free                         : 32212254720 = EXACTLY 30.00 GB
#   GET /api/list?dir=/         ->  200, folder "Ai-PhD" (empty)
#
# ⇒ **TB1's DURABLE CAPACITY IS 30 GB, NOT 1024.** The advertised "1 TB free" is 30 GB permanent
#   plus a 994 GB bonus that EVAPORATES on 2026-08-14. The cost table said "1 TB (with limits)";
#   "with limits" was carrying the whole sentence.
# ⇒ TB1 IS A 30 GB WORKING SURFACE, NOT A VAULT. The archive stays on ODX (1 TB, real).
#   The PDF library alone is ~11 GB; GDX has 100 GB. TB1 is the SMALLEST cloud surface we own.
#
# 🔴 SGH (grounded, Reddit-sourced) said the bonus lasts "3 months, or up to 6 months". The VENDOR'S
#    API says 30 days. SGH was 3-6x wrong on the one number that decides whether TB1 can hold data.
#    THE LADDER HELD: the publisher's own endpoint beats a grounded model, exactly like Crossref
#    beats a model on DOIs. Ask the vendor, not the forum.
# ⚠ STILL UNKNOWN, and it is the question that matters: what happens to files above 30 GB when the
#   bonus lapses — deleted, frozen, or account locked? SGH returned UNKNOWN; TeraBox publishes no ToS
#   page that says. DO NOT put anything on TB1 that you cannot afford to lose on 2026-08-14.
#   (Their PAID plan explicitly retains files after expiry. The free tier makes no such promise.)
TB1_PATH = None                    # PC client not installed; not needed — the API path works.
TB1_QUOTA_GB = 30.0                # PERMANENT quota. NOT the advertised 1024.
TB1_TEMP_GB = 994.0                # bonus — expires below
TB1_TEMP_EXPIRES = 1786740481      # 2026-08-14 20:48 UTC. Vendor-reported, not computed.

def tb1():
    import time as _t
    days = (TB1_TEMP_EXPIRES - _t.time()) / 86400.0
    out = {"id": "TB1", "kind": "terabox", "account": "keith.bbf@gmail.com",
           "quota": TB1_QUOTA_GB,                 # 30 GB — the DURABLE number
           "quota_measured": True,                # vendor's own /api/quota said so
           "quota_source": ("VENDOR API /api/quota?checkfree=1 -> init_quota_type="
                            "'permanent_30g_temp_994g', free=32212254720 (=30.00 GB exactly)."),
           "temp_quota": TB1_TEMP_GB,
           "temp_expires_ts": TB1_TEMP_EXPIRES,
           "temp_expires": "2026-08-14 20:48 UTC",
           "temp_days_left": round(days, 1),
           "advertised": 1024.0,
           "measured": False,
           "note": ("⚠ ADVERTISED 1024 GB = 30 GB PERMANENT + 994 GB that EXPIRES in %.1f days "
                    "(2026-08-14). Durable capacity is 30 GB — the SMALLEST cloud surface we own "
                    "(GDX=100, ODX=1024). NOT a vault. What happens to files above 30 GB at expiry "
                    "is UNKNOWN — TeraBox publishes no ToS answer and SGH could not find one. Do "
                    "not store anything here you cannot lose on 2026-08-14." % days)}
    if not TB1_PATH:
        # NOT an error — the DOM rail is PROVEN, read AND write. The local mirror is not the rail.
        out["error"] = ("USED not measurable from python — TB1's rail is the BROWSER, not the disk.")
        out["rail"] = "DOM-XHR (Chrome MCP -> javascript_tool, inside the logged-in page)"
        out["rail_proven"] = "2026-07-15 — read AND write, both verified server-side"
        out["rail_note"] = (
            "════ THE TB1 RAIL — PROVEN 2026-07-15. Read this before 'improving' it. ════\n"
            "READ : fetch('/api/quota?checkfree=1') and fetch('/api/list?dir=/...') with\n"
            "       credentials:'include', executed INSIDE the logged-in page. -> 200.\n"
            "WRITE: *** DO NOT hand-roll /api/precreate. *** I tried; it returns\n"
            "       errno 4000023 'need verify' even WITH the page's bdstoken — there is a second\n"
            "       verification layer, and reverse-engineering it is a losing game against a vendor\n"
            "       who changes it at will.\n"
            "       THE ANSWER: hand the app's OWN file input a File object and let TeraBox do its\n"
            "       own upload — its own verify, its own chunking, its own tokens:\n"
            "           const inp = document.getElementById('h5Input0');   // name=html5uploader\n"
            "           const dt = new DataTransfer();\n"
            "           dt.items.add(new File([body], 'NAME.md', {type:'text/markdown'}));\n"
            "           inp.files = dt.files;\n"
            "           inp.dispatchEvent(new Event('change', {bubbles:true}));\n"
            "       (h5Input2 has webkitdirectory=true -> whole-folder upload.)\n"
            "VERIFY: NEVER trust the UI's 'Upload Complete（1/1）' — that is a node's DONE by another\n"
            "       name, and a fabricated DONE cost us an hour today. Confirm with /api/list:\n"
            "       BTS_TB1_RAILCHECK.md -> isdir:0, size:13, md5:d067cfe0, and /api/quota used:0->13.\n"
            "WHY THIS BEATS THE ALTERNATIVES: no cookie extraction (the session never leaves the\n"
            "       browser), no unofficial rclone fork, no Open Platform registration, no native\n"
            "       client. Keith's framing was right — these are a LADDER, not alternatives.\n"
            "LIMIT: it needs a BROWSER, so python cannot drive it and NO NODE can reach it. TB1 is\n"
            "       COWORK-ONLY -> zero node edges in SIGNAL CORE. That is the truth, not a gap.")
        return out
    if not os.path.isdir(TB1_PATH):
        out["error"] = "TB1_PATH set but does not exist: %s" % TB1_PATH
        return out
    try:
        total, n = 0, 0
        for root, _dirs, files in os.walk(TB1_PATH):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f)); n += 1
                except OSError:
                    pass
        out.update({"measured": True, "used": _gb(total), "files": n, "path": TB1_PATH,
                    "method": "folder walk (%d files) — LOCAL mirror only. If the client is "
                              "upload-only this is NOT what is in the cloud." % n})
        out["free"] = round(out["quota"] - out["used"], 2)
        out["pct"] = round(100.0 * out["used"] / out["quota"], 1)
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, str(e)[:100])
    return out


def check():
    """Everything the <check> button runs. Returns a list of surface rows + a summary."""
    t0 = time.time()
    rows = [google_drive(a) for a in GOOGLE_ACCOUNTS]
    rows += [odx(), itc(), tb1()]
    return {
        "ts": int(time.time()),
        "when": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_s": round(time.time() - t0, 2),
        "surfaces": rows,
        "ok": sum(1 for r in rows if r.get("measured")),
        "total": len(rows),
        "legend": ("measured=true  -> probed just now. measured=false -> DECLARED or unreachable; "
                   "the reason is in .error/.quota_source. A declared number is NEVER a measurement."),
    }


if __name__ == "__main__":
    r = check()
    print("SURFACE <CHECK>   %s   (%.2fs)  %d/%d measured\n" %
          (r["when"], r["elapsed_s"], r["ok"], r["total"]))
    print("%-6s %-26s %10s %10s %8s  %s" % ("id", "account", "used GB", "quota GB", "pct", "state"))
    print("-" * 104)
    for s in r["surfaces"]:
        state = "measured" if s.get("measured") else ("ERROR: " + str(s.get("error", ""))[:44])
        print("%-6s %-26s %10s %10s %7s%%  %s" % (
            s["id"], (s.get("account") or "-")[:26],
            s.get("used", "-"), s.get("quota", "-"), s.get("pct", "-"), state))
        if s.get("used_in_trash"):
            print("       ^ of which %s GB is in Drive TRASH (reclaimable), %s GB actually in Drive"
                  % (s["used_in_trash"], s.get("used_in_drive")))
