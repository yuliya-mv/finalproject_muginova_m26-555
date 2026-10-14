"""Командный интерфейс ValutaTrade Hub."""

import shlex

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import ValutaTradeService


def _print_help() -> None:
    """Вывести список доступных команд."""
    print(
        "Доступные команды:\n"
        "  register --username ИМЯ --password ПАРОЛЬ\n"
        "  login --username ИМЯ --password ПАРОЛЬ\n"
        "  show-portfolio [--base ВАЛЮТА]\n"
        "  buy --currency ВАЛЮТА --amount СУММА\n"
        "  sell --currency ВАЛЮТА --amount СУММА\n"
        "  get-rate --from ВАЛЮТА --to ВАЛЮТА\n"
        "  help\n"
        "  exit"
    )


def _parse_options(arguments: list[str]) -> dict[str, str]:
    """Преобразовать аргументы вида --ключ значение в словарь."""
    options: dict[str, str] = {}
    index = 0

    while index < len(arguments):
        key = arguments[index]

        if not key.startswith("--"):
            raise ValueError(f"Неожиданный аргумент: {key}")

        if index + 1 >= len(arguments):
            raise ValueError(f"Для параметра {key} не указано значение")

        if arguments[index + 1].startswith("--"):
            raise ValueError(f"Для параметра {key} не указано значение")

        options[key] = arguments[index + 1]
        index += 2

    return options


def _required_option(options: dict[str, str], key: str) -> str:
    """Получить обязательный параметр команды."""
    value = options.get(key)
    if value is None or not value.strip():
        raise ValueError(f"Необходимо указать параметр {key}")
    return value


def _format_money(value: float) -> str:
    """Отформатировать сумму с разделителями тысяч."""
    return f"{value:,.2f}"


def _print_portfolio(service: ValutaTradeService, base_currency: str) -> None:
    """Вывести портфель пользователя в текстовом виде (как в ТЗ)."""
    result = service.show_portfolio(base_currency)

    username = result["username"]
    base = result["base_currency"]

    print(f"Портфель пользователя '{username}' (база: {base}):")

    if not result["rows"]:
        print("- Портфель пуст.")
        print("---------------------------------")
        print(f"ИТОГО: 0.00 {base}")
        return

    for row in result["rows"]:
        code = row["code"]
        balance = row["balance"]
        value = row["value"]

        if value is None:
            print(f"- {code}: {balance:.4f}  →  нет курса")
        else:
            print(
                f"- {code}: {balance:.4f}  →  "
                f"{_format_money(value)} {base}"
            )

    print("---------------------------------")
    print(f"ИТОГО: {_format_money(result['total_value'])} {base}")


def _execute_command(
    service: ValutaTradeService,
    command: str,
    arguments: list[str],
) -> bool:
    """Выполнить команду. Вернуть False для завершения приложения."""
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
            raise ValueError("'amount' должен быть положительным числом") from error

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
            raise ValueError("'amount' должен быть положительным числом") from error

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

        print(
            f"Курс {result['from_currency']}→{result['to_currency']}: "
            f"{result['rate']} (обновлено: {result['updated_at']})"
        )
        print(
            f"Обратный курс {result['to_currency']}→"
            f"{result['from_currency']}: {result['inverse_rate']}"
        )

    else:
        raise ValueError(
            f"Неизвестная команда: {command}. Введите help для справки."
        )

    return True


def _handle_command(service: ValutaTradeService, command_line: str) -> bool:
    """Разобрать и выполнить одну команду."""
    try:
        parts = shlex.split(command_line)

        if not parts:
            return True

        return _execute_command(service, parts[0], parts[1:])

    except (
        ApiRequestError,
        CurrencyNotFoundError,
        InsufficientFundsError,
        ValueError,
        OSError,
    ) as error:
        print(f"Ошибка: {error}")
        return True


def run() -> None:
    """Запустить интерактивный командный интерфейс."""
    service = ValutaTradeService()
    print("ValutaTrade Hub. Введите help для списка команд, exit для выхода.")

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