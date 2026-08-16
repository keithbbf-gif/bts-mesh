#!/usr/bin/env python3
"""
bts_figdig.py — headless figure digitizer for PUBLISHED SPECTRA.
Author: Cowork/Claude, 2026-07-13. Standard deps only: numpy + Pillow.

WHY NOT AN OFF-THE-SHELF TOOL
  WebPlotDigitizer, PlotDigitizer (dilawar), graph_grabber, StarryDigitizer, PinPoint — all surveyed
  2026-07-13. Every one of them is built around a HUMAN CLICKING IN A GUI to set axes and pick points,
  and their auto-extractors assume ONE curve on a clean background. Our targets are the opposite case:
  1970s printed synchrotron figures (Freeouf 1973; Lindau 1976) with a WATERFALL of stacked traces,
  which is precisely where those tools fail. So this is headless, scriptable, and follows one trace at
  a time through a crowded panel.

  (Their licences are also mostly GPL. This file is ours, so nothing is inherited.)

WHAT IT DOES
  Given an image and a 2-point-per-axis calibration, it walks the plot column by column, finds the
  dark pixels belonging to ONE trace, and follows it by CONTINUITY (nearest-to-previous), which is what
  keeps it from jumping onto a neighbouring trace in a waterfall.

USAGE
    from bts_figdig import calibrate, digitize
    cal = calibrate(px=[(120, 0.0), (980, 20.0)],      # (pixel_x, axis_value) x2  -- e.g. BE axis
                    py=[(760, 0.0), (100, 1.0)])       # (pixel_y, axis_value) x2  -- e.g. intensity
    xy  = digitize("freeouf_fig2.png", cal,
                   roi=(110, 90, 990, 770),            # left, top, right, bottom (pixels)
                   seed=(120, 300),                    # a pixel ON the trace you want
                   darkness=0.55)                      # 0..1; lower = only very dark ink counts
    # -> numpy array, shape (N, 2), columns = (axis_x, axis_y)

CALIBRATION IS THE WHOLE GAME. Digitizing is easy; getting the axes right is where the error lives.
Use TICK MARKS, not the axis frame, and use two ticks as FAR APART as the figure allows. A 1-pixel
error on a 10-pixel baseline is 10%; on an 800-pixel baseline it is 0.1%.

REVERSED AXES (binding energy usually runs right-to-left) are handled automatically: just give the
two calibration points with their true values and the sign takes care of itself.

VERIFY EVERY EXTRACTION. `selftest()` renders a curve with KNOWN values, digitizes it, and reports the
error. Run it whenever the code or the input class changes. A digitizer that has never been shown to
FAIL is not a digitizer -- it is a random number generator with a plot.
"""
import numpy as np
from PIL import Image


# ------------------------------------------------------------------ calibration
def calibrate(px, py):
    """px = [(pixel_x, value), (pixel_x, value)] ; py = [(pixel_y, value), (pixel_y, value)]"""
    (x1, vx1), (x2, vx2) = px
    (y1, vy1), (y2, vy2) = py
    if x1 == x2 or y1 == y2:
        raise ValueError("calibration points must differ in pixel coordinate")
    return {"ax": (vx2 - vx1) / (x2 - x1), "bx": vx1 - (vx2 - vx1) / (x2 - x1) * x1,
            "ay": (vy2 - vy1) / (y2 - y1), "by": vy1 - (vy2 - vy1) / (y2 - y1) * y1}


def _to_value(cal, xs, ys):
    return cal["ax"] * xs + cal["bx"], cal["ay"] * ys + cal["by"]


# ------------------------------------------------------------------ the extractor
def digitize(path, cal, roi=None, seed=None, darkness=0.55, max_jump=25, smooth=0):
    """Follow ONE trace through the panel and return its (x, y) in AXIS units.

    roi       : (l, t, r, b) pixel box of the plotting area — excludes axes, labels, legend.
    seed      : (px, py) a pixel ON the trace to follow. Required in a waterfall; without it the
                darkest run in the first column is taken, which is a coin flip when traces overlap.
    darkness  : ink threshold on 0..1 (0 = black). Printed 1970s figures: 0.5-0.65 works.
    max_jump  : max vertical pixel move allowed between adjacent columns. This is the ANTI-JUMP guard:
                a real spectrum is continuous; a jump to a neighbouring trace is not. Raise it only if
                the trace has genuinely steep edges (a Fermi edge on a compressed axis can be steep).
    smooth    : optional boxcar over the extracted y, in columns. 0 = none. Prefer 0 and smooth later,
                so the raw extraction stays auditable.
    """
    im = Image.open(path).convert("L")
    a = np.asarray(im, dtype=float) / 255.0          # 0 = black, 1 = white
    if roi:
        l, t, r, b = roi
    else:
        t, l = 0, 0
        b, r = a.shape
    sub = a[t:b, l:r]
    ink = sub < darkness                              # True where there is ink

    ys, cols = [], []
    prev = None if seed is None else (seed[1] - t)

    for c in range(sub.shape[1]):
        rows = np.where(ink[:, c])[0]
        if rows.size == 0:
            continue
        # group contiguous runs of ink (a trace is a run; two traces are two runs)
        runs, start = [], rows[0]
        for i in range(1, rows.size):
            if rows[i] != rows[i - 1] + 1:
                runs.append((start, rows[i - 1])); start = rows[i]
        runs.append((start, rows[-1]))
        centres = np.array([(s + e) / 2.0 for s, e in runs])

        if prev is None:
            pick = centres[np.argmax([e - s for s, e in runs])]   # thickest run in column 0
        else:
            d = np.abs(centres - prev)
            if d.min() > max_jump:                                 # the trace vanished (gridline gap,
                continue                                           # label, tick) — skip, do not guess
            pick = centres[np.argmin(d)]
        prev = pick
        ys.append(pick + t); cols.append(c + l)

    if not cols:
        raise RuntimeError("no trace found — check roi / darkness / seed")

    xs = np.array(cols, dtype=float)
    yy = np.array(ys, dtype=float)
    if smooth and smooth > 1:
        k = np.ones(int(smooth)) / float(int(smooth))
        yy = np.convolve(yy, k, mode="same")

    vx, vy = _to_value(cal, xs, yy)
    return np.column_stack([vx, vy])


