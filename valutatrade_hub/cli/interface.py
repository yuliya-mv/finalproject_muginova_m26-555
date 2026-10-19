"""Командный интерфейс ValutaTrade Hub."""

import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import get_currency, list_currencies
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    ValutaTradeError,
)
from valutatrade_hub.core.usecases import ValutaTradeService
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.logging_config import (
    attach_console_handler,
    detach_console_handler,
    setup_logging,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.scheduler import build_updater


def _print_help() -> None:
    print(
        "Доступные команды:\n"
        "  register --username ИМЯ --password ПАРОЛЬ\n"
        "  login --username ИМЯ --password ПАРОЛЬ\n"
        "  show-portfolio [--base ВАЛЮТА]\n"
        "  buy --currency ВАЛЮТА --amount СУММА\n"
        "  sell --currency ВАЛЮТА --amount СУММА\n"
        "  get-rate --from ВАЛЮТА [--to ВАЛЮТА]\n"
        "  update-rates [--source ИСТОЧНИК]\n"
        "  show-rates [--currency ВАЛЮТА] [--top N] [--base ВАЛЮТА]\n"
        "  help\n"
        "  exit"
    )


def _parse_options(arguments: list[str]) -> dict[str, str]:
    """Преобразовать ключи в словарь."""
    options: dict[str, str] = {}
    index = 0

    while index < len(arguments):
        key = arguments[index]

        if not key.startswith("--"):
            raise ValueError(f"Параметр должен начинаться с --, факт: {key}")

        if index + 1 >= len(arguments):
            raise ValueError(f"Для параметра {key} не указано значение")

        if arguments[index + 1].startswith("--"):
            raise ValueError(f"Для параметра {key} не указано значение")

        options[key] = arguments[index + 1]
        index += 2

    return options


def _required_option(options: dict[str, str], key: str) -> str:
    value = options.get(key)
    if value is None or not value.strip():
        raise ValueError(f"Необходимо указать параметр {key}")
    return value


def _format_money(value: float) -> str:
    return f"{value:,.2f}"


def _print_portfolio(service: ValutaTradeService, base_currency: str) -> None:
    result = service.show_portfolio(base_currency)

    username = result["username"]
    base = result["base_currency"]

    print(f"Портфель пользователя '{username}' (база: {base}):")

    if not result["rows"]:
        print("Портфель пуст.")
        print(f"ИТОГО: 0.00 {base}")
        return

    table = PrettyTable()
    table.field_names = ["Валюта", "Баланс", f"Стоимость ({base})"]

    for row in result["rows"]:
        value = row["value"]
        value_text = (
            _format_money(value) if value is not None else "нет курса"
        )
        table.add_row([row["code"], f"{row['balance']:.4f}", value_text])

    print(table)
    print(f"ИТОГО: {_format_money(result['total_value'])} {base}")

    if result.get("missing_rate"):
        print("Для некоторых валют нет курса.")
    if result.get("is_stale"):
        print("Курсы устарели, выполните update-rates.")


def _execute_command(
    service: ValutaTradeService,
    command: str,
    arguments: list[str],
) -> bool:
    """Выполнение команд."""
    if command == "exit":
        return False

    if command == "help":
        _print_help()
        return True

    if command == "show-portfolio":
        options = _parse_options(arguments)
        unknown = set(options) - {"--base"}
        if unknown:
            raise ValueError(f"Неизвестный параметр: {sorted(unknown)[0]}")

        base = options.get("--base", "USD")
        _print_portfolio(service, base)
        return True

    if command == "update-rates":
        options = _parse_options(arguments)
        unknown = set(options) - {"--source"}
        if unknown:
            raise ValueError(f"Неизвестный параметр: {sorted(unknown)[0]}")

        source_filter = options.get("--source")
        _run_update_rates(source_filter)
        return True

    if command == "show-rates":
        options = _parse_options(arguments)
        unknown = set(options) - {"--currency", "--top", "--base"}
        if unknown:
            raise ValueError(f"Неизвестный параметр: {sorted(unknown)[0]}")

        _print_rates(options)
        return True

    options = _parse_options(arguments)

    if command == "register":
        username = _required_option(options, "--username")
        password = _required_option(options, "--password")
        user = service.register(username, password)
        print(
            f"Пользователь '{user.username}' зарегистрирован "
            f"(id={user.user_id}). Войдите: "
            f"login --username {user.username} --password ****"
        )

    elif command == "login":
        username = _required_option(options, "--username")
        password = _required_option(options, "--password")
        user = service.login(username, password)
        print(f"Вы вошли как '{user.username}'")

    elif command == "buy":
        currency = _required_option(options, "--currency")
        amount_text = _required_option(options, "--amount")

        try:
            amount = float(amount_text)
        except ValueError as error:
            raise ValueError(
                "'amount' должен быть положительным числом"
            ) from error

        result = service.buy(currency, amount)
        rate = result["rate"]

        if rate is not None:
            print(
                f"Покупка выполнена: {result['amount']:.4f} "
                f"{result['currency']} по курсу {rate:.2f} USD/"
                f"{result['currency']}"
            )
        else:
            print(
                f"Покупка выполнена: {result['amount']:.4f} "
                f"{result['currency']}"
            )

        print("Изменения в портфеле:")
        print(
            f"- {result['currency']}: было {result['before']:.4f} "
            f"→ стало {result['after']:.4f}"
        )

        if result["estimated_usd"] is not None:
            print(
                "Оценочная стоимость покупки: "
                f"{_format_money(result['estimated_usd'])} USD"
            )

    elif command == "sell":
        currency = _required_option(options, "--currency")
        amount_text = _required_option(options, "--amount")

        try:
            amount = float(amount_text)
        except ValueError as error:
            raise ValueError(
                "'amount' должен быть положительным числом"
            ) from error

        result = service.sell(currency, amount)
        rate = result["rate"]

        if rate is not None:
            print(
                f"Продажа выполнена: {result['amount']:.4f} "
                f"{result['currency']} по курсу {rate:.2f} USD/"
                f"{result['currency']}"
            )
        else:
            print(
                f"Продажа выполнена: {result['amount']:.4f} "
                f"{result['currency']}"
            )

        print("Изменения в портфеле:")
        print(
            f"- {result['currency']}: было {result['before']:.4f} "
            f"→ стало {result['after']:.4f}"
        )

        if result["estimated_usd"] is not None:
            print(
                "Оценочная выручка: "
                f"{_format_money(result['estimated_usd'])} USD"
            )

    elif command == "get-rate":
        from_currency = _required_option(options, "--from")
        to_currency = options.get("--to", "USD")
        result = service.get_rate(from_currency, to_currency)

        rate_value = result["rate"]
        inverse_value = result["inverse_rate"]

        if rate_value < 1:
            rate_text = f"{rate_value:.8f}".rstrip("0").rstrip(".")
        else:
            rate_text = f"{rate_value:.2f}"

        if inverse_value < 1:
            inverse_text = f"{inverse_value:.8f}".rstrip("0").rstrip(".")
        else:
            inverse_text = f"{inverse_value:.2f}"

        print(
            f"Курс {result['from_currency']}→{result['to_currency']}: "
            f"{rate_text} (обновлено: {result['updated_at']})"
        )
        print(
            f"Обратный курс {result['to_currency']}→"
            f"{result['from_currency']}: {inverse_text}"
        )

        if result.get("is_stale"):
            print("Курсы устарели, выполните update-rates.")

    else:
        raise ValueError(
            f"Неизвестная команда: {command}, откройте help."
        )

    return True


def _run_update_rates(source_filter: str | None) -> None:
    """Запустить Parser Service через команду update-rates."""
    config = ParserConfig()
    updater = build_updater(config)

    if source_filter:
        source_filter_lower = source_filter.lower()
        filtered = [
            (name, client)
            for name, client in updater.clients
            if source_filter_lower in name.lower()
        ]
        if not filtered:
            raise ValueError(
                f"Нет источника: {source_filter}. "
                "Доступны: CoinGecko, ExchangeRate-API."
            )
        updater.clients = filtered

    console_handler = attach_console_handler()
    try:
        result = updater.run_update()
    finally:
        detach_console_handler(console_handler)

    count = result["count_updated"]
    last_refresh = result["last_refresh"]
    errors = result["errors"]

    if errors:
        print(
            "Есть ошибки обновления."
            f"Обновлено: {count}. Проверьте logs/parser.log"
        )
    else:
        print(
            "Обновление завершено. "
            f"Обновлено: {count}. "
            f"Последняя синхронизация: {last_refresh}"
        )


def _print_rates(options: dict[str, str]) -> None:
    """Показать курсы из локального кэша (rates.json)."""
    from valutatrade_hub.parser_service.storage import Storage

    config = ParserConfig()
    storage = Storage(config)
    snapshot = storage.load_rates()

    pairs: dict[str, dict] = snapshot.get("pairs", {}) or {}
    last_refresh = snapshot.get("last_refresh", "unknown")

    if not pairs:
        print(
            "Локальный кеш курсов пуст, выполните update-rates."
        )
        return

    currency_filter = options.get("--currency")
    top = options.get("--top")
    base_filter = options.get("--base", "USD").upper()

    if currency_filter:
        currency_code = currency_filter.upper()
        get_currency(currency_code)
        key = f"{currency_code}_{base_filter}"
        entry = pairs.get(key)
        if entry is None:
            print(
                f"Курс для '{currency_code}' не найден в кеше."
            )
            return
        pairs = {key: entry}

    if top:
        try:
            top_n = int(top)
        except ValueError as error:
            raise ValueError("--top должен быть целым числом") from error

        crypto_codes = set(config.CRYPTO_CURRENCIES)
        candidates = []
        for pair, entry in pairs.items():
            from_code = pair.split("_")[0]
            if from_code not in crypto_codes:
                continue
            if not pair.endswith(f"_{base_filter}"):
                continue
            rate = entry.get("rate") if isinstance(entry, dict) else None
            if isinstance(rate, (int, float)):
                candidates.append((pair, float(rate), entry))

        candidates.sort(key=lambda item: item[1], reverse=True)
        pairs = {pair: entry for pair, _, entry in candidates[:top_n]}

    table = PrettyTable()
    table.field_names = ["Пара", "Курс", "Обновлено", "Источник"]

    for pair in sorted(pairs):
        entry = pairs[pair]
        if isinstance(entry, dict):
            rate = entry.get("rate", "—")
            updated_at = entry.get("updated_at", "—")
            source = entry.get("source", "—")
        else:
            rate = entry
            updated_at = "—"
            source = "—"

        if isinstance(rate, float):
            if rate < 1:
                rate_text = f"{rate:.8f}".rstrip("0").rstrip(".")
            else:
                rate_text = f"{rate:.4f}"
        else:
            rate_text = str(rate)

        table.add_row([pair, rate_text, updated_at, source])

    print(f"Rates from cache (updated at {last_refresh}):")
    print(table)


def _handle_command(service: ValutaTradeService, command_line: str) -> bool:
    try:
        parts = shlex.split(command_line)

        if not parts:
            return True

        return _execute_command(service, parts[0], parts[1:])

    except CurrencyNotFoundError as error:
        print(str(error))
        codes = ", ".join(sorted(list_currencies().keys()))
        print(f"Поддерживаемые коды: {codes}")
        return True

    except ApiRequestError as error:
        print(str(error))
        print("API недоступен, повторите попытку позже.")
        return True

    except InsufficientFundsError as error:
        print(str(error))
        return True

    except (ValutaTradeError, ValueError, OSError) as error:
        print(f"Ошибка: {error}")
        return True


def run() -> None:
    settings = SettingsLoader()
    setup_logging(
        log_file=settings.get("log_file", "logs/actions.log"),
        level=settings.get("log_level", "INFO"),
    )

    service = ValutaTradeService()
    print(
        "Welcome to ValutaTrade Hub. Введите help для списка команд, exit для выхода."
    )

    while True:
        try:
            command_line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nРабота приложения завершена.")
            break

        if not _handle_command(service, command_line):
            print("Работа приложения завершена.")
            break


if __name__ == "__main__":
    run()