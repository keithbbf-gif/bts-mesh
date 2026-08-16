# bts_gdx.py
"""
BTS GDX - Grok Build Worker Google Drive eXchange module.
Atomic uploads to the BTS_SGH_Handoff Drive folder, with a real byte-compare verify.

PROVENANCE
  v1  GBW (Grok Build Worker), BUILD-1, 2026-07-10.
  v2  GBW fix pass  -> closed D1 (header format), D2 (verify), D3 (folder check).
  v3  GBW fix pass  -> closed R1 (verify --note parity), R2 (Authorize on warm-start).
  v4  GBW fix pass  -> closed R4 (CRLF/LF byte asymmetry), R5 (header start-of-file check),
      BUT regressed R1 and R2 in the process. COWORK integrated: kept GBW's R4/R5 fixes
      and restored R1/R2. This file = GBW v4 + Cowork restoration.

STATUS: v4. D1-D3, R1, R2, R4, R5 all closed. Live-tested against Drive 2026-07-11.
  Verified by Cowork: uploaded bytes byte-match the re-derived expected bytes.
"""

import argparse
import json
import os
import tempfile
import time
from datetime import datetime, timezone

try:
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
except ImportError:
    raise ImportError("PyDrive2 is required. Install with: pip install PyDrive2")

# Configuration
FOLDER_ID = "1aiMjVZfFtiBGNAlkTwAYiq1Pvuz2F6hA"
SETTINGS_FILE = "settings.yaml"
LOG_FILE = "BTS_SIGNAL.log"

HANDOFF_HEADER = """<!-- HANDOFF HEADER -->
**SUMMARY:** {summary}
**OPEN_QUESTIONS:**
{questions}
**CONFIDENCE:** {confidence}
---
"""


def ensure_handoff_header(content: str, note: str = "") -> str:
    """Prepend the 3-field handoff header if missing.

    R5: the 'already has a header' test must check the START of the file. A plain
    `"<!-- HANDOFF HEADER -->" in content` substring test is wrong: this module (and
    the contract doc, and the verify reports) all MENTION the marker, so they would
    be misread as already-headered and silently get no header.
    """
    stripped = content.lstrip()
    if stripped.startswith("<!-- HANDOFF HEADER -->"):
        return content
    header = HANDOFF_HEADER.format(
        summary=note or "GBW build output",
        questions="- None",
        confidence="[V]",
    )
    return header + content


def get_drive() -> GoogleDrive:
    """Authenticate and return a GoogleDrive instance."""
    try:
        gauth = GoogleAuth(settings_file=SETTINGS_FILE)
        if os.path.exists("credentials.json"):
            gauth.LoadCredentialsFile("credentials.json")
        if gauth.credentials is None or gauth.access_token_expired:
            # Cold start / expired token: browser OAuth.
            gauth.LocalWebserverAuth()
        else:
            # R2: WARM START. Cached credentials are still valid, but Authorize()
            # must still run or the Drive service is never built. Dropping this
            # branch breaks every run after the first. (Regressed twice - keep it.)
            gauth.Authorize()
        gauth.SaveCredentialsFile("credentials.json")
        return GoogleDrive(gauth)
    except Exception as e:
        raise RuntimeError(f"Auth failure: {e}. Check settings.yaml and credentials.") from e


