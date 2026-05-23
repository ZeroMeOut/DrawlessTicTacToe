from packages.tictactoe import TicTacToe
from packages.minimax import minimax

def main():
    print("Hello from drawlesstictactoe!")
    game = TicTacToe()
    game.push(0, 0)
    game.push(2, 0) 
    game.push(1, 1)
    game.push(2, 1)
    game.push(1, 2)
    game.display_board()
    print(game.display_board_as_list())
    print(game.history)

if __name__ == "__main__":
    main()
