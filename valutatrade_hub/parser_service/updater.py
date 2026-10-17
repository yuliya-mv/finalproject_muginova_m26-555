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
        """Сохранить конфигурацию, клиентов и хранилище.

        :param clients: список пар (имя_источника, клиент).
        """
        self.config = config
        self.clients = clients
        self.storage = storage

    def run_update(self) -> dict[str, Any]:
        """Обновить курсы из всех источников.

        Возвращает словарь:
            {
                "count_updated": int,
                "last_refresh": str | None,
                "errors": list[dict],
                "sources": list[str],
            }

        Если упали все клиенты — бросает ApiRequestError.
        """
        _logger.info("Starting rates update...")

        errors: list[dict[str, str]] = []
        success_sources: list[str] = []
        combined: dict[str, float] = {}
        by_source: dict[str, dict[str, float]] = {}

        for source_name, client in self.clients:
            _logger.info("Fetching from %s...", source_name)

            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                _logger.error(
                    "Failed to fetch from %s: %s",
                    source_name,
                    error,
                )
                errors.append(
                    {"source": source_name, "error": str(error)}
                )
                continue
            except Exception as error:  # noqa: BLE001
                _logger.exception(
                    "Unexpected error from %s.", source_name
                )
                errors.append(
                    {"source": source_name, "error": str(error)}
                )
                continue

            if not rates:
                _logger.warning("%s: пустой ответ.", source_name)
                errors.append(
                    {
                        "source": source_name,
                        "error": "пустой ответ от источника",
                    }
                )
                continue

            _logger.info(
                "Fetching from %s... OK (%s rates)",
                source_name,
                len(rates),
            )
            success_sources.append(source_name)
            by_source[source_name] = rates
            combined.update(rates)

        if not success_sources:
            _logger.error("Все клиенты упали, обновление отменено.")
            raise ApiRequestError(
                "Не удалось обновить курсы: все источники недоступны."
            )

        # Сохраняем только то, что пришло, по источникам —
        # это позволяет сохранять старые значения для пар,
        # которые не обновились (см. Storage.save_rates).
        total_updated = 0
        last_refresh: str | None = None

        for source_name, rates in by_source.items():
            snapshot, count = self.storage.save_rates(rates, source_name)
            last_refresh = snapshot.get("last_refresh", last_refresh)
            total_updated += count

            self.storage.append_history(rates, source_name)

        result = {
            "count_updated": total_updated,
            "last_refresh": last_refresh,
            "errors": errors,
            "sources": success_sources,
        }

        _logger.info(
            "Update completed. Updated=%s, errors=%s",
            total_updated,
            len(errors),
        )
        return result