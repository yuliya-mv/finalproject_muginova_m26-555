
"""Настройки приложения ValutaTrade Hub."""

from pathlib import Path
from typing import Any


class SettingsLoader:
    """Единый объект для доступа к настройкам приложения."""

    _instance = None

    def __new__(cls):
        """Создать только один экземпляр класса."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = {
                "data_dir": "data",
                "base_currency": "USD",
                "rates_ttl_seconds": 300,
                "log_file": "logs/actions.log",
                "log_level": "INFO",
            }
        return cls._instance

    def get(self, key: str, default: Any = None) -> Any:
        """Получить настройку по имени."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Изменить настройку."""
        self._settings[key] = value

    def get_data_path(self, filename: str) -> Path:
        """Получить путь к файлу в каталоге данных."""
        return Path(self.get("data_dir", "data")) / filename

    def reload(self) -> None:
        """Восстановить значения настроек по умолчанию."""
        self._settings = {
            "data_dir": "data",
            "base_currency": "USD",
            "rates_ttl_seconds": 300,
            "log_file": "logs/actions.log",
            "log_level": "INFO",
        }
