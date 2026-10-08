# AMD fixtures

## Player fixtures (STAGE 7)

`amd_player_1489_2.html`, `amd_player_1489_162.html`, `amd_player_5781_1.html`,
`amd_player_5781_2.html`, `amd_player_5796_3.html`, `amd_player_1925_1.html` —
реальные публичные AMD episode pages HTTP 200, получены 2026-10-08 UTC.
URL/время/source bytes/SHA-256 source+fixture/expected result:
`amd_player_sources.json`. Наблюдения и границы: [PLAYER_DISCOVERY.md](../../../PLAYER_DISCOVERY.md).

Минимизация механическая: title/meta/released count, все исходные #elementb,
button[data-player] и Amedia/Kodik iframe; восстановлены scoped article/card/player
оболочки. В links сохранены class/href/data-vid/data-vlnk, включая public embed IDs.
Scripts, рекламные блоки, voiceover menus, auth/user/guest tokens не включены.
Public Kodik paths и VK hash сохранены как опубликованные URL-параметры, не секреты
авторизации. Тесты не загружают embed, scripts или media.

Полное равенство PlayerInfo/PlayerUnavailable при разборе исходного HTML и
fixtures подтверждено для всех шести страниц. Источники заглушек nz не являются
валидным видео. У OVA пустой data-vlnk и реальный Kodik lazy iframe позволяют
воспроизвести важный сценарий, который нельзя определить только из списка серий.
Playwright/WebView/video runtime этими fixtures не проверяются.

## Episodes fixtures (STAGE 6)

Обычным публичным GET `index.php?newsid=<id>` с redirect получены пять карточек
(HTTP 200, 2026-10-08 UTC). Lookup/final URL, время записи source body, размер,
SHA-256 source и fixture, число строк/копий — `amd_episode_sources.json`.

| Fixture | Случай | Строк | Копий навигации |
|---|---|---:|---:|
| `amd_episodes_1489.html` | Противостояние святого: длинный список и будущая серия | 162 | 2 |
| `amd_episodes_5781.html` | Магия вернувшегося должна быть особенной 2 | 2 | 4 |
| `amd_episodes_1925.html` | Противостояние святого: Битва пришествия богов — фильм | 1 | 4 |
| `amd_episodes_5796.html` | О моём перерождении в слизь OVA | 5 | 2 |
| `amd_episodes_5790.html` | Джанкет банк — явный анонс без серий | 0 | 0 |

Минимизация механическая: сохранены исходные `.amd-title`, `.amd-meta`,
`.amd-vser` и все `#elementb` из player block, включая дубли. В ссылках оставлены
class/href/data-vid и исходный текст. Оболочки article/amd-card/amd-content/player
восстановлены для scoped selectors. Остальная разметка, scripts, iframe, playback
атрибуты/URL, реклама, пользовательские данные и tokens исключены из fixture.

При получении **для всех пяти страниц проверено полное равенство Episode lists**
при разборе полного source HTML и fixture. Серию 162 не создаём из плана 180:
она явно присутствует в навигации. Пустой `data-vlnk` у OVA не доказывает отсутствие
другого плеера, поэтому playback availability остаётся задачей этапа 7.
Мутации для конфликтов/дробных/именованных ключей в тестах синтетические;
такие ключи не заявлены как подтверждённые варианты реального источника.

## Home fixtures (STAGE 5)

`amd_home.html` — карусель, лента серий и блок новых тайтлов;
`amd_ongoing.html` — карточки первой страницы онгоингов;
`amd_popular.html` — публичный «Топ 100».
URL, дата получения (2026-10-07 UTC), размер и SHA-256 полного исходника
сохранены в `amd_home_sources.json`.

Fixtures механически извлечены из сохранённых ответов HTTP 200: у главной
оставлены три соответствующих контейнера, у остальных страниц — `#dle-content`.
Scripts/styles удалены; HTML-оболочка/charset добавлены. В главной восстановлена
обёртка `data-home-block=new_anime` вокруг исходного content-контейнера.
Это минимизированные фрагменты; source SHA относится к исходному response body.

