# Aurora — архитектура

Статус: STAGE 7 backend discovery завершён, 2026-10-08.
Реализованы backend skeleton, AMD catalog API и независимый embed resolver;
остальная карта описывает последующие этапы.
Источник требований: [PROJECT_AGENT_PROMPT-1.md](PROJECT_AGENT_PROMPT-1.md).

## 1. Границы системы

```text
Публичные источники каталога
  → AnimeProvider: получение, разбор, нормализация
  → Catalog/Search/Release services + CacheService
  → FastAPI / JSON
  → Android network → data repositories → domain use cases
  → ViewModel / StateFlow → Compose

Episode → PlayerRepository → Backend PlayerService → PlayerProvider
  → PlayerInfo → Android PlayerEngine: WEB_EMBED | NATIVE_STREAM | EXTERNAL

Room → History/FavoritesRepository → use cases → UI
DataStore → SettingsRepository → use cases → UI
```

AMD (`amd.online`) — первый адаптер, а не основа доменной модели. Его разметка,
URL-шаблоны и селекторы ограничены `backend/app/providers/amd/`.
Android получает только нормализованные DTO. На этапе 2 исследована одна реальная
страница AMD; возможность публичного embed относится к этапу 7.

Каталог и воспроизведение используют разные интерфейсы: источник метаданных
не обязан предоставлять плеер. Замена плеера не меняет поиск, историю и избранное.

## 2. Предлагаемый стек

| Область | Решение для начала реализации | Причина |
|---|---|---|
| Backend | Python 3.13, uv, FastAPI, Pydantic 2 | Изолированное окружение, явный API-контракт; Python 3.13 уже установлен через uv |
| HTTP / HTML | httpx.AsyncClient, BeautifulSoup | Общий управляемый HTTP-клиент и простой fixture-first разбор |
| Хранение backend | SQLAlchemy 2, SQLite/aiosqlite; затем PostgreSQL/asyncpg | ORM отделён от моделей API, миграции при появлении таблиц |
| Backend quality | pytest, Ruff, Pyright | Offline-тесты контрактов и статические проверки |
| Android | Kotlin, Compose, Material 3, Navigation Compose | Нативная модульная оболочка и собственные визуальные примитивы |
| Android data | Retrofit + Kotlin Serialization, Coroutines/Flow | DTO отделены от domain; отмена устаревших запросов |
| Android local / DI | Room, DataStore, Hilt | История/избранное, настройки и явная сборка зависимостей |
| Изображения | Coil | Размер загрузки под компонент, memory/disk cache |
| Playback | WebView; адаптеры External Intent и Media3 по доступным источникам | WEB_EMBED — основной разрешённый сценарий |

Точные версии зависимостей фиксируются при соответствующем этапе в `uv.lock`
и Android version catalog/Gradle Wrapper. Системные Gradle/Kotlin не определяют
версии проекта. Совместимость AGP, Gradle, JDK, Kotlin/Compose compiler, KSP и Hilt
проверяется совместно перед этапом 9.

Предварительный `minSdk = 26`; окончательный выбор — после проверки телефона
и требований библиотек. API 31+ сам по себе не гарантирует быстрый backdrop blur.
`compileSdk`/`targetSdk` выбираются на этапе 9 по совместимости и актуальным
требованиям; установленные платформы 34–36 перечислены в `ENVIRONMENT.md`.

## 3. Карта backend

Этап 7: `providers/amd/player.py::AmdPlayerProvider` не наследует AmdProvider.
Общий сетевой helper `pages.py` используется обоими, но не связывает их contracts.
ID эпизода проверяется в identity; resolver получает исходную episode-page ссылку
из навигации и проверяет active episode/iframe. Допустимы только наблюдённые
HTTPS host/path/query. Player route/default wiring — этап 8; catalog availability
не меняется, playback URL не входит в CacheService. 261 offline test и live
discovery smoke прошли; runtime playback не проверен. [Отчёт](PLAYER_DISCOVERY.md).

