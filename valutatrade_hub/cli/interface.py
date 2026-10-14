"""Командный интерфейс ValutaTrade Hub."""

import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.usecases import ValutaTradeService


def _print_help() -> None:
    """Вывести список доступных команд."""
    print(
        """
Доступные команды:
  register --username ИМЯ --password ПАРОЛЬ
  login --username ИМЯ --password ПАРОЛЬ
  logout
  show-portfolio
  buy --currency ВАЛЮТА --amount СУММА
  sell --currency ВАЛЮТА --amount СУММА
  get-rate --from ВАЛЮТА [--to ВАЛЮТА]
  help
  exit
"""
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


def _print_portfolio(service: ValutaTradeService) -> None:
    """Вывести портфель пользователя."""
    result = service.show_portfolio()
    table = PrettyTable()
    table.field_names = ["Валюта", "Баланс"]

    for code, wallet in result["wallets"].items():
        table.add_row([code, f"{wallet.balance:.8f}"])

    print(table)
    print(
        f"Общая стоимость: {result['total_value']:.2f} "
        f"{result['base_currency']}"
    )


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

    if command == "logout":
        if arguments:
            raise ValueError("Команда logout не принимает параметры")
        service.logout()
        print("Вы вышли из аккаунта.")
        return True

    if command == "show-portfolio":
        if arguments:
            raise ValueError("Команда show-portfolio не принимает параметры")
        _print_portfolio(service)
        return True

    options = _parse_options(arguments)

    if command == "register":
        username = _required_option(options, "--username")
        password = _required_option(options, "--password")
        user = service.register(username, password)
        print(f"Пользователь '{user.username}' успешно зарегистрирован.")

    elif command == "login":
        username = _required_option(options, "--username")
        password = _required_option(options, "--password")
        user = service.login(username, password)
        print(f"Добро пожаловать, {user.username}!")

    elif command in ("buy", "sell"):
        currency = _required_option(options, "--currency")
        amount_text = _required_option(options, "--amount")

        try:
            amount = float(amount_text)
        except ValueError as error:
            raise ValueError("Сумма должна быть числом") from error

        if command == "buy":
            result = service.buy(currency, amount)
            action = "Куплено"
        else:
            result = service.sell(currency, amount)
            action = "Продано"

        print(
            f"{action}: {result['amount']:g} {result['currency']}. "
            f"Оценка в USD: {result['estimated_usd']}"
        )

    elif command == "get-rate":
        from_currency = _required_option(options, "--from")
        to_currency = options.get("--to", "USD")
        result = service.get_rate(from_currency, to_currency)
        print(
            f"{result['from_currency']} -> {result['to_currency']}: "
            f"{result['rate']}"
        )
        if result.get("inverse_rate") is not None:
            print(f"Обратный курс: {result['inverse_rate']}")

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
