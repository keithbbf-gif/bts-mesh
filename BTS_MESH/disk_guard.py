#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""disk_guard.py - name a disk by what it IS, never by where it happens to be. 2026-08-12.

PLM-31, a LIVE SAFETY DEFECT
----------------------------
A staged bat ended with:

    "STILL DO NOT initialize, format, or create a volume on Disk 0. The 5404 GB
     'Unallocated' is your NTFS volume, unreadable at 512-byte sectors. It is not
     empty space."

That was written when the 8 TB enumerated as Disk 0. **Disk 0 is now the WD_BLACK SN850X
- the C: boot drive.** Followed literally today, that instruction points a destructive
operation at the operating system.

  ==> DISK NUMBERS ARE ASSIGNED BY ENUMERATION ORDER AND CHANGE WHEN ANYTHING IS PLUGGED
      IN OR UNPLUGGED. SERIAL NUMBERS DO NOT.

It is the same defect class as the dated-handoff rot that bit this project four times: an
UNSTABLE IDENTIFIER standing in for a stable one. There the cost was reading the wrong
file; here it is `clean` on the boot disk.

WHY THIS IS A .py IN THE TREE AND NOT A WARNING IN A .bat
---------------------------------------------------------
The original guard lived in a Desktop `.bat`, which by Keith's own rule is deleted after
one use. So the warning had a lifetime of one run while the hazard is permanent, and the
next session rewrote the bat from prose that still said "Disk 0". A durable hazard needs a
durable guard. **The bat is the delivery; the .py is the tool.**

THE PROTECTED SET IS DISCOVERED, NOT TYPED
------------------------------------------
The disk carrying the system volume is found at runtime. Hardcoding "protect the SN850X"
would be the same mistake one level up - it would be wrong the day Keith changes boot
drives, and it would be wrong silently.

USAGE
    py -3.14 disk_guard.py                    # the map: number <-> serial <-> letters
    py -3.14 disk_guard.py --resolve SERIAL   # which Disk number is that serial, right now
    py -3.14 disk_guard.py --selftest         # negative controls
