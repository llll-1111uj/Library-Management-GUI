"""
SQLite 初始化与业务同步。
启动时自动建表（含主键、外键），借阅/归还/预约发生时实时更新 Books 与业务表。
密码以明文存取，不做哈希。
"""
import os
from datetime import datetime as Datetime, timedelta
from sqlite3 import connect, Connection

_CODE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_CODE_DIR)
DB_PATH = os.path.join(_ROOT_DIR, "Database", "Database.db")

DT_FMT = "%Y-%m-%d %H:%M:%S"

# 预约排队保留时长（到期后写入预约到期通知）
RESERVE_EXPIRE_DAYS = 3


def fmt_dt(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.strftime(DT_FMT)


def parse_dt(value):
    if not value:
        return None
    if isinstance(value, Datetime):
        return value
    for fmt in (DT_FMT, "%Y/%m/%d", "%Y-%m-%d"):
        try:
            return Datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def get_connection() -> Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_exists(cur, name: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _columns(cur, name: str):
    return [r[1] for r in cur.execute("PRAGMA table_info(%s)" % name)]


_KNOWN_MD5 = {
    "81dc9bdb52d04dc20036dbd8313ed055": "1234",  # 历史 md5("1234")
}


def _plain_password(username: str, password: str) -> str:
    """历史数据若仍是 32 位 MD5，默认账号或已知哈希还原为明文。"""
    if not password:
        return ""
    lowered = password.lower()
    if lowered in _KNOWN_MD5:
        return _KNOWN_MD5[lowered]
    if len(password) == 32 and all(c in "0123456789abcdef" for c in lowered):
        if username == "azarhajipour":
            return "1234"
        if username == "mahdihajipour":
            return "4321"
    return password


# ---------- 建表 SQL（每张表字段均有中文注释） ----------

SQL_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 用户主键
    first_name TEXT NOT NULL,                  -- 名
    last_name TEXT NOT NULL,                   -- 姓
    username TEXT NOT NULL UNIQUE,             -- 登录用户名
    password TEXT NOT NULL,                    -- 明文密码（不做哈希）
    email TEXT,                                -- 邮箱
    phone TEXT,                                -- 电话
    role TEXT NOT NULL CHECK(role IN ('costumer', 'officer')) -- 角色：读者/管理员
)
"""

SQL_CREATE_BOOKS = """
CREATE TABLE IF NOT EXISTS Books (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 图书主键
    name TEXT NOT NULL,                        -- 书名
    author TEXT NOT NULL,                      -- 作者
    state TEXT NOT NULL DEFAULT 'Available',   -- 图书状态：Available / Borrowed
    borrowed_time TEXT,                        -- 当前借出时间
    return_time TEXT,                          -- 当前应还时间
    borrowed_user_id INTEGER,                  -- 当前借阅人，关联 Users.user_id
    reserved_user_id INTEGER,                  -- 当前预约人，关联 Users.user_id
    FOREIGN KEY (borrowed_user_id) REFERENCES Users(user_id),
    FOREIGN KEY (reserved_user_id) REFERENCES Users(user_id)
)
"""

SQL_CREATE_RESERVE = """
CREATE TABLE IF NOT EXISTS reserve (
    reserve_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 预约主键
    user_id INTEGER NOT NULL,                     -- 预约用户，关联 Users.user_id
    book_id INTEGER NOT NULL,                     -- 预约图书，关联 Books.book_id
    reserve_time TEXT NOT NULL,                   -- 预约时间
    reserve_status TEXT NOT NULL,                 -- 预约状态：waiting/active/expired/cancelled/fulfilled
    expire_time TEXT,                             -- 预约排队到期时间
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (book_id) REFERENCES Books(book_id)
)
"""

SQL_CREATE_BORROW_RECORD = """
CREATE TABLE IF NOT EXISTS borrow_record (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 借阅记录主键
    user_id INTEGER NOT NULL,                    -- 借阅用户，关联 Users.user_id
    book_id INTEGER NOT NULL,                    -- 借阅图书，关联 Books.book_id
    borrow_time TEXT NOT NULL,                   -- 借出时间
    due_time TEXT,                               -- 应还时间（用于逾期判断）
    return_time TEXT,                            -- 实际归还时间，未还则为空
    borrow_status TEXT NOT NULL,                 -- 借阅状态：borrowed/returned/overdue
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (book_id) REFERENCES Books(book_id)
)
"""

SQL_CREATE_MESSAGE_NOTIFY = """
CREATE TABLE IF NOT EXISTS message_notify (
    notify_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 消息主键
    user_id INTEGER NOT NULL,                    -- 接收用户，关联 Users.user_id
    book_id INTEGER,                             -- 相关图书，关联 Books.book_id
    content TEXT NOT NULL,                       -- 消息内容
    notify_type TEXT NOT NULL,                   -- overdue=借书逾期；reserve_expire=预约排队到期
    create_time TEXT NOT NULL,                   -- 消息生成时间
    is_read INTEGER NOT NULL DEFAULT 0,          -- 是否已读：0未读 1已读
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (book_id) REFERENCES Books(book_id)
)
"""


def _migrate_users(cur):
    if not _table_exists(cur, "Users"):
        cur.execute(SQL_CREATE_USERS)
        return
    cols = _columns(cur, "Users")
    if "user_id" in cols:
        return
    cur.execute("ALTER TABLE Users RENAME TO Users_legacy")
    cur.execute(SQL_CREATE_USERS)
    id_col = "id" if "id" in _columns(cur, "Users_legacy") else None
    rows = cur.execute("SELECT * FROM Users_legacy").fetchall()
    names = _columns(cur, "Users_legacy")
    for row in rows:
        data = dict(zip(names, row))
        username = data.get("username")
        password = _plain_password(username, data.get("password"))
        cur.execute(
            """INSERT INTO Users(user_id, first_name, last_name, username, password, email, phone, role)
               VALUES(?,?,?,?,?,?,?,?)""",
            [
                data.get("id") if id_col else None,
                data.get("first_name"),
                data.get("last_name"),
                username,
                password,
                data.get("email"),
                data.get("phone"),
                data.get("role") or "costumer",
            ],
        )
    cur.execute("DROP TABLE Users_legacy")


def _normalize_passwords(cur):
    for user_id, username, password in cur.execute("SELECT user_id, username, password FROM Users").fetchall():
        plain = _plain_password(username, password)
        if plain != password:
            cur.execute("UPDATE Users SET password=? WHERE user_id=?", (plain, user_id))


def _migrate_books(cur):
    if not _table_exists(cur, "Books"):
        cur.execute(SQL_CREATE_BOOKS)
        return
    cols = _columns(cur, "Books")
    if "book_id" in cols and "state" in cols and "borrowed_user_id" in cols:
        return
    cur.execute("ALTER TABLE Books RENAME TO Books_legacy")
    cur.execute(SQL_CREATE_BOOKS)
    names = _columns(cur, "Books_legacy")
    seen = set()
    for row in cur.execute("SELECT * FROM Books_legacy").fetchall():
        data = dict(zip(names, row))
        key = (data.get("name"), data.get("author"))
        if key in seen:
            continue
        seen.add(key)
        cur.execute(
            """INSERT INTO Books(name, author, state, borrowed_time, return_time)
               VALUES(?,?,?,?,?)""",
            [
                data.get("name"),
                data.get("author"),
                data.get("state") or "Available",
                data.get("borrowed_time"),
                data.get("return_time"),
            ],
        )
    cur.execute("DROP TABLE Books_legacy")


def init_database():
    """启动时创建/迁移全部数据表。"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF")
    _migrate_users(cur)
    _migrate_books(cur)
    cur.execute(SQL_CREATE_RESERVE)
    cur.execute(SQL_CREATE_BORROW_RECORD)
    cur.execute(SQL_CREATE_MESSAGE_NOTIFY)
    _normalize_passwords(cur)
    conn.commit()
    cur.execute("PRAGMA foreign_keys = ON")
    return conn


