"""reserve.reserve_status: waiting/active/expired/cancelled/fulfilled."""
from datetime import datetime as Datetime, timedelta

from domain.reservation import Reservation
from repository.connection import RESERVE_EXPIRE_DAYS, fmt_dt, get_connection, parse_dt


class ReserveRepository:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def _conn(self):
        return get_connection(self.db_path)

    def insert(self, reservation, conn):
        conn.execute(
            """INSERT INTO reserve(user_id, book_id, reserve_time, reserve_status, expire_time)
               VALUES(?,?,?,?,?)""",
            [
                reservation.user_id,
                reservation.book_id,
                fmt_dt(reservation.reserved_time),
                reservation.status,
                fmt_dt(reservation.expire_time),
            ],
        )

    def count_active(self, user_id, conn):
        row = conn.execute(
            """SELECT COUNT(*) FROM reserve
               WHERE user_id=? AND reserve_status IN ('waiting', 'active')""",
            (user_id,),
        ).fetchone()
        return row[0] if row else 0

    def fulfill(self, user_id, book_id, conn):
        conn.execute(
            """UPDATE reserve SET reserve_status='fulfilled'
               WHERE user_id=? AND book_id=? AND reserve_status IN ('waiting', 'active')""",
            [user_id, book_id],
        )

    def activate_next(self, book_id, now, conn):
        next_row = conn.execute(
            """SELECT reserve_id, user_id FROM reserve
               WHERE book_id=? AND reserve_status='waiting'
               ORDER BY reserve_time ASC LIMIT 1""",
            (book_id,),
        ).fetchone()
        if not next_row:
            return None
        expire_time = (now or Datetime.now()) + timedelta(days=RESERVE_EXPIRE_DAYS)
        conn.execute(
            """UPDATE reserve SET reserve_status='active', expire_time=? WHERE reserve_id=?""",
            [fmt_dt(expire_time), next_row[0]],
        )
        conn.execute(
            "UPDATE Books SET reserved_user_id=? WHERE book_id=?",
            [next_row[1], book_id],
        )
        return next_row[1]
