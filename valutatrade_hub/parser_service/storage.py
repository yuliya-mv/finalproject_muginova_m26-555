"""Хранилище Parser Service."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.config import ParserConfig


_logger = get_logger("valutatrade_hub.parser")


class Storage:
    """Работа с rates.json и exchange_rates.json."""

    def __init__(self, config: ParserConfig) -> None:
        """Сохранить конфигурацию и пути к файлам."""
        self.config = config
        self.rates_path = Path(config.RATES_FILE_PATH)
        self.history_path = Path(config.HISTORY_FILE_PATH)

    def load_rates(self) -> dict[str, Any]:
        """Загрузить актуальный снимок курсов."""
        data = self._load_json(self.rates_path, default={})
        if not isinstance(data, dict):
            return {"pairs": {}, "last_refresh": None}

        if "pairs" not in data:
            data = {"pairs": data, "last_refresh": None}

        return data

    def load_history(self) -> list[dict[str, Any]]:
        """Загрузить историю измерений."""
        data = self._load_json(self.history_path, default=[])
        if not isinstance(data, list):
            return []
        return data

    def save_rates(
        self,
        new_rates: dict[str, float],
        source: str,
    ) -> tuple[dict[str, Any], int]:
        snapshot = self.load_rates()
        old_pairs: dict[str, Any] = snapshot.get("pairs", {}) or {}

        now_iso = datetime.now(timezone.utc).replace(
            microsecond=0
        ).isoformat()

        updated_pairs: dict[str, Any] = dict(old_pairs)

        for pair, rate in new_rates.items():
            updated_pairs[pair] = {
                "rate": rate,
                "updated_at": now_iso,
                "source": source,
            }

        updated_count = len(new_rates)

        new_snapshot = {
            "pairs": updated_pairs,
            "last_refresh": now_iso,
        }

        self._save_json(self.rates_path, new_snapshot)
        _logger.info(
            "rates.json обновлён: %s пар, last_refresh=%s",
            updated_count,
            now_iso,
        )
        return new_snapshot, updated_count

    def append_history(
        self,
        new_rates: dict[str, float],
        source: str,
    ) -> int:
        history = self.load_history()
        existing_ids = {entry.get("id") for entry in history}

        now = datetime.now(timezone.utc).replace(microsecond=0)
        timestamp_iso = now.isoformat()

        added = 0

        for pair, rate in new_rates.items():
            from_currency, _, to_currency = pair.partition("_")
            if not from_currency or not to_currency:
                continue

            entry_id = f"{from_currency}_{to_currency}_{timestamp_iso}"

            if entry_id in existing_ids:
                continue

            history.append(
                {
                    "id": entry_id,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": rate,
                    "timestamp": timestamp_iso,
                    "source": source,
                    "meta": {
                        "raw_id": self.config.CRYPTO_ID_MAP.get(
                            from_currency, from_currency.lower()
                        ),
                    },
                }
            )
            existing_ids.add(entry_id)
            added += 1

        if added > 0:
            self._save_json(self.history_path, history)
            _logger.info(
                "exchange_rates.json: добавлено %s записей.", added
            )

        return added

    @staticmethod
    def _load_json(path: Path, default: Any) -> Any:
        """Загрузить JSON из файла или вернуть значение по умолчанию."""
        if not path.exists() or path.stat().st_size == 0:
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            _logger.error("Некорректный JSON в файле %s: %s", path, error)
            return default

    @staticmethod
    def _save_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                suffix=".tmp",
                delete=False,
            ) as file:
                temp_path = file.name
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")

            os.replace(temp_path, path)
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)