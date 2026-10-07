# 🏠 Клиент ФИАС Public API на Python

Python-клиент для ФИАС Public API — федеральной информационной адресной системы Российской Федерации. Поддерживает синхронные и асинхронные операции.

> ⚠️ **Это неофициальный клиент.** Проект не связан с ФНС России и не
> поддерживается разработчиками ФИАС — независимая обёртка над публичным API.
> Актуальную документацию по API смотрите на [официальном сайте ФИАС](https://fias.nalog.ru/).

## 📦 Установка

### Установка из PyPI (рекомендуется)

```bash
pip install fias-public-api
```

### Установка из GitHub

```bash
pip install git+https://github.com/quonaro/fias-public-api
```

## 🔌 Зависимости

| Пакет      | Версия     | Описание                         |
| ---------- | ---------- | -------------------------------- |
| `requests` | `>=2.32.5` | HTTP библиотека для API запросов |
| `httpx`    | `>=0.28.1` | Асинхронная HTTP библиотека      |

## 🚀 Быстрый старт

### Синхронный пример

```python
from fias_public_api import get_token_sync, SyncFPA, AddressType

# Получаем токен автоматически
token = get_token_sync()

# Создаем клиент (address_type обязателен: 1 — административный, 2 — муниципальный)
api = SyncFPA(token, AddressType.ADMINISTRATIVE)

# Ищем адрес
results = api.search("Москва, Красная площадь")
print(f"Найдено: {len(results)} результатов")

# Получаем детали первого результата
if results:
    details = api.details_by_id(results[0]['id'])
    print(f"Адрес: {details.get('address', 'N/A')}")
```

### Асинхронный пример

```python
import asyncio
from fias_public_api import get_token_async, AsyncFPA, AddressType

async def main():
    token = await get_token_async()

    async with AsyncFPA(token, AddressType.ADMINISTRATIVE) as api:
        results = await api.search("Москва, Красная площадь")
        print(f"Найдено: {len(results)} результатов")

        if results:
            details = await api.details_by_id(results[0]['id'])
            print(f"Адрес: {details.get('address', 'N/A')}")

asyncio.run(main())
```

## 📋 Примеры использования

### 🔍 Поиск адресов

```python
# Простой поиск (используется address_type из конструктора)
results = api.search("Москва")

# Поиск с переопределением address_type для конкретного вызова
results = api.search("Санкт-Петербург", address_type=AddressType.MUNICIPALITY)

# Обработка результатов
for result in results:
    print(f"ID: {result['id']}")
    print(f"Адрес: {result['address']}")
    print(f"Тип: {result['type']}")
```

### 🗺️ Получить список регионов

```python
regions = api.get_regions()
for region in regions:
    print(region['name'])
```

### 🆔 Детали по ID

```python
from fias_public_api import AddressType

object_id = 12345
# address_type можно переопределить для конкретного вызова
details = api.details_by_id(object_id, address_type=AddressType.MUNICIPALITY)
```

### 🧬 Детали по GUID

```python
object_guid = "some-guid-string"
details = api.details_by_guid(object_guid, address_type=AddressType.ADMINISTRATIVE)
```

### 📍 Местоположение по IP

```python
location = api.get_location_by_ip("8.8.8.8")
print(location)
```

### 🛠️ Фильтрация адресных объектов

```python
items = api.get_address_items(
    path="7700000000000",
    address_level=7,
    name_part="Тверская"
)
```

### 💡 Подсказки по адресу

```python
hints = api.get_address_hint(
    search_string="Москва",
    up_to_level=5
)
```

### ⚙️ Опции клиента

```python
from fias_public_api import AddressType

api = SyncFPA(
    token,
    address_type=AddressType.ADMINISTRATIVE,
    enable_logging=True,
    timeout=30.0,  # таймаут каждого HTTP запроса, по умолчанию 15 секунд
)
```

`timeout` применяется к каждому запросу, включая `get_token_sync()` / `get_token_async()`.

### 🔄 Retry-декоратор

```python
from fias_public_api import retry_on_error
from requests.exceptions import ConnectionError, HTTPError

@retry_on_error(
    max_retries=5,
    delay=1.0,
    backoff=2.0,
    exceptions=(ConnectionError, HTTPError)
)
def search_with_retry(search_string):
    return api.search_address_items(search_string)
```

По умолчанию (`exceptions` не задан) повторяются ошибки транспорта обеих
библиотек: `OSError` (покрывает всё дерево `requests`) и `httpx.HTTPError`
(у httpx исключения наследуются от `Exception`, а не от `OSError`, поэтому их
нужно перечислять явно). Программные ошибки — `ValueError` на пустой запрос,
`KeyError`, `TypeError` — не повторяются: повторять заведомо неуспешный запрос
бессмысленно.

### 🔄 Обработка ошибок

Любой ответ с кодом 4xx/5xx поднимает исключение, а не возвращается как данные:

- синхронный клиент — `requests.HTTPError`
- асинхронный клиент — `httpx.HTTPStatusError`

```python
from requests.exceptions import HTTPError, RequestException, Timeout

try:
    results = api.search("Несуществующий адрес")
except HTTPError as e:
    if e.response.status_code == 404:
        print("Адрес не найден")
    elif e.response.status_code == 401:
        print("Неверный токен")
    else:
        print(f"HTTP ошибка: {e}")
except Timeout:
    print("Превышен таймаут запроса")
except RequestException as e:
    print(f"Ошибка сети: {e}")
```

Пустой поисковый запрос — это `ValueError`, он поднимается до обращения к сети:

```python
api.search("   ")  # ValueError: search_string cannot be empty
```

## 📚 Методы API

### Синхронные методы (`SyncFPA`)

- `search(search_string, address_type)` — поиск адресов по текстовой строке
- `details_by_id(object_id, address_type)` — детали по ID
- `details_by_guid(object_guid, address_type)` — детали по GUID
- `get_regions()` — список регионов
- `get_address_items(...)` — фильтрация адресных объектов
- `get_details(object_id)` — дополнительные сведения
- `is_descendant(ancestor, descendant, address_type)` — проверка вложенности
- `has_descendants(parent, up_to_level, address_type)` — проверка наличия потомков
- `get_address_item_by_cadastral_number(number, address_type)` — по кадастровому номеру
- `get_fias_object_types()` — типы объектов ФИАС
- `search_address_items(search_string, address_type)` — поиск по строке
- `get_address_hint(...)` — подсказки по адресу
- `search_address_item(search_string, address_type)` — поиск одного объекта
- `get_location_by_ip(ip, address_type)` — местоположение по IP

### Асинхронные методы (`AsyncFPA`)

Все методы из `SyncFPA` доступны в асинхронной версии с поддержкой `async`/`await`.

### Вспомогательные функции

- `get_token_sync(url, timeout)` — получить токен (синхронно)
- `get_token_async(url, timeout)` — получить токен (асинхронно)
- `STANDARD_HEADERS(token)` — стандартные HTTP-заголовки (`STANDART_HEADERS` оставлен как алиас)
- `AddressType` — перечисление типов адресов (`ADMINISTRATIVE = 1`, `MUNICIPALITY = 2`)
- `retry_on_error(...)` — декоратор для повторных попыток при ошибках
- `DEFAULT_RETRY_EXCEPTIONS` — что повторяется по умолчанию (`OSError`, `httpx.HTTPError`)
- `DEFAULT_TIMEOUT` — таймаут запросов по умолчанию (15 секунд)

## 📁 Примеры из папки examples

Все примеры доступны в папке [`examples/`](examples/):

- **01_basic_usage.py** — базовое использование API
- **02_address_types.py** — работа с типами адресов
- **03_async_usage.py** — асинхронное использование
- **04_retry_decorator.py** — использование retry декоратора
- **05_address_info_methods.py** — методы AddressInfo
- **06_search_methods.py** — методы поиска
- **07_location_methods.py** — определение локации по IP
- **08_error_handling.py** — обработка ошибок

## 🧪 Тестирование

```bash
# Установка зависимостей для разработки
pip install -e ".[dev]"

# Юнит-тесты: без сети, все HTTP вызовы замоканы
pytest

# Покрытие (branch coverage, порог fail_under задан в pyproject.toml)
pytest --cov --cov-report=term-missing

# Живые тесты против реального API ФИАС (нужна сеть, по умолчанию отключены)
pytest -m integration

# Линтер
ruff check .

# Запуск конкретного теста
pytest tests/test_sync.py::TestSyncFPA::test_get_regions
```

Оба клиента прогоняются через общую таблицу эндпоинтов (`tests/endpoints.py`),
поэтому метод, который разъедется по URL, HTTP-методу или вообще появится
только в одном из клиентов, роняет тест, а не проходит незамеченным.

Тесты, обращающиеся к боевому сервису, помечены маркером `integration` и не
входят в обычный прогон `pytest`, поэтому сборка не зависит от доступности
`fias.nalog.ru`.

## ⚠️ Изменения поведения в 1.1.0

Версия 1.1.0 исправляет ошибки обработки HTTP, поэтому часть поведения
намеренно изменилась:

- **HTTP-ошибки поднимают исключение.** Раньше ответ 4xx/5xx возвращался как
  обычный JSON, теперь это `requests.HTTPError` / `httpx.HTTPStatusError`.
  Код, проверявший `result.get("error")`, получит исключение вместо данных.
- **Таймаут по умолчанию — 15 секунд.** Запросы больше не могут висеть
  бесконечно; меняется через `SyncFPA(..., timeout=30.0)`.
- **`get_token_sync`/`get_token_async` на ошибке HTTP бросают `ValueError`**,
  а не `HTTPError` — sync и async приведены к одному поведению.
- **`retry_on_error(max_retries=0)`** теперь сразу бросает `ValueError`
  (раньше молча возвращал `None` из обёрнутой функции).
- **`details()`** выводит `DeprecationWarning`, а не `print` в stdout.
- `SYNC_RETRY_EXCEPTIONS` и `ASYNC_RETRY_EXCEPTIONS` сохранены как алиасы
  общего `DEFAULT_RETRY_EXCEPTIONS`; `STANDART_HEADERS` — алиас
  `STANDARD_HEADERS`. Старые импорты не ломаются.

## 🚢 Релиз

Релиз публикует тег, а не коммит. Версия задаётся явно через `lota push`:

```bash
lota push v1.1.0
```

Это запишет `version = "1.1.0"` в `pyproject.toml`, закоммитит изменение,
создаст тег и запушит ветку и тег. `lota push` без аргумента — обычный
`git push origin main`.

Пуш тега `v*` запускает `.github/workflows/publish.yml`: тесты и линтер,
сборка, публикация на PyPI (trusted publishing, fallback на
`PYPI_API_TOKEN`) и проверка, что версия реально появилась на PyPI — если
публикация не состоялась, workflow падает красным, а не молча завершается
зелёным. Дёргать версию руками не нужно: workflow берёт её из тега.

## 📄 Лицензия

MIT. Подробности см. в файле [LICENSE](LICENSE).

## 🔗 Полезные ссылки

- [PyPI Package](https://pypi.org/project/fias-public-api/)
- [Официальный сайт ФИАС](https://fias.nalog.ru/)
- [Swagger UI FIAS Public Service](https://fias-public-service.nalog.ru/api/spas/v2.0/swagger/index.html)
