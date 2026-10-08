# Aurora — окружение и отчёт STAGE 0

Проверено 2026-10-07, около 18:27–18:30 +03:00. Это снимок окружения,
не фиксация версий будущего проекта. Рабочий каталог: `/home/liman/aurora`.

## Исходное состояние

В каталоге были только:

| Файл | Размер |
|---|---:|
| `README.md` | 310 bytes |
| `PROJECT_AGENT_PROMPT-1.md` | 30 078 bytes |
| `ui_reference_liquid_glass.png` | 2 318 860 bytes, PNG RGB 1672 × 941 |

`git status` сообщил, что каталог не является Git-репозиторием.
Backend/Android source, Gradle Wrapper, `pyproject.toml`, `.env`,
`local.properties` и проектные сборочные конфигурации отсутствовали.
README ссылался на несуществующий `PROJECT_AGENT_PROMPT.md`; ссылка исправлена.

## Инструменты

| Инструмент / ресурс | Обнаружено |
|---|---|
| ОС | Arch/CachyOS, Linux 7.2.9-1-cachyos, x86_64 |
| RAM / swap | ~7,6 GiB / ~7,6 GiB; доступная RAM при проверке ~2,9 GiB |
| Диск проекта | ~127 GiB свободно |
| Git | `/usr/bin/git` |
| Python по умолчанию | 3.14.7, `/usr/bin/python` |
| uv | 0.12.3, `/home/liman/.local/bin/uv` |
| uv-managed Python | 3.13.15, 3.12.13, 3.11.15 |
| Java / javac по умолчанию | OpenJDK 17.0.20.1 |
| Другой установленный JDK | `jdk-openjdk` 27.u35-2; `/usr/lib/jvm/java-27-openjdk` |
| Kotlin CLI | kotlinc-jvm 2.4.20 |
| Системный Gradle | 9.8.0, launcher JVM 17; embedded Kotlin 2.4.10 |
| Gradle cache | Найден каталог distribution 9.1.0; это не wrapper проекта |
| ADB в PATH | `/usr/bin/adb`, 1.0.41 / package 37.0.0-android-tools |
| Android SDK | `/opt/android-sdk` |
| Android CLI | `/opt/android-sdk/cmdline-tools/latest/bin/android`, 1.0.16500706 |
| Дополнительный CLI entry | `/home/liman/.android/bin/android-cli` |
| sdkmanager | `/opt/android-sdk/cmdline-tools/latest/bin/sdkmanager`, перенаправляет в новый Android CLI |
| pytest / Ruff / Pyright в PATH | Не обнаружены; project-local dev environment ещё не создан |

`ANDROID_HOME`, `ANDROID_SDK_ROOT`, `JAVA_HOME`, `GRADLE_USER_HOME` не заданы
в окружении агента. `android` и `sdkmanager` не найдены через PATH, но доступны
по абсолютным путям выше. Проверена исполняемость CLI и чтение `android.jar`.

### Установленные SDK-компоненты

Определены из локальных `package.xml`, без загрузки Android system images:

- `cmdline-tools;latest` — 23.0.
- `platform-tools` — 37.0.1 внутри SDK (системный adb имеет другую версию).
- `platforms;android-34` revision 3; `android-35` revision 2; `android-36` revision 2.
- `build-tools;35.0.0`, `36.0.0`, `37.0.0`.
- `build;templates` — 0.1.1.
- Найден `/opt/android-sdk/licenses/android-sdk-license`; это не подтверждение
  лицензий для всех будущих загружаемых компонентов.

На этапе 9 задать SDK через локальную конфигурацию и использовать согласованный
ADB binary. Установленный системный Gradle не заменяет project Gradle Wrapper.

## Физическое устройство

```text
$ adb devices -l
List of devices attached

Physical device: отсутствует
ADB status: список пуст
Android/API, model, resolution, ABI: неизвестны — устройства нет
Physical device verification: BLOCKED — no authorized ADB device connected.
```

Build / Install / Launch / Runtime logs / Performance: N/A для STAGE 0,
приложения ещё нет. При подключении телефона проверить ровно выбранное устройство,
его API/model/ABI/resolution и authorization. Идентификатор устройства не нужен
в общей проектной документации. Автоматический запуск эмулятора не предусмотрен.

## Выполненные проверки

- Размеры и состав файлов, отсутствие Git/build configs.
- `python --version`, `uv --version`, `uv python list --only-installed`.
- `java -version`, `javac -version`, `kotlinc -version`, `gradle --version`.
- `adb version`, `adb devices -l`; чтение локального SDK manifest inventory.
- `android --version`, help для `android docs search`.
- Визуальный просмотр уменьшенной копии референса в `/tmp/opencode/`.
- Поиск технической документации через Context7: FastAPI modules/DI,
  Compose blur, shared-element limitations и predictive back.
