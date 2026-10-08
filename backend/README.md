# Aurora backend

**STAGE 7 backend discovery завершён.** Работают AMD catalog API и TTL/LRU-кэш;
добавлен независимый AmdPlayerProvider, но player HTTP route пока не подключён.
Серии берутся из публичной навигации, лента релизов — из видимого окна главной.
Описание разметки: [app/providers/amd/README.md](app/providers/amd/README.md).

## Запуск

Из каталога `backend/` с установленным uv:

```bash
uv sync --locked
uv run --locked uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Python закреплён на 3.13 в `.python-version` и `pyproject.toml`; uv создаёт
локальную `.venv`. `uv.lock` фиксирует runtime- и dev-зависимости.

- `GET http://127.0.0.1:8000/health` → `200 {"status":"ok"}`.
- `http://127.0.0.1:8000/docs` — Swagger UI.
- `GET http://127.0.0.1:8000/anime/amd:1489` — карточка «Противостояние святого».
- `GET http://127.0.0.1:8000/anime/amd:1489/episodes?page=4&pageSize=50` — серии.
- `GET http://127.0.0.1:8000/search?q=мир&page=2&pageSize=7` — поиск с пагинацией.
- `GET http://127.0.0.1:8000/home` — нормализованные секции главной.
- `GET http://127.0.0.1:8000/releases/latest?page=1&pageSize=20` — окно последних серий.
- `http://127.0.0.1:8000/openapi.json` — шесть реализованных маршрутов, включая health.
- Остановка — Ctrl+C. Общий `httpx.AsyncClient` закрывается через lifespan.

## Конфигурация

Настройки читаются при `create_app()`, без network/БД side effects при import.
Порядок приоритета: явные аргументы Settings → environment → `.env` в текущем
рабочем каталоге → defaults. Пример значений — [`.env.example`](.env.example).

