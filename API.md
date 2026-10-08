# Aurora — API и планируемые контракты

**STAGE 7: реализованы `/health`, `/anime/{id}`, `/anime/{id}/episodes`, `/search`,
`/home`, `/releases/latest` и единая обработка ошибок. Исследован embed resolver;
HTTP Player API ещё не подключён.**
Остальные endpoints ниже — план. Нормализованные модели и интерфейсы providers
уже существуют; конкретные HTTP payloads фиксируются на соответствующих этапах.
Текущий OpenAPI: `/openapi.json`; интерактивная документация: `/docs`.

## Реализовано

`GET /health` → HTTP 200, `Content-Type: application/json`, `{"status":"ok"}`.
Проверяет живость процесса без зависимости от AMD, БД или настроенного провайдера.
Каждый HTTP-запрос получает новый серверный `X-Request-ID` (32 hex-символа);
входящий одноимённый header не считается доверенным идентификатором.
В ошибках `error.requestId` совпадает с response header, включая HTTP 500.

Ещё не реализованные маршруты возвращают общий 404; test-only probe routes
не включаются в приложение или его OpenAPI.

### Anime details

`GET /anime/amd:1489` возвращает нормализованный `Anime` в camelCase, включая
`providerId`, `posterUrl`, `alternativeTitles`, `episodeCount`, `updatedAt`.
AMD ID: `amd:<положительное число из 1–12 цифр без ведущих нулей>`.
Slug названия не является частью идентичности. Неверный ID → 422; неизвестное
пространство провайдера → 404. Эти ошибки не требуют запроса к источнику.

Сейчас известны title/poster/description/genres/year; остальные необнаруженные
поля остаются null, [] или UNKNOWN. `updatedAt` — UTC-время получения метаданных.
Ответ не означает доступность воспроизведения. Пример проверенного тайтла:
`id=amd:1489`, `providerId=1489`, `title=Противостояние святого`, `year=2023`.

Upstream 404/410 → NOT_FOUND; 429 → RATE_LIMITED (числовой Retry-After сохраняется);
transport/timeout → NETWORK_ERROR; неверный HTML → PARSING_ERROR;
403/5xx/неожиданный redirect → PROVIDER_UNAVAILABLE. Схемы ошибок есть в OpenAPI.

## Общие правила

### Реализованный поиск

`GET /search?q=мир&page=2&pageSize=7` → `{items, page, pageSize, hasNext, total}`.
`q` очищается от внешних пробелов; AMD принимает **3–25 символов** (общая domain
модель допускает 1–200 для других провайдеров). `page` ≥1, `pageSize` 1–50,
по умолчанию 20. Страница за концом выдачи возвращает `items=[]`, `hasNext=false`.
В карточках результата известны ID/title/poster; остальные поля пока unknown/null.

Параметры `genre`, `year`, `type`, `status`, `rating`, `voiceover`, `sort`
типизированы, но AMD не предоставляет их в публичной поисковой форме:
любой заданный metadata-фильтр → **422 UNSUPPORTED_OPERATION до сетевого запроса**.
Неверные значения и неизвестные параметры → 422 VALIDATION_ERROR.
Capability `search_filters` AMD пуст; другие провайдеры могут объявлять свой набор.
Фильтрация одной страницы выдачи не выдаётся за полноценный глобальный поиск.

AMD отдаёт по 10 результатов. API объединяет необходимые source pages;
число результатов берётся из HTML источника. Смена total/дубли при объединении
или повреждённая разметка → 502 PARSING_ERROR, не пустой успешный ответ.
Нулевая выдача принимается только с явным сообщением источника «не найдено».

- REST/JSON; пути из брифа сохраняются без неоговорённого префикса.
- JSON-поля — `camelCase`; внутренние Python-модели — `snake_case` с явными aliases.
  Android DTO повторяют JSON и отдельно преобразуются в domain.
- ID — непрозрачные строки, безопасные для path; клиент их не разбирает.
- Временные метки — ISO 8601 UTC с timezone. Известна только дата — отдельное
  date-значение без выдуманного времени. Неизвестные поля — `null`, коллекции — `[]`.
- Nullable metadata не означает ошибку. Отсутствующий тайтл и сбой провайдера
  различаются кодом ошибки.
- Списки: `{items, page, pageSize, hasNext, total}`; `page` от 1,
  `pageSize` по умолчанию 20, максимум 50; `total` может быть `null`.
  Адаптер не придумывает количество страниц, если источник его не сообщает.
- Поиск: `q` после trim, 1–200 символов; неподдерживаемые фильтры — явный 422,
  а не молчаливое игнорирование. Ограничения AMD указаны в разделе поиска выше.

## Маршруты

