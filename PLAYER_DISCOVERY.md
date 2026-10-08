# Aurora — исследование плеера (STAGE 7)

Дата: 2026-10-08 UTC. Backend discovery завершён; реальное воспроизведение,
WebView, fullscreen и точный resume **не проверены на устройстве**.
`adb devices -l` вернул пустой список, Android-приложение ещё не создано.
Эмулятор не запускался. `/player/{episode_id}` — следующий этап 8.

## 1. Границы и результат

Реализован независимый `backend/app/providers/amd/player.py::AmdPlayerProvider`
по существующему `PlayerProvider`. Он возвращает исходный публичный iframe URL
как `WebEmbedPlayerInfo`, а не видеофайл или извлечённый поток.
Каталог не наследует плеер и не делает запрос для каждого Episode.
Автоматическое подключение к app factory и HTTP DTO/route отложены до этапа 8.

Не использовались авторизация, приватные AJAX/API, чужие ключи API,
расшифровка media URLs, подмена Referer/User-Agent, проксирование видео,
обход рекламы/CDN/региональных ограничений или extraction JavaScript плеера.
Обнаруженные iframe — техническое свидетельство публичного встраивания источником,
не аудит авторских прав всего каталога. Отказ или запрет vendor не обходить.

## 2. Как серия связана с плеером

1. Проверить `amd:<source ID>-episode-<положительный номер>`.
2. Открыть публичный `index.php?newsid=<id>` и same-origin redirect карточки.
3. Найти реальную ссылку серии в проверенной навигации `#elementb`.
   Slug берётся из HTML, а не генерируется из названия.
4. Открыть опубликованную AMD episode page. Redirect допускает смену slug,
   но не HTTPS origin, ID тайтла или номер эпизода.
5. Проверить активную серию `.sel-active` во всех копиях навигации.
6. Для Amedia сопоставить выбранный `data-vlnk` с `iframe.frame_video_mod.src`.
   Для Kodik проверить tab `data-has-ep`, все `iframe.amd-kodik-iframe.data-src`
   и query `episode`. Используется опубликованный URL без замены параметров.
7. Выбрать поддерживаемый embed: RUTUBE → Kodik → VK → Aser.

На типичное разрешение — три AMD GET (lookup → detail → episode page).
Каждая цепочка bounded: максимум три redirect и 2 MiB декодированного HTML.
Backend resolver **не запрашивает vendor/embed/media URL**: загрузка iframe
принадлежит будущему клиенту. Запросы плеера не входят в catalog cache.

## 3. Реальные наблюдения и fixtures

Шесть episode pages получены обычным GET без cookies авторизации, все HTTP 200.
URL/время/размер/source SHA-256/fixture SHA-256/результат:
`backend/tests/fixtures/amd_player_sources.json`.

| Серия | Исходная разметка | Resolver |
|---|---|---|
| `amd:1489-episode-2` | Amedia: публичный RUTUBE `/play/embed/<id>` | WEB_EMBED / RUTUBE |
| `amd:1489-episode-162` | Amedia: `/index.php?do=nz&id=1489` | PLAYER_UNAVAILABLE |
| `amd:5781-episode-1` | Amedia: Aser; Kodik tab=1, iframe season=2/episode=1 | WEB_EMBED / Kodik |
| `amd:5781-episode-2` | Заглушка Amedia; Kodik tab=0, пустой iframe | PLAYER_UNAVAILABLE |
| `amd:5796-episode-3` | Пустой Amedia data-vlnk; Kodik season=1/episode=3 | WEB_EMBED / Kodik |
| `amd:1925-episode-1` | Amedia: VK `video_ext.php`; Kodik tab=0 | WEB_EMBED / VK |

Вторая серия 5781 и серия 162 тайтла 1489 присутствуют в навигации, но не имеют
поддерживаемого публичного embed. Не следует путать существование Episode с
доступностью видео. Amedia tab=1 сам по себе также не доказывает доступность.
Kodik season здесь относится к vendor URL, не присваивается `Episode.season`.

Полный HTML и минимизированные fixtures дали одинаковые PlayerInfo/Unavailable
для всех шести страниц. Из fixtures исключены скрипты, реклама, комментарии,
авторизация и guest tokens; сохранены публичные iframe/навигация и их public IDs.
Хэш VK/путь Kodik оставлены как часть опубликованного embed, не добытый секрет.

## 4. Политика URL и ошибки

Разрешены только наблюдённые HTTPS host/path/query форматы, без credentials,
нестандартного порта, fragment, повторяющихся query keys и длины >2048:

| Host | Поддерживаемый формат |
|---|---|
| `rutube.ru` | `/play/embed/<32 hex>` без query |
| `kodikplayer.com` | `/serial/<id>/<32 hex>/720p`, ровно season/episode/only_translations/hide_selectors |
| `vk.com` | `/video_ext.php`, ровно oid/id/hash |
| `aser.pro` | `/vod/<id>` без query |

Protocol-relative Kodik URL нормализуется в HTTPS. Значения query сохраняются.
Иные домены/форматы требуют нового реального fixture и исследования; прямые
mp4/m3u8 не разрешены. Расширенные параметры RUTUBE из документации пока не
включены в resolver: нет подтверждённого source case.

- Некорректный episode ID → InvalidEpisodeId / VALIDATION_ERROR (422).
- Чужой namespace или отсутствующая серия → NotFound (404); URL не угадывается.
- Заглушка, пустой или неподдерживаемый embed → PlayerUnavailable (503).
- Конфликт копий, неверная активная серия, несогласованный iframe → ParsingError (502).
- Transport → NetworkError (502); 429 сохраняет Retry-After;
  403/5xx/неожиданный redirect → ProviderUnavailable (503).

