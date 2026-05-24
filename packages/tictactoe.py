class TicTacToe:
    def __init__(self):
        self.current_player = 'X'
        # Each entry is (row, col, player) so we can reconstruct the board without a separate grid
        self.fifo_storage: list[tuple[int, int, str]] = []
        self.avalible_moves = [(i, j) for i in range(3) for j in range(3)]
        self._evicted: list[tuple[int, int, str] | None] = []
        self.history: list[dict] = []  

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
    
    def display_board_as_list(self) -> list[list[str]]:
        cell = {(r, c): p for r, c, p in self.fifo_storage}

        board_list = []
        for i in range(3):
            row = [cell.get((i, j), ' ') for j in range(3)]
            board_list.append(row)
        
        return board_list

    ## FIFO, First in First Out
    def fifo(self, row: int, col: int) -> None:
        if len(self.fifo_storage) == 6:
            evicted = self.fifo_storage.pop(0)
            self.avalible_moves.append((evicted[0], evicted[1]))
            self._evicted.append(evicted) 
        else:
            self._evicted.append(None) 

        self.fifo_storage.append((row, col, self.current_player))
        self.avalible_moves.remove((row, col))

    def add_to_history(self) -> None:
        board_state = self.display_board_as_list()
        
        if len(self.history) >= 10:
            self.history.pop(0)
        
        self.history.append({
            'current_player': self.current_player,
            'board': board_state,
            'avalible_moves': self.avalible_moves.copy(),
            'next_move_to_be_removed': self._evicted[-1] if self._evicted else None,
        })

    def push(self, row: int, col: int) -> bool:
        if (row, col) in self.avalible_moves:
            self.fifo(row, col)
            self.current_player = 'O' if self.current_player == 'X' else 'X'
            self.add_to_history()
            return True
        else:
            # print("Invalid input")
            return False

    def revert(self) -> None:
        if not self.fifo_storage:
                    print("No moves to revert")
                    return

        if self.history:
            self.history.pop()
 
        # Undo the last push: the cell goes back to available
        last_row, last_col, _ = self.fifo_storage.pop()
        self.avalible_moves.append((last_row, last_col))
        self.current_player = 'O' if self.current_player == 'X' else 'X'
 
        # If that push evicted an entry, restore it at the front and remove it from available
        evicted = self._evicted.pop()
        if evicted is not None:
            self.fifo_storage.insert(0, evicted)
            self.avalible_moves.remove((evicted[0], evicted[1]))

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