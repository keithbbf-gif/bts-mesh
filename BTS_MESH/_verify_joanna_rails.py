"""
_verify_joanna_rails.py — prove the two rails on the JOANNA account. 2026-07-15.

WHY THIS EXISTS: this whole week's mess came from CLAIMING instead of MEASURING. So before the mesh
trusts these rails, they get probed and the HTTP codes get printed. Nothing here is inferred.

WHAT IT DOES *NOT* DO: it cannot tell you whether the $300 credit is paying. Only the console can.
It prints the exact console check at the end. Do not skip it.

Run:  py -3 _verify_joanna_rails.py        (or double-click _run_verify_joanna.bat)
"""
import json, os, sys, urllib.request, urllib.error

SEC = r"V:\Research4\.secrets"
GEM_KEY = os.path.join(SEC, "gemini_key.txt")     # restricted to Generative Language API
VTX_KEY = os.path.join(SEC, "vertex_key.txt")     # restricted to Agent Platform API

GEM_URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
VTX_URL = "https://aiplatform.googleapis.com/v1/publishers/google/models/{m}:generateContent"

PROMPT = "Reply with exactly one word: OK"


def _key(path):
    if not os.path.exists(path):
        return None, "MISSING FILE"
    k = open(path, encoding="utf-8").read().strip().strip('"')
    return (k, None) if k else (None, "EMPTY FILE")


def _post(url, key, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "x-goog-api-key": key})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        d = json.load(r)
        txt = "".join(p.get("text", "")
                      for p in d["candidates"][0]["content"]["parts"]).strip()
        um = d.get("usageMetadata", {}) or {}
        return r.status, txt, um, None
    except urllib.error.HTTPError as e:
        return e.code, None, {}, e.read().decode()[:400]
    except Exception as e:
        return None, None, {}, "%s: %s" % (type(e).__name__, str(e)[:200])


def diagnose_429(msg):
    """THE DISTINCTION THAT COST TWO DAYS. Three different 429s wear the same code."""
    low = (msg or "").lower()
    if "prepay" in low or "credit" in low:
        return ("BILLING STATE — *not* a quota. The project is linked to a PREPAY billing account "
                "at $0.\n     Google: 'Your projects aren't automatically downgraded to the Free "
                "Tier.' It STOPS DEAD;\n     it will NOT come back at midnight. Retrying can never "
                "fix it.\n     FIX: unlink/disable billing on the project -> drops to Free tier. "
                "Or buy credits.\n     >>> IF THIS FIRES ON A FREE-TRIAL ACCOUNT, SOMETHING LINKED "
                "A PAID ACCOUNT TO THE PROJECT.")
    return ("ORDINARY QUOTA. RPD resets at MIDNIGHT PACIFIC (doc-confirmed). This is the free tier "
            "WORKING,\n     merely spent for today. Backoff/wait is the right response.")


def probe(name, path, url, model, extra_body=None):
    print("\n" + "=" * 78)
    print("  %s" % name)
    print("=" * 78)
    key, err = _key(path)
    print("  key file : %s" % path)
    if err:
        print("  RESULT   : *** %s *** -- create the key and save it here." % err)
        return False
    print("  key      : %s...%s  (len %d, prefix %s)"
          % (key[:6], key[-4:], len(key), "AQ." if key.startswith("AQ.") else key[:4]))

    body = {"contents": [{"parts": [{"text": PROMPT}]}]}
    if extra_body:
        body["contents"][0].update(extra_body)

    code, txt, um, msg = _post(url.format(m=model), key, body)
    print("  model    : %s" % model)
    print("  HTTP     : %s" % code)

    if code == 200:
        print("  reply    : %r" % txt)
        print("  tokens   : in=%s out=%s" % (um.get("promptTokenCount"),
                                             um.get("candidatesTokenCount")))
        print("  RESULT   : *** PASS ***")
        return True

    print("  body     : %s" % (msg or "")[:300])
    if code == 429:
        print("  DIAGNOSIS: %s" % diagnose_429(msg))
    elif code == 403 and "API_KEY_SERVICE_BLOCKED" in (msg or ""):
        print("  DIAGNOSIS: key is not scoped to this API, OR org policy "
              "iam.managed.disableServiceAccountApiKeyCreation\n     is enforced. One key = ONE "
              "API; you need the SECOND key. (Scars gate 3/4.)")
    elif code == 403 and "billing" in (msg or "").lower():
        print("  DIAGNOSIS: billing not linked to THIS project. (Scars gate 2.)")
    elif code == 403:
        print("  DIAGNOSIS: likely IAM — service account needs 'Vertex AI User' "
              "(roles/aiplatform.user). (Scars gate 5.)")
    elif code == 400 and "role" in (msg or "").lower():
        print("  DIAGNOSIS: Vertex REQUIRES contents[].role; AI Studio does not. Payload bug.")
    elif code == 404:
        print("  DIAGNOSIS: model retired for new keys. Try gemini-flash-lite-latest.")
    print("  RESULT   : *** FAIL ***")
    return False


