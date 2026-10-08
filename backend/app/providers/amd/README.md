# AMD providers — STAGE 7

`AmdProvider` использует общий `httpx.AsyncClient`; поддерживаемые операции
capabilities — ANIME, SEARCH, HOME, RELEASES и EPISODES.
Schedule явно возвращает UnsupportedOperation.

## Независимый PlayerProvider

`player.py::AmdPlayerProvider` реализует отдельный Protocol, не наследует catalog.
Публичная карточка разрешает episode ID в исходный episode href; отдельный GET
этой страницы нужен для корректной active series и Kodik lazy iframe.
`parse_player_page` сверяет copies, selected data-vlnk, Amedia iframe,
Kodik data-has-ep и query episode. Не переписывает vendor URL под другую серию.

Поддерживаются наблюдённые HTTPS форматы RUTUBE → Kodik → VK → Aser;
неподдерживаемые/небезопасные URLs и AMD nz placeholder не выдаются как embed.
Unknown episode → NotFound, пустой/unsupported embed → PlayerUnavailable,
конфликт активной серии/frames → ParsingError. Calls идут только к AMD;
vendor HTML отдельно изучался read-only, stream URLs не извлекаются.
Player URLs не входят в catalog cache; catalog availability остаётся conservative.

`WebEmbedPlayerInfo.capabilities` описывает включённые функции Aurora: пока все
false. RUTUBE публично документирует progress/duration/seek postMessage, но
Android adapter и physical verification отсутствуют. HTTP player route и default
DI — этап 8. Полный [отчёт discovery](../../../../PLAYER_DISCOVERY.md).

## Список серий

`pages.py::fetch_detail_html()` — общий для details, episodes и player fetch с проверкой
source ID/redirect origin, ограничением 2 MiB и типизированными HTTP ошибками.
`episodes.py::parse_episodes()` выполняется в worker thread и читает только
навигацию `article.pmovie .pmovie__player #elementb a.nav_video_links`.
`data-vid`, текст ссылки и `/episode/<номер>/seriya-onlayn.html` должны совпадать;
числовой ID тайтла и HTTPS origin проверяются. Допускается смена slug.

AMD дублирует `id=elementb` для PWA/web и вариантов плеера: нужны все контейнеры,
а не только первый. Наборы номеров должны совпадать; внутри одного контейнера
повторы запрещены. Результат сортируется численно и пагинируется после разбора.
В `identity.py` общий с release feed конструктор ID и формат номера.

Исследованные случаи:
- `1489`: 162 строки, включая следующую невышедшую; заявленный план 180 не используется.
- `5781`: второй сезон как самостоятельный тайтл, 2 строки и 4 копии навигации.
- `1925`: фильм, 1 строка и 4 копии.
- `5796`: OVA, 5 строк и 2 копии; пустой `data-vlnk` при наличии Kodik.
- `5790`: анонс, нет списков; категория `/anonsy/` и `.amd-vser > span` со знаком `-`.

Пустой ответ разрешён только в последнем подтверждённом сценарии. Исчезновение
списка без этих признаков, конфликт копий, неверные URL/номера → ParsingError.
Дробные/именованные номера не встречены: новые форматы требуют реального fixture.
Сезон из названия/iframe не выводится; любой заданный season → UnsupportedOperation
до сети. `available=false`, `playerId=null`: данные разных плееров и placeholder
не позволяют установить playback availability только по навигации. Этап 7
добавил отдельный resolver без массовых запросов при получении списка серий.
Публичные episode pages/iframe/video URLs для получения списка не запрашиваются.

Episodes кэшируются внешним wrapper 180s по provider/anime/page/pageSize/season.
Fixtures и provenance: `tests/fixtures/amd_episodes_*.html`, `amd_episode_sources.json`.
Полный HTML и минимизированные fixtures дали идентичные списки для всех пяти страниц.

## Главная и релизы

`home.py` использует три публичных HTML-документа:
- `/`: `#owl-carou` → featured; блок новых тайтлов → newReleases;
  `#amd-poslednie-serii` → latest.
- `/ongoingi/`: карточки первой страницы → ongoing, status=ONGOING.
- `/top-100-1.html`: первые 20 `a.linek` → popular в порядке источника.

Сначала выполняются три последовательных GET с общим клиентом, затем разбор
в worker thread. На ответ действует лимит 2 MiB; HTTP/transport/parser
ошибки сохраняют разные коды. Отсутствующая обязательная секция не превращается
в успешный пустой Home. Movies/donghua/upcoming/recentlyUpdated пока пусты.

Release feed использует только видимые записи главной. API помечает это
`scope=RECENT_WINDOW`; pagination применяется внутри окна. Относительные даты не
интерпретируются без source timezone. Episode ID включает source ID тайтла и
номер: `amd:5781-episode-1`. Совместимость со списком серий проверена в этапе 6;
player mapping исследован в этапе 7, но catalog availability/playerId не изменены;
season/releasedAt по-прежнему неизвестны.

Кэш расположен вне AMD: `CachedAnimeProvider` + `CacheService`. Домашние секции
кэшируются 600s, release pages/episodes 180s, details 10800s, search 60s. Ключи home/release
независимы: свежая лента может обновиться раньше `home.latest`.

## Поиск

`search.py`: POST обычной формы `/index.php?do=search` с `do=search`,
`subaction=search`, `story`, `from_page` (0 для первой, 2 для второй страницы).
Поля и механизм `formNavigation` подтверждены публичной формой и её JS;
autocomplete/private AJAX не используется. Публичный config задаёт длину 3–25.

