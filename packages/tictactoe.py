class TicTacToe:
    def __init__(self):
        self.current_player = 'X'
        # Each entry is (row, col, player) so we can reconstruct the board without a separate grid
        self.fifo_storage: list[tuple[int, int, str]] = []
        self.avalible_moves = [(i, j) for i in range(3) for j in range(3)]

    def display_board(self) -> None:
        # Reconstruct cell values purely from fifo_storage.
        # Cells not in fifo_storage are in avalible_moves and therefore empty.
        cell = {(r, c): p for r, c, p in self.fifo_storage}

        for i in range(3):
            print(' | '.join(cell.get((i, j), ' ') for j in range(3)))
            if i < 2:
                print('---------')
        print(" ")

        # |   |  
      # ---------
        # |   |  
      # ---------
        # |   |  

    ## FIFO, First in First Out
    def fifo(self, row: int, col: int) -> None:
        if len(self.fifo_storage) == 6:
            old_row, old_col, _ = self.fifo_storage.pop(0)
            self.avalible_moves.append((old_row, old_col))

        self.fifo_storage.append((row, col, self.current_player))
        self.avalible_moves.remove((row, col))

    def push(self, row: int, col: int) -> None:
        if (row, col) in self.avalible_moves:
            self.fifo(row, col)  ## Makes it so that the game would be drawless, there would always be at least 3 spaces on the board
            self.current_player = 'O' if self.current_player == 'X' else 'X'
        else:
            print("Invalid input")

    def check_winner(self) -> str:
        winning_combinations = [
            [(0, 0), (0, 1), (0, 2)],  ## Row 1
            [(1, 0), (1, 1), (1, 2)],  ## Row 2
            [(2, 0), (2, 1), (2, 2)],  ## Row 3

            [(0, 0), (1, 0), (2, 0)],  ## Column 1
            [(0, 1), (1, 1), (2, 1)],  ## Column 2
            [(0, 2), (1, 2), (2, 2)],  ## Column 3

            [(0, 0), (1, 1), (2, 2)],  ## Diagonal 1
            [(0, 2), (1, 1), (2, 0)]   ## Diagonal 2
        ]

        # Build a lookup from occupied cells — skip available (empty) cells entirely
        occupied = {(r, c): p for r, c, p in self.fifo_storage}

        for combination in winning_combinations:
            # Skip any combination that contains an empty cell
            if any(cell not in occupied for cell in combination):
                continue

            players = [occupied[cell] for cell in combination]
            if len(set(players)) == 1:
                return players[0]

        return ' '  # No winner yet

    def reset_game(self) -> None:
        self.current_player = 'X'
        self.fifo_storage = []
        self.avalible_moves = [(i, j) for i in range(3) for j in range(3)]