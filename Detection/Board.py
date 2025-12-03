import chess

class Board:
    def __init__(self):
        self.last_valid_board = new_board()
        self.chess = chess.Board()

    def set_board(self, board : chess.Board):
        self.chess = board
    
    def validate_board_change(self, board):
        diffs = get_board_diffs(self.last_valid_board, board)

        moved_from_diffs = []
        moved_to_diffs = []
        take_piece_diffs = []
        for x,y,a,b in diffs:
            match (a, b):
                case ('W', '_') | ('B', '_'):
                    moved_from_diffs.append((x,y))
                case ('_', 'W') | ('_', 'B'):
                    moved_to_diffs.append((x,y))
                case ('B', 'W') | ('W', 'B'):
                    take_piece_diffs.append((x,y))

        print(len(moved_from_diffs), len(moved_to_diffs), len(take_piece_diffs))
        match len(moved_from_diffs), len(moved_to_diffs), len(take_piece_diffs):
            case 1, 1, 0:
                # try move
                    move = chess.Move.from_uci(chr(97 + moved_from_diffs[0][1]) + str(moved_from_diffs[0][0]+1) + chr(97 + moved_to_diffs[0][1]) + str(moved_to_diffs[0][0]+1))
            case 1, 0, 1:
                # piece was taken
                try:
                    move = chess.Move.from_uci(chr(97 + moved_from_diffs[0][1]) + str(moved_from_diffs[0][0]+1) + chr(97 + moved_to_diffs[0][1]) + str(moved_to_diffs[0][0]+1))
                except:
                    return False
            case _, _, _:
                # not a move
                return False

        print(move)
        if move in self.chess.legal_moves:
            self.chess.push(move)
            self.last_valid_board = board
            return True
        
        return False
    
def empty_board():
    return [['_' for _ in range(8)] for _ in range(8)]

def new_board():
    board =      [['W' for _ in range(8)] for _ in range(2)]
    board.extend([['_' for _ in range(8)] for _ in range(4)])
    board.extend([['B' for _ in range(8)] for _ in range(2)])
    return board

def get_board_diffs(board, new_board):
    diffs = []
    for y in range(8): 
        for x in range(8):
            if board[x][y] != new_board[x][y]:
                diffs.append([x,y,board[x][y],new_board[x][y]])

    return diffs