| Method / path | Ответ | Планируемый этап |
|---|---|---|
| `GET /health` | `{"status":"ok"}` — liveness, без запроса к AMD | 1 — реализовано |
| `GET /anime/{id}` | Anime | 3 — реализовано |
| `GET /search?q=…` | Page<Anime>; metadata-фильтры по capabilities | 4 — реализовано |
| `GET /home` | HomeResponse с нормализованными секциями | 5 — реализовано |
| `GET /releases/latest` | Page<Release> + scope | 5 — реализовано |
| `GET /anime/{id}/episodes` | Page<Episode>; season по возможностям источника | 6 — реализовано |
| `GET /schedule` | Датированные ScheduleEntry с Anime/ожидаемым Episode | Отдельный подэтап после исследования источника |
| `GET /player/{episode_id}` | PlayerInfo | 8 |

`HomeResponse`: `featured`, `continueWatching`, `latest`, `newReleases`, `ongoing`, `popular`,
`movies`, `donghua`, `recentlyUpdated`, `upcoming`. Все секции присутствуют;
неподдерживаемые секции пока пусты. `featured` и catalog-секции — списки Anime,
`latest` — список Release. `continueWatching` — список ContinueWatchingItem,
первоначально `[]`, поскольку персональная история локальная.
ContinueWatchingItem: Anime + Episode + nullable position/duration (мс).

### Главная и окно последних релизов

`GET /home` объединяет три публичные страницы AMD:

| Поле | Источник / смысл |
|---|---|
| `featured` | Карусель главной |
| `latest` | «Новые серии аниме» на главной |
| `newReleases` | «Новые аниме на сайте» — новые тайтлы |
| `ongoing` | Первая страница `/ongoingi/`, status=ONGOING |
| `popular` | Первые 20 позиций `/top-100-1.html`, порядок источника |
| `continueWatching` | `[]`, персональная история принадлежит Android |
| `movies`, `donghua`, `recentlyUpdated`, `upcoming` | Пока `[]` |

`GET /releases/latest?page=1&pageSize=20` отдаёт `{items, page, pageSize, hasNext,
total, scope}`. `scope="RECENT_WINDOW"` означает только видимое окно главной
(при исследовании 10 записей). Pagination применяется внутри этого окна;
`total` — размер окна, страница за концом — пустой список. Общие ограничения:
`page` ≥1, `pageSize` 1–50, по умолчанию 20.

Каждая запись содержит Anime и Episode. Episode ID:
`amd:<anime source ID>-episode-<номер>`; номер взят из строки релиза.
`season`, `playerId`, `releaseDate`, `releasedAt` остаются null, `available=false`
до подключения playback availability к catalog contract.
Наличие серии в ленте не гарантирует доступность плеера.
Надписи «Сегодня/Вчера» не преобразуются в UTC без подтверждённого часового пояса.
Совместимость episode identity со списком серий проверена на этапе 6.

### Список серий

`GET /anime/amd:1489/episodes?page=4&pageSize=50` возвращает
`{items, page, pageSize, hasNext, total}`. `page` ≥1, `pageSize` 1–50 (default 20).
Порядок — по возрастанию номера. Страница за концом возвращает `items=[]`,
`hasNext=false`, сохраняя `total`. Источник — ссылки публичной навигации карточки,
а не генерация диапазона из «вышло/запланировано N серий».

Episode DTO: `id`, `animeId`, `season`, `number`, `title`, `releaseDate`,
`thumbnail`, `available`, `playerId`. В AMD подтверждены ID, animeId и number;
остальные metadata-поля пока null, `available=false`. Этап 7 добавил отдельный
resolver, но catalog availability ещё не меняет и не делает player GET на каждую серию.
Это не утверждение, что все серии недоступны на самом AMD. В список входит
и следующая серия, если источник уже добавил её в навигацию с заглушкой.

ID `amd:<source ID>-episode-<номер>` общий с release feed, независим от slug,
порядка HTML, варианта плеера и URL видео. Повторы навигации PWA/web/player
объединяются только при совпадении наборов; конфликт, повтор внутри одного
набора или несовпадение href/data-vid/подписи → 502 PARSING_ERROR.

`season` — optional integer ≥0; AMD не сообщает сезон в этой навигации и
возвращает **422 UNSUPPORTED_OPERATION** для любого заданного season до сети.
Номер из названия или iframe не используется как номер сезона. Другой provider
может реализовать этот фильтр; service проверяет соответствие полученных серий.

Фильм и OVA представлены отдельными тайтлами с собственными числовыми сериями.
Дробные/именованные ключи эпизодов в исследованных страницах не встретились;
неподтверждённый формат вызывает ParsingError. Доменная модель допускает дроби
для будущих провайдеров. Пустой список AMD допустим только при явной категории
«Анонсы», отметке вышедших серий `-` и отсутствии навигации в блоке плеера.
Исчезновение блока/списка у обычного тайтла — ошибка, а не успешный пустой ответ.

Ошибки ID/namespace, upstream, redirect и размера HTML совпадают с details.
Неверные query-параметры → 422 VALIDATION_ERROR; отсутствие EPISODES capability
у провайдера → 422 UNSUPPORTED_OPERATION. Player URL в этом ответе отсутствует.

