"""Webcam loop: camera -> MediaPipe -> classify -> resolve hands -> state machine -> keys.

Run:  python -m gesture_control            (add --dry-run to only print actions)
Keys in the window: P = pause, Q / Esc = quit.
"""
import argparse
import os
import sys
import time

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from .actions import Executor
from .config import Config
from .paths import find_file
from .gestures import Gesture, classify, explain_thumb, extract_features
from .selector import filter_hands, resolve
from .state_machine import GestureStateMachine

WINDOW = "Gesture Control"
CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9),
               (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
               (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]
MODEL_HELP = (
    "Model file not found: {path}\n"
    "Download it into the project folder with PowerShell:\n"
    "  Invoke-WebRequest -Uri https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task "
    "-OutFile hand_landmarker.task"
)


def open_camera(index, cfg):
    """Try several Windows backends; return an opened capture that delivers a frame, else None."""
    for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY):
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.frame_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.frame_height)
            cap.set(cv2.CAP_PROP_FPS, cfg.camera_fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)      # always process the newest frame
            ok, _ = cap.read()
            if ok:
                return cap
        cap.release()
    return None


def create_landmarker(cfg):
    model_path = find_file(cfg.model_path)       # works from any folder and inside the exe
    if not os.path.isfile(model_path):
        raise FileNotFoundError(MODEL_HELP.format(path=cfg.model_path))
    with open(model_path, "rb") as f:        # buffer avoids Windows non-ASCII path problems
        model = f.read()
    options = vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_buffer=model),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=cfg.num_hands,
        min_hand_detection_confidence=cfg.min_detection_conf,
        min_hand_presence_confidence=cfg.min_presence_conf,
        min_tracking_confidence=cfg.min_tracking_conf,
    )
    return vision.HandLandmarker.create_from_options(options)


def draw_hand(frame, pts, color=(0, 255, 0)):
    ip = [(int(x), int(y)) for x, y in pts]
    for a, b in CONNECTIONS:
        cv2.line(frame, ip[a], ip[b], color, 2)
    for p in ip:
        cv2.circle(frame, p, 3, (0, 0, 255), -1)


def run(cfg, debug=False, dry_run=False):
    try:
        landmarker = create_landmarker(cfg)
    except Exception as e:  # missing model, corrupt model, ...
        print(f"Could not start hand tracking:\n{e}")
        return 2

    cap = open_camera(cfg.camera_index, cfg)
    if cap is None:
        print("Could not open the camera. Close other apps that use it (Zoom, Teams, Camera) "
              "or try --camera 1.")
        landmarker.close()
        return 1

    machine = GestureStateMachine(cfg)
    executor = Executor(dry_run=dry_run)
    paused = False
    pinch_active = False
    last_action, last_action_t = "", 0.0
    t0, last_ts, fails = time.monotonic(), -1, 0
    fps, prev_t = 0.0, time.monotonic()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                fails += 1
                if fails >= cfg.max_read_failures:
                    print("Camera stopped delivering frames.")
                    return 1
                time.sleep(0.02)
                continue
            fails = 0

            frame = cv2.flip(frame, 1)               # mirror: pointing right = right on screen
            h, w = frame.shape[:2]
            now = time.monotonic()
            fps = 0.9 * fps + 0.1 / max(now - prev_t, 1e-6)   # smoothed FPS
            prev_t = now
            ts = max(int((now - t0) * 1000), last_ts + 1)   # MediaPipe needs increasing timestamps
            last_ts = ts
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = landmarker.detect_for_video(
                mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)

            all_hands = [[(lm.x * w, lm.y * h) for lm in hand] for hand in result.hand_landmarks]
            labels = [(c[0].category_name if c else None) for c in result.handedness]
            labels += [None] * (len(all_hands) - len(labels))
            # Only the allowed hand(s) may give commands; others are drawn in grey and ignored.
            hands = filter_hands(all_hands, labels, cfg.controller_hand)
            gestures = [classify(p, cfg, pinch_active, (w, h)) for p in hands]
            gesture = resolve(gestures)
            pinch_active = gesture == Gesture.PINCH

            if paused:
                machine.reset()
                actions = []
            else:
                actions = machine.update(gesture, now)
            for a in actions:
                executor.execute(a)
                last_action, last_action_t = a.name, now

            for p in all_hands:
                draw_hand(frame, p, (0, 255, 0) if any(p is q for q in hands) else (130, 130, 130))
            lines = [f"gesture: {gesture.name}" + ("   [PAUSED]" if paused else "") + f"   FPS: {fps:.0f}"]
            if last_action and now - last_action_t < 1.5:
                lines.append(f"action: {last_action}")
            if debug:
                lines.append(f"hands: {labels}  (control: {cfg.controller_hand})")
                for p in hands:
                    f = extract_features(p)
                    if f:
                        lines.append("thumb: " + explain_thumb(p, cfg))
                        e = f.ext
                        lines.append(f"idx {e['index']:.2f} mid {e['middle']:.2f} ring {e['ring']:.2f} "
                                     f"pky {e['pinky']:.2f} thumb {f.thumb_out:.2f} pinch {f.pinch:.2f}")
            for i, text in enumerate(lines):
                cv2.putText(frame, text, (10, 25 + 25 * i), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (255, 255, 255), 2)

            cv2.imshow(WINDOW, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if key in (ord("p"), ord("P")):
                paused = not paused
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break                                  # window closed with the X button
    finally:
        cap.release()
        landmarker.close()
        cv2.destroyAllWindows()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Hand gesture control")
    ap.add_argument("--camera", type=int, default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--hand", choices=["Any", "Right", "Left"], default=None,
                    help="which hand may give commands (default: Any)")
    ap.add_argument("--debug", action="store_true", help="show finger ratios on screen")
    ap.add_argument("--dry-run", action="store_true", help="print actions, do not press keys")
    args = ap.parse_args(argv)
    cfg = Config()
    if args.camera is not None:
        cfg.camera_index = args.camera
    if args.model:
        cfg.model_path = args.model
    if args.hand:
        cfg.controller_hand = args.hand
    return run(cfg, debug=args.debug, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
