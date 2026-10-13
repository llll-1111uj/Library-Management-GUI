import logging
import os
import sys
from time import sleep
from typing import Union
from sys import path, argv, exit

if getattr(sys, "frozen", False):
    _ROOT_DIR = os.path.dirname(sys.executable)
    _CODE_DIR = getattr(sys, "_MEIPASS", _ROOT_DIR)
else:
    _CODE_DIR = os.path.dirname(os.path.abspath(__file__))
    _ROOT_DIR = os.path.dirname(_CODE_DIR)

for _p in (_ROOT_DIR, _CODE_DIR):
    if _p not in path:
        path.insert(0, _p)

os.chdir(_ROOT_DIR)

from PyQt5.QtCore import Qt
from functools import partial
from PyQt5.QtGui import QPixmap
from datetime import datetime as Datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QLabel, QTableWidget, QComboBox, QListWidget, QTextBrowser, QListWidgetItem, QMainWindow, \
    QDialog

from Lending import Lending
from Book import Book
from Person import Person
from Receipt_Bill import Receipt, Bill
from Tools import BookState, Tools, CommandState
from Officer import Officer  # noqa: F401  # REFACTOR-TRANSITION: keep Officer class; do not replace with User.
from domain.exceptions import ApprovalError, AuthError, RequestAlreadyHandled
from domain.request import RequestStatus, RequestType
from domain.rules import find_bill, find_delay
from repository.audit_repository import AuditRepository
from repository.book_repository import BookRepository
from repository.borrow_repository import BorrowRepository, restore_user_book_state
from repository.connection import get_connection, init_database
from repository.notify import refresh_notifications
from repository.request_repository import RequestRepository
from repository.user_repository import UserRepository
from service.approval_service import ApprovalService
from service.auth_service import AuthService
from service.book_service import BookService, action_visibility
from service.borrow_service import BorrowService
from service.user_service import UserService

_STATUS_LABEL = {
    RequestStatus.PENDING: "Not Accepted",
    RequestStatus.ACCEPTED: "Accepted",
    RequestStatus.DENIED: "Denied",
    RequestStatus.CANCELLED: "Denied",
}
_TYPE_LABEL = {
    RequestType.BORROW: "borrow",
    RequestType.RESERVE: "reserve",
    RequestType.RENEW: "extension",
    RequestType.RETURN: "return",
}
_BOOK_HEADER_SORT = {
    0: "name",
    1: "author",
    2: "state",
    3: "reserved_user_id",
    4: "borrowed_user_id",
    5: "borrowed_time",
    6: "return_time",
}

from GUI.Signin_gui import Ui_SignInWindow
from GUI.Signup_gui import Ui_SignUpWindow
from GUI.officer_gui import Ui_OfficerWindow
from GUI.costumer_gui import Ui_CostumerWindow

