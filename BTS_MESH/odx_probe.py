"""
odx_probe.py — one-shot diagnostic: find where OneDrive keeps its QUOTA on THIS machine.

WHY: bts_surfaces.py measured ODX used = 105.15 GB by walking the folder, but could not find the
quota, so it honestly returned null. The quota IS on disk somewhere — the sync client has to know
it — but the file name / key name / encoding varies by OneDrive build and account type.

This prints ONLY: file paths, encodings, and lines containing "quota"/"total"/"space".
It does NOT print account IDs, tokens, or file contents beyond those matched lines.

Run:  python odx_probe.py
Paste the output back to Claude and the parser gets fixed against ground truth, not a guess.
"""
import os, re, glob

LA = os.environ.get("LOCALAPPDATA", "")
BASE = os.path.join(LA, "Microsoft", "OneDrive", "settings")

KEYWORDS = re.compile(r"quota|total.*space|space.*total|storage|capacity|libsize", re.I)
# lines that look like they hold a big byte count
NUMISH = re.compile(r"\b\d{9,}\b")


def sniff(path):
    for enc in ("utf-16", "utf-16-le", "utf-8-sig", "utf-8", "latin-1"):
        try:
            txt = open(path, encoding=enc).read()
        except Exception:
            continue
        if not txt or txt.count("\x00") > len(txt) // 4:
            continue
        printable = sum(c.isprintable() or c in "\r\n\t" for c in txt[:400])
        if printable > 300:
            return enc, txt
    return None, None


print("=" * 78)
print("ODX QUOTA PROBE")
print("=" * 78)
print("OneDrive folder env : %s" % (os.environ.get("OneDrive") or "(not set)"))
print("OneDriveCommercial  : %s" % (os.environ.get("OneDriveCommercial") or "(not set)"))
print("OneDriveConsumer    : %s" % (os.environ.get("OneDriveConsumer") or "(not set)"))
print("settings dir        : %s   exists=%s" % (BASE, os.path.isdir(BASE)))
print()

if not os.path.isdir(BASE):
    print("!! settings dir not found — nothing to scan.")
    raise SystemExit(1)

hits = 0
for root, dirs, files in os.walk(BASE):
    for f in sorted(files):
        p = os.path.join(root, f)
        try:
            sz = os.path.getsize(p)
        except OSError:
            continue
        if sz > 8_000_000:                     # skip the big .dat blobs
            continue
        if not f.lower().endswith((".ini", ".cfg", ".txt", ".json")):
            continue
        enc, txt = sniff(p)
        if not txt:
            continue
        matched = [ln.strip() for ln in txt.splitlines()
                   if KEYWORDS.search(ln) or (NUMISH.search(ln) and "=" in ln)]
        if not matched:
            continue
        rel = os.path.relpath(p, BASE)
        print("-" * 78)
        print("FILE: %s   (%d bytes, %s)" % (rel, sz, enc))
        for ln in matched[:18]:
            # redact anything that looks like an id/hash/token, keep numbers + key names
            safe = re.sub(r"\b[0-9a-fA-F]{16,}\b", "<id>", ln)
            print("   " + safe[:150])
        hits += 1

print("-" * 78)
print("\n%d candidate file(s) scanned with matches." % hits)
if not hits:
    print("No quota-looking keys found. OneDrive may store it in a binary .dat on this build —")
    print("in that case the honest answer stays: USED is measured, QUOTA is unknown.")
    print("\nFallback (authoritative, 5 seconds, no code):")
    print("  Right-click the OneDrive cloud icon in the tray -> Settings -> Account.")
    print("  It shows e.g. '105.2 GB used of 1,024 GB'. Tell Claude that number and it gets")
    print("  pinned as a declared constant, clearly labelled as user-declared, not probed.")
