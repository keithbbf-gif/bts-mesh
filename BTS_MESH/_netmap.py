r"""
_netmap.py — the OPTIMIZED network map, 2026-07-16.
Every number is either MEASURED on this box today or explicitly marked ESTIMATE.
House rule: a value that was never measured must not look like one that was.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

DPI = 200
INK   = "#12161c"; GREY = "#5f6ea0"; LGREY = "#eef1f5"; MGREY = "#c8d0dc"
GRN   = "#1d7a46"; RED = "#c0272d"; AMB = "#b06f00"; BLU = "#1f4e9c"
W, H  = 13.6, 9.4

fig = plt.figure(figsize=(W, H), dpi=DPI)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 136); ax.set_ylim(0, 94); ax.axis("off")
fig.patch.set_facecolor("white")

TITLE_GAP, LINE_H, PAD_TOP, PAD_BOT = 4.4, 2.9, 2.6, 2.2
def boxh(lines):
    """Height a box NEEDS. First version hardcoded h and every box overflowed its last line —
    the text does not know the box exists, so the box must be sized from the text."""
    return PAD_TOP + TITLE_GAP + LINE_H*len(lines) + PAD_BOT

def box(x, y, w, title, lines, edge=INK, fc="white", lw=1.6, tsz=10, lsz=7.6, ls="-"):
    """y = BOTTOM of the box. Height is derived, never passed."""
    h = boxh(lines)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.2",
                                ec=edge, fc=fc, lw=lw, ls=ls, zorder=3))
    ax.text(x + w/2, y + h - PAD_TOP, title, ha="center", va="top", fontsize=tsz,
            fontweight="bold", color=edge, zorder=4)
    for i, (t, c) in enumerate(lines):
        ax.text(x + w/2, y + h - PAD_TOP - TITLE_GAP - i*LINE_H, t, ha="center", va="top",
                fontsize=lsz, color=c, zorder=4)
    return h

def link(p1, p2, label, col, lw=2.2, ls="-", off=0.0, fs=7.8, lblcol=None, dash=None):
    a = FancyArrowPatch(p1, p2, arrowstyle="-", color=col, lw=lw, ls=ls,
                        shrinkA=2, shrinkB=2, zorder=2)
    if dash: a.set_linestyle((0, dash))
    ax.add_patch(a)
    mx, my = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2 + off
    ax.text(mx, my, label, ha="center", va="center", fontsize=fs, fontweight="bold",
            color=lblcol or col, zorder=5,
            path_effects=[pe.withStroke(linewidth=3.2, foreground="white")])

# ── title ───────────────────────────────────────────────────────────────────────────────────
ax.text(3, 90.5, "KMesh — optimised network", fontsize=17, fontweight="bold", color=INK)
ax.text(3, 87.0, "MEASURED on KC-PC 2026-07-16 unless marked ESTIMATE.", fontsize=8.4, color=GREY)
ax.text(3, 84.4, "Photo library = 100–300 GB.", fontsize=8.4, color=GREY)

# ── the finding ─────────────────────────────────────────────────────────────────────────────
ax.add_patch(FancyBboxPatch((80, 76), 52, 12, boxstyle="round,pad=0.6,rounding_size=1.2",
                            ec=RED, fc="#fff4f4", lw=2.0, zorder=3))
ax.text(82.5, 85.6, "THE BOTTLENECK IS NOT THE NETWORK.", fontsize=10.5, fontweight="bold", color=RED)
ax.text(82.5, 82.2, "The 8 TB Sabrent writes 20.7 MB/s — 5× BELOW the gigabit LAN\n"
                    "it already sits on. Moving it to SRV1 / the router / Jack's PC\n"
                    "changes nothing: the DRIVE is the floor, not the wire.",
        fontsize=8.0, color=INK, va="top")

# ── WAN ─────────────────────────────────────────────────────────────────────────────────────
box(2, 68, 27, "WAN — Vyve/Lumen",
    [("302 ↓ / 35.7 ↑ Mbps  (4.46 MB/s up)", GREY),
     ("upload is the scarce resource", AMB)], edge=GREY)

# ── router ──────────────────────────────────────────────────────────────────────────────────
box(44, 58, 33, "EA7500  ·  192.168.1.10",
    [("gigabit LAN  ·  DHCP .100–.149", GREY),
     ("USB + FTP tab present", GREY),
     ("✗ DO NOT serve files from its USB", RED),
     ("router CPU caps 10–40 MB/s [ESTIMATE]", RED)], edge=BLU)
link((29, 74), (44, 72), "302/35.7", GREY, lw=1.8, off=1.6)

# ── SRV1 ────────────────────────────────────────────────────────────────────────────────────
box(44, 26, 33, "SRV1  —  Linux + Samba (SMB3)",
    [("i5, DDR3/4 era  ·  you already own it", GRN),
     ("saturates gigabit ≈110 MB/s [ESTIMATE]", GRN),
     ("SMB is NOT CPU-bound at 1 GbE", GREY),
     ("→ ADD RAM: 8–16 GB ≈ $15", GRN),
     ("page-cache holds the thumbnails", GREY)], edge=GRN, lw=2.4)
link((60, 58), (60, 50), "1 Gbps", GRN, lw=3.0)

# ── KC-PC ───────────────────────────────────────────────────────────────────────────────────
box(2, 44, 31, "KC-PC  (Keith)",
    [("I219-V  ·  LINK 1 Gbps  ✓ MEASURED", GRN),
     ("C: SN850X  1584 MB/s w", GREY),
     ("V: ADATA  459 MB/s w  (447 GB free)", GREY),
     ("D: Passport  92.7 MB/s w", GREY)], edge=INK)
link((33, 58), (44, 64), "110 MB/s", GRN, lw=3.0, off=1.5)

# ── Jack ────────────────────────────────────────────────────────────────────────────────────
box(95, 48, 36, "Jack's PC  (JMesh)",
    [("NOW: wireless 5 GHz AC", RED),
     ("25–50 MB/s [ESTIMATE] — HIS ceiling", RED),
     ("no server upgrade can lift it", GREY),
     ("→ WIRE HIM: Cat5e/6 ≈ $12", GRN),
     ("25–50  →  110 MB/s", GRN)], edge=AMB, lw=2.2)
link((77, 70), (95, 68), "wifi 25–50", RED, lw=1.6, dash=(4, 3), off=1.9)
link((77, 62), (95, 57), "wired 110  ← DO THIS", GRN, lw=3.0, off=-2.0)

# ── drives ──────────────────────────────────────────────────────────────────────────────────
box(88, 36, 44, "3 TB Hitachi  →  PHOTO LIBRARY",
    [("~100–150 MB/s [ESTIMATE, CMR era]  ·  matches gigabit", GRN),
     ("⚠ SMART-check first: ~2012, hours unknown", AMB)], edge=GRN, lw=2.4)
link((77, 40), (88, 43), "SATA/USB", GRN, lw=2.4, off=1.5)

box(88, 19, 44, "+ 3 TB twin  ≈ $30  →  SECOND COPY",
    [("300 GB of irreplaceable product photography", GREY),
     ("on ONE 2012 drive is the actual risk", AMB)], edge=GRN, lw=1.6, ls="--")
link((110, 36), (110, 34), "", GREY, lw=1.2, dash=(3, 3))

box(88, 1, 44, "8 TB Sabrent (G:)  →  BACKUP ONLY",
    [("20.7 MB/s write  ✓ MEASURED  — SMR behaviour", RED),
     ("fine overnight · useless live", GREY),
     ("stays the Tera-4 mirror. Do NOT host the library.", RED)], edge=RED, lw=2.0)
link((77, 30), (88, 10), "USB3 · 21 MB/s = the floor", RED, lw=1.8, dash=(5, 3), off=2.4, fs=7.4)

# ── KS-124 ──────────────────────────────────────────────────────────────────────────────────
box(2, 26, 31, "KS-124 switch",
    [("24-port 10/100 = 12.5 MB/s", RED),
     ("✗ printers only — keep storage OFF it", RED)], edge=RED, lw=1.4, ls="--")
link((33, 33), (44, 34), "10/100", RED, lw=1.2, dash=(3, 3), off=1.5)

# ── verdict ─────────────────────────────────────────────────────────────────────────────────
ax.add_patch(FancyBboxPatch((2, 3), 40, 21, boxstyle="round,pad=0.6,rounding_size=1.2",
                            ec=INK, fc=LGREY, lw=1.8, zorder=3))
ax.text(4.5, 22.2, "THE SETUP  —  completes KMesh", fontsize=10.5, fontweight="bold", color=INK)
for i, (t, c) in enumerate([
        ("1.  SRV1 = the file server (Linux+Samba)      $0", GRN),
        ("2.  Photo library -> 3 TB Hitachi, NOT the 8TB", GRN),
        ("3.  8 TB Sabrent stays the BACKUP target      $0", GREY),
        ("4.  Skip the EA7500 USB (router CPU)          $0", GREY),
        ("5.  RAM in SRV1, 8-16 GB                    ~$15", GRN),
        ("6.  WIRE JACK - biggest single win          ~$12", GRN),
        ("7.  Optional 3 TB twin for copy #2          ~$30", GREY)]):
    ax.text(4.5, 18.9 - i*2.15, t, fontsize=7.6, color=c, family="DejaVu Sans Mono")
ax.text(4.5, 4.4, "TOTAL:  $0 – 45", fontsize=11, fontweight="bold", color=GRN)

# ── legend ──────────────────────────────────────────────────────────────────────────────────
ax.text(45, 22.0, "✓ MEASURED  = benched on KC-PC 2026-07-16 (seq write, flushed).", fontsize=7.0, color=GREY)
ax.text(45, 19.6, "[ESTIMATE]  = vendor spec / class behaviour — NOT measured here.", fontsize=7.0, color=GREY)
ax.text(45, 17.2, "Dashed      = a path you should NOT use, or one not yet built.", fontsize=7.0, color=GREY)
ax.text(45, 14.0, "⚠ Bench READ/4K numbers were PAGE-CACHE and are excluded —", fontsize=7.0, color=AMB)
ax.text(45, 11.6, "   nothing reads 4.5 GB/s off a USB spinner. Writes only.", fontsize=7.0, color=AMB)
ax.text(45, 8.4, "SRV1 completes KMesh for now (Keith, 2026-07-16).", fontsize=7.4, color=GRN, style="italic")

# Path must work from BOTH the Windows host and the Linux sandbox. The first run of this script
# hardcoded the D:\ path, ran in the sandbox, and created a FILE LITERALLY NAMED "V:\Research4\..."
# in the cwd — the classic bts_paths bug (see CLAUDE.md rule 2: the rails are pinned to Windows by
# hardcoded path strings, nothing else).
import os
_here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(_here, "KMESH_NETWORK_MAP_2026-07-16.png")
fig.savefig(out, dpi=DPI, facecolor="white", bbox_inches="tight", pad_inches=0.25)
print("wrote", out)
