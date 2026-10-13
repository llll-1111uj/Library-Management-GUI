"""Deprecated book/loan persistence helpers.

Use repository.connection for SQLite access and repository.user_repository for users.
This module is kept so GUIManager book/loan calls still work until A2/A3.
"""
# REFACTOR-TRANSITION: Database.py is a compatibility facade; expect DeprecationWarning.
import warnings
from datetime import datetime as Datetime, timedelta

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
    """用借阅记录、预约表恢复内存中的已借/预约状态。"""
    conn = get_connection()
    cur = conn.cursor()
    users_by_id = {}
    for role in ("costumer", "officer"):
        for person in users_map.get(role, []):
            if getattr(person, "user_id", None):
                users_by_id[person.user_id] = person

    for user_id, book_id, borrow_time, due_time, borrow_status in cur.execute(
        """SELECT user_id, book_id, borrow_time, due_time, borrow_status
           FROM borrow_record WHERE borrow_status IN ('borrowed', 'overdue')"""
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
            "extension": 0,
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


def persist_borrow(user, book, borrow_time, due_time):
    """借阅成功：同步 Books 日期/状态，写入 borrow_record。"""
    conn = get_connection()
    upsert_user(conn, user)
    upsert_book(conn, book)
    cur = conn.cursor()
    cur.execute(
        """UPDATE Books SET state=?, borrowed_time=?, return_time=?, borrowed_user_id=?
           WHERE book_id=?""",
        ["Borrowed", fmt_dt(borrow_time), fmt_dt(due_time), user.user_id, book.book_id],
    )
    cur.execute(
        """INSERT INTO borrow_record(user_id, book_id, borrow_time, due_time, return_time, borrow_status)
           VALUES(?,?,?,?,?,?)""",
        [user.user_id, book.book_id, fmt_dt(borrow_time), fmt_dt(due_time), None, "borrowed"],
    )
    cur.execute(
        """UPDATE reserve SET reserve_status='fulfilled'
           WHERE user_id=? AND book_id=? AND reserve_status IN ('waiting', 'active')""",
        [user.user_id, book.book_id],
    )
    conn.commit()
    refresh_notifications(conn)
    conn.commit()
    conn.close()


def persist_return(user, book, return_time):
    """归还成功：Books 恢复可借并清空日期，更新 borrow_record。"""
    conn = get_connection()
    upsert_user(conn, user)
    upsert_book(conn, book)
    cur = conn.cursor()
    reserved_user_id = getattr(getattr(book, "reserved", None), "user_id", None)
    cur.execute(
        """UPDATE Books SET state=?, borrowed_time=NULL, return_time=NULL,
           borrowed_user_id=NULL, reserved_user_id=?
           WHERE book_id=?""",
        ["Available", reserved_user_id, book.book_id],
    )
    cur.execute(
        """UPDATE borrow_record SET return_time=?, borrow_status='returned'
           WHERE user_id=? AND book_id=? AND borrow_status IN ('borrowed', 'overdue')""",
        [fmt_dt(return_time), user.user_id, book.book_id],
    )
    next_row = cur.execute(
        """SELECT reserve_id, user_id FROM reserve
           WHERE book_id=? AND reserve_status='waiting'
           ORDER BY reserve_time ASC LIMIT 1""",
        (book.book_id,),
    ).fetchone()
    if next_row:
        expire_time = return_time + timedelta(days=RESERVE_EXPIRE_DAYS) if return_time else Datetime.now() + timedelta(
            days=RESERVE_EXPIRE_DAYS)
        cur.execute(
            """UPDATE reserve SET reserve_status='active', expire_time=? WHERE reserve_id=?""",
            [fmt_dt(expire_time), next_row[0]],
        )
        cur.execute(
            "UPDATE Books SET reserved_user_id=? WHERE book_id=?",
            [next_row[1], book.book_id],
        )
    conn.commit()
    refresh_notifications(conn)
    conn.commit()
    conn.close()


def persist_reserve(user, book, reserve_time):
    """预约成功：写入 reserve，同步 Books.reserved_user_id。"""
    conn = get_connection()
    upsert_user(conn, user)
    upsert_book(conn, book)
    cur = conn.cursor()
    status = "waiting"
    expire_time = None
    if getattr(book.state, "value", str(book.state)) == "Available":
        status = "active"
        expire_time = reserve_time + timedelta(days=RESERVE_EXPIRE_DAYS)
    cur.execute(
        """INSERT INTO reserve(user_id, book_id, reserve_time, reserve_status, expire_time)
           VALUES(?,?,?,?,?)""",
        [user.user_id, book.book_id, fmt_dt(reserve_time), status, fmt_dt(expire_time)],
    )
    cur.execute(
        "UPDATE Books SET reserved_user_id=? WHERE book_id=?",
        [user.user_id, book.book_id],
    )
    conn.commit()
    refresh_notifications(conn)
    conn.commit()
    conn.close()


def persist_extension(user, book, due_time):
    """续借：同步 Books.return_time 与 borrow_record.due_time。"""
    conn = get_connection()
    upsert_user(conn, user)
    upsert_book(conn, book)
    cur = conn.cursor()
    cur.execute(
        "UPDATE Books SET return_time=? WHERE book_id=?",
        [fmt_dt(due_time), book.book_id],
    )
    cur.execute(
        """UPDATE borrow_record SET due_time=?, borrow_status='borrowed'
           WHERE user_id=? AND book_id=? AND borrow_status IN ('borrowed', 'overdue')""",
        [fmt_dt(due_time), user.user_id, book.book_id],
    )
    conn.commit()
    conn.close()


def _has_notify(cur, user_id, book_id, notify_type):
    row = cur.execute(
        """SELECT notify_id FROM message_notify
           WHERE user_id=? AND IFNULL(book_id,0)=IFNULL(?,0) AND notify_type=? AND is_read=0""",
        [user_id, book_id, notify_type],
    ).fetchone()
    return row is not None


def refresh_notifications(conn=None):
    """扫描逾期借阅与到期预约，写入 message_notify（带生成时间）。"""
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True
    cur = conn.cursor()
    now = Datetime.now()
    now_s = fmt_dt(now)

    for record_id, user_id, book_id, due_time in cur.execute(
        """SELECT record_id, user_id, book_id, due_time FROM borrow_record
           WHERE borrow_status IN ('borrowed', 'overdue')"""
    ).fetchall():
        due = parse_dt(due_time)
        if due and due < now:
            cur.execute(
                "UPDATE borrow_record SET borrow_status='overdue' WHERE record_id=?",
                (record_id,),
            )
            if not _has_notify(cur, user_id, book_id, "overdue"):
                cur.execute(
                    """INSERT INTO message_notify(user_id, book_id, content, notify_type, create_time, is_read)
                       VALUES(?,?,?,?,?,0)""",
                    [
                        user_id,
                        book_id,
                        "借书逾期提醒：您借阅的图书已超过应还日期，请尽快归还。",
                        "overdue",
                        now_s,
                    ],
                )

    for reserve_id, user_id, book_id, expire_time in cur.execute(
        """SELECT reserve_id, user_id, book_id, expire_time FROM reserve
           WHERE reserve_status IN ('waiting', 'active') AND expire_time IS NOT NULL"""
    ).fetchall():
        expire = parse_dt(expire_time)
        if expire and expire < now:
            cur.execute(
                "UPDATE reserve SET reserve_status='expired' WHERE reserve_id=?",
                (reserve_id,),
            )
            cur.execute(
                """UPDATE Books SET reserved_user_id=NULL
                   WHERE book_id=? AND reserved_user_id=?""",
                [book_id, user_id],
            )
            if not _has_notify(cur, user_id, book_id, "reserve_expire"):
                cur.execute(
                    """INSERT INTO message_notify(user_id, book_id, content, notify_type, create_time, is_read)
                       VALUES(?,?,?,?,?,0)""",
                    [
                        user_id,
                        book_id,
                        "预约排队到期提醒：您的图书预约排队已到期，预约已失效。",
                        "reserve_expire",
                        now_s,
                    ],
                )
    conn.commit()
    if close_after:
        conn.close()
