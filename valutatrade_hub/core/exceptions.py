"""Пользовательские исключения ValutaTrade Hub."""


class ValutaTradeError(Exception):
    """Базовое исключение ValutaTrade Hub."""


class ValidationError(ValutaTradeError):
    """Данные неверные: занят логин, ошибка суммы и пр."""


class UserNotFoundError(ValutaTradeError):
    """Пользователь не найден."""

    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Пользователь '{username}' не найден")


class InvalidPasswordError(ValutaTradeError):
    """Пароль неправильный."""

    def __init__(self):
        super().__init__("Неверный пароль")


class InsufficientFundsError(ValutaTradeError):
    """На баланесе недостаточно средств."""

    def __init__(self, available: float, required: float, currency_code: str):
        self.available = available
        self.required = required
        self.currency_code = currency_code

        message = (
            f"Недостаточно средств: доступно {available:g} {currency_code}, "
            f"требуется {required:g} {currency_code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(ValutaTradeError):
    """Валюта отсутствует в списке известных."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'. Проверьте код валюты")


class ApiRequestError(ValutaTradeError):
    """Ошибка обращения к внешнему API."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")