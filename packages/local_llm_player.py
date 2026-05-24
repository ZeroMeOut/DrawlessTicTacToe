import random
from pydantic import BaseModel
from ollama import chat, ChatResponse

class Move(BaseModel):
    row: int
    col: int


class LocalLLMPlayer:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.history: list = []
        self.previous_move_made: Move | None = None
        self.consecutive_invalid: int = 0  # tracks back-to-back invalid moves

    def make_move(self, game_history: list[dict], was_valid: bool, game_loops: int) -> Move:

        # Update the invalid move streak
        if self.previous_move_made is not None:
            if was_valid:
                self.consecutive_invalid = 0
            else:
                self.consecutive_invalid += 1

        # Build the previous move message
        if was_valid and self.previous_move_made is not None:
            previous_move_message = f'Your previous move was {self.previous_move_made} which was valid.'
        elif not was_valid and self.previous_move_made is not None:
            previous_move_message = f'Your previous move was {self.previous_move_made} which was invalid.'
        else:
            previous_move_message = ' '

        # Random fallback if the LLM has failed 3 times in a row
        if self.consecutive_invalid >= 3:
            available = game_history[-1]['avalible_moves']
            chosen = random.choice(available)
            move = Move(row=chosen[0], col=chosen[1])

            self.history.append({
                'game_history': game_history,
                'previous_move_message': previous_move_message,
                'random_choice_proc': 'Yes — 3 consecutive invalid moves triggered random fallback',
                'loop_player_is_in': game_loops,
            })
            if len(self.history) > 50:
                self.history.pop(0)

            self.previous_move_made = move
            self.consecutive_invalid = 0  # reset after random proc
            return move

        # Normal LLM path
        info = {
            'game_history': game_history,
            'previous_move_message': previous_move_message,
            'random_choice_proc': 'No',
            'loop_player_is_in': game_loops,
        }

        self.history.append(info)
        if len(self.history) > 50:
            self.history.pop(0)

        response: ChatResponse = chat(
            model=self.model_name,
            messages=[{
                'role': 'user',
                'content': (
                    'You are to play a move in a game of tic-tac-toe as O. '
                    'The board is represented as a 3x3 grid, with rows and columns '
                    f'indexed from 0 to 2. Here is some info: {self.history}'
                )
            }],
            format=Move.model_json_schema(),
        )

        if response.message.content is None:
            raise ValueError("LLM did not return a move.")

        self.previous_move_made = Move.model_validate_json(response.message.content)
        move = Move.model_validate_json(response.message.content)
        return move

def test():
    Player = LocalLLMPlayer(model_name='gemma3n:e2b')
    move = Player.make_move(game_history=[{'current_player': 'O', 'board': [['X', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'X', 'board': [['X', ' ', ' '], [' ', ' ', ' '], ['O', ' ', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 1), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'O', 'board': [['X', ' ', ' '], [' ', 'X', ' '], ['O', ' ', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 2), (2, 1), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'X', 'board': [['X', ' ', ' '], [' ', 'X', ' '], ['O', 'O', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 2), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'O', 'board': [['X', ' ', ' '], [' ', 'X', 'X'], ['O', 'O', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (2, 2)], 'next_move_to_be_removed': None}]
                                          , was_valid=True
                                          , game_loops=5)
    print(f"LLM chose to place O at row {move.row} and column {move.col}.")

if __name__ == "__main__":    
    test()