"""Shim: password helpers live in domain.password."""
# REFACTOR-TRANSITION: Code.Password re-exports domain.password.
from domain.password import hash_password, is_hashed, verify_password, pwd_context

__all__ = ["hash_password", "is_hashed", "verify_password", "pwd_context"]
