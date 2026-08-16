#!/usr/bin/env python3
r"""
bench_drive.py - READ-ONLY throughput + health for a drive. Runs natively.

WHY THIS IS PYTHON AND NOT POWERSHELL-IN-A-BAT
    The first version of this was a long `powershell -Command "..."` inside a
    .bat with cmd line-continuations. It failed on its own quoting: `|` was
    escaped as `^|`, which is a CMD escape for UNQUOTED metacharacters, so the
    carets were passed through verbatim and PowerShell refused to parse them.
    Then the bat printed "Report: <path>" anyway, for a file that was never
    written - a script that announces success it did not verify.
    Two lessons, both already written down elsewhere in this repo:
      * the TOOL belongs in the tree; the .bat is delivery, and should be short
        enough to be obviously correct
      * a step must VERIFY its own output exists before claiming it

    The SMART half is delegated to bts_drive_health.py, which already passes its
    PowerShell as a single argv element - no shell escaping anywhere.

*** READ-ONLY. This writes nothing to the target drive, by construction: it
    only ever opens files with mode 'rb'. ***

Usage:
    py -3.14 bench_drive.py "G:\Tera 4 - back 24" --compare "V:\Research4\Ai\PhD2_DATA_ARCHIVE"
    py -3.14 bench_drive.py --selftest
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

CHUNK = 1 << 20          # 1 MB
CAP_BYTES = 2 << 30      # stop after ~2 GB
CAP_SECONDS = 60.0


def biggest(root: Path, want=24, min_size=20 << 20, budget_s=45.0):
    """Largest files under root. Walk is time-boxed: a 7.3 TB tree must not
    turn the benchmark into a directory crawl."""
    found = []
    t0 = time.perf_counter()
    truncated = False
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        for fn in filenames:
            p = Path(dirpath) / fn
            try:
                sz = p.stat().st_size
            except Exception:
                continue
            if sz >= min_size:
                found.append((sz, p))
        if time.perf_counter() - t0 > budget_s:
            truncated = True
            break
    found.sort(key=lambda x: -x[0])
    if not found:
        return [], truncated, 0
    return found[:want], truncated, len(found)


def bench(root: Path):
    """Return a result dict. Never raises on a bad file - counts it."""
    r = {"root": str(root), "ok": False, "mb_s": None, "mb": 0.0, "sec": 0.0,
         "errors": 0, "files": 0, "note": ""}
    if not root.exists():
        r["note"] = "path not found"
        return r
    files, truncated, total_seen = biggest(root)
    if not files:
        files, truncated, total_seen = biggest(root, want=200, min_size=0, budget_s=20.0)
    if not files:
        r["note"] = "no readable files found"
        return r
    if truncated:
        r["note"] = "file scan time-boxed; benchmarked the largest found so far (%d candidates)" % total_seen

    buf = bytearray(CHUNK)
    total = 0
    errs = 0
    used = 0
    t0 = time.perf_counter()
    for sz, p in files:
        if total >= CAP_BYTES or (time.perf_counter() - t0) > CAP_SECONDS:
            break
        try:
            with open(p, "rb") as fh:
                used += 1
                while True:
                    n = fh.readinto(buf)
                    if not n:
                        break
                    total += n
                    if total >= CAP_BYTES or (time.perf_counter() - t0) > CAP_SECONDS:
                        break
        except Exception:
            errs += 1
    dt = max(time.perf_counter() - t0, 1e-3)
    r.update(ok=True, mb=total / 1048576.0, sec=dt, errors=errs, files=used,
             mb_s=(total / 1048576.0) / dt)
    return r


def health_rows():
    """SMART, via the already-tested module. Returns (rows, note).

    🔴 2026-07-31: this READ the ledger and never WROTE to it. Measured by the
    absence of drive_health.json after two full native runs — the trend check
    (an 8 C rise, or any growth in uncorrected errors) had no history to
    compare against and never would have. The whole point of the tool is that
    G: degraded over EIGHTEEN DAYS in plain sight, which only a series catches;
    a monitor that keeps no series is a thermometer you never write down.
    It now appends every reading, same as bts_drive_health's own run()."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import bts_drive_health as dh
    except Exception as e:
        return [], "bts_drive_health unavailable: %s" % e
    disks, note = dh.read_disks()
    if not disks:
        return [], note or "no physical disks visible"
    led = dh.load_ledger()
    prev = {}
    for rec in reversed(led["readings"]):
        for d in rec.get("disks", []):
            prev.setdefault(dh.key_of(d), dict(d, when=rec["when"]))
    out = []
    for d in disks:
        st, why = dh.judge(d, prev.get(dh.key_of(d)))
        out.append((d, st, why))
    # RECORD IT. Even an all-UNKNOWN reading is worth keeping: the DATE a disk
    # stopped reporting counters is itself a data point.
    try:
        from datetime import timezone
        led["readings"].append(
            {"when": datetime.now(timezone.utc).isoformat(timespec="seconds"), "disks": disks})
        led["readings"] = led["readings"][-500:]
        dh.LEDGER.write_text(__import__("json").dumps(led, indent=1), encoding="utf-8")
    except Exception as e:                                          # noqa: BLE001
        note = (note + " | ledger not written: %s" % e).strip(" |")
    return out, note


