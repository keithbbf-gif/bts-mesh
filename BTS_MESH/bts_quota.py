#!/usr/bin/env python3
"""
bts_quota.py — MEASURE the surface quotas instead of assuming them.

Keith, 2026-07-13, on whether to buy more Google Drive: "Yes" — verify first.
And the verification found a problem in our own dashboard: SURFACE CAPACITY has been showing
GDX as "? / 100 GB". The "?" was honest (we could not see usage). **The 100 GB was not.**
It was an assumption nobody measured. A stock Google account is 15 GB, shared with Gmail and
Photos. Planning a purchase against an unverified quota is exactly the failure class this
dashboard exists to prevent — so: measure it.

HOW: the Google Drive desktop client mounts the account at X: and reports the ACCOUNT QUOTA as
the volume's size. shutil.disk_usage("X:\\") therefore gives total / used / free for the Drive
account itself. Same trick works for the OneDrive folder (ODX) and every local drive.

ITC (Cloudflare R2) is NOT a mounted volume — its usage is measured by the publish bat, and its
quota is the R2 free tier (10 GB). Left as-is, and flagged as such.

Run on the HOST. Writes into dash.json -> surfaces{} so SURFACE CAPACITY stops guessing.
"""
import json, os, shutil, time

HERE = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.join(HERE, "dash.json")

VOLS = [
    ("GDX", r"X:\\",                       "Google Drive — the exchange rail. Fast (580 MB/s) and PRIVATE."),
    ("D:",  r"D:\\",                       "Research2 + PhD library live here. 84 MB/s write."),
    ("C:",  r"C:\\",                       "System / NVMe. 1416 MB/s write."),
    ("G:",  r"G:\\",                       "Tera mirror. 31 MB/s write — the slowest surface we own."),
]

# ── ODX CANNOT BE MEASURED THIS WAY, AND THE FIRST VERSION OF THIS SCRIPT LIED ABOUT IT ──────────
# D:\ODX\OneDrive is a FOLDER ON D:. shutil.disk_usage() on it returns the D: VOLUME's numbers, so
# the script cheerfully reported ODX as 1364/3726 GB — which is just D: wearing a different label.
# A wrong number that looks plausible is worse than a "?", and this dashboard's whole discipline is
# to never emit one. Caught 2026-07-13.
#
# OneDrive's real quota is only visible from the OneDrive client. Keith read it off the client:
ODX_REPORTED = {"used": 105.5, "quota": 1024.0,
                "source": "Keith read it from the OneDrive client, 2026-07-13",
                "note": "OneDrive — cold archive, 1 TB. NOT measurable by disk_usage (the local path "
                        "is a folder on D:, which is what the first version of this script wrongly "
                        "reported). Accessibility is its weak point: no node can read it."}

def gb(n):
    return round(n / (1024 ** 3), 2)

if __name__ == "__main__":
    out = {}
    print("%-6s %10s %10s %10s   %s" % ("surface", "used GB", "free GB", "total GB", "note"))
    print("-" * 92)
    for name, path, note in VOLS:
        try:
            t, u, f = shutil.disk_usage(path)
            out[name] = {"used": gb(u), "free": gb(f), "quota": gb(t), "note": note,
                         "measured": True, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
            pct = u / t * 100 if t else 0
            print("%-6s %10.2f %10.2f %10.2f   %4.1f%%  %s" % (name, gb(u), gb(f), gb(t), pct, note[:44]))
        except Exception as e:
            out[name] = {"used": None, "free": None, "quota": None, "measured": False,
                         "note": "NOT MEASURABLE: %s" % (str(e)[:60])}
            print("%-6s %10s %10s %10s   %s" % (name, "-", "-", "-", "not present / not measurable"))

    # ODX — user-reported, NOT measured. Labelled as such, because the difference matters.
    out["ODX"] = {"used": ODX_REPORTED["used"], "quota": ODX_REPORTED["quota"],
                  "free": round(ODX_REPORTED["quota"] - ODX_REPORTED["used"], 2),
                  "measured": False, "source": ODX_REPORTED["source"], "note": ODX_REPORTED["note"]}
    print("%-6s %10.2f %10.2f %10.2f   %4.1f%%  %s" % (
        "ODX", ODX_REPORTED["used"], ODX_REPORTED["quota"] - ODX_REPORTED["used"],
        ODX_REPORTED["quota"], ODX_REPORTED["used"] / ODX_REPORTED["quota"] * 100,
        "USER-REPORTED (OneDrive client) — not measurable here"))

    # ITC is not a volume — its usage comes from the publish, its quota is the R2 free tier.
    out["ITC"] = {"used": 4.51, "quota": 10.0, "measured": False,
                  "note": "Cloudflare R2 free tier. Usage from the last publish, NOT live. "
                          "PUBLIC WEB — the PDF library should not be here."}

    # OWN FILE (surfaces.json) — dash.json is rebuilt on every launch and would erase this.
    SRF = os.path.join(HERE, "surfaces.json")
    payload = {"surfaces": out, "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    tmp = SRF + ".tmp"
    json.dump(payload, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, SRF)
    print("\nwrote %d surfaces -> surfaces.json (merged into dash.json by bts_snapshot)" % len(out))

    g = out.get("GDX", {})
    if g.get("measured"):
        print("\n*** GDX ACCOUNT QUOTA = %.2f GB  (used %.2f, free %.2f) ***" % (g["quota"], g["used"], g["free"]))
        print("    The dashboard has been claiming 100 GB. If this says ~15 GB, that claim was invented.")
        print("    Unique PDF corpus = 11.05 GB. Scholarly core = 1.74 GB. Plan the purchase against THIS.")
