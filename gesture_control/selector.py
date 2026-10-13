"""Combine the gestures of all visible hands into ONE gesture.

We do not track "which hand is which" (index 0 is not a stable identity).
Instead every visible hand is classified every frame and the result is
decided by a simple rule, so hand switching needs no stale state:
  - no hands            -> NONE
  - no valid gesture    -> UNKNOWN
  - one distinct valid  -> that gesture (either hand, or both doing the same)
  - different valid ones-> CONFLICT (nothing is executed)
"""
from .gestures import Gesture, VALID_GESTURES


def resolve(gestures):
    if not gestures:
        return Gesture.NONE
    valid = {g for g in gestures if g in VALID_GESTURES}
    if len(valid) > 1:
        return Gesture.CONFLICT
    if len(valid) == 1:
        return next(iter(valid))
    return Gesture.UNKNOWN


def filter_hands(hands, labels, wanted):
    """Keep only hands whose MediaPipe label ("Left"/"Right") equals `wanted`.

    wanted == "Any" keeps every hand. A hand with an unknown label (None) is
    dropped when a specific side is requested, so it can never trigger commands.
    """
    if wanted == "Any":
        return list(hands)
    return [h for h, label in zip(hands, labels) if label == wanted]
