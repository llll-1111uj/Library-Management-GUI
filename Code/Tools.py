from sys import path
from enum import Enum
from typing import Union
from datetime import timedelta, datetime as Datetime

from Receipt_Bill import Bill, Receipt
from domain.book import BookState  # REFACTOR-TRANSITION: single BookState enum

class CommandState(Enum):
    """
       Enum class for CommandState.
    """

    SameBorrowReturn = "Borrowing date and returning date are the same !"
    BorrowedBefore = "User's trying to borrow a book which already has been borrowed !"
    Done = "Done !"
    MaximumBorrow = "User passed the limit of maximum borrowing !"
    MaximumReserved = "User passed the limit of maximum reserving !"
    NoMoreExtension = "User already used the extension week !"
    ExtensionLimitReached = "User passed the limit of maximum extension days !"
    Bill = "User have a bill to pay !"


class Tools:
    """
       This is a class for helping other classes to use same functions.
    """

    @staticmethod
    def add_time(time: Datetime, days: int) -> Datetime:
        """
        The function to add given days to given datetime.

        Parameters:
            time (Datetime): The time need to be changed.
            days (int): The days need to added to given time.

        Returns:
            Datetime: a Datetime object of added date
        """

        return time + timedelta(days=days)

    @staticmethod
    def find_delay(allowed_date: Datetime, returned_date: Datetime) -> int:
        # REFACTOR-TRANSITION: rules live in domain.rules
        from domain.rules import find_delay as _find_delay
        return _find_delay(allowed_date, returned_date)

    @staticmethod
    def find_bill(delay: int):
        # REFACTOR-TRANSITION: rules live in domain.rules
        from domain.rules import find_bill as _find_bill
        return _find_bill(delay)

    @staticmethod
    def create_pdf(entry: Union[Bill, Receipt]):
        """
        The function to make a new pdf by given entry.

        Parameters:
            entry (Union[Bill, Receipt]): The entry need to be pdf.
        """

        from fpdf import FPDF

        # create pdf, add a page
        pdf = FPDF()
        pdf.add_page()

        pdf.set_font("Arial", "B", size=25)

        if isinstance(entry, Receipt):  # if it's a receipt
            mode = "Receipt"
            pdf.cell(200, 15, txt="Receipt", ln=1, align='C')
            pdf.set_font("Arial", size=15)

            text = "\n".join(["\nCustomer:", f"Name: {entry.costumer.first_name} {entry.costumer.last_name}",
                              f"Email: {entry.costumer.email}", "\nBook:", f'Name: {entry.book.name}',
                              f'Author: {entry.book.author}', "\nState:",
                              f'Borrowed Date: {entry.costumer.returned_books[entry.book]["borrowed_time"].strftime("%Y/%m/%d")}',
                              f'Extension Days: {entry.costumer.returned_books[entry.book]["extension"]}',
                              f'Returned Date: {entry.costumer.returned_books[entry.book]["returned_time"].strftime("%Y/%m/%d")}',
                              f'Delay: {str(entry.delay) + " days" if entry.delay else "No"}'])

        else:  # if it's a bill
            mode = "Bill"
            pdf.cell(200, 10, txt="Bill", ln=1, align='C')

            text = "\n".join(["\nCustomer:", f"Name: {entry.costumer.first_name} {entry.costumer.last_name}",
                              f"Email: {entry.costumer.email}", "\nBook:", f'Name: {entry.book.name}',
                              f'Author: {entry.book.author}', "\nState:",
                              f'Borrowed Date: {entry.costumer.returned_books[entry.book]["borrowed_time"].strftime("%Y/%m/%d")}',
                              f'Extension Days: {entry.costumer.returned_books[entry.book]["extension"]}',
                              f'Returned Date: {entry.costumer.returned_books[entry.book]["returned_time"].strftime("%Y/%m/%d")}',
                              f'Delay: {str(entry.delay) + " days" if entry.delay else "No"}',
                              f'Payment: {entry.cost} $'])

        for row in text.split('\n'):
            if row in ['Customer:', 'State:', 'Book:']:
                pdf.set_font("Arial", "B", size=17)
                pdf.cell(200, 10, txt=row, ln=1, align='L')
            else:
                pdf.set_font("Arial", size=15)
                pdf.cell(200, 10, txt=row, ln=1, align='L')

        # save the pdf
        pdf.output(
            f'{mode}_{entry.costumer.first_name}-{entry.costumer.last_name}[{Datetime.now().strftime("%H.%M.%S")}].pdf')
