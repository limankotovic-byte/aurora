# Aurora — Liquid Glass design system

STAGE 0: спецификация для будущего `android/core/designsystem/`.
Основной источник — [ui_reference_liquid_glass.png](ui_reference_liquid_glass.png),
1672 × 941: Home, Browse, Details, нижняя панель компонентов и motion-концепты.

## Визуальная интерпретация

Главный акцент — иллюстрации и постеры на почти чёрном фоне. Стекло заметно
в навигации, CTA, поиске, chips и tabs; свечение сконцентрировано на активных
элементах. Синий и фиолетовый задают идентичность, magenta — редкий блик.
Фон hero плавно уходит в чёрный; подписи и управление остаются читаемыми.

Референс задаёт принципы, а не плотность и размеры для копирования: мелкий
текст увеличиваем, три колонки оставляем только при достаточной ширине.
Рамки телефонов, фон презентации и декоративная типографика названий аниме
не становятся UI-компонентами. Иллюстрации референса не служат готовыми ассетами.
Иконки cast/download на макете не добавляют такие функции в MVP.

## Токены: primitive → semantic → component

Все значения ниже — начальные проектные токены, не результат точного
пипеточного измерения. Финальная проверка — в Compose showcase на телефоне.

| Primitive | Значение | Semantic role |
|---|---|---|
| black / navy | `#03050C` / `#080D1B` | background / backdropEnd |
| navySurface / navyRaised | `#10172B` / `#18213B` | surface / surfaceElevated |
| white / silver / muted | `#F4F7FF` / `#B8C3DA` / `#93A3C1` | textPrimary / textSecondary / textMuted |
| blue / violet | `#3974FF` / `#865CFF` | accentPrimary / accentSecondary |
| magenta / ice | `#C267E8` / `#97B4FF` | reflection / focusRim |
| deepBlue / deepViolet | `#244ACA` / `#5B35BC` | actionGradientStart / actionGradientEnd |
| amber / rose | `#FFD16A` / `#FF819D` | rating / error |

Пример цепочки: `deepBlue → actionGradientStart → HeroButton.fillStart`.
Яркий голубой остаётся ободком/свечением, а под белым текстом CTA используется
более тёмный action-gradient. Цвета и размеры не задаются hex/dp прямо в features.
Расчёт STAGE 0: непрозрачные пары text/surface дают минимум 6,25:1;
текст CTA на концах градиента — 6,74:1 и 7,31:1. Это не заменяет измерение
контраста итогового стекла поверх artwork.

- `AnimeTheme`: Material 3 как основа semantics, типографики и поведения;
  собственные `AnimeColors`, `AnimeTypography`, `AnimeSpacing`, `AnimeShapes`,
  `AnimeElevation`, `AnimeGlass`, `AnimeMotion` через единый theme API.
- Шаг spacing: 4, 8, 12, 16, 20, 24, 32 dp; боковой отступ 20 dp,
  между секциями 24 dp, между карточками 12 dp.
- Shape: poster 12 dp, landscape/panel 20 dp, hero 24 dp, chips/nav — capsule.
- Typography: системный sans-serif с кириллицей; body 16/24 sp, secondary 14/20,
  label 12/16, section 20/26, hero 28/34. Размеры масштабируются системным font scale.
  Декоративный serif из названий на референсе не заменяет обычный UI-шрифт.
- Touch target ≥48 × 48 dp, в том числе у визуально маленьких chips и иконок.
  Высота строк растёт с font scale; у Details доступен полный заголовок.
- Постер 2:3, landscape ~16:9. `LazyVerticalGrid` адаптивный (обычно 2–3 колонки),
  ширина карточки ориентировочно от 104 dp, с проверкой длинных названий.

## GlassSurface

Центральная абстракция: `shape`, `opacity`, `borderStrength`, `blurMode`,
`blurRadius`, `activeGlow`, `elevation`, `content`.

Порядок слоёв: тёмная подложка → приглушённый фон → внутренний градиентный блик →
тонкий светлый rim → контент. Glow рисуется только для выбранного/нажатого
элемента. Текст и иконки не размываются.

| Режим | Реализация | Когда |
|---|---|---|
| Basic | Подложка ~0,82 opacity, статический блик, rim 1 dp / ~0,14 alpha; без live blur | Базовый режим, старые API, слабое устройство |
| Enhanced | Те же слои + размытие отдельного фонового слоя, пробный radius 12–20 dp | Только после замеров на API 31+ |
| High contrast | Подложка ≥0,96 opacity, усиленный focus, минимум бликов | Настройка доступности / сложное изображение |

`Modifier.blur` размывает содержимое своего слоя и на Android ниже API 31
не даёт нужного эффекта. Он не является универсальным backdrop-filter.
Поэтому blur на контейнере с текстом не используется как реализация стекла.
Для hero допустимо заранее размытое уменьшенное изображение. Настоящее семплирование
фона — отдельный прототип, не обязательное условие всего приложения.
Смена режима сохраняет геометрию и визуальную иерархию компонентов.

## Референс → Compose-компоненты

