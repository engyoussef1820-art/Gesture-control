import random

from gesture_control.config import Config
from gesture_control.gestures import Gesture, classify, explain_thumb
from tests.helpers import fist, make_hand, open_hand, pinch_hand, point, thumb

CFG = Config()
FRAME = (640, 480)


def c(pts, **kw):
    return classify(pts, CFG, frame_size=FRAME, **kw)


def test_supported_gestures():
    assert c(thumb("up")) == Gesture.THUMB_UP
    assert c(thumb("down")) == Gesture.THUMB_DOWN
    assert c(point("right")) == Gesture.POINT_RIGHT
    assert c(point("left")) == Gesture.POINT_LEFT
    assert c(pinch_hand()) == Gesture.PINCH


def test_open_hand_and_fist_are_unknown():
    assert c(open_hand()) == Gesture.UNKNOWN
    assert c(fist()) == Gesture.UNKNOWN   # fist must not look like a pinch or a thumb


def test_diagonal_pointing_is_unknown():
    for u in [(1, -1), (1, 1), (-1, -1), (-1, 1), (0, -1)]:
        assert c(make_hand(1.9, 0.85, 0.85, 0.85, u=u)) == Gesture.UNKNOWN


def test_ambiguous_finger_is_unknown():
    assert c(make_hand(1.3, 0.85, 0.85, 0.85, u=(1, 0))) == Gesture.UNKNOWN
    assert c(make_hand(1.9, 1.3, 0.85, 0.85, u=(1, 0))) == Gesture.UNKNOWN


def test_pinch_hysteresis():
    pts = pinch_hand(gap_px=35)                    # 0.35 palm: between on/off thresholds
    assert c(pts, pinch_active=False) != Gesture.PINCH
    assert c(pts, pinch_active=True) == Gesture.PINCH
    pts = pinch_hand(gap_px=60)
    assert c(pts, pinch_active=True) != Gesture.PINCH


def test_invalid_landmarks_are_unknown():
    assert classify(None, CFG) == Gesture.UNKNOWN
    assert classify([(0, 0)] * 5, CFG) == Gesture.UNKNOWN
    assert classify([(0, 0)] * 21, CFG) == Gesture.UNKNOWN            # zero-size hand
    bad = point("right")
    bad[8] = (float("nan"), 1.0)
    assert classify(bad, CFG) == Gesture.UNKNOWN


def test_hand_touching_frame_edge_is_unknown():
    pts = point("right")
    pts[8] = (FRAME[0] + 5, pts[8][1])                                 # fingertip outside the frame
    assert c(pts) == Gesture.UNKNOWN


def test_small_noise_does_not_change_result():
    rng = random.Random(1)
    for make, expected in [(lambda: point("right"), Gesture.POINT_RIGHT),
                           (lambda: thumb("up"), Gesture.THUMB_UP),
                           (open_hand, Gesture.UNKNOWN)]:
        for _ in range(200):
            noisy = [(x + rng.uniform(-1.5, 1.5), y + rng.uniform(-1.5, 1.5)) for x, y in make()]
            assert c(noisy) == expected


def test_explain_thumb_reports_the_blocking_condition():
    assert explain_thumb(thumb("up"), CFG) == "thumb OK up"
    assert explain_thumb(thumb("down"), CFG) == "thumb OK down"
    assert "not curled" in explain_thumb(make_hand(1.05, 0.85, 0.85, 0.85, u=(1, 0), thumb_dir=(0, -1)), CFG)
    assert "thumb not out" in explain_thumb(fist(), CFG)
    assert "tilted" in explain_thumb(make_hand(0.85, 0.85, 0.85, 0.85, u=(1, 0), thumb_dir=(1, -1)), CFG)
    assert explain_thumb(None, CFG) == "no valid landmarks"
