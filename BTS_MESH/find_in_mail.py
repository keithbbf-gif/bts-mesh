#!/usr/bin/env python3
"""
find_in_mail.py - search Keith's Thunderbird mail stores and EXTRACT the attachments.

WHY THIS EXISTS
  2026-08-02: looking for a draft response to Abraxas's Requests for Admission that Heather
  Gilley sent shortly before they were due. The Cowork sandbox caps a bash call at 45 s and the
  mail stores total ~20 GB - `imap.gmail.com/INBOX` alone is 8.1 GB. Every sandbox grep timed
  out. This runs natively, where there is no cap.

  It also answers a standing question that outranks the search itself: WERE OUR DISCOVERY
  RESPONSES EVER SERVED? If nothing went out, all 25 of Abraxas's RFAs are deemed admitted under
  12 O.S. 3236(A). A scan that reads every folder settles it either way - and a NEGATIVE result
  is a real finding here, not a failed search.

WHAT IT DOES
  Streams each mbox (never loads one into memory), splits on the mbox 'From ' separator, parses
  headers, filters, and writes any matching attachment to disk. Reports a dated table.

  🔴 A NEGATIVE IS REPORTED AS A MEASUREMENT, NOT AS SILENCE. The report always states how many
  bytes and messages were actually scanned per folder. "Not found" is only meaningful if you know
  the search actually looked - a scan that died early and printed nothing looks identical to a
  clean miss, and that is how people conclude a document does not exist when it does.

USAGE (native Windows - do NOT run this in the sandbox)
    py -3.14 find_in_mail.py --from heltonlawfirm --after 2026-01-01 --before 2026-05-01
    py -3.14 find_in_mail.py --body "requests? for admission" --extract
    py -3.14 find_in_mail.py --selftest
"""
from __future__ import annotations
import argparse, email, email.policy, email.utils, re, sys, time
from datetime import datetime, timezone
from pathlib import Path

TB   = Path(r"C:\Users\Papa\AppData\Roaming\Thunderbird\Profiles")
OUT  = Path(r"V:\Ai\Legal\MAIL_FIND")
SEP  = re.compile(rb"^From ", re.M)
SKIP = {".msf", ".dat", ".sqlite", ".json", ".js", ".db", ".log", ".ini", ".xpi", ".txt"}


def stores() -> list[Path]:
    out = []
    for prof in TB.glob("*"):
        for sub in ("ImapMail", "Mail"):
            d = prof / sub
            if not d.is_dir():
                continue
            for p in d.rglob("*"):
                if p.is_file() and p.suffix.lower() not in SKIP and p.stat().st_size > 4096:
                    out.append(p)
    return sorted(out, key=lambda p: -p.stat().st_size)


def _strip_envelope(p: bytes) -> bytes:
    """🔴 THE BUG THAT ATE THE FIRST RUN — 2026-08-02.

    SEP splits on b"^From " and DISCARDS the separator, so every chunk begins with the remainder
    of the mbox envelope line: `keith@4figs.com Mon Aug  2 ...`. That line has no colon, so
    email.message_from_bytes treats it as a malformed header, stops parsing, and returns a message
    with NO HEADERS AT ALL.

    The damage was silent and total: every hit printed `undated` with a blank sender and subject;
    every date filter was skipped because `dt` was None; `is_multipart()` was False so NO ATTACHMENT
    WAS EVER EXTRACTED; and the attachment-name pass could not match anything by construction.
    282,446 messages and 33 GB were read correctly and then thrown away at the parse.

    ⇒ Drop the envelope line before the parser sees it.
    """
    nl = p.find(b"\n")
    return p[nl + 1:] if nl != -1 else p


def messages(path: Path, chunk: int = 8 << 20):
    """Yield raw message bytes, envelope line removed. Streams; an 8 GB mbox never enters memory."""
    buf = b""
    with path.open("rb") as f:
        while True:
            blk = f.read(chunk)
            if not blk:
                break
            buf += blk
            parts = SEP.split(buf)
            buf = parts.pop() if parts else b""
            for p in parts:
                if p.strip():
                    yield _strip_envelope(p)
        if buf.strip():
            yield _strip_envelope(buf)