| Переменная | Default | Ограничение |
|---|---|---|
| `AURORA_ENVIRONMENT` | `development` | `development`, `test`, `production` |
| `AURORA_CATALOG_PROVIDER` | `amd` | `amd` или `none` для отключения каталога |
| `AURORA_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `AURORA_HTTP_TIMEOUT_SECONDS` | 10 | >0, ≤120, конечное число |
| `AURORA_HTTP_MAX_CONNECTIONS` | 20 | 1–100 |
| `AURORA_HTTP_MAX_KEEPALIVE_CONNECTIONS` | 10 | 0–100, ≤ max connections |

Невалидная конфигурация останавливает startup. `environment` — метка окружения,
не переключатель небезопасного debug: FastAPI traceback responses выключены.

Приложение пишет JSON-логи в stderr через `aurora.*`: timestamp, level, event,
request ID, route template, method, status, duration; для ошибок — стабильный
code и тип неожиданного исключения. Query strings, request body, authorization,
cookies и подробности provider exceptions в эти логи не включаются.
`--no-access-log` исключает дублирующий access log Uvicorn с сырыми URL.
Служебные startup/shutdown сообщения Uvicorn имеют собственный формат.

## Структура

```text
app/main.py               # create_app, lifespan, composition root
app/core/                 # settings, errors, JSON logging, request middleware
app/api/dependencies.py   # AppResources, отдельные dependencies providers
app/api/errors.py         # единый HTTP error boundary
app/api/routes/health.py  # liveness без обращения к каталогу
app/models/               # snake_case domain: Anime/Episode/Release/PlayerInfo
app/providers/base.py     # AnimeProvider, PlayerProvider, capabilities
app/providers/amd/        # details/search/home/releases/episodes, identity и selectors
app/providers/amd/player.py # public iframe resolver, не извлекает stream URLs
app/providers/amd/pages.py # bounded detail/episode-page GET для обоих providers
app/api/routes/episodes.py # список серий, query validation
app/services/episodes.py  # namespace/capabilities, проверка identity и season
app/services/cache.py     # TTL/LRU/single-flight, clock injection
app/services/cached_provider.py # provider-independent cache policy
app/schemas/home.py       # Home/Release response DTO
app/schemas/episodes.py   # общий Episode DTO, pagination/season query
app/schemas/common.py     # camelCase HTTP health/error schemas
tests/                    # config/API/models/DI, исходящие соединения запрещены
tests/fixtures/           # реальные AMD details/search/home/episodes/player fixtures и provenance
tests/providers/          # offline-проверки AMD parsers/providers/API
```

`create_app(settings, anime_provider=..., player_provider=...)` позволяет
инъекцию независимых адаптеров. FastAPI `dependency_overrides` поддерживается
для `get_anime_provider` и `get_player_provider`. По умолчанию каталог использует
`CachedAnimeProvider(AmdProvider(...))` с общим lifespan HTTP-клиентом.
Инъектированный в factory catalog provider также оборачивается кэшем.
При `AURORA_CATALOG_PROVIDER=none` catalog dependency выдаёт `PROVIDER_UNAVAILABLE`.
Player dependency пока выдаёт `PLAYER_UNAVAILABLE`, если отдельный player_provider
не инъектирован (независимо от catalog setting). Default wiring — этап 8.
Это не мешает liveness. Test-only probe routes остаются в тестах.

Кэш: 128 завершённых записей, in-process LRU; TTL home=600s, releases=180s,
episodes=180s, details=10800s, search=60s. TTL отсчитывается после загрузки. Ответы копируются,
поэтому потребитель не изменяет содержимое кэша. Одновременные запросы с одним
ключом используют одну загрузку; отмена одного ожидающего запроса не отменяет
загрузку для остальных. Ошибки не сохраняются. При shutdown pending-задачи
отменяются, и приложение дожидается их завершения до закрытия HTTP-клиента.
Размер/clock заданы в `CacheService`, TTL — в `CachedAnimeProvider`.

Запуск по умолчанию использует один worker. Несколько workers имеют независимые
кэши: для общего single-flight/TTL потребуется общее хранилище.

Поля доменных моделей не являются готовыми response DTO будущего каталога.
Сериализация соответствующих endpoint-схем будет добавляться вместе с routes.
`SearchQuery` задаёт строку, pagination и типизированные metadata-фильтры.
SearchService проверяет capabilities. AMD: q длиной 3–25, metadata-фильтры → 422.
`ScheduleEntry` — предварительная модель, без готового schedule API.

Episodes: данные нормализуются из `#elementb a.nav_video_links` публичной карточки.
Одинаковые PWA/web/player-копии объединяются, конфликтующие возвращают ParsingError.
`amd:<source ID>-episode-<number>` совпадает с ID в latest releases.
Числовой порядок стабилен независимо от сортировки HTML; total включает только
фактические строки, включая placeholder следующей серии. Фильм/OVA — отдельные
тайтлы. В AMD season неизвестен: переданный `season` → 422 до сети.
`available=false`, `playerId=null` пока не связываются с playback resolver:
получение списка не делает отдельный player GET для каждой серии.
У явного анонса без серий — пустая страница; у повреждённой навигации — ошибка.

Player discovery: `AmdPlayerProvider(client).get_player(episode_id)` получает
numeric lookup → публичную карточку → исходную episode page → проверенный iframe.
Возвращается WebEmbedPlayerInfo; unknown episode → NotFound, placeholder →
PlayerUnavailable. `get_embed_url` возвращает None только при PlayerUnavailable;
`supports_embed` означает наличие supported source iframe, не успешное playback.
Capabilities progress/seek/fullscreen=false до Android integration/device tests.
Общий catalog cache не сохраняет player URLs. HTTP/DI wiring — следующий этап.
Evidence и WebView policy: [PLAYER_DISCOVERY.md](../PLAYER_DISCOVERY.md).

## Проверки

