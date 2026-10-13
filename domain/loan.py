class Loan:
    def __init__(
        self,
        book_id,
        user_id,
        borrowed_time,
        return_time,
        actual_return_time=None,
        extension_days=0,
        status="borrowed",
        record_id=None,
    ):
        self.record_id = record_id
        self.book_id = book_id
        self.user_id = user_id
        self.borrowed_time = borrowed_time
        self.return_time = return_time  # due_time in borrow_record
        self.actual_return_time = actual_return_time  # return_time in borrow_record
        self.extension_days = extension_days or 0
        self.status = status