def hdr(msg, name: str) -> str:
    try:
        v = msg.get(name, "")
        return str(v) if v else ""
    except Exception:
        return ""


def _tee(msg: str) -> None:
    """Print AND log. 2026-08-02: the first run produced an empty MAIL_FIND and a closed console,
    so there was no way to tell a clean miss from a scan that never read a byte. That ambiguity is
    the exact failure this tool was written to prevent, and printing alone did not prevent it."""
    print(msg)
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        with (OUT / "_SCAN_LOG.txt").open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def scan(a) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    _tee(f"\n### {time.strftime('%Y-%m-%d %H:%M:%S')}  args: from={a.from_!r} subject={a.subject!r} "
         f"body={a.body!r} attach={a.attach!r} after={a.after} before={a.before} extract={a.extract}")
    after  = datetime.fromisoformat(a.after).replace(tzinfo=timezone.utc) if a.after else None
    before = datetime.fromisoformat(a.before).replace(tzinfo=timezone.utc) if a.before else None
    re_from = re.compile(a.from_, re.I) if a.from_ else None
    re_subj = re.compile(a.subject, re.I) if a.subject else None
    re_body = re.compile(a.body.encode(), re.I) if a.body else None
    re_att  = re.compile(a.attach, re.I) if a.attach else None

    # 🔴 ONE SWEEP, NOT FOUR. Each pass re-reads all 33 GB and takes 6-12 minutes; the first run
    # spent ~38 minutes reading the same bytes four times. A preset ORs the criteria so the disk is
    # read once and every hit is tagged with what caught it.
    re_or = None
    if a.preset == "abraxas":
        # 🔴 ADDED 2026-08-15 BECAUSE THE SCAR ABOVE WAS WRITTEN AND THEN NOT APPLIED.
        # `mailhunt_abraxas__t1500.py` ran SEVEN separate queries over ~31 GB — seven full sweeps of
        # the same bytes — and TIMED OUT at 1500 s having proven nothing. The comment directly above
        # already said "ONE SWEEP, NOT FOUR" and explained exactly this. A lesson recorded in a
        # docstring is not a lesson enforced by a mechanism: the preset was the mechanism, and the
        # next job simply did not use it. So this preset now exists and the job calls it.
        #
        # \s+ everywhere a phrase can wrap: quoted-printable breaks lines mid-sentence, which is how
        # a literal "requests for admission" search misses a document that plainly contains it.
        re_or = re.compile(
            rb"yerokhin"                                  # the counterparty, any header or body
            rb"|abraxas"                                   # the entity, incl. abraxas-labs
            rb"|no\s+longer\s+authorized"                  # THE REVOCATION — kills the Count II defect
            rb"|not\s+authorized\s+to\s+perform"
            rb"|pay\s+you\s+for\s+the\s+time"              # UNCONDITIONAL acknowledgment (12 O.S. 101)
            rb"|time\s+you\s+worked"
            rb"|pay\s+for\s+your\s+time"
            rb"|no[t]?\s+(?:longer\s+)?welcome"            # the withdrawal of access
            rb"|remove\s+your\s+access"
            rb"|revoke\s+your\s+access"
            rb"|sherburne"                                 # the quantum-meruit rate benchmark
            rb"|all\s?set\s+analytical"
            rb"|allsetanalytical"
            rb"|vortex\s+mixer"                            # the June 5 2020 invoice line items
            rb"|hplc\s+deposit",
            re.I)
        _tee("  PRESET abraxas: ONE sweep, OR of {yerokhin, abraxas, no longer authorized, "
             "pay you for the time, not welcome / remove access, sherburne, All Set Analytical, "
             "vortex mixer, HPLC deposit}. Seven queries collapsed into one pass over the disk.")
        _tee("  ⚠ A ZERO RESULT HERE IS A FINDING, NOT A FAILURE: Keith's 2020 mail was sent from "
             "Keith@ORACLabs.com, which may not be in Thunderbird at all. Zero would mean the "
             "mailbox is not local and the email must come from an export or from Abraxas — it is "
             "responsive to their own RFP 5 and RFP 13.")
    if a.preset == "gilley":
        re_or = re.compile(
            rb"heltonlawfirm"                     # anyone at the firm, any header or body
            rb"|certificate of service"           # the standing question: was anything SERVED?
            rb"|requests?\s+for\s+admission"      # \s+ - quoted-printable wraps lines mid-phrase
            rb"|response[s]?\s+to\s+.{0,40}admission",
            re.I)
        _tee("  PRESET gilley: one sweep, OR of {heltonlawfirm, certificate of service, "
             "requests for admission, responses to ... admission}")

    hits, wrote, scanned_b, scanned_m, t0 = [], [], 0, 0, time.time()
    files = stores()
    _tee(f"\n{'='*96}\n  find_in_mail - {len(files)} stores, "
         f"{sum(p.stat().st_size for p in files)/1e9:.1f} GB\n{'='*96}")
    if not files:
        _tee(f"  🔴 ZERO MAIL STORES FOUND under {TB}")
        _tee("     That is a PATH failure, not a search result. Nothing was read. Do not")
        _tee("     conclude anything about the mail from this run.")
        return 4
    for p in files[:6]:
        _tee(f"     store: {p.stat().st_size/1e6:9.1f} MB  {p.relative_to(TB)}")
    if len(files) > 6:
        _tee(f"     ... and {len(files)-6} more")

    for path in files:
        sz = path.stat().st_size
        n = 0
        try:
            for raw in messages(path):
                n += 1
                tag = ""
                if re_or is not None:
                    mo = re_or.search(raw)
                    if not mo:
                        continue
                    tag = mo.group(0).decode("utf-8", "replace").lower()[:34]
                elif re_body and not re_body.search(raw):
                    continue
                head = raw[:8192]
                if re_or is None and re_from and not re_from.search(
                        head.decode("utf-8", "replace")):
                    continue
                try:
                    msg = email.message_from_bytes(raw, policy=email.policy.default)
                except Exception:
                    continue
                subj = hdr(msg, "subject")
                if re_or is None and re_subj and not re_subj.search(subj):
                    continue
                dt = None
                try:
                    dt = email.utils.parsedate_to_datetime(hdr(msg, "date"))
                    if dt and dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                except Exception:
                    pass
                if dt and after and dt < after:
                    continue
                if dt and before and dt > before:
                    continue

                atts = []
                for part in msg.walk() if msg.is_multipart() else []:
                    fn = part.get_filename()
                    if not fn:
                        continue
                    if re_att and not re_att.search(fn):
                        continue
                    atts.append(fn)
                    if a.extract:
                        try:
                            data = part.get_payload(decode=True) or b""
                            safe = re.sub(r'[^A-Za-z0-9._ -]', "_", fn)[:110]
                            stamp = dt.strftime("%Y-%m-%d") if dt else "undated"
                            dest = OUT / f"{stamp}__{safe}"
                            k = 1
                            while dest.exists():
                                dest = OUT / f"{stamp}__{k}__{safe}"; k += 1
                            dest.write_bytes(data)
                            wrote.append(dest.name)
                        except Exception as e:
                            print(f"     ! could not extract {fn}: {e}")
                if re_or is None and a.attach and not atts:
                    continue
                hits.append((dt, hdr(msg, "from")[:44], subj[:66], atts, path.name, tag))
            scanned_b += sz; scanned_m += n
        except Exception as e:
            _tee(f"  ! {path.name}: {type(e).__name__}: {e}")

    _tee(f"\n  SCANNED {scanned_m:,} messages / {scanned_b/1e9:.1f} GB "
         f"in {time.time()-t0:.0f}s\n  MATCHED {len(hits)}\n")
    for dt, fr, subj, atts, box, tag in sorted(hits, key=lambda h: (h[0] is None, h[0])):
        d = dt.strftime("%Y-%m-%d %H:%M") if dt else "undated        "
        _tee(f"  {d}  {fr:<44} {subj}")
        _tee(f"{'':>20}[{box}]{('  <' + tag + '>') if tag else ''}")
        for x in atts:
            _tee(f"{'':>20}  ATT: {x}")
    if a.extract:
        _tee(f"\n  ATTACHMENTS ACTUALLY WRITTEN: {len(wrote)}")
        for w in wrote[:40]:
            _tee(f"     {w}")
    if not hits:
        _tee("  🔴 NO MATCH - and note the scanned totals above. A clean miss and a scan that")
        _tee("     died early look identical unless you check that it actually read the bytes.")
    return 0


