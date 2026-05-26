import os
import sys
import inspect
import importlib
from google import genai
from dotenv import load_dotenv
from pydantic import BaseModel
from google.genai import types

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_FILE = os.path.join(BASE_DIR, "generated_heuristic.py")


class GeneratedHeuristic(BaseModel):
    reasoning: str
    python_code: str


class LLMPlayer:
    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)
        self.generated_code: str = ""
        self.generated_reasoning: str = ""
        self.prompt: str = (
            'You are to generate a python AI class called CustomAIStrategy to play an endless/FIFO tic-tac-toe game.\n'
            'RULES & CONSTRAINTS:\n'
            '- No imports allowed. Use pure Python.\n'
            '- All helper functions must be defined inside the class.\n'
            '- Do NOT include any markdown code blocks (like ```python) in your python_code output field.\n\n'
            'REQUIRED CLASS STRUCTURE:\n'
            'class CustomAIStrategy:\n'
            '    def __init__(self, board: list[list[str]], fifo_storage: list[tuple[int, int, str]], your_sign: str, current_player: str):\n'
            '        self.board = board\n'
            '        self.fifo_storage = fifo_storage\n'
            '        self.your_sign = your_sign\n'
            '        self.current_player = current_player\n\n'
            '    def main(self) -> tuple[int, int]:\n'
            '        # Your strategic implementation goes here\n'
            '        # Must analyze the board and return a valid (row, col) tuple from empty spaces.\n'
            '        return (row, col)\n\n'
            'Board format example: [[" ", " ", " "], ["X", " ", " "], [" ", "O", " "]]\n'
            'fifo_storage format example: [(1, 0, "X"), (2, 1, "O")] where index 0 is the oldest piece to be evicted.'
        )

    def write_generated_file(self, code: str) -> None:
        with open(GENERATED_FILE, "w") as f:
            f.write(code)

    def class_checker(self) -> bool:
        module_name = "generated_heuristic"
        target_class_name = "CustomAIStrategy"

        if not os.path.exists(GENERATED_FILE):
            print("Generated file does not exist.")
            return False

        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)

        try:
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)

            if not hasattr(module, target_class_name):
                return False

            potential_class = getattr(module, target_class_name)
            return inspect.isclass(potential_class)

        except Exception as e:
            print(f"class_checker error: {e}")
            return False

    def generate_algo(self) -> bool:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=self.prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeneratedHeuristic,
            ),
        )

        if response.text is None:
            print("LLM did not return any content.")
            return False

        result = GeneratedHeuristic.model_validate_json(response.text)
        self.generated_code = result.python_code
        self.generated_reasoning = result.reasoning
        self.write_generated_file(result.python_code)
        return True

    def improve_algo(self, feedback: str, game_history: list[tuple[int, int, str]]) -> bool:
        improvement_prompt = (
            f"The previous heuristic you generated had the following reasoning: {self.generated_reasoning}\n"
            f"And the following code:\n{self.generated_code}\n"
            f"Based on the game history: {game_history}\n"
            f"And the feedback: {feedback}\n"
            "Please generate an improved version of the heuristic, following the same format as before:\n"
            f"{self.prompt}"
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=improvement_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeneratedHeuristic,
            ),
        )

        if response.text is None:
            print("LLM did not return any content.")
            return False

        result = GeneratedHeuristic.model_validate_json(response.text)
        self.generated_code = result.python_code
        self.generated_reasoning = result.reasoning
        self.write_generated_file(result.python_code)
        return True

    def generate_until_valid(self) -> None:
        while True:
            if self.generate_algo() and self.class_checker():
                return
            print("Failed to generate a valid heuristic. Retrying...")

    def improve_until_valid(self, feedback: str, game_history: list[tuple[int, int, str]]) -> None:
        while True:
            if self.improve_algo(feedback, game_history) and self.class_checker():
                return
            print("Failed to produce a valid improved heuristic. Retrying...")

    def initialise(self) -> None:
        self.generate_until_valid()

    def improve(self, feedback: str, game_history: list[tuple[int, int, str]]) -> None:
        if not feedback and not game_history:
            return
        self.improve_until_valid(feedback, game_history)


if __name__ == "__main__":
    model_name = "gemini-2.5-flash"
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("GEMINI_API_KEY must be set in the environment variables.")
    else:
        player = LLMPlayer(model_name=model_name, api_key=api_key)
        player.initialise()
        print("Initial algorithm generated successfully.")
        print(f"Reasoning: {player.generated_reasoning}")