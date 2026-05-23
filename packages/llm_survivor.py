from ollama import chat, ChatResponse
from pydantic import BaseModel

class Move(BaseModel):
    row: int
    col: int

class LLMSurvivor:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.history: list = []
        self.preivous_move_made: Move | None = None

    def make_move(self, game_history: list[dict], was_valid: bool) -> Move:

        if was_valid and self.preivous_move_made is not None:
            previous_move_messasge = f'Your pevious move was {self.preivous_move_made} which was valid.'
        elif not was_valid and self.preivous_move_made is not None:
            previous_move_messasge = f'Your pevious move was {self.preivous_move_made} which was invalid.'
        else:
            previous_move_messasge = ' '

        info = {
            'game_history': game_history,
            'previous_move_message': previous_move_messasge,
        }

        self.history.append(info)

        if len(self.history) > 20:
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

        self.preivous_move_made = Move.model_validate_json(response.message.content)
        
        move = Move.model_validate_json(response.message.content)
        return move

def test():
    survivor = LLMSurvivor(model_name='gemma3n:e2b')
    move =survivor.make_move(game_history=[{'current_player': 'O', 'board': [['X', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'X', 'board': [['X', ' ', ' '], [' ', ' ', ' '], ['O', ' ', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 1), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'O', 'board': [['X', ' ', ' '], [' ', 'X', ' '], ['O', ' ', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 2), (2, 1), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'X', 'board': [['X', ' ', ' '], [' ', 'X', ' '], ['O', 'O', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 2), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'O', 'board': [['X', ' ', ' '], [' ', 'X', 'X'], ['O', 'O', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (2, 2)], 'next_move_to_be_removed': None}]
                                          , was_valid=True)
    print(f"LLM chose to place O at row {move.row} and column {move.col}.")

if __name__ == "__main__":    
    test()