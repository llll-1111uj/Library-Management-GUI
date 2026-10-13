"""Officer constructor keeps role=officer. Methods live on domain.user.User."""
# REFACTOR-TRANSITION: keep a real Officer class for constructors and type(name).
# TODO: A4 阶段统一 User 类型。
from domain.user import User


class Officer(User):
    def __init__(self, first_name: str, last_name: str, username: str, password: str, email: str, phone: str) -> None:
        super().__init__(first_name, last_name, username, password, email, phone, role="officer")
