"""Builds synthetic 21-point hands (pixel coords) for tests.

Finger values are ratios: distance(wrist, tip) / distance(wrist, knuckle).
~1.9 = extended, ~0.85 = curled. `u` is the direction the fingers point
(image coords: (0,-1) = up, (1,0) = right).
"""
import math

CANON_MCP = {"index": (98, -20), "middle": (100, 0), "ring": (97, 20), "pinky": (88, 40)}
BASE = {"index": 5, "middle": 9, "ring": 13, "pinky": 17}
THUMB_CMC, THUMB_MCP, THUMB_TUCK = (15, -25), (40, -45), (80, -15)


def make_hand(index=1.9, middle=1.9, ring=1.9, pinky=1.9, u=(0.0, -1.0),
              thumb_dir=None, thumb_len=90.0, origin=(300.0, 300.0)):
    n = math.hypot(*u)
    u = (u[0] / n, u[1] / n)
    s = (-u[1], u[0])

    def img(a, b):
        return (origin[0] + u[0] * a + s[0] * b, origin[1] + u[1] * a + s[1] * b)

    pts = [None] * 21
    pts[0] = origin
    pts[1], pts[2] = img(*THUMB_CMC), img(*THUMB_MCP)
    if thumb_dir is None:
        pts[4] = img(*THUMB_TUCK)
    else:
        d = math.hypot(*thumb_dir)
        pts[4] = (pts[2][0] + thumb_dir[0] / d * thumb_len, pts[2][1] + thumb_dir[1] / d * thumb_len)
    pts[3] = ((pts[2][0] + pts[4][0]) / 2, (pts[2][1] + pts[4][1]) / 2)
    for name, r in (("index", index), ("middle", middle), ("ring", ring), ("pinky", pinky)):
        a, b = CANON_MCP[name]
        k = BASE[name]
        for j, f in enumerate((1.0, 1 + (r - 1) * 0.33, 1 + (r - 1) * 0.66, r)):
            pts[k + j] = img(a * f, b * f)
    return pts


def open_hand():
    return make_hand(thumb_dir=(-1, -0.3))


def fist():
    return make_hand(0.85, 0.85, 0.85, 0.85)


def point(direction):  # "right" / "left"
    u = (1, 0) if direction == "right" else (-1, 0)
    return make_hand(1.9, 0.85, 0.85, 0.85, u=u)


def thumb(direction):  # "up" / "down"
    return make_hand(0.85, 0.85, 0.85, 0.85, u=(1, 0), thumb_dir=(0, -1 if direction == "up" else 1))


def pinch_hand(gap_px=7):
    pts = make_hand(index=1.4)
    pts[4] = (pts[8][0] + gap_px, pts[8][1])
    return pts
