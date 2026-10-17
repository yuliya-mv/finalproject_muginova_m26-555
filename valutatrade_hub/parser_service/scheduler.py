"""Планировщик периодического обновления курсов."""

import time

from valutatrade_hub.logging_config import get_logger, setup_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import Storage
from valutatrade_hub.parser_service.updater import RatesUpdater


_logger = get_logger("valutatrade_hub.parser")


def build_updater(config: ParserConfig) -> RatesUpdater:
    """Собрать RatesUpdater с обоими клиентами."""
    clients = [
        ("CoinGecko", CoinGeckoClient(config)),
        ("ExchangeRate-API", ExchangeRateApiClient(config)),
    ]
    return RatesUpdater(
        config=config,
        clients=clients,
        storage=Storage(config),
    )


def run_forever(interval_seconds: int | None = None) -> None:
    """Бесконечно обновлять курсы с заданным интервалом."""
    config = ParserConfig()
    interval = interval_seconds or config.UPDATE_INTERVAL_SECONDS
    updater = build_updater(config)

    _logger.info(
        "Scheduler started, interval=%s сек.", interval
    )

    while True:
        try:
            updater.run_update()
        except Exception as error:  # noqa: BLE001
            _logger.exception("Scheduler update failed: %s", error)

        _logger.info("Scheduler: ожидание %s сек.", interval)
        time.sleep(interval)


def main() -> None:
    """Точка входа для запуска планировщика."""
    setup_logging()
    try:
        run_forever()
    except KeyboardInterrupt:
        _logger.info("Scheduler остановлен пользователем.")


if __name__ == "__main__":
    main()