- Попытка `android docs search` не удалась при инициализации локального индекса
  (`write.lock` / concurrent index change). CLI попытался загрузить Knowledge Base;
  сведения об API получены через Context7. Это не блокирует STAGE 1.
- Проверка документации — **PASS**: локальные ссылки, парность code fences,
  отсутствие trailing whitespace, наличие этапов 0–21 и всех восьми API routes.
- SHA-256 исходного брифа и PNG совпали с исходными значениями.
- Расчёт контраста непрозрачных текстовых пар — **PASS**: минимум 6,25:1;
  белого текста CTA на двух концах action-gradient — 6,74:1 и 7,31:1.
  Прозрачные поверхности поверх artwork требуют отдельной проверки в UI.

Проверка будущей матрицы AGP/Gradle/JDK и практическая производительность
Compose/WebView остаются задачами этапов реализации, а не результатом этого аудита.

## Отчёт этапа

**DONE — STAGE 0.**

- Implemented: аудит окружения, анализ референса, архитектурные границы,
  модульная карта, tokens/components/motion specification и roadmap.
- Files changed: `README.md`; добавлены `ARCHITECTURE.md`, `DESIGN_SYSTEM.md`,
  `API.md`, `TODO.md`, `ENVIRONMENT.md`.
- Tests/checks: проверки окружения и документации выше выполнены; структура,
  ссылки, roadmap, исходные файлы и базовый контраст — PASS. Unit/build tests — N/A.
- Problems discovered: нет Git-репозитория и ADB device; SDK CLI отсутствует
  в PATH; phone performance и embed progress не проверены; Android docs index error.
- Remaining: STAGE 1 и последующие задачи из `TODO.md`.
- Next recommended stage: **STAGE 1 — Backend skeleton**, по отдельному указанию.

## Обновление после STAGE 1 — 2026-10-07

Исходный снимок STAGE 0 выше сохранён как история. Текущее состояние:

- Инициализирован Git, ветка `main`; настроен `.gitignore`.
- Создан `backend/` с uv-managed `.venv` на Python 3.13.15 и `uv.lock`.
- Runtime: FastAPI 0.142.2, Starlette 1.7.0, Pydantic 2.13.5,
  pydantic-settings 2.15.0, httpx 0.28.1, Uvicorn 0.54.0.
- Dev: pytest 9.1.1, Ruff 0.16.10, Pyright 1.1.414, httpx2 2.13.1.
- Исправлена несовместимость проверок с актуальным TestClient: Starlette 1.7
  предпочитает `httpx2`, который добавлен только в dev-зависимости.
- **50 tests passed**, Ruff lint/format PASS, Pyright strict: 0 errors/warnings.
- Реальный HTTP smoke Uvicorn на временном loopback-порту: health 200 с JSON
  и request ID, OpenAPI с единственным `/health`; процесс затем остановлен.
- Попытка дополнительного read-only review через Claude CLI завершилась
  `Not logged in`; внешнее review не выполнено. Основные проверки выполнены локально.
- Следующий этап — **STAGE 2 — AMD parser proof of concept**.

## Обновление после STAGE 2 — 2026-10-07

- Обычным GET получена публичная карточка
  `https://amd.online/1489-protivostojanie-svjatogo.html`: HTTP 200, 351 762 bytes.
- Добавлены BeautifulSoup 4.15.0 / Soup Sieve 2.10; версии зафиксированы в uv.lock.
- Реализован чистый parser пяти metadata fields, централизованы AMD selectors
  и URL patterns; добавлен минимизированный HTML fixture с provenance.
- **85 tests passed** (35 новых parser tests), Ruff lint/format PASS,
  Pyright strict — 0 errors / 0 warnings.
- Полный сохранённый response и fixture дали идентичные пять полей.
  Исходник использован только как локальный исследовательский artifact;
  воспроизводимые тесты зависят от fixture в репозитории.
- Обнаружены особенности: clan avatar перед poster image; ссылка «дунхуа»
  относится к подборкам; год имеет собственный `/anime/god/YYYY/` URL.
- Следующий этап — **STAGE 3 — Anime details backend**.

## Обновление после STAGE 3 — 2026-10-07

- Добавлен `/anime/{id}`, CatalogService, camelCase AnimeResponse и AMD provider.
- Публичный `index.php?newsid=1489` вернул 301 на detail URL с тем же ID.
- **111 offline tests passed**, Ruff lint/format PASS, Pyright strict 0 errors/warnings.
- Live smoke через ASGI TestClient с настоящим AMD HTTP: `/anime/amd:1489` → 200,
  «Противостояние святого», 2023; завершён 2026-10-07 около 20:24 UTC.
- Следующий этап — **STAGE 4 — Search backend**.

## Обновление после STAGE 4 — 2026-10-07

