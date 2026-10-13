"""SQLite connection and schema. Canonical DB path: Database/Database.db."""
import logging
import os
import sys
from datetime import datetime as Datetime
from sqlite3 import connect, Connection

from domain.password import hash_password, is_hashed

logger = logging.getLogger(__name__)

if getattr(sys, "frozen", False):
    _ROOT_DIR = os.path.dirname(sys.executable)
else:
    _ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_ROOT_DIR, "Database", "Database.db")

DT_FMT = "%Y-%m-%d %H:%M:%S"
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


def get_connection(db_path=None) -> Connection:
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = connect(path)
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


SQL_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 用户主键
    first_name TEXT NOT NULL,                  -- 名
    last_name TEXT NOT NULL,                   -- 姓
    username TEXT NOT NULL UNIQUE,             -- 登录用户名
    password TEXT NOT NULL,                    -- bcrypt 哈希，不存明文
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
    extension_days INTEGER NOT NULL DEFAULT 0,   -- 累计续期天数（目标由 requests.extra_days 表示）
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (book_id) REFERENCES Books(book_id)
)
"""

SQL_CREATE_REQUESTS = """
CREATE TABLE IF NOT EXISTS requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    request_type TEXT NOT NULL
        CHECK(request_type IN ('BORROW', 'RESERVE', 'RENEW', 'RETURN')),
    status TEXT NOT NULL
        CHECK(status IN ('PENDING', 'ACCEPTED', 'DENIED', 'CANCELLED')),
    extra_days INTEGER NOT NULL DEFAULT 0, -- RENEW：目标累计续期天数
    created_at TEXT NOT NULL,
    handled_by INTEGER,
    handled_at TEXT,
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (book_id) REFERENCES Books(book_id),
    FOREIGN KEY (handled_by) REFERENCES Users(user_id)
)
"""

SQL_CREATE_AUDIT_LOG = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    detail TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
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
        password = data.get("password") or ""
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
    """Startup fallback: upgrade leftover plaintext Users.password to bcrypt.
    Skip rows that are neither bcrypt nor a known plaintext (no MD5).
    One-row failure is logged and does not abort startup.
    """
    rows = cur.execute("SELECT user_id, username, password FROM Users").fetchall()
    for user_id, username, password in rows:
        try:
            if not password or is_hashed(password):
                continue
            hashed = hash_password(password)
            if not hashed:
                continue
            cur.execute("UPDATE Users SET password=? WHERE user_id=?", (hashed, user_id))
            logger.info("upgraded plaintext password for username=%s", username)
        except Exception:
            logger.exception("password upgrade failed user_id=%s username=%s", user_id, username)


def _ensure_column(cur, table, column, ddl_type):
    if not _table_exists(cur, table):
        return
    if column in _columns(cur, table):
        return
    cur.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, column, ddl_type))


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


def init_database(db_path=None):
    """Create/migrate all tables. Startup password normalize lives here."""
    try:
        conn = get_connection(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = OFF")
        _migrate_users(cur)
        _migrate_books(cur)
        cur.execute(SQL_CREATE_RESERVE)
        cur.execute(SQL_CREATE_BORROW_RECORD)
        cur.execute(SQL_CREATE_MESSAGE_NOTIFY)
        cur.execute(SQL_CREATE_REQUESTS)
        cur.execute(SQL_CREATE_AUDIT_LOG)
        _ensure_column(cur, "borrow_record", "extension_days", "INTEGER NOT NULL DEFAULT 0")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_books_name_author ON Books(name, author)")
        _normalize_passwords(cur)
        conn.commit()
        cur.execute("PRAGMA foreign_keys = ON")
        logger.info("database schema ready path=%s", db_path or DB_PATH)
        return conn
    except Exception:
        logger.exception("init_database failed")
        raise
