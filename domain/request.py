from datetime import datetime as Datetime
from enum import Enum


class RequestType(Enum):
    BORROW = "BORROW"
    RESERVE = "RESERVE"
    RENEW = "RENEW"
    RETURN = "RETURN"


class RequestStatus(Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DENIED = "DENIED"
    CANCELLED = "CANCELLED"


class Request:
    def __init__(
        self,
        user_id,
        book_id,
        request_type,
        status=RequestStatus.PENDING,
        extra_days=0,
        created_at=None,
        request_id=None,
        handled_by=None,
        handled_at=None,
    ):
        self.request_id = request_id
        self.user_id = user_id
        self.book_id = book_id
        self.request_type = request_type if isinstance(request_type, RequestType) else RequestType(request_type)
        self.status = status if isinstance(status, RequestStatus) else RequestStatus(status)
        self.extra_days = extra_days or 0
        self.created_at = created_at or Datetime.now()
        self.handled_by = handled_by
        self.handled_at = handled_at
