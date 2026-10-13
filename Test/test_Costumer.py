import os
import pytest
from sys import path
from datetime import datetime as Datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path.insert(1, _ROOT)
from Code.Person import Person
from Code.Book import Book
from Code.Costumer import Costumer
from Code.Tools import BookState, CommandState, Tools
from Code.Password import is_hashed, verify_password


def _cmd(value):
    return getattr(value, "value", value)


def _assert_cmd(actual, expected):
    assert _cmd(actual) == _cmd(expected)


def _assert_orders(actual, expected):
    assert len(actual) == len(expected)
    for got, want in zip(actual, expected):
        assert set(got.keys()) == set(want.keys())
        for key, value in want.items():
            if key == "state":
                assert _cmd(got[key]) == _cmd(value)
            else:
                assert got[key] == value


class TestCostumer:
    @pytest.fixture
    def setUp(self):
        self.book1 = Book("Me Before you 1", "JoJo Moyes", BookState.Available)
        self.book2 = Book("Me Before you 2", "JoJo Moyes", BookState.Available)
        self.book3 = Book("Me Before you 3", "JoJo Moyes", BookState.Available)
        self.book4 = Book("Me after You", "Ms. joJo Moyes", BookState.Available, Person())

        self.costumer1 = Costumer("zahra", "Karimi", "ZAHRAkarimi", "1234", "zahrakarimi@Gmail.Com", "09101234567")
        self.costumer2 = Costumer("Fateme", "azizi", "fatemeazizi", "4321", "Fatemeazizi#gmail.com", "+5369745")

    def test_names(self, setUp):
        assert self.costumer1.first_name == "Zahra"
        assert self.costumer1.last_name == "Karimi"

        assert self.costumer2.first_name == "Fateme"
        assert self.costumer2.last_name == "Azizi"

    def test_credintial(self, setUp):
        assert self.costumer1.username == "zahrakarimi"
        assert is_hashed(self.costumer1.password)
        assert verify_password("1234", self.costumer1.password)
        assert self.costumer1.email == "zahrakarimi@gmail.com"
        assert self.costumer1.phone == "+989101234567"

        assert self.costumer2.username == "fatemeazizi"
        assert is_hashed(self.costumer2.password)
        assert verify_password("4321", self.costumer2.password)
        assert self.costumer2.email == "---"
        assert self.costumer2.phone == "---"

    def test_get_available_books(self, setUp):
        assert self.costumer1.get_available_books([self.book1, self.book2]) == [self.book1.name, self.book2.name]

    def test_borrow_book(self, setUp):
        time1 = Datetime.now()
        time2 = Datetime.now()
        time3 = Datetime.now()
        time4 = Datetime.now()
        _assert_cmd(self.costumer1.borrow_book(self.book1, time1), CommandState.Done)
        _assert_cmd(self.costumer1.borrow_book(self.book2, time2, 14), CommandState.Done)
        _assert_cmd(self.costumer1.borrow_book(self.book3, time3, 22), CommandState.Done)

        _assert_cmd(self.costumer1.borrow_book(self.book1, time1), CommandState.BorrowedBefore)
        _assert_cmd(self.costumer1.borrow_book(self.book4, time4, 20), CommandState.MaximumBorrow)

        _assert_orders(self.costumer1.orders, [
            {'book': self.book1, 'order': 'borrowing book', 'date': time1, 'state': CommandState.Done},
            {'book': self.book2, 'order': 'borrowing book', 'date': time2, 'state': CommandState.Done},
            {'book': self.book3, 'order': 'borrowing book', 'date': time3, 'state': CommandState.Done},
            {'book': self.book1, 'order': 'borrowing book', 'date': time1, 'state': CommandState.BorrowedBefore},
            {'book': self.book4, 'order': 'borrowing book', 'date': time4,
             'state': CommandState.MaximumBorrow}])

        assert list(self.costumer1.borrowed_books.keys()) == [self.book1, self.book2, self.book3]

        assert self.book1.state == BookState.Borrowed
        assert self.book2.state == BookState.Borrowed
        assert self.book3.state == BookState.Borrowed
        assert self.book4.state != BookState.Borrowed

        assert self.book1.borrowed == self.costumer1
        assert self.book2.borrowed == self.costumer1
        assert self.book3.borrowed == self.costumer1
        assert self.book4.borrowed != self.costumer1

        assert self.book1.borrowed_time == time1
        assert self.book2.borrowed_time == time2
        assert self.book3.borrowed_time == time3
        assert self.book4.borrowed_time != time4

        assert self.book1.return_time == Tools.add_time(time1, 7)
        assert self.book2.return_time == Tools.add_time(time2, 14)
        assert self.book3.return_time == Tools.add_time(time3, 21)
        assert self.book4.return_time != Tools.add_time(time4, 7)

    def test_reserve_book(self, setUp):
        time1 = Datetime.now()
        time2 = Datetime.now()
        time3 = Datetime.now()
        time4 = Datetime.now()
        _assert_cmd(self.costumer1.reserve_book(self.book1, time1), CommandState.Done)
        _assert_cmd(self.costumer1.reserve_book(self.book2, time2), CommandState.Done)
        _assert_cmd(self.costumer1.reserve_book(self.book3, time3), CommandState.Done)
        _assert_cmd(self.costumer1.reserve_book(self.book4, time4), CommandState.MaximumReserved)

        assert self.costumer1.reserve == [self.book1, self.book2, self.book3]

        assert self.book1.reserved == self.costumer1
        assert self.book2.reserved == self.costumer1
        assert self.book3.reserved == self.costumer1
        assert self.book4.reserved != self.costumer1

        _assert_orders(self.costumer1.orders, [
            {'book': self.book1, 'order': 'reserving book', 'date': time1, 'state': CommandState.Done},
            {'book': self.book2, 'order': 'reserving book', 'date': time2, 'state': CommandState.Done},
            {'book': self.book3, 'order': 'reserving book', 'date': time3, 'state': CommandState.Done},
            {'book': self.book4, 'order': 'reserving book', 'date': time4,
             'state': CommandState.MaximumReserved}])

    def test_extension_book(self, setUp):
        time1 = Datetime.now()
        time2 = Datetime.now()
        self.costumer1.borrow_book(self.book1, time1)
        self.costumer1.borrow_book(self.book2, time2)
        book1_return_time = self.book1.return_time

        time3 = Datetime.now()
        time4 = Datetime.now()
        time5 = Datetime.now()
        time6 = Datetime.now()
        _assert_cmd(self.costumer1.extension_book(self.book1, time3, 1), CommandState.Done)
        _assert_cmd(self.costumer1.extension_book(self.book1, time4, 6), CommandState.Done)
        _assert_cmd(self.costumer1.extension_book(self.book1, time5, 1), CommandState.NoMoreExtension)

        _assert_cmd(self.costumer1.extension_book(self.book2, time6, 8), CommandState.ExtensionLimitReached)

        assert self.costumer1.borrowed_books[self.book1]['return_time'] == Tools.add_time(book1_return_time, 7)
        assert self.costumer1.borrowed_books[self.book1]['extension'] == 7

        assert self.costumer1.borrowed_books[self.book2]['return_time'] == self.book2.return_time
        assert self.costumer1.borrowed_books[self.book2]['extension'] == 0

        _assert_orders(self.costumer1.orders, [
            {'book': self.book1, 'order': 'borrowing book', 'date': time1, 'state': CommandState.Done},
            {'book': self.book2, 'order': 'borrowing book', 'date': time2, 'state': CommandState.Done},
            {'book': self.book1, 'order': 'extension returning date of book', 'date': time3,
             'state': CommandState.Done},
            {'book': self.book1, 'order': 'extension returning date of book', 'date': time4,
             'state': CommandState.Done},
            {'book': self.book1, 'order': 'extension returning date of book', 'date': time5,
             'state': CommandState.NoMoreExtension},
            {'book': self.book2, 'order': 'extension returning date of book', 'date': time6,
             'state': CommandState.ExtensionLimitReached}])

    def test_return_book(self, setUp):
        time1 = Datetime.now()
        time2 = Datetime.now()
        time3 = Datetime.now()
        time4 = Datetime.now()
        self.costumer1.borrow_book(self.book1, time1)
        self.costumer1.borrow_book(self.book2, time2)
        self.costumer1.borrow_book(self.book3, time3)
        self.costumer1.extension_book(self.book3, time4, 7)

        book1_borrowed_time = self.book1.borrowed_time
        book2_borrowed_time = self.book2.borrowed_time
        book3_borrowed_time = self.book3.borrowed_time

        time5 = Datetime.now()
        time6 = Datetime.now()
        time7 = Datetime.now()
        returned = self.costumer1.return_book(self.book1, time3, self.book1.return_time)
        _assert_cmd(returned, CommandState.Done)
        billed = self.costumer1.return_book(self.book2, time4, Tools.add_time(self.book2.return_time, 7))
        assert _cmd(billed[0]) == _cmd(CommandState.Bill) and billed[1] == 14
        billed2 = self.costumer1.return_book(self.book3, time5, Tools.add_time(self.book3.return_time, 9))
        assert _cmd(billed2[0]) == _cmd(CommandState.Bill) and billed2[1] == 24
        assert not len(self.costumer1.borrowed_books)

        assert self.book1.state == BookState.Available and self.book2.state == BookState.Available and self.book3.state == BookState.Available

        _assert_orders(self.costumer1.orders, [
            {'book': self.book1, 'order': 'borrowing book', 'date': time1, 'state': CommandState.Done},
            {'book': self.book2, 'order': 'borrowing book', 'date': time2, 'state': CommandState.Done},
            {'book': self.book3, 'order': 'borrowing book', 'date': time3, 'state': CommandState.Done},
            {'book': self.book3, 'order': 'extension returning date of book', 'date': time4,
             'state': CommandState.Done},

            {'book': self.book1, 'order': 'returning book', 'date': time5, 'state': CommandState.Done,
             'bill': 0},
            {'book': self.book2, 'order': 'returning book', 'date': time6, 'state': CommandState.Bill,
             'bill': 14},
            {'book': self.book3, 'order': 'returning book', 'date': time7, 'state': CommandState.Bill,
             'bill': 24}])

        self.costumer1.returned_books = {
            self.book1: {'borrowed_time': time1, 'returned_time': book1_borrowed_time,
                         'extension': 0, 'delay': 0},
            self.book2: {'borrowed_time': time2, 'returned_time': Tools.add_time(book2_borrowed_time, 7),
                         'extension': 0, 'delay': 7},
            self.book3: {'borrowed_time': time3, 'returned_time': Tools.add_time(book3_borrowed_time, 7),
                         'extension': 7, 'delay': 9},
        }
