# Aurora — план разработки

Обновлено: 2026-10-08. Этапы выполняются по одному с отчётом и остановкой.

## DONE

- [x] **STAGE 0 — Repository and environment analysis.**
  - Проверены файлы проекта, конфигурации, Git, Python/uv, Java/Kotlin/Gradle.
  - Обнаружены Android SDK/CLI, platforms/build-tools и ADB.
  - Выполнен `adb devices -l`: устройств нет.
  - Изучен визуальный референс Home/Browse/Details и motion concepts.
  - Подготовлены `ARCHITECTURE.md`, `DESIGN_SYSTEM.md`, `API.md`, `ENVIRONMENT.md`.
  - Обновлён README с правильным именем исходного брифа и навигацией по документам.
  - Зафиксированы карта модулей, риски и границы дальнейших этапов.

- [x] **STAGE 1 — Backend skeleton.**
  - Git `main` и `.gitignore`; Python 3.13 / uv / lockfile / dev tools.
  - FastAPI app factory/lifespan, Settings, JSON logging, error envelope/request IDs.
  - `GET /health` с независимостью от источников.
  - Раздельные `AnimeProvider`/`PlayerProvider`, capabilities, normalized models.
  - 50 offline tests: settings, errors, validation, fake-provider DI, lifecycle.
  - Ruff lint/format PASS; Pyright strict 0 errors/warnings.
  - Uvicorn HTTP smoke: health 200, request ID, OpenAPI только `/health`.
  - Документация запуска/контрактов обновлена.

- [x] **STAGE 2 — AMD parser proof of concept.**
  - Одна реальная публичная страница «Противостояние святого»: HTTP 200.
  - Минимизированный HTML fixture с URL/датой/source hash и описанием очистки.
  - Чистый parser пяти полей и общие AMD selectors/URL patterns.
  - Учтены вложенная картинка клана, genre/collection links и точный year link.
  - 35 новых offline tests; весь suite — 85 passed, Ruff/Pyright PASS.
  - Полная сохранённая страница и fixture дали одинаковый metadata result.

- [x] **STAGE 3 — Anime details backend.**
  - Числовой AMD ID и публичный lookup с проверкой redirect identity.
  - AMD provider на lifespan HTTP client, CatalogService, AnimeResponse и route.
  - 111 offline tests, Ruff/Pyright PASS; live `/anime/amd:1489` → 200.
  - Документация конфигурации, ошибок и запуска обновлена.

- [x] **STAGE 4 — Search backend.**
  - Публичная форма поиска, четыре реальные HTML fixtures и provenance.
  - Search provider/service/DTO/route, нормализация и агрегированная pagination.
  - Типизированные filters и capability validation; AMD metadata-фильтры → 422.
  - 138 offline tests, Ruff/Pyright PASS; два live search smoke → HTTP 200.

- [x] **STAGE 5 — Home backend и кэш.**
  - Главная, онгоинги и «Топ 100» AMD: три реальные HTML fixtures и provenance.
  - `/home`: featured, latest, newReleases, ongoing, popular; HTTP DTO.
  - `/releases/latest`: pagination внутри видимого окна, `scope=RECENT_WINDOW`.
  - Отдельные CacheService/CachedAnimeProvider: TTL/LRU, single-flight и shutdown.
  - 151 offline test, Ruff/Pyright PASS; live home/releases → HTTP 200, cache hit.
  - Документация API, архитектуры, запуска и ограничений обновлена.

- [x] **STAGE 6 — Episodes backend.**
  - Пять реальных fixtures: длинный сериал, второй сезон, фильм, OVA и анонс.
  - `get_episodes()`, EpisodeService, DTO и `/anime/{id}/episodes`.
  - Общая identity с релизами; проверка URL/номеров/копий навигации, pagination.
  - Неизвестные season/playback сохранены; AMD season filter → 422 до сети.
  - Episodes TTL=180s с изоляцией anime/page/pageSize/season в ключе.
  - 198 offline tests, Ruff/Pyright PASS; пять live episodes smoke → HTTP 200.
  - Полные HTML и минимизированные fixtures дали идентичные Episode lists.

- [x] **STAGE 7 — Player discovery (backend).**
  - Шесть реальных episode-page fixtures, source provenance и full/fixture equality.
  - Независимый AmdPlayerProvider: numeric ID → detail → published episode → iframe.
  - Allowlisted HTTPS RUTUBE/Kodik/VK/Aser, placeholders, active identity и redirects.
  - PlayerCapabilities по умолчанию false; RUTUBE progress/seek документированы,
    но Android adapter/runtime не проверены; WebView requirements записаны.
  - 261 offline test, Ruff/Pyright PASS; live четыре embeds/две заглушки подтверждены.
  - `PLAYER_DISCOVERY.md`, ADB повторно пустой; device playback остаётся BLOCKED.

## IN PROGRESS

Нет активного этапа. STAGE 7 backend discovery завершён; ожидается указание начать STAGE 8.

## NEXT

