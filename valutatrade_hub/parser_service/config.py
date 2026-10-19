"""Конфигурация Parser Service."""

import os
from dataclasses import dataclass

CRYPTO_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}


@dataclass
class ParserConfig:
    """Параметры Parser Service."""

    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")

    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    REQUEST_TIMEOUT: int = 10
    UPDATE_INTERVAL_SECONDS: int = 300

    def get_api_key(self) -> str:
        return self.EXCHANGERATE_API_KEY or ""