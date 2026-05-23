from ollama import chat, ChatResponse
from pydantic import BaseModel

class Move(BaseModel):
    row: int
    col: int

class LLMSurvivor:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.is_valid_move = True

    def make_move(self, history: list[dict]) -> Move:
        response: ChatResponse = chat(
            model=self.model_name,
            messages=[{
                'role': 'user',
                'content': (
                    'You are to play a move in a game of tic-tac-toe as O. '
                    'The board is represented as a 3x3 grid, with rows and columns '
                    f'indexed from 0 to 2. The history of board states is: {history}'
                )
            }],
            format=Move.model_json_schema(),
        )
        if response.message.content is None:
            raise ValueError("LLM did not return a move.")
        
        move = Move.model_validate_json(response.message.content)
        return move

def main():
    survivor = LLMSurvivor(model_name='gemma3n:e2b')
    row, col =survivor.make_move(history=[{'current_player': 'O', 'board': [['X', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'X', 'board': [['X', ' ', ' '], [' ', ' ', ' '], ['O', ' ', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 1), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'O', 'board': [['X', ' ', ' '], [' ', 'X', ' '], ['O', ' ', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 2), (2, 1), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'X', 'board': [['X', ' ', ' '], [' ', 'X', ' '], ['O', 'O', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (1, 2), (2, 2)], 'next_move_to_be_removed': None}, 
                                          {'current_player': 'O', 'board': [['X', ' ', ' '], [' ', 'X', 'X'], ['O', 'O', ' ']], 'avalible_moves': [(0, 1), (0, 2), (1, 0), (2, 2)], 'next_move_to_be_removed': None}])
    print(f"LLM chose to place O at row {row[1]} and column {col[1]}.")

if __name__ == "__main__":    
    main()