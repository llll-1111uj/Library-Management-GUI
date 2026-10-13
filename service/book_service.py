"""Book listing and combo-box filter (Available / Borrowed / Reserved)."""
import logging
import math

from repository.book_repository import BookRepository
from repository.user_repository import UserRepository

logger = logging.getLogger(__name__)

FILTER_AVAILABLE = "Available"
FILTER_BORROWED = "Borrowed"
FILTER_RESERVED = "Reserved"
PAGE_SIZES = (20, 50)


def action_visibility(filter_state):
    """Borrow/reserve button visibility from GUI.fill_table combo index."""
    if filter_state == FILTER_BORROWED:
        return {"reserve": True, "borrow": False}
    if filter_state == FILTER_RESERVED:
        return {"reserve": False, "borrow": False}
    return {"reserve": True, "borrow": True}


class BookService:
    def __init__(self, book_repo=None, user_repo=None):
        self.book_repo = book_repo or BookRepository()
        self.user_repo = user_repo or UserRepository()

    def _users_by_id(self, users_by_id=None):
        if users_by_id is not None:
            return users_by_id
        _users, by_id = self.user_repo.list_all()
        return by_id

    def list_books(self, filter_state=None, users_by_id=None):
        users_by_id = self._users_by_id(users_by_id)
        try:
            if not filter_state:
                books, _by_id = self.book_repo.list_all(users_by_id)
                return books
            return self.book_repo.list_by_state(filter_state, users_by_id)
        except Exception:
            logger.exception("list_books failed filter_state=%s", filter_state)
            raise

    def get(self, book_id, users_by_id=None):
        users_by_id = self._users_by_id(users_by_id)
        return self.book_repo.get_by_id(book_id, users_by_id)

    def search_books(self, keyword=None, filter_state=None, sort_by="name", sort_dir="ASC",
                     page=1, page_size=20, users_by_id=None):
        users_by_id = self._users_by_id(users_by_id)
        try:
            page_size = int(page_size)
        except (TypeError, ValueError):
            page_size = 20
        if page_size not in PAGE_SIZES:
            page_size = 20
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1
        try:
            total = self.book_repo.count_matching(keyword=keyword, state=filter_state)
        except Exception:
            logger.exception("search_books count failed filter_state=%s", filter_state)
            raise
        total = int(total or 0)
        total_pages = max(1, int(math.ceil(total / float(page_size)))) if total else 1
        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size
        try:
            books, total = self.book_repo.search(
                users_by_id,
                keyword=keyword,
                state=filter_state,
                sort_by=sort_by,
                sort_dir=sort_dir,
                limit=page_size,
                offset=offset,
            )
        except Exception:
            logger.exception("search_books failed filter_state=%s", filter_state)
            raise
        return {
            "books": books,
            "total": int(total or 0),
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "sort_by": sort_by,
            "sort_dir": sort_dir,
        }