Этап 6: `api/routes/episodes.py` → `services/episodes.py` → `AmdProvider.get_episodes`
→ `providers/amd/episodes.py`. Общий `schemas/episodes.py` используется также Release DTO.
Details и episodes используют один bounded fetch helper с прежними URL/error checks.
Числовой episode ID централизован в AMD identity и совместим с release feed.
Все копии навигации сравниваются, результат сортируется и пагинируется; total
описывает реальные строки, включая source placeholders. Metadata season неизвестна,
AMD отклоняет фильтр. Availability/player mapping относятся к этапу 7.
Пять реальных fixtures и live endpoints проверены; 198 offline tests PASS.

Этап 5: `api/routes/home.py` и `schemas/home.py` добавляют `/home` и
`/releases/latest`. AMD `home.py` разбирает главную, первую страницу онгоингов
и публичный «Топ 100»; список эпизодов добавлен в этапе 6.
`HomeCatalog.new_releases` добавлен отдельно от `latest`: новые тайтлы и новые
серии имеют разный смысл. Лента релизов явно ограничена `RECENT_WINDOW`.
В composition root любой catalog provider обёрнут `CachedAnimeProvider`;
политика кэша отделена от HTML и routes. 151 offline test и live smoke прошли.

Этап 4: `api/routes/search.py` → `services/search.py` → `AmdProvider.search`
→ `providers/amd/search.py`. Параметры и ответ находятся в `schemas/search.py`;
domain SearchQuery дополнен filters. SearchService проверяет capabilities,
провайдер дополнительно проверяет ограничения своего источника.
AMD поддерживает q (3–25), но не metadata-фильтры; они явно отклоняются.
Пагинация API 1–50 агрегирует исходные страницы по 10 карточек с контролем total/IDs.
138 offline tests и live search smoke прошли.

Этап 3: `api/routes/anime.py` → `services/catalog.py` → `AmdProvider.get_anime()`
→ чистый parser. `schemas/anime.py` явно преобразует domain в camelCase DTO.
AMD подключён по умолчанию через lifespan-клиент; `AURORA_CATALOG_PROVIDER=none`
отключает его. Подмена provider через app factory/Depends сохраняется.
ID `amd:<число>` разрешается через публичный `index.php?newsid=...`, затем
проверенный same-origin redirect с сохранением source ID. Slug не хранится в ID.
Проверки: 111 offline tests, Ruff/Pyright и live AMD details request.

Реализованы `main.py`, `core/`, `api/dependencies.py`, `api/errors.py`, health route,
`models/`, `schemas/common.py`, `providers/base.py` и offline `tests/`.
AMD catalog adapter подключён через app factory/DI; остальные адаптеры — будущие этапы.
Lifespan создаёт и закрывает общий `httpx.AsyncClient`, даже при ошибке запроса.
Application logging — JSON с request ID и route template; HTTP ошибки имеют
единый envelope. Команды запуска/проверок — [backend/README.md](backend/README.md).

Этап 2 добавил `providers/amd/{parser,selectors,models}.py` и реальный
минимизированный fixture `tests/fixtures/amd_anime.html` с provenance.
`parse_anime_page(html, page_url=...)` — чистая функция без I/O, результат
`ParsedAnimeDetails` содержит ровно пять полей. Она не создаёт фиктивный ID
или полный Anime. Полный сохранённый source HTML и fixture проверены на равенство
всех пяти полей. Описание предположений: [AMD parser](backend/app/providers/amd/README.md).

Целевая структура, создаваемая постепенно (включая будущие модули):

```text
backend/
  pyproject.toml, uv.lock, .python-version
  app/
    main.py                     # app factory, lifespan, подключение routes
    api/
      dependencies.py           # сборка сервисов/провайдеров через Depends
      routes/                   # health, home, search, anime, releases, schedule, player
    core/                       # config, logging, exceptions
    models/                     # нормализованные Anime, Episode, Release, PlayerInfo
    schemas/                    # HTTP request/response, pagination, error envelope
    providers/
      base.py                   # AnimeProvider и отдельный PlayerProvider
      amd/
        provider.py, parser.py, selectors.py
        search.py, details.py, releases.py, episodes.py, schedule.py, player.py
    services/                   # catalog, search, releases, schedule, player, cache
    repositories/               # сохранение каталога/кэша, без HTML-разбора
    db/                         # engine/session, ORM tables; позже миграции
    utils/                      # http, parsing, общая normalization
  tests/
    fixtures/                   # amd_home/anime/search/releases.html по мере изучения
    providers/, services/, api/
```

