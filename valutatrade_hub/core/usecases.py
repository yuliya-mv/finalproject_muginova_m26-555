
"""Бизнес-операции приложения ValutaTrade Hub."""

from datetime import datetime, timezone
from typing import Any

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import convert_currency, validate_currency_code
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader


class ValutaTradeService:
    """Выполнение операций с пользователями, портфелями и курсами."""

    def __init__(self) -> None:
        """Подготовить доступ к настройкам и хранилищу."""
        self.database = DatabaseManager()
        self.settings = SettingsLoader()
        self.current_user: User | None = None

    def register(self, username: str, password: str) -> User:
        """Зарегистрировать нового пользователя."""
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не должно быть пустым")
        if not isinstance(password, str) or len(password) < 4:
            raise ValueError("Пароль должен содержать не менее 4 символов")

        users = self.database.load("users", [])
        if isinstance(users, dict):
            users = list(users.values())

        if any(user.get("username") == username.strip() for user in users):
            raise ValueError("Пользователь с таким именем уже существует")

        user_id = max(
            (int(user.get("user_id", 0)) for user in users),
            default=0,
        ) + 1

        user = User(user_id, username.strip(), password)
        users.append(user.to_dict())
        self.database.save("users", users)

        portfolios = self.database.load("portfolios", {})
        if not isinstance(portfolios, dict):
            portfolios = {}

        portfolios[str(user_id)] = {"user_id": user_id, "wallets": {}}
        self.database.save("portfolios", portfolios)

        return user

    def login(self, username: str, password: str) -> User:
        """Войти в приложение и установить текущего пользователя."""
        users = self.database.load("users", [])
        if isinstance(users, dict):
            users = list(users.values())

        for user_data in users:
            if user_data.get("username") != username:
                continue

            user = User.from_dict(user_data)
            if user.verify_password(password):
                self.current_user = user
                return user

            break

        raise ValueError("Неверное имя пользователя или пароль")

    def logout(self) -> None:
        """Завершить текущую пользовательскую сессию."""
        self.current_user = None

    def get_portfolio(self) -> Portfolio:
        """Получить портфель текущего пользователя."""
        user = self._require_login()
        portfolios = self.database.load("portfolios", {})
        portfolio_data = portfolios.get(str(user.user_id), {})

        wallets: dict[str, Wallet] = {}
        for code, wallet_data in portfolio_data.get("wallets", {}).items():
            if isinstance(wallet_data, dict):
                balance = wallet_data.get("balance", 0.0)
            else:
                balance = wallet_data
            wallets[code] = Wallet(code, balance)

        return Portfolio(user.user_id, wallets, user)

    def show_portfolio(self, base_currency: str = "USD") -> dict[str, Any]:
        """Вернуть кошельки и общую стоимость портфеля."""
        portfolio = self.get_portfolio()
        rates = self._load_rates()
        total = portfolio.get_total_value(base_currency, rates)
        return {
            "wallets": portfolio.wallets,
            "base_currency": base_currency.upper(),
            "total_value": total,
        }

    def buy(self, currency_code: str, amount: float) -> dict[str, Any]:
        """Купить валюту, увеличив её баланс в портфеле."""
        user = self._require_login()
        code = validate_currency_code(currency_code)
        amount = self._validate_amount(amount)

        portfolio = self.get_portfolio()
        wallet = portfolio.get_wallet(code)
        if wallet is None:
            wallet = portfolio.add_currency(code)

        wallet.deposit(amount)
        self._save_portfolio(portfolio)

        usd_value = self._estimate_usd(code, amount)
        return {
            "action": "buy",
            "username": user.username,
            "currency": code,
            "amount": amount,
            "estimated_usd": usd_value,
        }

    def sell(self, currency_code: str, amount: float) -> dict[str, Any]:
        """Продать валюту при наличии кошелька и достаточного баланса."""
        user = self._require_login()
        code = validate_currency_code(currency_code)
        amount = self._validate_amount(amount)

        portfolio = self.get_portfolio()
        wallet = portfolio.get_wallet(code)
        if wallet is None:
            raise InsufficientFundsError(0.0, amount, code)

        wallet.withdraw(amount)
        self._save_portfolio(portfolio)

        usd_value = self._estimate_usd(code, amount)
        return {
            "action": "sell",
            "username": user.username,
            "currency": code,
            "amount": amount,
            "estimated_usd": usd_value,
        }

    def get_rate(
        self,
        from_currency: str,
        to_currency: str = "USD",
    ) -> dict[str, Any]:
        """Получить прямой и обратный курсы валют."""
        source = validate_currency_code(from_currency)
        target = validate_currency_code(to_currency)
        rates_data = self.database.load("rates", {})
        rates = rates_data.get("pairs", rates_data)

        direct_rate = self._find_rate(rates, source, target)
        if direct_rate is None:
            raise ApiRequestError(
                f"Курс {source}/{target} отсутствует в локальном хранилище. "
                "Попробуйте обновить курсы и повторить запрос."
            )

        return {
            "from_currency": source,
            "to_currency": target,
            "rate": direct_rate,
            "inverse_rate": round(1 / direct_rate, 8),
        }

    def _require_login(self) -> User:
        """Вернуть текущего пользователя или сообщить об отсутствии входа."""
        if self.current_user is None:
            raise ValueError("Сначала войдите в систему")
        return self.current_user

    @staticmethod
    def _validate_amount(amount: float) -> float:
        """Проверить, что сумма является положительным числом."""
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or amount <= 0
        ):
            raise ValueError("Сумма должна быть положительным числом")
        return float(amount)

    def _load_rates(self) -> dict:
        """Загрузить курсы и привести их к формату пар."""
        data = self.database.load("rates", {})
        return data.get("pairs", data)

    def _find_rate(
        self,
        rates: dict,
        source: str,
        target: str,
    ) -> float | None:
        """Найти курс прямой или обратной пары."""
        if source == target:
            return 1.0

        direct = rates.get(f"{source}_{target}")
        if direct is not None:
            value = direct.get("rate") if isinstance(direct, dict) else direct
            if isinstance(value, (int, float)) and value > 0:
                return float(value)

        source_usd = self._usd_rate(rates, source)
        target_usd = self._usd_rate(rates, target)

        if source_usd is not None and target_usd is not None:
            return source_usd / target_usd

        return None

    @staticmethod
    def _usd_rate(rates: dict, currency_code: str) -> float | None:
        """Получить курс валюты к USD."""
        if currency_code == "USD":
            return 1.0

        value = rates.get(f"{currency_code}_USD")
        if isinstance(value, dict):
            value = value.get("rate")

        if isinstance(value, (int, float)) and value > 0:
            return float(value)

        return None

    def _estimate_usd(self, currency_code: str, amount: float) -> float | None:
        """Оценить сумму в USD, если курс доступен."""
        try:
            rates = self._load_rates()
            return convert_currency(amount, currency_code, "USD", rates)
        except (ValueError, CurrencyNotFoundError):
            return None

    def _save_portfolio(self, portfolio: Portfolio) -> None:
        """Сохранить кошельки портфеля текущего пользователя."""
        portfolios = self.database.load("portfolios", {})
        portfolios[str(portfolio.user_id)] = {
            "user_id": portfolio.user_id,
            "wallets": {
                code: wallet.get_balance_info()["balance"]
                for code, wallet in portfolio.wallets.items()
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.database.save("portfolios", portfolios)