- [ ] **STAGE 8 — Player API.**
  - PlayerService, camelCase discriminated HTTP DTO и `GET /player/{episode_id}`.
  - Подключить независимый player provider/settings/DI, не связав с catalog settings.
  - API tests: WEB_EMBED, permitted URL cases, invalid/missing/unavailable,
    typed upstream errors и capabilities без ложного обещания resume.
  - Документация, проверки и остановка перед Android skeleton.

## LATER

| Этап | Результат | Критерий проверки |
|---|---|---|
| 9 — Android skeleton | Compose, navigation, DI, network, Room/DataStore, theme/motion shell | Build/unit/static + install/launch/navigation/logcat на телефоне |
| 10 — Design foundation | Glass/components, previews/showcase | Читаемость, Basic/Enhanced, font scale, скролл на телефоне |
| 11 — Motion foundation | Wave/Orb/shared poster/tab prototypes, Motion Demo | Cancel/back/repeat tap/rotation/reduced motion/frame pacing |
| 12 — Home UI | Hero, секции, состояния, локальный Continue Watching contract | API mapping, loading/retry, изображения/скролл на телефоне |
| 13 — Browse/Search UI | Debounce, filters sheet, grid | Отмена запросов, сохранение фильтров, empty/error, keyboard/insets |
| 14 — Details UI | Artwork, metadata, tabs, episodes, actions | Длинные списки, poster transition и back на телефоне |
| 15 — Player UI | Embed, fullscreen, orientation, back/lifecycle | Нет фонового звука/утечек после выхода, unavailable UI |
| 16 — History | Room, continue/progress/completed | Перезапуск приложения, корректные timestamps, реальные возможности player |
| 17 — Favorites/Library | Add/remove, библиотека | Идемпотентность, offline snapshots, сохранение после перезапуска |
| 18 — Navigation polish | Финальные bar/orb и major transitions | Стабильный back stack, process recreation, reduced motion |
| 19 — Notifications | Release tracking, отдельно выбранный push/poll подход | После стабильного MVP, дубликаты/разрешения/timezone |
| 20 — Performance/polish | Startup/memory/scroll/blur/WebView/cache | Замеры на телефоне, локальные оптимизации и записанные компромиссы |
| 21 — Android TV | Отдельная адаптация | Только после стабильной мобильной версии |

### Вопросы, которые нужно закрыть в нужном этапе

- [x] На этапе 2: подтвердить публичный metadata HTML одной AMD-страницы и реальные selectors.
- [x] На этапе 3: проверен публичный lookup по source ID; `amd:1489` независим от slug.
- [x] На этапе 4: публичный поиск AMD поддерживает только q; metadata-фильтры
  отсутствуют в форме и явно отклоняются. Combined catalog filters требуют отдельного исследования.
- [x] `/releases/latest` включён в этап 5 и реализован; область данных явно
  ограничена видимым окном главной AMD (`RECENT_WINDOW`).
- [x] На этапе 6: ID серий совместимы с релизами; дубли навигации удаляются,
  фильм/OVA — отдельные тайтлы. Seasons неизвестны, фильтр явно отклоняется AMD.
- [ ] После исследования источника согласовать небольшой отдельный подэтап
  `/schedule`: timezone, date precision, модель и fixtures/API tests.
- [x] На этапе 7: RUTUBE официально документирует progress/duration/seek;
  другие vendors пока не подтверждены. Android-интеграция и точный resume
  не считаются выполненными до физических проверок этапов 15/16.
- [ ] На этапе 9: applicationId, совместимая версия сборочной цепочки,
  min/compile/target SDK, base URL debug API и IA центрального orb.
- [ ] На этапе 9: для локального backend через USB рассмотреть `adb reverse`
  и debug-only network config; не расширять production cleartext policy.
- [ ] На этапе 10: режимы glass и контраст поверх реальных изображений.
- [ ] Перед MVP: подтвердить необходимые catalog/feed endpoints; история,
  library и playback проходят единый пользовательский сценарий.

## BLOCKED

- **Physical device verification: BLOCKED — no authorized ADB device connected.**
  `adb devices -l` на STAGE 0 и повторно на STAGE 7 вернул пустой список. Сборочные/unit/static проверки
  будущих этапов могут выполняться; emulator не является автоматической заменой.
- **WebView playback/fullscreen/progress/seek: BLOCKED для physical verification.**
  RUTUBE API документирован, но Aurora Android adapter ещё не реализован;
  third-party cookies/географические ограничения/playback других vendors не проверены.

Отсутствие `ANDROID_HOME` и CLI в PATH — задача настройки перед Android build,
а не отсутствие SDK. Данные окружения: [ENVIRONMENT.md](ENVIRONMENT.md).

## Правило приёмки Android-этапов

С этапа 9 при подключённом телефоне каждый этап с runnable-изменениями включает
build → `adb devices` → выбор целевого физического устройства → install →
launch → проверку сценариев → application logcat. При нескольких устройствах
цель уточняется, команды выполняются с `adb -s`.

Отчёт: Physical device / ADB status / Android API / Build / Install / Launch /
Features manually verified / Runtime errors / Performance / Device-specific issues.
Отсутствие телефона записывается как BLOCKED, а не как успешный runtime test.
