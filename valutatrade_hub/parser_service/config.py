"""Конфигурация Parser Service."""

import os
from dataclasses import dataclass, field

from valutatrade_hub.core.currencies import (
    CryptoCurrency,
    FiatCurrency,
    list_currencies,
)


def _split_currencies() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Разделить известные валюты на фиатные и криптовалютные коды."""
    fiat: list[str] = []
    crypto: list[str] = []

    for code, currency in list_currencies().items():
        if isinstance(currency, FiatCurrency):
            fiat.append(code)
        elif isinstance(currency, CryptoCurrency):
            crypto.append(code)

    return tuple(sorted(fiat)), tuple(sorted(crypto))


_FIAT_CODES, _CRYPTO_CODES = _split_currencies()


@dataclass
class ParserConfig:
    """Настройки Parser Service."""

    # Ключ загружается из переменной окружения (не хранится в коде).
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")

    # Эндпоинты.
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Списки валют — из общего реестра currencies.py.
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple[str, ...] = _FIAT_CODES
    CRYPTO_CURRENCIES: tuple[str, ...] = _CRYPTO_CODES

    # Сопоставление кодов CoinGecko → ID монеты.
    CRYPTO_ID_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    # Пути к файлам данных.
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    # Сетевые параметры.
    REQUEST_TIMEOUT: int = 10

    # Интервал обновления для scheduler (секунды).
    UPDATE_INTERVAL_SECONDS: int = 300

    def get_api_key(self) -> str:
        """Вернуть API-ключ, выбросив ApiRequestError при его отсутствии."""
        from valutatrade_hub.core.exceptions import ApiRequestError

        if not self.EXCHANGERATE_API_KEY:
            raise ApiRequestError(
                "Не задан EXCHANGERATE_API_KEY. Установите переменную "
                "окружения перед запуском Parser Service."
            )
        return self.EXCHANGERATE_API_KEY