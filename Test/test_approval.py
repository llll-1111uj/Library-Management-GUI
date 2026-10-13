import os
from sys import path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE = os.path.join(_ROOT, "Code")
path.insert(1, _ROOT)
path.insert(1, _CODE)

import pytest

from domain.book import Book, BookState
from domain.exceptions import ApprovalError, RequestAlreadyHandled
from domain.request import RequestStatus
from domain.user import User
from Officer import Officer
from repository.audit_repository import AuditRepository
from repository.book_repository import BookRepository
from repository.borrow_repository import BorrowRepository
from repository.connection import get_connection, init_database
from repository.request_repository import RequestRepository
from repository.user_repository import UserRepository
from service.approval_service import ApprovalService
from service.borrow_service import BorrowService


def _env(tmp_path, extra_books=1):
    db_path = str(tmp_path / "appr.db")
    init_database(db_path)
    users = UserRepository(db_path)
    books = BookRepository(db_path)
    reader = User("Azar", "Haji", "reader1", "1234", "r@a.com", "09111234567")
    officer = Officer("Mahdi", "Haji", "officer1", "4321", "o@a.com", "09117654321")
    users.upsert(reader, role="costumer")
    users.upsert(officer, role="officer")
    catalog = []
    for i in range(extra_books):
        book = Book("Title %s" % (i + 1), "Author", BookState.Available)
        books.upsert(book)
        catalog.append(book)
    borrow = BorrowService(RequestRepository(db_path))
    approval = ApprovalService(db_path)
    return {
        "db": db_path,
        "reader": reader,
        "officer": officer,
        "books": catalog,
        "book_repo": books,
        "borrow": borrow,
        "approval": approval,
        "req": RequestRepository(db_path),
        "loans": BorrowRepository(db_path),
        "audit": AuditRepository(db_path),
    }


class TestApproval:
    def test_confirm_borrow(self, tmp_path):
        env = _env(tmp_path)
        req = env["borrow"].submit_borrow(env["reader"], env["books"][0])
        env["approval"].confirm(req.request_id, env["officer"])
        book = env["book_repo"].get_by_id(env["books"][0].book_id, {})
        assert book.state == BookState.Borrowed
        loans = env["loans"].list_active_by_user(env["reader"].user_id)
        assert len(loans) == 1
        assert env["req"].get(req.request_id).status == RequestStatus.ACCEPTED

    def test_confirm_return_sets_available(self, tmp_path):
        env = _env(tmp_path)
        req = env["borrow"].submit_borrow(env["reader"], env["books"][0])
        env["approval"].confirm(req.request_id, env["officer"])
        ret = env["borrow"].submit_return(env["reader"], env["books"][0])
        env["approval"].confirm(ret.request_id, env["officer"])
        book = env["book_repo"].get_by_id(env["books"][0].book_id, {})
        assert book.state == BookState.Available

    def test_deny_does_not_change_book(self, tmp_path):
        env = _env(tmp_path)
        req = env["borrow"].submit_borrow(env["reader"], env["books"][0])
        env["approval"].deny(req.request_id, env["officer"])
        book = env["book_repo"].get_by_id(env["books"][0].book_id, {})
        assert book.state == BookState.Available
        assert env["req"].get(req.request_id).status == RequestStatus.DENIED

    def test_confirm_twice_raises(self, tmp_path):
        env = _env(tmp_path)
        req = env["borrow"].submit_borrow(env["reader"], env["books"][0])
        env["approval"].confirm(req.request_id, env["officer"])
        with pytest.raises(RequestAlreadyHandled):
            env["approval"].confirm(req.request_id, env["officer"])

    def test_borrow_limit_rolls_back(self, tmp_path):
        env = _env(tmp_path, extra_books=4)
        for book in env["books"][:3]:
            req = env["borrow"].submit_borrow(env["reader"], book)
            env["approval"].confirm(req.request_id, env["officer"])
        fourth = env["borrow"].submit_borrow(env["reader"], env["books"][3])
        with pytest.raises(ApprovalError) as exc:
            env["approval"].confirm(fourth.request_id, env["officer"])
        assert exc.value.message == "User's maximum borrowed books reached !"
        assert env["req"].get(fourth.request_id).status == RequestStatus.PENDING
        book = env["book_repo"].get_by_id(env["books"][3].book_id, {})
        assert book.state == BookState.Available
        conn = get_connection(env["db"])
        count = conn.execute("SELECT COUNT(*) FROM borrow_record").fetchone()[0]
        conn.close()
        assert count == 3

    def test_renew_over_seven_rejected(self, tmp_path):
        env = _env(tmp_path)
        req = env["borrow"].submit_borrow(env["reader"], env["books"][0])
        env["approval"].confirm(req.request_id, env["officer"])
        renew = env["borrow"].submit_renew(env["reader"], env["books"][0], 10)
        with pytest.raises(ApprovalError) as exc:
            env["approval"].confirm(renew.request_id, env["officer"])
        assert exc.value.message == "User passed the limit of maximum extension days !"
        assert env["req"].get(renew.request_id).status == RequestStatus.PENDING

    def test_renew_same_as_current_rejected(self, tmp_path):
        env = _env(tmp_path)
        req = env["borrow"].submit_borrow(env["reader"], env["books"][0])
        env["approval"].confirm(req.request_id, env["officer"])
        first = env["borrow"].submit_renew(env["reader"], env["books"][0], 5)
        env["approval"].confirm(first.request_id, env["officer"])
        second = env["borrow"].submit_renew(env["reader"], env["books"][0], 5)
        with pytest.raises(ApprovalError) as exc:
            env["approval"].confirm(second.request_id, env["officer"])
        assert exc.value.message == "User already used the extension week !"

    def test_renew_seven_ok(self, tmp_path):
        env = _env(tmp_path)
        req = env["borrow"].submit_borrow(env["reader"], env["books"][0])
        env["approval"].confirm(req.request_id, env["officer"])
        renew = env["borrow"].submit_renew(env["reader"], env["books"][0], 7)
        env["approval"].confirm(renew.request_id, env["officer"])
        conn = get_connection(env["db"])
        loan = env["loans"].get_active(env["reader"].user_id, env["books"][0].book_id, conn)
        conn.close()
        assert loan.extension_days == 7
        assert env["req"].get(renew.request_id).status == RequestStatus.ACCEPTED
