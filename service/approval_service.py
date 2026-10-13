"""Single-transaction confirm/deny. Books.state is Available/Borrowed only."""
from datetime import datetime as Datetime

from domain.book import BookState
from domain.exceptions import ApprovalError, RequestAlreadyHandled
from domain.request import RequestStatus, RequestType
from domain.reservation import Reservation
from domain.rules import (
    DEFAULT_LOAN_DAYS,
    MAX_EXTENSION_DAYS,
    add_time,
    can_borrow,
    can_reserve,
    find_bill,
    find_delay,
)
from repository.audit_repository import AuditRepository
from repository.book_repository import BookRepository
from repository.borrow_repository import BorrowRepository
from repository.connection import RESERVE_EXPIRE_DAYS, get_connection
from repository.request_repository import RequestRepository
from repository.reserve_repository import ReserveRepository


class _Ref:
    def __init__(self, user_id):
        self.user_id = user_id


class ApprovalService:
    def __init__(self, db_path=None, request_repo=None, book_repo=None, borrow_repo=None,
                 reserve_repo=None, audit_repo=None):
        self.db_path = db_path
        self.request_repo = request_repo or RequestRepository(db_path)
        self.book_repo = book_repo or BookRepository(db_path)
        self.borrow_repo = borrow_repo or BorrowRepository(db_path)
        self.reserve_repo = reserve_repo or ReserveRepository(db_path)
        self.audit_repo = audit_repo or AuditRepository(db_path)

    def confirm(self, request_id, officer):
        conn = get_connection(self.db_path)
        extra = {"bill": 0}
        try:
            conn.execute("BEGIN IMMEDIATE")
            request = self.request_repo.get(request_id, conn=conn)
            if request is None:
                raise ApprovalError("This request is already handled !")
            if request.status != RequestStatus.PENDING:
                raise RequestAlreadyHandled()
            book = self.book_repo.get_by_id(request.book_id, {}, conn=conn)
            if book is None:
                raise ApprovalError("User doesn't have the book !")
            now = Datetime.now()
            rtype = request.request_type
            if rtype == RequestType.BORROW:
                self._confirm_borrow(conn, request, book, now)
            elif rtype == RequestType.RESERVE:
                self._confirm_reserve(conn, request, book, now)
            elif rtype == RequestType.RENEW:
                self._confirm_renew(conn, request, book)
            elif rtype == RequestType.RETURN:
                extra["bill"] = self._confirm_return(conn, request, book, now)
            else:
                raise ApprovalError("This request is already handled !")
            updated = self.request_repo.update_status(
                request_id, RequestStatus.ACCEPTED, officer.user_id, now, conn=conn
            )
            if updated != 1:
                raise RequestAlreadyHandled()
            self.audit_repo.add(
                officer.user_id, "CONFIRM", "request", request_id, rtype.value, conn=conn
            )
            conn.commit()
            request.status = RequestStatus.ACCEPTED
            request.handled_by = officer.user_id
            request.handled_at = now
            extra["request"] = request
            return extra
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def deny(self, request_id, officer):
        conn = get_connection(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            request = self.request_repo.get(request_id, conn=conn)
            if request is None or request.status != RequestStatus.PENDING:
                raise RequestAlreadyHandled()
            now = Datetime.now()
            updated = self.request_repo.update_status(
                request_id, RequestStatus.DENIED, officer.user_id, now, conn=conn
            )
            if updated != 1:
                raise RequestAlreadyHandled()
            self.audit_repo.add(
                officer.user_id, "DENY", "request", request_id, request.request_type.value, conn=conn
            )
            conn.commit()
            request.status = RequestStatus.DENIED
            return request
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _confirm_borrow(self, conn, request, book, now):
        if self.borrow_repo.get_active(request.user_id, request.book_id, conn):
            raise ApprovalError("User already borrowed this book !")
        if not can_borrow(self.borrow_repo.count_active(request.user_id, conn)):
            raise ApprovalError("User's maximum borrowed books reached !")
        if book.state != BookState.Available:
            raise ApprovalError("User already borrowed this book !")
        due = add_time(now, DEFAULT_LOAN_DAYS)
        self.book_repo.update_state(
            request.book_id, BookState.Borrowed, now, due, _Ref(request.user_id), conn=conn
        )
        self.borrow_repo.insert_borrow(request.user_id, request.book_id, now, due, conn)
        self.reserve_repo.fulfill(request.user_id, request.book_id, conn)

    def _confirm_reserve(self, conn, request, book, now):
        if not can_reserve(self.reserve_repo.count_active(request.user_id, conn)):
            raise ApprovalError("User's maximum reserved books reached !")
        status = "waiting"
        expire_time = None
        if book.state == BookState.Available:
            status = "active"
            expire_time = add_time(now, RESERVE_EXPIRE_DAYS)
        self.reserve_repo.insert(
            Reservation(request.book_id, request.user_id, now, expire_time, status),
            conn,
        )
        self.book_repo.set_reserved(request.book_id, request.user_id, conn)

    def _confirm_renew(self, conn, request, book):
        loan = self.borrow_repo.get_active(request.user_id, request.book_id, conn)
        if loan is None:
            raise ApprovalError("User doesn't have the book !")
        extra_days = request.extra_days
        if extra_days > MAX_EXTENSION_DAYS:
            raise ApprovalError("User passed the limit of maximum extension days !")
        actual_add = extra_days - (loan.extension_days or 0)
        if actual_add <= 0:
            raise ApprovalError("User already used the extension week !")
        due = add_time(loan.return_time, actual_add) if loan.return_time else None
        self.book_repo.update_state(
            request.book_id,
            BookState.Borrowed,
            book.borrowed_time,
            due,
            _Ref(request.user_id),
            conn=conn,
        )
        self.borrow_repo.update_due(request.user_id, request.book_id, due, extra_days, conn)

    def _confirm_return(self, conn, request, book, now):
        loan = self.borrow_repo.get_active(request.user_id, request.book_id, conn)
        if loan is None:
            raise ApprovalError("User doesn't have the book !")
        delay = find_delay(loan.return_time, now)
        bill = find_bill(delay)
        reserved_id = getattr(book, "reserved_user_id", None)
        self.book_repo.update_state(
            request.book_id, BookState.Available, None, None, None, conn=conn
        )
        self.book_repo.set_reserved(request.book_id, reserved_id, conn)
        self.borrow_repo.mark_returned(request.user_id, request.book_id, now, conn)
        next_user = self.reserve_repo.activate_next(request.book_id, now, conn)
        if next_user is None and not reserved_id:
            self.book_repo.set_reserved(request.book_id, None, conn)
        return bill
