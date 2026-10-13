import os
from sys import path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE = os.path.join(_ROOT, "Code")
path.insert(1, _ROOT)
path.insert(1, _CODE)

import pytest

from domain.book import Book, BookState
from domain.exceptions import AuthError
from domain.request import RequestStatus
from domain.user import User
from Officer import Officer
from repository.audit_repository import AuditRepository
from repository.book_repository import BookRepository
from repository.connection import get_connection, init_database
from repository.request_repository import RequestRepository
from repository.user_repository import UserRepository
from service.approval_service import ApprovalService
from service.auth_service import AuthService
from service.borrow_service import BorrowService


def _columns(conn, table):
    return [row[1] for row in conn.execute("PRAGMA table_info(%s)" % table).fetchall()]


@pytest.fixture
def audit_env(tmp_path):
    db_path = str(tmp_path / "audit.db")
    init_database(db_path)
    users = UserRepository(db_path)
    books = BookRepository(db_path)
    reader = User("Azar", "Haji", "reader1", "1234", "r@a.com", "09111234567")
    officer = Officer("Mahdi", "Haji", "officer1", "4321", "o@a.com", "09117654321")
    users.upsert(reader, role="costumer")
    users.upsert(officer, role="officer")
    book = Book("Title 1", "Author", BookState.Available)
    books.upsert(book)
    return {
        "db": db_path,
        "users": users,
        "reader": reader,
        "officer": officer,
        "book": book,
        "auth": AuthService(users, AuditRepository(db_path)),
        "borrow": BorrowService(RequestRepository(db_path)),
        "approval": ApprovalService(db_path),
        "audit": AuditRepository(db_path),
    }


class TestAudit:
    def test_schema_columns(self, audit_env):
        conn = get_connection(audit_env["db"])
        cols = _columns(conn, "audit_log")
        conn.close()
        assert cols == [
            "id", "user_id", "action", "target_type", "target_id", "detail", "created_at",
        ]

    def test_register_login_and_officer_actions(self, audit_env):
        env = audit_env
        env["auth"].register_costumer(
            "newreader", "pw", "pw", "New Reader", "n@a.com", "09110000000", ["reader1", "officer1"],
        )
        env["auth"].register_officer(
            "newofficer", "pw", "pw", "New Officer", "no@a.com", "09110000001",
            ["reader1", "officer1", "newreader"],
        )
        users_map, _by_id = env["users"].list_all()
        all_users = users_map["costumer"] + users_map["officer"]
        env["auth"].login("reader1", "1234", all_users)
        with pytest.raises(AuthError):
            env["auth"].login("reader1", "wrong", all_users)
        req = env["borrow"].submit_borrow(env["reader"], env["book"])
        env["approval"].confirm(req.request_id, env["officer"])
        ret = env["borrow"].submit_return(env["reader"], env["book"])
        env["approval"].deny(ret.request_id, env["officer"])

        rows = env["audit"].list_recent(200)
        actions = [row["action"] for row in rows]
        assert "REGISTER" in actions
        assert "ADD_OFFICER" in actions
        assert "LOGIN" in actions
        assert "LOGIN_FAILED" in actions
        assert "CONFIRM" in actions
        assert "DENY" in actions
        assert rows[0]["id"] >= rows[-1]["id"]
        login = next(row for row in rows if row["action"] == "LOGIN")
        assert login["username"] == "reader1"
        failed = next(row for row in rows if row["action"] == "LOGIN_FAILED")
        assert failed["username"] is None
        assert failed["user_id"] is None
        confirm = next(row for row in rows if row["action"] == "CONFIRM")
        assert confirm["username"] == "officer1"
        assert confirm["target_type"] == "request"
        deny = next(row for row in rows if row["action"] == "DENY")
        assert deny["username"] == "officer1"
        assert env["borrow"].request_repo.get(ret.request_id).status == RequestStatus.DENIED
