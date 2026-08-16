r"""
_tb1_research — SGH + GEM in PARALLEL on: how do we make TB1 maximally useful to the mesh?
Keith 2026-07-16: "What about TB1? SGH/GEM on it to find out how to make it max functional on the
mesh (read/write/local/R2/FTP/etc.)"

⚠ THIS IS A RE-OPEN, DELIBERATELY SCOPED. On 2026-07-16 we ferried a publisher-doc sweep that
DISQUALIFIED TB1 as the FEDERATION MEETING POINT. That verdict stands and is NOT the question here.
The question now is narrower and different: **given what TB1 IS, what is the most useful job it can
hold in the mesh?** Do not re-litigate the meeting-point verdict; build on it.

WHAT IS ALREADY MEASURED — do not contradict without a publisher citation, and do not re-ask:
  · Quota: init_quota_type='permanent_30g_temp_994g'. 30.00 GB PERMANENT + 994 GB TEMP.
    time_limit_quota_expire_time=1786740481 = 2026-08-14 20:48 UTC (~30 days). NOT "3-6 months" —
    that figure came from Reddit and was 3-6x WRONG; the vendor's own API says 30 days.
  · What happens to >30 GB at expiry: **UNKNOWN**. No publisher page states it. ToS/blog cover only
    PAID lapse ("we will reclaim your unused storage space, and the saved files will be permanently
    retained"). That silence is why TB1 cannot hold the archive.
  · Open Platform (terabox.com/integrations/docs) is REAL and documented: oauth/gettoken (access 2d,
    refresh 30d SINGLE-USE), precreate -> superfile2 chunk (>4MiB) -> create, list, download(dlink),
    filemanager(delete/move/rename/copy), quota. BUT: application requires **iOS AND Android URL
    schemes** we do not have, and there is **NO maintained official-OAuth library** in any language.
  · The Windows client is **selective auto-backup / upload-focused**, NOT a two-way sync folder.
  · Everything on GitHub (gulp79/rclone-extra, BenjiThatFoxGuy-Labs/bclone, saahiyo/terabox-gateway)
    is COOKIE/session scraping, not official OAuth. rclone has an open FR, no native support.
  · Mesh context: ITC=Cloudflare R2 (public web, ai.dchambers.com, ~5/10 GB). GDX=Google Drive
    (11.7/100 GB, the SGH<->Cowork handoff). ODX=OneDrive (105/1024 GB, the cold archive; Copilot's
    only rail). TB1 currently has ZERO node edges.

ASK BOTH NODES THE SAME THING. Two vendors = disagreement is signal.
"""
import sys, json, time, datetime, threading
sys.path.insert(0, r"V:\Research4\Ai\BTS_MESH")

OUT = r"V:\Research4\Ai\BTS_MESH\_tb1_research_raw.json"
LOG = r"V:\Research4\Ai\BTS_MESH\_tb1_research.txt"

