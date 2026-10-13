"""User persistence via repository.connection."""
import logging

from domain.user import User
from repository.connection import get_connection, init_database

logger = logging.getLogger(__name__)


def resolve_role(person, role=None):
    if role in ("officer", "costumer"):
        return role
    stored = getattr(person, "role", None)
    if stored in ("officer", "costumer"):
        return stored
    # REFACTOR-TRANSITION: fall back to Officer class name when role is missing.
    return "officer" if type(person).__name__ == "Officer" else "costumer"


def upsert_user_on_conn(conn, person, role=None):
    role = resolve_role(person, role)
    person.role = role
    cur = conn.cursor()
    user_id = getattr(person, "user_id", None)
    if not user_id:
        row = cur.execute(
            "SELECT user_id FROM Users WHERE username=?",
            (person.username,),
        ).fetchone()
        if row:
            user_id = row[0]
            person.user_id = user_id
    values = [
        person.first_name,
        person.last_name,
        person.username,
        person.password,
        person.email,
        person.phone,
        role,
    ]
    try:
        if user_id:
            cur.execute(
                """UPDATE Users SET first_name=?, last_name=?, username=?, password=?,
                   email=?, phone=?, role=? WHERE user_id=?""",
                values + [user_id],
            )
        else:
            cur.execute(
                """INSERT INTO Users(first_name, last_name, username, password, email, phone, role)
                   VALUES(?,?,?,?,?,?,?)""",
                values,
            )
            person.user_id = cur.lastrowid
    except Exception:
        logger.exception("upsert user failed username=%s", person.username)
        raise
    return person.user_id


class UserRepository:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def _conn(self):
        return get_connection(self.db_path)

    def ensure_schema(self):
        conn = init_database(self.db_path)
        conn.close()

    def list_all(self):
        # REFACTOR-TRANSITION: reload officers as Officer, not User.
        from Officer import Officer

        try:
            conn = self._conn()
            rows = conn.execute(
                """SELECT user_id, first_name, last_name, username, password, email, phone, role
                   FROM Users"""
            ).fetchall()
            conn.close()
        except Exception:
            logger.exception("load users failed")
            raise

        result = {"costumer": [], "officer": []}
        by_id = {}
        for user_id, first_name, last_name, username, password, email, phone, role in rows:
            if role == "officer":
                person = Officer(first_name, last_name, username, password, email or "", phone or "")
                result["officer"].append(person)
            else:
                person = User(first_name, last_name, username, password, email or "", phone or "", role="costumer")
                result["costumer"].append(person)
            person.user_id = user_id
            person.role = role or "costumer"
            by_id[user_id] = person
        logger.info("loaded %s users", len(by_id))
        return result, by_id

    def upsert(self, person, role=None, conn=None):
        close_after = False
        if conn is None:
            conn = self._conn()
            close_after = True
        try:
            user_id = upsert_user_on_conn(conn, person, role)
            if close_after:
                conn.commit()
            return user_id
        except Exception:
            if close_after:
                conn.rollback()
            raise
        finally:
            if close_after:
                conn.close()

    def save_users(self, users_map):
        conn = self._conn()
        try:
            for person in users_map.get("costumer", []):
                upsert_user_on_conn(conn, person, "costumer")
            for person in users_map.get("officer", []):
                upsert_user_on_conn(conn, person, "officer")
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("save users failed")
            raise
        finally:
            conn.close()
