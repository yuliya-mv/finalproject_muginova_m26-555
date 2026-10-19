"""Загрузчик настроек (Singleton)."""

import tomllib
from pathlib import Path


class SettingsLoader:
    """Загрузчик настроек с использованием Singleton. __new__ выбран из-за простоты"""

    _instance = None

    _DEFAULTS = {
        "data_dir": "data",
        "base_currency": "USD",
        "rates_ttl_seconds": 300,
        "log_file": "logs/actions.log",
        "log_level": "INFO",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Загрузить настройки из pyproject.toml"""
        if getattr(self, "_initialized", False):
            return

        project_root = Path(__file__).resolve().parents[2]
        self.settings_path = project_root / "pyproject.toml"
        self._settings = self._load_settings()

        self._initialized = True

    def _load_settings(self) -> dict:
        """Прочитать [tool.valutatrade] из pyproject.toml"""
        settings = dict(self._DEFAULTS)

        if not self.settings_path.exists():
            return settings

        try:
            with self.settings_path.open("rb") as file:
                pyproject = tomllib.load(file)
        except tomllib.TOMLDecodeError:
            return settings

        section = pyproject.get("tool", {}).get("valutatrade", {})
        if isinstance(section, dict):
            settings.update(section)

        return settings

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def set(self, key, value) -> None:
        self._settings[key] = value

    def all(self):
        return self._settings.copy()

    def reload(self) -> None:
        """Перезагрузить настройки из pyproject.toml"""
        self._initialized = False
        self.__init__()