### Кэш

Успешные нормализованные данные кэшируются на один backend-процесс:
home 600 секунд, latest releases 180, episodes 180, details 10 800, search 60.
Ключ включает provider, операцию, все query/filter/page параметры и версию схемы.
Для episodes в ключ также входят animeId и season.
Ошибки не кэшируются; после истечения TTL запрос повторяется. Stale/partial ответы
пока не выдаются: повреждение обязательной секции возвращает ошибку всего `/home`.
`updatedAt` сохраняет время получения исходных данных, а не время cache hit.
Ключи home и release pages независимы: `home.latest` может обновляться реже.

При появлении partial/stale cache-ответов добавить явные метаданные состояния
секции и `fetchedAt`; отказ провайдера не выдавать за успешный пустой Home.
New Episodes и New Releases отображаются из определённых release/catalog данных,
а не из случайной сортировки по внутреннему `updatedAt`.

ScheduleEntry — предварительная модель. Часовой пояс источника, точность дат,
границы периода и поддерживаемые фильтры должны быть определены до реализации
`/schedule`. Уведомления не выводят «вышла серия» только из расписания.

## PlayerInfo

Минимальный согласованный пример:

```json
{
  "provider": "provider-key",
  "type": "WEB_EMBED",
  "embedUrl": "https://player.example/embed/public-episode",
  "qualityHint": null
}
```

Адрес выше иллюстративный, не проверенный AMD embed.

Discriminated union по `type`:

- `WEB_EMBED`: обязательный `embedUrl`, публичный embed или разрешённая player page.
- `NATIVE_STREAM`: обязательный `streamUrl`, только явно разрешённый прямой поток.
- `EXTERNAL`: обязательный `externalUrl`, проверенный адрес для внешнего обработчика.

В доменной модели этапа 1 неприменимые URL-поля запрещены, URL допускают только
HTTP(S). Финальная camelCase HTTP-схема плеера фиксируется на этапе 8.
`qualityHint` — подсказка источника, а не обещание выбора качества в чужом плеере.
Этап 7 добавил в WebEmbed domain модель `capabilities={progress, seek, fullscreen}`.
Все по умолчанию false: это включённые возможности Aurora, а не перечень
документированных возможностей vendor. RUTUBE документирует progress/seek через
postMessage, но безопасный Android adapter/device тест ещё не выполнен.
Android не предполагает доступ к cross-origin player events по умолчанию.

`AmdPlayerProvider` пока не подключён к default DI и маршрутам. Он получает
публичную карточку по numeric ID, опубликованную AMD episode page, проверяет
active episode и source iframe; выбирает RUTUBE → Kodik → VK → Aser только
для allowlisted HTTPS форматов. Заглушка/нет поддерживаемого iframe →
PlayerUnavailable, серия вне навигации → NotFound, некорректный episode ID →
VALIDATION_ERROR. `supports_embed` означает resolved source iframe, не playback.
Вендорские endpoints не запрашиваются resolver-ом, embed URL не кэшируется
общим catalog cache. Ни stream extraction, ни fallback на произвольную страницу нет.
Контракт `/player/{episode_id}` и camelCase DTO фиксируются на этапе 8.
Подробности: [PLAYER_DISCOVERY.md](PLAYER_DISCOVERY.md).

## Ошибки

Реализованный envelope:
`{"error":{"code":"NOT_FOUND","message":"Запрашиваемый ресурс не найден","requestId":"…"}}`.
UI локализует сообщение по стабильному `code`; внутренние tracebacks не возвращаются.
Текст внутренних исключений, неверный input и validation details в ответ не включаются.

| Ошибка | HTTP |
|---|---:|
| Validation / unsupported filter | 422 |
| NotFound | 404 |
| RateLimited | 429, `Retry-After` если известно |
| NetworkError / ParsingError источника | 502 |
| ProviderUnavailable / PlayerUnavailable | 503 |
| UnknownError | 500 |

Коды: `VALIDATION_ERROR`, `NOT_FOUND`, `RATE_LIMITED`, `NETWORK_ERROR`,
`PARSING_ERROR`, `PROVIDER_UNAVAILABLE`, `PLAYER_UNAVAILABLE`, `UNKNOWN_ERROR`.
Дополнительно: `UNSUPPORTED_OPERATION` → 422; framework 405 →
`METHOD_NOT_ALLOWED` с сохранением `Allow`; прочие HTTPException → `HTTP_ERROR`
с исходным HTTP status и общим сообщением. `RateLimited.retry_after` (секунды)
передаётся в `Retry-After`. Ошибка response validation — 500, не пользовательский 422.

На Android отсутствие сети до API отображается как локальный NetworkError,
а не как HTTP-ответ. Недоступность плеера не переводится в «серия просмотрена».
Негативные сценарии и стабильность поля `code` проверяются контрактными тестами.
