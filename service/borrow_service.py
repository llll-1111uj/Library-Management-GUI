"""Submit PENDING library requests. Does not change Books.state."""
from datetime import datetime as Datetime

from domain.request import Request, RequestStatus, RequestType
from repository.request_repository import RequestRepository


class BorrowService:
    def __init__(self, request_repo=None):
        self.request_repo = request_repo or RequestRepository()

    def _submit(self, user, book, request_type, extra_days=0):
        existing = self.request_repo.find_pending(user.user_id, book.book_id, request_type)
        if existing:
            return existing
        request = Request(
            user_id=user.user_id,
            book_id=book.book_id,
            request_type=request_type,
            status=RequestStatus.PENDING,
            extra_days=extra_days,
            created_at=Datetime.now(),
        )
        self.request_repo.add(request)
        return request

    def submit_borrow(self, user, book):
        return self._submit(user, book, RequestType.BORROW)

    def submit_reserve(self, user, book):
        return self._submit(user, book, RequestType.RESERVE)

    def submit_renew(self, user, book, days):
        return self._submit(user, book, RequestType.RENEW, extra_days=days)

    def submit_return(self, user, book):
        return self._submit(user, book, RequestType.RETURN)
