"""Password hashing helpers. Users.password stores bcrypt only."""
import re
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Full bcrypt string: $2a$/$2b$/$2x$/$2y$ + 2-digit cost + 53-char payload.
_BCRYPT_RE = re.compile(r"^\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}$")


def is_hashed(stored: str) -> bool:
    """True only for a complete bcrypt hash, not a loose $2b$ prefix."""
    if not stored or not isinstance(stored, str):
        return False
    return _BCRYPT_RE.match(stored) is not None


def hash_password(plain: str) -> str:
    if not plain:
        return ""
    return pwd_context.hash(plain)


def verify_password(plain: str, stored: str) -> bool:
    """Verify bcrypt; leftover plaintext compares as-is. No MD5."""
    if not plain or not stored:
        return False
    if is_hashed(stored):
        try:
            return pwd_context.verify(plain, stored)
        except Exception:
            return False
    return stored == plain
