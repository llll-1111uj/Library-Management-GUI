"""Domain and application errors with GUI-stable messages.

GUIManager has no QMessageBox/Alert; prompts go through set_error (QLabel).
ApprovalError.message must match these strings exactly:

Please select a book from table !
This book is already reserved !
You can borrow this book !
You can't reserve any new book !
You can't borrow any new book !
Sent request to officer !
This request is already handled !
User request accepted !
User already borrowed this book !
User's maximum borrowed books reached !
User's maximum reserved books reached !
User doesn't have the book !
User passed the limit of maximum extension days !
User already used the extension week !
User request accepted ! Issue a receipt
User request accepted ! Issue a bill for {n} $
User request denied !
"""


class AuthError(Exception):
    """Raised when registration or login validation fails."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class RequestAlreadyHandled(Exception):
    def __init__(self, message: str = "This request is already handled !"):
        super().__init__(message)
        self.message = message


class ApprovalError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