В каталоге `backend/`:

```bash
uv sync --locked
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pyright
```

Результат STAGE 7: **261 tests passed** (62 player checks и один capabilities check),
Ruff lint/format PASS,
Pyright strict — **0 errors / 0 warnings**. Полный сохранённый HTML и минимизированная
фикстура дают одинаковые пять полей. HTTP smoke этапа 1: health 200, request ID
присутствует, OpenAPI содержит только `/health`.

Тесты проверяют:
- liveness и request IDs, OpenAPI и framework 404/405;
- typed domain errors, validation 422, unexpected/response-validation 500;
- отсутствие внутренних деталей ошибок в HTTP и application logs;
- `Retry-After`, lifecycle cleanup, request logging;
- Settings precedence/validation;
- nullable metadata, UTC, IDs, связи Release, ограничения pagination/query;
- discriminated PlayerInfo и HTTP(S) URL;
- независимую инъекцию/fake providers и unsupported operations.
- AMD metadata на реальной фикстуре: вложенное изображение клана, taxonomy links,
  отсутствие/изменение полей, кодировка, относительные URLs и ошибочные годы.

Тесты изолируют `AURORA_*`/dotenv и блокируют исходящие socket connections.
Starlette 1.7 TestClient использует dev-зависимость `httpx2`; рабочий HTTP-клиент
приложения остаётся `httpx.AsyncClient`. Warnings рассматриваются как ошибки.

Документы проекта: [архитектура](../ARCHITECTURE.md), [API](../API.md),
[этапы](../TODO.md). Следующий этап — **8: Player API**.

Player tests: шесть реальных episode-page fixtures, сравнение source-selected
iframe и навигации, allowlisted HTTPS host/path/query, placeholders, Kodik episode
и flags, неизвестные ID, безопасные redirects и limits, typed HTTP/transport/parser
errors. MockTransport проверяет, что resolver обращается только к AMD, не vendor.
Live 2026-10-08 около 01:49 UTC: RUTUBE/Kodik/Kodik/VK и две unavailable-заглушки.
Video не проигрывалось; WebView/cookies/fullscreen/resume проверка BLOCKED без телефона.

Episodes tests: пять реальных fixtures (series/season sequel/movie/OVA/announcement),
identity/release compatibility, сортировка и копии навигации, malformed labels/URLs,
явное отсутствие серий, ошибки источника, query validation, pagination/cache,
инъекция независимого provider с season support и проверка его результатов.
Live smoke 2026-10-08 около 01:36 UTC: amd:1489 (page=4/pageSize=50) → 12 из 162;
amd:5781 → 2; amd:1925 → 1; amd:5796 → 5; amd:5790 → 0. Все HTTP 200.
Повторные ответы из кэша совпали; shared detail fetch также проверен live.

Home/cache tests проверяют реальные fixtures главной/онгоингов/топа, обязательные
секции, episode ID и unknown timestamps, release window pagination, repeated hits,
TTL с fake clock, LRU eviction, копирование значений, single-flight, отмену запроса,
shutdown, изоляцию ключей и восстановление после upstream failure.
Live home/releases smoke прошёл; повторный home вернул тот же cached payload.

Search tests проверяют четыре реальные fixtures, явную пустую выдачу, изменения
разметки, объединение source pages, валидацию/неподдерживаемые filters и HTTP errors.
Live search smoke 2026-10-07: «Наруто» → 1 результат; «мир», page=2/pageSize=7 →
7 результатов, total=191. Источник может менять эти числа со временем.

Этап 3 проверяет цепочку HTTP MockTransport → AMD provider → CatalogService →
AnimeResponse → FastAPI, ошибки ID/источника/разметки, ограничение redirects/body
и lifespan wiring. Отдельный live smoke через ASGI TestClient и реальную сеть:
`/anime/amd:1489` → HTTP 200 (2026-10-07). В pytest сеть по-прежнему запрещена.
