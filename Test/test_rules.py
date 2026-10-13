import os
from sys import path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE = os.path.join(_ROOT, "Code")
path.insert(1, _ROOT)
path.insert(1, _CODE)

from domain.rules import MAX_BORROW, MAX_RESERVE, can_borrow, can_reserve


class TestBorrowLimits:
    def test_borrow_cap_is_three(self):
        assert MAX_BORROW == 3
        assert can_borrow(0)
        assert can_borrow(2)
        assert not can_borrow(3)
        assert not can_borrow(4)

    def test_reserve_cap_is_three(self):
        assert MAX_RESERVE == 3
        assert can_reserve(2)
        assert not can_reserve(3)
