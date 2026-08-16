r"""
_usage_research — ask SGH and GEM, in PARALLEL, what usage/metering APIs actually exist.
Keith 2026-07-16: "RESEARCH (meaning have SGH and GEM do it) how to measure usage, I bet there is
an API call for each channel/usage type that will get us most of the way there."

RULES BAKED INTO THE PROMPTS (learned the hard way, 2026-07-16 TeraBox ferry):
  - SOURCE TIER on every claim: PUBLISHER doc / GITHUB / FORUM. Forums are labelled weak.
  - "UNKNOWN" is a valid and PREFERRED answer. A guess here costs hours of building the wrong thing.
  - The 3-6x TeraBox error came from Reddit. Re-tasking with measured facts + a tier rule made SGH
    return UNKNOWN instead of guessing. THE PROMPT WAS THE FIX, NOT THE MODEL.
  - Give them the MEASURED context up front so they cannot contradict it.

SGH  = web + docs sweep (paid, ungrounded ~$0.001-0.02; search=True is REFUSED by the governor and
       we are NOT overriding it -- grok-4.5 has broad doc knowledge and this is a known-domain question).
GEM  = independent second pass (free-ish via Vertex; ~$0.02/call on the $300 trial).
Two vendors, two answers -> disagreement is signal.
"""
import sys, json, time, datetime, threading
sys.path.insert(0, r"V:\Research4\Ai\BTS_MESH")

OUT = r"V:\Research4\Ai\BTS_MESH\_usage_research_raw.json"
LOG = r"V:\Research4\Ai\BTS_MESH\_usage_research.txt"

CONTEXT = """CONTEXT -- MEASURED ON THIS MACHINE, do not contradict without a publisher citation:
- Anthropic: Claude Max 20x subscription ($200/mo) + "usage credits" wallet, monthly spend cap $250,
  ~$242 spent, resets Aug 1. Consumed via the Claude desktop app (Cowork), NOT via an API key.
- xAI: SuperGrok Heavy subscription ($100/mo, chat UI only) AND a separate xAI API key (grok-4.5,
  ~$10/mo cap). xAI docs state the subscription grants NO API credits -- separate billing systems.
- Google: Gemini API key on AI Studio returns 429 "prepayment credits are depleted". Vertex /
  "Gemini Enterprise Agent Platform" works on a $300 free-trial billing account (010E47-824B53-7202F5),
  expires 2026-10-13, $0 of $300 used.
- Microsoft: M365 Family with Copilot (60 AI credits/mo).
"""

QUESTIONS = """QUESTIONS -- answer A-F. For EVERY claim give a URL and a TIER (PUBLISHER / GITHUB / FORUM).
Write UNKNOWN rather than guess. I will check your sources.

A) ANTHROPIC: Is there ANY programmatic way to read usage/spend for a CLAUDE MAX SUBSCRIPTION (not a
   Console API key)? Specifically: does the Anthropic Console expose a usage or cost endpoint
   (e.g. /v1/organizations/usage_report/messages, /v1/organizations/cost_report), what auth does it
   need (admin key? sk-ant-admin?), and does it report SUBSCRIPTION/Max/Cowork usage or ONLY
   pay-as-you-go API-key usage? THIS IS THE MOST IMPORTANT QUESTION. If the answer is "subscription
   usage is UI-only", say so plainly.

B) xAI: Is there an API to read xAI API spend/credit balance? (e.g. api.x.ai management/billing
   endpoints, /v1/api-key, console.x.ai). Can it report the SuperGrok SUBSCRIPTION usage/quota, or
   only API spend? Give exact endpoint + auth.

C) GOOGLE GEMINI / AI STUDIO: Is there an endpoint to read remaining free-tier quota or
   rate-limit headroom for a Gemini API key? Docs say rate limits are "viewable in AI Studio" behind
   auth -- is there a machine-readable equivalent? Cite.

D) GOOGLE CLOUD / VERTEX: Exact API to read (1) the $300 free-trial credit balance remaining and
   (2) actual spend, per service. Consider: Cloud Billing API v1
   (cloudbilling.googleapis.com), billingAccounts.getSpendingInformation, BigQuery billing export,
   Cloud Monitoring metrics. Which of these works for a FREE TRIAL account with no BigQuery export
   configured? What scopes/roles? Is there anything that gives credit-vs-cash breakdown
   ("Other savings" vs "Usage cost") programmatically?

E) MICROSOFT: Any API for M365 Copilot AI-credit consumption on a CONSUMER/Family licence?

F) For each of A-E, state in ONE line: MACHINE-READABLE (endpoint exists) or UI-ONLY (no endpoint).
   Then give the single best endpoint per vendor as a ready-to-run curl.
"""

PROMPT = CONTEXT + "\n" + QUESTIONS

res = {}
def run_sgh():
    t0=time.time()
    try:
        from bts_sgh import ask
        r = ask(PROMPT, priority="WORK")
        res["SGH"] = {"ok": bool(r.get("ok")), "reason": r.get("reason"),
                      "text": r.get("full_text") or r.get("text"),
                      "usd": r.get("cost_usd"), "s": round(time.time()-t0,1)}
    except Exception as e:
        res["SGH"] = {"ok": False, "reason": "EXC: %s: %s" % (type(e).__name__, str(e)[:200]), "s": round(time.time()-t0,1)}

def run_gem():
    t0=time.time()
    try:
        from bts_gem import ask
        r = ask(PROMPT)
        res["GEM"] = {"ok": bool(r.get("ok")), "reason": r.get("reason"),
                      "text": r.get("text"), "via": r.get("via"),
                      "usd": r.get("cost_usd"), "s": round(time.time()-t0,1)}
    except Exception as e:
        res["GEM"] = {"ok": False, "reason": "EXC: %s: %s" % (type(e).__name__, str(e)[:200]), "s": round(time.time()-t0,1)}

ts = [threading.Thread(target=run_sgh), threading.Thread(target=run_gem)]
print("firing SGH + GEM in parallel ...")
for t in ts: t.start()
for t in ts: t.join(timeout=300)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"when": datetime.datetime.now().isoformat(timespec="seconds"), "res": res}, f, indent=1)

with open(LOG, "w", encoding="utf-8") as f:
    for k in ("SGH", "GEM"):
        d = res.get(k, {"ok": False, "reason": "no result"})
        hdr = "="*78 + "\n%s  ok=%s  %ss  $%s  %s\n" % (k, d.get("ok"), d.get("s"), d.get("usd"), d.get("reason") or "")
        f.write(hdr + "="*78 + "\n")
        f.write((d.get("text") or "(no text)") + "\n\n")
        print(hdr)
print("wrote %s" % LOG)
