from packages.tictactoe import TicTacToe

def main():
    print("Hello from drawlesstictactoe!")
    game = TicTacToe()
    game.push(0, 0)
    game.push(2, 0) 
    game.push(0, 1)
    game.push(2, 1)
    game.push(1, 2)
    game.push(0, 2)
    game.push(1, 0)
    game.display_board()
    winner = game.check_winner()
    print(game.avalible_moves)
    if winner != ' ':
        print(f"The winner is: {winner}")   

if __name__ == "__main__":
    main()
