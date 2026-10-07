# Contributing

Спасибо, что хотите помочь проекту. Ниже — всё, что нужно, чтобы PR прошёл
ревью и CI с первого раза.

## Подготовка окружения

```bash
pip install -e ".[dev]"   # или: uv sync --extra dev
```

## Проверки перед PR

Те же команды, что гоняет CI:

```bash
ruff check .                                     # линтер
pytest -m "not integration" --cov=fias_public_api  # юнит-тесты + покрытие
```

- Юнит-тесты работают **полностью офлайн** — все HTTP-вызовы замоканы.
- Покрытие гейтится на 95% branch coverage (`fail_under` в `pyproject.toml`).
- `pytest -m integration` — живые тесты против `fias.nalog.ru`, локально
  можно не запускать.

## Правила для тестов

- **Не ходите в сеть из юнит-тестов.** Сетевые тесты помечаются
  `@pytest.mark.integration` и не входят в обычный прогон.
- Мокайте `requests.request`, а не `requests.get`/`requests.post` —
  клиент вызывает именно его.
- Новый метод API добавляется в **оба** клиента (`SyncFPA` и `AsyncFPA`)
  и в таблицу `tests/endpoints.py` — паритет sync/async проверяется
  автоматически.

## Коммиты

- Сообщения на английском, без подписей и трейлеров от ботов.
- **Не бампайте `version` в `pyproject.toml`** — версию выставляет
  мейнтейнер при релизе через `lota push vX.Y.Z`.

## Pull Request

1. Форк → ветка от `main` → PR в `main`.
2. Опишите, что меняется и зачем; если поведение меняется — скажите об этом
   явно.
3. CI (`ruff` + `pytest` на Python 3.10–3.13) должен быть зелёным —
   публикация на PyPI гейтится этими же проверками.

## Обратная совместимость

Публичные имена (`SyncFPA`, `AsyncFPA`, `get_token_sync`, `get_token_async`,
`AddressType`, `STANDART_HEADERS`, `STANDARD_HEADERS`, `retry_on_error` и
константы-алиасы) ломать нельзя без явного обсуждения в issue.
