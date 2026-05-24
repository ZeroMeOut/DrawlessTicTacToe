from packages.tictactoe import TicTacToe

def evaluate(game: TicTacToe, depth: int) -> float:
    winner = game.check_winner()
    if winner == 'X':
        return 10 + depth
    elif winner == 'O':
        return -10 - depth
    return 0

def minimax_alpha_beta(
    game: TicTacToe,
    depth: int,
    is_maximizing: bool,
    alpha: float,
    beta: float
) -> tuple[tuple[int, int], float]:

    if depth == 0 or game.check_winner() != ' ':
        return ((0, 0), evaluate(game, depth))

    best_move = (0, 0)  

    if is_maximizing:
        max_eval = float('-inf')
        for move in game.avalible_moves:
            row, col = move
            game.push(row, col)
            _, score = minimax_alpha_beta(game, depth - 1, False, alpha, beta)
            game.revert()

            if score > max_eval:
                max_eval = score
                best_move = move  ## Here was the bug

            alpha = max(alpha, score)
            if beta <= alpha:
                break

        return (best_move, max_eval)

    else:
        min_eval = float('inf')
        for move in game.avalible_moves:
            row, col = move
            game.push(row, col)
            _, score = minimax_alpha_beta(game, depth - 1, True, alpha, beta)
            game.revert()

            if score < min_eval:
                min_eval = score
                best_move = move  

            beta = min(beta, score)
            if beta <= alpha:
                break

        return (best_move, min_eval)