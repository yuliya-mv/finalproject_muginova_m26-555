
"""Вспомогательные функции для проверки валют и конвертации."""

from valutatrade_hub.core.currencies import get_currency


def validate_currency_code(code: str) -> str:
    """Проверить код валюты и вернуть его в верхнем регистре."""
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Код валюты не должен быть пустым")

    normalized_code = code.strip().upper()
    get_currency(normalized_code)
    return normalized_code


def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    rates: dict,
) -> float:
    """Конвертировать сумму через USD на основе переданных курсов."""
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise ValueError("Сумма должна быть числом")

    if amount < 0:
        raise ValueError("Сумма не может быть отрицательной")

    source = validate_currency_code(from_currency)
    target = validate_currency_code(to_currency)

    if source == target:
        return float(amount)

    source_rate = _get_usd_rate(source, rates)
    target_rate = _get_usd_rate(target, rates)

    return float(amount) * source_rate / target_rate


def _get_usd_rate(currency_code: str, rates: dict) -> float:
    """Получить стоимость одной единицы валюты в USD."""
    if currency_code == "USD":
        return 1.0

    pair = f"{currency_code}_USD"
    value = rates.get(pair)

    if isinstance(value, dict):
        value = value.get("rate")

    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"Курс {pair} отсутствует или некорректен")

    return float(value)
