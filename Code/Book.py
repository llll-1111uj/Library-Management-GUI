"""Shim: Book is domain.book.Book (same class object)."""
# REFACTOR-TRANSITION: keep Code.Book import path.
from domain.book import Book

__all__ = ["Book"]
