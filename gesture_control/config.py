"""All tunable settings in one place.

Distances are relative to the palm length (wrist -> middle-finger knuckle),
so they do not depend on how far you sit from the camera.
"""
from dataclasses import dataclass


@dataclass
class Config:
    # --- camera / model ---
    camera_index: int = 0
    model_path: str = "hand_landmarker.task"
    num_hands: int = 2
    controller_hand: str = "Any"       # "Any", "Right" or "Left": which hand may give commands
    min_detection_conf: float = 0.6
    min_presence_conf: float = 0.6
    min_tracking_conf: float = 0.5
    max_read_failures: int = 30        # consecutive failed frames before giving up
    frame_width: int = 640             # smaller frames = faster processing
    frame_height: int = 480
    camera_fps: int = 30

    # --- geometry (ratios, see gestures.py) ---
    min_palm_px: float = 25.0          # ignore tiny / far-away hands
    edge_margin: float = 0.01          # hand touching the frame border -> UNKNOWN
    finger_extended: float = 1.50      # tip-to-wrist / knuckle-to-wrist >= this -> extended
    finger_curled: float = 1.30        # ... <= this -> curled; in between -> ambiguous
    thumb_extended: float = 0.60      # thumb tip to index knuckle / palm
    pinch_on: float = 0.25             # thumb-tip to index-tip distance / palm to START a pinch
    pinch_off: float = 0.45            # ... to END a pinch (hysteresis)
    pinch_min_index: float = 1.20      # index must not be fully curled (else a fist looks like a pinch)
    horizontal_ratio: float = 2.0      # pointing: |dx| >= ratio * |dy|
    vertical_ratio: float = 1.5        # thumb: |dy| >= ratio * |dx|

    # --- timing (seconds) ---
    min_confirm_frames: int = 2        # a gesture must also last this many frames
    confirm_arrow_s: float = 0.14     # hold time before an arrow key fires
    confirm_pinch_s: float = 0.08
    confirm_volume_s: float = 0.14
    release_grace_s: float = 0.12      # dropouts shorter than this do not count as a release
    cooldown_s: float = 0.25           # minimum gap between two one-shot key presses
    volume_interval_s: float = 0.11    # one volume step per interval while held
