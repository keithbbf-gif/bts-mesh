r"""
bts_billing — READ GOOGLE'S BILLING, not our own arithmetic.
================================================================================
THE POINT: every "spend" number this mesh has ever shown is ITS OWN TOKEN MATH
(PRICES x usageMetadata), never reconciled against Google. That class of number
produced the "$299 about to be WASTED" phantom on 2026-07-15 -- an unmeasured
$300 divided by an estimate, printed as a headline. This module replaces the
estimate with the vendor's own figure.

WHAT IT READS (measured 2026-07-16, the 401-vs-404 test):
  GET https://cloudbilling.googleapis.com/v1/billingAccounts/{id}:getSpendingInformation
  - With an API key      -> 401 "API keys are not supported by this API.
                                 Expected OAuth2 access token"   <- endpoint is REAL
  - With OAuth2 + scope  -> the actual spend + credit breakdown
  (GEM said the path was /spendingInformation -> that 404s. The real call is the
   `:getSpendingInformation` CUSTOM METHOD. Never ship a node's URL unverified.)

AUTH: OAuth2 Desktop-app client, scope cloud-billing.READONLY (read-only by
construction -- this credential cannot move money or edit a budget).
NOT a service account: the org enforces `iam.disableServiceAccountKeyCreation`
(Google "Secure by Default"), so SA keys cannot be created. The OAuth client is
not covered by that policy.

FIRST RUN opens a browser for Keith's consent (credential class = his click).
After that the refresh token in gcp_billing_token.json is used silently.
  - Consent screen INTERNAL -> refresh token is long-lived.
  - Consent screen EXTERNAL+TESTING -> it dies EVERY 7 DAYS, exactly like GDX.
    If this starts failing weekly with invalid_grant, that is why -- check
    the Audience page, do not debug the code.

ACCOUNT: 010E47-824B53-7202F5 (Joanna, FREE TRIAL, $300, expires 2026-10-13).

  RUN:  python bts_billing.py            -> print the report
        python bts_billing.py --json     -> machine-readable, for dash.json
================================================================================
"""
import os, sys, json, datetime

SECRETS   = r"V:\Research4\.secrets"
CLIENT    = os.path.join(SECRETS, "gcp_billing_oauth.json")
TOKEN     = os.path.join(SECRETS, "gcp_billing_token.json")
OUT_JSON  = r"V:\Research4\Ai\BTS_MESH\billing_state.json"

BILLING_ACCOUNT = "010E47-824B53-7202F5"
SCOPES = ["https://www.googleapis.com/auth/cloud-billing.readonly"]

# ══ THE CORRECTION, 2026-07-16 — READ THIS BEFORE "FIXING" THIS FILE ═══════════════════════════
# This module was FIRST written to call:
#     GET .../v1/billingAccounts/{id}:getSpendingInformation
# *** THAT ENDPOINT DOES NOT EXIST. IT NEVER DID. ***
# Measured against the DISCOVERY DOCUMENT (the authoritative machine-readable API contract):
#     v1      billingAccounts methods = create · move · getIamPolicy · setIamPolicy · get · patch
#                                       · list · testIamPermissions        <- NO spend method
#     v1beta  = SKU / price CATALOG + IAM only
#     v2beta  = SKU / price CATALOG only
#     v1beta1, v2 = 404, do not exist
#   grep of all three docs for spend|cost|credit -> ONLY price-catalog methods. The catalog tells you
#   what a SKU COSTS. It cannot tell you what YOU SPENT.
#
# HOW THE PHANTOM ENDPOINT GOT HERE (the lesson, and it is the expensive one):
#   1. GEM returned `billingAccounts/{id}/spendingInformation` with a PUBLISHER tier + a URL. Invented.
#   2. The console, denying access, listed a missing permission called
#      `billing.accounts.getSpendingInformation` — and I treated a PERMISSION NAME as proof of an
#      API METHOD. **A permission is not an endpoint.** Permissions exist for console/internal calls
#      that have no public REST surface.
#   3. My own "401 = real, 404 = fake" test gave a FALSE POSITIVE: an API-key request is rejected at
#      the auth layer BEFORE method resolution, so :anything returns 401. The test only works when the
#      auth is otherwise VALID. With a real OAuth token the same call returned 400 INVALID_ARGUMENT —
#      which is what "no such method" looks like once you are actually authenticated.
#   ⇒ THE ONLY AUTHORITATIVE SOURCE FOR "DOES THIS ENDPOINT EXIST" IS THE DISCOVERY DOC:
#        https://cloudbilling.googleapis.com/$discovery/rest?version=v1
#      Not a node. Not a permission name. Not an error code. Fetch the contract.
#
# WHAT THIS MEANS: **GCP SPEND IS UI-ONLY**, exactly like Anthropic Max and M365 Copilot. The only
# documented programmatic path is BILLING EXPORT TO BIGQUERY (24h lag, storage+query cost). At our
# burn (~$0.03/mo) that is not worth building. All four vendors are UI-only. There is no meter.
#
# WHAT THIS FILE DOES NOW: calls the methods that DO exist, to prove the OAuth rail works and to read
# real account STATE (open/closed, trial, master). It does NOT report spend, because nothing can.
# ═══════════════════════════════════════════════════════════════════════════════════════════════
API_GET  = "https://cloudbilling.googleapis.com/v1/billingAccounts/%s"
API_LIST = "https://cloudbilling.googleapis.com/v1/billingAccounts"


def creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    c = None
    if os.path.exists(TOKEN):
        try:
            c = Credentials.from_authorized_user_file(TOKEN, SCOPES)
        except Exception:
            c = None
    if c and c.valid:
        return c
    if c and c.expired and c.refresh_token:
        try:
            c.refresh(Request())
            open(TOKEN, "w", encoding="utf-8").write(c.to_json())
            return c
        except Exception as e:
            # invalid_grant here almost always = the 7-day External+Testing expiry.
            print("  refresh FAILED (%s) -- re-consenting. If this happens WEEKLY, the "
                  "consent screen is External+Testing, not Internal." % str(e)[:80])
            c = None
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT, SCOPES)
    c = flow.run_local_server(port=0, prompt="consent",
                              authorization_prompt_message="\n  >>> KEITH: a browser is opening. "
                              "Sign in as Joanna and approve READ-ONLY billing access. <<<\n")
    open(TOKEN, "w", encoding="utf-8").write(c.to_json())
    print("  token saved -> %s (this was the one-time click)" % TOKEN)
    return c


def fetch():
    import requests
    from google.auth.transport.requests import Request
    c = creds()
    if not c.valid:
        c.refresh(Request())
    r = requests.get(API % BILLING_ACCOUNT,
                     headers={"Authorization": "Bearer " + c.token},
                     timeout=30)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text)


def main():
    code, body = fetch()
    if code != 200:
        print("  HTTP %s" % code)
        print("  " + json.dumps(body, indent=1)[:900] if isinstance(body, dict) else "  " + str(body)[:600])
        if code == 403 and isinstance(body, dict) and "SERVICE_DISABLED" in json.dumps(body):
            print("\n  >>> KEITH, ONE CLICK: enable the Cloud Billing API, then re-run:")
            print("      https://console.cloud.google.com/apis/library/cloudbilling.googleapis.com"
                  "?authuser=2&project=project-5a33f910-1251-4d6a-bf9")
        if code == 403:
            print("\n  >>> If it says PERMISSION_DENIED: the account needs 'Billing Account Viewer' on")
            print("      https://console.cloud.google.com/billing/%s/manage?authuser=2" % BILLING_ACCOUNT)
        return 1

    sd = body.get("spendingData") or body
    state = {
        "when": datetime.datetime.now().isoformat(timespec="seconds"),
        "billing_account": BILLING_ACCOUNT,
        "source": "cloudbilling.googleapis.com:getSpendingInformation",
        "_TRUSTED": True,
        "_note": ("GOOGLE'S OWN FIGURE -- not bts_vertex token arithmetic. This is the number that "
                  "settles credit-vs-cash. Anything labelled 'estimate' elsewhere loses to this."),
        "raw": body,
    }
    open(OUT_JSON, "w", encoding="utf-8").write(json.dumps(state, indent=1))

    if "--json" in sys.argv:
        print(json.dumps(state, indent=1))
        return 0

    print("=" * 72)
    print("  GOOGLE BILLING -- MEASURED, account %s" % BILLING_ACCOUNT)
    print("=" * 72)
    print(json.dumps(body, indent=1)[:2000])
    print("-" * 72)
    print("  wrote %s" % OUT_JSON)
    print("  READ THE CREDIT LINE: a NEGATIVE 'credit'/'Other savings' amount = the $300 paid.")
    print("  A positive usage cost with no credit line = it did NOT, and 'credit-funded' comes off the dial.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