- Публичная форма поиска AMD: POST, q 3–25 символов, 10 карточек на source page.
- Сохранены четыре минимизированные fixtures и provenance JSON; metadata-фильтры
  в форме отсутствуют, API отклоняет их с 422 до обращения к источнику.
- Реализован `/search`, pagination до 50 на API page, SearchService/capabilities.
- **138 tests passed**, Pyright strict 0 errors/warnings, Ruff lint/format PASS.
- Live smoke около 20:31 UTC: «Наруто» → 1 результат; «мир», page=2/pageSize=7 →
  7 карточек из 191, HTTP 200. Исходящие соединения в offline suite запрещены.
- Следующий этап — **STAGE 5 — Home backend и кэш**.

## Обновление после STAGE 5 — 2026-10-08

- Исследованы публичные `/`, `/ongoingi/`, `/top-100-1.html` AMD;
  fixtures/provenance получены 2026-10-07 UTC.
- Добавлены `/home` и `/releases/latest`, отдельные CacheService/CachedAnimeProvider.
  Кэш ограничен 128 завершёнными записями; TTL home=600s, releases=180s,
  details=10800s, search=60s; single-flight, LRU, cancellation-safe ожидание.
- **151 offline test passed**, Pyright strict 0 errors/warnings, Ruff lint/format PASS.
- Live smoke 2026-10-07 около 20:41 UTC: home → HTTP 200, 14 featured,
  12 новых тайтлов, 10 релизов, 12 ongoing, 20 popular. Повторный `/home`
  вернул идентичный cached payload (около 4 мс против 803 мс первого запроса).
- `/releases/latest` → HTTP 200, total=10, `scope=RECENT_WINDOW`.
  Относительные source dates не интерпретируются без подтверждённой timezone;
  release timestamps/season/playerId unknown, доступность playback ещё не подтверждена.
- Документация обновлена; следующий этап — **STAGE 6 — Episodes backend**.

## Обновление после STAGE 6 — 2026-10-08

- Публичные карточки AMD содержат числовые episode links, повторяющиеся в
  PWA/web/player блоках. Следующая невышедшая серия может уже иметь свою строку.
- Пять fixtures и provenance (source/fixture hashes), полное равенство нормализованных
  списков из исходного HTML и fixtures подтверждено при их подготовке.
- Реализованы get_episodes, EpisodeService, DTO, `/anime/{id}/episodes` и TTL=180s.
  ID совместимы с релизами; source seasons неизвестны, фильтр → 422 до сети.
- **198 offline tests passed**, Ruff lint/format PASS, Pyright strict 0 errors/warnings.
- Live smoke около 01:36 UTC: amd:1489 page=4/pageSize=50 → 12 из 162;
  amd:5781 → 2; amd:1925 → 1; amd:5796 → 5; amd:5790 → 0; все HTTP 200.
  Повторные cached payloads идентичны, refactored details fetch также вернул 200.
- Playback не проверяется по одному data-vlnk: OVA имеет другой player при пустом
  атрибуте; season/playerId/availability пока не определяются из player-разметки.
- Следующий этап — **STAGE 7 — Player discovery**.

## Обновление после STAGE 7 — 2026-10-08

- Публичные AMD episode pages получены обычными GET, шесть HTTP 200;
  iframe/navigation fixtures и provenance добавлены, full/fixture equality PASS.
- AmdPlayerProvider реализует отдельный Protocol; lookup/detail/episode GET
  используют общий bounded pages helper. Обращений к vendor в resolver нет.
- Live smoke около 01:49 UTC: amd:1489-e2 → RUTUBE; amd:5781-e1 → Kodik;
  amd:5796-e3 → Kodik; amd:1925-e1 → VK. Следующие 1489-e162/5781-e2 →
  PLAYER_UNAVAILABLE. Refactored details/episodes также прошли live regression.
- Отдельные статические GET vendor: RUTUBE/Kodik/Aser HTTP 200, VK ConnectError.
  Ни один результат не заявляется как проверенный video playback.
- Официальный RUTUBE embed API документирует currentTime/duration/seek;
  PlayerCapabilities в Aurora всё ещё progress/seek/fullscreen=false до adapter/device tests.
- Android документация проверена через Context7, Android CLI docs и официальный
  security guide. `/opt/android-sdk/platform-tools/adb devices -l` вновь пуст;
  WebView playback/cookies/fullscreen/resume verification BLOCKED. Emulator не запускался.
- **261 offline tests passed**, Ruff lint/format PASS, Pyright strict 0 errors/warnings.
  Claude CLI loggedIn=false, поэтому дополнительное внешнее review не выполнялось.
- Подробности: [PLAYER_DISCOVERY.md](PLAYER_DISCOVERY.md).
  Следующий этап — **STAGE 8 — Player API**; HTTP route/default DI пока не подключены.
