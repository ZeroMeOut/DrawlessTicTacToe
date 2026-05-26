"""
main.py — sits one level above the packages/ folder.

Layout:
    main.py
    packages/
        __init__.py
        tictactoe.py
        minimax.py
        llmplayer.py
        generated_heuristic.py   ← written at runtime by llmplayer

The LLM plays as O; minimax plays as X and always moves first.

Win condition for the LLM  : win a game against minimax.
Survival condition         : reach 15 total board states in a single game
                             without losing.
The LLM gets 5 attempts.  After each loss the algorithm is improved using
the game history and feedback before the next attempt.
"""

import os
import sys
import importlib

# Ensure 'packages' is importable from wherever main.py is run
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from packages.tictactoe import TicTacToe
from packages.minimax import minimax_alpha_beta
from packages.llmplayer import LLMPlayer

MAX_ATTEMPTS      = 5
SURVIVAL_TARGET   = 15   # board states (pushes) without losing
LLM_SIGN          = 'O'
MINIMAX_SIGN      = 'X'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_llm_strategy():
    """Import (or reload) the generated CustomAIStrategy class."""
    module_name = "packages.generated_heuristic"
    if module_name in sys.modules:
        module = importlib.reload(sys.modules[module_name])
    else:
        module = importlib.import_module(module_name)
    return module.CustomAIStrategy


def llm_move(game: TicTacToe) -> tuple[int, int]:
    """Ask the LLM strategy for its move, with a fallback to the first available."""
    Strategy = load_llm_strategy()
    strategy = Strategy(
        board=game.display_board_as_list(),
        fifo_storage=list(game.fifo_storage),
        your_sign=LLM_SIGN,
        current_player=game.current_player,
    )
    try:
        row, col = strategy.main()
        if (row, col) in game.avalible_moves:
            return row, col
        print(f"  [LLM returned invalid move ({row},{col}), falling back to first available]")
    except Exception as e:
        print(f"  [LLM strategy raised an error: {e}, falling back to first available]")

    return game.avalible_moves[0]


def build_feedback(winner: str, state_count: int) -> str:
    """Produce a short feedback string for the improvement prompt."""
    if winner == LLM_SIGN:
        return "You won! Keep the same general approach."
    if winner == MINIMAX_SIGN:
        return (
            f"You lost after {state_count} board states. "
            "The opponent (minimax with alpha-beta pruning) beat you. "
            "Focus on blocking immediate threats and avoiding moves that "
            "hand the opponent a forced win."
        )
    return (
        f"The game ended without a winner after {state_count} board states. "
        "Try to create more threats and capitalise on opponent weaknesses."
    )


def print_result(attempt: int, winner: str, state_count: int) -> None:
    print(f"\n  Board states reached: {state_count}")
    if winner == LLM_SIGN:
        print("  Result : LLM WON  ✓")
    elif winner == MINIMAX_SIGN:
        print("  Result : LLM LOST ✗")
    else:
        print(f"  Result : No winner yet after {state_count} states")


# ---------------------------------------------------------------------------
# Single game
# ---------------------------------------------------------------------------

_game_instance = TicTacToe()  # single reused instance


def play_game() -> tuple[str, int, list[tuple[int, int, str]]]:
    """
    Play one full game between minimax (X, always first) and the LLM (O).

    Returns:
        winner      — 'X', 'O', or ' ' (no winner within survival target)
        state_count — number of board states that occurred
        game_history— flat list of (row, col, player) moves in order
    """
    game = _game_instance
    game.reset_game()
    state_count = 0
    game_history: list[tuple[int, int, str]] = []

    while True:
        # --- minimax (X) moves ---
        move, _ = minimax_alpha_beta(game, depth=6)
        if move is None:
            break
        row, col = move
        player_before = game.current_player
        game.push(row, col)
        game_history.append((row, col, player_before))
        state_count += 1

        print(f"\n  Minimax ({MINIMAX_SIGN}) played ({row}, {col})  [state {state_count}]")
        game.display_board()

        winner = game.check_winner()
        if winner != ' ':
            return winner, state_count, game_history

        if state_count >= SURVIVAL_TARGET:
            return ' ', state_count, game_history

        # --- LLM (O) moves ---
        row, col = llm_move(game)
        player_before = game.current_player
        game.push(row, col)
        game_history.append((row, col, player_before))
        state_count += 1

        print(f"  LLM     ({LLM_SIGN}) played ({row}, {col})  [state {state_count}]")
        game.display_board()

        winner = game.check_winner()
        if winner != ' ':
            return winner, state_count, game_history

        if state_count >= SURVIVAL_TARGET:
            return ' ', state_count, game_history


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)

    player = LLMPlayer(model_name="gemini-3.5-flash", api_key=api_key)

    print("=" * 60)
    print("Generating initial LLM strategy...")
    print("=" * 60)
    player.initialise()
    print("Strategy ready.\n")

    overall_success = False

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print("=" * 60)
        print(f"Attempt {attempt} / {MAX_ATTEMPTS}")
        print("=" * 60)

        winner, state_count, game_history = play_game()
        print_result(attempt, winner, state_count)

        # Success: LLM won, or survived to the target without losing
        if winner == LLM_SIGN or (winner == ' ' and state_count >= SURVIVAL_TARGET):
            print("\n✓ LLM met the success condition!")
            overall_success = True
            break

        # Failure: LLM lost
        if attempt < MAX_ATTEMPTS:
            print(f"\nImproving strategy before attempt {attempt + 1}...")
            feedback = build_feedback(winner, state_count)
            player.improve(feedback=feedback, game_history=game_history)
            print("Strategy updated.\n")
        else:
            print("\nAll attempts exhausted.")

    print("\n" + "=" * 60)
    if overall_success:
        print("FINAL RESULT: SUCCESS — the LLM strategy passed the challenge.")
    else:
        print("FINAL RESULT: FAILURE — the LLM could not meet the success condition.")
    print("=" * 60)


if __name__ == "__main__":
    main()