import pytest
import Board

def test_new_board():
    b = Board.Board()
    diffs = b.validate_board_change(Board.new_board())
    assert(len(diffs) == 0)
    
    diffs = b.validate_board_change(Board.empty_board())
    assert(len(diffs) == 32)
