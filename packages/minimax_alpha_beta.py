from packages.tictactoe import TicTacToe

def evaluate(game: TicTacToe, depth: int, player: str) -> float:
    other_player = 'O' if player == 'X' else 'X'
    winner = game.check_winner()

    if winner == player:
        return 100 + depth
    elif winner == other_player:
        return -100 - depth
    
    ## Since it's drawless, we need to estimate who is winning based on 2-in-a-rows
    score = 0
    winning_combinations = [
        [(0, 0), (0, 1), (0, 2)], [(1, 0), (1, 1), (1, 2)], [(2, 0), (2, 1), (2, 2)], ## Rows
        [(0, 0), (1, 0), (2, 0)], [(0, 1), (1, 1), (2, 1)], [(0, 2), (1, 2), (2, 2)], ## Cols
        [(0, 0), (1, 1), (2, 2)], [(0, 2), (1, 1), (2, 0)]                            ## Diagonals
    ]
    
    occupied = {(r, c): p for r, c, p in game.fifo_storage}
    
    for combo in winning_combinations:
        players = [occupied[cell] for cell in combo if cell in occupied]
        ## If a combo contains 2 pieces of the same player and 0 of the other, it's a threat
        if len(players) == 2 and len(set(players)) == 1:
            if players[0] == player:
                score += 10 
            else:
                score -= 10

    return score

def minimax_alpha_beta(game: TicTacToe, depth: int = 6, is_maximizing: bool = True, 
                       alpha: float = float('-inf'), beta: float = float('inf'), player: str = 'X') -> tuple[tuple[int, int] | None, float]:

    if game.check_winner() != ' ' or depth == 0:
        return (None, evaluate(game, depth, player))

    best_move = None
    moves_to_try = list(game.avalible_moves)

    if is_maximizing:
        max_eval = float('-inf')
        for move in moves_to_try:
            row, col = move
            game.push(row, col)
            _, score = minimax_alpha_beta(game, depth - 1, False, alpha, beta)
            game.revert()

            if score > max_eval:
                max_eval = score
                best_move = move

            alpha = max(alpha, score)
            if beta <= alpha:
                break
        return (best_move, max_eval)

    else:
        min_eval = float('inf')
        for move in moves_to_try:
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