- `models/` не зависит от FastAPI routes, SQLAlchemy или AMD. `schemas/` задаёт
  wire-контракт и использует явное преобразование; ORM-сущности живут в `db/`.
  На этапе 1 HTTP-схемы реализованы для health/error; catalog response DTO
  появятся на этапах соответствующих routes. Доменные модели сохраняют snake_case.
- Routes валидируют вход, вызывают сервис и преобразуют результат/ошибку.
  Здесь нет HTTP-запросов к AMD, селекторов и политики кэша.
- `AnimeProvider`: `get_home`, `search`, `get_anime`, `get_episodes`,
  `get_latest_releases`, `get_schedule`; поддержка фильтров/операций описывается
  capabilities. Неподдерживаемая операция не маскируется пустым успешным ответом.
- `PlayerProvider`: `get_player`, `supports_embed`, `get_embed_url`; не наследует
  каталог. Этап 1 задал интерфейс, этап 7 реализовал независимый AMD resolver.
- Сетевое получение и чистый parser разделены. Parser принимает сохранённый HTML,
  не управляет БД, кэшем и retry. Обязательные поля проверяются после разбора.
- `AsyncClient` и DB engine принадлежат lifespan; таймауты, лимиты соединений,
  ограниченные повторы transient-ошибок и закрытие ресурсов централизованы.
- Структурные логи: request ID, route, provider, duration, error code;
  cookies, секреты и URL-параметры с токенами не записываются.

## 4. Модели и идентичность

- `Anime`: `id`, `provider`, `provider_id`, `title`, `original_title`,
  `alternative_titles`, `description`, `poster_url`, `backdrop_url`, `year`,
  `status`, `type`, `genres`, `rating`, `episode_count`, `current_episode`,
  `age_rating`, `voiceovers`, `updated_at`.
- `Episode`: `id`, `anime_id`, `season`, `number`, `title`, `release_date`,
  `thumbnail`, `available`, `player_id`.
- `Release`: `anime`, `episode`, `released_at`, `provider`.
- `PlayerInfo`: `provider`, `type`, `embed_url`, `quality_hint`; прямой поток
  и внешний адрес получают отдельные поля с проверкой по типу (см. `API.md`).

`id` — непрозрачная для Android стабильная строка с пространством провайдера.
Алгоритм backend кодирует source ID безопасно для URL path, без `/`; сохраняет
`provider_id` отдельно. ID эпизода включает идентичность тайтла и выпуска,
а не временный URL плеера. Конкретное соответствие определяется по fixture.
Объединение одинаковых тайтлов разных провайдеров — отдельная будущая задача.

Неизвестные значения остаются `null`/`UNKNOWN`, а не выдуманными датами,
рейтингами и номерами серий. Рейтинг нормализуется к 0–10 только если шкала
источника известна. `updated_at` — время обновления нашей записи, не релиза.
Этап 6 подтвердил числовую навигацию AMD: фильм/OVA — отдельные тайтлы;
сезоны явно не указаны, дробные/именованные ключи не обнаружены и пока отклоняются.
Начальный `Episode.number` допускает конечное неотрицательное число (включая
дробное), `season` — неотрицательное целое или null. `available` по умолчанию
false до подтверждения источником. Release проверяет связь Episode → Anime.
Временные метки принимают только timezone-aware значения и приводятся к UTC.

Этап 1 использует generic `Page[T]`, `Pagination`, минимальный `SearchQuery`,
`HomeCatalog` и предварительный `ScheduleEntry` для типизированных Protocol.
`HomeCatalog` не содержит персональную историю; поле HTTP `continueWatching`
реализовано в схеме `/home` как первоначально пустой список.
Provider capabilities описывают операции;
неподдерживаемые вызовы должны поднимать `UnsupportedOperation`.

## 5. Кэш и локальные данные

Реализованный `CacheService` получает clock и размер через конструктор;
начальное хранилище — собственный OrderedDict, максимум 128 завершённых записей.
Это in-process TTL/LRU-cache на один backend worker. Внешний cache repository
понадобится при переходе к общему хранилищу для нескольких workers.

