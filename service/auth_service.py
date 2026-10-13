"""Login, register, and default-account seeding."""
import logging
from re import search

from domain.exceptions import AuthError
from domain.password import is_hashed, verify_password
from domain.user import User
from repository.audit_repository import AuditRepository
from repository.user_repository import UserRepository

logger = logging.getLogger(__name__)

_EMAIL_RE = '^[A-Za-z0-9._%+-]+[@][A-Za-z0-9.-]+[A-Z|a-z]{2,3}$'


class AuthService:
    def __init__(self, user_repo=None, audit_repo=None):
        self.user_repo = user_repo or UserRepository()
        self.audit_repo = audit_repo or AuditRepository(getattr(self.user_repo, "db_path", None))

    def _validate_register(self, username, password, password_2, fullname, email, taken_usernames):
        if not username:
            raise AuthError("Username is empty !")
        if username in taken_usernames:
            raise AuthError("Username is already used !")
        if not password or not password_2:
            raise AuthError("Password is empty !")
        if not fullname:
            raise AuthError("Name is empty !")
        if password != password_2:
            raise AuthError("Passwords are not matching !")
        if email and not search(_EMAIL_RE, email):
            raise AuthError("Entered email is not valid !")

    def register(self, username, password, password_2, fullname, email, phone, role, taken_usernames):
        username = (username or "").lower()
        self._validate_register(username, password, password_2, fullname, email, taken_usernames)
        first_name = fullname.split(" ")[0]
        last_name = fullname.replace(first_name, "", 1)
        if role == "officer":
            # REFACTOR-TRANSITION: construct Officer, not a bare User, so memory lists stay typed.
            from Officer import Officer
            person = Officer(first_name, last_name, username, password, email, phone)
        else:
            person = User(first_name, last_name, username, password, email, phone, role="costumer")
        try:
            self.user_repo.upsert(person, role=person.role)
            action = "ADD_OFFICER" if role == "officer" else "REGISTER"
            self.audit_repo.add(person.user_id, action, "user", person.user_id, username)
        except Exception:
            logger.exception("register persist failed username=%s role=%s", username, role)
            raise
        logger.info("registered username=%s role=%s", username, person.role)
        return person

    def register_costumer(self, username, password, password_2, fullname, email, phone, taken_usernames):
        return self.register(
            username, password, password_2, fullname, email, phone, "costumer", taken_usernames
        )

    def register_officer(self, username, password, password_2, fullname, email, phone, taken_usernames):
        return self.register(
            username, password, password_2, fullname, email, phone, "officer", taken_usernames
        )

    def login(self, identity, password, users):
        identity = (identity or "").lower()
        if not identity:
            raise AuthError("Username/Email address is empty !")
        if not password:
            raise AuthError("Password is empty !")

        for entrance in users:
            identity_ok = entrance.username == identity or entrance.email == identity
            if not identity_ok or not verify_password(password, entrance.password):
                continue
            # Login upgrade is a second-line fallback; startup _normalize_passwords is primary.
            if not is_hashed(entrance.password):
                try:
                    entrance.password = password
                    self.user_repo.upsert(entrance, role=getattr(entrance, "role", None))
                    logger.info("upgraded plaintext password on login username=%s", entrance.username)
                except Exception:
                    logger.exception("login password upgrade failed username=%s", entrance.username)
                    raise
            logger.info("login ok username=%s", entrance.username)
            self.audit_repo.add(entrance.user_id, "LOGIN", "user", entrance.user_id, entrance.username)
            return entrance
        self.audit_repo.add(None, "LOGIN_FAILED", "user", None, identity)
        raise AuthError("Username/Email address or password incorrect !")

    def seed_defaults(self):
        costumer = User(
            "Azar", "Hajipuor", "azarhajipour", "1234", "azarhajipour@Gmail.Com", "09111234567",
            role="costumer",
        )
        # REFACTOR-TRANSITION: default admin must be an Officer instance.
        from Officer import Officer
        officer = Officer("Mahdi", "Hajipuor", "mahdihajipour", "4321", "mahdihajipour@gmail.com", "09117654321")
        try:
            self.user_repo.save_users({"costumer": [costumer], "officer": [officer]})
        except Exception:
            logger.exception("seed default accounts failed")
            raise
        logger.info("seeded default accounts")
        return {"costumer": [costumer], "officer": [officer]}
