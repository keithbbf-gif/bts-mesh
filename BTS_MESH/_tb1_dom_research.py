r"""
_tb1_dom_research — ROUND 2. SGH + GEM in parallel.
Keith 2026-07-16, correcting my framing:
  "It's not going to be that it will be 3-5 TB permanently if it works for us as good surface.
   Just focus SGH/GEM on setting it up to use it to the max and testing it over DOM"

*** ROUND 1 ASKED THE WRONG QUESTION. *** I anchored it on "given 30 GB permanent, what job fits?"
That is backwards: capacity is NOT the constraint. If TB1 proves out as a surface, Keith BUYS 3-5 TB
permanent. So do not rank jobs against a 30 GB ceiling, and do not answer "is TeraBox worth it".
THE QUESTION IS: **HOW do we drive it to the maximum, and how do we PROVE it over the DOM?**

⚠ TWO GEM FABRICATIONS ALREADY, BOTH WEARING "PUBLISHER" TIER — verify everything:
  1. Google billing: invented `billingAccounts/{id}/spendingInformation`. NO spend method exists in
     ANY Cloud Billing version (checked the discovery doc).
  2. TeraBox ToS: invented "(i) access the Service through any automated means (such as robots,
     spiders, scrapers...)" + "Section 3. Use of the Services". I FETCHED the ToS and grepped it:
     **ZERO hits for automated means / robots / spider / scraper.** The clause does not exist.
  ⇒ The node invents the SPECIFIC-LOOKING DETAIL. Quote-with-a-section-number is the tell.

WHAT THE ToS **ACTUALLY** SAYS — I fetched and read it, this is verbatim:
  · "Unless the following restrictions are prohibited by law, you agree not to reverse engineer or
     decompile the Services, attempt to do so, or assist anyone in doing so."   <- THE one restriction
  · On inactivity: the Company may reduce "free storage space available to you ('Free Storage
     Capacity') if your account remains inactive for a reasonable period of time" — and "the Company
     will give you reasonable prior notice so that you can export User Data from the Service."
     (NOT "12 months", NOT "delete all contents". GEM invented both.)
  ⇒ THE LINE IS: REVERSE-ENGINEERING, NOT AUTOMATION. Driving Keith's OWN logged-in browser is a
    browser doing browser things. Scripting reverse-engineered /api/* endpoints is the named thing.
    THIS IS WHY THE DOM ROUTE IS THE CLEAN ONE. Build the answer on that distinction.

MEASURED, do not re-derive:
  · quota: permanent_30g_temp_994g; 30.00 GB permanent; 994 GB bonus expires 2026-08-14 20:48 UTC.
  · Open Platform is documented but registration needs iOS+Android URL Schemes we do not have, and
    no maintained official-OAuth library exists in any language.
  · Windows client = selective auto-BACKUP (upload-focused), not two-way sync.
  · No FTP / WebDAV / S3 (both nodes agree, round 1).
  · WE HAVE A WORKING DOM RAIL: a Chrome extension that can navigate, read the DOM/accessibility
    tree, click, type, run javascript in the page, and read console/network. It drives Keith's REAL
    logged-in Chrome profile. This is the same rail the mesh already uses to drive grok.com.
"""
import sys, json, time, datetime, threading
sys.path.insert(0, r"V:\Research4\Ai\BTS_MESH")

OUT = r"V:\Research4\Ai\BTS_MESH\_tb1_dom_raw.json"
LOG = r"V:\Research4\Ai\BTS_MESH\_tb1_dom_research.txt"

