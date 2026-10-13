from gesture_control.config import Config
from gesture_control.gestures import Gesture as G
from gesture_control.selector import filter_hands, resolve
from gesture_control.state_machine import Action as A, GestureStateMachine

DT = 1 / 30


def feed(sm, gesture, seconds, t):
    out = []
    for _ in range(round(seconds / DT)):
        t += DT
        out += sm.update(gesture, t)
    return out, t


def make():
    return GestureStateMachine(Config()), 0.0


def test_no_hand_or_unknown_never_acts():
    sm, t = make()
    for g in (G.NONE, G.UNKNOWN, G.CONFLICT):
        out, t = feed(sm, g, 3, t)
        assert out == []


def test_single_pinch_gives_one_space_even_if_held():
    sm, t = make()
    out, t = feed(sm, G.PINCH, 3, t)
    assert out == [A.KEY_SPACE]


def test_release_then_pinch_again_gives_second_space():
    sm, t = make()
    out1, t = feed(sm, G.PINCH, 1, t)
    _, t = feed(sm, G.UNKNOWN, 0.4, t)
    out2, t = feed(sm, G.PINCH, 1, t)
    assert out1 == [A.KEY_SPACE] and out2 == [A.KEY_SPACE]


def test_short_flicker_does_not_repeat_space():
    sm, t = make()
    out, t = feed(sm, G.PINCH, 0.5, t)
    o, t = feed(sm, G.UNKNOWN, DT, t)       # one bad frame
    out += o
    o, t = feed(sm, G.PINCH, 1, t)
    out += o
    assert out == [A.KEY_SPACE]


def test_short_blip_is_ignored():
    sm, t = make()
    out, t = feed(sm, G.PINCH, 0.05, t)
    o, t = feed(sm, G.UNKNOWN, 1, t)
    assert out + o == []


def test_arrows_fire_once():
    for g, a in ((G.POINT_RIGHT, A.KEY_RIGHT), (G.POINT_LEFT, A.KEY_LEFT)):
        sm, t = make()
        out, t = feed(sm, g, 2, t)
        assert out == [a]


def test_volume_repeats_while_held_and_stops_on_release():
    sm, t = make()
    out, t = feed(sm, G.THUMB_UP, 1.0, t)
    assert set(out) == {A.VOLUME_UP} and 6 <= len(out) <= 12
    out, t = feed(sm, G.UNKNOWN, 1.0, t)
    assert out == []                          # nothing after release


def test_volume_up_to_down_switch_stops_up_immediately():
    sm, t = make()
    _, t = feed(sm, G.THUMB_UP, 0.6, t)
    out, t = feed(sm, G.THUMB_DOWN, 0.05, t)  # shorter than confirm time
    assert out == []                          # no UP, and DOWN not confirmed yet
    out, t = feed(sm, G.THUMB_DOWN, 0.6, t)
    assert out and set(out) == {A.VOLUME_DOWN}


def test_conflict_between_hands_executes_nothing():
    assert resolve([G.THUMB_UP, G.THUMB_DOWN]) == G.CONFLICT
    assert resolve([G.PINCH, G.POINT_RIGHT]) == G.CONFLICT
    sm, t = make()
    out, t = feed(sm, resolve([G.THUMB_UP, G.THUMB_DOWN]), 2, t)
    assert out == []


def test_conflict_cancels_active_volume():
    sm, t = make()
    _, t = feed(sm, G.THUMB_UP, 0.6, t)
    out, t = feed(sm, G.CONFLICT, 1.0, t)
    assert out == []


def test_resolve_hand_switching():
    assert resolve([]) == G.NONE
    assert resolve([G.POINT_RIGHT]) == G.POINT_RIGHT        # first hand
    assert resolve([]) == G.NONE                            # first hand leaves
    assert resolve([G.POINT_LEFT]) == G.POINT_LEFT          # second hand takes over
    assert resolve([G.UNKNOWN, G.POINT_LEFT]) == G.POINT_LEFT   # other hand idle -> still works
    assert resolve([G.UNKNOWN, G.UNKNOWN]) == G.UNKNOWN
    assert resolve([G.THUMB_UP, G.THUMB_UP]) == G.THUMB_UP  # both hands agree


def test_hand_leaves_and_returns_recovers_without_restart():
    sm, t = make()
    out1, t = feed(sm, G.POINT_RIGHT, 1, t)
    _, t = feed(sm, G.NONE, 1, t)
    out2, t = feed(sm, G.POINT_RIGHT, 1, t)
    assert out1 == [A.KEY_RIGHT] and out2 == [A.KEY_RIGHT]


def test_reset_clears_state():
    sm, t = make()
    _, t = feed(sm, G.THUMB_UP, 1, t)
    sm.reset()
    assert sm.active is None and sm.candidate is None


def test_filter_hands_by_side():
    hands, labels = ["H1", "H2"], ["Left", "Right"]
    assert filter_hands(hands, labels, "Any") == ["H1", "H2"]
    assert filter_hands(hands, labels, "Right") == ["H2"]
    assert filter_hands(hands, labels, "Left") == ["H1"]
    assert filter_hands(["H1"], [None], "Right") == []        # unknown side never controls
    assert resolve(filter_hands(["X"], ["Left"], "Right")) == G.NONE   # only the ignored hand visible
