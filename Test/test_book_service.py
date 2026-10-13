import os
from datetime import datetime as Datetime
from sys import path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE = os.path.join(_ROOT, "Code")
path.insert(1, _ROOT)
path.insert(1, _CODE)

import pytest

from Code.Book import Book as CodeBook
from domain.book import Book, BookState
from domain.user import User
from repository.book_repository import BookRepository
from repository.connection import get_connection, init_database
from repository.user_repository import UserRepository
from service.book_service import (
    FILTER_AVAILABLE,
    FILTER_BORROWED,
    FILTER_RESERVED,
    BookService,
    action_visibility,
)


@pytest.fixture
def book_env(tmp_path):
    db_path = str(tmp_path / "books.db")
    init_database(db_path)
    users = UserRepository(db_path)
    books = BookRepository(db_path)
    reader = User("Azar", "Haji", "azarhajipour", "1234", "azar@haji.com", "09111234567")
    users.upsert(reader, role="costumer")
    available = Book("Available Title", "Author A", BookState.Available)
    borrowed = Book("Borrowed Title", "Author B", BookState.Borrowed, borrowed=reader,
                    borrowed_time=Datetime(2026, 1, 1), return_time=Datetime(2026, 1, 8))
    reserved = Book("Reserved Title", "Author C", BookState.Available, reserved=reader)
    books.upsert(available)
    books.upsert(borrowed)
    books.upsert(reserved)
    service = BookService(books, users)
    _map, users_by_id = users.list_all()
    return service, books, users_by_id, db_path, reader


class TestBookService:
    def test_book_shim_same_class(self):
        assert CodeBook is Book
        assert not hasattr(BookState, "Reserved")

    def test_list_filters_match_fill_table(self, book_env):
        service, _repo, users_by_id, _db, _reader = book_env
        available = service.list_books(FILTER_AVAILABLE, users_by_id=users_by_id)
        borrowed = service.list_books(FILTER_BORROWED, users_by_id=users_by_id)
        reserved = service.list_books(FILTER_RESERVED, users_by_id=users_by_id)
        assert [b.name for b in available] == ["Available Title"]
        assert [b.name for b in borrowed] == ["Borrowed Title"]
        assert [b.name for b in reserved] == ["Reserved Title"]
        assert available[0].is_reserved is False
        assert reserved[0].is_reserved is True
        assert reserved[0].state == BookState.Available

    def test_action_visibility_matches_fill_table_buttons(self):
        assert action_visibility(FILTER_AVAILABLE) == {"reserve": True, "borrow": True}
        assert action_visibility(FILTER_BORROWED) == {"reserve": True, "borrow": False}
        assert action_visibility(FILTER_RESERVED) == {"reserve": False, "borrow": False}

    def test_state_column_never_stores_reserved(self, book_env):
        _service, _repo, _users, db_path, _reader = book_env
        conn = get_connection(db_path)
        states = [row[0] for row in conn.execute("SELECT state FROM Books").fetchall()]
        conn.close()
        assert "Reserved" not in states
        assert set(states) <= {"Available", "Borrowed"}

    def test_person_module_alias(self):
        from Person import Person as P1
        from Code.Person import Person as P2
        assert P1 is P2
