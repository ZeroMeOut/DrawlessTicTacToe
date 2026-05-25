from packages.tictactoe import TicTacToe
## Idk why I need to do package. here when it is in the same folder
## My main isnt working without it which is annoying

def evaluate(game: TicTacToe, depth: int, active_player: str) -> float:
    other_player = 'O' if active_player == 'X' else 'X'
    winner = game.check_winner()

    if winner == active_player:
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
            if players[0] == active_player:
                score += 10 
            else:
                score -= 10

    return score

def minimax_alpha_beta(game: TicTacToe, depth: int = 6, 
                       alpha: float = float('-inf'), beta: float = float('inf')) -> tuple[tuple[int, int] | None, float]:
    current_moving_player = game.current_player

    if game.check_winner() != ' ' or depth == 0:
        return (None, evaluate(game, depth, current_moving_player))

    best_move = None
    max_eval = float('-inf')
    moves_to_try = list(game.avalible_moves)

    for move in moves_to_try:
        row, col = move
        game.push(row, col)
        _, opponent_score = minimax_alpha_beta(game, depth - 1, -beta, -alpha)
        score = -opponent_score
        
        game.revert()

        if score > max_eval:
            max_eval = score
            best_move = move

        alpha = max(alpha, score)
        if alpha >= beta:
            break  # Beta cut-off

    return (best_move, max_eval)