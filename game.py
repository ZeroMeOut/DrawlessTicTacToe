import os
import sys
import time
import curses
import importlib

# Ensure the parent directory can resolve internal package paths seamlessly
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Correct package routing based on your folder structure
from packages.tictactoe import TicTacToe
from packages.minimax import minimax_alpha_beta
from packages.llmplayer import LLMPlayer

# Configurable list of models — add any future models here!
SUPPORTED_MODELS = [
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-2.5-pro",
]

ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")

def setup_and_get_env_key() -> tuple[str, str]:
    """Checks for .env file existence, creates a template if missing, and safely cleans the token."""
    if not os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, "w") as f:
            f.write("GEMINI_API_KEY=YOUR_API_KEY_HERE\n")
        return "", "Created new .env file template. Please add your key."
        
    with open(ENV_FILE_PATH, "r") as f:
        for line in f:
            cleaned_line = line.strip()
            if cleaned_line.startswith("GEMINI_API_KEY="):
                key = cleaned_line.split("=", 1)[1].strip()
                key = key.strip("'\"") # Strip off literal wrapping quotes if they exist
                if key in ["", "YOUR_API_KEY_HERE"]:
                    return "", "Token empty in .env"
                return key, "Token loaded from .env"
                
    return "", ".env file corrupt or key missing"

def verify_token_with_api(api_key: str, model_name: str) -> tuple[bool, str]:
    """Validates the live API token against Google's servers using a fast baseline call."""
    if not api_key:
        return False, "The token in your env is invalid"
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        client.models.generate_content(
            model=model_name,
            contents="Ping test",
        )
        return True, "Valid Token"
    except Exception as e:
        return False, f"The token in your env is invalid: {str(e)}"

