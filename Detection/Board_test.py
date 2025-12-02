import pytest
import Board

def test_validate_board_change():
    b = Board.Board()
    diffs = b.validate_board_change(Board.new_board())
    assert(len(diffs) == 0)
