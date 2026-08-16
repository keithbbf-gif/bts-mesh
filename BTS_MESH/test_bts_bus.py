import os, sys, glob, json, threading, tempfile
sys.path.insert(0, "/tmp/bts_mesh")
import bts_bus as B

fails = []
def check(name, cond):
    print(("  PASS " if cond else "  FAIL ") + name)
    if not cond: fails.append(name)

d = tempfile.mkdtemp(prefix="btstest_")
log = os.path.join(d, "BTS_SIGNAL.log")
cur_claude = os.path.join(d, ".cursor_claude")
cur_grok   = os.path.join(d, ".cursor_grok")

print("== atomic_write ==")
p = os.path.join(d, "sub/dir/out.md")
B.atomic_write(p, "hello world\n" * 1000)
check("file exists + full content", os.path.exists(p) and open(p).read().count("hello world") == 1000)
check("no .tmp_ leftovers", len(glob.glob(os.path.join(d, "sub/dir/.tmp_*"))) == 0)

print("== envelope validation ==")
try:
    B.make_envelope("BOGUS", "x"); check("rejects bad type", False)
except ValueError: check("rejects bad type", True)
try:
    B.make_envelope("NEW_OUTPUT_READY", "note", path=None); check("requires path", False)
except ValueError: check("requires path", True)
try:
    B.make_envelope("TASK_COMPLETE", ""); check("requires note", False)
except ValueError: check("requires note", True)
e = B.make_envelope("NEW_OUTPUT_READY", "staged X", path="SGH_returns/x.md")
check("good envelope builds", e["type"] == "NEW_OUTPUT_READY" and e["ts"].endswith("Z"))

print("== append + cursor + self-filter ==")
B.append_signal(log, "SGH", B.make_envelope("NEW_OUTPUT_READY", "batch B done", path="SGH_returns/b.md"))
B.append_signal(log, "SGH", B.make_envelope("TASK_COMPLETE", "idle now"))
got = B.read_new_signals(log, cur_claude, mine="CLA")   # Claude reads Grok's 2
check("claude sees 2 new", len(got) == 2)
check("first is NEW_OUTPUT_READY", got[0]["env"]["type"] == "NEW_OUTPUT_READY")
again = B.read_new_signals(log, cur_claude, mine="CLA")
check("cursor advanced (0 on re-read)", len(again) == 0)

# Claude ACKs -> Grok should see 1, and Claude should NOT see its own ACK
B.append_signal(log, "CLA", B.make_envelope("ACK", "read+integrated b", path="SGH_returns/b.md"))
grok_got = B.read_new_signals(log, cur_grok, mine="SGH")  # grok filters its own -> sees only CLA ack (1)
check("grok sees only claude's ack (self-filter)", len(grok_got) == 1 and grok_got[0]["env"]["type"] == "ACK")
claude_got = B.read_new_signals(log, cur_claude, mine="CLA")
check("claude does not re-consume, ignores own ack", len(claude_got) == 0)

print("== concurrent appends (20 threads) don't corrupt lines ==")
log2 = os.path.join(d, "concurrent.log")
def worker(i):
    B.append_signal(log2, "SGH" if i % 2 else "CLA",
                    B.make_envelope("TASK_COMPLETE", f"msg {i}"))
ts = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
[t.start() for t in ts]; [t.join() for t in ts]
lines = [l for l in open(log2) if l.strip()]
parsed_ok = sum(1 for l in lines if B._parse_line(l) is not None)
check("all 20 lines present", len(lines) == 20)
check("all 20 lines parse (no interleave corruption)", parsed_ok == 20)

print("== SPAWN_SESSION envelope (mesh) ==")
sp = B.make_envelope("SPAWN_SESSION", "spin up grok for lit sweep",
                     agent="grok", topic="lit-sweep", seed_path="SESSION_SEED_lit-sweep.md")
check("spawn carries routing extras", sp.get("agent") == "grok" and sp.get("seed_path"))

print()
print("RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL -> {fails}")
sys.exit(1 if fails else 0)
