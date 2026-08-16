"""
bts_sync.py — the OS-sync transport layer (Keith's design, 2026-07-11).

THE IDEA
    Let the OS do the syncing. Google Drive Desktop replicates D:\\BTS_SYNC\\GDX to
    Drive; OneDrive replicates D:\\BTS_SYNC\\ODX. The mesh then does nothing but
    ordinary local file I/O. No PyDrive2 OAuth on the Cowork side, no client_secrets
    on disk, no connector flakiness, no bespoke transfer code.

    Cowork writes -> Google/Microsoft push it up -> GEM / COPILOT see it.
    They write   -> it lands on disk    -> bts_dymon's watchdog fires (~1s).

    This is also what finally gives COPILOT a real rail: it is Microsoft-native and
    reads OneDrive, so ODX is the only surface it can actually use.

THE TRAP THIS MODULE EXISTS TO PREVENT
    Sync makes it very easy to ASSUME DELIVERY. "The file is on my disk" is NOT
    "the file is in the cloud and the other agent can see it." Sync can lag, stall,
    or leave a placeholder stub — and it looks perfectly fine locally the whole time.

    So verify() does not go away, it CHANGES JOB:
        old: "did my upload succeed?"
        new: "did the sync actually LAND?"
    Same no-fake-DONE guard, pointed at the new failure mode.

KNOWN GOTCHAS (both already bit this workspace once)
  * OneDrive Files On-Demand placeholders: a stub is stat-visible, reports a size, and
    is NOT actually there. Reading it fails or returns nothing. -> is_materialized()
    reads the bytes rather than trusting stat(). Set the folder to "Always keep on this
    device" or the mesh will read phantoms.
  * Sync propagates DELETIONS. These surfaces live OUTSIDE V:\\Research4 on purpose,
    so a mis-sync can never reach the archive. Never point a sync client at the archive.
  * Sync is NOT backup. It replicates corruption and deletion faithfully.
    R2/ITC remains the actual backup.
"""
from __future__ import annotations

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bts_bus  # noqa: E402

# --- the two transport surfaces -------------------------------------------------
#
# CORRECTED 2026-07-12. The first cut of this used D:\BTS_SYNC\{GDX,ODX} and would have
# FAILED SILENTLY. Two reasons, both worth remembering:
#
#  1. Google Drive Desktop's "folders from your computer" (mirroring D:\BTS_SYNC\GDX)
#     uploads into Drive's **Computers** section — a DIFFERENT place from My Drive.
#     SGH / GBW / GEM all read+write `BTS_SGH_Handoff` in **My Drive**. We'd have ended
#     up with two folders that look right and never talk to each other.
#     -> Correct approach: STREAM My Drive and use the REAL shared folder as the surface.
#        The local path IS the folder the agents already use. One folder, not two.
#
#  2. OneDrive cannot sync an arbitrary path. It only syncs what lives inside the
#     OneDrive folder. -> ODX must live at %OneDrive%\BTS_ODX.
#
ONEDRIVE_ROOT = os.environ.get("OneDrive") or r"C:\Users\Papa\OneDrive"

# The Drive letter Google assigns varies (G:, H:, ...). Find the real folder, don't guess.
GDX_DRIVE_SUBPATH = os.path.join("My Drive", "BTS_SGH_Handoff")


def _find_gdx() -> str | None:
    """Locate the streamed My Drive copy of BTS_SGH_Handoff, whatever letter it got."""
    for letter in "GHIJKLMNOPQRSTUVWXYZDEF":
        cand = os.path.join(f"{letter}:\\", GDX_DRIVE_SUBPATH)
        if os.path.isdir(cand):
            return cand
    return None


SURFACES = {
    # None until Google Drive Desktop is installed + streaming. We do NOT invent a path.
    "GDX": _find_gdx(),                                   # <-> GEM, GBW, SGH
    "ODX": os.path.join(ONEDRIVE_ROOT, "BTS_ODX"),        # <-> COPILOT
}

LOG_PATH = os.path.join(HERE, "BTS_SIGNAL.log")

