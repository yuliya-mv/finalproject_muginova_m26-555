"""API-клиенты Parser Service."""

from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.config import CRYPTO_ID_MAP, ParserConfig

_logger = get_logger("valutatrade_hub.parser")


class BaseApiClient(ABC):
    """Базовый класс для всех API-клиентов Parser Service."""

    def __init__(self, config: ParserConfig) -> None:
        self.config = config
        self.timeout = config.REQUEST_TIMEOUT

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Получить курсы в стандартизированном формате: {"BTC_USD": 59.21, ...}."""


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko — получает курсы криптовалют к USD."""

    def fetch_rates(self) -> dict[str, float]:
        """Запросить курсы криптовалют у CoinGecko."""
        codes = list(self.config.CRYPTO_CURRENCIES)
        ids = [
            CRYPTO_ID_MAP[code]
            for code in codes
            if code in CRYPTO_ID_MAP
        ]

        if not ids:
            _logger.debug("CoinGecko: нет криптовалют для запроса.")
            return {}

        params = {
            "ids": ",".join(ids),
            "vs_currencies": self.config.BASE_CURRENCY.lower(),
        }

        _logger.debug(
            "CoinGecko: GET %s params=%s",
            self.config.COINGECKO_URL,
            params,
        )

        try:
            response = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as error:
            _logger.exception("CoinGecko: ошибка сети.")
            raise ApiRequestError(
                f"CoinGecko: ошибка сети ({error})"
            ) from error

        if response.status_code != 200:
            _logger.error(
                "CoinGecko: HTTP %s — %s",
                response.status_code,
                response.text[:200],
            )
            raise ApiRequestError(
                f"CoinGecko: HTTP {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as error:
            _logger.exception("CoinGecko: некорректный JSON.")
            raise ApiRequestError(
                "CoinGecko: некорректный JSON."
            ) from error

        base = self.config.BASE_CURRENCY.upper()
        result: dict[str, float] = {}

        for code in codes:
            coin_id = CRYPTO_ID_MAP.get(code)
            if coin_id is None:
                continue

            entry = payload.get(coin_id)
            if not isinstance(entry, dict):
                continue

            rate = entry.get(self.config.BASE_CURRENCY.lower())
            if isinstance(rate, (int, float)) and not isinstance(rate, bool):
                result[f"{code}_{base}"] = float(rate)

        _logger.debug("CoinGecko: получено %s курсов.", len(result))
        return result


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API — получает курсы фиатных валют к USD"""

    def fetch_rates(self) -> dict[str, float]:
        """Получить курсы фиатных валют через ExchangeRate-API."""
        api_key = self.config.get_api_key()
        base = self.config.BASE_CURRENCY.upper()
        url = (
            f"{self.config.EXCHANGERATE_API_URL}/{api_key}"
            f"/latest/{base}"
        )

        _logger.debug("ExchangeRate-API: GET %s", url)

        try:
            response = requests.get(url, timeout=self.timeout)
        except requests.exceptions.RequestException as error:
            _logger.exception("ExchangeRate-API: ошибка сети.")
            raise ApiRequestError(
                f"ExchangeRate-API: ошибка сети ({error})"
            ) from error

        if response.status_code != 200:
            _logger.error(
                "ExchangeRate-API: HTTP %s — %s",
                response.status_code,
                response.text[:200],
            )
            raise ApiRequestError(
                f"ExchangeRate-API: HTTP {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as error:
            _logger.exception("ExchangeRate-API: некорректный JSON.")
            raise ApiRequestError(
                "ExchangeRate-API: некорректный JSON."
            ) from error

        if payload.get("result") != "success":
            _logger.error(
                "ExchangeRate-API: ответ с ошибкой: %s",
                payload.get("error-type", "unknown"),
            )
            raise ApiRequestError(
                "ExchangeRate-API: ответ с ошибкой "
                f"({payload.get('error-type', 'unknown')})"
            )

        conversion_rates = payload.get("conversion_rates", {})
        if not isinstance(conversion_rates, dict):
            raise ApiRequestError(
                "ExchangeRate-API: нет conversion_rates"
            )

        result: dict[str, float] = {}

        for code in self.config.FIAT_CURRENCIES:
            if code == base:
                continue

            raw = conversion_rates.get(code)
            if (
                not isinstance(raw, (int, float))
                or isinstance(raw, bool)
                or raw <= 0
            ):
                continue

            result[f"{code}_{base}"] = 1.0 / float(raw)

        _logger.debug(
            "ExchangeRate-API: получено %s курсов.", len(result)
        )
        return result