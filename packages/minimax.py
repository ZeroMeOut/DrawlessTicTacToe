from  packages.tictactoe import TicTacToe

def evaluate(game: TicTacToe, depth: int) -> float:
    winner = game.check_winner()
    if winner == 'X':
        return 10 + depth
    elif winner == 'O':
        return -10 - depth
    else:
        return 0

def minimax(game: TicTacToe, depth: int, is_maximizing: bool) -> tuple[tuple[int, int], float]:
     
    if is_maximizing:
        best = ((0, 0),float('-inf'))
    else:
        best = ((0, 0),float('inf'))
    
    if depth == 0 or game.check_winner() != ' ':
        return ((0, 0), evaluate(game, depth))

    for move in game.avalible_moves:
        row, col = move
        game.push(row, col)

        _, score = minimax(game, depth - 1, not is_maximizing)

        game.revert()

        if is_maximizing:
            if score > best[1]:
                best = (move, score)
        else:
            if score < best[1]:
                best = (move, score)
    return best