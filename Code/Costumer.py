"""Shim: Costumer is domain.user.User (same class object)."""
# REFACTOR-TRANSITION: keep Code.Costumer import path; Costumer is User (same class).
from domain.user import User as Costumer

__all__ = ["Costumer"]
