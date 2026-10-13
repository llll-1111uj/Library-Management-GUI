import sys

class Person:
    """
       This is a class for representing a person.
    """

    def __init__(self):
        """
            Constructor function,

            self.first_name: first name of the person
            self.last_name: last name of the person

        """

        self.last_name = None
        self.first_name = None


# REFACTOR-TRANSITION: Person and Code.Person must be the same module (fixes test_Book).
_mod = sys.modules[__name__]
sys.modules["Person"] = _mod
sys.modules["Code.Person"] = _mod
