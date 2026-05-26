"""
games/constants.py
──────────────────
All shared constants: colour pair IDs, model list, timing, Mode enum.
To add a new Gemini model, append it to AVAILABLE_MODELS.
"""

from enum import Enum, auto

# ---------------------------------------------------------------------------
# Colour pair indices  (registered in utils.init_colors)
# ---------------------------------------------------------------------------
C_NORMAL      = 1   # default text
C_HIGHLIGHT   = 2   # selected menu item / active
C_BOARD       = 3   # board lines + empty cells
C_X           = 4   # X pieces
C_O           = 5   # O pieces
C_EVICT       = 6   # piece about to be evicted (next FIFO pop)
C_LOCKED      = 7   # locked menu option
C_BORDER      = 8   # box borders
C_STATUS_OK   = 9   # status bar success
C_STATUS_ERR  = 10  # status bar error
C_STATUS_INFO = 11  # status bar info / dim
C_TITLE       = 12  # title / heading
C_REASONING   = 13  # reasoning panel text
C_WINNER      = 14  # winner banner

# ---------------------------------------------------------------------------
# Available Gemini models  ← add more strings here to extend the picker
# ---------------------------------------------------------------------------
AVAILABLE_MODELS: list[str] = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3.5-flash",
]

# ---------------------------------------------------------------------------
# Timing & attempt config
# ---------------------------------------------------------------------------
AI_MOVE_DELAY: float  = 2.0   # minimum seconds between AI moves (minimax + LLM)
LLM_ATTEMPTS:  int    = 5     # number of games LLM plays against minimax before stopping
ATTEMPT_PAUSE: float  = 3.0   # seconds to display result before auto-resetting

# ---------------------------------------------------------------------------
# Game mode
# ---------------------------------------------------------------------------
class Mode(Enum):
    HUMAN_VS_MINIMAX = auto()
    LLM_VS_MINIMAX   = auto()
    HUMAN_VS_LLM     = auto()

MODE_LABELS: dict[Mode, str] = {
    Mode.HUMAN_VS_MINIMAX: "Human  vs  Minimax",
    Mode.LLM_VS_MINIMAX:   "LLM    vs  Minimax",
    Mode.HUMAN_VS_LLM:     "Human  vs  LLM    ",
}