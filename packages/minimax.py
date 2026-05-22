from  packages.tictactoe import TicTacToe

def evaluate(game: TicTacToe) -> float:
    winner = game.check_winner()
    if winner == 'X':
        return 1
    elif winner == 'O':
        return -1
    else:
        return 0

def minimax(game: TicTacToe, depth: int, is_maximizing: bool, alpha: float, beta: float) -> tuple[tuple[int, int], float]:
    if depth == 0 or game.check_winner() != ' ':
        return ((0, 0), evaluate(game))

    if is_maximizing:
        maxEval = float('-inf')
        for move in game.avalible_moves:
            row, col = move
            game.push(row, col)

            _, score = minimax(game, depth - 1, not is_maximizing, alpha, beta)

            game.revert()
            maxEval = max(score, maxEval)
            alpha = max(alpha, score)
            if beta <= alpha:
                break
        return (move, maxEval)
            
    else:
        minEval = float('inf')
        for move in game.avalible_moves:
            row, col = move
            game.push(row, col)

            _, score = minimax(game, depth - 1, not is_maximizing, alpha, beta)

            game.revert()
            minEval = min(score, minEval)
            beta = min(beta, score)
            if beta <= alpha:
                break
        return (move, minEval)