class CursesApp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.game = TicTacToe()
        self.model_idx = 0
        self.selected_model = SUPPORTED_MODELS[self.model_idx]
        self.api_key, self.token_status = setup_and_get_env_key()
        
        self.attempts_remaining = 5
        self.state_count = 0
        self.game_mode = None  
        
        self.cursor_row = 0
        self.cursor_col = 0
        
        # Color setups
        curses.curs_set(0)
        self.stdscr.keypad(True)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Menu UI / System Information
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Success metrics / 'O' Player
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)     # Errors / 'X' Player
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Grid highlights
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # EVICTION WARNING (Oldest Piece)

    def draw_window_header(self, subtitle: str):
        self.stdscr.clear()
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(1, 2, f"=== ADVERSARIAL FIFO TIC-TAC-TOE PLATFORM ===")
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(2, 2, subtitle, curses.A_DIM)

    def check_screen_size(self, min_rows=22, min_cols=75) -> bool:
        """Returns True if screen is big enough, otherwise draws a clean warning."""
        max_y, max_x = self.stdscr.getmaxyx()
        if max_y < min_rows or max_x < min_cols:
            self.stdscr.clear()
            self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(1, 2, "⚠️ TERMINAL WINDOW TOO SMALL")
            self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(3, 2, f"Current size: {max_y} rows x {max_x} columns")
            self.stdscr.addstr(4, 2, f"Required size: Min {min_rows} rows x {min_cols} columns")
            self.stdscr.addstr(6, 2, "Please stretch/enlarge your terminal window to continue...", curses.A_BLINK)
            self.stdscr.refresh()
            return False
        return True

    def show_invalid_token_popup(self, full_error_msg: str):
        """Spawns an insulated sub-window popup displaying an invalid token alert."""
        max_y, max_x = self.stdscr.getmaxyx()
        
        # Define dimension configurations for the modal dialog box
        win_height = 8
        win_width = min(max_x - 6, 68)
        start_y = max(0, (max_y - win_height) // 2)
        start_x = max(0, (max_x - win_width) // 2)
        
        # Instantiate localized window module mapping
        popup_win = curses.newwin(win_height, win_width, start_y, start_x)
        popup_win.keypad(True)
        popup_win.box()
        
        # Paint background element structures
        popup_win.attron(curses.color_pair(3) | curses.A_BOLD)
        popup_win.addstr(1, 2, " ⚠️  AUTHENTICATION FAILURE ")
        popup_win.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        # Truncate warning logs gracefully to stay within window bounds
        display_err = full_error_msg[:win_width - 6]
        popup_win.addstr(3, 3, display_err, curses.color_pair(3))
        popup_win.addstr(4, 3, "Check your root .env file variables configurations.", curses.A_DIM)
        
        popup_win.addstr(win_height - 2, 3, "Press [Any Key] to dismiss this dialog...", curses.color_pair(1))
        popup_win.refresh()
        
        # Flush pending characters then catch input to freeze execution temporarily
        curses.flushinp()
        popup_win.getch()
        del popup_win
        self.stdscr.clear()

    def display_main_menu(self) -> bool:
        while True:
            if not self.check_screen_size(min_rows=16, min_cols=75):
                time.sleep(0.2)
                continue
                
            self.draw_window_header("Initialization Configuration & Authentication")
            
            self.stdscr.addstr(4, 4, f"1. Active Model Target:  < {self.selected_model} > (Use Left/Right Arrows)")
            
            is_valid = "Valid" in self.token_status or "Unchecked" in self.token_status or "loaded" in self.token_status.lower()
            status_color = curses.color_pair(2) if "Valid" in self.token_status else (curses.color_pair(1) if "Unchecked" in self.token_status else curses.color_pair(3))
            
            self.stdscr.addstr(5, 4, f"2. API Credentials Check: ")
            self.stdscr.addstr(self.token_status[:45], status_color | curses.A_BOLD)
            
            masked_key = self.api_key[:10] + "..." if len(self.api_key) > 10 else "None"
            self.stdscr.addstr(6, 7, f"Token Registry Value: [{masked_key}]", curses.A_DIM)

            self.stdscr.addstr(8, 4, "Select Operational Simulation Mode:")
            self.stdscr.addstr(9, 6, "A) Human vs Minimax Bot")
            self.stdscr.addstr(10, 6, "B) LLM Meta-Heuristic Function vs Minimax Bot")
            self.stdscr.addstr(11, 6, "Q) Terminate Engine")
            
            self.stdscr.addstr(13, 4, "Controls: [V] Re-Verify Token, [Arrows] Select Model, [A/B/Q] Select Mode")
            self.stdscr.refresh()
            
            ch = self.stdscr.getch()
            if ch == curses.KEY_RIGHT:
                self.model_idx = (self.model_idx + 1) % len(SUPPORTED_MODELS)
                self.selected_model = SUPPORTED_MODELS[self.model_idx]
            elif ch == curses.KEY_LEFT:
                self.model_idx = (self.model_idx - 1) % len(SUPPORTED_MODELS)
                self.selected_model = SUPPORTED_MODELS[self.model_idx]
            elif ch in [ord('v'), ord('V')]:
                self.token_status = "Pinging Google API Servers..."
                self.stdscr.refresh()
                self.api_key, _ = setup_and_get_env_key()
                success, msg = verify_token_with_api(self.api_key, self.selected_model)
                self.token_status = msg
                if not success:
                    self.show_invalid_token_popup(msg)
            elif ch in [ord('a'), ord('A')]:
                self.game_mode = 'human'
                break
            elif ch in [ord('b'), ord('B')]:
                self.api_key, _ = setup_and_get_env_key()
                success, msg = verify_token_with_api(self.api_key, self.selected_model)
                self.token_status = msg
                if not success:
                    self.show_invalid_token_popup(msg)
                    continue  
                self.game_mode = 'llm'
                break
            elif ch in [ord('q'), ord('Q')]:
                return False
        return True

    def interruptible_delay(self, seconds: float) -> bool:
        """Sleeps for a duration but actively listens for the 'Q' key to abort the match."""
        self.stdscr.nodelay(True)
        start_time = time.time()
        while time.time() - start_time < seconds:
            ch = self.stdscr.getch()
            if ch in [ord('q'), ord('Q')]:
                self.stdscr.nodelay(False)
                return True
            time.sleep(0.1)
        self.stdscr.nodelay(False)
        return False

    def draw_battle_dashboard(self, action_log: str = ""):
        if not self.check_screen_size(min_rows=22, min_cols=75):
            return

        self.draw_window_header(f"Live Simulation Loop: {self.game_mode.upper()} vs MINIMAX")
        
        self.stdscr.addstr(4, 2, f"Target Objective   : Survive 50 game states or beat Minimax.", curses.A_BOLD)
        self.stdscr.addstr(5, 2, f"Current Progress   : [ {self.state_count} / 50 ] States Scaled")
        
        life_color = curses.color_pair(2) if self.attempts_remaining > 1 else curses.color_pair(3)
        self.stdscr.addstr(6, 2, f"Attempts Remaining : ")
        self.stdscr.addstr(f"{self.attempts_remaining} / 5 Left", life_color | curses.A_BOLD)
        
        eviction_target = None
        if len(self.game.fifo_storage) >= 6:
            eviction_target = (self.game.fifo_storage[0][0], self.game.fifo_storage[0][1])

        board_matrix = self.game.display_board_as_list()
        grid_y, grid_x = 8, 6  
        for r in range(3):
            for c in range(3):
                val = board_matrix[r][c]
                
                if eviction_target and r == eviction_target[0] and c == eviction_target[1]:
                    attr = curses.color_pair(5) | curses.A_BOLD
                elif val == 'X':
                    attr = curses.color_pair(3) | curses.A_BOLD
                elif val == 'O':
                    attr = curses.color_pair(2) | curses.A_BOLD
                else:
                    attr = curses.A_NORMAL
                
                if self.game_mode == 'human' and self.game.current_player == 'O' and r == self.cursor_row and c == self.cursor_col:
                    attr |= curses.color_pair(4)
                    
                self.stdscr.addstr(grid_y + (r * 2), grid_x + (c * 4), f" {val} ", attr)
                if c < 2:
                    self.stdscr.addstr(grid_y + (r * 2), grid_x + (c * 4) + 3, "|")
            if r < 2:
                self.stdscr.addstr(grid_y + (r * 2) + 1, grid_x, "-----------")
                
        self.stdscr.addstr(15, 2, "Temporal FIFO Board Memory Tracking:", curses.A_UNDERLINE)
        if self.game.fifo_storage:
            next_to_die = self.game.fifo_storage[0]
            self.stdscr.addstr(16, 4, f"Active Elements on Grid: {len(self.game.fifo_storage)} / 6 Pieces Max")
            self.stdscr.addstr(17, 4, f"Next piece to be evicted: Player '{next_to_die[2]}' at space ({next_to_die[0]}, {next_to_die[1]})", curses.color_pair(5) | curses.A_BOLD)
        else:
            self.stdscr.addstr(16, 4, "Grid space empty. Queue buffer unpopulated.")

        self.stdscr.addstr(19, 2, "System Status Logs: ")
        self.stdscr.addstr(action_log[:50], curses.color_pair(1) | curses.A_BOLD)
        
        self.stdscr.addstr(21, 2, "CONTROLS: ")
        if self.game_mode == 'human' and self.game.current_player == 'O':
            self.stdscr.addstr("Use [Arrow Keys] to shift, [Enter] to claim. ")
        self.stdscr.addstr("Press [Q] to abort.", curses.color_pair(3))
            
        self.stdscr.refresh()

    def run_simulation(self):
        self.game.reset_game()
        self.state_count = 0
        llm_player_agent = None

        if self.game_mode == 'llm':
            self.draw_battle_dashboard("Querying Gemini to generate the baseline heuristic class architecture...")
            llm_player_agent = LLMPlayer(model_name=self.selected_model, api_key=self.api_key)
            llm_player_agent.initialise()

        while self.state_count < 50:
            winner = self.game.check_winner()
            if winner != ' ':
                if winner == 'O':
                    self.draw_battle_dashboard(f"🎉 VICTORY! Player O achieved a winning layout configuration at state index {self.state_count}!")
                    self.stdscr.getch()
                    return
                else:
                    self.attempts_remaining -= 1
                    if self.attempts_remaining <= 0:
                        self.draw_battle_dashboard("❌ ELIMINATION: All remaining attempts exhausted without reaching 50 states.")
                        self.stdscr.getch()
                        return
                    
                    if self.game_mode == 'llm':
                        feedback = f"Defeat. Minimax algorithm out-positioned your code and claimed a victory configuration at loop {self.state_count}."
                        self.draw_battle_dashboard("💥 Defeat encountered. Feeding failure telemetry back to model for healing...")
                        llm_player_agent.improve(feedback=feedback, game_history=self.game.history)
                        
                    self.game.reset_game()
                    self.state_count = 0
                    continue

            if self.game.current_player == 'X':
                self.draw_battle_dashboard("Minimax calculation calculating target grid layout choices...")
                
                if self.game_mode == 'llm' or self.state_count > 0:
                    if self.interruptible_delay(3.0): 
                        return 
                
                move, _ = minimax_alpha_beta(self.game, depth=4)
                if move:
                    self.game.push(*move)
                self.state_count += 1
            else:
                if self.game_mode == 'human':
                    self.draw_battle_dashboard("Awaiting user grid allocation parameters...")
                    ch = self.stdscr.getch()
                    
                    if ch in [ord('q'), ord('Q')]:
                        return
                        
                    if ch == curses.KEY_UP:
                        self.cursor_row = max(0, self.cursor_row - 1)
                    elif ch == curses.KEY_DOWN:
                        self.cursor_row = min(2, self.cursor_row + 1)
                    elif ch == curses.KEY_LEFT:
                        self.cursor_col = max(0, self.cursor_col - 1)
                    elif ch == curses.KEY_RIGHT:
                        self.cursor_col = min(2, self.cursor_col + 1)
                    elif ch in [10, 13, curses.KEY_ENTER]:
                        chosen_coordinate = (self.cursor_row, self.cursor_col)
                        if chosen_coordinate in self.game.avalible_moves:
                            self.game.push(*chosen_coordinate)
                            self.state_count += 1
                else:
                    self.draw_battle_dashboard("Invoking the dynamic strategy class definition...")
                    
                    if self.interruptible_delay(3.0):
                        return 
                    
                    try:
                        if "packages.generated_heuristic" in sys.modules:
                            importlib.reload(sys.modules["packages.generated_heuristic"])
                        import packages.generated_heuristic as gh
                        
                        strategy_instance = gh.CustomAIStrategy(
                            board=self.game.display_board_as_list(),
                            fifo_storage=self.game.fifo_storage.copy(),
                            your_sign='O',
                            current_player=self.game.current_player
                        )
                        move = strategy_instance.main()
                        
                        if move not in self.game.avalible_moves:
                            raise ValueError(f"Calculated placement point {move} is invalid or already occupied.")
                            
                        self.game.push(*move)
                        self.state_count += 1
                        
                    except Exception as e:
                        self.attempts_remaining -= 1
                        if self.attempts_remaining <= 0:
                            self.draw_battle_dashboard(f"❌ COMPILATION CRASH: {str(e)}. No attempts left.")
                            self.stdscr.getch()
                            return
                        
                        feedback = f"Your generated class crashed during active execution evaluation: {str(e)}"
                        self.draw_battle_dashboard("⚠️ Active Heuristic Runtime Crash! Deploying code patch context maps...")
                        llm_player_agent.improve(feedback=feedback, game_history=self.game.history)
                        
                        self.game.reset_game()
                        self.state_count = 0

        self.draw_battle_dashboard("🎉 SURVIVAL MISSION COMPLETE! Successfully scaled 50 states against Minimax!")
        self.stdscr.getch()

def main_engine(stdscr):
    app = CursesApp(stdscr)
    while app.display_main_menu(): 
        app.run_simulation()
        app.attempts_remaining = 5 
        app.game.reset_game()

if __name__ == "__main__":
    curses.wrapper(main_engine)