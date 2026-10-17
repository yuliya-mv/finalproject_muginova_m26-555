"""Пользовательские исключения приложения ValutaTrade Hub."""


class ValutaTradeError(Exception):
    """Базовое исключение приложения ValutaTrade Hub."""


class ValidationError(ValutaTradeError):
    """Ошибка валидации входных данных."""


class UserNotFoundError(ValutaTradeError):
    """Пользователь не найден."""

    def __init__(self, username: str) -> None:
        """Создать исключение для отсутствующего пользователя."""
        self.username = username
        super().__init__(f"Пользователь '{username}' не найден")


class InvalidPasswordError(ValutaTradeError):
    """Неверный пароль."""

    def __init__(self, message: str = "Неверный пароль") -> None:
        """Создать исключение о неверном пароле."""
        super().__init__(message)


class InsufficientFundsError(ValutaTradeError):
    """Исключение при недостаточном балансе кошелька."""

    def __init__(
        self,
        available: float,
        required: float,
        currency_code: str,
    ) -> None:
        """Создать исключение с доступной и требуемой суммами."""
        self.available = available
        self.required = required
        self.currency_code = currency_code

        message = (
            f"Недостаточно средств: доступно {available:g} {currency_code}, "
            f"требуется {required:g} {currency_code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(ValutaTradeError):
    """Исключение при обращении к неизвестной валюте."""

    def __init__(self, code: str) -> None:
        """Создать исключение для неизвестного кода валюты."""
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(ValutaTradeError):
    """Исключение при ошибке обращения к внешнему API."""

    def __init__(self, reason: str) -> None:
        """Создать исключение с описанием причины ошибки."""
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")