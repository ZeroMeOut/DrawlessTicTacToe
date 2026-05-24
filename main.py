from packages.minimax import minimax
from packages.tictactoe import TicTacToe
from packages.llm_survivor import LLMSurvivor
from packages.minimax_alpha_beta import minimax_alpha_beta

def main():
    print("Hello from drawlesstictactoe!")
    game = TicTacToe()
    
    survivor = LLMSurvivor(model_name='gemma3n:e2b')

    for i in range(3):
        print(f"Game {i + 1}")
        game.reset_game()
        while True:
            if game.current_player == 'X':
                row, col = minimax_alpha_beta(game=game, depth=10, is_maximizing=True, alpha=float('-inf'), beta=float('inf'))[0]
                ## row, col = minimax(game=game, depth=3, is_maximizing=True)[0]
                game.push(row, col)
                print(f"Minimax placed X at row {row} and column {col}.")
                game.display_board()

                if game.check_winner() != ' ':
                    print(f"{game.check_winner()} wins!")
                    break
            else:
                was_valid = True
                while True:
                    move = survivor.make_move(game_history=game.history, was_valid=was_valid, game_loops=i +1)
                    was_valid = game.push(move.row, move.col)

                    if was_valid is False:
                        print(f"LLM placed O at row {move.row} and column {move.col}.")

                    if was_valid:
                        print(f"LLM placed O at row {move.row} and column {move.col}.")
                        game.display_board()
                        break

                if game.check_winner() != ' ':
                    print(f"{game.check_winner()} wins!")
                    break

if __name__ == "__main__":
    main()