# Hidpi scaling
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
# use Hidpi icons
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class GUI(Ui_SignInWindow):
    """
       This is a class for creating the gui.
       """

    def __init__(self):
        """
            Constructor function,

            self.officers_costumers: to keep costumers and officers
            self.books: to keep books
            self.partition: to keep the partition window
            self.user: to keep the signed in user
        """

        super().__init__()
        self.officers_costumers = {"costumer": [], "officer": []}
        self.books = []
        self.partition = None
        self.user = None
        self.user_repo = UserRepository()
        self.auth = AuthService(self.user_repo)
        self.book_repo = BookRepository()
        self.book_service = BookService(self.book_repo, self.user_repo)
        self.user_service = UserService(self.user_repo)
        self.request_repo = RequestRepository()
        self.borrow_repo = BorrowRepository()
        self.borrow_service = BorrowService(self.request_repo)
        self.approval_service = ApprovalService()
        self.audit_repo = AuditRepository()
        self._book_page = 1
        self._book_sort_by = "name"
        self._book_sort_dir = "ASC"
        self._filling_books = False

    def setupUi(self, MainWindow):
        """CMS_UI parent class function"""

        super().setupUi(MainWindow)

    def retranslateUi(self, MainWindow):
        """CMS_UI parent class function"""

        super().retranslateUi(MainWindow)
        _translate = QtCore.QCoreApplication.translate

    def add_book(self, name: str, author: str, state: BookState = BookState.Available):
        """
            The function to add new a book

            Parameters:
                name (str): The string value of book's name
                author (str): The string value of book's author
                state (str): The string value of book's state
        """

        self.books.append(Book(name, author, state))

    def main(self) -> None:
        """
            Main function, read the sqlite file and set the logo for main page (sign in)
        """
        self.officers_costumers = {"costumer": [], "officer": []}
        self.books = []

        self.readSqlite()
        if self.officers_costumers["costumer"]:
            self.user = self.officers_costumers["costumer"][0]
        else:
            self.user = None

        self.set_logo(self.label_logo, MainWindow)

    def open_sign_up(self):
        """
            Function to open the sign up window and hide the sign in windows,
            it creates a new dialog and set it to gui designed for sign_up,
            then sets the logo and connect the push button to sign_up function.
        """

        MainWindow.hide()
        self.set_error(self.label_error)
        self.empty_boxes('signin')

        self.signup_app = QtWidgets.QDialog()

        self.signup = Ui_SignUpWindow()
        self.signup.setupUi(self.signup_app)
        self.signup_app.setSizeGripEnabled(True)

        self.signup.pushButton_Signup.clicked.connect(self.sign_up)

        self.set_logo(self.signup.label_logo, self.signup_app)
        self.signup_app.closeEvent = self.not_main_closeEvent

        frame = self.signup_app.frameGeometry()
        frame.moveCenter(QtWidgets.QApplication.desktop().availableGeometry().center())
        self.signup_app.move(frame.topLeft())

        self.signup_app.show()
        self.signup.lineEdit_username.setFocus()
        self.signup_app.exec_()

    def sign_up(self):
        """
            Function to check the sign up credential and sign up a new user if they're fine,
            it change the error label if there is a problem, and if successful reached,
            it will hide this window and open the sign in window in waiting of 1 second with uses of
            the multithreading.
        """

        self.set_error(self.signup.label_error, "")

        taken = [i.username for i in list(self.officers_costumers['costumer'] + self.officers_costumers['officer'])]
        try:
            person = self.auth.register_costumer(
                self.signup.lineEdit_username.text(),
                self.signup.lineEdit_password.text(),
                self.signup.lineEdit_password_2.text(),
                self.signup.lineEdit_full_name.text(),
                self.signup.lineEdit_email.text(),
                self.signup.lineEdit_phone.text(),
                taken,
            )
        except AuthError as exc:
            self.set_error(self.signup.label_error, exc.message)
            return
        except Exception:
            logging.getLogger(__name__).exception("sign_up failed")
            self.set_error(self.signup.label_error, "Username is already used !")
            return

        # REFACTOR-TRANSITION: AuthService already upserted; saveSqlite writes the snapshot again.
        self.commit_registered_user(person, "costumer")

        self.set_error(self.signup.label_error, "Signing up ...", 'green')
        QtWidgets.QApplication.processEvents()
        sleep(1)

        self.signup_app.close()

    def sign_in(self):
        """
            Function to check the sign in credential and sign in the new user if they're fine.
        """

        self.set_error(self.label_error, "")

        users = self.officers_costumers['costumer'] + self.officers_costumers['officer']
        try:
            entrance = self.auth.login(
                self.lineEdit_username_email.text(),
                self.lineEdit_password.text(),
                users,
            )
        except AuthError as exc:
            self.set_error(self.label_error, exc.message)
            return
        except Exception:
            logging.getLogger(__name__).exception("sign_in failed")
            self.set_error(self.label_error, "Username/Email address or password incorrect !")
            return

        self.set_error(self.label_error, "Signing in ...", 'green')
        self.user = entrance
        QtWidgets.QApplication.processEvents()
        sleep(1)

        self.open_partition()

    def open_partition(self):
        """
            Function to checks if the person is officer or costumer and opens the appropriate partition window
            and sets the connection between objects and functions.
        """

        MainWindow.hide()
        self.set_error(self.label_error)
        self.empty_boxes('signin')

        partition_app = QtWidgets.QDialog()

        # TODO: A4 阶段统一 User 类型。
        # Keep memory-list membership (not isinstance/role) to choose costumer vs officer UI.
        if self.user in self.officers_costumers['costumer']:  # if it's a costumer
            self.partition = Ui_CostumerWindow()
            self.partition.setupUi(partition_app)
            partition_app.setSizeGripEnabled(True)

            # ========= 新增：设置列表滚动条（读者端） =========
            self.partition.listWidget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
            self.partition.listWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            # ================================================

            # fill the list with list of actions of the costumer
            self.fill_list(self.partition.listWidget, 'costumer')

            # fill the table of my_books with borrowed or returned books
            self.fill_table(self.partition.tableWidget_my_books, 'my_books')

            # if an item selected from table of my books, decide to show or hide "return" and "add days" buttons
            self.partition.tableWidget_my_books.itemSelectionChanged.connect(self.my_books_table_select)

            # connect the push buttons to their functions
            self.partition.pushButton_reserve.clicked.connect(partial(self.costumer_request1, 'reserve'))
            self.partition.pushButton_borrow.clicked.connect(partial(self.costumer_request1, 'borrow'))
            self.partition.pushButton_add_days.clicked.connect(partial(self.costumer_request2, 'extension'))
            self.partition.pushButton_return.clicked.connect(partial(self.costumer_request2, 'return'))

            self.partition.tabWidget.currentChanged.connect(partial(self.SwitchTab, 'costumer'))
            self.partition.listWidget.currentItemChanged.connect(
                partial(self.fill_description, self.partition.textBrowser, 'costumer'))

        else:  # if it's a officer
            self.partition = Ui_OfficerWindow()
            self.partition.setupUi(partition_app)
            partition_app.setSizeGripEnabled(True)

            # ========= 新增：设置列表滚动条（管理员端） =========
            self.partition.listWidget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
            self.partition.listWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            # ==================================================


            # fill the list with list of actions of all costumer
            self.fill_list(self.partition.listWidget, 'officer')

            # connect the push buttons to their functions
            self.partition.pushButton_confirm.clicked.connect(partial(self.officer_confirm, True))
            self.partition.pushButton_deny.clicked.connect(partial(self.officer_confirm, False))
            self.partition.pushButton_issue_receipt.clicked.connect(partial(self.issue_rb, 'receipt'))
            self.partition.pushButton_issue_bill.clicked.connect(partial(self.issue_rb, 'bill'))

            self.partition.pushButton_create_officer.clicked.connect(self.add_officer)

            self.partition.pushButton_issue_receipt.hide()
            self.partition.pushButton_issue_bill.hide()
            self.partition.tabWidget.currentChanged.connect(partial(self.SwitchTab, 'officer'))
            self.partition.listWidget.currentItemChanged.connect(
                partial(self.fill_description, self.partition.textBrowser, 'officer'))

        self._book_page = 1
        self._book_sort_by = "name"
        self._book_sort_dir = "ASC"
        self._wire_books_table()
        self.fill_table(self.partition.tableWidget_books, 'books', self.partition.comboBox_books)

        partition_app.closeEvent = self.not_main_closeEvent
        self.set_logo(self.partition.label_logo, partition_app)
        partition_app.show()
        partition_app.exec_()

    def set_logo(self, object: QLabel, main_window: Union[QMainWindow, QDialog]):
        """
            The function to set logo and icon of the window

            Parameters:
                object (QLabel): The label should have the logo
                main_window (Union[QMainWindow, QDialog]): The window should have the icon
        """

        # logo
        pixmap = QPixmap(os.path.join(_ROOT_DIR, 'logo64.png'))
        object.setPixmap(pixmap)

        # icon
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(os.path.join(_ROOT_DIR, "logo.ico")), QtGui.QIcon.Selected, QtGui.QIcon.On)
        main_window.setWindowIcon(icon)

    def set_error(self, object: QLabel, text: str = "", color: str = "red"):
        """
            The function to set text to given error labels

            Parameters:
                object (QLabel): The label should its text be changed
                text (str): The text the label should have now
                color (str): The color of the label's text
        """

        if color == "red":
            object.setStyleSheet("background-color:#F6F8FA;color:#FC0000")

        else:
            object.setStyleSheet("background-color:#F6F8FA;color:#50C878")

        object.setText(text)

    def empty_boxes(self, window: str):
        """
            The function to clear the text in line edits

            Parameters:
                window (str): The name of partition which it's labels should be empty
        """

        if window == "signin":
            self.lineEdit_username_email.setText("")
            self.lineEdit_password.setText("")

        elif window == "officer":
            self.partition.lineEdit_username.setText("")
            self.partition.lineEdit_password.setText("")
            self.partition.lineEdit_password_2.setText("")
            self.partition.lineEdit_full_name.setText("")
            self.partition.lineEdit_email.setText("")
            self.partition.lineEdit_phone.setText("")

    def my_books_table_select(self):
        """
            The function to show or hide the 'return' and 'add days' buttons,

            if checks if the item selected is borrowed, if will show these two buttons,
            if not it will hide them.
        """

        index = self.partition.tableWidget_my_books.currentRow()
        if index > -1:
            self.partition.spinBox.setValue(int(self.partition.tableWidget_my_books.item(index, 4).text()))

            if self.partition.tableWidget_my_books.item(index, 1).text() == "Borrowed":
                self.partition.pushButton_return.show()
                self.partition.pushButton_add_days.show()

            else:
                self.partition.pushButton_return.hide()
                self.partition.pushButton_add_days.hide()

    def not_main_closeEvent(self, event):
        """ The function which any window (except sign_in) will run when it's closed. """

        MainWindow.show()

    def closeEvent(self, event) -> None:
        """This function enables when user close the main window (sing_in window)"""

        self.saveSqlite()

    def fill_table(self, table: QTableWidget, mode: str, comboBox: QComboBox = "") -> None:
        """
            The function to fill the given table with modes or comboBox.

            Parameters:
                table (QTableWidget): The table that should be filled by items
                mode (str): The mode of being filled
                comboBox (QComboBox): The combobox which uses when filling the books table
        """

        if mode == "books":
            self._fill_books_table()
            return

        elif mode == 'my_books':
            table.setRowCount(0)
            loans = self.borrow_repo.list_by_user(self.user.user_id)
            users_by_id = self._users_by_id()
            x = 0
            for loan in loans:
                if loan.status not in ("borrowed", "overdue"):
                    continue
                book = self.book_service.get(loan.book_id, users_by_id=users_by_id)
                if not book:
                    continue
                due = loan.return_time
                borrowed_at = loan.borrowed_time
                delay = find_delay(due, Datetime.now()) if due else 0
                bill = find_bill(delay)
                table.insertRow(x)
                table.setItem(x, 0, QtWidgets.QTableWidgetItem(book.name))
                table.setItem(x, 1, QtWidgets.QTableWidgetItem("Borrowed"))
                table.setItem(x, 2, QtWidgets.QTableWidgetItem(borrowed_at.strftime("%Y/%m/%d") if borrowed_at else "---"))
                table.setItem(x, 3, QtWidgets.QTableWidgetItem(due.strftime("%Y/%m/%d") if due else "---"))
                table.setItem(x, 4, QtWidgets.QTableWidgetItem(str(loan.extension_days)))
                table.setItem(x, 5, QtWidgets.QTableWidgetItem(str(delay)))
                table.setItem(x, 6, QtWidgets.QTableWidgetItem(str(bill)))
                x += 1
            y = 0
            for loan in loans:
                if loan.status != "returned":
                    continue
                book = self.book_service.get(loan.book_id, users_by_id=users_by_id)
                if not book:
                    continue
                delay = find_delay(loan.return_time, loan.actual_return_time)
                bill = find_bill(delay)
                table.insertRow(y + x)
                table.setItem(y + x, 0, QtWidgets.QTableWidgetItem(book.name))
                table.setItem(y + x, 1, QtWidgets.QTableWidgetItem("Returned"))
                table.setItem(y + x, 2, QtWidgets.QTableWidgetItem(
                    loan.borrowed_time.strftime("%Y/%m/%d") if loan.borrowed_time else "---"))
                table.setItem(y + x, 3, QtWidgets.QTableWidgetItem(
                    loan.actual_return_time.strftime("%Y/%m/%d") if loan.actual_return_time else "---"))
                table.setItem(y + x, 4, QtWidgets.QTableWidgetItem(str(loan.extension_days)))
                table.setItem(y + x, 5, QtWidgets.QTableWidgetItem(str(delay)))
                table.setItem(y + x, 6, QtWidgets.QTableWidgetItem(str(bill)))
                y += 1

    def _wire_books_table(self):
        partition = self.partition
        table = partition.tableWidget_books
        table.setSortingEnabled(False)
        header = table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.sortIndicatorChanged.connect(self._on_books_sort)
        partition.comboBox_books.currentIndexChanged.connect(self._on_books_filter_changed)
        if hasattr(partition, "lineEdit_book_search"):
            partition.lineEdit_book_search.returnPressed.connect(self._on_books_search)
        if hasattr(partition, "pushButton_book_search"):
            partition.pushButton_book_search.clicked.connect(self._on_books_search)
        if hasattr(partition, "comboBox_page_size"):
            partition.comboBox_page_size.currentIndexChanged.connect(self._on_books_filter_changed)
        if hasattr(partition, "pushButton_book_prev"):
            partition.pushButton_book_prev.clicked.connect(self._on_books_prev)
        if hasattr(partition, "pushButton_book_next"):
            partition.pushButton_book_next.clicked.connect(self._on_books_next)

    def _books_filter_state(self):
        combo = self.partition.comboBox_books
        return {0: "Available", 1: "Borrowed"}.get(combo.currentIndex(), "Reserved")

    def _books_page_size(self):
        if not hasattr(self.partition, "comboBox_page_size"):
            return 20
        try:
            return int(self.partition.comboBox_page_size.currentText())
        except (TypeError, ValueError):
            return 20

    def _books_keyword(self):
        if not hasattr(self.partition, "lineEdit_book_search"):
            return ""
        return self.partition.lineEdit_book_search.text()

    def _on_books_filter_changed(self, *_args):
        self._book_page = 1
        self._fill_books_table()

    def _on_books_search(self):
        self._book_page = 1
        self._fill_books_table()

    def _on_books_prev(self):
        self._book_page = max(1, int(self._book_page or 1) - 1)
        self._fill_books_table()

    def _on_books_next(self):
        self._book_page = int(self._book_page or 1) + 1
        self._fill_books_table()

    def _on_books_sort(self, logical_index, order):
        if self._filling_books:
            return
        self._book_sort_by = _BOOK_HEADER_SORT.get(logical_index, "name")
        self._book_sort_dir = "DESC" if order == Qt.DescendingOrder else "ASC"
        self._fill_books_table()

    def _fill_books_table(self):
        if self.partition is None or self._filling_books:
            return
        table = self.partition.tableWidget_books
        filter_state = self._books_filter_state()
        visibility = action_visibility(filter_state)
        if hasattr(self.partition, "pushButton_reserve") and hasattr(self.partition, "pushButton_borrow"):
            self.partition.pushButton_reserve.setVisible(visibility["reserve"])
            self.partition.pushButton_borrow.setVisible(visibility["borrow"])

        users_by_id = {}
        for role in ("costumer", "officer"):
            for person in self.officers_costumers.get(role, []):
                if getattr(person, "user_id", None):
                    users_by_id[person.user_id] = person

        self._filling_books = True
        try:
            result = self.book_service.search_books(
                keyword=self._books_keyword(),
                filter_state=filter_state,
                sort_by=self._book_sort_by,
                sort_dir=self._book_sort_dir,
                page=self._book_page,
                page_size=self._books_page_size(),
                users_by_id=users_by_id,
            )
            self._book_page = result["page"]
            books = result["books"]
            table.setSortingEnabled(False)
            table.setRowCount(0)
            x = 0
            while x < len(books):
                table.insertRow(x)
                table.setItem(x, 0, QtWidgets.QTableWidgetItem(books[x].name))
                table.setItem(x, 1, QtWidgets.QTableWidgetItem(books[x].author))
                table.setItem(x, 2, QtWidgets.QTableWidgetItem(filter_state))
                table.setItem(x, 3, QtWidgets.QTableWidgetItem("Yes" if books[x].is_reserved else "No"))
                if filter_state == "Available":
                    table.setItem(x, 4, QtWidgets.QTableWidgetItem("No"))
                    table.setItem(x, 5, QtWidgets.QTableWidgetItem("---"))
                    table.setItem(x, 6, QtWidgets.QTableWidgetItem("---"))
                elif filter_state == "Borrowed":
                    table.setItem(x, 4, QtWidgets.QTableWidgetItem("Yes"))
                    table.setItem(
                        x, 5,
                        QtWidgets.QTableWidgetItem(
                            books[x].borrowed_time.strftime("%Y/%m/%d") if books[x].borrowed_time else "---",
                        ),
                    )
                    table.setItem(
                        x, 6,
                        QtWidgets.QTableWidgetItem(
                            books[x].return_time.strftime("%Y/%m/%d") if books[x].return_time else "---",
                        ),
                    )
                else:
                    if not books[x].borrowed.first_name:
                        table.setItem(x, 4, QtWidgets.QTableWidgetItem("No"))
                        table.setItem(x, 5, QtWidgets.QTableWidgetItem("---"))
                        table.setItem(x, 6, QtWidgets.QTableWidgetItem("---"))
                    else:
                        table.setItem(x, 4, QtWidgets.QTableWidgetItem("Yes"))
                        table.setItem(
                            x, 5,
                            QtWidgets.QTableWidgetItem(
                                books[x].borrowed_time.strftime("%Y/%m/%d") if books[x].borrowed_time else "---",
                            ),
                        )
                        table.setItem(
                            x, 6,
                            QtWidgets.QTableWidgetItem(
                                books[x].return_time.strftime("%Y/%m/%d") if books[x].return_time else "---",
                            ),
                        )
                x += 1
            if hasattr(self.partition, "label_book_page"):
                self.partition.label_book_page.setText("%s / %s" % (result["page"], result["total_pages"]))
            if hasattr(self.partition, "pushButton_book_prev"):
                self.partition.pushButton_book_prev.setEnabled(result["page"] > 1)
            if hasattr(self.partition, "pushButton_book_next"):
                self.partition.pushButton_book_next.setEnabled(result["page"] < result["total_pages"])
            header = table.horizontalHeader()
            col = 0
            for index, name in _BOOK_HEADER_SORT.items():
                if name == self._book_sort_by:
                    col = index
                    break
            order = Qt.DescendingOrder if self._book_sort_dir == "DESC" else Qt.AscendingOrder
            header.blockSignals(True)
            header.setSortIndicator(col, order)
            header.blockSignals(False)
        finally:
            self._filling_books = False

    def _is_audit_tab(self):
        if self.partition is None or not hasattr(self.partition, "tab_Audit"):
            return False
        return self.partition.tabWidget.currentWidget() is self.partition.tab_Audit

    def _refresh_audit_if_visible(self):
        if self._is_audit_tab():
            self.fill_audit_table()

    def fill_audit_table(self):
        if self.partition is None or not hasattr(self.partition, "tableWidget_audit"):
            return
        table = self.partition.tableWidget_audit
        rows = self.audit_repo.list_recent(200)
        table.setRowCount(0)
        for index, row in enumerate(rows):
            table.insertRow(index)
            target = row.get("target_type") or ""
            if row.get("target_id") is not None:
                target = ("%s #%s" % (target, row["target_id"])).strip()
            table.setItem(index, 0, QtWidgets.QTableWidgetItem(row.get("created_at") or ""))
            table.setItem(index, 1, QtWidgets.QTableWidgetItem(row.get("username") or "—"))
            table.setItem(index, 2, QtWidgets.QTableWidgetItem(row.get("action") or ""))
            table.setItem(index, 3, QtWidgets.QTableWidgetItem(target))
            table.setItem(index, 4, QtWidgets.QTableWidgetItem(row.get("detail") or ""))

    def fill_list(self, list_: QListWidget, mode: str) -> None:
        """
            The function to fill the given list with modes.

            Parameters:
                list_ (QListWidget): The list that should be filled by items
                mode (str): The mode of being filled
        """

        # clear the list
        list_.clear()

        emoji = {"Not Accepted": "❔", "Accepted": "✅", "Denied": "❌"}  # emoji keeper
        users_by_id = self._users_by_id()

        if mode == "costumer":
            for req in self.request_repo.list_by_user(self.user.user_id):
                book = self.book_service.get(req.book_id, users_by_id=users_by_id)
                label = _STATUS_LABEL.get(req.status, "Not Accepted")
                rtype = _TYPE_LABEL.get(req.request_type, req.request_type.value.lower())
                name = book.name if book else str(req.book_id)
                item_ = f'{rtype.title()}) {name} => {label}'
                item = QListWidgetItem(item_)
                item.setData(Qt.UserRole, req.request_id)
                if item_.endswith("Not Accepted"):
                    item.setForeground(Qt.blue)
                elif item_.endswith("Accepted"):
                    item.setForeground(Qt.darkGreen)
                else:
                    item.setForeground(Qt.red)
                list_.addItem(item)

        else:  # if mode is officer
            self.partition.pushButton_issue_receipt.hide()
            self.partition.pushButton_issue_bill.hide()
            self.list_ = []
            for req in self.request_repo.list_all():
                book = self.book_service.get(req.book_id, users_by_id=users_by_id)
                person = self.user_service.get(req.user_id)
                label = _STATUS_LABEL.get(req.status, "Not Accepted")
                rtype = _TYPE_LABEL.get(req.request_type, req.request_type.value.lower())
                name = book.name if book else str(req.book_id)
                uname = f'{person.first_name} {person.last_name}' if person else str(req.user_id)
                item_ = f'{emoji[label]} {rtype.title()}) {name} => {uname}'
                item = QListWidgetItem(item_)
                item.setData(Qt.UserRole, req.request_id)
                list_.addItem(item)
                self.list_.append(item_)

    def fill_description(self, textBrowser: QTextBrowser, mode: str):
        """
            The function to fill the description of selected item in lists.

            Parameters:
                textBrowser (QTextBrowser): The text browser object to be filled with text.
                mode (str): The mode of being filled
        """

        item = self.partition.listWidget.currentItem()
        if item is None:
            return
        req = self.request_repo.get(item.data(Qt.UserRole))
        if req is None:
            return
        users_by_id = self._users_by_id()
        book = self.book_service.get(req.book_id, users_by_id=users_by_id)
        person = self.user_service.get(req.user_id)
        info = {
            "request": _TYPE_LABEL.get(req.request_type, req.request_type.value.lower()),
            "book": book,
            "date": req.created_at,
            "accepted": _STATUS_LABEL.get(req.status, "Not Accepted"),
        }
        if req.request_type == RequestType.RENEW:
            info["extension"] = req.extra_days
        if mode != "costumer":
            if req.request_type == RequestType.RETURN:
                self.partition.pushButton_issue_receipt.show()
                self.partition.pushButton_issue_bill.show()
            else:
                self.partition.pushButton_issue_receipt.hide()
                self.partition.pushButton_issue_bill.hide()
            info["user"] = person
        text = [f'{key.title()}: {info[key]}' for key in info.keys()]
        textBrowser.setText("\n".join(text).replace("Book: ", "Book:\n").title())

    def costumer_request1(self, mode):
        """
            The function to handle request of costumer,
            in 'tableWidget_books' and modes 'reserve' and 'borrow'

            Parameters:
                mode (str): The mode of request
        """

        index = self.partition.tableWidget_books.currentRow()

        if index == -1:  # if item not selected in table
            self.set_error(self.partition.label_error, "Please select a book from table !")
            return

        book = [i for i in self.books if i.name == self.partition.tableWidget_books.item(index, 0).text()][0]

        if mode == 'reserve':
            if book.reserved.first_name:
                self.set_error(self.partition.label_error, "This book is already reserved !")

            elif book.reserved.first_name is None and book.borrowed.first_name is None:
                self.set_error(self.partition.label_error, "You can borrow this book !")

            elif len(self.user.reserve) == 3:
                self.set_error(self.partition.label_error, "You can't reserve any new book !")

            else:
                self.borrow_service.submit_reserve(self.user, book)
                self.set_error(self.partition.label_error, "Sent request to officer !", 'green')

        elif mode == 'borrow':
            if len(self.user.borrowed_books) == 3:
                self.set_error(self.partition.label_error, "You can't borrow any new book !")

            else:
                self.borrow_service.submit_borrow(self.user, book)
                self.set_error(self.partition.label_error, "Sent request to officer !", 'green')

    def costumer_request2(self, mode):
        """
            The function to handle request of costumer,
            in 'tableWidget_my_books' and modes 'extension' and 'return'

            Parameters:
                mode (str): The mode of request
        """

        index = self.partition.tableWidget_my_books.currentRow()

        if index == -1:
            self.set_error(self.partition.label_error_2, "Please select a book from table !")
            return

        book = [i for i in self.books if i.name == self.partition.tableWidget_my_books.item(index, 0).text()][0]

        if mode == 'extension':
            current = int(self.partition.tableWidget_my_books.item(index, 4).text())
            if self.partition.spinBox.value() <= current:
                self.set_error(self.partition.label_error_2, f"Extension days can't be equal/less than {current} !")

            else:
                self.borrow_service.submit_renew(self.user, book, self.partition.spinBox.value())
                self.set_error(self.partition.label_error_2, "Sent request to officer !", 'green')

        elif mode == 'return':
            self.borrow_service.submit_return(self.user, book)
            self.set_error(self.partition.label_error_2, "Sent request to officer !", 'green')

    def officer_confirm(self, accept: bool = True):
        """
            The function to add a new request to

            Parameters:
                accept (bool): The boolean value of action officer performed on a request
        """

        item = self.partition.listWidget.currentItem()
        if item is None:
            return
        request_id = item.data(Qt.UserRole)
        self.set_error(self.partition.label_error)
        try:
            if accept:
                extra = self.approval_service.confirm(request_id, self.user)
                req = extra["request"]
                bill = extra.get("bill") or 0
                if req.request_type == RequestType.RETURN:
                    if bill:
                        self.set_error(
                            self.partition.label_error,
                            f"User request accepted ! Issue a bill for {bill} $",
                            "green",
                        )
                    else:
                        self.set_error(
                            self.partition.label_error,
                            "User request accepted ! Issue a receipt",
                            "green",
                        )
                else:
                    self.set_error(self.partition.label_error, "User request accepted !", "green")
            else:
                self.approval_service.deny(request_id, self.user)
                self.set_error(self.partition.label_error, "User request denied !", "green")
        except RequestAlreadyHandled as exc:
            self.set_error(self.partition.label_error, exc.message)
        except ApprovalError as exc:
            self.set_error(self.partition.label_error, exc.message)

        self._reload_catalog()
        if hasattr(self.partition, "tableWidget_books"):
            self.fill_table(self.partition.tableWidget_books, "books", self.partition.comboBox_books)
        self.fill_list(self.partition.listWidget, "officer")
        self._refresh_audit_if_visible()

    def issue_rb(self, mode: str):
        """
            The function to create a bill or receipt

            Parameters:
                mode (str): The mode of being bill or receipt
        """

        item = self.partition.listWidget.currentItem()
        if item is None:
            return
        req = self.request_repo.get(item.data(Qt.UserRole))
        if req is None or req.status != RequestStatus.ACCEPTED or req.request_type != RequestType.RETURN:
            self.set_error(self.partition.label_error, f"Only accepted returning can have a {mode} !")
            return
        users_by_id = self._users_by_id()
        book = self.book_service.get(req.book_id, users_by_id=users_by_id)
        user = self.user_service.get(req.user_id)
        loans = [ln for ln in self.borrow_repo.list_by_user(req.user_id) if ln.book_id == req.book_id and ln.status == "returned"]
        loan = loans[-1] if loans else None
        delay = find_delay(loan.return_time, loan.actual_return_time) if loan else 0
        bill = find_bill(delay)
        if mode == "receipt":
            Tools.create_pdf(Receipt(book, user, delay))
        else:
            Tools.create_pdf(Bill(book, user, delay, bill))
        self.set_error(self.partition.label_error, "Done !", "green")

    def add_officer(self):
        """
            The function to add a new officer, it's similar to sign up
        """

        self.set_error(self.partition.label_error_2, "")

        taken = [i.username for i in list(self.officers_costumers['costumer'] + self.officers_costumers['officer'])]
        try:
            person = self.auth.register_officer(
                self.partition.lineEdit_username.text(),
                self.partition.lineEdit_password.text(),
                self.partition.lineEdit_password_2.text(),
                self.partition.lineEdit_full_name.text(),
                self.partition.lineEdit_email.text(),
                self.partition.lineEdit_phone.text(),
                taken,
            )
        except AuthError as exc:
            self.set_error(self.partition.label_error_2, exc.message)
            return
        except Exception:
            logging.getLogger(__name__).exception("add_officer failed")
            self.set_error(self.partition.label_error_2, "Username is already used !")
            return

        # REFACTOR-TRANSITION: AuthService already upserted; saveSqlite writes the snapshot again.
        self.commit_registered_user(person, "officer")

        self.set_error(self.partition.label_error_2, "Signed up the new user successfully !", 'green')
        self.empty_boxes("officer")
        self._refresh_audit_if_visible()

    def SwitchTab(self, mode: str) -> None:
        """
            This function handle changes when switching between tabs

            Parameters:
                mode (str): The mode of being costumer or officer
        """

        widget = self.partition.tabWidget.currentWidget()
        if mode == "costumer":
            if widget is getattr(self.partition, "tab_Books", None) or self.partition.tabWidget.currentIndex() == 0:
                self.fill_table(self.partition.tableWidget_books, 'books', self.partition.comboBox_books)

            elif widget is getattr(self.partition, "tab_My_Books", None) or self.partition.tabWidget.currentIndex() == 1:
                self.fill_table(self.partition.tableWidget_my_books, 'my_books')

            elif self.partition.tabWidget.currentIndex() == 2:
                self.fill_list(self.partition.listWidget, mode)

        else:
            if widget is getattr(self.partition, "tab_Notification", None) or self.partition.tabWidget.currentIndex() == 0:
                self.fill_list(self.partition.listWidget, 'officer')

            elif widget is getattr(self.partition, "tab_Books_State", None):
                self.fill_table(self.partition.tableWidget_books, 'books', self.partition.comboBox_books)

            elif widget is getattr(self.partition, "tab_Audit", None):
                self.fill_audit_table()

    def _connect_db(self):
        return get_connection()

    def ensure_tables(self, conn=None):
        """启动时创建 Users/Books/reserve/borrow_record/message_notify。"""
        close_after = False
        if conn is None:
            conn = init_database()
            close_after = True
        else:
            init_database()
        if close_after:
            conn.close()

    def _seed_default_accounts(self):
        """Create built-in reader and officer accounts when the Users table is empty."""
        seeded = self.auth.seed_defaults()
        self.officers_costumers["costumer"].extend(seeded["costumer"])
        self.officers_costumers["officer"].extend(seeded["officer"])

    def _seed_default_books(self):
        self.add_book("Me Before you", "Jojo Moyes")
        self.add_book("Me After you", "Jojo Moyes")
        self.add_book("Paris 1", "Jojo Moyes")
        self.add_book("Paris 2", "Jojo Moyes")
        self.add_book("Paris 3", "Jojo Moyes")
        self.add_book("Paris 4", "Jojo Moyes")
        self.add_book("Paris 5", "Jojo Moyes")
        self.add_book("Paris 6", "Jojo Moyes")

    def commit_registered_user(self, person, role):
        # REFACTOR-TRANSITION: AuthService.upsert is write #1; saveSqlite snapshot is write #2.
        self.officers_costumers[role].append(person)
        self.saveSqlite()

    def _users_by_id(self):
        by_id = {}
        for role in ("costumer", "officer"):
            for person in self.officers_costumers.get(role, []):
                if getattr(person, "user_id", None):
                    by_id[person.user_id] = person
        return by_id

    def _reload_catalog(self):
        users_by_id = self._users_by_id()
        self.books, books_by_id = self.book_repo.list_all(users_by_id)
        restore_user_book_state(self.officers_costumers, books_by_id)
        refresh_notifications()

    def saveSqlite(self):
        """将用户与图书（含状态、日期）同步写入数据库，不删除借阅/预约/消息记录。"""
        init_database()
        self.user_repo.save_users(self.officers_costumers)
        for book in self.books:
            self.book_repo.upsert(book)

    def readSqlite(self):
        """
            启动时建表、加载用户和图书，并刷新逾期/预约到期消息。
        """
        init_database()
        self.officers_costumers, users_by_id = self.user_repo.list_all()
        if not users_by_id:
            self.officers_costumers = {"costumer": [], "officer": []}
            self._seed_default_accounts()
            self.officers_costumers, users_by_id = self.user_repo.list_all()

        self.books, books_by_id = self.book_repo.list_all(users_by_id)
        if not self.books:
            self._seed_default_books()
            self.saveSqlite()
            self.books, books_by_id = self.book_repo.list_all(users_by_id)

        restore_user_book_state(self.officers_costumers, books_by_id)
        refresh_notifications()


def main():
    """Application entry: start sign-in window with login/register wired up."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    global MainWindow

    app = QtWidgets.QApplication(argv)
    app.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
    MainWindow = QtWidgets.QMainWindow()

    ui = GUI()
    ui.setupUi(MainWindow)

    ui.main()

    MainWindow.closeEvent = ui.closeEvent
    ui.pushButton_Signin.clicked.connect(ui.sign_in)
    ui.pushButton_create_account.clicked.connect(ui.open_sign_up)

    MainWindow.show()
    exit(app.exec_())


if __name__ == "__main__":
    main()

