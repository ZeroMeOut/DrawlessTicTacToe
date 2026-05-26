"""
games/menu_screen.py
────────────────────
Main menu screen.

Responsibilities
  • Animated progress bar while GEMINI_API_KEY is being validated.
  • Lock / unlock LLM-dependent modes based on validation result.
  • Model picker (← →) shown once the key is valid.
  • Returns (Mode, model_str) on Enter, None otherwise.
"""

import curses
import time
import threading

from .constants import (
    AVAILABLE_MODELS, MODE_LABELS, Mode,
    C_HIGHLIGHT, C_LOCKED, C_NORMAL, C_BORDER,
    C_STATUS_OK, C_STATUS_ERR, C_STATUS_INFO, C_TITLE,
)
from .utils import safe_addstr
from .env_validator import validate_env


class MenuScreen:
    # ASCII-art title split into lines
    _TITLE_LINES = [
        " ███████╗██╗███████╗ ██████╗     ████████╗████████╗████████╗",
        " ██╔════╝██║██╔════╝██╔═══██╗       ██╔══╝    ██╔═╝    ██╔═╝",
        " █████╗  ██║█████╗  ██║   ██║       ██║       ██║      ██║  ",
        " ██╔══╝  ██║██╔══╝  ██║   ██║       ██║       ██║      ██║  ",
        " ██║     ██║██║     ╚██████╔╝       ██║       ██║      ██║  ",
        " ╚═╝     ╚═╝╚═╝      ╚═════╝        ╚═╝       ╚═╝      ╚═╝  ",
        "              ── F I F O  E d i t i o n ──",
    ]

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.cursor = 0
        self.selected_model = 0

        # Validation state (written by background thread)
        self.api_valid   = False
        self.api_key: str | None = None
        self.api_msg     = ""
        self.validating  = True

        threading.Thread(target=self._validate, daemon=True).start()

    # ------------------------------------------------------------------
    # Background validation
    # ------------------------------------------------------------------
    def _validate(self) -> None:
        valid, key, msg = validate_env()
        self.api_valid  = valid
        self.api_key    = key
        self.api_msg    = msg
        self.validating = False

    # ------------------------------------------------------------------
    # Lock helpers
    # ------------------------------------------------------------------
    def _requires_llm(self, idx: int) -> bool:
        return idx in (1, 2)

    def _locked(self, idx: int) -> bool:
        return self._requires_llm(idx) and not self.api_valid

    # ------------------------------------------------------------------
    # Draw helpers
    # ------------------------------------------------------------------
    def _draw_title(self, h: int, w: int) -> None:
        attr = curses.color_pair(C_TITLE) | curses.A_BOLD
        for i, line in enumerate(self._TITLE_LINES):
            x = max(0, (w - len(line)) // 2)
            safe_addstr(self.stdscr, 1 + i, x, line, attr)

    def _draw_validation_bar(self, h: int, w: int, row: int) -> None:
        if self.validating:
            tick    = int(time.time() * 4) % 4
            spinner = "⠋⠙⠸⠴"[tick]
            bar_w   = 30
            filled  = int((time.time() % 2) / 2 * bar_w)
            bar     = "█" * filled + "░" * (bar_w - filled)
            msg     = f" {spinner} Validating API key  [{bar}]"
            attr    = curses.color_pair(C_STATUS_INFO) | curses.A_BOLD
        elif self.api_valid:
            msg  = f" ✓  {self.api_msg}"
            attr = curses.color_pair(C_STATUS_OK) | curses.A_BOLD
        else:
            msg  = f" ✗  {self.api_msg}"
            attr = curses.color_pair(C_STATUS_ERR) | curses.A_BOLD

        x = max(0, (w - len(msg)) // 2)
        safe_addstr(self.stdscr, row, x, msg, attr)

    def _draw_options(self, h: int, w: int, start_row: int) -> None:
        options = list(MODE_LABELS.values())
        for i, label in enumerate(options):
            locked   = self._locked(i)
            selected = (i == self.cursor)

            if locked:
                prefix = "  🔒  "
                attr   = curses.color_pair(C_LOCKED) | curses.A_DIM
                suffix = "  (requires GEMINI_API_KEY)"
            elif selected:
                prefix = "  ▶   "
                attr   = curses.color_pair(C_HIGHLIGHT) | curses.A_BOLD
                suffix = "  "
            else:
                prefix = "      "
                attr   = curses.color_pair(C_NORMAL)
                suffix = "  "

            line = f"{prefix}{label}{suffix}"
            x    = max(0, (w - 40) // 2)
            safe_addstr(self.stdscr, start_row + i * 2, x, line, attr)

    def _draw_model_picker(self, h: int, w: int, row: int) -> None:
        model = AVAILABLE_MODELS[self.selected_model]
        label = "  Model: "
        x     = max(0, (w - 40) // 2)
        safe_addstr(self.stdscr, row, x, label,
                    curses.color_pair(C_STATUS_INFO))
        safe_addstr(self.stdscr, row, x + len(label),
                    f"[ {model} ]  ← → to change",
                    curses.color_pair(C_STATUS_OK) | curses.A_BOLD)

    def _draw_hints(self, h: int, w: int) -> None:
        hints = "↑↓ navigate   Enter select   ← → model   Q quit"
        safe_addstr(self.stdscr, h - 1,
                    max(0, (w - len(hints)) // 2),
                    hints, curses.color_pair(C_STATUS_INFO))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def draw(self) -> None:
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()

        self._draw_title(h, w)
        self._draw_validation_bar(h, w, row=9)

        separator_y = 11
        sep = "─" * min(60, w - 4)
        safe_addstr(self.stdscr, separator_y,
                    max(0, (w - len(sep)) // 2),
                    sep, curses.color_pair(C_BORDER))

        self._draw_options(h, w, start_row=separator_y + 2)

        model_row = separator_y + 2 + len(MODE_LABELS) * 2 + 1
        if self.api_valid:
            self._draw_model_picker(h, w, model_row)

        self._draw_hints(h, w)
        self.stdscr.refresh()

    def handle_key(self, key: int) -> tuple[Mode, str] | None:
        """
        Process *key* and return (Mode, model_name) when the user confirms
        a selection, or None to remain on the menu.
        """
        n = len(MODE_LABELS)
        if key in (curses.KEY_UP, ord('k')):
            self.cursor = (self.cursor - 1) % n
        elif key in (curses.KEY_DOWN, ord('j')):
            self.cursor = (self.cursor + 1) % n
        elif key == curses.KEY_LEFT:
            self.selected_model = (self.selected_model - 1) % len(AVAILABLE_MODELS)
        elif key == curses.KEY_RIGHT:
            self.selected_model = (self.selected_model + 1) % len(AVAILABLE_MODELS)
        elif key in (curses.KEY_ENTER, 10, 13):
            if self._locked(self.cursor):
                return None
            mode = list(Mode)[self.cursor]
            return mode, AVAILABLE_MODELS[self.selected_model]
        return None