# ValutaTrade Hub

Учебный проект, который реализуется в виде консольного приложения, имитирующего работу валютного кошелька, и оформлен как полноценный Python-пакет.

Это комплексная платформа, которая позволяет пользователям регистрироваться, управлять своим виртуальным портфелем фиатных и крипто валют, совершать сделки по покупке/продаже, а также отслеживать актуальные курсы в реальном времени. Система состоит из двух основных сервисов:

* **Сервис Парсинга (Parser Service)**: Отдельное приложение, которое по запросу или расписанию обращается к публичным API, получает актуальные курсы, сравнивает их с предыдущими значениями и сохраняет историю в базу данных.
* **Основной Сервис (Core Service)**: Главное приложение, которое предоставляет пользовательский интерфейс (CLI), управляет пользователями, их кошельками, историей транзакций и взаимодействует с сервисом парсинга для получения актуальных курсов.

## Демонстрация работы
https://asciinema.org/a/sk4AjVkDClkJPJah

## Структура проекта

`````
finalproject_<фамилия>_<группа>/
│  
├── data/
│    ├── users.json          
│    ├── portfolios.json       
│    ├── rates.json               # локальный кэш для Core Service
│    └── exchange_rates.json      # хранилище Parser Service (исторические данные).json            
├── valutatrade_hub/
│    ├── __init__.py
│    ├── logging_config.py         
│    ├── decorators.py            
│    ├── core/
│    │    ├── __init__.py
│    │    ├── currencies.py         
│    │    ├── exceptions.py         
│    │    ├── models.py           
│    │    ├── usecases.py          
│    │    └── utils.py             
│    ├── infra/
│    │    ├─ __init__.py
│    │    ├── settings.py           
│    │    └── database.py          
│    ├── parser_service/
│    │    ├── __init__.py
│    │    ├── config.py             # конфигурация API и параметров обновления
│    │    ├── api_clients.py        # работа с внешними API
│    │    ├── updater.py            # основной модуль обновления курсов
│    │    ├── storage.py            # операции чтения/записи exchange_rates.json
│    │    └── scheduler.py          # планировщик периодического обновления
│    └── cli/
│         ├─ __init__.py
│         └─ interface.py     
│
├── main.py
├── uv.lock
├── pyproject.toml
├── README.md
└── .gitignore               
`````

## Установка

Проект требует установку uv

| Инструмент | Установка | Запуск |
|---|---|---|
| **UV** | `uv sync` | `uv run project` |

## Управление приложением

### Команды

`````
register --username ИМЯ --password ПАРОЛЬ - Регистрация нового пользователя
login --username ИМЯ --password ПАРОЛЬ - Вход в систему
show-portfolio [--base ВАЛЮТА] - Показать портфель и его стоимость
buy --currency ВАЛЮТА --amount СУММА - Купить валюту
sell --currency ВАЛЮТА --amount СУММА - Продать валюту
get-rate --from ВАЛЮТА [--to ВАЛЮТА] - Получить курс
update-rates [--source ИСТОЧНИК] - Обновить курсы через Parser Service
show-rates [--currency ВАЛЮТА] [--top N] [--base ВАЛЮТА] - Показать кэш курсов
help - Справка
exit - Выход
`````

### Пример работы

`````
> register --username alice --password 1234
Пользователь 'alice' зарегистрирован (id=3). Войдите: login --username alice --password ****

> login --username alice --password 1234
Вы вошли как 'alice' 

> show-portfolio
Портфель пользователя 'alice' (база: USD):
- USD: 150.00  → 150.00 USD
- BTC: 0.0500  → 2965.00 USD
- EUR: 200.00  → 214.00 USD
---------------------------------
ИТОГО: 3,329.00 USD 

> buy --currency BTC --amount 0.05
Покупка выполнена: 0.0500 BTC по курсу 59300.00 USD/BTC
Изменения в портфеле:
- BTC: было 0.0000 → стало 0.0500
Оценочная стоимость покупки: 2,965.00 USD

> sell --currency USD --amount 100
Продажа выполнена: 0.0100 BTC по курсу 59800.00 USD/BTC
Изменения в портфеле:
- BTC: было 0.0500 → стало 0.0400
Оценочная выручка: 598.00 USD

> get-rate --from USD --to BTC
Курс USD→BTC: 0.00001685 (обновлено: 2025-10-09 00:03:22)
Обратный курс BTC→USD: 59337.21

> update-rates
INFO: Starting rates update...
INFO: Fetching from CoinGecko... OK (3 rates)
INFO: Fetching from ExchangeRate-API... OK (3 rates)
INFO: Writing 6 rates to data/rates.json...
Update successful. Total rates updated: 6. Last refresh: 2025-10-10T15:30:00

> show-rates --top 2
Rates from cache (updated at 2025-10-10T15:30:00):
- BTC_USD: 59337.21
- ETH_USD: 3720.00

> show-rates --currency RUB
Rates from cache (updated at 2025-10-10T15:30:00):
- RUB_USD: 0.01016
`````