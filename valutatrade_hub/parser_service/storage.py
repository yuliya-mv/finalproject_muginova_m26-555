"""Хранилище Parser Service."""

from datetime import datetime, timezone

from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.config import CRYPTO_ID_MAP, ParserConfig

_logger = get_logger("valutatrade_hub.parser")


class Storage:
    """Работа с rates.json и exchange_rates.json."""

    def __init__(self, config: ParserConfig) -> None:
        self.config = config
        self.db = DatabaseManager()

    def load_rates(self) -> dict:
        """Загрузить последние курсы."""
        data = self.db.load("rates", {})
        if not isinstance(data, dict):
            return {"pairs": {}, "last_refresh": None}
        if "pairs" not in data:
            data = {"pairs": data, "last_refresh": None}
        return data

    def load_history(self) -> list:
        data = self.db.load("exchange_rates", [])
        return data if isinstance(data, list) else []

    def save(self, new_rates: dict, source: str) -> int:
        now_iso = datetime.now(timezone.utc).replace(
            microsecond=0
        ).isoformat()

        snapshot = self.load_rates()
        old_pairs = snapshot.get("pairs", {}) or {}

        history = self.load_history()
        known_ids = {entry.get("id") for entry in history}

        accepted = 0
        updated_pairs = dict(old_pairs)

        for pair, rate in new_rates.items():
            old = old_pairs.get(pair)
            if old and now_iso <= old.get("updated_at", ""):
                continue

            from_currency, _, to_currency = pair.partition("_")
            if not from_currency or not to_currency:
                continue

            updated_pairs[pair] = {
                "rate": rate,
                "updated_at": now_iso,
                "source": source,
            }

            entry_id = f"{from_currency}_{to_currency}_{now_iso}"
            if entry_id not in known_ids:
                history.append({
                    "id": entry_id,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "rate": rate,
                    "timestamp": now_iso,
                    "source": source,
                    "meta": {
                        "raw_id": CRYPTO_ID_MAP.get(
                            from_currency, from_currency.lower()
                        ),
                    },
                })
                known_ids.add(entry_id)

            accepted += 1

        if accepted == 0:
            return 0

        self.db.save("exchange_rates", history)
        self.db.save("rates", {
            "pairs": updated_pairs,
            "last_refresh": now_iso,
        })

        _logger.info(
            "rates.json обновлён: %s пар, last_refresh=%s",
            accepted,
            now_iso,
        )
        return accepted