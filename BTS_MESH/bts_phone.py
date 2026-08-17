"""bts_phone — the V:\\Ai letter pair.

OUTBOX / INBOX are peer-file paths (the letters), not a bus and not CHANNELS
through cowork. Callers stat them; this module does not create them.
"""
from bts_paths import airoot

OUTBOX = airoot("COW_TO_QA_ENGINEER.md")
INBOX = airoot("QA_ENGINEER_TO_COW.md")
