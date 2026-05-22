from ollama import chat
from ollama import ChatResponse


history = [['X', ' ', ' '], [' ', 'X', 'X'], ['O', 'O', ' ']]

response: ChatResponse = chat(model='gemma3n:e2b', messages=[
  {
    'role': 'user',
    'content': 'You are to play a move in a game of tic-tac-toe as O. '
    'The board is represented as a 3x3 grid, with rows and columns indexed from 0 to 2. The history of states of the board is as follows:'
    f'{history}'
  },
])
print(response['message']['content'])
# or access fields directly from the response object
print(response.message.content)