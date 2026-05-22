class TicTacToe:
    def __init__(self):
        self.board = [[' ' for _ in range(3)] for _ in range(3)]  ##[[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]
        self.current_player = 'X'
        self.fifo_storage = []

    def display_board(self)-> None:
        for i, row in enumerate(self.board):
            print(' | '.join(row))
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
            old_row, old_col = self.fifo_storage.pop(0)
            self.board[old_row][old_col] = ' '
        
        self.fifo_storage.append((row, col))

    
    def push(self, row: int , col: int) -> None:
        if self.board[row][col] == ' ':
            self.fifo(row, col) ## Makes it so that the game would be drawless, there would always be at least 3 spaces on the board
            self.board[row][col] = self.current_player
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

        for combination in winning_combinations:
            temp = []
            for row, col in combination:
                temp.append(self.board[row][col])
            
            if len(set(temp)) == 1 and temp[0] != ' ':
                return temp[0]
            
        return ' '  # No winner yet
    
    def reset_game(self) -> None:
        self.board = [[' ' for _ in range(3)] for _ in range(3)]
        self.current_player = 'X'
        self.fifo_storage = []

    