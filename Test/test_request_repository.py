import os
from sys import path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE = os.path.join(_ROOT, "Code")
path.insert(1, _ROOT)
path.insert(1, _CODE)

from datetime import datetime as Datetime

from domain.request import Request, RequestStatus, RequestType
from domain.user import User
from domain.book import Book, BookState
from repository.book_repository import BookRepository
from repository.connection import init_database
from repository.request_repository import RequestRepository
from repository.user_repository import UserRepository


def _env(tmp_path):
    db_path = str(tmp_path / "req.db")
    init_database(db_path)
    users = UserRepository(db_path)
    books = BookRepository(db_path)
    reader = User("Azar", "Haji", "reader1", "1234", "r@a.com", "09111234567")
    users.upsert(reader, role="costumer")
    book = Book("Title One", "Author", BookState.Available)
    books.upsert(book)
    return RequestRepository(db_path), reader, book, db_path


class TestRequestRepository:
    def test_add_get_and_status(self, tmp_path):
        repo, reader, book, _db = _env(tmp_path)
        req = Request(reader.user_id, book.book_id, RequestType.BORROW, RequestStatus.PENDING)
        rid = repo.add(req)
        loaded = repo.get(rid)
        assert loaded.status == RequestStatus.PENDING
        assert loaded.request_type == RequestType.BORROW
        count = repo.update_status(rid, RequestStatus.ACCEPTED, reader.user_id, Datetime.now())
        assert count == 1
        assert repo.get(rid).status == RequestStatus.ACCEPTED
        assert repo.update_status(rid, RequestStatus.DENIED, reader.user_id, Datetime.now()) == 0

    def test_list_all_is_entities_only(self, tmp_path):
        repo, reader, book, _db = _env(tmp_path)
        repo.add(Request(reader.user_id, book.book_id, RequestType.RESERVE))
        rows = repo.list_all()
        assert len(rows) == 1
        assert isinstance(rows[0], Request)
        assert not hasattr(rows[0], "book_name")
