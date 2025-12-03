import pytest
import Board

def test_new_board():
    b = Board.Board()
    assert(b.validate_board_change(Board.new_board()) == False)
    move_board = Board.new_board()
    move_board[1][0] = '_'
    move_board[3][0] = 'W'
    assert(b.validate_board_change(move_board) == True)
