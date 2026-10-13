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

    def list_by_state(self, state, users_by_id):
        # "Reserved" is a combo filter, not Books.state (see Book.is_reserved).
        label = state.value if hasattr(state, "value") else str(state or "")
        try:
            conn = self._conn()
            if label == "Borrowed":
                rows = conn.execute(
                    _BOOK_SELECT + " WHERE state=?",
                    (BookState.Borrowed.value,),
                ).fetchall()
            elif label == "Reserved":
                rows = conn.execute(
                    _BOOK_SELECT + " WHERE reserved_user_id IS NOT NULL",
                ).fetchall()
            else:
                rows = conn.execute(
                    _BOOK_SELECT + " WHERE state=? AND reserved_user_id IS NULL",
                    (BookState.Available.value,),
                ).fetchall()
            conn.close()
        except Exception:
            logger.exception("list_by_state failed state=%s", label)
            raise
        return [_to_book(row, users_by_id) for row in rows]

    def get_by_id(self, book_id, users_by_id):
        try:
            conn = self._conn()
            row = conn.execute(_BOOK_SELECT + " WHERE book_id=?", (book_id,)).fetchone()
            conn.close()
        except Exception:
            logger.exception("get_by_id failed book_id=%s", book_id)
            raise
        if not row:
            return None
        return _to_book(row, users_by_id)

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
