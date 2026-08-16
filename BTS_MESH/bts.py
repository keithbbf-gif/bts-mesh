#!/usr/bin/env python3
"""
bts.py — command-line control for the BTS mesh. Pure stdlib.
Usage:
  bts.py send   <AGENT> <TYPE> <note> [--path P] [--root R]   append a signal
  bts.py log    [--root R] [--n 20]                            tail the signal log
  bts.py reg    [--root R]                                     show session registry
  bts.py discover [--root R]                                   run discovery pass
  bts.py dead   [--root R]                                     show dead-letter
  bts.py state  [--root R]                                     write+print mesh_state.json
  bts.py doctor [--root R]                                     run health check
"""
import sys, os, json, argparse
import bts_bus as B, bts_registry as R, bts_discovery as D, bts_state as S

def arg(a,k,default=None):
    return a[a.index(k)+1] if k in a else default

def main():
    a=sys.argv[1:]
    if not a: print(__doc__); return 0
    cmd=a[0]; root=arg(a,"--root",".")
    if cmd=="send":
        agent,typ,note=a[1],a[2],a[3]; path=arg(a,"--path")
        env=B.make_envelope(typ,note,path=path)
        B.append_signal(os.path.join(root,"BTS_SIGNAL.log"),agent,env)
        print("sent",env.get("mid") or typ)
    elif cmd=="log":
        n=int(arg(a,"--n","20")); lg=os.path.join(root,"BTS_SIGNAL.log")
        if not os.path.exists(lg): print("(no log)"); return 0
        for l in [x for x in open(lg) if x.strip()][-n:]:
            r=B._parse_line(l)
            if r: print(f"{r['env'].get('ts','?')}  {r['agent']:6} {r['env'].get('type'):16} {r['env'].get('note','')}")
    elif cmd=="reg":
        reg=R.load_registry(os.path.join(root,"SESSION_REGISTRY.json"))
        for s in reg["sessions"]: print(f"  {s.get('sid'):24} {s.get('agent'):8} {s.get('status'):10} {s.get('topic')}")
        if not reg["sessions"]: print("(no sessions)")
    elif cmd=="discover":
        add=D.discover_and_record(root); print("discovered:",json.dumps(add) if add else "(nothing new)")
    elif cmd=="dead":
        dl=os.path.join(root,"DEAD_LETTER.log")
        print(open(dl).read() if os.path.exists(dl) else "(clean — no dead letters)")
    elif cmd=="state":
        print(open(S.write(root)).read())
    elif cmd=="doctor":
        import bts_doctor; return bts_doctor.run(root)
    else:
        print("unknown cmd",cmd); print(__doc__); return 2
    return 0

if __name__=="__main__": sys.exit(main())
