"""Pure geometry: 21 hand landmarks (pixel coords) -> a Gesture.

No MediaPipe / OpenCV imports here, so everything can be unit-tested.
Landmark indices follow MediaPipe Hands: 0 wrist, 1-4 thumb, 5-8 index,
9-12 middle, 13-16 ring, 17-20 pinky (MCP, PIP, DIP, TIP in order).
"""
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from .config import Config


class Gesture(Enum):
    NONE = auto()        # no hand visible
    UNKNOWN = auto()     # hand visible but pose is not a supported / clear gesture
    CONFLICT = auto()    # two hands show different valid gestures
    THUMB_UP = auto()
    THUMB_DOWN = auto()
    POINT_LEFT = auto()
    POINT_RIGHT = auto()
    PINCH = auto()


VALID_GESTURES = {Gesture.THUMB_UP, Gesture.THUMB_DOWN, Gesture.POINT_LEFT,
                  Gesture.POINT_RIGHT, Gesture.PINCH}

# finger name -> (MCP index, TIP index)
FINGERS = {"index": (5, 8), "middle": (9, 12), "ring": (13, 16), "pinky": (17, 20)}


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


@dataclass
class Features:
    palm: float            # wrist -> middle MCP, in pixels
    ext: dict              # finger -> (wrist-to-tip) / (wrist-to-knuckle); ~0.8 curled, ~1.9 extended
    thumb_out: float       # thumb tip to index knuckle / palm
    pinch: float           # thumb tip to index tip / palm
    index_dir: tuple       # index knuckle -> tip vector (dx, dy)
    thumb_dir: tuple       # thumb MCP -> tip vector (dx, dy)


def extract_features(points) -> Optional[Features]:
    """Return None for missing / malformed / degenerate landmarks."""
    if points is None or len(points) != 21:
        return None
    if not all(len(p) >= 2 and math.isfinite(p[0]) and math.isfinite(p[1]) for p in points):
        return None
    palm = _dist(points[0], points[9])
    if palm <= 1e-6:
        return None
    ext = {}
    for name, (mcp, tip) in FINGERS.items():
        base = _dist(points[0], points[mcp])
        if base <= 1e-6:
            return None
        ext[name] = _dist(points[0], points[tip]) / base
    return Features(
        palm=palm,
        ext=ext,
        thumb_out=_dist(points[4], points[5]) / palm,
        pinch=_dist(points[4], points[8]) / palm,
        index_dir=(points[8][0] - points[5][0], points[8][1] - points[5][1]),
        thumb_dir=(points[4][0] - points[2][0], points[4][1] - points[2][1]),
    )


def _inside(points, frame_size, margin):
    w, h = frame_size
    return all(margin * w <= p[0] <= (1 - margin) * w and
               margin * h <= p[1] <= (1 - margin) * h for p in points)


def classify(points, cfg: Config, pinch_active: bool = False, frame_size=None) -> Gesture:
    """Classify one hand. Anything unclear returns UNKNOWN (never guesses).

    pinch_active: was the previous frame a pinch? Used for hysteresis so the
    pinch does not flicker near the threshold.
    """
    f = extract_features(points)
    if f is None or f.palm < cfg.min_palm_px:
        return Gesture.UNKNOWN
    if frame_size is not None and not _inside(points, frame_size, cfg.edge_margin):
        return Gesture.UNKNOWN   # partly out of frame -> landmarks are unreliable

    # 1) Pinch: thumb tip touches index tip, and the index is not a closed fist
    limit = cfg.pinch_off if pinch_active else cfg.pinch_on
    if f.pinch <= limit and f.ext["index"] >= cfg.pinch_min_index:
        return Gesture.PINCH

    state = {}
    for name, r in f.ext.items():
        state[name] = "ext" if r >= cfg.finger_extended else "curl" if r <= cfg.finger_curled else "mid"

    # 2) Pointing: index clearly extended, other three clearly curled, direction ~horizontal
    if state["index"] == "ext" and all(state[n] == "curl" for n in ("middle", "ring", "pinky")):
        dx, dy = f.index_dir
        if dx != 0 and abs(dx) >= cfg.horizontal_ratio * abs(dy):
            return Gesture.POINT_RIGHT if dx > 0 else Gesture.POINT_LEFT
        return Gesture.UNKNOWN   # diagonal / vertical pointing is ignored on purpose

    # 3) Thumbs up/down: four fingers clearly curled, thumb out and ~vertical
    if all(s == "curl" for s in state.values()) and f.thumb_out >= cfg.thumb_extended:
        dx, dy = f.thumb_dir
        if dy != 0 and abs(dy) >= cfg.vertical_ratio * abs(dx):
            return Gesture.THUMB_UP if dy < 0 else Gesture.THUMB_DOWN

    return Gesture.UNKNOWN   # open hand, fist, ambiguous poses ...


def explain_thumb(points, cfg: Config) -> str:
    """Short debug text: why a thumbs up/down is (not) recognised right now."""
    f = extract_features(points)
    if f is None:
        return "no valid landmarks"
    bad = [f"{n[:3]} {r:.2f}" for n, r in f.ext.items() if r > cfg.finger_curled]
    if bad:
        return f"not curled (need <={cfg.finger_curled}): " + ", ".join(bad)
    if f.thumb_out < cfg.thumb_extended:
        return f"thumb not out: {f.thumb_out:.2f} < {cfg.thumb_extended}"
    dx, dy = f.thumb_dir
    tilt = abs(dy) / max(abs(dx), 1e-6)
    if tilt < cfg.vertical_ratio:
        return f"thumb tilted: {tilt:.1f} < {cfg.vertical_ratio}"
    return "thumb OK " + ("up" if dy < 0 else "down")
