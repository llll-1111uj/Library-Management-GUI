"""borrow_record: due_time=应还, return_time=实还."""
import logging

from domain.loan import Loan
from repository.connection import fmt_dt, get_connection, parse_dt

logger = logging.getLogger(__name__)

_SELECT = """
SELECT record_id, user_id, book_id, borrow_time, due_time, return_time,
       borrow_status, IFNULL(extension_days, 0) FROM borrow_record
"""


def _row(row):
    (record_id, user_id, book_id, borrow_time, due_time, return_time,
     borrow_status, extension_days) = row
    return Loan(
        book_id=book_id,
        user_id=user_id,
        borrowed_time=parse_dt(borrow_time),
        return_time=parse_dt(due_time),
        actual_return_time=parse_dt(return_time),
        extension_days=extension_days or 0,
        status=borrow_status,
        record_id=record_id,
    )


class BorrowRepository:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def _conn(self):
        return get_connection(self.db_path)

    def insert_borrow(self, user_id, book_id, borrow_time, due_time, conn):
        conn.execute(
            """INSERT INTO borrow_record(user_id, book_id, borrow_time, due_time, return_time,
               borrow_status, extension_days) VALUES(?,?,?,?,?,?,?)""",
            [user_id, book_id, fmt_dt(borrow_time), fmt_dt(due_time), None, "borrowed", 0],
        )

    def list_active_by_user(self, user_id, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        rows = conn.execute(
            _SELECT + " WHERE user_id=? AND borrow_status IN ('borrowed', 'overdue') ORDER BY record_id",
            (user_id,),
        ).fetchall()
        if close_after:
            conn.close()
        return [_row(r) for r in rows]

    def list_by_user(self, user_id, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        rows = conn.execute(
            _SELECT + " WHERE user_id=? ORDER BY record_id",
            (user_id,),
        ).fetchall()
        if close_after:
            conn.close()
        return [_row(r) for r in rows]

    def count_active(self, user_id, conn):
        row = conn.execute(
            """SELECT COUNT(*) FROM borrow_record
               WHERE user_id=? AND borrow_status IN ('borrowed', 'overdue')""",
            (user_id,),
        ).fetchone()
        return row[0] if row else 0

    def get_active(self, user_id, book_id, conn):
        row = conn.execute(
            _SELECT + " WHERE user_id=? AND book_id=? AND borrow_status IN ('borrowed', 'overdue') ORDER BY record_id DESC LIMIT 1",
            (user_id, book_id),
        ).fetchone()
        return _row(row) if row else None

    def mark_returned(self, user_id, book_id, actual_return_time, conn):
        conn.execute(
            """UPDATE borrow_record SET return_time=?, borrow_status='returned'
               WHERE user_id=? AND book_id=? AND borrow_status IN ('borrowed', 'overdue')""",
            [fmt_dt(actual_return_time), user_id, book_id],
        )

    def update_due(self, user_id, book_id, due_time, extension_days, conn):
        conn.execute(
            """UPDATE borrow_record SET due_time=?, borrow_status='borrowed', extension_days=?
               WHERE user_id=? AND book_id=? AND borrow_status IN ('borrowed', 'overdue')""",
            [fmt_dt(due_time), extension_days, user_id, book_id],
        )


def restore_user_book_state(users_map, books_by_id, db_path=None):
    conn = get_connection(db_path)
    cur = conn.cursor()
    users_by_id = {}
    for role in ("costumer", "officer"):
        for person in users_map.get(role, []):
            if getattr(person, "user_id", None):
                users_by_id[person.user_id] = person

    has_ext = "extension_days" in [r[1] for r in cur.execute("PRAGMA table_info(borrow_record)")]
    ext_sql = ", IFNULL(extension_days,0)" if has_ext else ", 0"
    for user_id, book_id, borrow_time, due_time, extension_days in cur.execute(
        """SELECT user_id, book_id, borrow_time, due_time%s
           FROM borrow_record WHERE borrow_status IN ('borrowed', 'overdue')""" % ext_sql
    ):
        user = users_by_id.get(user_id)
        book = books_by_id.get(book_id)
        if not user or not book or not hasattr(user, "borrowed_books"):
            continue
        b_time = parse_dt(borrow_time)
        d_time = parse_dt(due_time)
        user.borrowed_books[book] = {
            "borrowed_time": b_time,
            "return_time": d_time,
            "extension": extension_days or 0,
        }

    for user_id, book_id in cur.execute(
        """SELECT user_id, book_id FROM reserve
           WHERE reserve_status IN ('waiting', 'active')"""
    ):
        user = users_by_id.get(user_id)
        book = books_by_id.get(book_id)
        if not user or not book or not hasattr(user, "reserve"):
            continue
        if book not in user.reserve:
            user.reserve.append(book)
    conn.close()
