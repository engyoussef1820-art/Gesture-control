"""Turns a per-frame gesture stream into discrete actions.

Rules:
  * A gesture must be stable for `confirm_*_s` seconds AND `min_confirm_frames` frames.
  * One-shot gestures (arrows, pinch) fire ONCE when confirmed. They cannot fire
    again until the gesture has been absent longer than `release_grace_s`
    (a real release), and never twice within `cooldown_s`.
  * Continuous gestures (thumbs up/down) emit one volume step every
    `volume_interval_s` while held, and stop as soon as the gesture changes.
  * Short dropouts (< release_grace_s) of the active gesture are ignored (jitter).
"""
import math
from enum import Enum, auto

from .config import Config
from .gestures import Gesture


class Action(Enum):
    KEY_RIGHT = auto()
    KEY_LEFT = auto()
    KEY_SPACE = auto()
    VOLUME_UP = auto()
    VOLUME_DOWN = auto()


ONE_SHOT = {Gesture.POINT_RIGHT: Action.KEY_RIGHT,
            Gesture.POINT_LEFT: Action.KEY_LEFT,
            Gesture.PINCH: Action.KEY_SPACE}
CONTINUOUS = {Gesture.THUMB_UP: Action.VOLUME_UP,
              Gesture.THUMB_DOWN: Action.VOLUME_DOWN}


class GestureStateMachine:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.reset()

    def reset(self):
        self.active = None            # confirmed gesture currently held
        self.candidate = None         # gesture being confirmed
        self.candidate_since = 0.0
        self.candidate_frames = 0
        self.last_seen = 0.0          # last time `active` was observed
        self.last_fire = {}           # one-shot gesture -> time of last key press
        self.last_volume = 0.0

    def _confirm_time(self, g):
        if g == Gesture.PINCH:
            return self.cfg.confirm_pinch_s
        if g in CONTINUOUS:
            return self.cfg.confirm_volume_s
        return self.cfg.confirm_arrow_s

    def update(self, gesture, now):
        """Feed one frame's gesture; returns a list of Actions to execute (usually empty)."""
        cfg = self.cfg
        valid = gesture if (gesture in ONE_SHOT or gesture in CONTINUOUS) else None
        out = []

        if self.active is not None:
            if valid == self.active:
                self.last_seen = now
                if self.active in CONTINUOUS and now - self.last_volume >= cfg.volume_interval_s:
                    out.append(CONTINUOUS[self.active])
                    self.last_volume = now
                return out
            if valid is None and now - self.last_seen <= cfg.release_grace_s:
                return out                    # brief dropout: keep state, do nothing
            self.active = None                # released, or switched to another gesture
            self.candidate = None

        if valid is None:
            self.candidate = None
            self.candidate_frames = 0
            return out

        if valid != self.candidate:
            self.candidate = valid
            self.candidate_since = now
            self.candidate_frames = 1
            return out

        self.candidate_frames += 1
        if (self.candidate_frames < cfg.min_confirm_frames
                or now - self.candidate_since < self._confirm_time(valid)):
            return out

        if valid in ONE_SHOT:
            if now - self.last_fire.get(valid, -math.inf) < cfg.cooldown_s:
                return out
            out.append(ONE_SHOT[valid])
            self.last_fire[valid] = now
        else:
            out.append(CONTINUOUS[valid])
            self.last_volume = now
        self.active = valid
        self.last_seen = now
        return out
