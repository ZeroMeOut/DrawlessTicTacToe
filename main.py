from packages.tictactoe import TicTacToe
from packages.minimax import minimax

def main():
    print("Hello from drawlesstictactoe!")
    game = TicTacToe()
    game.push(0, 0)
    game.push(2, 0)
    game.push(1, 1)
    game.display_board() 
    game.revert()
    game.display_board()

if __name__ == "__main__":
    main()