"""
from __future__ import annotations

import json
import subprocess
import sys

PS = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]

_QUERY = r"""
$sys = (Get-Partition | Where-Object { $_.DriveLetter -eq $env:SystemDrive.Substring(0,1) }).DiskNumber
Get-Disk | ForEach-Object {
  $n = $_.Number
  $letters = (Get-Partition -DiskNumber $n -ErrorAction SilentlyContinue |
              Where-Object { $_.DriveLetter } | ForEach-Object { "$($_.DriveLetter):" }) -join ","
  [PSCustomObject]@{
    number     = $n
    serial     = ($_.SerialNumber   -replace '\s','')
    name       = $_.FriendlyName
    size_gb    = [math]::Round($_.Size / 1GB, 1)
    bus        = $_.BusType
    partstyle  = $_.PartitionStyle
    letters    = $letters
    is_system  = ($n -eq $sys)
    is_boot    = $_.IsBoot
  }
} | ConvertTo-Json -Depth 3
"""


def inventory():
    """Return (disks, error). NEVER fabricates a disk and never guesses a serial."""
    try:
        r = subprocess.run(PS + [_QUERY], capture_output=True, text=True,
                           errors="replace", timeout=90)
    except Exception as e:                                          # noqa: BLE001
        return [], "powershell did not run: %s" % e
    if r.returncode != 0:
        return [], (r.stderr or "").strip()[:200]
    out = (r.stdout or "").strip()
    if not out:
        return [], "no output from Get-Disk"
    try:
        data = json.loads(out)
    except ValueError as e:
        return [], "unparseable Get-Disk output: %s" % e
    return (data if isinstance(data, list) else [data]), ""


def protected(disks):
    """The disks that must never be initialized, formatted or cleaned.

    DISCOVERED, not typed: whatever currently carries the system volume. A hardcoded
    model or serial would be wrong the day the boot drive changes, and wrong silently."""
    return [d for d in disks if d.get("is_system") or d.get("is_boot")]


def resolve(serial, disks):
    """Serial -> the disk NUMBER it occupies right now.

    Returns (number, note). REFUSES on absent or ambiguous, because 'I could not find it'
    must never be reported as a number that some later step will act on."""
    want = (serial or "").strip().upper()
    if not want:
        return None, "no serial given"
    hits = [d for d in disks if (d.get("serial") or "").upper() == want]
    if not hits:
        return None, ("serial %s is NOT PRESENT on this machine. Do not proceed - an "
                      "absent target is exactly when a disk-number instruction hits the "
                      "wrong disk." % want)
    if len(hits) > 1:
        return None, "serial %s matches %d disks - ambiguous, refusing" % (want, len(hits))
    return hits[0]["number"], ""


def report() -> int:
    disks, err = inventory()
    print("=" * 78)
    print("  disk_guard - identity by SERIAL, never by disk number")
    print("=" * 78)
    if err:
        print("  NOT MEASURED: %s" % err)
        print("  (This is CORRECT off-Windows. It is not a pass, and it is not a")
        print("   licence to fall back on disk numbers.)")
        return 2
    print("  %-4s %-22s %-20s %9s %-8s %-8s %s"
          % ("#", "serial", "name", "GB", "bus", "letters", "role"))
    print("  " + "-" * 74)
    prot = {d["number"] for d in protected(disks)}
    for d in sorted(disks, key=lambda x: x["number"]):
        role = "*** PROTECTED - SYSTEM ***" if d["number"] in prot else ""
        print("  %-4s %-22s %-20s %9s %-8s %-8s %s"
              % (d["number"], (d.get("serial") or "NOT REPORTED")[:22],
                 (d.get("name") or "?")[:20], d.get("size_gb"),
                 d.get("bus"), d.get("letters") or "-", role))
    print()
    print("  DO NOT initialize, format, clean or create a volume on:")
    for d in protected(disks):
        print("    Disk %s  serial %s  (%s)  <- THE SYSTEM DISK, TODAY"
              % (d["number"], d.get("serial"), d.get("name")))
    print()
    print("  The disk NUMBER above is true only for this boot. Quote the SERIAL in any")
    print("  instruction that outlives this session - PLM-31 exists because a warning")
    print("  said 'Disk 0' and Disk 0 became the boot drive.")
    return 0


def selftest() -> int:
    """A guard never shown to REFUSE is not a guard."""
    fake = [
        {"number": 0, "serial": "AAA111", "name": "boot", "size_gb": 931.0,
         "bus": "NVMe", "letters": "C:", "is_system": True, "is_boot": True},
        {"number": 1, "serial": "BBB222", "name": "data", "size_gb": 447.0,
         "bus": "NVMe", "letters": "V:", "is_system": False, "is_boot": False},
        {"number": 2, "serial": "BBB222", "name": "clone", "size_gb": 447.0,
         "bus": "USB", "letters": "", "is_system": False, "is_boot": False},
    ]
    checks = []
    n, note = resolve("BBB111", fake[:2])
    checks.append(("an ABSENT serial refuses, returning no number", n is None and note))
    n, note = resolve("BBB222", fake)
    checks.append(("an AMBIGUOUS serial refuses rather than picking one",
                   n is None and "ambiguous" in note))
    n, note = resolve("bbb222", fake[:2])
    checks.append(("a present serial resolves, case-insensitively", n == 1 and not note))
    checks.append(("the SYSTEM disk is protected by discovery, not by number",
                   [d["serial"] for d in protected(fake)] == ["AAA111"]))
    # The PLM-31 scenario itself: the same serial moves to a different number.
    moved = [dict(fake[1], number=0), dict(fake[0], number=1)]
    n, _ = resolve("BBB222", moved)
    checks.append(("a serial still resolves after the disk NUMBER changes", n == 0))
    checks.append(("and the system disk moves with it, still protected",
                   [d["serial"] for d in protected(moved)] == ["AAA111"]))
    print("=" * 78)
    print("  disk_guard --selftest")
    print("=" * 78)
    for label, good in checks:
        print("  %s  %s" % ("OK  " if good else "FAIL", label))
    bad = [l for l, g in checks if not g]
    print("SELFTEST PASS - it refuses on absent and ambiguous, and identity survives a "
          "renumbering." if not bad else "SELFTEST FAIL - %d check(s)." % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--resolve" in sys.argv:
        i = sys.argv.index("--resolve")
        serial = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
        disks, err = inventory()
        if err:
            print("NOT MEASURED: %s" % err)
            sys.exit(2)
        num, note = resolve(serial, disks)
        if num is None:
            print("REFUSED: %s" % note)
            sys.exit(1)
        print("serial %s is Disk %s RIGHT NOW (re-check before every destructive step)"
              % (serial, num))
        sys.exit(0)
    sys.exit(report())
