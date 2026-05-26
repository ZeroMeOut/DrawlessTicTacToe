"""
main.py
───────
Entry point.  Run:  python main.py

Directory layout expected:
  main.py          ← this file
  .env             ← GEMINI_API_KEY=...
  games/           ← TUI screens and helpers
  packages/        ← tictactoe.py, minimax.py, llmplayer.py
"""

import curses
import os
import sys
import time
from dotenv import load_dotenv

# Make sure `packages.*` imports resolve from here
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

from games.utils        import init_colors
from games.menu_screen  import MenuScreen
from games.game_screen  import GameScreen


def main(stdscr) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    init_colors()

    menu        = MenuScreen(stdscr)
    game: GameScreen | None = None
    state       = "menu"

    while True:
        if state == "menu":
            menu.draw()
            key = stdscr.getch()
            if key in (ord('q'), ord('Q')):
                break
            result = menu.handle_key(key)
            if result:
                mode, model = result
                game = GameScreen(stdscr, mode, menu.api_key, model)
                state = "game"

        elif state == "game":
            game.tick()
            game.draw()
            key = stdscr.getch()
            if key != -1:
                action = game.handle_key(key)
                if action == 'quit':
                    break
                elif action == 'menu':
                    menu  = MenuScreen(stdscr)
                    state = "menu"

        time.sleep(0.05)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass