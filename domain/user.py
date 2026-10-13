from re import search
from typing import Union
from datetime import datetime as Datetime

from Person import Person
from Lending import Lending
from Tools import CommandState, BookState, Tools
from Receipt_Bill import Receipt, Bill

from domain.password import hash_password, is_hashed


class User(Person):
    """Reader or officer. Code.Costumer is this class (shim alias)."""

    def __init__(
        self,
        first_name: str,
        last_name: str,
        username: str,
        password: str,
        email: str,
        phone: str,
        role: str = "costumer",
    ) -> None:
        self.user_id = None
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.password = password
        self.email = email
        self.phone = phone
        self.role = role if role in ("officer", "costumer") else "costumer"
        self.orders = []
        self.reserve = []
        self.borrowed_books = {}
        self.returned_books = {}

    @property
    def first_name(self) -> str:
        return self._first_name

    @first_name.setter
    def first_name(self, first_name: str):
        self._first_name = first_name.title()

    @property
    def last_name(self) -> str:
        return self._last_name

    @last_name.setter
    def last_name(self, last_name: str):
        self._last_name = last_name.title()

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, username: str):
        self._username = username.lower()

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, password: str):
        if not password:
            self._password = ""
            return
        if is_hashed(password):
            self._password = password
        else:
            self._password = hash_password(password)

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, email: str):
        regex = '^[A-Za-z0-9._%+-]+[@][A-Za-z0-9.-]+[A-Z|a-z]{2,3}$'
        if search(regex, email):
            self._email = email.lower()
        else:
            self._email = "---"

    @property
    def phone(self) -> str:
        return self._phone

    @phone.setter
    def phone(self, phone: str):
        if phone.startswith("0"):
            self._phone = "+98" + phone[1:]
        elif phone.startswith("+98"):
            self._phone = phone
        else:
            self._phone = "---"

    @property
    def orders(self) -> list:
        return self._orders

    @orders.setter
    def orders(self, orders: list):
        self._orders = orders

    @property
    def reserve(self) -> list:
        return self._reserve

    @reserve.setter
    def reserve(self, reserve: list):
        self._reserve = reserve

    @property
    def borrowed_books(self) -> dict:
        return self._borrowed_books

    @borrowed_books.setter
    def borrowed_books(self, borrowed_books: dict):
        self._borrowed_books = borrowed_books

    @property
    def returned_books(self) -> dict:
        return self._returned_books

    @returned_books.setter
    def returned_books(self, returned_books: dict):
        self._returned_books = returned_books

    def get_available_books(self, books: list) -> list:
        books = sorted(books, key=lambda x: x.name)
        books_names = [book.name for book in books]
        self.orders.append({'order': 'geting available books', 'date': Datetime.now()})
        return books_names

    def borrow_book(self, book: Lending, date: Datetime, return_days: int = 7) -> CommandState:
        if return_days > 21:
            return_days = 21

        self.orders.append({'book': book, 'order': 'borrowing book', 'date': date, 'state': CommandState.Done})

        if book in self.borrowed_books.keys():
            self.orders[-1]['state'] = CommandState.BorrowedBefore
            return CommandState.BorrowedBefore

        elif len(self.borrowed_books.keys()) < 3:
            self.borrowed_books[book] = {"borrowed_time": date, "return_time": Tools.add_time(date, return_days),
                                         "extension": 0}
            book.state = BookState.Borrowed
            book.borrowed = self
            book.borrowed_time = date
            book.return_time = Tools.add_time(date, return_days)
            return CommandState.Done

        else:
            self.orders[-1]['state'] = CommandState.MaximumBorrow
            return CommandState.MaximumBorrow

    def reserve_book(self, book: Lending, date: Datetime) -> CommandState:
        self.orders.append({'book': book, 'order': 'reserving book', 'date': date, 'state': CommandState.Done})

        if len(self.reserve) < 3:
            self.reserve.append(book)
            book.reserved = self
            return CommandState.Done

        else:
            self.orders[-1]['state'] = CommandState.MaximumReserved
            return CommandState.MaximumReserved

    def extension_book(self, book: Lending, date: Datetime, add_date: int) -> CommandState:
        self.orders.append(
            {'book': book, 'order': 'extension returning date of book', 'date': date, 'state': CommandState.Done})

        if self.borrowed_books[book]['extension'] == 7:
            self.orders[-1]['state'] = CommandState.NoMoreExtension
            return CommandState.NoMoreExtension

        elif self.borrowed_books[book]['extension'] + add_date > 7:
            self.orders[-1]['state'] = CommandState.ExtensionLimitReached
            return CommandState.ExtensionLimitReached

        elif self.borrowed_books[book]['extension'] + add_date <= 7:
            book.return_time = Tools.add_time(self.borrowed_books[book]['return_time'], add_date)
            self.borrowed_books[book]['return_time'] = book.return_time
            self.borrowed_books[book]['extension'] += add_date
            return CommandState.Done

    def return_book(self, book: Lending, date: Datetime, returned_time: Datetime) -> Union[CommandState, list]:
        self.orders.append(
            {'book': book, 'order': 'returning book', 'date': date, 'state': CommandState.Done, 'bill': 0})

        self.returned_books[book] = {'borrowed_time': self.borrowed_books[book]['borrowed_time'],
                                     'returned_time': returned_time,
                                     'extension': self.borrowed_books[book]['extension'],
                                     'delay': Tools.find_delay(self.borrowed_books[book]['return_time'],
                                                               returned_time)}

        book.state = BookState.Available
        book.borrowed = Person()
        book.borrowed_time = None
        book.return_time = None
        del self.borrowed_books[book]

        if self.returned_books[book]['delay'] == 0:
            self.orders[-1]['state'] = CommandState.Done
            return CommandState.Done

        else:
            cost = Tools.find_bill(self.returned_books[book]['delay'])

            self.orders[-1]['state'] = CommandState.Bill
            self.orders[-1]['bill'] = cost
            return [CommandState.Bill, cost]

    def issue_receipt(self, book: Lending, costumer: Person, delay: int) -> Receipt:
        return Receipt(book, costumer, delay)

    def issue_bill(self, book: Lending, costumer: Person, delay: int, cost: int) -> Bill:
        return Bill(book, costumer, delay, cost)

    def books_status(self, books: list) -> dict:
        return {'Available Books': [book for book in books if book.state == BookState.Available],
                'Borrowed Books': [book for book in books if book.state == BookState.Borrowed]}