def selftest() -> int:
    """🔴 STRENGTHENED 2026-08-02, and the reason is the whole lesson.

    The previous selftest asserted the SPLITTER returned 2 messages and that a string survived.
    Both were true. The PARSE was broken the entire time, and the test could not see it because it
    never asked the parser a question. A control that does not exercise the thing that breaks is
    not a control - it is decoration that makes you confident.

    This version parses, and asserts on Date, Subject, and an extracted attachment.
    """
    import tempfile, base64
    att = base64.b64encode(b"PDFDATA").decode()
    mb = (b"From a@b Mon Jan  1 00:00:00 2020\r\n"
          b"From: Heather Gilley <hgilley@heltonlawfirm.com>\r\n"
          b"Date: Wed, 4 Mar 2026 10:00:00 +0000\r\n"
          b"Subject: Draft RFA responses\r\n"
          b'Content-Type: multipart/mixed; boundary="B"\r\n\r\n'
          b"--B\r\nContent-Type: text/plain\r\n\r\nsee attached\r\n"
          b'--B\r\nContent-Type: application/pdf\r\nContent-Transfer-Encoding: base64\r\n'
          b'Content-Disposition: attachment; filename="RFA Responses DRAFT.pdf"\r\n\r\n'
          + att.encode() + b"\r\n--B--\r\n"
          b"From b@c Mon Jan  1 00:00:00 2020\r\nFrom: Y <y@other.com>\r\n"
          b"Subject: no\r\n\r\nx\r\n")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "INBOX"; p.write_bytes(mb)
        got = list(messages(p))
        assert len(got) == 2, f"splitter returned {len(got)}, expected 2"

        m = email.message_from_bytes(got[0], policy=email.policy.default)
        # these three are exactly what the first run got wrong, silently
        assert "heltonlawfirm" in hdr(m, "from"), f"FROM did not parse: {hdr(m,'from')!r}"
        assert hdr(m, "subject") == "Draft RFA responses", f"SUBJECT: {hdr(m,'subject')!r}"
        dt = email.utils.parsedate_to_datetime(hdr(m, "date"))
        assert dt.year == 2026 and dt.month == 3, f"DATE: {dt!r}"
        assert m.is_multipart(), "is_multipart() False - attachments would be invisible"
        names = [q.get_filename() for q in m.walk() if q.get_filename()]
        assert names == ["RFA Responses DRAFT.pdf"], f"attachment names: {names}"
        payload = [q.get_payload(decode=True) for q in m.walk()
                   if q.get_filename()][0]
        assert payload == b"PDFDATA", "attachment did not decode"

    print("  selftest: splitter 2/2 · FROM · SUBJECT · DATE(2026-03) · multipart · "
          "attachment name AND bytes - PASS")
    print("  selftest: (the old version passed while all of the above was broken)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_", default="")
    ap.add_argument("--subject", default="")
    ap.add_argument("--body", default="")
    ap.add_argument("--attach", default="")
    ap.add_argument("--after", default="")
    ap.add_argument("--before", default="")
    ap.add_argument("--extract", action="store_true")
    ap.add_argument("--preset", default="", choices=["", "gilley", "abraxas"])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not any([a.from_, a.subject, a.body, a.attach, a.preset]):
        print("need one of --from --subject --body --attach --preset"); return 2
    return scan(a)


if __name__ == "__main__":
    sys.exit(main())
