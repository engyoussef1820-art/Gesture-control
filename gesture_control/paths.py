"""Find bundled files (the hand model) both in normal runs and in the PyInstaller exe."""
import os
import sys


def app_dirs():
    dirs = []
    if getattr(sys, "frozen", False):                 # running as a PyInstaller exe
        dirs.append(os.path.dirname(sys.executable))
        if hasattr(sys, "_MEIPASS"):                  # the "_internal" folder
            dirs.append(sys._MEIPASS)
    dirs.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # project root
    dirs.append(os.getcwd())
    return dirs


def find_file(name):
    """Return a full path for `name`; if it is not found, return `name` unchanged."""
    if os.path.isabs(name):
        return name
    for d in app_dirs():
        path = os.path.join(d, name)
        if os.path.isfile(path):
            return path
    return name