Каждая страница содержит 10 карточек. Первый запрос получает total и проверяет
query echo; далее запрашиваются нужные страницы, до 7 HTTP-запросов на API-вызов
при pageSize≤50. Details для каждой карточки не запрашиваются. Кэш добавлен в этапе 5.
Изменение total/повторные IDs при объединении означает ParsingError.
Редиректы поиска не исполняются; HTML ограничен 2 MiB на ответ.

В форме отсутствуют genre/year/type/status/rating/voiceover/sort. `search_filters`
пуст; переданный фильтр явно отклоняется, а не игнорируется и не применяется
к неполной странице. Отдельный фильтр каталога на главной не является подтверждённым
combined search API. Его исследование потребуется для будущего расширения.

CSS и pattern счётчика — `selectors.py`; URL identity rules — `identity.py`.
HTML-fixtures и provenance: `tests/fixtures/amd_search*.html`,
`tests/fixtures/amd_search_sources.json`. Live проверки поиска — HTTP 200.

Идентичность: `amd:1489` ↔ source ID `1489`. Публичный lookup
`https://amd.online/index.php?newsid=1489` проверен: HTTP 301 на
`/1489-protivostojanie-svjatogo.html`. Таким образом смена slug не меняет ID.
Этот endpoint — публичная HTML-страница, не video/private API.

URL/ID-правила находятся в `identity.py`. Redirect разрешён только на HTTPS
amd.online с тем же числовым ID, максимум 3 перехода; ответ ограничен 2 MiB
декодированного HTML. Разбор выполняется в worker thread. HTTP ошибки и
ошибки parser различаются; автоматических повторов нет. Кэш управляется внешним wrapper.
`updated_at` — время нормализации в UTC. Live API smoke 2026-10-07: HTTP 200.

## Parser foundation (этап 2)

Чистый PoC разбора одной публичной карточки AMD. Точка входа:

```python
parse_anime_page(html: str | bytes, *, page_url: str) -> ParsedAnimeDetails
```

Функция принимает уже полученный HTML и конечный URL страницы для разрешения
относительных ссылок. Она возвращает только `title`, `poster_url`, `description`,
`genres`, `year`. `ParsedAnimeDetails` — частичный результат, не полный `Anime`:
ID/provider добавляет `provider.py`; DTO находится в `schemas/anime.py`.

## Проверенный источник

https://amd.online/1489-protivostojanie-svjatogo.html — «Противостояние святого».
2026-10-07 страница доступна через обычный HTTP GET, возвращает HTTP 200 и
серверный HTML с метаданными. Подробный provenance и способ минимизации:
[tests/fixtures/README.md](../../../tests/fixtures/README.md).

Проверка полной сохранённой страницы и минимизированной фикстуры дала одинаковые
пять полей: название, абсолютный poster URL, описание из двух абзацев (972 символа),
шесть жанров и 2023 год. Это проверка одной страницы, а не всего каталога AMD.

## Правила разбора

CSS selectors и source-specific URL patterns находятся в `selectors.py`.

| Поле | Наблюдаемая структура / обработка |
|---|---|
| Карточка | Ровно одна `.amd-card` внутри `article.pmovie` |
| title | `.amd-content .amd-title h1`; trim/collapse whitespace, обязательное поле |
| poster_url | `.amd-left .amd-poster > img`, атрибут `src`; HTTP(S), absolute/relative/protocol-relative |
| description | `.amd-content .amd-description`; обычный текст, `p` разделены двумя переводами строки |
| genres | Ссылки `.amd-tags` с путём `/anime/ghanr/` того же host; порядок/регистр сохранены, дубликаты case-insensitive |
| year | Ссылка `.amd-meta` с путём `/anime/god/YYYY/`, её текст должен совпадать с годом |

Перед постером находится вложенное изображение клана. Поэтому selector `> img`
существенен: выбор первого произвольного `img` даёт неверную картинку.
В `.amd-tags` есть «дунхуа», но это `/anime/podborka/`, а не жанр.
Год не извлекается из даты загрузки постера, описания, названия или сезонной подписи.

Отсутствующая/неоднозначная карточка и пустой/исчезнувший title → `ParsingError`.
Отсутствующие optional fields → `null`/`[]`. Невалидный poster URL → `null`;
разные валидные годы → `null`. URL с credentials и non-HTTP(S) схемами не принимаются.
Scripts/styles/templates/noscript исключены из текстовых полей. Парсер не делает
сетевых запросов, не загружает изображения и не исполняет содержимое страницы.

В этой версии подтверждён обычный `src`; другие lazy-loading схемы и альтернативные
шаблоны страницы потребуют реального fixture перед расширением selectors.
С этапа 3 HTTP status/timeout и `ParsingError` различаются в provider adapter.

## Проверки

Из каталога `backend/`:

```bash
uv run --locked pytest tests/providers/test_amd_parser.py
```

35 случаев: реальный fixture, UTF-8 bytes, missing/changed/ambiguous markup,
optional fields, nested clan avatar, relative/invalid poster URLs, genre isolation,
year mismatch/conflict, пробелы/HTML entities и исключение script/template content.
Они используют существующий запрет исходящих socket connections в `tests/conftest.py`.

Реализация: BeautifulSoup 4.15.0 / Soup Sieve 2.10, стандартный `html.parser`.
Документация проверена через Context7:
[Beautiful Soup — select/get_text/decompose](https://www.crummy.com/software/BeautifulSoup/bs4/doc/).
