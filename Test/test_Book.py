import pytest
from sys import path
from datetime import datetime as Datetime, timedelta

path.insert(1, '../')
from Code.Person import Person
from Code.Book import Book
from Code.Costumer import Costumer
from Code.Tools import BookState


class TestBook:
    @pytest.fixture
    def setUp(self):
        self.costumer1 = Costumer("Zahra", "Karimi", "zahrakarimi", "1234", "zahrakarimi@gmail.com", "09101234567")
        self.costumer2 = Costumer("Fateme", "Azizi", "fatemeazizi", "4321", "fatemeazizi@gmail.com", "09107654321")

        self.book1 = Book("Me Before you 1", "JoJo Moyes", BookState.Available)
        self.book2 = Book("Me after You", "Ms. joJo Moyes", BookState.Available, Person(), Datetime.now(),
                          Datetime.now())

    def test_names(self, setUp):
        assert self.book1.name == "Me Before You 1"
        assert self.book1.author == "Jojo Moyes"
        assert self.book2.name == "Me After You"
        assert self.book2.author == "Ms. Jojo Moyes"

    def test_states(self, setUp):
        assert self.book1.state == BookState.Available
        assert self.book2.state == BookState.Available

        self.book1.state = BookState.Borrowed
        self.book2.state = BookState.Borrowed

        assert self.book1.state == BookState.Borrowed
        assert self.book2.state == BookState.Borrowed

    def test_reserved(self, setUp):
        assert isinstance(self.book1.reserved, Person)
        assert isinstance(self.book2.reserved, Person)

        self.book1.reserved = self.costumer1
        self.book2.reserved = self.costumer2

        assert isinstance(self.book1.reserved, Person)
        assert isinstance(self.book2.reserved, Person)

    def test_borrowed(self, setUp):
        assert isinstance(self.book1.borrowed, Person)
        assert isinstance(self.book2.borrowed, Person)

        self.book1.borrowed = self.costumer1
        self.book2.borrowed = self.costumer2

        assert isinstance(self.book1.borrowed, Person)
        assert isinstance(self.book2.borrowed, Person)

    def test_times(self, setUp):
        # Book 构造时未传日期就是 None，这是既定契约；是否填日期由
        # Costumer.borrow_book / persist_borrow 负责，不在 Book 类。
        # 借出后日期如何被填充应在借阅 service / repository 层测，不是构造函数的职责。
        assert self.book1.borrowed_time is None
        assert self.book1.return_time is None

        assert isinstance(self.book2.borrowed_time, Datetime)
        assert isinstance(self.book2.return_time, Datetime)

        same_day = Datetime(2026, 1, 1, 12, 0, 0)
        book_same = Book(
            "Same Day Return",
            "Author",
            BookState.Available,
            Person(),
            same_day,
            same_day,
        )
        assert book_same.borrowed_time == same_day
        assert book_same.return_time == same_day + timedelta(days=7)
