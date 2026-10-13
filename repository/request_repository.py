"""requests table. No joins — GUI loads names via BookService / UserService."""
import logging

from domain.request import Request, RequestStatus, RequestType
from repository.connection import fmt_dt, get_connection, parse_dt

logger = logging.getLogger(__name__)

_SELECT = """
SELECT request_id, user_id, book_id, request_type, status, extra_days,
       created_at, handled_by, handled_at FROM requests
"""


def _row(row):
    (request_id, user_id, book_id, request_type, status, extra_days,
     created_at, handled_by, handled_at) = row
    return Request(
        user_id=user_id,
        book_id=book_id,
        request_type=request_type,
        status=status,
        extra_days=extra_days,
        created_at=parse_dt(created_at),
        request_id=request_id,
        handled_by=handled_by,
        handled_at=parse_dt(handled_at),
    )


class RequestRepository:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def _conn(self):
        return get_connection(self.db_path)

    def add(self, request, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO requests(user_id, book_id, request_type, status, extra_days,
               created_at, handled_by, handled_at) VALUES(?,?,?,?,?,?,?,?)""",
            [
                request.user_id,
                request.book_id,
                request.request_type.value,
                request.status.value,
                request.extra_days,
                fmt_dt(request.created_at),
                request.handled_by,
                fmt_dt(request.handled_at),
            ],
        )
        request.request_id = cur.lastrowid
        if close_after:
            conn.commit()
            conn.close()
        return request.request_id

    def get(self, request_id, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        row = conn.execute(_SELECT + " WHERE request_id=?", (request_id,)).fetchone()
        if close_after:
            conn.close()
        return _row(row) if row else None

    def find_pending(self, user_id, book_id, request_type, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        rtype = request_type.value if hasattr(request_type, "value") else request_type
        row = conn.execute(
            _SELECT + " WHERE user_id=? AND book_id=? AND request_type=? AND status=? ORDER BY request_id DESC LIMIT 1",
            (user_id, book_id, rtype, RequestStatus.PENDING.value),
        ).fetchone()
        if close_after:
            conn.close()
        return _row(row) if row else None

    def list_by_status(self, status, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        label = status.value if hasattr(status, "value") else status
        rows = conn.execute(_SELECT + " WHERE status=? ORDER BY request_id", (label,)).fetchall()
        if close_after:
            conn.close()
        return [_row(r) for r in rows]

    def list_by_user(self, user_id, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        rows = conn.execute(_SELECT + " WHERE user_id=? ORDER BY request_id", (user_id,)).fetchall()
        if close_after:
            conn.close()
        return [_row(r) for r in rows]

    def list_all(self, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        rows = conn.execute(_SELECT + " ORDER BY request_id").fetchall()
        if close_after:
            conn.close()
        return [_row(r) for r in rows]

    def update_status(self, request_id, status, handled_by, handled_at, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        label = status.value if hasattr(status, "value") else status
        cur = conn.cursor()
        cur.execute(
            """UPDATE requests SET status=?, handled_by=?, handled_at=?
               WHERE request_id=? AND status=?""",
            [label, handled_by, fmt_dt(handled_at), request_id, RequestStatus.PENDING.value],
        )
        count = cur.rowcount
        if close_after:
            conn.commit()
            conn.close()
        return count
