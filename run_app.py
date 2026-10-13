"""Entry point used for the PyInstaller exe (and handy for `python run_app.py`)."""
import sys
import traceback

from gesture_control.main import main

if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        traceback.print_exc()
        code = 1
    if code and getattr(sys, "frozen", False):
        input("\nPress Enter to close...")      # keep the window open so the error can be read
    sys.exit(code)
