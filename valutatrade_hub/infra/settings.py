"""Настройки приложения ValutaTrade Hub."""

from pathlib import Path
from typing import Any


class SettingsLoader:
    """Единый объект для доступа к настройкам приложения."""

    _instance: "SettingsLoader | None" = None

    _DEFAULTS: dict[str, Any] = {
        "data_dir": "data",
        "base_currency": "USD",
        "rates_ttl_seconds": 300,
        "log_file": "logs/actions.log",
        "log_level": "INFO",
    }

    def __new__(cls) -> "SettingsLoader":
        """Создать только один экземпляр класса.

        Способ через __new__ выбран, потому что он простой и
        явный: приложение не должно создавать несколько
        загрузчиков настроек.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = dict(cls._DEFAULTS)
        return cls._instance

    def get(self, key: str, default: Any = None) -> Any:
        """Получить настройку по имени."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Изменить настройку в текущем экземпляре."""
        self._settings[key] = value

    def get_data_path(self, filename: str) -> Path:
        """Получить путь к файлу в каталоге данных."""
        return Path(self.get("data_dir", "data")) / filename

    def reload(self) -> None:
        """Сбросить настройки к значениям по умолчанию."""
        self._settings = dict(self._DEFAULTS)