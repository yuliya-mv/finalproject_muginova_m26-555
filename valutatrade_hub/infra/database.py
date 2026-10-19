"""Работа с JSON-хранилищем"""

import json
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Менеджер JSON-файлов с использованием Singleton."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self.settings = SettingsLoader()
        self.project_root = Path(__file__).resolve().parents[2]

        data_dir = Path(self.settings.get("data_dir", "data"))
        if not data_dir.is_absolute():
            data_dir = self.project_root / data_dir

        self._paths = {
            "users": data_dir / "users.json",
            "portfolios": data_dir / "portfolios.json",
            "rates": data_dir / "rates.json",
            "exchange_rates": data_dir / "exchange_rates.json",
        }

        self._initialized = True

    def get_path(self, key: str) -> Path:
        """Получить путь к файлу."""
        try:
            return self._paths[key]
        except KeyError as error:
            raise ValueError(f"Неизвестное хранилище: {key}") from error

    def load(self, key: str, default=None):
        path = self.get_path(key)

        if not path.exists() or path.stat().st_size == 0:
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(f"Некорректный JSON в файле {path}") from error

    def save(self, key: str, data) -> None:
        """Сохранить данные в JSON-файл."""
        path = self.get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = path.with_suffix(path.suffix + ".tmp")

        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
            file.write("\n")

        temp_path.replace(path)