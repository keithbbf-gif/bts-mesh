"""test_burn_packets.py — /api/burn packets object (phone/board/lock/tmp).

Peer-file stats only. No rail probe. Absent lock → FREE.
"""
import json, os, sys, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bts_serve as S

fails = []
def check(name, cond):
    print(("  PASS " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)

d = tempfile.mkdtemp(prefix="bts_burn_packets_")
try:
    paths = {
        "phone_cow_to_qa": os.path.join(d, "COW_TO_QA_ENGINEER.md"),
        "phone_qa_to_cow": os.path.join(d, "QA_ENGINEER_TO_COW.md"),
        "board": os.path.join(d, "board.json"),
        "lock": os.path.join(d, "tree_lock"),
        "tmp": os.path.join(d, "tmp", "temp_files.toml"),
    }

    print("== absent peers ==")
    p0 = S.packets(paths)
    check("lock FREE when absent", p0["lock"]["status"] == "FREE" and p0["lock"]["exists"] is False)
    check("mtime 0 / seq 0", p0["mtime"] == 0 and p0["seq"] == 0)
    check("phone pair present", "cow_to_qa" in p0["phone"] and "qa_to_cow" in p0["phone"])

    print("== live peers ==")
    open(paths["phone_cow_to_qa"], "w", encoding="utf-8").write("# cow -> qa\n")
    open(paths["phone_qa_to_cow"], "w", encoding="utf-8").write("# qa -> cow\n")
    json.dump({"seq": 7, "items": [{"status": "open"}, {"status": "done"}]},
              open(paths["board"], "w", encoding="utf-8"))
    os.makedirs(os.path.dirname(paths["tmp"]), exist_ok=True)
    open(paths["tmp"], "w", encoding="utf-8").write(
        "[[file]]\npath = \"a.tmp\"\n[[file]]\npath = \"b.tmp\"\nstatus = \"closed\"\n")
    open(paths["lock"], "w", encoding="utf-8").write("COWORK\n")

    p1 = S.packets(paths)
    check("phone mtime/size", p1["phone"]["cow_to_qa"]["exists"] and p1["phone"]["cow_to_qa"]["size"] > 0)
    check("board.seq", p1["board"]["seq"] == 7 and p1["seq"] == 7)
    check("board open count", p1["board"]["open"] == 1)
    check("lock HELD", p1["lock"]["status"] == "HELD" and p1["lock"]["holder"] == "COWORK")
    check("tmp open count", p1["tmp"]["open"] == 1)
    check("events painted", len(p1["events"]) >= 4)
    check("fingerprint mtime", p1["mtime"] > 0)

    print("== burn() ==")
    b = S.burn(paths)
    check("packets on burn", b["packets"]["seq"] == 7)
    check("gem+sgh still there", "gem" in b and "sgh" in b)
    check("no rail_check imported", "rail_check" not in sys.modules)
finally:
    shutil.rmtree(d, ignore_errors=True)

print("RESULT %s" % ("PASS" if not fails else "FAIL: " + ", ".join(fails)))
sys.exit(0 if not fails else 1)
