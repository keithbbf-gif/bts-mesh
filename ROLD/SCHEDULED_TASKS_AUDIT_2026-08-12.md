# SCHEDULED TASKS — audit, 2026-08-12 (PLM-14)

**Two schedulers run this mesh and they are NOT interchangeable.**
A Cowork task runs in the Linux sandbox: it cannot see `V:` as a drive letter,
cannot run a `.bat`, caps a call at 45 s and cannot write a spend ledger across
the FUSE mount. That combination is what blinded `free-tier-allotment-check` for
seven days. A NATIVE Windows task runs where the drive letters and credentials
are real.

> **THE RULE:** anything touching `V:`, `D:` or a rail credential is a **NATIVE**
> task. Cowork tasks are for Cowork-only work.

| task | next run | status | verdict |
|---|---|---|---|
| `\BTS Drive Health` | 8/13/2026 2:15:00 AM | Ready | **KEEP, ELEVATED.** `Get-StorageReliabilityCounter` needs admin; unelevated it returns UNKNOWN. |
| `\BTS Publish Watch` | 8/12/2026 12:25:00 PM | Ready | 🔴 **RETIRE.** Its own disable condition — *once the wrapper writes the tally directly* — has been met since 2026-07-30. ~18,000 launches since, zero lines. |
| `\BTS Queue Runner` | 8/12/2026 12:25:00 PM | Running | **KEEP — the most load-bearing monitor in the mesh.** Intermittent as at 2026-08-12; needs the multiple-instances setting (PLM-37). |
| `\BTS Rail Check` | 8/13/2026 2:05:00 AM | Ready | **KEEP.** Writes RAIL_HEALTH daily and now adopts the elevated drive reading. |
| `\Microsoft\Windows\AppID\VerifiedPublisherCertStoreCheck` | N/A | Disabled | **REVIEW** — not yet classified. |
| `\Microsoft\Windows\Windows Error Reporting\QueueReporting` | 8/12/2026 3:07:14 PM | Ready | **REVIEW** — not yet classified. |
| `\Microsoft\Windows\Windows Error Reporting\QueueReporting` | 8/12/2026 3:12:53 PM | Ready | **REVIEW** — not yet classified. |
| `\Microsoft\Windows\Windows Error Reporting\QueueReporting` | 8/12/2026 3:14:22 PM | Ready | **REVIEW** — not yet classified. |
| `\Microsoft\Windows\Windows Error Reporting\QueueReporting` | 8/12/2026 3:23:41 PM | Ready | **REVIEW** — not yet classified. |
| `\Microsoft\Windows\Windows Error Reporting\QueueReporting` | 8/12/2026 3:35:55 PM | Ready | **REVIEW** — not yet classified. |
| `\R2 Publish Nightly` | 8/12/2026 10:00:00 PM | Ready | **KEEP.** Proven: ten dated OK lines in PUBLISH.log. Three nights genuinely missing (08-03/07/09). |

## Cowork-side tasks
Cowork's scheduler is not queryable from here. Known from the record:
`gdx-token-watch` (obsolete — PLM-07 removed the fuse), `bts-r2-watchdog-10min`
(ON DEMAND by Keith's ruling — **not a defect, do not 'fix' it**),
`import-samples-log` / `phd-work-driver-7min` / `free-tier-allotment-check`
(disabled, correctly).

⚠ **A disable CONDITION written into prose is a condition nobody evaluates.**
`BTS Publish Watch` proves it: the condition was met on 2026-07-30 and the task
ran ~18,000 more times because nothing tested the sentence.
