import chess

class Board:
    def __init__(self):
        self.last_valid_board = new_board()

    def validate_board_change(self, board):
        diffs = []
        for y in range(8): 
            for x in range(8):
                if self.last_valid_board[x][y] != board[x][y]:
                    diffs.append([x,y,self.last_valid_board[x][y],board[x][y]])

        return diffs
    
def empty_board():
    return [['_' for _ in range(8)] for _ in range(8)]

def new_board():
    board =      [['W' for _ in range(8)] for _ in range(2)]
    board.extend([['_' for _ in range(8)] for _ in range(4)])
    board.extend([['B' for _ in range(8)] for _ in range(2)])
    return board