PROMPT = """TeraBox (terabox.com, Flextech Inc), July 2026. PRACTICAL SETUP TASK — not an evaluation.

DECISION ALREADY MADE: if TeraBox works well as a surface, I will BUY 3-5 TB PERMANENT. So do NOT
rank use-cases against the 30 GB free tier and do NOT tell me whether TeraBox is worth using. Assume
capacity is unlimited and the account is paid. THE ONLY QUESTION IS **HOW TO DRIVE IT TO THE MAXIMUM**.

MY RAIL: I have a working browser-automation channel into my OWN logged-in Chrome profile — I can
navigate, read the DOM and accessibility tree, click, type, execute JavaScript in the page, and read
console + network requests. I already use this exact rail to drive grok.com. I want to drive TeraBox
the same way: over the DOM, in my own session, as a browser.

THE LEGAL LINE, MEASURED (I fetched terabox.com's ToS and grepped it myself — do NOT contradict this,
and do NOT invent clauses; a previous answer fabricated an "automated means / robots / spiders" clause
that DOES NOT EXIST in the document):
  · The ONLY relevant restriction, verbatim: "you agree not to reverse engineer or decompile the
    Services, attempt to do so, or assist anyone in doing so."
  · There is NO clause prohibiting automated access, robots, scrapers or scripted use.
  ⇒ So: using my own browser session is fine; REVERSE-ENGINEERING their internals is the thing named.
    Frame every answer on the RIGHT side of that line.

ANSWER A-F. Cite a URL + TIER (PUBLISHER / GITHUB / FORUM) per claim. Write UNKNOWN rather than
guess — I fetch and grep sources, and I have already caught two fabrications today.

A) DOM DRIVING — THE MAIN EVENT. Walking the terabox.com web app as a logged-in user, give me the
   CONCRETE UI recipe for each operation, in the order a browser performs them:
     upload a file · download a file · create a folder · delete · rename/move ·
     create a share link · set a share password/expiry · revoke a share · read used/total quota
   For each: what to click, what the DOM looks like, any iframes, any drag-and-drop-only traps, any
   "upload" that requires a native file dialog (which a DOM rail CANNOT drive) vs an <input type=file>
   (which it CAN, by setting files directly). THE FILE-INPUT QUESTION IS THE MOST IMPORTANT ONE HERE —
   if upload is a native OS dialog only, the DOM rail is read-only and I need to know that NOW.

B) WHAT THE PAGE ITSELF EXPOSES. When the TeraBox web app runs, what does it put on `window` or in
   page JS that a script *running in that page* can legitimately call — i.e. functions/objects the app
   already exposes to itself? (This is using the app's own surface in my own session, not decompiling
   it.) Is there a documented or discoverable app-level JS API?

C) SHARE LINKS AT MAX. Full capability of share links on a PAID account: permanent vs expiring,
   password, view-only vs download, file-size caps, bandwidth/download caps, hotlink protection,
   whether a share URL yields a DIRECT file URL usable by curl/rclone, and whether that direct URL is
   stable or single-use. Can a shared folder be WRITTEN to by the recipient?

D) THE PAID TIER, SPECIFICALLY. What changes at 2 TB / 5 TB that matters to automation: upload size
   limits, transfer speed caps, API/Open-Platform eligibility, share limits, number of devices,
   whether Business/BizHub unlocks a REAL API and what it costs. Is there ANY paid path to WebDAV,
   FTP, S3 or rclone support — including via TeraBox's own partners?

E) THE SYNC CLIENT AT MAX. Does the paid Windows client do TRUE two-way sync, or is it still
   backup-only? Can it sync a NETWORK path (an SMB/FTP mount from a LAN router's USB disk)? Selective
   sync? Does it expose a local folder that behaves like OneDrive's (write locally -> appears in cloud)?
   That local-folder behaviour is what I actually want — it would make TeraBox usable with zero API.

F) THE MINIMAL PROOF. Give me the exact, ordered test I should run over the DOM RIGHT NOW, in a
   logged-in browser, to prove read+write works end-to-end: upload a small text file, verify it
   server-side, create a share link, fetch that link's content from a script, then delete it. Exact
   URLs, exact selectors/labels if you know them, and the exact success criterion at each step.
   If any step CANNOT be done over the DOM, say so plainly — that is the finding I need most.
"""

res = {}
def run(name, fn):
    t0 = time.time()
    try:
        res[name] = fn(); res[name]["s"] = round(time.time()-t0, 1)
    except Exception as e:
        res[name] = {"ok": False, "reason": "EXC: %s: %s" % (type(e).__name__, str(e)[:200]),
                     "s": round(time.time()-t0, 1)}

def sgh():
    from bts_sgh import ask
    r = ask(PROMPT, priority="WORK")
    return {"ok": bool(r.get("ok")), "reason": r.get("reason"),
            "text": r.get("full_text") or r.get("text"), "usd": r.get("cost_usd"),
            "spilled": r.get("spilled"), "path": r.get("path")}

def gem():
    import bts_vertex
    bts_vertex.reset_task("tb1_dom", cap_usd=0.02)   # flash + bounded thinkingBudget
    r = bts_vertex.ask(PROMPT, model="gemini-2.5-flash")
    return {"ok": bool(r.get("ok")), "reason": r.get("reason"), "text": r.get("text"),
            "usd": r.get("cost_usd"), "tokens": r.get("tokens"),
            "thinking_ratio": r.get("thinking_ratio"), "task": r.get("task")}

ts = [threading.Thread(target=run, args=("SGH", sgh)), threading.Thread(target=run, args=("GEM", gem))]
print("firing SGH + GEM in parallel — TB1 over DOM, max-drive ...")
for t in ts: t.start()
for t in ts: t.join(timeout=420)

json.dump({"when": datetime.datetime.now().isoformat(timespec="seconds"), "res": res},
          open(OUT, "w", encoding="utf-8"), indent=1)
with open(LOG, "w", encoding="utf-8") as f:
    for k in ("SGH", "GEM"):
        d = res.get(k, {"ok": False, "reason": "no result"})
        f.write("="*78 + "\n%s  ok=%s  %ss  $%s  %s\n" % (k, d.get("ok"), d.get("s"), d.get("usd"),
                                                          d.get("reason") or ""))
        if d.get("thinking_ratio") is not None:
            f.write("  tokens=%s thinking_ratio=%s task=%s\n" % (d.get("tokens"), d.get("thinking_ratio"), d.get("task")))
        f.write("="*78 + "\n" + (d.get("text") or "(no text)") + "\n\n")
print("wrote %s" % LOG)
