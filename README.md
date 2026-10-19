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
│    ├── users.json              # список пользователей         
│    ├── portfolios.json         # портфели и кошельки       
│    ├── rates.json              # локальный кэш для Core Service
│    └── exchange_rates.json     # хранилище Parser Service (исторические данные).json            
├── valutatrade_hub/
│    ├── __init__.py
│    ├── logging_config.py     # Настройка логов (формат, уровень, ротация)         
│    ├── decorators.py         # @log_action (логирование операций)            
│    ├── core/
│    │    ├── __init__.py
│    │    ├── currencies.py    # базовый класс Currency и наследники Fiat/Crypto     
│    │    ├── exceptions.py    # пользовательские исключения     
│    │    ├── models.py        # реализация классов    
│    │    ├── usecases.py      # бизнес-логика     
│    │    └── utils.py         # вспомогательные функции    
│    ├── infra/
│    │    ├─ __init__.py
│    │    ├── settings.py      # Singleton SettingsLoader (конфигурация)      
│    │    └── database.py      # Singleton DatabaseManager (над JSON-хранилищем)    
│    ├── parser_service/
│    │    ├── __init__.py
│    │    ├── config.py             # конфигурация API и параметров обновления
│    │    ├── api_clients.py        # работа с внешними API
│    │    ├── updater.py            # основной модуль обновления курсов
│    │    ├── storage.py            # операции чтения/записи exchange_rates.json
│    │    └── scheduler.py          # планировщик периодического обновления
│    └── cli/
│         ├─ __init__.py
│         └─ interface.py           # команды
│
├── main.py
├── uv.lock
├── pyproject.toml
├── README.md
└── .gitignore               
`````

## Установка

Проект работает на Python 3.12. 
Требует установку uv и ключ для парсинга, который после регистрации присылает платформа на указанный email.

| Инструмент | Установка | Запуск |
|---|---|---|
| **UV** | `uv sync` | `uv run project` |
| **ExchangeRate-API** | `https://www.exchangerate-api.com/` | `EXCHANGERATE_API_KEY="<Ключ_платформы>"` - macOS, Linux <br> `$env:EXCHANGERATE_API_KEY="<Ключ_платформы>"` - Windows |

CoinGecko отвечает за криптовалюты (используется учебный ключ от Яндекс Практикума), ExchangeRate-API — за фиатные.
Обе платформы нужны для Parser Service — это отдельный сервис, который по расписанию или по запросу обращается к публичным API, получает курсы, приводит их к единому JSON-формату и сохраняет актуальные значения в файл exchange_rates.json. Он ведёт подробный журнал: фиксирует каждую операцию, время обновления и возможные ошибки. Запустить его можно вручную через CLI-команду update-rates или настроить автоматический запуск по таймеру.


## Управление приложением

### Команды

Структура: command --key value
То есть сначала указывается команда, затем её ключ (параметр), и затем значение.

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