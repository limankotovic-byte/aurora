# Aurora

Модульный Android-клиент аниме с нативным интерфейсом Liquid Glass,
заменяемыми источниками каталога и отдельным слоем воспроизведения.

## Состояние

**STAGE 7 завершён: Player discovery.**
Работают `/home`, `/releases/latest`, `/anime/{id}`, `/anime/{id}/episodes` и `/search`.
Добавлен независимый resolver публичных embed; HTTP player route пока не подключён.
Всего **261 offline-тест**; mapping серий и заглушки проверены live.
Playback/resume в Android WebView не проверены: телефон не подключён.
Следующий этап — **STAGE 8: Player API**, по отдельному указанию.

## Запуск backend

```bash
cd backend
uv sync --locked
uv run --locked uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
```

Проверка: `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`.
Настройки и команды проверок: [backend/README.md](backend/README.md).
Результаты исследования AMD: [описание парсера](backend/app/providers/amd/README.md).

## Документация

- [Исходный бриф](PROJECT_AGENT_PROMPT-1.md) — требования и границы этапов.
- [Визуальный референс](ui_reference_liquid_glass.png) — основное направление дизайна.
- [Архитектура и карта модулей](ARCHITECTURE.md).
- [Дизайн-система и motion](DESIGN_SYSTEM.md).
- [API](API.md) — реализованная основа и предполагаемый контракт следующих этапов.
- [Исследование плеера](PLAYER_DISCOVERY.md) — embed mapping, capabilities и WebView ограничения.
- [План этапов](TODO.md).
- [Окружение и отчёт STAGE 0](ENVIRONMENT.md).

## Порядок разработки

Один этап — одна проверяемая задача: исследование → локальные изменения →
проверки → документация → отчёт → остановка. Целевая структура описана
в `ARCHITECTURE.md`; каталоги добавляются по мере реализации этапов.

Основная Android-проверка — на физическом телефоне через ADB.
На момент STAGE 0 подключённых устройств нет. Доступный SDK:
`/opt/android-sdk`; подробности и ограничения — в `ENVIRONMENT.md`.
