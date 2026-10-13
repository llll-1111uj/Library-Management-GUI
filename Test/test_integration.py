import os
from sys import path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE = os.path.join(_ROOT, "Code")
path.insert(1, _ROOT)
path.insert(1, _CODE)

import pytest

from domain.book import Book, BookState
from domain.exceptions import ApprovalError, RequestAlreadyHandled
from domain.password import is_hashed, verify_password
from domain.request import RequestStatus, RequestType
from domain.user import User
from Officer import Officer
from repository.book_repository import BookRepository
from repository.borrow_repository import BorrowRepository
from repository.connection import get_connection, init_database
from repository.request_repository import RequestRepository
from repository.user_repository import UserRepository
from service.approval_service import ApprovalService
from service.auth_service import AuthService
from service.book_service import FILTER_AVAILABLE, BookService
from service.borrow_service import BorrowService


@pytest.fixture
def stack(tmp_path):
    db_path = str(tmp_path / "int.db")
    init_database(db_path)
    users = UserRepository(db_path)
    books = BookRepository(db_path)
    catalog = []
    for i in range(25):
        book = Book("Catalog %02d" % i, "Author %s" % (i % 3), BookState.Available)
        books.upsert(book)
        catalog.append(book)
    return {
        "db": db_path,
        "users": users,
        "books": books,
        "catalog": catalog,
        "auth": AuthService(users),
        "borrow": BorrowService(RequestRepository(db_path)),
        "approval": ApprovalService(db_path),
        "loans": BorrowRepository(db_path),
        "req": RequestRepository(db_path),
        "search": BookService(books, users),
    }


class TestIntegration:
    def test_password_hash_persisted(self, stack):
        person = stack["auth"].register_costumer(
            "hashuser", "pw1", "pw1", "Hash User", "h@a.com", "09111234567", []
        )
        assert is_hashed(person.password)
        loaded = stack["users"].get_by_username_or_email("hashuser")
        assert is_hashed(loaded.password)
        assert verify_password("pw1", loaded.password)
        conn = get_connection(stack["db"])
        stored = conn.execute("SELECT password FROM Users WHERE username=?", ("hashuser",)).fetchone()[0]
        conn.close()
        assert stored != "pw1"
        assert is_hashed(stored)

    def test_request_state_machine(self, stack):
        reader = stack["auth"].register_costumer(
            "smreader", "pw1", "pw1", "SM Reader", "sm@a.com", "09111234567", []
        )
        officer = stack["auth"].register_officer(
            "smofficer", "pw1", "pw1", "SM Officer", "smo@a.com", "09111234568", ["smreader"]
        )
        book = stack["catalog"][0]
        pending = stack["borrow"].submit_borrow(reader, book)
        assert pending.status == RequestStatus.PENDING
        stacked = stack["borrow"].submit_borrow(reader, book)
        assert stacked.request_id == pending.request_id
        stack["approval"].confirm(pending.request_id, officer)
        assert stack["req"].get(pending.request_id).status == RequestStatus.ACCEPTED
        with pytest.raises(RequestAlreadyHandled):
            stack["approval"].deny(pending.request_id, officer)
        ret = stack["borrow"].submit_return(reader, book)
        assert ret.request_type == RequestType.RETURN
        stack["approval"].deny(ret.request_id, officer)
        assert stack["req"].get(ret.request_id).status == RequestStatus.DENIED
        assert stack["books"].get_by_id(book.book_id, {}).state == BookState.Borrowed

    def test_borrow_limit_and_transaction_rollback(self, stack):
        reader = stack["auth"].register_costumer(
            "capreader", "pw1", "pw1", "Cap Reader", "c@a.com", "09111234567", []
        )
        officer = stack["auth"].register_officer(
            "capofficer", "pw1", "pw1", "Cap Officer", "co@a.com", "09111234568", ["capreader"]
        )
        for book in stack["catalog"][:3]:
            req = stack["borrow"].submit_borrow(reader, book)
            stack["approval"].confirm(req.request_id, officer)
        assert len(stack["loans"].list_active_by_user(reader.user_id)) == 3
        fourth = stack["catalog"][3]
        req4 = stack["borrow"].submit_borrow(reader, fourth)
        with pytest.raises(ApprovalError):
            stack["approval"].confirm(req4.request_id, officer)
        assert stack["req"].get(req4.request_id).status == RequestStatus.PENDING
        assert stack["books"].get_by_id(fourth.book_id, {}).state == BookState.Available
        conn = get_connection(stack["db"])
        loan_count = conn.execute(
            "SELECT COUNT(*) FROM borrow_record WHERE user_id=? AND borrow_status='borrowed'",
            (reader.user_id,),
        ).fetchone()[0]
        conn.close()
        assert loan_count == 3

    def test_search_pagination(self, stack):
        users_map, users_by_id = stack["users"].list_all()
        page1 = stack["search"].search_books(
            "Catalog", FILTER_AVAILABLE, page=1, page_size=20, users_by_id=users_by_id
        )
        assert page1["total"] == 25
        assert page1["total_pages"] == 2
        assert len(page1["books"]) == 20
        page2 = stack["search"].search_books(
            "Catalog", FILTER_AVAILABLE, page=2, page_size=20, users_by_id=users_by_id
        )
        assert len(page2["books"]) == 5
        overflow = stack["search"].search_books(
            "Catalog", FILTER_AVAILABLE, page=9, page_size=20, users_by_id=users_by_id
        )
        assert overflow["page"] == 2
        names = [b.name for b in page1["books"] + page2["books"]]
        assert names == sorted(names)
