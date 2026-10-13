"""Deprecated book/loan persistence helpers.

Use repository.connection for SQLite access and repository.user_repository for users.
This module is kept so GUIManager book/loan calls still work until A2/A3.
"""
# REFACTOR-TRANSITION: Database.py is a compatibility facade; expect DeprecationWarning.
import warnings
from datetime import timedelta

from repository.connection import (  # noqa: F401
    DB_PATH,
    DT_FMT,
    RESERVE_EXPIRE_DAYS,
    fmt_dt,
    get_connection,
    init_database,
    parse_dt,
)
from repository.book_repository import BookRepository
from repository.borrow_repository import BorrowRepository, restore_user_book_state as _restore_loans
from repository.notify import refresh_notifications as _refresh_notifications
from repository.reserve_repository import ReserveRepository
from repository.user_repository import UserRepository, upsert_user_on_conn

# REFACTOR-TRANSITION: warning is documented in README Known Issues.
warnings.warn(
    "Code.Database is deprecated; use repository.connection and repository.user_repository.",
    DeprecationWarning,
    stacklevel=2,
)


def upsert_user(conn, person, role=None):
    # REFACTOR-TRANSITION: delegate user writes to UserRepository.
    return upsert_user_on_conn(conn, person, role)


def upsert_book(conn, book):
    # REFACTOR-TRANSITION: delegate to BookRepository; keep signature for persist_*.
    return BookRepository().upsert(book, conn=conn)


def save_users_and_books(users_map, books):
    conn = get_connection()
    for person in users_map.get("costumer", []):
        upsert_user(conn, person, "costumer")
    for person in users_map.get("officer", []):
        upsert_user(conn, person, "officer")
    for book in books:
        upsert_book(conn, book)
    conn.commit()
    conn.close()


def load_users():
    # REFACTOR-TRANSITION: GUIManager A1 uses UserRepository.list_all directly.
    return UserRepository().list_all()


def load_books(users_by_id):
    # REFACTOR-TRANSITION: GUIManager.readSqlite still calls this until A3.
    return BookRepository().list_all(users_by_id)


def restore_user_book_state(users_map, books_by_id):
    # REFACTOR-TRANSITION: logic lives in borrow_repository.restore_user_book_state
    return _restore_loans(users_map, books_by_id)


def persist_borrow(user, book, borrow_time, due_time):
    # REFACTOR-TRANSITION: prefer ApprovalService.confirm
    conn = get_connection()
    upsert_user(conn, user)
    upsert_book(conn, book)
    books = BookRepository()
    books.update_state(book.book_id, "Borrowed", borrow_time, due_time, user, conn=conn)
    BorrowRepository().insert_borrow(user.user_id, book.book_id, borrow_time, due_time, conn)
    ReserveRepository().fulfill(user.user_id, book.book_id, conn)
    conn.commit()
    refresh_notifications(conn)
    conn.close()


def persist_return(user, book, return_time):
    conn = get_connection()
    upsert_user(conn, user)
    upsert_book(conn, book)
    reserved_user_id = getattr(book, "reserved_user_id", None) or getattr(getattr(book, "reserved", None), "user_id", None)
    books = BookRepository()
    books.update_state(book.book_id, "Available", None, None, None, conn=conn)
    books.set_reserved(book.book_id, reserved_user_id, conn)
    BorrowRepository().mark_returned(user.user_id, book.book_id, return_time, conn)
    ReserveRepository().activate_next(book.book_id, return_time, conn)
    conn.commit()
    refresh_notifications(conn)
    conn.close()


def persist_reserve(user, book, reserve_time):
    from domain.reservation import Reservation
    conn = get_connection()
    upsert_user(conn, user)
    upsert_book(conn, book)
    status = "waiting"
    expire_time = None
    if getattr(book.state, "value", str(book.state)) == "Available":
        status = "active"
        expire_time = reserve_time + timedelta(days=RESERVE_EXPIRE_DAYS)
    ReserveRepository().insert(
        Reservation(book.book_id, user.user_id, reserve_time, expire_time, status), conn
    )
    BookRepository().set_reserved(book.book_id, user.user_id, conn)
    conn.commit()
    refresh_notifications(conn)
    conn.close()


def persist_extension(user, book, due_time):
    conn = get_connection()
    upsert_user(conn, user)
    upsert_book(conn, book)
    ext = 0
    if hasattr(user, "borrowed_books") and book in user.borrowed_books:
        ext = user.borrowed_books[book].get("extension", 0)
    BookRepository().update_state(book.book_id, "Borrowed", book.borrowed_time, due_time, user, conn=conn)
    BorrowRepository().update_due(user.user_id, book.book_id, due_time, ext, conn)
    conn.commit()
    conn.close()


def refresh_notifications(conn=None):
    return _refresh_notifications(conn)