| Данные | Начальный TTL |
|---|---:|
| home | 600 секунд |
| latest releases | 180 секунд |
| episodes (anime ID + page/pageSize + season) | 180 секунд |
| anime details | 10 800 секунд |
| search | 60 секунд |
| genres/filter metadata (план) | 86 400 секунд |
| schedule (план) | 1 800 секунд |

Ключ: provider + операция + нормализованные фильтры/query/page + версия схемы.
Реализованы single-flight, LRU eviction, expiry и тесты с управляемыми часами.
TTL начинается после успешной загрузки; deepcopy изолирует cache value от потребителей.
Отмена waiter не отменяет общую загрузку; lifespan отменяет pending tasks и
дожидается их завершения до закрытия клиента. Ошибки не кэшируются.
Stale/partial выдачи пока нет. Ключи home/release pages независимы.
Персональные данные и временные playback URL не входят в общий catalog cache.

История и избранное первоначально принадлежат Room на устройстве, настройки —
DataStore. Backend не заводит фиктивного «общего пользователя».
`/home.continueWatching` первоначально пуст; Android объединяет каталог с Room.
Для работы offline сохранять рядом с history/favorites небольшой snapshot
нормализованного тайтла, а не только ID; не дублировать весь каталог без нужды.

History: `animeId`, `episodeId`, `position`, `duration`, `updatedAt`, `completed`.
Единица position/duration — миллисекунды; неизвестная duration — `null`.
Порог completed: 95% при известной положительной duration либо достоверное
событие завершения. Favorites: `animeId`, `addedAt`. Записи идемпотентны по ID.

## 6. Карта Android и зависимости

```text
android/
  settings.gradle.kts, build.gradle.kts, gradle.properties
  gradle/libs.versions.toml, gradle/wrapper/, gradlew, gradlew.bat
  app/                          # Application, DI composition root, NavHost
  core/
    model/                      # чистые Kotlin domain-модели
    common/                     # ошибки/result, dispatchers, небольшие общие контракты
    domain/                     # repository interfaces, use cases
    data/                       # реализации repositories, DTO/entity ↔ domain
    network/                    # AnimeApi, DTO, HTTP client
    database/                   # Room entities, DAO, migrations
    preferences/                # DataStore adapter
    designsystem/               # theme, tokens, components, motion, previews
    navigation/                 # маршруты и события, без feature implementation
    player/                     # PlayerEngine и Android-адаптеры воспроизведения
  feature/
    home/, browse/, search/, details/, player/
    library/, history/, settings/, schedule/
```

`domain`, `data`, `preferences` дополняют рекомендованную в брифе карту, чтобы
UseCase/Repository/DataStore имели явное место и не попадали в UI или `common`.

Правила compile-time зависимостей:

```text
core:domain       → core:model, core:common
core:network      → core:common (+ собственные DTO)
core:database     → собственные entities/DAO
core:preferences → собственные settings storage types
core:data         → domain, model, common, network, database, preferences
core:player       → model, common (+ Android WebView/позже Media3)
core:designsystem → Compose/Material 3; без network, data и features
core:navigation  → контракты маршрутов; без feature-модулей
feature:*         → domain, model, common, designsystem, navigation
feature:player    → также core:player
app               → features + data + player (DI и сборка графа)
```

Features не зависят друг от друга. UI-компоненты принимают display-модели и
callbacks; ViewModel управляет `UiState`, анимация остаётся UI-задачей.
Интерфейсы `AnimeRepository`, `PlayerRepository`, `HistoryRepository`,
`FavoritesRepository`, `SettingsRepository` находятся в `core:domain`.
Ни Compose, ни ViewModel не обращаются непосредственно к Retrofit/DAO.

Поиск: debounce ~300 мс, отмена предыдущего запроса и защита от запоздалого
ответа; фильтры — типизированное состояние. Навигация передаёт ID, не большие
объекты и не player URL. Состояния loading/content/empty/error различаются.
History/favorites используют Flow; UI подписывается с учётом lifecycle.

## 7. Playback и ограничения возможностей

