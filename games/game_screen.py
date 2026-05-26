"""
games/game_screen.py
────────────────────
The in-game screen.

Responsibilities
  • Render the FIFO board (eviction highlighted in yellow).
  • Handle human cursor movement and piece placement.
  • Schedule minimax and LLM moves on background threads with AI_MOVE_DELAY.
  • Show the LLM reasoning + AI-status panel (right side) for LLM modes.
  • Handle R (restart) and Q (quit) keys.
"""

import curses
import sys
import time
import threading
import textwrap
import importlib

from .constants import (
    Mode, MODE_LABELS, AI_MOVE_DELAY, LLM_ATTEMPTS, ATTEMPT_PAUSE,
    C_HIGHLIGHT, C_BOARD, C_X, C_O, C_EVICT,
    C_BORDER, C_STATUS_OK, C_STATUS_ERR, C_STATUS_INFO,
    C_TITLE, C_REASONING, C_WINNER,
)
from .utils import safe_addstr, draw_box

# Board cell dimensions (chars)
CELL_W = 7
CELL_H = 3


def _import_game_modules():
    """Lazily import game modules from the packages/ directory."""
    global TicTacToe, minimax_alpha_beta, LLMPlayer
    from packages.tictactoe import TicTacToe          # type: ignore
    from packages.minimax   import minimax_alpha_beta  # type: ignore
    from packages.llmplayer import LLMPlayer           # type: ignore