def upsert_user(conn, person, role=None):
    if role is None:
        role = "officer" if type(person).__name__ == "Officer" else "costumer"
    cur = conn.cursor()
    user_id = getattr(person, "user_id", None)
    if not user_id:
        row = cur.execute(
            "SELECT user_id FROM Users WHERE username=?",
            (person.username,),
        ).fetchone()
        if row:
            user_id = row[0]
            person.user_id = user_id
    values = [
        person.first_name,
        person.last_name,
        person.username,
        person.password,
        person.email,
        person.phone,
        role,
    ]
    if user_id:
        cur.execute(
            """UPDATE Users SET first_name=?, last_name=?, username=?, password=?,
               email=?, phone=?, role=? WHERE user_id=?""",
            values + [user_id],
        )
    else:
        cur.execute(
            """INSERT INTO Users(first_name, last_name, username, password, email, phone, role)
               VALUES(?,?,?,?,?,?,?)""",
            values,
        )
        person.user_id = cur.lastrowid
    return person.user_id


def upsert_book(conn, book):
    cur = conn.cursor()
    book_id = getattr(book, "book_id", None)
    borrowed_user_id = getattr(getattr(book, "borrowed", None), "user_id", None)
    reserved_user_id = getattr(getattr(book, "reserved", None), "user_id", None)
    state = book.state.value if hasattr(book.state, "value") else str(book.state or "Available")
    values = [
        book.name,
        book.author,
        state,
        fmt_dt(book.borrowed_time) if getattr(book, "borrowed_time", None) else None,
        fmt_dt(book.return_time) if getattr(book, "return_time", None) else None,
        borrowed_user_id,
        reserved_user_id,
    ]
    if not book_id:
        row = cur.execute(
            "SELECT book_id FROM Books WHERE name=? AND author=?",
            (book.name, book.author),
        ).fetchone()
        if row:
            book_id = row[0]
            book.book_id = book_id
    if book_id:
        cur.execute(
            """UPDATE Books SET name=?, author=?, state=?, borrowed_time=?, return_time=?,
               borrowed_user_id=?, reserved_user_id=? WHERE book_id=?""",
            values + [book_id],
        )
    else:
        cur.execute(
            """INSERT INTO Books(name, author, state, borrowed_time, return_time,
               borrowed_user_id, reserved_user_id) VALUES(?,?,?,?,?,?,?)""",
            values,
        )
        book.book_id = cur.lastrowid
    return book.book_id


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
    from Costumer import Costumer
    from Officer import Officer

    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """SELECT user_id, first_name, last_name, username, password, email, phone, role
           FROM Users"""
    ).fetchall()
    conn.close()
    result = {"costumer": [], "officer": []}
    by_id = {}
    for user_id, first_name, last_name, username, password, email, phone, role in rows:
        password = _plain_password(username, password)
        if role == "officer":
            person = Officer(first_name, last_name, username, password, email or "", phone or "")
            result["officer"].append(person)
        else:
            person = Costumer(first_name, last_name, username, password, email or "", phone or "")
            result["costumer"].append(person)
        person.user_id = user_id
        by_id[user_id] = person
    return result, by_id


def load_books(users_by_id):
    from Book import Book
    from Person import Person
    from Tools import BookState

    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """SELECT book_id, name, author, state, borrowed_time, return_time,
                  borrowed_user_id, reserved_user_id FROM Books"""
    ).fetchall()
    conn.close()
    books = []
    by_id = {}
    for (book_id, name, author, state, borrowed_time, return_time,
         borrowed_user_id, reserved_user_id) in rows:
        book_state = BookState.Borrowed if state == BookState.Borrowed.value else BookState.Available
        borrowed = users_by_id.get(borrowed_user_id) if borrowed_user_id else Person()
        reserved = users_by_id.get(reserved_user_id) if reserved_user_id else Person()
        book = Book(
            name,
            author,
            book_state,
            borrowed=borrowed or Person(),
            borrowed_time=parse_dt(borrowed_time),
            return_time=parse_dt(return_time),
            reserved=reserved or Person(),
        )
        book.book_id = book_id
        books.append(book)
        by_id[book_id] = book
    return books, by_id


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