# The Drive folder GDX is expected to sync to (for cloud-side verification).
GDX_DRIVE_FOLDER_ID = "1aiMjVZfFtiBGNAlkTwAYiq1Pvuz2F6hA"


def surface_path(surface: str) -> str:
    s = surface.upper()
    if s not in SURFACES:
        raise KeyError(f"unknown surface {surface!r}; known: {sorted(SURFACES)}")
    p = SURFACES[s]
    if not p:
        raise RuntimeError(
            "GDX surface not available: Google Drive Desktop is not streaming "
            "'My Drive\\BTS_SGH_Handoff' on any drive letter. Install Drive Desktop "
            "(Stream mode) and set that folder to 'Available offline'. "
            "Refusing to invent a local path that syncs nowhere."
        )
    return p


def _proc_running(exe: str) -> bool:
    """Is a sync client actually running? A folder with a dead client behind it is a
    trap: it looks like a working rail and delivers nothing."""
    try:
        import subprocess
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe}"],
            capture_output=True, text=True, timeout=10,
        ).stdout.lower()
        return exe.lower() in out
    except Exception:
        return False


def clients() -> dict:
    return {
        "onedrive_running": _proc_running("OneDrive.exe"),
        "google_drive_running": (_proc_running("GoogleDriveFS.exe")
                                 or _proc_running("DriveFS.exe")),
    }


# --------------------------------------------------------------------------------
# Stub detection — the OneDrive placeholder trap
# --------------------------------------------------------------------------------

def is_materialized(path: str) -> bool:
    """True only if the file's bytes are ACTUALLY on this disk.

    A OneDrive/Drive placeholder passes os.path.exists() and reports a size, but the
    content is not local. stat() lies; reading does not. So we read.
    """
    if not os.path.isfile(path):
        return False
    try:
        declared = os.path.getsize(path)
        with open(path, "rb") as f:
            data = f.read()
        if declared and not data:
            return False              # classic placeholder: size on paper, no bytes
        return len(data) == declared
    except OSError:
        return False                  # recall-on-open failed -> not really here