Полные исходники были исследовательскими файлами `/tmp/opencode/aurora-*-source.html`.
При завершении документации они уже отсутствовали: дополнительная сверка полного
HTML с home fixtures не выполнена. Offline-тесты используют сохранённые fixtures;
source hashes фиксируют происхождение, но не заменяют полный snapshot.

Наблюдаемые размеры: 14 featured, 12 новых тайтлов, 10 строк серий, 12 ongoing;
popular parser берёт первые 20 из исходного топа. Лента содержит относительные
временные подписи, но точный timestamp остаётся unknown. Номера серий берутся из
самих строк; даты, сезоны и URL плеера не выдумываются.

## Search fixtures (STAGE 4)

`amd_search.html` — запрос «Наруто», 1 результат;
`amd_search_many.html` — «мир», первая страница из 191 результата;
`amd_search_page2.html` — «мир», вторая страница;
`amd_search_empty.html` — «aurorazzznomatchxyz», явное отсутствие результатов.
Все получены публичным POST `/index.php?do=search` 2026-10-07.
SHA-256 полного response, размеры, query и page: `amd_search_sources.json`.

Фикстуры получены механическим извлечением `#dle-content` и, для пустой выдачи,
`.message-info` из исходного HTML. Сохранены форма/echo, счётчик, все карточки
и навигация. Scripts/styles удалены; оболочка документа добавлена. Cookies,
общая навигация, авторизация и guest tokens не включены. Это минимизированные
реальные фрагменты, а не полные byte-identical snapshots. Тесты меняют их в памяти.

## `amd_anime.html`

Минимизированный HTML-фрагмент **реальной публичной страницы**, а не пример,
составленный по догадкам о разметке.

- URL: https://amd.online/1489-protivostojanie-svjatogo.html
- Название: «Противостояние святого» / Xian Ni.
- Получено: **2026-10-07T16:13:33.773728+00:00**, обычный HTTP GET, HTTP 200.
- Исходный response body: 351 762 bytes.
- SHA-256 исходного body:
  `7ec00c621a15e7f2bb85dc89f0858f17a17ea324ed016b1178648cb3165dc2f6`.
- Этот hash относится к полному исходнику, **не** к минимизированной фикстуре.

Сохранены структура `article.pmovie → .amd-card`, poster/title/tags/meta/description,
оба абзаца описания и характерные соседние элементы: вложенная картинка клана,
название на другом языке, рейтинг, количество серий, сезон и ссылка на подборку.
Текст пяти извлекаемых полей, poster src и metadata href взяты из исходной страницы.

Минимизация: удалены scripts/styles, player-разметка, auth forms, гостевые tokens,
комментарии, пользовательские списки, рекламные блоки и остальная навигация.
Оболочка документа/отступы сокращены; оставлена одна ссылка жанра вне карточки.
Данные клана заменены нейтральными `/clans/fixture-clan` и `/uploads/clans/fixture.png`;
его вложенность перед настоящим постером сохранена для регрессионного теста.
Fixture не является точной побайтовой копией всей страницы.

Ожидаемые значения:

- `title`: `Противостояние святого`.
- `poster_url`: `https://amd.online/uploads/posts/2024-12/original.webp`.
- `description`: оба исходных абзаца, разделённые `\n\n`.
- `genres`: `экшен`, `приключения`, `фэнтези`, `исторический`, `китайское`, `3D`.
- `year`: `2023`.

«дунхуа» здесь — ссылка `/anime/podborka/`, а не `/anime/ghanr/`;
парсер не смешивает эти категории. Регистр названий жанров сохраняется.
Число `1489` наблюдается в URL и служебных data-id страницы, но устойчивый
контракт идентичности и сопоставление с `Anime` относятся к этапу 3.

Тесты читают этот файл локально; сетевые подключения блокируются общим conftest.
Варианты повреждённых/неполных полей строятся из этого fixture в памяти.
При обновлении страницы повторно проверить пять полей вручную, provenance,
selector assumptions и expected values, затем запустить provider tests и общие checks.
