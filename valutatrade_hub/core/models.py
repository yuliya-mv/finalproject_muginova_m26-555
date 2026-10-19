"""Модели пользователя, кошелька и портфеля."""

import hashlib
import secrets
from datetime import datetime, timezone


class User:
    """Пользователь приложения."""

    def __init__(
        self,
        user_id: int,
        username: str,
        password: str,
        registration_date: datetime | None = None,
    ):
        """Создать пользователя и сохранить пароль в хешированном виде."""
        self._validate_user_id(user_id)

        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не должно быть пустым")
        if not isinstance(password, str) or len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        self._user_id = user_id
        self._username = username.strip()
        self._salt = secrets.token_hex(16)
        self._hashed_password = self._hash_password(password, self._salt)
        self._registration_date = registration_date or datetime.now(
            timezone.utc
        )

    @staticmethod
    def _hash_password(password: str, salt: str):
        return hashlib.sha256(
            (password + salt).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _validate_user_id(value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("user_id должен быть целым числом")
        if value <= 0:
            raise ValueError("user_id должен быть положительным")

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value: str):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не должно быть пустым")
        self._username = value.strip()

    @property
    def password(self):
        raise AttributeError("Пароль недоступен для чтения")

    @password.setter
    def password(self, new_password: str):
        self.change_password(new_password)

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def verify_password(self, password: str):
        if not isinstance(password, str):
            return False
        return secrets.compare_digest(
            self._hashed_password,
            self._hash_password(password, self._salt),
        )

    def change_password(self, new_password: str):
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        self._salt = secrets.token_hex(16)
        self._hashed_password = self._hash_password(
            new_password, self._salt
        )

    def get_user_info(self) -> dict:
        """Вывести данные пользователя без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def to_dict(self) -> dict:
        """Подготовить данные пользователя для сохранения в JSON."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Восстановить данные пользователя."""
        user = cls.__new__(cls)
        user._user_id = int(data["user_id"])
        user._username = data["username"]
        user._hashed_password = data["hashed_password"]
        user._salt = data["salt"]
        user._registration_date = datetime.fromisoformat(
            data["registration_date"]
        )
        return user


class Wallet:
    """Кошелёк для хранения одной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не должен быть пустым")

        self.currency_code = currency_code.strip().upper()
        self._balance = 0.0
        self.balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value < 0
        ):
            raise ValueError("Баланс должен быть 0 или больше")
        self._balance = float(value)

    def deposit(self, amount: float):
        self._validate_amount(amount)
        self.balance = self.balance + amount

    def withdraw(self, amount: float):
        from valutatrade_hub.core.exceptions import InsufficientFundsError

        self._validate_amount(amount)

        if amount > self.balance:
            raise InsufficientFundsError(
                self.balance, amount, self.currency_code
            )

        self.balance = self.balance - amount

    @staticmethod
    def _validate_amount(value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("amount должен быть числом")

        if value <= 0:
            raise ValueError("amount должен быть положительным")

    def get_balance_info(self) -> dict:
        return {
            "currency_code": self.currency_code,
            "balance": self.balance,
        }


class Portfolio:
    """Портфель пользователя."""

    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
        user: User | None = None,
    ):
        self._user_id = user_id
        self._wallets = dict(wallets) if wallets is not None else {}
        self._user = user

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def user(self) -> User | None:
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        code = currency_code.strip().upper()

        if not code:
            raise ValueError("Код валюты не должен быть пустым")

        if code not in self._wallets:
            self._wallets[code] = Wallet(code)

        return self._wallets[code]

    def get_wallet(self, currency_code: str) -> Wallet | None:
        return self._wallets.get(currency_code.strip().upper())

    def get_total_value(
        self,
        base_currency: str = "USD",
        rates: dict | None = None,
    ) -> float:
        """Рассчитать общую стоимость портфеля в выбранной валюте."""
        from valutatrade_hub.core.currencies import get_currency
        from valutatrade_hub.core.utils import EXCHANGE_RATES, convert_currency

        get_currency(base_currency)

        exchange_rates = rates if rates is not None else EXCHANGE_RATES
        normalized_base = base_currency.strip().upper()

        total = 0.0
        for code, wallet in self._wallets.items():
            total += convert_currency(
                wallet.balance, code, normalized_base, exchange_rates
            )

        return total