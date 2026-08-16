r"""
domain_assay.py — is this domain actually free? Built 2026-08-16.

Named for what it does: an assay tests a sample for what it really contains, rather than for what
the label says. Every "domain availability" search box is a sales funnel; this asks the registry.

HOW IT ANSWERS
  RDAP (RFC 7482), Verisign's public endpoint. No key, no account, no rate deal. A registered domain
  returns a JSON record; an unregistered one returns nothing. That asymmetry is the whole method.

🔴 AND THAT ASYMMETRY IS EXACTLY WHY THIS TOOL NEEDS A CONTROL ON EVERY RUN.
  "Nothing came back" and "the lookup failed" are the SAME RESPONSE. A network blip, a throttle, a
  changed URL, a typo in the path — all of them return empty, and empty is what this tool reports as
  AVAILABLE. So a silent failure does not look like a failure. It looks like good news.
  ⇒ `calibrate()` runs before any batch: one domain that MUST be registered, one nonsense string
    that MUST NOT be. If either control disagrees, the tool REFUSES to report on anything.
    A checker that has only ever been shown to succeed is not a checker.

🔴 THE FALSE NEGATIVE THAT PROMPTED THIS FILE — measured 2026-08-16 05:50.
  Verisign's RDAP serves .com and .net ONLY. A query for `theassay.ai` against it returned empty,
  and empty means available. It was reported as available for about ten seconds before the TLD was
  noticed. It is not an answer about .ai at all — it is the server saying "not my registry."
  ⇒ Any TLD outside .com/.net is REFUSED, loudly, rather than answered wrongly. Wrong answers about
    a domain are cheap to make and expensive to act on.

⚠ AND WHAT THIS TOOL DELIBERATELY DOES NOT DO: judge the name. Availability is the easy half. It
  will happily return five hundred free strings, all of them bad. `lawassay.com` was free, correct,
  and flat, and no scoring function was going to say so. Send the survivors to `mesh_fanout.py` and
  let several families rank them; that is what the mesh is for and it costs pennies.

  RUN:  py -3.14 domain_assay.py --selftest
        py -3.14 domain_assay.py assaylaw.com crucible.com
        py -3.14 domain_assay.py --words assay,crux,bench --suffix law,ai,works
"""
import json
import sys
import time
import urllib.error
import urllib.request

RDAP = "https://rdap.verisign.com/%s/v1/domain/%s"
OK_TLDS = ("com", "net")
CONTROL_REGISTERED = "google.com"          # must always come back with a record
CONTROL_FREE = "qzxkvbnmplwrjjh7zzq.com"   # must always come back empty
PAUSE = 0.6                                # be a good citizen on a free public endpoint


class AssayError(RuntimeError):
    pass


def _raw(domain: str, timeout: int = 25):
    """Return (status, body). status 404/empty body -> not registered."""
    tld = domain.rsplit(".", 1)[-1].lower()
    if tld not in OK_TLDS:
        raise AssayError(
            "TLD .%s is not served by this endpoint. Verisign RDAP answers for .com and .net only, "
            "and returns EMPTY for everything else — which this tool would otherwise read as "
            "AVAILABLE. Refusing rather than guessing." % tld)
    req = urllib.request.Request(RDAP % (tld, domain.lower()),
                                 headers={"Accept": "application/rdap+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def registered(domain: str):
    """True / False / None. None means the lookup could not be trusted."""
    try:
        st, body = _raw(domain)
    except AssayError:
        raise
    except Exception:                                                 # noqa: BLE001
        return None
    if st == 200 and body.strip().startswith("{"):
        try:
            return bool(json.loads(body).get("ldhName"))
        except Exception:                                             # noqa: BLE001
            return None
    if st == 404 or not body.strip():
        return False
    return None


def calibrate(verbose: bool = True):
    """Prove BOTH directions before believing anything. Returns True only if both controls agree."""
    a = registered(CONTROL_REGISTERED)
    time.sleep(PAUSE)
    b = registered(CONTROL_FREE)
    ok = (a is True) and (b is False)
    if verbose:
        print("  control  %-24s registered=%s  (must be True)" % (CONTROL_REGISTERED, a))
        print("  control  %-24s registered=%s  (must be False)" % (CONTROL_FREE, b))
        print("  CALIBRATION %s" % ("PASS" if ok else "FAIL — results are NOT trustworthy"))
    return ok


def check(domains, verbose: bool = True):
    """Check a list. Refuses to run at all if calibration fails."""
    if not calibrate(verbose=verbose):
        raise AssayError("calibration failed — refusing to report. An empty response from this "
                         "endpoint is indistinguishable from a failed one, so an uncalibrated run "
                         "reports outages as good news.")
    out = {}
    for d in domains:
        time.sleep(PAUSE)
        try:
            r = registered(d)
        except AssayError as e:
            out[d] = "REFUSED"
            if verbose: print("  %-32s REFUSED  %s" % (d, e))
            continue
        out[d] = {True: "taken", False: "AVAILABLE", None: "unknown"}[r]
        if verbose:
            print("  %-32s %s" % (d, out[d]))
    return out


def combos(words, suffixes, tld="com"):
    seen, out = set(), []
    for w in words:
        for s in suffixes:
            for cand in (w + s, s + w):
                d = (cand + "." + tld).lower()
                if d not in seen:
                    seen.add(d); out.append(d)
    return out


def selftest():
    print("domain_assay selftest")
    ok = True
    ok &= calibrate()
    # the TLD guard must REFUSE, not answer. This is the false negative that produced this file.
    try:
        registered("example.ai")
        print("  [FAIL] .ai was answered instead of refused")
        ok = False
    except AssayError:
        print("  [ok]   a non-.com/.net TLD is REFUSED, not silently reported available")
    print("SELFTEST %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    a = sys.argv[1:]
    if not a or "--selftest" in a:
        return selftest()
    if "--words" in a:
        words = a[a.index("--words") + 1].split(",")
        sfx = a[a.index("--suffix") + 1].split(",") if "--suffix" in a else [""]
        cands = combos(words, sfx)
        print("  %d candidates" % len(cands))
        res = check(cands)
        free = [d for d, v in res.items() if v == "AVAILABLE"]
        print("\n  AVAILABLE (%d):" % len(free))
        for d in free:
            print("    " + d)
        print("\n  ⚠ Availability is the easy half. Send these to mesh_fanout and let several "
              "families rank them before you register anything.")
        return 0
    check([d for d in a if not d.startswith("-")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