| Область изображения | Компонент | Принцип реализации |
|---|---|---|
| Hero Home | `HeroBanner`, `HeroButton`, `FavoriteButton` | Coil artwork + scrim, минимум метаданных, CTA и индикаторы |
| Continue Watching | `ContinueWatchingCard` / `AnimeLandscapeCard` | Заголовок, эпизод, достоверный прогресс; неизвестную позицию не рисовать |
| New Episodes / Browse grid | `AnimePosterCard`, `RatingBadge` | Постер главный; rating/episode badge, title/metadata ниже |
| Поиск и фильтры | `SearchBar`, `GlassTabBar`, `GenreChip`, `FilterChip` | Одна система active/focus; фильтры в bottom sheet |
| Floating bottom bar | `GlassNavigationBar`, `NavigationOrb` | Capsule с safe-area padding, четыре пункта и центральная сфера |
| Details | `DetailsHero`, `GlassTabBar`, `EpisodeCard` | Большой artwork → scrim; tabs Episodes/About/Related, выбор сезона |
| Нижняя панель UI details | `GlassChip`, `PlayerButton`, `SectionHeader` | Общие tokens, press 0,98, одинаковая оптика стекла |
| Состояния контента | `LoadingSkeleton`, `ErrorState`, `EmptyState` | Стабильные размеры, понятный retry, отсутствие ложных данных |

`AnimeCard` — общая основа вариантов, не отдельный стиль каждой feature.
Компонентам передаются отображаемые данные/callbacks; сетевых запросов внутри нет.
Состояния: default, pressed, selected, focused, disabled, loading/error по смыслу.
Выбор обозначается также подписью/semantics, а не только свечением.

Навигация: Home, Browse, Library, Settings; orb остаётся элементом идентичности.
Его действие (Search или Discover) выбирается после проверки IA на этапе 9,
финальная интеграция — этап 18. До выбора это не обещанная функция.
Long press может быть дополнительным действием, но не единственным способом
доступа к функции. Bottom bar учитывает gesture/IME insets и не перекрывает контент.

## Motion в `core/designsystem/motion/`

| Primitive | Поведение | Начальная длительность |
|---|---|---:|
| `LiquidWaveReveal` | Mask от точки нажатия, органическая кривая, сине-фиолетовый светлый край | 420 мс (диапазон 350–550) |
| `OrbCollapse` / `RippleCollapseTransition` | Лёгкое сжатие страницы → круг к точке возврата → затухающий ripple | 360 мс (300–450) |
| `SharedPosterTransition` | Стабильный anime ID, poster → Details header; заголовок отдельно | 400 мс |
| `GlassTabSelection` | Подложка перемещается под активный tab | 200 мс |
| Press / favorite / chip | Scale 0,98, короткий highlight, один glow pulse | 120–180 мс |
| Reduced motion | Простой fade, без волны/орба/parallax | 120 мс; 0 при отключённых системных анимациях |

`AnimeMotion` хранит tokens, `PageTransition` — согласованный coordinator,
`SharedElementMotion` — адаптер shared-element API. Центральная политика
`MotionPolicy` объединяет системные настройки и app reduced-motion setting.
Параметры масштаба и времени не разбросаны по features.

Первый прототип волны: анимируемая Path-маска и градиентный край. Настоящая
рефракция не требуется для принятия прототипа. Glow ограничен областью перехода;
нет бесконечной пульсации orb, шейдеров на каждом постере или постоянного parallax.

Один активный major transition. Повторный tap, отмена/back, поворот и восстановление
состояния не создают двойную навигацию. Точка возврата хранится в нормализованных
координатах; если исходная карточка исчезла, используется стабильный fallback.
При predictive back переход зависит от gesture progress и корректно откатывается,
а не проигрывается независимо после pop. Навигационный back stack — источник истины.

Shared-element Compose имеет ограничения с `AndroidView`/WebView: анимируется
оболочка или постер. Сам player не подвергается liquid-деформации. Если shared
poster нестабилен, временный fade/scale сохраняет пространственную связь.

## Проверка на этапах 10–11

- Showcase: все компоненты/состояния, светлые и тёмные artwork, длинные русские
  названия, 200% font scale, TalkBack/focus, Basic/Enhanced/High contrast.
- Контраст обычного текста ≥4,5:1, крупного текста/значимых иконок ≥3:1;
  измерять итоговую композицию поверх artwork, не только исходные hex.
- Motion Demo: wave/orb/shared poster, быстрые повторные taps, отмена/back,
  rotation, фон/возврат, системные анимации 0 и app reduced motion.
- Телефон: скролл poster grid и переключения при загрузке Coil. Цель — ровное
  ощущение 60 FPS; при 60 Гц кадр имеет бюджет ~16,7 мс. Сравнивать frame timings
  в profileable/release-like сборке, поскольку debug не даёт финальных выводов.
- Lazy-списки со стабильными ключами; ограничение decoded image size;
  animation state читается по возможности на draw/layer-фазе, не перестраивает grid.
- При jank сначала уменьшить blur area/radius/overdraw проблемного компонента,
  затем выбрать Basic для него. Результат и компромисс документировать.

Источники: [Compose blur](https://developer.android.com/develop/ui/compose/graphics/images/customize),
[shared elements](https://developer.android.com/develop/ui/compose/animation/shared-elements),
[navigation/back](https://developer.android.com/develop/ui/compose/animation/shared-elements/navigation).
