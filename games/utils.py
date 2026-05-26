"""
games/utils.py
──────────────
Curses helper functions shared by all screens.
"""

import curses
from .constants import (
    C_NORMAL, C_HIGHLIGHT, C_BOARD, C_X, C_O, C_EVICT, C_LOCKED,
    C_BORDER, C_STATUS_OK, C_STATUS_ERR, C_STATUS_INFO, C_TITLE,
    C_REASONING, C_WINNER,
)


def init_colors() -> None:
    """Register all colour pairs.  Must be called after curses.initscr()."""
    curses.start_color()
    curses.use_default_colors()
    bg = -1
    curses.init_pair(C_NORMAL,      curses.COLOR_WHITE,   bg)
    curses.init_pair(C_HIGHLIGHT,   curses.COLOR_BLACK,   curses.COLOR_CYAN)
    curses.init_pair(C_BOARD,       curses.COLOR_CYAN,    bg)
    curses.init_pair(C_X,           curses.COLOR_RED,     bg)
    curses.init_pair(C_O,           curses.COLOR_BLUE,    bg)
    curses.init_pair(C_EVICT,       curses.COLOR_BLACK,   curses.COLOR_YELLOW)
    curses.init_pair(C_LOCKED,      curses.COLOR_BLACK,   bg)
    curses.init_pair(C_BORDER,      curses.COLOR_CYAN,    bg)
    curses.init_pair(C_STATUS_OK,   curses.COLOR_GREEN,   bg)
    curses.init_pair(C_STATUS_ERR,  curses.COLOR_RED,     bg)
    curses.init_pair(C_STATUS_INFO, curses.COLOR_YELLOW,  bg)
    curses.init_pair(C_TITLE,       curses.COLOR_MAGENTA, bg)
    curses.init_pair(C_REASONING,   curses.COLOR_WHITE,   bg)
    curses.init_pair(C_WINNER,      curses.COLOR_BLACK,   curses.COLOR_GREEN)


def safe_addstr(win, y: int, x: int, text: str, attr: int = 0) -> None:
    """Write *text* at (y, x) clipped to the window bounds; swallows errors."""
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    max_len = w - x - 1
    if max_len <= 0:
        return
    try:
        win.addstr(y, x, text[:max_len], attr)
    except curses.error:
        pass


def draw_box(
    win,
    y: int,
    x: int,
    h: int,
    w: int,
    title: str = "",
    color_pair: int = C_BORDER,
) -> None:
    """Draw a box-drawing border with an optional centred title on the top edge."""
    attr = curses.color_pair(color_pair)
    try:
        win.attron(attr)
        win.addch(y,     x,     curses.ACS_ULCORNER)
        win.addch(y,     x+w-1, curses.ACS_URCORNER)
        win.addch(y+h-1, x,     curses.ACS_LLCORNER)
        win.addch(y+h-1, x+w-1, curses.ACS_LRCORNER)
        for i in range(1, w-1):
            win.addch(y,     x+i, curses.ACS_HLINE)
            win.addch(y+h-1, x+i, curses.ACS_HLINE)
        for i in range(1, h-1):
            win.addch(y+i, x,     curses.ACS_VLINE)
            win.addch(y+i, x+w-1, curses.ACS_VLINE)
        win.attroff(attr)
    except curses.error:
        pass

    if title:
        label = f" {title} "
        tx = x + max(1, (w - len(label)) // 2)
        safe_addstr(win, y, tx, label, attr | curses.A_BOLD)