`WEB_EMBED` использует только публичную embed/player-страницу. Этап 7 подтвердил
mapping и allowlisted embed форматы RUTUBE/Kodik/VK/Aser. Требования cookies и
реальная доступность playback проверяются на физическом устройстве, не по HTTP 200.
`NATIVE_STREAM` допустим для явно разрешённого прямого URL. `EXTERNAL` запускает
внешний обработчик с понятной ошибкой при его отсутствии. Отсутствующий embed
возвращает `PlayerUnavailable`, а не запускает поиск защищённого потока.

WebView принадлежит lifecycle экрана: обработка custom fullscreen view,
ориентации, back, остановки звука, ухода в фон и уничтожения. Back сначала
закрывает fullscreen, затем выполняет согласованную политику возврата.
JS/cookies включаются по реальным требованиям разрешённого плеера; произвольный
JavaScript bridge, смешанный контент и небезопасный file access не нужны.

**Точный resume — подтверждённая возможность API RUTUBE, но ещё не интеграция Aurora.**
Документированы currentTime/durationChange/setCurrentTime через postMessage.
Нужны доверенная iframe-оболочка, origin/source validation и ограниченный канал
к Android; addJavascriptInterface нельзя предоставлять vendor pages/всем frames.
У других vendors progress/seek не подтверждены: fallback — последний эпизод.
PlayerCapabilities в WebEmbed domain по умолчанию progress/seek/fullscreen=false
до реализации/проверки соответствующего Android адаптера (этапы 15/16).
Device playback, реклама, cookies и точный resume пока не выполнены;
это не обнаруженный отказ API. [Ограничения и evidence](PLAYER_DISCOVERY.md).

## 8. Риски и проверка

| Риск | Решение / контрольный этап |
|---|---|
| Изменение AMD, неоднозначные поля | Fixtures, централизованные selectors, явная ParsingError; этапы 2–7 |
| Embed разрешается, но playback не работает | Runtime device tests, cookies/region/ошибки vendor; backend discovery не гарантирует проигрывание |
| Нет общего API прогресса у vendors | RUTUBE API документирован; origin-bound Android adapter и отдельные device tests необходимы |
| Backdrop blur и layered overdraw | Basic glass + локально измеряемый Enhanced; этап 10 |
| Liquid transitions конфликтуют с back/отменой | Один transition coordinator, прототип на этапе 11 |
| WebView не участвует в Compose shared elements | Анимация оболочки/постера, отдельный lifecycle; этапы 11/15 |
| Большие изображения и длинные списки | Coil size limits, Lazy с ключами, bounded cache; этапы 12–14 |
| Несовместимые сборочные версии | Wrapper + version catalog, проверить матрицу до этапа 9 |
| Ограниченная RAM ноутбука (~7,6 GiB) | Физический телефон, ограничить Gradle workers/heap по замерам |
| SQLite → PostgreSQL | Миграции и проверка реальным PostgreSQL до заявления о совместимости |
| Schedule не выделен отдельным этапом брифа | `/releases/latest` реализован в этапе 5; `/schedule` требует отдельного согласованного подэтапа |

Backend tests: API через fake providers; parser через локальные fixtures;
cache через fake clock; временная БД для repository tests. CI по умолчанию
не зависит от AMD или проигрывания видео.
Android: repository/use case/ViewModel tests; критичные UI-навигационные сценарии
и производительность проверяются на физическом устройстве начиная с этапа 9.
Подробности визуального прототипирования — [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).

## 9. Источники технических решений

Документация проверена через Context7; версии API уточняются перед реализацией.

- [FastAPI: разбиение на модули](https://fastapi.tiangolo.com/tutorial/bigger-applications/).
- [FastAPI: подмена зависимостей в тестах](https://fastapi.tiangolo.com/advanced/testing-dependencies/).
- [Compose: изображения и blur](https://developer.android.com/develop/ui/compose/graphics/images/customize).
- [Compose: shared elements и ограничения AndroidView](https://developer.android.com/develop/ui/compose/animation/shared-elements).
- [Compose: shared elements и navigation/back](https://developer.android.com/develop/ui/compose/animation/shared-elements/navigation).