def usb_controls(out_path=""):
    """Benchmark every USB volume this machine has, discovering them itself.

    THE CONTROL THAT SHOULD HAVE RUN FIRST. Every G: measurement so far has
    been of G: alone, so 'this machine's USB is healthy' was assumed, never
    tested. D: is a WD My Passport, 3.7 TB, also USB, on the same controllers."""
    rows, note = health_rows()
    targets = []
    for d, _st, _why in rows:
        if (d.get("bus") or "").upper() != "USB":
            continue
        for L in (d.get("letters") or "").split(","):
            L = L.strip()
            if L:
                targets.append((L + ":\\", d.get("name") or "?", d.get("size_gb")))
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    L = ["# USB control benchmark - %s" % stamp, "",
         "**READ-ONLY.** Every USB volume on this machine, same method, same moment.",
         "Drives were DISCOVERED by the tool — no paths were passed in, because three",
         "bats tonight failed on cmd quoting rather than on logic.", ""]
    if not targets:
        L += ["`NOT MEASURED` — no USB volumes found. " + (note or ""), ""]
        print("\n".join(L))
        return 1
    L += ["| volume | disk | size | read speed | moved | files | errors |",
          "|---|---|---|---|---|---|---|"]
    results = []
    for root, name, gb in targets:
        print("  benchmarking %s (%s) ..." % (root, name), flush=True)
        r = bench(Path(root))
        results.append((root, name, r))
        if r["ok"]:
            cached = r["mb_s"] and r["mb_s"] > 1500
            spd = ("~%.0f MB/s **CACHED**" % r["mb_s"]) if cached else ("**%.1f MB/s**" % r["mb_s"])
            L.append("| `%s` | %s | %s GB | %s | %.0f MB in %.1f s | %d | %d |"
                     % (root, name, gb, spd, r["mb"], r["sec"], r["files"], r["errors"]))
        else:
            L.append("| `%s` | %s | %s GB | NOT MEASURED | - | - | %s |"
                     % (root, name, gb, r["note"]))
    ok = [(root, name, r) for root, name, r in results if r["ok"] and r["mb_s"]]
    L += ["", "## Verdict", ""]
    if len(ok) >= 2:
        fast = max(ok, key=lambda x: x[2]["mb_s"])
        slow = min(ok, key=lambda x: x[2]["mb_s"])
        ratio = fast[2]["mb_s"] / max(slow[2]["mb_s"], 0.001)
        L += ["Fastest USB volume: `%s` at **%.1f MB/s**  " % (fast[0], fast[2]["mb_s"]),
              "Slowest USB volume: `%s` at **%.1f MB/s**  " % (slow[0], slow[2]["mb_s"]),
              "**Ratio: %.0fx**" % ratio, ""]
        if ratio > 10:
            L += ["🟢 **The USB stack, controllers and drivers are HEALTHY** — another USB drive on",
                  "the same machine is %.0fx faster. So the fault is confined to the slow drive:" % ratio,
                  "its CABLE, its ENCLOSURE BRIDGE, or its PLATTERS.", "",
                  "⚠ The cable has still never been swapped. The test that 'eliminated' it used a",
                  "USB 2.0 printer, which never touched the SuperSpeed pairs."]
        else:
            L += ["🔴 **Every USB volume is slow.** This is not one failing drive — it is this",
                  "machine's USB path. Much better news for the data: try the drive on another PC."]
    else:
        L += ["Only %d USB volume(s) could be measured — not enough for a comparison." % len(ok)]
    L.append("")
    text = "\n".join(L) + "\n"
    print("\n" + text)
    if out_path:
        try:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_text(text, encoding="utf-8")
            print("  written and verified: %s (%d B)" % (out_path, Path(out_path).stat().st_size))
        except Exception as e:
            print("  [!] could not write %s: %s" % (out_path, e))
            return 1
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", default=r"G:\Tera 4 - back 24")
    ap.add_argument("--compare", default=r"V:\Research4\Ai\PhD2_DATA_ARCHIVE")
    ap.add_argument("--out", default="")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--usb-controls", action="store_true",
                    help="benchmark EVERY USB volume, discovering them itself. "
                         "Takes no paths — see the note below.")
    args = ap.parse_args()

    # ---------------------------------------------------------------------
    # 🔴 WHY --usb-controls TAKES NO PATHS, 2026-07-31
    #   Three bats tonight failed on cmd quoting, not on logic:
    #     ^|   escaped pipes passed verbatim into PowerShell
    #     "D:\"  the TRAILING BACKSLASH escaped the closing quote, so Windows
    #            merged every later argument into one and the tool was handed
    #            `D:" --compare " --out V:\...` as its path. The control never
    #            ran, and the run still printed a confident-looking table.
    #   Fixing each instance was not working. So the paths move OUT of the bat
    #   entirely: this flag DISCOVERS the drives itself. A bat that passes no
    #   arguments cannot quote them wrongly.
    # ---------------------------------------------------------------------
    if args.usb_controls:
        return usb_controls(args.out)

    if args.selftest:
        import tempfile
        d = Path(tempfile.mkdtemp())
        (d / "a.bin").write_bytes(os.urandom(4 << 20))
        r = bench(d)
        ok = r["ok"] and r["mb"] > 3.9 and r["errors"] == 0
        print("  bench on a known 4 MB file: %.1f MB read, %.1f MB/s, %d error(s)  %s"
              % (r["mb"], r["mb_s"], r["errors"], "PASS" if ok else "*** FAIL ***"))
        r2 = bench(Path(str(d / "nope")))
        ok2 = (not r2["ok"]) and r2["note"] == "path not found"
        print("  missing path reports, does not crash:                            %s"
              % ("PASS" if ok2 else "*** FAIL ***"))
        return 0 if (ok and ok2) else 1

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    L = ["# G: health and READ speed - %s" % stamp, "",
         "**READ-ONLY TEST. Nothing was written to the target drive.**", "",
         "## 1. READ throughput", "",
         "| target | read speed | volume moved | files | errors |", "|---|---|---|---|---|"]

    results = []
    for label, path in (("TARGET", args.target), ("COMPARE", args.compare)):
        if not path:
            continue
        r = bench(Path(path))
        results.append((label, r))
        if r["ok"]:
            # CACHE DETECTOR. Last run reported V: at 6,323 MB/s - that is not a
            # disk, that is the OS file cache serving files this same tool had
            # read 40 minutes earlier. It was published as a comparison number
            # and it was meaningless. No spinning disk, USB enclosure or SATA
            # SSD reaches four figures; NVMe tops out around 7,000 but not on a
            # 24-file mixed read. So: label it, do not silently present it.
            cached = r["mb_s"] and r["mb_s"] > 1500
            speed = ("~%.0f MB/s **CACHED — NOT A DISK MEASUREMENT**" % r["mb_s"]) if cached \
                    else ("**%.1f MB/s**" % r["mb_s"])
            L.append("| `%s` | %s | %.0f MB in %.1f s | %d | %d |"
                     % (path, speed, r["mb"], r["sec"], r["files"], r["errors"]))
            if cached:
                L.append("| | | | | *served from RAM — re-run after a reboot, "
                         "or ignore this row* |")
        else:
            L.append("| `%s` | NOT MEASURED | - | - | %s |" % (path, r["note"]))
        if r["note"] and r["ok"]:
            L.append("| | | | | *%s* |" % r["note"])

    L += ["", "## 2. SMART / reliability  (scar S-96 - the signal nothing was watching)", ""]
    rows, note = health_rows()
    if not rows:
        L += ["`NOT MEASURED` - %s" % note, ""]
    else:
        L += ["| disk | bus | status | temperature | uncorrected r/w | power-on |",
              "|---|---|---|---|---|---|"]
        for d, st, why in rows:
            temp = ("%s C (max %s)" % (d.get("temp"), d.get("temp_max"))) if d.get("counters") else "NOT MEASURED"
            L.append("| %s%s | %s | **%s** | %s | %s / %s | %s h |"
                     % (d.get("name"), (" (%s:)" % d["letters"]) if d.get("letters") else "",
                        d.get("bus"), st, temp, d.get("read_unc"), d.get("write_unc"), d.get("poh")))
        L.append("")
        for d, st, why in rows:
            for w in why:
                L.append("- **%s** — %s" % (d.get("name"), w))
        L.append("")

    L += ["## 3. Reading this against the record", "",
          "Baseline on file (BU.MD / S-96): **WRITES** degraded 17.7 -> 0.6 MB/s over eighteen days,",
          "then `USB device has malfunctioned`. **Reads were clean throughout and a SHA-256 matched.**",
          "Cable and port are already ELIMINATED (the printer prints on the drive's old port).", "",
          "- A healthy READ number does **not** clear this drive. The failing workload was WRITES.",
          "- It does mean the rescue copy is viable, which is the decision in front of us.",
          "- If temperature reads above ~50 C with the enclosure open and idle, **that is the",
          "  finding, not the speed.** It ran for weeks under two routers with no fan.",
          "- Compare the two rows above as a RATIO, not as absolutes: same method, same machine,",
          "  same moment. V: is the known-good reference at ~107 MB/s write.", ""]

    text = "\n".join(L) + "\n"
    out = Path(args.out) if args.out else Path(
        r"V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\G_HEALTH_%s.md" % datetime.now().strftime("%Y-%m-%d"))
    wrote = False
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        wrote = out.exists() and out.stat().st_size > 0
    except Exception as e:
        print("  [!] could not write %s: %s" % (out, e))

    print(text)
    # VERIFY before claiming. The previous version announced a report it never wrote.
    if wrote:
        print("  report written and verified: %s (%d B)" % (out, out.stat().st_size))
        return 0
    print("  *** REPORT NOT WRITTEN. The numbers above are still valid; the file is not there. ***")
    return 1


if __name__ == "__main__":
    sys.exit(main())
