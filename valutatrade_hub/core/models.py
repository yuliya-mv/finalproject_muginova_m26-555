"""Модели пользователя, кошелька и портфеля."""

import hashlib
import secrets
from datetime import datetime


class User:
    """Пользователь приложения."""

    def __init__(
        self,
        user_id: int,
        username: str,
        password: str,
        registration_date: datetime | None = None,
    ) -> None:
        """Создать пользователя и сохранить пароль в хешированном виде."""
        self._user_id = user_id
        self._username = username
        self._salt = secrets.token_hex(16)
        self._hashed_password = self._hash_password(password, self._salt)
        self._registration_date = registration_date or datetime.now()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Получить SHA-256 хеш пароля с солью."""
        return hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()

    @property
    def user_id(self) -> int:
        """Вернуть идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Вернуть имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Проверить и изменить имя пользователя."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не должно быть пустым")
        self._username = value.strip()

    @property
    def registration_date(self) -> datetime:
        """Вернуть дату регистрации."""
        return self._registration_date

    def verify_password(self, password: str) -> bool:
        """Проверить соответствие пароля сохранённому хешу."""
        if not isinstance(password, str):
            return False
        return secrets.compare_digest(
            self._hashed_password,
            self._hash_password(password, self._salt),
        )

    def change_password(self, new_password: str) -> None:
        """Изменить пароль, создав новую соль."""
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен содержать не менее 4 символов")

        self._salt = secrets.token_hex(16)
        self._hashed_password = self._hash_password(new_password, self._salt)

    def get_user_info(self) -> dict:
        """Вернуть данные пользователя без пароля и соли."""
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
        """Восстановить пользователя из словаря."""
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

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        """Создать кошелёк с начальным балансом."""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не должен быть пустым")

        self.currency_code = currency_code.strip().upper()
        self._balance = 0.0
        self.balance = balance

    @property
    def balance(self) -> float:
        """Вернуть текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Проверить и изменить баланс."""
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or value < 0
        ):
            raise ValueError("Баланс должен быть неотрицательным числом")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополнить кошелёк положительной суммой."""
        self._validate_amount(amount)
        self.balance = self.balance + amount

    def withdraw(self, amount: float) -> None:
        """Снять средства при достаточном балансе."""
        from valutatrade_hub.core.exceptions import InsufficientFundsError

        self._validate_amount(amount)

        if amount > self.balance:
            raise InsufficientFundsError(
                self.balance, amount, self.currency_code
            )

        self.balance = self.balance - amount

    @staticmethod
    def _validate_amount(amount: float) -> None:
        """Проверить, что сумма является положительным числом."""
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or amount <= 0
        ):
            raise ValueError("Сумма должна быть положительным числом")

    def get_balance_info(self) -> dict:
        """Вернуть код валюты и текущий баланс."""
        return {
            "currency_code": self.currency_code,
            "balance": self.balance,
        }


class Portfolio:
    """Портфель пользователя с набором валютных кошельков."""

    def __init__(
        self,
        user_id: int,
        wallets: dict[str, Wallet] | None = None,
        user: User | None = None,
    ) -> None:
        """Создать портфель и скопировать переданные кошельки."""
        self._user_id = user_id
        self._wallets = dict(wallets) if wallets is not None else {}
        self._user = user

    @property
    def user_id(self) -> int:
        """Вернуть идентификатор владельца портфеля."""
        return self._user_id

    @property
    def user(self) -> User | None:
        """Вернуть связанного пользователя."""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Вернуть копию словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавить кошелёк для валюты, если его ещё нет."""
        code = currency_code.strip().upper()

        if not code:
            raise ValueError("Код валюты не должен быть пустым")

        if code not in self._wallets:
            self._wallets[code] = Wallet(code)

        return self._wallets[code]

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """Найти кошелёк по коду валюты."""
        return self._wallets.get(currency_code.strip().upper())

    def get_total_value(
        self,
        base_currency: str = "USD",
        rates: dict | None = None,
    ) -> float:
        """Рассчитать общую стоимость портфеля в выбранной валюте."""
        from valutatrade_hub.core.currencies import get_currency

        get_currency(base_currency)

        if rates is None:
            exchange_rates = {
                "USD_USD": 1.0,
                "EUR_USD": 1.08,
                "GBP_USD": 1.27,
                "RUB_USD": 0.01,
                "BTC_USD": 60000.0,
                "ETH_USD": 3000.0,
                "SOL_USD": 150.0,
            }
        else:
            exchange_rates = rates

        normalized_base = base_currency.strip().upper()
        if normalized_base == "USD":
            base_usd_rate = 1.0
        else:
            base_key = f"{normalized_base}_USD"
            base_usd_rate = self._extract_rate(exchange_rates, base_key)

        total_usd = 0.0

        for code, wallet in self._wallets.items():
            if code == "USD":
                total_usd += wallet.balance
                continue

            usd_rate = self._extract_rate(exchange_rates, f"{code}_USD")
            total_usd += wallet.balance * usd_rate

        return total_usd / base_usd_rate

    @staticmethod
    def _extract_rate(rates: dict, pair: str) -> float:
        """Извлечь курс пары из поддерживаемого формата данных."""
        from valutatrade_hub.core.exceptions import CurrencyNotFoundError

        value = rates.get(pair)

        if isinstance(value, dict):
            value = value.get("rate")

        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or value <= 0
        ):
            raise CurrencyNotFoundError(pair.removesuffix("_USD"))

        return float(value)