class GameScreen:
    """
    Terminal layout (≥ 80 × 24):

    col 0 ──────── col 41 ──────── col 79
    ┌──────────────────────┐  ┌──────────────────────────┐
    │ Header / mode label  │  │ LLM Reasoning            │
    │                      │  │ (scrolling text)         │
    │   Board (3×3)        │  │                          │
    │                      │  └──────────────────────────┘
    │ Status / move log    │  ┌──────────────────────────┐
    │                      │  │ AI Status  (spinner)     │
    └──────────────────────┘  └──────────────────────────┘
    hints bar
    """

    BOARD_TOP  = 4   # row where the board starts
    BOARD_LEFT = 3   # col where the board starts

    def __init__(
        self,
        stdscr,
        mode: Mode,
        api_key: str | None,
        model: str,
    ):
        self.stdscr  = stdscr
        self.mode    = mode
        self.api_key = api_key
        self.model   = model

        _import_game_modules()
        self.game = TicTacToe()

        # UI state
        self.log: list[str]             = []
        self.status_msg                 = "Turn: X"
        self.status_color               = C_STATUS_INFO
        self.winner: str | None         = None
        self.cursor_r                   = 1
        self.cursor_c                   = 1

        # Right-panel state (LLM modes only)
        self.reasoning_lines: list[str] = []
        self.ai_status                  = "Initialising…"
        self.ai_status_color            = C_STATUS_INFO

        # LLM player instances  (X = first player, O = second)
        self.llm_x: "LLMPlayer | None" = None
        self.llm_o: "LLMPlayer | None" = None

        # Multi-attempt state (LLM vs Minimax only)
        # Each entry: {"attempt": int, "winner": str, "moves": int}
        self.attempt_current:  int              = 1
        self.attempt_results:  list[dict]       = []
        self._attempt_game_history: list        = []   # fifo_storage snapshot per move
        self._between_attempts: bool            = False  # True during improve + pause
        self._all_attempts_done: bool           = False

        # Threading
        self._ai_thinking          = False
        self._ai_lock              = threading.Lock()
        self._move_pending: tuple[int, int] | None = None
        self._move_lock            = threading.Lock()
        self._last_ai_move_time    = 0.0

        self._init_llms()

    # ------------------------------------------------------------------
    # LLM lifecycle
    # ------------------------------------------------------------------
    def _init_llms(self) -> None:
        if self.mode in (Mode.LLM_VS_MINIMAX, Mode.HUMAN_VS_LLM):
            threading.Thread(target=self._do_init_llm, daemon=True).start()
        else:
            self.ai_status       = "Ready."
            self.ai_status_color = C_STATUS_OK

    def _do_init_llm(self) -> None:
        self._set_ai_status("Initialising LLM…", C_STATUS_INFO)
        llm = LLMPlayer(model_name=self.model, api_key=self.api_key)
        llm.initialise()
        self._push_reasoning(f"[Attempt 1 — Init reasoning]\n{llm.generated_reasoning}")

        if self.mode == Mode.LLM_VS_MINIMAX:
            self.llm_x = llm   # LLM plays X
        else:
            self.llm_o = llm   # LLM plays O (Human vs LLM)

        self._set_ai_status("LLM ready ✓", C_STATUS_OK)
        self._log("LLM initialised and ready.")

    def _on_attempt_finished(self, result_winner: str) -> None:
        """
        Called (from the main thread via tick) right after a game ends
        in LLM_VS_MINIMAX mode.  Records the result, then either:
          • triggers improve + auto-reset for the next attempt, or
          • marks the training run as complete.
        """
        llm = self.llm_x  # LLM always plays X in LLM_VS_MINIMAX
        n   = self.attempt_current

        self.attempt_results.append({
            "attempt": n,
            "winner":  result_winner,
            "moves":   len(self._attempt_game_history),
        })
        self._log(f"Attempt {n}/{LLM_ATTEMPTS}: winner={result_winner}")

        if n >= LLM_ATTEMPTS:
            self._all_attempts_done = True
            wins   = sum(1 for r in self.attempt_results if r["winner"] == 'X')
            losses = sum(1 for r in self.attempt_results if r["winner"] == 'O')
            self._set_status(
                f"Training done — LLM {wins}W / {losses}L / "
                f"{LLM_ATTEMPTS - wins - losses}D  (Q quit  R menu)",
                C_STATUS_OK,
            )
            self._push_reasoning(
                f"\n{'═'*32}\n"
                f"Training complete: {wins}W {losses}L\n"
                f"{'═'*32}"
            )
            return

        # Not done yet — kick off improve + reset in background
        self._between_attempts = True
        history = list(self._attempt_game_history)

        def _improve_and_reset() -> None:
            llm_sign   = 'X'
            outcome    = ("won" if result_winner == llm_sign
                          else "lost" if result_winner != ' '
                          else "drew")
            feedback   = (
                f"Attempt {n}/{LLM_ATTEMPTS}: you {outcome} as {llm_sign} "
                f"against minimax. Analyse the game and improve your strategy."
            )
            next_n = n + 1
            self._set_ai_status(
                f"Improving before attempt {next_n}…", C_STATUS_INFO
            )
            llm.improve(feedback=feedback, game_history=history)
            self._push_reasoning(
                f"\n[Attempt {next_n} reasoning]\n{llm.generated_reasoning}"
            )
            self._set_ai_status(f"Ready for attempt {next_n}", C_STATUS_OK)

            # Brief pause so the player can read the result
            time.sleep(ATTEMPT_PAUSE)
            self._hard_reset_for_next_attempt(next_n)

        threading.Thread(target=_improve_and_reset, daemon=True).start()

    def _hard_reset_for_next_attempt(self, next_n: int) -> None:
        """Reset board state for the next attempt (called from background thread)."""
        self.game.reset_game()
        self.winner                 = None
        self._attempt_game_history  = []
        self._move_pending          = None
        self._ai_thinking           = False
        self._last_ai_move_time     = 0.0
        self.cursor_r               = 1
        self.cursor_c               = 1
        self.attempt_current        = next_n
        self._between_attempts      = False
        self._set_status(f"Attempt {next_n}/{LLM_ATTEMPTS} — Turn: X", C_STATUS_INFO)
        self._log(f"── Attempt {next_n} ──")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _set_ai_status(self, msg: str, color: int) -> None:
        self.ai_status       = msg
        self.ai_status_color = color

    def _push_reasoning(self, text: str) -> None:
        """Word-wrap *text* and append to the scrolling reasoning buffer."""
        panel_w = 34
        for raw_line in text.splitlines():
            for wrapped in textwrap.wrap(raw_line, panel_w) or [""]:
                self.reasoning_lines.append(wrapped)
        self.reasoning_lines = self.reasoning_lines[-200:]

    def _log(self, msg: str) -> None:
        self.log.append(msg)
        if len(self.log) > 50:
            self.log.pop(0)

    def _set_status(self, msg: str, color: int = C_STATUS_INFO) -> None:
        self.status_msg   = msg
        self.status_color = color

    # ------------------------------------------------------------------
    # Move logic
    # ------------------------------------------------------------------
    def _apply_move(self, r: int, c: int) -> None:
        if self.winner:
            return
        if not self.game.push(r, c):
            self._set_status("Invalid move!", C_STATUS_ERR)
            return

        player = 'O' if self.game.current_player == 'X' else 'X'
        self._log(f"{player}: ({r},{c})")

        # Record snapshot for improve() feedback
        if self.mode == Mode.LLM_VS_MINIMAX:
            self._attempt_game_history.extend(list(self.game.fifo_storage))

        w = self.game.check_winner()
        if w != ' ':
            self.winner = w
            if self.mode == Mode.LLM_VS_MINIMAX and not self._all_attempts_done:
                llm_sign  = 'X'
                outcome   = "wins" if w == llm_sign else "loses"
                self._set_status(
                    f"Attempt {self.attempt_current}/{LLM_ATTEMPTS}: "
                    f"LLM {outcome}!  Improving…",
                    C_WINNER if w == llm_sign else C_STATUS_ERR,
                )
                self._log(f"★ Winner: {w}")
                # Trigger the between-attempts logic
                self._on_attempt_finished(w)
            else:
                self._set_status(
                    f"  {w} wins!  Press R to restart or Q to quit  ",
                    C_WINNER,
                )
                self._log(f"★ Winner: {w}")
        else:
            n = self.attempt_current
            total = LLM_ATTEMPTS if self.mode == Mode.LLM_VS_MINIMAX else 1
            attempt_label = (f"Attempt {n}/{total} — " if self.mode == Mode.LLM_VS_MINIMAX else "")
            self._set_status(f"{attempt_label}Turn: {self.game.current_player}", C_STATUS_INFO)

    def _schedule_ai_move(self) -> None:
        if self._ai_thinking or self.winner:
            return
        with self._ai_lock:
            if self._ai_thinking:
                return
            self._ai_thinking = True
        threading.Thread(target=self._do_ai_move, daemon=True).start()

    def _do_ai_move(self) -> None:
        try:
            # Enforce cooldown
            remaining = AI_MOVE_DELAY - (time.time() - self._last_ai_move_time)
            if remaining > 0:
                time.sleep(remaining)

            current = self.game.current_player
            move: tuple[int, int] | None = None

            if self._should_minimax(current):
                self._set_ai_status("Minimax thinking…", C_STATUS_INFO)
                move, _ = minimax_alpha_beta(self.game)
                self._set_ai_status("Minimax done.", C_STATUS_OK)

            elif self._should_llm(current):
                llm = self.llm_x if current == 'X' else self.llm_o
                if llm is None:
                    self._set_ai_status("LLM not ready yet…", C_STATUS_ERR)
                    with self._ai_lock:
                        self._ai_thinking = False
                    return

                self._set_ai_status("LLM generating move…", C_STATUS_INFO)
                board = self.game.display_board_as_list()
                fifo  = list(self.game.fifo_storage)
                avail = list(self.game.avalible_moves)

                try:
                    mod_name = "generated_heuristic"
                    if mod_name in sys.modules:
                        mod = importlib.reload(sys.modules[mod_name])
                    else:
                        mod = importlib.import_module(mod_name)
                    strategy = mod.CustomAIStrategy(
                        board=board,
                        fifo_storage=fifo,
                        your_sign=current,
                        current_player=current,
                    )
                    move = strategy.main()
                    if move not in avail:
                        move = avail[0] if avail else None
                except Exception as exc:
                    self._log(f"LLM heuristic error: {exc}")
                    move = avail[0] if avail else None

                self._set_ai_status("LLM move ready.", C_STATUS_OK)

            self._last_ai_move_time = time.time()
            with self._move_lock:
                self._move_pending = move

        finally:
            with self._ai_lock:
                self._ai_thinking = False

    # ------------------------------------------------------------------
    # Turn helpers
    # ------------------------------------------------------------------
    def _should_minimax(self, player: str) -> bool:
        return (
            (self.mode == Mode.HUMAN_VS_MINIMAX and player == 'O') or
            (self.mode == Mode.LLM_VS_MINIMAX   and player == 'O')
        )

    def _should_llm(self, player: str) -> bool:
        return (
            (self.mode == Mode.LLM_VS_MINIMAX and player == 'X') or
            (self.mode == Mode.HUMAN_VS_LLM   and player == 'O')
        )

    def _is_human_turn(self) -> bool:
        p = self.game.current_player
        return (
            (self.mode == Mode.HUMAN_VS_MINIMAX and p == 'X') or
            (self.mode == Mode.HUMAN_VS_LLM     and p == 'X')
        )

    # ------------------------------------------------------------------
    # Board rendering
    # ------------------------------------------------------------------
    def _evict_cell(self) -> tuple[int, int] | None:
        """Return the (r, c) of the piece that will be popped on the next move."""
        if len(self.game.fifo_storage) == 6:
            r, c, _ = self.game.fifo_storage[0]
            return (r, c)
        return None

    def _draw_board(self) -> None:
        top   = self.BOARD_TOP
        left  = self.BOARD_LEFT
        evict = self._evict_cell()
        cell  = {(r, c): p for r, c, p in self.game.fifo_storage}

        for row in range(3):
            for col in range(3):
                cy = top  + row * (CELL_H + 1)
                cx = left + col * (CELL_W + 1)
                piece     = cell.get((row, col), ' ')
                is_evict  = (evict == (row, col))
                is_cursor = (
                    self._is_human_turn() and
                    not self.winner and
                    self.cursor_r == row and
                    self.cursor_c == col
                )

                box_attr = curses.color_pair(C_BOARD)
                safe_addstr(self.stdscr, cy,   cx, "┌─────┐", box_attr)
                safe_addstr(self.stdscr, cy+1, cx, "│     │", box_attr)
                safe_addstr(self.stdscr, cy+2, cx, "└─────┘", box_attr)

                # Piece colour
                if piece == 'X':
                    p_attr = curses.color_pair(C_X) | curses.A_BOLD
                elif piece == 'O':
                    p_attr = curses.color_pair(C_O) | curses.A_BOLD
                else:
                    p_attr = curses.color_pair(C_BOARD)

                if is_evict and piece != ' ':
                    p_attr = curses.color_pair(C_EVICT) | curses.A_BOLD

                if is_cursor:
                    safe_addstr(self.stdscr, cy+1, cx, "│  ·  │",
                                curses.color_pair(C_HIGHLIGHT))
                    if piece != ' ':
                        safe_addstr(self.stdscr, cy+1, cx+3, piece, p_attr)
                    continue

                safe_addstr(self.stdscr, cy+1, cx+3, piece, p_attr)

        # Row separators
        for row in range(2):
            cy = top + (row + 1) * (CELL_H + 1) - 1
            safe_addstr(self.stdscr, cy, left, "├─────┼─────┼─────┤",
                        curses.color_pair(C_BOARD))

        # Eviction legend
        if evict:
            legend_y = top + 3 * (CELL_H + 1)
            safe_addstr(self.stdscr, legend_y, left,
                        "  ⚠  Next eviction highlighted in yellow",
                        curses.color_pair(C_STATUS_INFO))

    # ------------------------------------------------------------------
    # Panel rendering
    # ------------------------------------------------------------------
    def _draw_left_panel(self) -> None:
        h, w = self.stdscr.getmaxyx()

        mode_label = MODE_LABELS[self.mode]
        safe_addstr(self.stdscr, 1, 2,
                    f"FIFO Tic-Tac-Toe  ·  {mode_label}",
                    curses.color_pair(C_TITLE) | curses.A_BOLD)

        if self.mode == Mode.LLM_VS_MINIMAX:
            # Show attempt pip progress: ● ● ○ ○ ○
            pips = "".join(
                "●" if i < self.attempt_current else "○"
                for i in range(LLM_ATTEMPTS)
            )
            sub = f"Model: {self.model}   [{pips}]  Attempt {self.attempt_current}/{LLM_ATTEMPTS}"
        elif self.mode != Mode.HUMAN_VS_MINIMAX:
            sub = f"Model: {self.model}"
        else:
            sub = "Press Q to quit · R to restart"
        safe_addstr(self.stdscr, 2, 2, sub, curses.color_pair(C_STATUS_INFO))

        self._draw_board()

        board_bottom = self.BOARD_TOP + 3 * (CELL_H + 1) + 2
        safe_addstr(self.stdscr, board_bottom, 2,
                    self.status_msg[:36],
                    curses.color_pair(self.status_color) | curses.A_BOLD)

        log_top = board_bottom + 2
        safe_addstr(self.stdscr, log_top - 1, 2, "─ Move log ─",
                    curses.color_pair(C_BORDER))
        for i, entry in enumerate(self.log[-(h - log_top - 2):]):
            safe_addstr(self.stdscr, log_top + i, 2, entry[:36],
                        curses.color_pair(C_TITLE - 1))  # C_NORMAL

        hint = ("Arrow keys move · Enter place · Q quit · R restart"
                if self._is_human_turn() and not self.winner
                else "Q quit · R restart")
        safe_addstr(self.stdscr, h - 1, 2, hint[:36],
                    curses.color_pair(C_STATUS_INFO))

    def _draw_right_panel(self) -> None:
        """Only shown when a LLM is involved."""
        if self.mode == Mode.HUMAN_VS_MINIMAX:
            return
        h, w = self.stdscr.getmaxyx()

        px = 42
        pw = max(10, w - px - 1)
        if pw < 10:
            return

        # Reasoning box
        reason_h = max(5, h - 16)   # slightly shorter to fit scoreboard
        draw_box(self.stdscr, 1, px, reason_h, pw, "LLM Reasoning")
        inner_w = pw - 2
        visible = self.reasoning_lines[-(reason_h - 2):]
        for i, line in enumerate(visible):
            safe_addstr(self.stdscr, 2 + i, px + 1, line[:inner_w],
                        curses.color_pair(C_REASONING))

        # AI status box
        status_y = reason_h + 2
        draw_box(self.stdscr, status_y, px, 4, pw, "AI Status")
        if self._ai_thinking or self._between_attempts:
            tick    = int(time.time() * 4) % 4
            spinner = "⠋⠙⠸⠴"[tick]
            msg     = f"{spinner} {self.ai_status}"
        else:
            msg = self.ai_status
        safe_addstr(self.stdscr, status_y + 1, px + 2, msg[:pw - 4],
                    curses.color_pair(self.ai_status_color) | curses.A_BOLD)

        # Attempt scoreboard (LLM vs Minimax only)
        if self.mode == Mode.LLM_VS_MINIMAX:
            score_y = status_y + 5
            draw_box(self.stdscr, score_y, px, min(LLM_ATTEMPTS + 4, h - score_y - 1), pw,
                     "Scoreboard")
            for j, res in enumerate(self.attempt_results):
                w_str = res["winner"]
                if w_str == 'X':
                    label = f"  #{res['attempt']}  LLM wins  ✓"
                    attr  = curses.color_pair(C_STATUS_OK) | curses.A_BOLD
                else:
                    label = f"  #{res['attempt']}  Minimax wins"
                    attr  = curses.color_pair(C_STATUS_ERR)
                safe_addstr(self.stdscr, score_y + 1 + j, px + 1, label[:pw - 2], attr)
            # Pending attempts as dots
            for j in range(len(self.attempt_results), LLM_ATTEMPTS):
                label = f"  #{j+1}  …"
                safe_addstr(self.stdscr, score_y + 1 + j, px + 1, label[:pw - 2],
                            curses.color_pair(C_STATUS_INFO) | curses.A_DIM)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def draw(self) -> None:
        self.stdscr.erase()
        self._draw_left_panel()
        self._draw_right_panel()
        self.stdscr.refresh()

    def handle_key(self, key: int) -> str | None:
        """Return 'quit' / 'menu' / None."""
        if key in (ord('q'), ord('Q')):
            return 'quit'
        if key in (ord('r'), ord('R')):
            self.reset()
            return None
        if self.winner or not self._is_human_turn():
            return None

        if key == curses.KEY_UP:
            self.cursor_r = (self.cursor_r - 1) % 3
        elif key == curses.KEY_DOWN:
            self.cursor_r = (self.cursor_r + 1) % 3
        elif key == curses.KEY_LEFT:
            self.cursor_c = (self.cursor_c - 1) % 3
        elif key == curses.KEY_RIGHT:
            self.cursor_c = (self.cursor_c + 1) % 3
        elif key in (curses.KEY_ENTER, 10, 13):
            if (self.cursor_r, self.cursor_c) in self.game.avalible_moves:
                self._apply_move(self.cursor_r, self.cursor_c)
            else:
                self._set_status("Cell occupied!", C_STATUS_ERR)
        return None

    def tick(self) -> None:
        """Called every frame to drive AI turns."""
        if self.winner or self._between_attempts:
            return

        # Flush any pending AI move onto the board
        with self._move_lock:
            move = self._move_pending
            self._move_pending = None
        if move is not None:
            self._apply_move(*move)
            return

        # Trigger AI if it's their turn
        if not self._ai_thinking and not self._is_human_turn():
            self._schedule_ai_move()

    def reset(self) -> None:
        """Full reset — restarts the entire training run from attempt 1."""
        self.game.reset_game()
        self.winner                 = None
        self.log                    = []
        self.reasoning_lines        = []
        self._move_pending          = None
        self._ai_thinking           = False
        self._between_attempts      = False
        self._all_attempts_done     = False
        self._last_ai_move_time     = 0.0
        self.cursor_r               = 1
        self.cursor_c               = 1
        self.attempt_current        = 1
        self.attempt_results        = []
        self._attempt_game_history  = []
        self._set_status("Turn: X", C_STATUS_INFO)
        self._set_ai_status("Initialising…", C_STATUS_INFO)
        # Re-generate a fresh heuristic from scratch
        self.llm_x = None
        self.llm_o = None
        self._init_llms()