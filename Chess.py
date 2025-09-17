
COLOR = ["WHITE", "BLACK"]
PIECE_TYPE = ["KING", "QUEEN", "ROOK", "BISHOP", "KNIGHT", "PAWN"]

class Chess:
    def __init__(self):
        self.board = {}
        self.turn = 0

    def newGame(self):
        self.board.clear()
        self.board[(0,0)] = Piece("BLACK", "ROOK")
    
    
    def movePiece(self, x:int, y:int, toX:int, toY:int) -> bool:
        if self.board[(x,y)] == None:
            return False
        piece = self.board[x,y]
        match piece.type:
            case "KING":
                pass
            case "QUEEN":
                pass
            case "ROOK":
                pass
            case "BISHOP":
                pass
            case "KNIGHT":
                pass
            case "PAWN":
                pass

class Piece():
    def __init__(self, color:str, type:str):
        if not COLOR.__contains__(color):
            raise ValueError("Invalid piece color.")

        if not PIECE_TYPE.__contains__(type):
            raise ValueError("Invalid piece type.")
        
        self.color = color
        self.type = type

    