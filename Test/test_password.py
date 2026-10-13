import os
from sys import path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CODE = os.path.join(_ROOT, "Code")
path.insert(1, _ROOT)
path.insert(1, _CODE)

from domain.password import hash_password, is_hashed, verify_password


class TestPasswordHash:
    def test_hash_is_bcrypt_not_plaintext(self):
        hashed = hash_password("secret-123")
        assert hashed != "secret-123"
        assert is_hashed(hashed)
        assert hashed.startswith("$2")
        assert verify_password("secret-123", hashed)
        assert not verify_password("wrong", hashed)

    def test_loose_prefix_is_not_hashed(self):
        assert not is_hashed("$2b$")
        assert not is_hashed("md5-not-used")
        assert not is_hashed("")

    def test_plaintext_verify_fallback_no_md5(self):
        assert verify_password("1234", "1234")
        assert not verify_password("1234", "81dc9bdb52d04dc20036dbd8313ed055")
