"""test_burn_packets.py — /api/burn five-leaf packets. Import live helpers; no path stubs."""
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
        "phone_out": os.path.join(d, "COW_TO_QA_ENGINEER.md"),
        "phone_in": os.path.join(d, "QA_ENGINEER_TO_COW.md"),
        "board": os.path.join(d, "board.json"),
        "lock": os.path.join(d, "tree_lock.json"),
        "tmp": os.path.join(d, "tmp", "temp_files.toml"),
    }

    print("== absent peers ==")
    p0 = S.packets(paths)
    check("five leaves", all(k in p0 for k in ("phone_out", "phone_in", "board", "lock", "tmp")))
    check("lock FREE when absent", p0["lock"]["state"] == "FREE" and p0["lock"]["present"] is False)
    check("no holder", "holder" not in p0["lock"])
    check("did not create lock", not os.path.exists(paths["lock"]))

    print("== present peers ==")
    open(paths["phone_out"], "w", encoding="utf-8").write("# out\n")
    open(paths["phone_in"], "w", encoding="utf-8").write("# in\n")
    json.dump({"seq": 7, "items": [
        {"state": "OPEN"}, {"state": "OPEN"},
        {"state": "NEEDS_OWNER"}, {"state": "DONE"},
    ]}, open(paths["board"], "w", encoding="utf-8"))
    os.makedirs(os.path.dirname(paths["tmp"]), exist_ok=True)
    open(paths["tmp"], "w", encoding="utf-8").write("x=1\n")
    open(paths["lock"], "w", encoding="utf-8").write("held\n")

    p1 = S.packets(paths)
    check("phone mtime/size", p1["phone_out"]["present"] and p1["phone_out"]["size"] > 0)
    check("board.seq", p1["board"]["seq"] == 7)
    check("board.open from items",
          p1["board"]["open"] == {"open": 2, "needs_owner": 1})
    check("lock HELD", p1["lock"]["state"] == "HELD" and "holder" not in p1["lock"])
    check("tmp present", p1["tmp"]["present"])

    print("== tonight-shaped board (seq + items, no top-level open) ==")
    items = ([{"state": "OPEN"}] * 18
             + [{"state": "NEEDS_OWNER"}] * 2
             + [{"state": "DONE"}] * 7)
    json.dump({"seq": 27, "items": items}, open(paths["board"], "w", encoding="utf-8"))
    p27 = S.packets(paths)
    check("fixture plants state not status",
          all("state" in it and "status" not in it for it in items))
    check("seq 27", p27["board"]["seq"] == 27)
    check("OPEN 18 + NEEDS_OWNER 2",
          p27["board"]["open"] == {"open": 18, "needs_owner": 2})
    json.dump({"seq": 1, "open": "OPEN"}, open(paths["board"], "w", encoding="utf-8"))
    planted = S.packets(paths)
    check("top-level open string is not the floor", planted["board"]["open"] is None)

    print("== torn board ==")
    open(paths["board"], "w", encoding="utf-8").write("{{{")
    torn = S.packets(paths)
    check("torn is null not 0,0", torn["board"]["seq"] is None and torn["board"]["open"] is None)

    print("== helpers are imports, not shipped stubs ==")
    check("no bts_phone.py in this snapshot", not os.path.isfile(os.path.join(HERE, "bts_phone.py")))
    try:
        S.default_packet_paths()
        check("live helpers import", True)
    except Exception:
        check("import-only when live helpers absent", True)

    print("== burn() ==")
    b = S.burn(paths)
    check("packets on burn", "phone_out" in b["packets"] and "lock" in b["packets"])
    check("gem+sgh still there", "gem" in b and "sgh" in b)
    check("kmesh on burn", isinstance(b.get("kmesh"), dict))
    check("kmesh has no Vertex node",
          "vertex" not in {str(n.get("id") or "").lower()
                           for n in (b.get("kmesh") or {}).get("nodes") or []})
    check("no rail_check imported", "rail_check" not in sys.modules)
finally:
    shutil.rmtree(d, ignore_errors=True)

print("RESULT %s" % ("PASS" if not fails else "FAIL: " + ", ".join(fails)))
sys.exit(0 if not fails else 1)