def wait_materialized(path: str, timeout: float = 30.0, interval: float = 0.5) -> bool:
    """Block until the bytes are genuinely local (sync pulled them down), or give up."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_materialized(path):
            return True
        time.sleep(interval)
    return False


# --------------------------------------------------------------------------------
# Write — atomic, so a reader (or a sync client mid-upload) never sees a half file
# --------------------------------------------------------------------------------

def put(surface: str, name: str, content: str, note: str = "", agent: str = "CLA") -> str:
    """Write a deliverable onto a sync surface and announce it on the bus.

    Atomic temp->rename is LOAD-BEARING here: the sync client watches the folder and
    will happily start uploading a half-written file if you stream straight into the
    final name.
    """
    from bts_schemas import HandoffHeader  # local import: keeps bts_sync importable bare

    root = surface_path(surface)
    os.makedirs(root, exist_ok=True)
    dest = os.path.join(root, name)

    if not HandoffHeader.present_in(content):
        content = HandoffHeader(
            summary=note or "mesh deliverable",
            open_questions=[],
            confidence="[G]",
        ).render() + content

    bts_bus.atomic_write(dest, content)   # temp -> fsync -> os.replace

    env = bts_bus.make_envelope(
        "NEW_OUTPUT_READY",
        note=note or f"{name} staged on {surface.upper()}",
        path=f"BTS_SYNC/{surface.upper()}/{name}",
    )
    bts_bus.append_signal(LOG_PATH, agent, env)
    return dest


# --------------------------------------------------------------------------------
# Verify — the NEW job: did the sync actually reach the cloud?
# --------------------------------------------------------------------------------

def verify_local(surface: str, name: str) -> bool:
    """Weak check: the bytes are really on this disk (not a stub). NOT proof of delivery."""
    return is_materialized(os.path.join(surface_path(surface), name))


def verify_cloud(surface: str, name: str) -> dict:
    """STRONG check: the file actually materialised in the cloud, where the other agent
    will look for it. This is the no-fake-DONE guard for the sync era.

    GDX: verifiable today via the Drive API (PyDrive2 credentials already exist).
    ODX: NOT verifiable from Cowork yet — we have no OneDrive API wired up. Rather than
         pretend, we say so. An unverifiable claim is exactly what this whole contract
         exists to prevent.
    """
    s = surface.upper()

    if s == "GDX":
        try:
            from pydrive2.auth import GoogleAuth
            from pydrive2.drive import GoogleDrive
        except ImportError:
            return {"verified": None, "reason": "PyDrive2 not installed"}
        try:
            gauth = GoogleAuth(settings_file="settings.yaml")
            if os.path.exists("credentials.json"):
                gauth.LoadCredentialsFile("credentials.json")
            if gauth.credentials is None or gauth.access_token_expired:
                gauth.LocalWebserverAuth()
            else:
                gauth.Authorize()
            drive = GoogleDrive(gauth)
            q = f"'{GDX_DRIVE_FOLDER_ID}' in parents and title='{name}' and trashed=false"
            hits = drive.ListFile({"q": q}).GetList()
            if not hits:
                return {"verified": False, "reason": f"{name} has NOT appeared in Drive yet"}
            local = os.path.join(surface_path(s), name)
            remote_size = int(hits[0].get("fileSize") or 0)
            local_size = os.path.getsize(local) if os.path.isfile(local) else -1
            return {
                "verified": remote_size == local_size,
                "file_id": hits[0]["id"],
                "remote_size": remote_size,
                "local_size": local_size,
                "reason": "size match" if remote_size == local_size else "SIZE MISMATCH - sync incomplete",
            }
        except Exception as e:
            return {"verified": None, "reason": f"Drive check failed: {e}"}

    if s == "ODX":
        return {
            "verified": None,
            "reason": ("ODX cloud-verify NOT IMPLEMENTED — no OneDrive API wired up from "
                       "Cowork. Local materialisation can be checked (verify_local), but "
                       "that is NOT proof Copilot can see it. Do not claim delivery."),
        }

    raise KeyError(f"unknown surface {surface!r}")


def await_sync(surface: str, name: str, timeout: float = 120.0, interval: float = 5.0) -> dict:
    """Write-then-confirm: poll the CLOUD until the file really lands, or time out."""
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        last = verify_cloud(surface, name)
        if last.get("verified") is True:
            return last
        if last.get("verified") is None:
            return last               # unverifiable (e.g. ODX) — say so, don't spin
        time.sleep(interval)
    last["reason"] = f"TIMEOUT after {timeout}s — {last.get('reason', '')}"
    return last


def status() -> dict:
    """Is each surface present, IS ITS SYNC CLIENT ACTUALLY RUNNING, and are any files stubs?

    A folder whose sync client is dead is the worst kind of failure: writes land, look
    perfect, and reach nobody. So we report the client, not just the folder.
    """
    cl = clients()
    out = {"clients": cl}
    for name, root in SURFACES.items():
        client_up = cl["google_drive_running"] if name == "GDX" else cl["onedrive_running"]
        if not root:
            out[name] = {
                "path": None,
                "exists": False,
                "sync_client_running": client_up,
                "READY": False,
                "problem": "Google Drive Desktop is not streaming My Drive\\BTS_SGH_Handoff",
            }
            continue
        exists = os.path.isdir(root)
        files = sorted(os.listdir(root)) if exists else []
        stubs = [f for f in files
                 if os.path.isfile(os.path.join(root, f))
                 and not is_materialized(os.path.join(root, f))]
        problems = []
        if not exists:
            problems.append("folder missing")
        if not client_up:
            problems.append("SYNC CLIENT NOT RUNNING — writes here reach nobody")
        if stubs:
            problems.append(f"{len(stubs)} placeholder stub(s) — set 'Always keep on this device'")
        out[name] = {
            "path": root,
            "exists": exists,
            "files": len(files),
            "placeholder_stubs": stubs,
            "sync_client_running": client_up,
            "READY": bool(exists and client_up and not stubs),
            "problem": "; ".join(problems) or None,
        }
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(status(), indent=2))