def main():
    print("\nJOANNA RAIL VERIFY - 2026-07-15")
    print("billing 010E47-824B53-7202F5 | project project-5a33f910-1251-4d6a-bf9")

    gem_ok = probe("RAIL 1/2  GEM - AI Studio free tier (bts_gem.py)",
                   GEM_KEY, GEM_URL, "gemini-flash-lite-latest")

    vtx_ok = probe("RAIL 2/2  VERTEX - Agent Platform, the $300 door (bts_vertex.py)",
                   VTX_KEY, VTX_URL, "gemini-2.5-flash", extra_body={"role": "user"})

    print("\n" + "=" * 78)
    print("  SUMMARY")
    print("=" * 78)
    print("  GEM (free tier)      : %s" % ("PASS" if gem_ok else "FAIL"))
    print("  VERTEX ($300 door)   : %s" % ("PASS" if vtx_ok else "FAIL"))

    if gem_ok and vtx_ok:
        print("""
  Both rails live. The architecture is now what you always thought it was:
      free daily quota PRIMARY  ->  Vertex on the $300 FAILOVER  ->  never dies mid-chapter

  *** ONE THING LEFT, AND CODE CANNOT DO IT ***
  Nothing above proves the $300 is PAYING for Vertex. That is [G] - no Google page states
  first-party Gemini on Agent Platform is credit-eligible; we reasoned it from an enumerated
  two-item exclusion list plus "third-party generative AI models" being what the trial RESTRICTS.
  The Vertex call above just cost ~$0.0004 of SOMETHING. Which something is the whole question.

  *** WAIT ~24h BEFORE READING THE METER. ***
  Google: "Typically, your costs are available within a day, but can sometimes take more than
  24 hours." The AI Studio billing page says the same of its graphs. Reading it in 5 minutes and
  seeing nothing means NOTHING. Do not conclude from an empty report.

  GO READ IT (tomorrow):
      https://console.cloud.google.com/billing/010E47-824B53-7202F5/reports
      Group by SKU, time range = today, find the Agent Platform / Gemini row.

  *** HOW TO READ IT - THIS IS THE BIT THAT IS EASY TO GET BACKWARDS ***
  "Usage cost" is ALWAYS populated - it is the on-demand rate, charged or not. It is NOT the
  signal. The credit appears as a SEPARATE OFFSETTING LINE. Google's own worked example:

      SKU                        Usage cost   Saving programs   Other savings   Subtotal
      N1 Predefined Instance     $33.75       $0.00             -$33.75         $0.00

      -> "Other savings" NEGATIVE and "Subtotal" $0.00   = CREDIT PAID IT. Confirmed. Burn it.
      -> "Other savings" $0.00 and "Subtotal" > $0        = the credit is NOT covering Vertex.

  *** DO NOT USE THE CLOUD HUB "Optimization" PAGE FOR THIS. *** It reports GROSS cost:
  "based on your contract prices, BEFORE any committed-use discounts (CUDs) or other credits are
  applied." Credits are INVISIBLE there - it will show a dollar figure either way and look exactly
  like the credit failed. FALSE NEGATIVE GUARANTEED. Use Billing -> Reports, nothing else.

  *** DO NOT CLICK "ACTIVATE" / "Upgrade to paid". *** Non-billable is the entire safety property,
  AND activating makes the account Paid -> the Gemini project goes Tier 1 -> the free daily quota
  dies and a $10 prepay is required. That is the documented autopsy of the deleted account.
  It does NOT extend the credit: "must be consumed within the original 90 days from sign-up".""")
    else:
        print("""
  Fix the FAIL above before wiring anything into the mesh.
  Console checklist: V:\\Research4\\Ai\\BTS_MESH\\JOANNA_RAIL_SETUP_2026-07-15.md""")
    print()
    return 0 if (gem_ok and vtx_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