PROMPT = """TeraBox (terabox.com, Flextech Inc), July 2026. I need to decide what JOB to give a TeraBox
free account inside a small multi-agent "mesh" that already has three storage surfaces. This is NOT a
question about whether TeraBox is good — it is about what it is BEST AT, given hard constraints.

HARD FACTS I MEASURED FROM TERABOX'S OWN AUTHENTICATED API — do not contradict these without a
publisher-doc citation, and do not re-derive them:
- init_quota_type = 'permanent_30g_temp_994g'; free = 32212254720 bytes = 30.00 GB PERMANENT.
- time_limit_quota_expire_time = 1786740481 = 2026-08-14 20:48 UTC (~30 days) for the 994 GB bonus.
  (Reddit says "3-6 months". Reddit is WRONG. The vendor's API says 30 days.)
- What happens to data >30 GB when the bonus lapses: NOT DOCUMENTED anywhere. Treat as UNKNOWN.
- Open Platform exists and is documented, but registration needs iOS+Android URL Schemes (we have
  neither), and there is NO maintained library using the official OAuth.
- The Windows client is selective auto-BACKUP (upload-focused), not a two-way sync folder.

MY EXISTING SURFACES (so do not propose duplicating them):
- Cloudflare R2 -> a PUBLIC website (ai.dchambers.com). ~5 GB of 10. This is the publish surface.
- Google Drive  -> the agent<->agent handoff surface. 11.7 GB of 100. Synced to disk by Drive Desktop.
- OneDrive      -> the cold/private archive. 105 GB of 1024.
- All of it runs on ONE Windows PC + a Linux sandbox. There is also a LAN router (Linksys EA7500)
  with a USB port and an FTP server tab.

PRIORITY OF SOURCES: terabox.com publisher docs (help centre, ToS, release notes, Open Platform
Integration Document, Business/BizHub) FIRST. Then GitHub. Forums LAST and label them WEAK.
State the TIER (PUBLISHER / GITHUB / FORUM) for every claim. Write UNKNOWN rather than guess —
I check sources, and a previous answer here was 3-6x wrong because it leaned on Reddit.

ANSWER A-F:

A) THE CORE QUESTION: given a 30 GB PERMANENT, always-there tier — what is the single most useful JOB
   for TeraBox in this mesh? Rank concrete options and say why, e.g.: (i) a 30 GB hot scratch/exchange
   surface for agent handoffs; (ii) an off-site copy of the SMALL critical set (drafts, manifests,
   keys-excluded); (iii) a public-ish share/distribution surface via share links; (iv) nothing — it is
   strictly worse than what I already have. Be willing to say (iv).

B) SHARE LINKS AS AN API: can a file be made publicly downloadable via a share link, and can that link
   be created and revoked PROGRAMMATICALLY? Is there a direct-download URL usable by a script (curl/
   rclone), and does it expire? Exact endpoints/params. This is the "poor man's R2" question.

C) READ/WRITE FROM A SCRIPT WITHOUT THE OPEN PLATFORM: precisely what does the logged-in web/session
   (cookie) API allow — list, upload, download, delete, mkdir, share? Give exact endpoints. What EXACTLY
   in the ToS prohibits or permits this for personal automation? Quote it. Is there any rate limit?

D) FTP / WebDAV / S3: does TeraBox expose ANY of these, directly or via an official bridge? If not,
   can the TeraBox Windows client point at a folder that is ITSELF an FTP/SMB mount (e.g. a USB disk
   on a LAN router), so the router becomes the local source and TeraBox becomes the off-site leg?
   Any documented problems with syncing a network path?

E) THE 30 GB QUESTION: is the 30 GB permanent tier stable and reliable long-term, or does it also
   degrade (inactivity clauses, forced app opens, ads-to-keep-space)? Quote the ToS on account
   inactivity and on space reclamation.

F) VERDICT IN ONE LINE: the single best job for TB1 in this mesh, or "none — do not use it".
   Then: the exact minimal steps to set that job up.
"""

res = {}
def run(name, fn):
    t0 = time.time()
    try:
        res[name] = fn()
        res[name]["s"] = round(time.time() - t0, 1)
    except Exception as e:
        res[name] = {"ok": False, "reason": "EXC: %s: %s" % (type(e).__name__, str(e)[:200]),
                     "s": round(time.time() - t0, 1)}

def sgh():
    from bts_sgh import ask
    r = ask(PROMPT, priority="WORK")
    return {"ok": bool(r.get("ok")), "reason": r.get("reason"),
            "text": r.get("full_text") or r.get("text"), "usd": r.get("cost_usd"),
            "spilled": r.get("spilled"), "path": r.get("path")}

def gem():
    # flash + the new $0.01/task cap + bounded thinkingBudget. Vertex bills THINKING at the OUTPUT
    # rate — measured 28.5x the visible answer on pro — so pro is the wrong tool for a long sweep.
    import bts_vertex
    bts_vertex.reset_task("tb1_research", cap_usd=0.01)
    r = bts_vertex.ask(PROMPT, model="gemini-2.5-flash")
    return {"ok": bool(r.get("ok")), "reason": r.get("reason"), "text": r.get("text"),
            "usd": r.get("cost_usd"), "tokens": r.get("tokens"),
            "thinking_ratio": r.get("thinking_ratio"), "task": r.get("task")}

ts = [threading.Thread(target=run, args=("SGH", sgh)), threading.Thread(target=run, args=("GEM", gem))]
print("firing SGH + GEM in parallel on TB1 ...")
for t in ts: t.start()
for t in ts: t.join(timeout=420)

json.dump({"when": datetime.datetime.now().isoformat(timespec="seconds"), "res": res},
          open(OUT, "w", encoding="utf-8"), indent=1)
with open(LOG, "w", encoding="utf-8") as f:
    for k in ("SGH", "GEM"):
        d = res.get(k, {"ok": False, "reason": "no result"})
        f.write("=" * 78 + "\n%s  ok=%s  %ss  $%s  %s\n" % (k, d.get("ok"), d.get("s"), d.get("usd"),
                                                            d.get("reason") or ""))
        if d.get("thinking_ratio") is not None:
            f.write("  tokens=%s  thinking_ratio=%s  task=%s\n" % (d.get("tokens"),
                                                                   d.get("thinking_ratio"), d.get("task")))
        f.write("=" * 78 + "\n" + (d.get("text") or "(no text)") + "\n\n")
print(open(LOG, encoding="utf-8").read()[:1500])
print("wrote %s" % LOG)
