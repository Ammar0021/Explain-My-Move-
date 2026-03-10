
# engine_config.py  —  Explain My Move  v1.2
# Author: Ammar
#
# Contains:
#   ConfigManager  (Design Class 5)
#   get_stockfish_path()  — runtime path resolution (dev vs compiled .exe)
#
# Changes from v1.0 → v1.2:
#   - APP_VERSION constant added ("1.2")
#   - bad_move_threshold setting added: centipawn drop that classifies a
#     user-entered move as a "mistake", triggering the bad-move explanation
#     feature (new F09 — Bad Move Explanation).
#   - show_bad_move_analysis toggle added.
#   - validate_settings() extended to cover both new settings.


import sys
import os

APP_VERSION = "1.3"


# STOCKFISH PATH RESOLUTION


_DEV_STOCKFISH_PATH = (
    r"C:\Users\rahma\Desktop\Stuff\NEA\Explain-My-Move"
    r"\stockfish\stockfish-windows-x86-64-avx2.exe"
)

_STOCKFISH_FILENAME = "stockfish-windows-x86-64-avx2.exe"


def get_stockfish_path() -> str:
    """
    Returns the correct path to the Stockfish binary at runtime.

    When running as a compiled .exe (PyInstaller sets sys.frozen = True),
    bundled files are extracted to a temp directory at sys._MEIPASS.

    When running as a plain .py script during development, returns
    _DEV_STOCKFISH_PATH directly.
    """
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "stockfish", _STOCKFISH_FILENAME)
    else:
        return _DEV_STOCKFISH_PATH



# CONFIG MANAGER CLASS  (Design Section 3.2.2(d) — Class 5)


class ConfigManager:
    """
    Stores and validates all system configuration settings.

    Class constants:
        DEPTH_MIN / DEPTH_MAX           — engine depth slider bounds
        TIMEOUT_MIN / TIMEOUT_MAX       — analysis timeout bounds
        MULTIPV_MIN / MULTIPV_MAX       — multi-pv count bounds
        BAD_MOVE_THRESHOLD_MIN/MAX      — mistake detection threshold bounds

    v1.2 additions:
        bad_move_threshold  — centipawn drop at which a move is flagged (F09)
        show_bad_move_analysis — user-facing toggle for the feature
    """

    DEPTH_MIN   = 1
    DEPTH_MAX   = 20
    TIMEOUT_MIN = 1.0
    TIMEOUT_MAX = 30.0
    MULTIPV_MIN = 1
    MULTIPV_MAX = 5

    BAD_MOVE_THRESHOLD_MIN = 50
    BAD_MOVE_THRESHOLD_MAX = 500

    def __init__(self):
        self.settings: dict = {}
        self.load_config()

    def load_config(self):
        """Populates settings with application defaults."""
        self.settings = {
            "engine_path":             get_stockfish_path(),
            "engine_depth":            12,
            "timeout":                 10.0,
            "multipv_count":           3,
            "word_limit_beginner":     30,
            "word_limit_intermediate": 40,
            "mode":                    "Beginner",
            "dark_mode":               False,
            # v1.2 — bad-move analysis
            "bad_move_threshold":      100,
            "show_bad_move_analysis":  True,
            # v1.3 — JSON output toggle
            "show_json_output":        True,
        }
        self.validate_settings()

    def validate_settings(self):
        """
        Validates all settings. Raises ValueError if any value is out of bounds.
        Called after load_config() and after every update_setting() call.
        """
        d = self.settings

        if not isinstance(d.get("engine_path"), str) or not d["engine_path"]:
            raise ValueError("engine_path must be a non-empty string.")

        depth = d.get("engine_depth")
        if not isinstance(depth, int) or not (self.DEPTH_MIN <= depth <= self.DEPTH_MAX):
            raise ValueError(
                f"engine_depth must be an integer {self.DEPTH_MIN}–{self.DEPTH_MAX}. Got: {depth}"
            )

        timeout = d.get("timeout")
        if not isinstance(timeout, (int, float)) or not (
            self.TIMEOUT_MIN <= float(timeout) <= self.TIMEOUT_MAX
        ):
            raise ValueError(
                f"timeout must be {self.TIMEOUT_MIN}–{self.TIMEOUT_MAX}s. Got: {timeout}"
            )

        multipv = d.get("multipv_count")
        if not isinstance(multipv, int) or not (self.MULTIPV_MIN <= multipv <= self.MULTIPV_MAX):
            raise ValueError(
                f"multipv_count must be {self.MULTIPV_MIN}–{self.MULTIPV_MAX}. Got: {multipv}"
            )

        if d.get("mode") not in ("Beginner", "Intermediate"):
            raise ValueError(f"mode must be 'Beginner' or 'Intermediate'. Got: {d.get('mode')}")

        threshold = d.get("bad_move_threshold")
        if not isinstance(threshold, int) or not (
            self.BAD_MOVE_THRESHOLD_MIN <= threshold <= self.BAD_MOVE_THRESHOLD_MAX
        ):
            raise ValueError(
                f"bad_move_threshold must be {self.BAD_MOVE_THRESHOLD_MIN}–"
                f"{self.BAD_MOVE_THRESHOLD_MAX}. Got: {threshold}"
            )

        if not isinstance(d.get("show_json_output"), bool):
            raise ValueError(f"show_json_output must be a bool. Got: {d.get('show_json_output')}")

    def get_setting(self, key: str):
        """Safe read-only access. Raises KeyError for unknown keys."""
        if key not in self.settings:
            raise KeyError(
                f"ConfigManager: unknown key '{key}'. "
                f"Available: {list(self.settings.keys())}"
            )
        return self.settings[key]

    def update_setting(self, key: str, value):
        """
        Atomic write: updates the value then immediately re-validates.
        Restores the old value and re-raises if validation fails.
        """
        if key not in self.settings:
            raise KeyError(f"ConfigManager: unknown key '{key}'.")
        old = self.settings[key]
        self.settings[key] = value
        try:
            self.validate_settings()
        except ValueError:
            self.settings[key] = old
            raise
