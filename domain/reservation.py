class Reservation:
    def __init__(
        self,
        book_id,
        user_id,
        reserved_time,
        expire_time=None,
        status="waiting",
        reserve_id=None,
    ):
        self.reserve_id = reserve_id
        self.book_id = book_id
        self.user_id = user_id
        self.reserved_time = reserved_time
        self.expire_time = expire_time
        self.status = status