`supports_embed` означает наличие поддерживаемого iframe, не успешное проигрывание.
`get_embed_url` возвращает None только для PlayerUnavailable, не скрывает другие ошибки.
Public URL не логируется resolver-ом. `quality_hint=null`: `/720p` не обещает качество.

## 5. HTTP-проверки vendor — отдельно от playback

Единичные обычные GET опубликованных embed без выполнения JS:

| Vendor | Результат | Что это подтверждает |
|---|---|---|
| RUTUBE | HTTP 200, HTML shell; X-Frame-Options/CSP не объявлены | Embed endpoint отвечает, но video start не проверен |
| Kodik | HTTP 200, player page с меню «Получить код» | Публичная player page; playback не проверен |
| Aser | HTTP 200, JS player; CSP `upgrade-insecure-requests` | Публичный endpoint, только статическая проверка |
| VK | ConnectError в окружении | Runtime доступность не подтверждена |

Отсутствие запретительных headers не гарантирует отсутствие browser/runtime,
cookie, DRM, географических или embedding-ограничений. HTTP 200 не является
доказательством воспроизведения. Resolver возвращает source VK embed, но не
обещает, что он заработает на устройстве. Необходимо различать discovery и runtime.

## 6. Progress, seek и fullscreen

[Официальная документация RUTUBE](https://rutube.ru/info/embed/) описывает:
- входящие `player:currentTime` (`data.time`, секунды), `player:durationChange`;
- `player:ready`, `player:changeState`, `player:playComplete`, `player:error`;
- исходящую команду `player:setCurrentTime` с `data.time` после готовности;
- fullscreen через allowFullScreen и событие `player:changeFullscreen`.

**Точный resume у RUTUBE документированно возможен**, но сообщения, seek и
поведение рекламы ещё не проверены в Aurora. Документация содержит примеры с
targetOrigin `*`; Aurora не должна повторять небезопасный wildcard-паттерн.
Потребуется собственная минимальная HTTPS-оболочка с iframe, проверкой
`event.origin == 'https://rutube.ru'` **и** `event.source == iframe.contentWindow`,
валидацией схемы/диапазонов/размера сообщений и ограниченным origin-bound каналом
к Android. Нет чтения чужого cross-origin DOM и произвольного evaluateJavascript.
Позиции источника преобразуются в ms для Room. Реклама не должна считаться
прогрессом эпизода; завершение проверяется по достоверному событию/длительности.

У Kodik/VK/Aser официальное событие progress/seek в этом исследовании не
подтверждено. Сторонние parsers и предполагаемые методы generic Playerjs не
используются как контракт. Для них fallback — последний открытый эпизод,
не обещание точного resume. Можно расширить только после отдельной проверки.

В `WebEmbedPlayerInfo.capabilities` добавлен `PlayerCapabilities`:
`progress=false`, `seek=false`, `fullscreen=false`. Это **включённые возможности
Aurora**, а не отрицание возможностей vendor. Все пока false: нет Android
адаптера/оболочки и device проверки. На этапах 15/16 флаги меняются только после
реальных тестов конкретной связки; backend discovery не завершает resume MVP.

## 7. Условия безопасной Android WebView-интеграции

Официальные Android рекомендации проверены через Context7, Android CLI docs и
[Native bridges](https://developer.android.com/privacy-and-security/risks/insecure-webview-native-bridges),
[Managing WebView](https://developer.android.com/develop/ui/views/layout/webapps/managing-webview).

- Только HTTPS, allowlist основных переходов/redirect; не открывать произвольные
  intent/file/content/data URLs, downloads/popups и новые окна внутри player WebView.
- Внешний переход — только после действия пользователя и проверки адреса.
- Не применять addJavascriptInterface к странице vendor: он доступен всем frames
  и не позволяет надёжно проверить вызывающий origin. Будущий канал progress
  доступен только собственной доверенной оболочке, с ограниченной схемой сообщений.
- JavaScript нужен самому player, но native privileges, file/content access,
  mixed content, автоматические permissions геолокации/камеры/микрофона не нужны.
- Safe Browsing остаётся включённым, SSL error → отказ, не proceed.
- Не подменять origin/Referer/cookies и не переносить AMD login в vendor.
  Third-party cookies не включать глобально; реальная необходимость пока не проверена.
- Воспроизведение по user gesture. Autoplay/DRM/popups не разблокировать ради обхода.
- Fullscreen через WebChromeClient/custom view, корректные back/rotation.
- При выходе/фоне остановить playback, удалить iframe, закрыть каналы, снять
  listeners и уничтожить WebView; onPause сам по себе не считать гарантией тишины.
- Renderer crash: удалить/уничтожить старый WebView, не переиспользовать его.
  Фиксировать версию WebView при device проверках.

**Безопасное открытие на Android не заявлено как доказанный результат.**
Нужны physical-device тесты: запуск, user gesture, cookies, fullscreen/back,
фон/выход без звука, ошибки vendor, region restrictions, seek/progress и рекламу.

## 8. Проверки и следующий этап

261 offline test, Ruff lint/format PASS, Pyright strict 0 errors/warnings.
Live provider smoke 2026-10-08 около 01:49 UTC повторил четыре embed результата и
две заглушки; refactored details/episodes прошли live regression. Эти проверки
не проигрывали видео. ADB — пусто, WebView playback verification BLOCKED.
Claude CLI review недоступно (`loggedIn=false`); тесты выполнены самостоятельно.

Этап 8: PlayerService, camelCase discriminated HTTP DTO, `/player/{episode_id}`,
независимые settings/DI player provider, API tests для unavailable и ошибок.
Episode availability в каталоге пока не меняется; массовых player-запросов нет.
