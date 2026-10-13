import os
from sys import path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE = os.path.join(_ROOT, "Code")
path.insert(1, _ROOT)
path.insert(1, _CODE)

from Code.Costumer import Costumer
from Code.Officer import Officer
from domain.user import User


class TestUserShim:
    def test_costumer_is_domain_user(self):
        assert Costumer is User

    def test_constructed_costumer_is_user_instance(self):
        person = Costumer("zahra", "Karimi", "ZAHRAkarimi", "1234", "zahrakarimi@Gmail.Com", "09101234567")
        assert type(person) is User
        assert isinstance(person, User)
        assert isinstance(person, Costumer)

    def test_officer_class_kept(self):
        assert Officer.__name__ == "Officer"
        assert issubclass(Officer, User)
        assert Officer is not User
        officer = Officer("Mahdi", "Haji", "mahdihajipour", "4321", "mahdi@hajipour.com", "09117654321")
        assert officer.role == "officer"
        assert type(officer) is Officer
