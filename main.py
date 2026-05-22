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
    print("Move and score: ", minimax(game, 10, True, float('-inf'), float('inf')))
    game.display_board()
    print(game.display_board_as_list())

if __name__ == "__main__":
    main()
