"""Books table access. DB path remains Database/Database.db."""
import logging

from domain.book import Book, BookState
from Person import Person
from repository.connection import fmt_dt, get_connection, parse_dt

logger = logging.getLogger(__name__)

_BOOK_SELECT = """
SELECT book_id, name, author, state, borrowed_time, return_time,
       borrowed_user_id, reserved_user_id FROM Books
"""

_SORT_COLUMNS = {
    "name": "name COLLATE NOCASE",
    "author": "author COLLATE NOCASE",
    "state": "state",
    "book_id": "book_id",
    "reserved_user_id": "reserved_user_id",
    "borrowed_user_id": "borrowed_user_id",
    "borrowed_time": "borrowed_time",
    "return_time": "return_time",
}


def _persist_state(state):
    if hasattr(state, "value"):
        state = state.value
    state = str(state or "Available")
    if state == "Reserved":
        return None
    if state == BookState.Borrowed.value:
        return BookState.Borrowed.value
    return BookState.Available.value


def _to_book(row, users_by_id):
    (book_id, name, author, state, borrowed_time, return_time,
     borrowed_user_id, reserved_user_id) = row
    users_by_id = users_by_id or {}
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
    book.borrowed_user_id = borrowed_user_id
    book.reserved_user_id = reserved_user_id
    return book


class BookRepository:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def _conn(self):
        return get_connection(self.db_path)

    def list_all(self, users_by_id):
        # REFACTOR-TRANSITION: users_by_id hydrates borrowed/reserved Person here.
        # After A3, repository returns raw Book rows; BookService assembles Person.
        try:
            conn = self._conn()
            rows = conn.execute(_BOOK_SELECT).fetchall()
            conn.close()
        except Exception:
            logger.exception("list_all books failed")
            raise
        books = []
        by_id = {}
        for row in rows:
            book = _to_book(row, users_by_id)
            books.append(book)
            by_id[book.book_id] = book
        logger.info("loaded %s books", len(books))
        return books, by_id

    def _filter_sql(self, state, keyword):
        label = state.value if hasattr(state, "value") else str(state or "")
        clauses = []
        params = []
        if label == "Borrowed":
            clauses.append("state=?")
            params.append(BookState.Borrowed.value)
        elif label == "Reserved":
            clauses.append("reserved_user_id IS NOT NULL")
        elif label == "Available":
            clauses.append("state=? AND reserved_user_id IS NULL")
            params.append(BookState.Available.value)
        text = (keyword or "").strip()
        if text:
            clauses.append("(name LIKE ? OR author LIKE ?)")
            like = "%" + text + "%"
            params.extend([like, like])
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        return where, params, label

    def list_by_state(self, state, users_by_id):
        # "Reserved" is a combo filter, not Books.state (see Book.is_reserved).
        where, params, label = self._filter_sql(state, None)
        try:
            conn = self._conn()
            rows = conn.execute(_BOOK_SELECT + where, params).fetchall()
            conn.close()
        except Exception:
            logger.exception("list_by_state failed state=%s", label)
            raise
        return [_to_book(row, users_by_id) for row in rows]

    def count_matching(self, keyword=None, state=None):
        where, params, label = self._filter_sql(state, keyword)
        try:
            conn = self._conn()
            total = conn.execute("SELECT COUNT(*) FROM Books" + where, params).fetchone()[0]
            conn.close()
        except Exception:
            logger.exception("count books failed state=%s keyword=%s", label, keyword)
            raise
        return int(total or 0)

    def search(self, users_by_id, keyword=None, state=None, sort_by="name", sort_dir="ASC",
               limit=20, offset=0):
        where, params, label = self._filter_sql(state, keyword)
        order_expr = _SORT_COLUMNS.get(sort_by) or _SORT_COLUMNS["name"]
        direction = "DESC" if str(sort_dir).upper() == "DESC" else "ASC"
        limit = max(0, int(limit or 0))
        offset = max(0, int(offset or 0))
        try:
            conn = self._conn()
            total = conn.execute("SELECT COUNT(*) FROM Books" + where, params).fetchone()[0]
            rows = conn.execute(
                _BOOK_SELECT + where + " ORDER BY %s %s, book_id ASC LIMIT ? OFFSET ?" % (
                    order_expr, direction,
                ),
                list(params) + [limit, offset],
            ).fetchall()
            conn.close()
        except Exception:
            logger.exception("search books failed state=%s keyword=%s", label, keyword)
            raise
        logger.debug("search books state=%s total=%s page_offset=%s", label, total, offset)
        return [_to_book(row, users_by_id) for row in rows], int(total or 0)

    def get_by_id(self, book_id, users_by_id, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        try:
            row = conn.execute(_BOOK_SELECT + " WHERE book_id=?", (book_id,)).fetchone()
        except Exception:
            logger.exception("get_by_id failed book_id=%s", book_id)
            raise
        finally:
            if close_after:
                conn.close()
        if not row:
            return None
        return _to_book(row, users_by_id)

    def set_reserved(self, book_id, reserved_user_id, conn):
        conn.execute(
            "UPDATE Books SET reserved_user_id=? WHERE book_id=?",
            [reserved_user_id, book_id],
        )

    def upsert(self, book, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        cur = conn.cursor()
        book_id = getattr(book, "book_id", None)
        borrowed_user_id = getattr(getattr(book, "borrowed", None), "user_id", None)
        reserved_user_id = getattr(getattr(book, "reserved", None), "user_id", None)
        state = _persist_state(getattr(book, "state", None)) or BookState.Available.value
        values = [
            book.name,
            book.author,
            state,
            fmt_dt(book.borrowed_time) if getattr(book, "borrowed_time", None) else None,
            fmt_dt(book.return_time) if getattr(book, "return_time", None) else None,
            borrowed_user_id,
            reserved_user_id,
        ]
        try:
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
            if close_after:
                conn.commit()
        except Exception:
            if close_after:
                conn.rollback()
            logger.exception("upsert book failed name=%s", getattr(book, "name", None))
            raise
        finally:
            if close_after:
                conn.close()
        return book.book_id

    def update_state(self, book_id, state, borrowed_time=None, return_time=None, borrower=None, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        label = state.value if hasattr(state, "value") else str(state or "Available")
        borrower_id = getattr(borrower, "user_id", None)
        cur = conn.cursor()
        try:
            if label == "Reserved":
                cur.execute(
                    "UPDATE Books SET reserved_user_id=? WHERE book_id=?",
                    (borrower_id, book_id),
                )
            else:
                db_state = _persist_state(label)
                cur.execute(
                    """UPDATE Books SET state=?, borrowed_time=?, return_time=?, borrowed_user_id=?
                       WHERE book_id=?""",
                    [db_state, fmt_dt(borrowed_time), fmt_dt(return_time), borrower_id, book_id],
                )
            if close_after:
                conn.commit()
        except Exception:
            if close_after:
                conn.rollback()
            logger.exception("update_state failed book_id=%s", book_id)
            raise
        finally:
            if close_after:
                conn.close()
