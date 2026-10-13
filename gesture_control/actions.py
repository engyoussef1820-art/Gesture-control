"""Sends keys / volume changes on Windows using ctypes (no extra dependency)."""
import sys

from .state_machine import Action

# action -> (virtual-key code, is_extended_key)
_VK = {
    Action.KEY_RIGHT: (0x27, True),
    Action.KEY_LEFT: (0x25, True),
    Action.KEY_SPACE: (0x20, False),
    Action.VOLUME_UP: (0xAF, False),
    Action.VOLUME_DOWN: (0xAE, False),
}
_EXTENDED, _KEYUP = 0x0001, 0x0002


class Executor:
    def __init__(self, dry_run: bool = False):
        # dry_run only prints the action; it is also forced on non-Windows systems
        self.dry_run = dry_run or sys.platform != "win32"
        if not self.dry_run:
            import ctypes
            self._user32 = ctypes.windll.user32

    def execute(self, action: Action):
        if self.dry_run:
            print(f"[dry-run] {action.name}")
            return
        vk, ext = _VK[action]
        flags = _EXTENDED if ext else 0
        self._user32.keybd_event(vk, 0, flags, 0)            # key down
        self._user32.keybd_event(vk, 0, flags | _KEYUP, 0)   # key up
