"""Lookup only — no login or permission checks."""
from repository.user_repository import UserRepository


class UserService:
    def __init__(self, user_repo=None):
        self.user_repo = user_repo or UserRepository()

    def get(self, user_id):
        return self.user_repo.get(user_id)

    def get_by_username_or_email(self, identity):
        return self.user_repo.get_by_username_or_email(identity)

    def list_all(self):
        return self.user_repo.list_all()