def put(local_path: str, note: str = ""):
    """Atomically upload a file into the GDX handoff folder."""
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local file not found: {local_path}")

    drive = get_drive()

    with open(local_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    uploaded_content = ensure_handoff_header(original_content, note)
    final_name = os.path.basename(local_path)

    temp_file_obj = None
    tmp_path = None

    try:
        # D3: really check the folder. CreateFile() alone never touches the API.
        folder = drive.CreateFile({"id": FOLDER_ID})
        folder.FetchMetadata()
        if folder["mimeType"] != "application/vnd.google-apps.folder":
            raise RuntimeError(f"ID {FOLDER_ID} is not a folder")

        # Upload under a temp name, then rename -> a reader never sees a half-file.
        temp_name = f"temp_{int(time.time())}_{final_name}"
        temp_file_obj = drive.CreateFile({
            "title": temp_name,
            "parents": [{"id": FOLDER_ID}],
        })

        # R4: BINARY mode. Text mode on Windows silently rewrites \n -> \r\n, so the
        # uploaded bytes stopped matching the bytes verify() re-derives, and the
        # byte-compare failed 100% of the time. Write the exact bytes.
        uploaded_bytes = uploaded_content.encode("utf-8")
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".tmp") as tmp:
            tmp.write(uploaded_bytes)
            tmp_path = tmp.name

        temp_file_obj.SetContentFile(tmp_path)
        temp_file_obj.Upload()

        # Atomic rename onto the final name.
        temp_file_obj["title"] = final_name
        temp_file_obj.Upload()

        ts = datetime.now(timezone.utc).isoformat()
        log_entry = {
            "type": "NEW_OUTPUT_READY",
            "path": final_name,
            "note": note,
            "ts": ts,
        }
        with open(LOG_FILE, "a", encoding="utf-8") as logf:
            logf.write(f"GBW|{json.dumps(log_entry)}\n")

        file_id = temp_file_obj.get("id")
        print(f"Successfully uploaded: {final_name} (ID: {file_id})")
        return file_id

    except Exception as e:
        # Never orphan a temp_* file in the shared folder.
        if temp_file_obj and temp_file_obj.get("id"):
            try:
                temp_file_obj.Delete()
            except Exception:
                pass
        raise RuntimeError(f"Upload failed: {e}") from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def verify(file_id: str, local_path: str, note: str = "") -> bool:
    """Download the uploaded file and byte-compare it to the expected bytes.

    R1: `note` MUST match the value passed to put(). The note becomes the header's
    SUMMARY, so without it the re-derived bytes differ and verify always FAILs.
    (Dropped twice on refactor - keep the parameter.)
    """
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local file not found: {local_path}")

    drive = get_drive()
    tmp_path = None
    try:
        with open(local_path, "r", encoding="utf-8") as f:
            original_content = f.read()
        expected_bytes = ensure_handoff_header(original_content, note).encode("utf-8")

        file_obj = drive.CreateFile({"id": file_id})
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        file_obj.GetContentFile(tmp_path)

        with open(tmp_path, "rb") as remote_f:
            remote_bytes = remote_f.read()

        match = remote_bytes == expected_bytes
        if match:
            print(f"Verify PASS for {file_id} ({len(remote_bytes)} bytes)")
        else:
            print(
                f"Verify FAIL for {file_id}: "
                f"remote {len(remote_bytes)} bytes vs expected {len(expected_bytes)} bytes"
            )
        return match

    except Exception as e:
        raise RuntimeError(f"Verify failed: {e}") from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="BTS GDX - Google Drive eXchange")
    subparsers = parser.add_subparsers(dest="command", required=True)

    put_parser = subparsers.add_parser("put", help="Upload a file atomically")
    put_parser.add_argument("local_path", help="Path to the local file")
    put_parser.add_argument("--note", default="", help="Note -> becomes the header SUMMARY")

    verify_parser = subparsers.add_parser("verify", help="Byte-compare an uploaded file")
    verify_parser.add_argument("file_id", help="Google Drive file ID")
    verify_parser.add_argument("local_path", help="Path to the local source file")
    verify_parser.add_argument(
        "--note",
        default="",
        help="The SAME --note used with put (must match, or verify will FAIL)",
    )

    args = parser.parse_args()

    try:
        if args.command == "put":
            put(args.local_path, args.note)
        elif args.command == "verify":
            ok = verify(args.file_id, args.local_path, args.note)
            exit(0 if ok else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1)


if __name__ == "__main__":
    main()
