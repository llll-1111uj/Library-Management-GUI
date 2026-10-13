from datetime import datetime as Datetime, timedelta
from enum import Enum

from Lending import Lending
from Person import Person


class BookState(Enum):
    Available = "Available"
    Borrowed = "Borrowed"


class Book(Lending):
    def __init__(
        self,
        name: str,
        author: str,
        state: BookState,
        borrowed: Person = None,
        borrowed_time: Datetime = None,
        return_time: Datetime = None,
        reserved: Person = None,
    ):
        self.book_id = None
        self.name = name
        self.author = author
        self.state = state
        self.reserved = reserved if reserved is not None else Person()
        self.borrowed = borrowed if borrowed is not None else Person()
        self.borrowed_time = borrowed_time
        self.return_time = return_time

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name.title()

    @property
    def author(self) -> str:
        return self._author

    @author.setter
    def author(self, author: str):
        self._author = author.title()

    @property
    def state(self) -> BookState:
        return self._state

    @state.setter
    def state(self, state: BookState):
        self._state = state

    @property
    def borrowed(self) -> Person:
        return self._borrowed

    @borrowed.setter
    def borrowed(self, borrowed: Person):
        self._borrowed = borrowed

    @property
    def reserved(self) -> Person:
        return self._reserved

    @reserved.setter
    def reserved(self, reserved: Person):
        self._reserved = reserved

    @property
    def is_reserved(self) -> bool:
        """Presentation helper: reserved person is attached. Not a BookState."""
        return bool(getattr(self.reserved, "first_name", None))

    @property
    def borrowed_time(self) -> Datetime:
        return self._borrowed_time

    @borrowed_time.setter
    def borrowed_time(self, borrowed_time: Datetime):
        self._borrowed_time = borrowed_time

    @property
    def return_time(self) -> Datetime:
        return self._return_time

    @return_time.setter
    def return_time(self, return_time: Datetime):
        if return_time is None:
            self._return_time = return_time
        elif self.borrowed_time == return_time:
            self._return_time = return_time + timedelta(days=7)
        else:
            self._return_time = return_time

    def __str__(self):
        if self.borrowed and getattr(self.borrowed, "first_name", None):
            borrow_person = f'{self.borrowed.first_name} {self.borrowed.last_name}'
            borrow_time = self.borrowed_time.strftime("%Y/%m/%d") if self.borrowed_time else "---"
            return_time = self.return_time.strftime("%Y/%m/%d") if self.return_time else "---"
        else:
            borrow_person, borrow_time, return_time = "---", "---", "---"

        reserv_person = (
            f'{self.reserved.first_name} {self.reserved.last_name}' if self.is_reserved else "---"
        )

        text = f'Name: {self.name}\nAuthor: {self.author}\n' \
               f'State: {self.state.value}\n' \
               f'Borrowed: {borrow_person}, Date: {borrow_time}\nReturn Date: {return_time}\n' \
               f'Reserved: {reserv_person}'

        return text
