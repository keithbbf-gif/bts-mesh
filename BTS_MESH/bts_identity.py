r"""
bts_identity — WHO THIS MESH IS.  Created 2026-07-15 (Keith).
================================================================================
Keith, 2026-07-15: "Finish BTS-MESH, henceforth known as KMesh - and Jack's will
be JMesh. He's building it now. We will be connecting the two MESH on the local
network (possibly through a shared NAS drive on the LAN) and my brothers' MESHes
- HMesh (Harrison, MD in residency) and GMesh (2nd/3rd year law school)."

WHY THIS FILE EXISTS INSTEAD OF A DIRECTORY RENAME
--------------------------------------------------
The obvious reading of "henceforth known as KMesh" is: rename V:\Research4\Ai\
BTS_MESH -> KMESH. That is WRONG, and would actively block the thing Keith wants
next (federation). Reason:

    BTS_MESH is the SOFTWARE.   KMesh is an INSTANCE of it.

Jack is installing the same stack (Claude/Grok/TeraBox/OneDrive/GoogleDrive).
Harrison and Garrett will too. If the directory carries the owner's initial, then
Jack's box needs JMESH\, Harrison's HMESH\, and every hardcoded path, every
import, every publish rule and every peer's launcher diverges -> four FORKS of
one codebase before the first federation packet is ever sent. Renaming here also
breaks: 66 files / 135 path references, the Desktop .vbs launcher, the R2 publish
subtree (= live URLs under ai.dchambers.com), and WATCHDOG_STATE.

So the identity lives in a CONSTANT, not in a path. `git clone` the platform,
edit MESH_ID, done. That is what makes KMesh <-> JMesh possible at all.

MESH_ID is the ONLY line a new peer must change.
================================================================================
"""

# --- THIS mesh -----------------------------------------------------------------
MESH_ID    = "KMesh"
OWNER      = "Keith"
OWNER_MAIL = "keith.bbf@gmail.com"
ROLE       = "research"          # UPS / dissertation / physics
HOST       = "PAPA"              # ASUS PRIME Z370-A, i7-8700K

# --- The family mesh federation ------------------------------------------------
# status: "live" | "building" | "planned"
# NOTE: every field below that is not KMesh is UNVERIFIED - reported by Keith,
# not measured by me. Do not let these harden into facts. Jack's stack in
# particular is mid-install as of 2026-07-15 and nothing has been probed.
PEERS = {
    "JMesh": {
        "owner": "Jack", "mail": "ranny.bbf@gmail.com", "role": "general",
        "status": "building",           # [U] Keith-reported 2026-07-15
        "stack": ["claude", "grok", "terabox", "onedrive", "googledrive"],
        "link": "LAN",                  # same physical network as KMesh
        "note": "Mirrors Keith's mesh. Shared surface = TB1 (both accounts) "
                "and possibly a LAN NAS. First federation target.",
    },
    "HMesh": {
        "owner": "Harrison", "mail": None, "role": "medical",
        "status": "planned",
        "stack": [],
        "link": "WAN",
        "note": "MD in residency. Residency = near-zero spare time; his mesh "
                "must run with no babysitting. Data-scoping for H is KEITH'S "
                "call and is YEARS out (Keith 2026-07-16) — do not raise it.",
    },
    "GMesh": {
        "owner": "Garrett", "mail": None, "role": "legal",
        "status": "planned",
        "stack": [],
        "link": "WAN",
        "note": "Law school 2L/3L [U - Keith unsure], internship now. Legal "
                "work = privilege + confidentiality. Same warning as HMesh: no "
                "shared-surface sync until scoped. Citation-checking is the "
                "obvious high-value rail for him (same job as our DOI rail).",
    },
}

# --- Surfaces THIS mesh owns ---------------------------------------------------
SURFACES = ["ITC", "GDX", "ODX", "TB1", "LOCAL"]

# Candidate meeting points for KMesh <-> JMesh. NONE ARE BUILT.
# TB1 is the only one where both parties already hold an account.
MEETING_POINTS = {
    "TB1":  {"status": "candidate", "why": "Both Keith+Jack have TeraBox. "
             "Write rail PROVEN 2026-07-15 (h5Input0 File injection, verified "
             "server-side). BUT: 30 GB permanent + 994 GB bonus EXPIRING "
             "2026-08-14; and sharing needs a shared FOLDER, which is untested."},
    "NAS":  {"status": "proposed", "why": "Keith's idea 2026-07-15. LAN-local, "
             "no cloud quota, no vendor. UNTESTED - no NAS identified on this "
             "box yet. G: is labelled 'NAS1' (7452 GB, 3600 free) - VERIFY "
             "whether that is a real LAN NAS or a USB SABRENT enclosure; "
             "Get-PhysicalDisk says BusType=USB, so it is probably NOT a NAS "
             "despite the label. Do not build on G: until that is settled."},
    "GDX":  {"status": "candidate", "why": "Proven rail, but it is keith.bbf's "
             "Drive - 100 GB, 11.7 used. Sharing = permissions change."},
}


def whoami():
    return {"mesh_id": MESH_ID, "owner": OWNER, "host": HOST, "role": ROLE,
            "surfaces": SURFACES}


def peer(mesh_id):
    return PEERS.get(mesh_id)


def federation_ready():
    """Honest answer to 'can KMesh talk to JMesh yet?'  Currently: NO.

    Returns (ready: bool, blockers: list). Never returns True on optimism -
    each blocker must be knocked down by a MEASUREMENT, not a plan.
    """
    blockers = []
    if not any(p["status"] == "live" for p in PEERS.values()):
        blockers.append("No peer is live. JMesh is mid-install (Keith-reported, "
                        "unprobed). Nothing to talk to.")
    blockers.append("No meeting point exists. TB1 shared-folder = untested; "
                    "NAS = unidentified (G: is labelled NAS1 but reports "
                    "BusType=USB).")
    blockers.append("No wire protocol. bts_state.emit() is local-only; there is "
                    "no peer envelope, no addressing, no auth between meshes.")
    blockers.append("No trust model. A surface that syncs everything to everyone "
                    "is the wrong default. Per-peer data scoping is KEITH'S call "
                    "and is years out (2026-07-16) — do not design it.")
    # ---- BLOCKER 5, added 2026-07-31. GW's unique contribution to the KMESH
    # blueprint, and the only one of the four nodes to find it. It is a TOCTOU
    # hole at the core of the pointer architecture: verify_pointers.py going
    # GREEN proves the control tree was intact AT THAT INSTANT and says nothing
    # about the next instant. Any node with write access can edit a control file
    # after the check, and the following green run CERTIFIES the edited tree in
    # silence. Between meshes that is fatal — a peer would be trusting our
    # verifier's word about a tree it cannot see.
    blockers.append("No notarization of control files. A green verify_pointers "
                    "run is a point-in-time claim, not a standing one: any node "
                    "may rewrite a control file afterwards and the next green run "
                    "certifies it silently (TOCTOU). Federation requires the "
                    "checker to sign WHAT IT CHECKED — content hashes recorded at "
                    "verify time — so a peer can tell that the tree it is reading "
                    "is the tree that passed. GW, KMESH blueprint 2026-07-31.")
    return (False, blockers)


if __name__ == "__main__":
    import json
    print(json.dumps(whoami(), indent=2))
    ready, blk = federation_ready()
    print(f"\nfederation_ready = {ready}")
    for b in blk:
        print(f"  BLOCKER: {b}")
