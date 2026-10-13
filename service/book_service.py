"""Book listing and combo-box filter (Available / Borrowed / Reserved)."""
import logging

from repository.book_repository import BookRepository
from repository.user_repository import UserRepository

logger = logging.getLogger(__name__)

FILTER_AVAILABLE = "Available"
FILTER_BORROWED = "Borrowed"
FILTER_RESERVED = "Reserved"


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
