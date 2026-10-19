"""Обновление курсов валют из всех источников Parser Service."""

from typing import Any

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import Storage

_logger = get_logger("valutatrade_hub.parser")


class RatesUpdater:
    """Точка входа для обновления курсов из всех источников."""

    def __init__(
        self,
        config: ParserConfig,
        clients: list[tuple[str, BaseApiClient]],
        storage: Storage,
    ) -> None:
        self.config = config
        self.clients = clients
        self.storage = storage

    def run_update(self) -> dict[str, Any]:
        """Обновить курсы из всех источников."""
        _logger.info("Начато обновление...")

        errors: list[dict[str, str]] = []
        success_sources: list[str] = []
        by_source: dict[str, dict[str, float]] = {}

        for source_name, client in self.clients:
            _logger.info("Получение данных %s...", source_name)

            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                _logger.error(
                    "Не удалось получить данные от %s: %s",
                    source_name,
                    error,
                )
                errors.append({"source": source_name, "error": str(error)})
                continue
            except Exception as error:
                _logger.exception("Неизвестная ошибка: %s.", source_name)
                errors.append({"source": source_name, "error": str(error)})
                continue

            if not rates:
                _logger.warning("%s: пустой ответ.", source_name)
                errors.append({
                    "source": source_name,
                    "error": "пустой ответ от источника",
                })
                continue

            _logger.info(
                "Получение данных от %s... OK (%s rates)",
                source_name,
                len(rates),
            )
            success_sources.append(source_name)
            by_source[source_name] = rates

        if not success_sources:
            _logger.error("API-клиенты недоступны, обновление отменено.")
            raise ApiRequestError(
                "Не удалось обновить курсы: все источники недоступны."
            )

        total_updated = 0
        for source_name, rates in by_source.items():
            count = self.storage.save(rates, source_name)
            total_updated += count

        snapshot = self.storage.load_rates()
        last_refresh = snapshot.get("last_refresh")

        result = {
            "count_updated": total_updated,
            "last_refresh": last_refresh,
            "errors": errors,
            "sources": success_sources,
        }

        _logger.info(
            "Обновление завершено. Обновлено=%s, ошибок=%s",
            total_updated,
            len(errors),
        )
        return result