"""Find the Android emulator window (LDPlayer / BlueStacks / Nox / MEmu).

On Windows we ask the OS for the emulator's window rectangle directly, so
capture.py can point the camera ONLY at the emulator instead of the whole
desktop. That's what caused the infinite hall-of-mirrors preview: with a
fullscreen capture, the preview window sits inside its own screenshot and
photographs itself forever.

Coordinates are physical pixels (we opt into DPI awareness first), which
matches what mss captures. Safe to import on any platform: on non-Windows
every function here just returns None.
"""
import sys

DEFAULT_KEYWORDS = ("ldplayer", "bluestacks", "nox", "memu", "gameloop")


def _ensure_dpi_aware():
    """Make GetWindowRect agree with mss (physical pixels, not scaled)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()  # system-wide fallback
    except Exception:
        pass


def find_emulator_window(keywords=DEFAULT_KEYWORDS):
    """Return (left, top, width, height) of the emulator window, or None.

    Picks the largest visible top-level window whose title contains one of
    the keywords (case-insensitive). None when the emulator isn't open or
    we're not on Windows.
    """
    if sys.platform != "win32":
        return None
    _ensure_dpi_aware()
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    matches = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def enum_cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if any(k in title.lower() for k in keywords):
            rect = wintypes.RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                w, h = rect.right - rect.left, rect.bottom - rect.top
                if w > 100 and h > 100:  # skip tiny helper windows
                    matches.append((w * h, title,
                                    (rect.left, rect.top, w, h)))
        return True

    user32.EnumWindows(enum_cb, 0)
    if not matches:
        return None
    matches.sort(reverse=True)
    _area, title, rect = matches[0]
    print(f"found emulator window '{title}' at {rect[0]},{rect[1]} "
          f"{rect[2]}x{rect[3]} — bring it to the front so the game shows")
    return rect
