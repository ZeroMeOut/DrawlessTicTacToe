import os
import json
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
    
    ## Fallback condition if the LLM fails 3 time or any prasing issues
    def random_fallback_move(self, available_moves: list[tuple[int, int]]) -> Move:
        chosen = random.choice(available_moves)
        return Move(row=chosen[0], col=chosen[1])

    ## Update the history with the latest game state and move validity, which will be passed to the LLM for context in the next turn
    def add_to_history(self, game_history: list[dict], was_valid: bool, game_loops: int) -> None:
        if self.previous_move_made is not None:
            if was_valid:
                previous_move_message = f'Your previous move was {self.previous_move_made} which was valid.'
            else:
                previous_move_message = f'Your previous move was {self.previous_move_made} which was invalid.'
        else:
            previous_move_message = 'Error then parsing previous move or no previous move made.'

        info = {
            'game_history': game_history,
            'previous_move_message': previous_move_message,
            'random_choice_proc': 'Yes' if self.consecutive_invalid >= 3 else 'No',
            'loop_player_is_in': game_loops,
        }
        self.history.append(info)
        
        if len(self.history) > 50:
            self.history.pop(0)

    def make_move(self, game_history: list[dict], was_valid: bool, game_loops: int) -> Move:
        # Update the invalid move streak
        if self.previous_move_made is not None:
            if was_valid:
                self.consecutive_invalid = 0
            else:
                self.consecutive_invalid += 1
        
        ## Add the current game state and move validity to the history 
        self.add_to_history(game_history, was_valid, game_loops)  

        # Random fallback if the LLM has failed 3 times in a row
        if self.consecutive_invalid >= 3:
            move = self.random_fallback_move(game_history[-1]['avalible_moves'])
            self.previous_move_made = move
            self.consecutive_invalid = 0  # reset after random proc
            return move

        # Normal LLM path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'game_logs.json')
        
        with open(json_path, 'r') as f:
            examples = json.load(f)

        response: ChatResponse = chat(
            model=self.model_name,
            messages=[{
                'role': 'user',
                'content': (
                    'You are to play a move in a game of tic-tac-toe as O. '
                    'The board is represented as a 3x3 grid, with rows and columns '
                    f'example games: {examples} '
                    f'indexed from 0 to 2. Here is some info: {self.history}'
                )
            }],
            format=Move.model_json_schema(),
        )

        if response.message.content is None:
            move = self.random_fallback_move(game_history[-1]['avalible_moves'])
            self.previous_move_made = move
            return move

        ## If the LLM response can't be parsed for some reason
        try:
            self.previous_move_made = Move.model_validate_json(response.message.content)
            move = Move.model_validate_json(response.message.content)
            return move
        
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            move = self.random_fallback_move(game_history[-1]['avalible_moves'])
            self.previous_move_made = move
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