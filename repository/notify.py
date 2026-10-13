from datetime import datetime as Datetime

from repository.connection import fmt_dt, get_connection, parse_dt


def _has_notify(cur, user_id, book_id, notify_type):
    row = cur.execute(
        """SELECT notify_id FROM message_notify
           WHERE user_id=? AND IFNULL(book_id,0)=IFNULL(?,0) AND notify_type=? AND is_read=0""",
        [user_id, book_id, notify_type],
    ).fetchone()
    return row is not None


def refresh_notifications(conn=None, db_path=None):
    close_after = False
    if conn is None:
        conn = get_connection(db_path)
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
