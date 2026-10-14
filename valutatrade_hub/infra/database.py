
"""Работа с JSON-хранилищем приложения."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Единый объект для доступа к JSON-файлам приложения."""

    _instance = None

    def __new__(cls):
        """Создать только один экземпляр класса."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Подготовить пути к файлам данных один раз."""
        if self._initialized:
            return

        project_root = Path(__file__).resolve().parents[2]
        data_dir = Path(SettingsLoader().get("data_dir", "data"))

        if not data_dir.is_absolute():
            data_dir = project_root / data_dir

        self._paths = {
            "users": data_dir / "users.json",
            "portfolios": data_dir / "portfolios.json",
            "rates": data_dir / "rates.json",
            "exchange_rates": data_dir / "exchange_rates.json",
        }
        self._initialized = True

    def load(self, name: str, default: Any = None) -> Any:
        """Загрузить данные из выбранного JSON-файла."""
        path = self._get_path(name)

        if not path.exists() or path.stat().st_size == 0:
            return default if default is not None else {}

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as error:
            raise ValueError(f"Некорректный JSON в файле {path}") from error

    def save(self, name: str, data: Any) -> None:
        """Атомарно сохранить данные в выбранный JSON-файл."""
        path = self._get_path(name)
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
                json.dump(data, file, ensure_ascii=False, indent=4)
                file.write("\n")

            os.replace(temp_path, path)
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)

    def _get_path(self, name: str) -> Path:
        """Вернуть путь к файлу по его логическому имени."""
        try:
            return self._paths[name]
        except KeyError as error:
            raise ValueError(f"Неизвестное хранилище: {name}") from error
