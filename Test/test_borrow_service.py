import os
from sys import path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE = os.path.join(_ROOT, "Code")
path.insert(1, _ROOT)
path.insert(1, _CODE)

from domain.book import Book, BookState
from domain.request import RequestStatus, RequestType
from domain.user import User
from repository.book_repository import BookRepository
from repository.connection import get_connection, init_database
from repository.request_repository import RequestRepository
from repository.user_repository import UserRepository
from service.borrow_service import BorrowService


def _env(tmp_path):
    db_path = str(tmp_path / "sub.db")
    init_database(db_path)
    users = UserRepository(db_path)
    books = BookRepository(db_path)
    reader = User("Azar", "Haji", "reader1", "1234", "r@a.com", "09111234567")
    users.upsert(reader, role="costumer")
    book = Book("Title One", "Author", BookState.Available)
    books.upsert(book)
    svc = BorrowService(RequestRepository(db_path))
    return svc, reader, book, db_path, books


class TestBorrowServiceSubmit:
    def test_submit_borrow_pending_does_not_change_book(self, tmp_path):
        svc, reader, book, db_path, books = _env(tmp_path)
        req = svc.submit_borrow(reader, book)
        assert req.status == RequestStatus.PENDING
        reloaded = books.get_by_id(book.book_id, {})
        assert reloaded.state == BookState.Available
        conn = get_connection(db_path)
        state = conn.execute("SELECT state FROM Books WHERE book_id=?", (book.book_id,)).fetchone()[0]
        conn.close()
        assert state == "Available"

    def test_submit_borrow_twice_one_pending_row(self, tmp_path):
        svc, reader, book, db_path, _books = _env(tmp_path)
        first = svc.submit_borrow(reader, book)
        second = svc.submit_borrow(reader, book)
        assert first.request_id == second.request_id
        conn = get_connection(db_path)
        count = conn.execute(
            "SELECT COUNT(*) FROM requests WHERE user_id=? AND book_id=? AND request_type=? AND status=?",
            (reader.user_id, book.book_id, RequestType.BORROW.value, RequestStatus.PENDING.value),
        ).fetchone()[0]
        conn.close()
        assert count == 1
