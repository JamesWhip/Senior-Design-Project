import pytest
import PieceDetection as pd

def test_order_points():
    points = [(1,1), (10, 10), (1, 10), (10, 1)]
    assert (pd.order_points(points) == [(1,1), (10, 1), (10, 10), (1, 10)])
