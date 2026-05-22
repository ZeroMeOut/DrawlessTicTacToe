from packages.tictactoe import TicTacToe
from packages.minimax import minimax

def main():
    print("Hello from drawlesstictactoe!")
    game = TicTacToe()
    game.push(0, 0)
    game.push(2, 0) 
    print("Move and score: ", minimax(game, 10, True, float('-inf'), float('inf')))
    game.display_board()

if __name__ == "__main__":
    main()
