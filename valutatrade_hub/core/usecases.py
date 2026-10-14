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

    # ------------------------------------------------------------------
    # Регистрация и вход
    # ------------------------------------------------------------------

    def register(self, username: str, password: str) -> User:
        """Зарегистрировать нового пользователя."""
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не должно быть пустым")
        if not isinstance(password, str) or len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        clean_username = username.strip()
        users = self._load_users()

        if any(user.get("username") == clean_username for user in users):
            raise ValueError(f"Имя пользователя '{clean_username}' уже занято")

        user_id = max(
            (int(user.get("user_id", 0)) for user in users),
            default=0,
        ) + 1

        user = User(user_id, clean_username, password)
        users.append(user.to_dict())
        self.database.save("users", users)

        portfolios = self._load_portfolios()
        portfolios.append({"user_id": user_id, "wallets": {}})
        self.database.save("portfolios", portfolios)

        return user

    def login(self, username: str, password: str) -> User:
        """Войти в приложение и установить текущего пользователя."""
        users = self._load_users()

        found: dict | None = None
        for user_data in users:
            if user_data.get("username") == username:
                found = user_data
                break

        if found is None:
            raise ValueError(f"Пользователь '{username}' не найден")

        user = User.from_dict(found)
        if not user.verify_password(password):
            raise ValueError("Неверный пароль")

        self.current_user = user
        return user

    # ------------------------------------------------------------------
    # Портфель
    # ------------------------------------------------------------------

    def get_portfolio(self) -> Portfolio:
        """Получить портфель текущего пользователя."""
        user = self._require_login()
        portfolios = self._load_portfolios()

        portfolio_data = self._find_portfolio(portfolios, user.user_id)
        if portfolio_data is None:
            portfolio_data = {"user_id": user.user_id, "wallets": {}}

        wallets: dict[str, Wallet] = {}
        for code, wallet_data in portfolio_data.get("wallets", {}).items():
            if isinstance(wallet_data, dict):
                balance = wallet_data.get("balance", 0.0)
            else:
                balance = wallet_data
            wallets[code] = Wallet(code, balance)

        return Portfolio(user.user_id, wallets, user)

    def show_portfolio(self, base_currency: str = "USD") -> dict[str, Any]:
        """Вернуть подготовленные строки и итог портфеля."""
        validate_currency_code(base_currency)

        portfolio = self.get_portfolio()
        rates = self._load_rates()

        rows: list[dict[str, Any]] = []
        total = 0.0

        for code, wallet in portfolio.wallets.items():
            try:
                value = convert_currency(
                    wallet.balance, code, base_currency, rates
                )
            except (ValueError, CurrencyNotFoundError):
                value = None

            if value is not None:
                total += value

            rows.append(
                {
                    "code": code,
                    "balance": wallet.balance,
                    "value": value,
                }
            )

        return {
            "username": portfolio.user.username if portfolio.user else "",
            "base_currency": base_currency.upper(),
            "rows": rows,
            "total_value": total,
        }

    # ------------------------------------------------------------------
    # Покупка / продажа
    # ------------------------------------------------------------------

    def buy(self, currency_code: str, amount: float) -> dict[str, Any]:
        """Купить валюту, увеличив её баланс в портфеле."""
        user = self._require_login()
        code = validate_currency_code(currency_code)
        amount = self._validate_amount(amount)

        portfolio = self.get_portfolio()
        wallet = portfolio.get_wallet(code)

        before = wallet.balance if wallet is not None else 0.0
        if wallet is None:
            wallet = portfolio.add_currency(code)

        wallet.deposit(amount)
        after = wallet.balance

        self._save_portfolio(portfolio)

        rate = self._get_rate_value(code, "USD")
        estimated_usd = amount * rate if rate is not None else None

        return {
            "action": "buy",
            "username": user.username,
            "currency": code,
            "amount": amount,
            "before": before,
            "after": after,
            "rate": rate,
            "estimated_usd": estimated_usd,
        }

    def sell(self, currency_code: str, amount: float) -> dict[str, Any]:
        """Продать валюту при наличии кошелька и достаточного баланса."""
        user = self._require_login()
        code = validate_currency_code(currency_code)
        amount = self._validate_amount(amount)

        portfolio = self.get_portfolio()
        wallet = portfolio.get_wallet(code)

        if wallet is None:
            raise ValueError(
                f"У вас нет кошелька '{code}'. "
                "Добавьте валюту: она создаётся автоматически "
                "при первой покупке."
            )

        before = wallet.balance
        wallet.withdraw(amount)
        after = wallet.balance

        self._save_portfolio(portfolio)

        rate = self._get_rate_value(code, "USD")
        estimated_usd = amount * rate if rate is not None else None

        return {
            "action": "sell",
            "username": user.username,
            "currency": code,
            "amount": amount,
            "before": before,
            "after": after,
            "rate": rate,
            "estimated_usd": estimated_usd,
        }

    # ------------------------------------------------------------------
    # Курсы
    # ------------------------------------------------------------------

    def get_rate(
        self,
        from_currency: str,
        to_currency: str = "USD",
    ) -> dict[str, Any]:
        """Получить прямой и обратный курсы валют."""
        source = validate_currency_code(from_currency)
        target = validate_currency_code(to_currency)

        rates_data = self.database.load("rates", {})
        pairs = rates_data.get("pairs", rates_data)

        raw_rate = self._find_rate(pairs, source, target)

        if raw_rate is None:
            raise ApiRequestError(
                f"Курс {source}→{target} недоступен. "
                "Повторите попытку позже или выполните update-rates."
            )

        updated_at = self._find_updated_at(pairs, source, target)

        inverse_raw = 1 / raw_rate

        return {
            "from_currency": source,
            "to_currency": target,
            "rate": round(raw_rate, 8),
            "inverse_rate": round(inverse_raw, 2)
            if inverse_raw >= 1
            else round(inverse_raw, 8),
            "updated_at": updated_at,
        }

    # ------------------------------------------------------------------
    # Приватные помощники
    # ------------------------------------------------------------------

    def _require_login(self) -> User:
        """Вернуть текущего пользователя или сообщить об отсутствии входа."""
        if self.current_user is None:
            raise ValueError("Сначала выполните login")
        return self.current_user

    @staticmethod
    def _validate_amount(amount: float) -> float:
        """Проверить, что сумма является положительным числом."""
        if (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or amount <= 0
        ):
            raise ValueError("'amount' должен быть положительным числом")
        return float(amount)

    def _load_users(self) -> list:
        """Загрузить список пользователей."""
        users = self.database.load("users", [])
        if isinstance(users, dict):
            users = list(users.values())
        return users

    def _load_portfolios(self) -> list:
        """Загрузить список портфелей."""
        portfolios = self.database.load("portfolios", [])
        if isinstance(portfolios, dict):
            portfolios = list(portfolios.values())
        return portfolios

    @staticmethod
    def _find_portfolio(portfolios: list, user_id: int) -> dict | None:
        """Найти портфель по user_id в списке."""
        for portfolio in portfolios:
            if int(portfolio.get("user_id", -1)) == user_id:
                return portfolio
        return None

    def _save_portfolio(self, portfolio: Portfolio) -> None:
        """Сохранить кошельки портфеля в portfolios.json (список)."""
        portfolios = self._load_portfolios()
        new_entry = {
            "user_id": portfolio.user_id,
            "wallets": {
                code: wallet.get_balance_info()
                for code, wallet in portfolio.wallets.items()
            },
        }

        for index, entry in enumerate(portfolios):
            if int(entry.get("user_id", -1)) == portfolio.user_id:
                portfolios[index] = new_entry
                break
        else:
            portfolios.append(new_entry)

        self.database.save("portfolios", portfolios)

    def _load_rates(self) -> dict:
        """Загрузить курсы и вернуть словарь пар."""
        data = self.database.load("rates", {})
        return data.get("pairs", data)

    def _get_rate_value(self, source: str, target: str) -> float | None:
        """Получить курс source→target без исключений."""
        try:
            rates = self._load_rates()
            return self._find_rate(rates, source, target)
        except Exception:
            return None

    def _find_rate(
        self,
        rates: dict,
        source: str,
        target: str,
    ) -> float | None:
        """Найти курс прямой или обратной пары через USD."""
        if source == target:
            return 1.0

        direct = rates.get(f"{source}_{target}")
        if direct is not None:
            value = direct.get("rate") if isinstance(direct, dict) else direct
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if value > 0:
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

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if value > 0:
                return float(value)

        return None

    @staticmethod
    def _find_updated_at(rates: dict, source: str, target: str) -> str:
        """Найти метку updated_at для пары, если есть."""
        for pair in (f"{source}_{target}", f"{target}_{source}"):
            entry = rates.get(pair)
            if isinstance(entry, dict) and "updated_at" in entry:
                return str(entry["updated_at"])
        return datetime.now(timezone.utc).isoformat()