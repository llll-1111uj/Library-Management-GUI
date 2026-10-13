import os
from sys import path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE = os.path.join(_ROOT, "Code")
path.insert(1, _ROOT)
path.insert(1, _CODE)

import pytest

from domain.exceptions import AuthError
from domain.password import is_hashed, verify_password
from domain.user import User
from repository.connection import get_connection, init_database
from repository.user_repository import UserRepository
from service.auth_service import AuthService


@pytest.fixture
def auth(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_database(db_path)
    repo = UserRepository(db_path)
    return AuthService(repo), repo, db_path


class TestAuthService:
    def test_register_and_login(self, auth):
        service, repo, _db = auth
        person = service.register_costumer(
            "NewUser", "pw1", "pw1", "New User", "new@user.com", "09111234567", []
        )
        assert is_hashed(person.password)
        assert verify_password("pw1", person.password)
        users, by_id = repo.list_all()
        assert person.username in [u.username for u in users["costumer"]]
        logged = service.login("newuser", "pw1", users["costumer"] + users["officer"])
        assert logged.username == "newuser"

    def test_register_duplicate_username(self, auth):
        service, _repo, _db = auth
        service.register_costumer("dup", "pw1", "pw1", "A B", "a@b.com", "09111234567", [])
        with pytest.raises(AuthError) as exc:
            service.register_costumer("dup", "pw1", "pw1", "A B", "a@b.com", "09111234567", ["dup"])
        assert exc.value.message == "Username is already used !"

    def test_login_plaintext_upgrade(self, auth):
        service, repo, _db = auth
        person = User("Azar", "Haji", "plainuser", "hashed-placeholder", "plain@user.com", "09111234567")
        person._password = "1234"
        repo.upsert(person, role="costumer")
        users, _by_id = repo.list_all()
        loaded = users["costumer"][0]
        loaded._password = "1234"
        logged = service.login("plainuser", "1234", [loaded])
        assert is_hashed(logged.password)
        assert verify_password("1234", logged.password)
        users, _by_id = repo.list_all()
        assert is_hashed(users["costumer"][0].password)

    def test_register_dual_write_memory_and_db(self, auth):
        """Register then dual-write: DB row and in-memory list both keep the user."""
        service, repo, db_path = auth
        officers_costumers = {"costumer": [], "officer": []}

        person = service.register_costumer(
            "DualUser", "pw1", "pw1", "Dual User", "dual@user.com", "09111234567", []
        )
        # Same sequence as GUI.commit_registered_user (AuthService upsert + snapshot).
        officers_costumers["costumer"].append(person)
        repo.save_users(officers_costumers)

        assert person in officers_costumers["costumer"]
        assert any(u.username == "dualuser" for u in officers_costumers["costumer"])

        conn = get_connection(db_path)
        row = conn.execute(
            "SELECT username, role FROM Users WHERE username=?",
            ("dualuser",),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "dualuser"
        assert row[1] == "costumer"

    def test_seed_defaults(self, auth):
        service, repo, _db = auth
        service.seed_defaults()
        users, by_id = repo.list_all()
        assert len(by_id) == 2
        names = {u.username for u in users["costumer"] + users["officer"]}
        assert names == {"azarhajipour", "mahdihajipour"}
        officer = users["officer"][0]
        assert officer.role == "officer"
        assert is_hashed(officer.password)
        assert verify_password("4321", officer.password)
