import pytest
import Board
import chess
import numpy as np
import numpy.testing as npt

def test_new_board():
    b = Board.Board()
    assert(b.validate_board_change(Board.new_board()) == False)
    move_board = Board.new_board()
    move_board[1][0] = '_'
    move_board[3][0] = 'W'
    assert(b.validate_board_change(move_board) == True)

def test_set_board():
    b = Board.Board()
    b.set_last_valid_board(Board.empty_board)
    c = chess.Board()
    b.set_board(c)

    assert(b.get_last_valid_board() == Board.new_board())