# ------------------------------------------------------------------ NEGATIVE CONTROL
def selftest(tmp="_figdig_selftest.png", verbose=True):
    """Render a curve whose values we KNOW, digitize it, and measure the error.

    This is the whole point. If this ever fails, every number this module produced is suspect.
    It also plants a SECOND, nearby trace — the waterfall trap — so a pass proves the follower does
    not hop onto its neighbour.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = np.linspace(0.0, 20.0, 2000)
    truth = 0.35 + 0.5 * np.exp(-((x - 6.0) ** 2) / 2.0) + 0.25 * np.exp(-((x - 12.0) ** 2) / 8.0)
    decoy = truth - 0.22                                   # the neighbouring trace, 0.22 below

    fig, ax = plt.subplots(figsize=(8, 5), dpi=110)
    ax.plot(x, decoy, color="k", lw=1.4)                   # the trap
    ax.plot(x, truth, color="k", lw=1.4)                   # the target
    ax.set_xlim(20, 0)                                     # REVERSED, like a binding-energy axis
    ax.set_ylim(0, 1.2)
    fig.savefig(tmp)                                       # NOT bbox_inches='tight' — that would
    plt.close(fig)                                         # invalidate the transform below

    # Calibrate from matplotlib's OWN data->pixel transform, so this test measures the EXTRACTOR and
    # not my ability to eyeball a tick. (In real use the calibration comes from tick marks, and its
    # error adds to whatever this test reports — see the docstring.)
    H = fig.canvas.get_width_height()[1]
    def to_px(xv, yv):
        p = ax.transData.transform((xv, yv))
        return float(p[0]), float(H - p[1])                # matplotlib y is bottom-up; images are top-down

    x1, _ = to_px(2.0, 0.0); x2, _ = to_px(18.0, 0.0)      # two well-separated "ticks"
    _, y1 = to_px(0.0, 0.2); _, y2 = to_px(0.0, 1.0)
    cal = calibrate(px=[(x1, 2.0), (x2, 18.0)], py=[(y1, 0.2), (y2, 1.0)])

    lpx, _ = to_px(19.8, 0.0); rpx, _ = to_px(0.2, 0.0)
    _, tpx = to_px(0.0, 1.18); _, bpx = to_px(0.0, 0.02)
    roi = (int(min(lpx, rpx)) + 1, int(tpx) + 1, int(max(lpx, rpx)) - 1, int(bpx) - 1)

    sx, sy = to_px(19.5, float(np.interp(19.5, x, truth)))   # seed ON the target, not the decoy
    got = digitize(tmp, cal, roi=roi, seed=(int(sx), int(sy)), darkness=0.5)

    # compare on the target curve
    gi = np.argsort(got[:, 0])
    gx, gy = got[gi, 0], got[gi, 1]
    ref = np.interp(gx, x, truth)
    err = gy - ref
    rms = float(np.sqrt(np.mean(err ** 2)))
    mx = float(np.max(np.abs(err)))
    span = float(truth.max() - truth.min())
    ok = rms < 0.01 * span * 3 and mx < 0.05 * span        # generous: 3% rms, 5% worst-case of span

    if verbose:
        print("bts_figdig selftest — NEGATIVE CONTROL (a decoy trace sits 0.22 below the target)")
        print("  points recovered : %d" % len(gx))
        print("  rms error        : %.4f  (%.2f%% of the curve's span)" % (rms, 100 * rms / span))
        print("  worst-case error : %.4f  (%.2f%% of span)" % (mx, 100 * mx / span))
        print("  x-range recovered: %.2f -> %.2f  (true 0 -> 20, axis reversed)" % (gx.min(), gx.max()))
        print("  VERDICT          : %s" % ("PASS" if ok else "FAIL — do not trust extractions"))
    return ok, rms, mx


if __name__ == "__main__":
    selftest()
