r"""
SRV1 hardware research — ECS KA3 MVP. SGH + GEM in parallel.
Keith 2026-07-16: "found a suitable system, Elite Group KA3 MVP MOBO... dual 10/100 and Gigabit ports,
32GB DDR2 RAM... 2x PCIe 16 slots. Jack is getting it I/O peripherals KVM and power on it now."

WHY DELEGATE THIS: a motherboard spec is IN THE WORLD (publisher manual, chipset datasheet). That is
exactly Rule 1's target. Contrast TB1's DOM, which only WE can see — that had to be measured.

⚠ TWO THINGS I DOUBT AND MUST NOT ASSERT WITHOUT A SOURCE:
  1. "32GB DDR2" — AM2-era boards typically cap at 8 GB (4x2GB unbuffered). 32 GB would be remarkable.
     THIS NUMBER IS LOAD-BEARING: RAM is the photo-library accelerator (page cache) in task A5.
  2. Keith earlier described SRV1 as "icore 5, DDR 3/4 era" and the network map says so. The KA3 MVP is
     AM2/DDR2, ~2006. Different machine, different decade. One of the two is wrong.
"""
import sys, json, time, datetime, threading
sys.path.insert(0, r"D:\Research2\Ai\BTS_MESH")

OUT = r"D:\Research2\Ai\BTS_MESH\_srv1_research_raw.json"
LOG = r"D:\Research2\Ai\BTS_MESH\_srv1_research.txt"

PROMPT = """Hardware spec question. I need PUBLISHER-SOURCED facts, not impressions.

BOARD: "Elite Group KA3 MVP" (ECS KA3 MVP). I believe it is AMD socket AM2, ATI Radeon Xpress 3200 /
RD580 chipset, DDR2, ~2006-2007. CORRECT ME IF THAT IS WRONG.

INTENDED JOB: a 24/7 LAN FILE SERVER (Linux + Samba/SMB3) on a gigabit home LAN. It will serve a
100-300 GB photo library (many small files - thumbnails, browsing) to two wired PCs, and hold a 3 TB
SATA drive plus possibly a second. Nothing else. No VMs, no transcoding.

Cite a URL + TIER (PUBLISHER = ECS manual/product page or AMD/ATI datasheet; GITHUB; FORUM = weak) for
EVERY claim. Write UNKNOWN rather than guess — I will check your sources, and I have caught two
fabrications from these rails today.

A) MAX RAM — THE MOST IMPORTANT QUESTION. What is the ECS KA3 MVP's MAXIMUM supported memory, per the
   ECS manual? How many DIMM slots, what DDR2 speeds, and what is the largest module it accepts
   (1 GB? 2 GB? 4 GB?)? **Is 32 GB possible on this board AT ALL?** I have been told it has 32 GB and I
   doubt it. If the real cap is 8 GB, say so plainly and cite the manual. Does it need unbuffered
   non-ECC, and does it support 4 GB unbuffered DDR2 DIMMs (did those even exist for AM2)?

B) NETWORK — how many onboard NICs, and what SPEED each? I have been told "dual 10/100 and Gigabit
   ports". Is that ONE gigabit + something else, or two? Give the exact controller chip
   (e.g. Marvell 88E8053, Realtek RTL8111). **Is the gigabit NIC on PCIe or on the PCI bus?** A gigabit
   NIC behind 32-bit PCI shares 133 MB/s with everything else and will NOT sustain ~110 MB/s.

C) SATA — how many SATA ports, what generation (SATA I 1.5 Gb/s or SATA II 3 Gb/s), which controller?
   Does it support drives >2 TB (a 3 TB drive needs GPT + a controller/BIOS that does not choke)? Any
   known 2.2 TB limit on this chipset?

D) CPU + POWER — what CPUs does it take (AM2: Athlon 64 X2? Phenom?), and what is realistic IDLE system
   power draw for this board + a low-end AM2 CPU + 2 spinning drives, in WATTS? This is the whole
   question for a 24/7 box: at ~$0.12/kWh, 100 W idle = ~$105/year, which is more than the entire rest
   of my plan costs. Give a number with a source if one exists; UNKNOWN if not.

E) LINUX + SMB REALITY CHECK — can an AM2-era CPU (say Athlon 64 X2 4200+, 2.2 GHz dual core) running
   Linux + Samba actually SATURATE gigabit (~110 MB/s) on large sequential reads? SMB is not usually
   CPU-bound at 1 GbE on modern hardware — is that still true on 2006 silicon? What is the realistic
   ceiling? Cite a benchmark if one exists.

F) THE PCIe x16 SLOTS — 2x PCIe x16 is claimed. On RD580 are they BOTH electrically x16, or x16 + x8/x4?
   Could one usefully hold a SATA HBA or a 2.5GbE NIC? Would a 2.5GbE card even help behind this
   chipset's uplink?

G) VERDICT IN ONE LINE: for a 24/7 gigabit Samba file server serving a photo library, is this board
   FINE, MARGINAL, or A MISTAKE? If it is a mistake, say what the actual blocker is (power? RAM? PCI-bus
   NIC?) - not vibes.
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
            "text": r.get("full_text") or r.get("text"), "usd": r.get("cost_usd")}

def gem():
    import bts_vertex
    bts_vertex.reset_task("srv1_research", cap_usd=0.02)
    r = bts_vertex.ask(PROMPT, model="gemini-2.5-flash")
    return {"ok": bool(r.get("ok")), "reason": r.get("reason"), "text": r.get("text"),
            "usd": r.get("cost_usd"), "tokens": r.get("tokens"), "thinking_ratio": r.get("thinking_ratio")}

ts = [threading.Thread(target=run, args=("SGH", sgh)), threading.Thread(target=run, args=("GEM", gem))]
print("firing SGH + GEM in parallel on the ECS KA3 MVP ...")
for t in ts: t.start()
for t in ts: t.join(timeout=420)

json.dump({"when": datetime.datetime.now().isoformat(timespec="seconds"), "res": res},
          open(OUT, "w", encoding="utf-8"), indent=1)
with open(LOG, "w", encoding="utf-8") as f:
    for k in ("SGH", "GEM"):
        d = res.get(k, {"ok": False, "reason": "no result"})
        f.write("="*78 + "\n%s  ok=%s  %ss  $%s  %s\n" % (k, d.get("ok"), d.get("s"), d.get("usd"),
                                                          d.get("reason") or ""))
        f.write("="*78 + "\n" + (d.get("text") or "(no text)") + "\n\n")
print("wrote %s" % LOG)
