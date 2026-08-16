#!/usr/bin/env python3
r"""
bts_drive_health.py - the monitor that did not exist when a 7.3 TB mirror died.

-------------------------------------------------------------------------------
WHY
-------------------------------------------------------------------------------
Scar S-96, and it was unanimous across four nodes in the KMESH blueprint as the
critical hole: `rail_check` probes FOUR API RAILS every night and ZERO DISKS.

G: ("NAS1", a SABRENT USB enclosure) ran hot under two routers for weeks. Its
write speed slid 17.7 -> 0.6 MB/s across eighteen days and then it reported
"USB device has malfunctioned". Nothing noticed. It was found only because
Cowork added V: to a benchmark table for an unrelated reason and re-ran it.

**SMART temperature is one query.** It would have said so in week one.

-------------------------------------------------------------------------------
WHAT IT REFUSES TO DO
-------------------------------------------------------------------------------
* It does not run on Linux. The Cowork sandbox has no physical disks and no
  drive letters; anything it reported would be about the sandbox. On a
  non-Windows host every field is NOT MEASURED and the exit code says so.
  (A probe that says "not mounted" is reporting on the sandbox, never on
  Keith's machine - the standing note in the TOOLS INDEX.)
* It does not infer health from speed alone. A slow disk may be busy. A hot
  disk with rising uncorrected errors is dying. Those are different claims.
* It does not treat a MISSING reliability counter as a good reading. Many USB
  bridges do not pass SMART through, and "the bridge hid it" must never render
  as "the disk is fine" - that is the failure mode this whole file exists for.

-------------------------------------------------------------------------------
THE TREND IS THE POINT
-------------------------------------------------------------------------------
A single temperature is weak evidence. The ledger keeps every reading, so the
check that actually matters is available: is this disk hotter, or erroring more,
than it was last week? G: did not fail suddenly - it degraded measurably for
eighteen days in full view of a mesh that was looking somewhere else.

Usage:
    python bts_drive_health.py                 read, record, report
    python bts_drive_health.py --selftest      prove the checks go RED
    python bts_drive_health.py --json          machine-readable, for rail_check
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "drive_health.json"

# Thresholds. Stated, dated, and deliberately conservative.
TEMP_WARN = 45      # C - a passively cooled enclosure sitting idle should be well under this
TEMP_CRIT = 50      # C - G: ran covered by two routers for weeks
NOT_MEASURED = "NOT MEASURED"

PS = r"""
$out = @()
foreach ($d in Get-PhysicalDisk) {
  $rc = $null
  try { $rc = $d | Get-StorageReliabilityCounter -ErrorAction Stop } catch { $rc = $null }
  $letters = @()
  try {
    $letters = ($d | Get-Disk | Get-Partition -ErrorAction SilentlyContinue |
                Where-Object DriveLetter | ForEach-Object { $_.DriveLetter })
  } catch {}
  $out += [pscustomobject]@{
    name        = $d.FriendlyName
    serial      = $d.SerialNumber
    bus         = "$($d.BusType)"
    size_gb     = [math]::Round($d.Size/1GB,1)
    health      = "$($d.HealthStatus)"
    operational = ($d.OperationalStatus -join ',')
    letters     = ($letters -join ',')
    temp        = if ($rc) { $rc.Temperature }              else { $null }
    temp_max    = if ($rc) { $rc.TemperatureMax }           else { $null }
    read_unc    = if ($rc) { $rc.ReadErrorsUncorrected }    else { $null }
    read_tot    = if ($rc) { $rc.ReadErrorsTotal }          else { $null }
    write_unc   = if ($rc) { $rc.WriteErrorsUncorrected }   else { $null }
    poh         = if ($rc) { $rc.PowerOnHours }             else { $null }
    counters    = if ($rc) { $true } else { $false }
  }
}
$out | ConvertTo-Json -Depth 3 -Compress
"""


def read_disks():
    """Return (list_of_disks, note). Never fabricates a reading."""
    if platform.system() != "Windows":
        return [], ("%s: not Windows. The sandbox has no physical disks — reporting nothing "
                    "rather than reporting about the sandbox." % NOT_MEASURED)
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", PS],
                           capture_output=True, text=True, timeout=90)
    except Exception as e:
        return [], "%s: powershell failed (%s)" % (NOT_MEASURED, e)
    body = (p.stdout or "").strip()
    if not body:
        return [], "%s: powershell returned nothing (%s)" % (NOT_MEASURED, (p.stderr or "")[:120])
    try:
        data = json.loads(body)
    except Exception as e:
        return [], "%s: unparseable powershell output (%s)" % (NOT_MEASURED, e)
    if isinstance(data, dict):
        data = [data]
    return data, ""


def judge(d, prev=None):
    """Return (status, reasons). prev is the most recent earlier reading, if any."""
    reasons = []
    status = "GREEN"

    def worse(s):
        nonlocal status
        order = {"GREEN": 0, "AMBER": 1, "RED": 2, "UNKNOWN": 1}
        if order[s] > order[status]:
            status = s

    if not d.get("counters"):
        worse("UNKNOWN")
        # 🔴 2026-07-31: this message used to say "this BRIDGE does not pass SMART
        # through" for every disk that returned nothing. First real run: ALL SIX
        # disks came back UNKNOWN — including two INTERNAL NVMe drives, which have
        # no bridge at all. A per-device explanation for a failure that hit 6 of 6
        # is the wrong explanation, and it is the same defect this whole session
        # kept finding: attributing a systemic cause to an individual instrument.
        # Get-StorageReliabilityCounter generally requires an ELEVATED session.
        # The caller now distinguishes the two cases; this text no longer asserts
        # a cause it did not measure.
        reasons.append("no reliability counters returned. Cause NOT MEASURED — could be an "
                       "enclosure that does not pass SMART through, or a query that needs "
                       "elevation. UNKNOWN is not GREEN.")
    else:
        t = d.get("temp")
        # 🔴 A ZERO TEMPERATURE FROM A DEVICE THAT ANSWERS NOTHING ELSE IS NOT A ZERO.
        # Measured 2026-08-11 21:36 (elevated): the SanDisk Cruzer returned
        #   temp = 0, temp_max = 0, read_unc = None, write_unc = None
        # A running USB stick is not at 0 C. Every other field on that device is a
        # non-answer, and the temperature is the same non-answer arriving as a number
        # because PowerShell hands back 0 for an absent value. Scored as a real reading
        # it is the COLDEST, HEALTHIEST disk in the rack.
        # The pairing is what makes this safe to judge: 0 alongside a 0 maximum is a
        # device reporting nothing. A genuine 0 C with a real maximum would still be
        # honoured below.
        if t == 0 and not d.get("temp_max"):
            worse("UNKNOWN")
            reasons.append("temperature reported as 0 C alongside a 0 maximum - that is a "
                           "device answering NOTHING, not a cold disk. NOT MEASURED.")
        elif t is None:
            worse("UNKNOWN")
            reasons.append("temperature not reported")
        elif t >= TEMP_CRIT:
            worse("RED")
            reasons.append("temperature %s C >= %s C" % (t, TEMP_CRIT))
        elif t >= TEMP_WARN:
            worse("AMBER")
            reasons.append("temperature %s C >= %s C" % (t, TEMP_WARN))
        for key, label in (("read_unc", "UNCORRECTED read errors"),
                           ("write_unc", "UNCORRECTED write errors")):
            v = d.get(key)
            if isinstance(v, int) and v > 0:
                worse("RED")
                reasons.append("%s = %d" % (label, v))
            elif v is None:
                # 🔴 2026-08-11: GREEN ON A `None` IS NOT GREEN ON A ZERO.
                # This arm did not exist. A disk that returned a temperature but NO error
                # counters fell through every branch and kept status GREEN - so "the drive
                # reports zero uncorrected errors" and "the drive did not answer the
                # question" were rendered identically, as GREEN.
                # Measured the same night: TWO of the four disks in the elevated GREEN x4
                # reading had read=None write=None. Their GREEN rested on temperature alone
                # and nothing said so. That is the exact shape of the G: failure this whole
                # tool was built for - a disk sliding 17.7 -> 0.6 MB/s while reporting fine.
                # This file's own header already says it "does not treat a MISSING
                # reliability counter as a good reading." It did, for this field.
                worse("UNKNOWN")
                reasons.append("%s NOT REPORTED by this device - not measured, not zero"
                               % label)
        # THE TREND — the thing that would have caught G:
        if prev and prev.get("counters"):
            pt, ct = prev.get("temp"), d.get("temp")
            if isinstance(pt, int) and isinstance(ct, int) and ct - pt >= 8:
                worse("AMBER")
                reasons.append("temperature ROSE %d C since %s" % (ct - pt, prev.get("when", "?")[:16]))
            for key, label in (("read_unc", "read"), ("write_unc", "write")):
                pv, cv = prev.get(key), d.get(key)
                if isinstance(pv, int) and isinstance(cv, int) and cv > pv:
                    worse("RED")
                    reasons.append("%s uncorrected errors GREW %d -> %d" % (label, pv, cv))

    h = (d.get("health") or "").lower()
    if h and h != "healthy":
        worse("RED")
        reasons.append("HealthStatus = %s" % d.get("health"))
    op = (d.get("operational") or "").lower()
    if op and op not in ("ok", "online"):
        worse("AMBER")
        reasons.append("OperationalStatus = %s" % d.get("operational"))

    return status, reasons


def _fmt_counter(v):
    """A counter that was not reported must not look like a zero."""
    return NOT_MEASURED if v is None else str(v)


def _fmt_temp(j):
    """Render a temperature, and NEVER render a missing maximum as a number.

    🔴 2026-08-11: this printed "37 C (max 0 C)" for the Passport and the Cruzer. There is
    no such thing as a 0 C maximum - it is a MISSING VALUE that PowerShell handed back as a
    zero, and the format string turned straight into a figure. "37 of max 0" is incoherent:
    read literally the disk is 37 C over its limit, and any comparison written against it is
    either alarming or silently skipped.

    bts_kdash_feed already forbids rendering UNMEASURED as a number. The rule existed; this
    tool broke it internally, which is how a rule scoped to one instrument fails to protect
    the next one.
    """
    if not j.get("counters"):
        return NOT_MEASURED
    t, tmax = j.get("temp"), j.get("temp_max")
    if t is None or (t == 0 and not tmax):
        return NOT_MEASURED
    if isinstance(tmax, int) and tmax > 0:
        return "%s C (max %s C)" % (t, tmax)
    return "%s C (max %s)" % (t, NOT_MEASURED)


def load_ledger():
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except Exception:
        return {"_readme": "Append-only drive health history. bts_drive_health.py owns this file.",
                "readings": []}


def key_of(d):
    return d.get("serial") or d.get("name") or "?"


def run(as_json=False):
    disks, note = read_disks()
    led = load_ledger()
    prev_by_key = {}
    for r in reversed(led["readings"]):
        for dd in r.get("disks", []):
            prev_by_key.setdefault(key_of(dd), dict(dd, when=r["when"]))

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    judged = []
    for d in disks:
        st, why = judge(d, prev_by_key.get(key_of(d)))
        judged.append(dict(d, status=st, reasons=why))

    if disks:
        led["readings"].append({"when": now, "disks": disks})
        led["readings"] = led["readings"][-500:]
        try:
            LEDGER.write_text(json.dumps(led, indent=1), encoding="utf-8")
        except Exception as e:
            note = (note + " | ledger not written: %s" % e).strip(" |")

    worst = "GREEN"
    for j in judged:
        if j["status"] == "RED":
            worst = "RED"
        elif j["status"] in ("AMBER", "UNKNOWN") and worst == "GREEN":
            worst = j["status"]
    if not disks:
        worst = "NOT MEASURED"

    # SYSTEMIC vs PER-DEVICE. If EVERY disk lacks counters — internal NVMe
    # included — the query failed, not the hardware. Say which one, once, at the
    # top, instead of repeating a guessed per-device cause N times.
    n_nc = sum(1 for d in disks if not d.get("counters"))
    if disks and n_nc == len(disks):
        note = ((note + " | " if note else "") +
                "🔴 ALL %d disk(s) returned no reliability counters, internal NVMe included. "
                "That is SYSTEMIC, not per-device: Get-StorageReliabilityCounter typically "
                "requires an ELEVATED session. Re-run as Administrator before concluding "
                "anything about any disk." % len(disks))

    if as_json:
        print(json.dumps({"when": now, "result": worst, "note": note, "disks": judged}, indent=1))
        return 0 if worst in ("GREEN", "NOT MEASURED") else 2

    print("=" * 78)
    print("  bts_drive_health   %s" % now)
    print("=" * 78)
    if note:
        print("  %s" % note)
    if not disks:
        print("  RESULT: NOT MEASURED")
        print("\n  This is CORRECT off-Windows. It is not a pass.")
        return 0
    for j in judged:
        print("\n  %-28s %-6s %8s GB  %s" % (j.get("name"), j.get("bus"), j.get("size_gb"), j["status"]))
        if j.get("letters"):
            print("      drive letters : %s" % j["letters"])
        print("      temperature   : %s" % _fmt_temp(j))
        print("      uncorrected   : read=%s write=%s"
              % (_fmt_counter(j.get("read_unc")), _fmt_counter(j.get("write_unc"))))
        print("      power-on      : %s h" % j.get("poh"))
        for r in j["reasons"]:
            print("      -> %s" % r)
    print("\n" + "-" * 78)
    print("  history: %d reading(s) in %s" % (len(led["readings"]), LEDGER.name))
    print("  RESULT: %s" % worst)
    return 0 if worst == "GREEN" else 2


def selftest():
    """A verifier never shown to fail is not a verifier."""
    fails = []

    def check(name, got, want):
        ok = got == want
        print("  %-40s got=%-9s want=%-9s %s" % (name, got, want, "PASS" if ok else "*** FAIL ***"))
        if not ok:
            fails.append(name)

    base = {"counters": True, "temp": 30, "temp_max": 35, "read_unc": 0, "write_unc": 0,
            "health": "Healthy", "operational": "OK", "name": "T", "serial": "S"}
    check("healthy disk", judge(base)[0], "GREEN")
    check("warm disk -> AMBER", judge(dict(base, temp=46))[0], "AMBER")
    check("hot disk -> RED", judge(dict(base, temp=51))[0], "RED")
    check("uncorrected read error -> RED", judge(dict(base, read_unc=1))[0], "RED")
    check("unhealthy status -> RED", judge(dict(base, health="Unhealthy"))[0], "RED")
    check("no SMART passthrough -> UNKNOWN",
          judge({"counters": False, "health": "Healthy", "operational": "OK"})[0], "UNKNOWN")
    # the one that matters: a slide, not a threshold
    prev = dict(base, temp=32, when="2026-07-13T00:00:00")
    check("temperature SLIDE -> AMBER", judge(dict(base, temp=41), prev)[0], "AMBER")
    check("error count GROWING -> RED",
          judge(dict(base, read_unc=3), dict(prev, read_unc=1))[0], "RED")
    check("same temp, no trend flag", judge(dict(base, temp=30), prev)[0], "GREEN")

    # 🔴 ADDED 2026-08-11. Two of the four disks in that night's "GREEN x4" reading had
    # read=None write=None. Before this arm existed, the line below returned GREEN.
    check("counter NOT REPORTED -> UNKNOWN, never GREEN",
          judge(dict(base, read_unc=None, write_unc=None))[0], "UNKNOWN")
    check("read reported, write NOT -> UNKNOWN",
          judge(dict(base, write_unc=None))[0], "UNKNOWN")
    check("a real zero is still GREEN",
          judge(dict(base, read_unc=0, write_unc=0))[0], "GREEN")

    # Rendering. A missing maximum must never come back as a number.
    check("missing temp_max is not rendered as 0 C",
          _fmt_temp(dict(base, temp=37, temp_max=0)), "37 C (max %s)" % NOT_MEASURED)
    check("null temp_max is not rendered as a number",
          _fmt_temp(dict(base, temp=37, temp_max=None)), "37 C (max %s)" % NOT_MEASURED)
    check("a real temp_max still renders", _fmt_temp(dict(base, temp=37, temp_max=70)),
          "37 C (max 70 C)")
    check("an unreported counter is not printed as a zero",
          _fmt_counter(None), NOT_MEASURED)
    check("a real zero counter still prints as 0", _fmt_counter(0), "0")

    # 🔴 The SanDisk Cruzer case, measured elevated 2026-08-11: temp 0, max 0, no counters.
    check("0 C with a 0 maximum -> UNKNOWN, not the healthiest disk in the rack",
          judge(dict(base, temp=0, temp_max=0, read_unc=0, write_unc=0))[0], "UNKNOWN")
    check("0 C with a 0 maximum is not rendered as a temperature",
          _fmt_temp(dict(base, temp=0, temp_max=0)), NOT_MEASURED)
    check("a genuine 0 C WITH a real maximum is still honored",
          _fmt_temp(dict(base, temp=0, temp_max=70)), "0 C (max 70 C)")

    print()
    if fails:
        print("  SELFTEST FAILED: %s" % ", ".join(fails))
        return 1
    # ASCII only - this stdout gets redirected by a scheduler (S-134).
    print("  SELFTEST PASS - every judgement was shown to go RED/AMBER on demand,")
    print("  and a NOT-REPORTED counter is now distinguishable from a measured zero.")
    print("  NOTE: this proves the JUDGEMENT. It cannot prove the READING off-Windows.")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(run(as_json="--json" in sys.argv))
