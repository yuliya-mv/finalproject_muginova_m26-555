"""Декоратор @log_action для трассировки доменных операций"""

import functools
from datetime import datetime, timezone

from valutatrade_hub.logging_config import get_logger, setup_logging


_logger = get_logger("valutatrade_hub.decorators")


def _format_timestamp() -> str:
    """Вернуть текущее время в ISO-формате (UTC)."""
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat()


def log_action(action: str, verbose: bool = False):
    """Создать декоратор для логирования операции.

    :param action: имя операции (BUY, SELL, REGISTER, LOGIN).
    :param verbose: добавлять ли контекст «было → стало».
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            setup_logging()

            currency = ""
            amount = ""

            if args:
                if len(args) >= 1 and isinstance(args[0], str):
                    currency = args[0]
                if len(args) >= 2 and isinstance(args[1], (int, float)):
                    amount = args[1]

            username = ""
            user = getattr(self, "current_user", None)
            if user is not None:
                username = getattr(user, "username", "")

            try:
                result = func(self, *args, **kwargs)

                rate = result.get("rate") if isinstance(result, dict) else None
                before = result.get("before") if isinstance(result, dict) else None
                after = result.get("after") if isinstance(result, dict) else None

                parts = [
                    _format_timestamp(),
                    "INFO",
                    action,
                    f"user='{username}'",
                    f"currency='{currency}'",
                    f"amount={amount}",
                ]
                if rate is not None:
                    parts.append(f"rate={rate}")
                    parts.append("base='USD'")
                if verbose and before is not None and after is not None:
                    parts.append(f"wallet={before}->{after}")
                parts.append("result=OK")

                _logger.info(" ".join(part for part in parts if part))
                return result

            except Exception as error:
                parts = [
                    _format_timestamp(),
                    "ERROR",
                    action,
                    f"user='{username}'",
                    f"currency='{currency}'",
                    f"amount={amount}",
                    "result=ERROR",
                    f"error_type={type(error).__name__}",
                    f'error_message="{error}"',
                ]
                _logger.error(" ".join(parts))
                raise

        return wrapper

    return decorator