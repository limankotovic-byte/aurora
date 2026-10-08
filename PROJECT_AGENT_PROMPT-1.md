# PROJECT AGENT BRIEF — Anime Streaming Android App

> **Reference image:** `ui_reference_liquid_glass.png`
>
> Treat this image as the primary visual reference for the application's design language.
> Do not copy it pixel-for-pixel. Recreate its visual principles consistently across the app.

---

# 0. Core working rule

You are acting as the lead software architect and implementation agent for a modular Android anime client.

**Do not build the whole project in one pass.**

The project must be developed in small, verifiable stages.

For every stage:

1. inspect the current state of the repository;
2. state the goal;
3. state which files/modules will be touched;
4. state which files/modules will NOT be touched;
5. implement only the current scope;
6. run relevant checks/tests;
7. fix current-stage issues;
8. update documentation;
9. report what changed;
10. stop before moving to the next stage unless explicitly instructed.

Prefer small local changes over broad rewrites.

---

# 1. Product vision

Build a modern Android anime application with:

- native Android UI;
- anime catalog;
- search;
- filters;
- ongoing titles;
- latest releases;
- new episode feed;
- anime details;
- episode selection;
- continue watching;
- favorites;
- watch history;
- notifications for new episodes;
- a replaceable external player layer;
- support for public/authorized embed playback.

Initial catalog source:

- AMD / amd.online public catalog data.

The application architecture must **not** depend permanently on AMD.

AMD is only one `AnimeProvider`.

Future providers may include:

- AniList;
- Jikan / MyAnimeList;
- Shikimori;
- other metadata/catalog providers;
- other authorized playback providers.

---

# 2. Important playback restrictions

Do not implement or assist with:

- DRM bypass;
- CDN protection bypass;
- token/signature forgery;
- extraction of protected m3u8/mpd streams;
- emulation of private video APIs;
- circumvention of playback restrictions.

Allowed playback methods:

- public embed;
- public player page;
- documented provider API;
- external playback intent;
- native stream only when the source explicitly exposes a permitted direct stream.

Default fallback:

`WEB_EMBED`

The video/player implementation must be isolated so it can be replaced later without changing the catalog, search, history, or UI architecture.

---

# 3. System architecture

High-level flow:

```text
Public catalog sources
        ↓
AnimeProvider implementations
        ↓
Normalization layer
        ↓
Backend API
        ↓
Android repository layer
        ↓
Use cases
        ↓
ViewModels
        ↓
Jetpack Compose UI
```

Playback flow:

```text
Episode
   ↓
PlayerRepository
   ↓
PlayerProvider
   ↓
WEB_EMBED / NATIVE_STREAM / EXTERNAL
```

---

# 4. Backend stack

Use:

- Python
- FastAPI
- Pydantic
- httpx
- BeautifulSoup / selectolax or equivalent
- SQLAlchemy or SQLModel
- SQLite for development
- PostgreSQL-ready architecture
- pytest
- structured logging

Suggested structure:

```text
backend/
  app/
    main.py

    api/
      routes/
        health.py
        home.py
        search.py
        anime.py
        releases.py
        schedule.py
        player.py

    core/
      config.py
      logging.py
      exceptions.py

    models/
      anime.py
      episode.py
      genre.py
      release.py
      player.py

    schemas/
      anime.py
      episode.py
      release.py
      player.py

    providers/
      base.py

      amd/
        provider.py
        parser.py
        selectors.py
        search.py
        details.py
        releases.py
        episodes.py
        schedule.py
        player.py

    services/
      catalog.py
      search.py
      releases.py
      player.py
      cache.py

    repositories/
      anime.py
      cache.py
      history.py

    db/
      database.py
      tables.py

    utils/
      http.py
      parsing.py
      normalization.py

  tests/
    fixtures/
    providers/
    services/
    api/

  README.md
  ARCHITECTURE.md
  API.md
  TODO.md
```

---

# 5. Provider abstraction

Create provider interfaces before implementing the full AMD parser.

Example:

```python
class AnimeProvider:
    async def get_home(...)
    async def search(...)
    async def get_anime(...)
    async def get_episodes(...)
    async def get_latest_releases(...)
    async def get_schedule(...)
```

Playback must be separate:

```python
class PlayerProvider:
    async def get_player(...)
    async def supports_embed(...)
    async def get_embed_url(...)
```

Do not place application business logic directly into AMD HTML parsing code.

AMD-specific selectors, assumptions, URL patterns and parsing behavior must live only inside:

```text
providers/amd/
```

---

# 6. Normalized data models

The Android app must never depend on AMD HTML structure.

Use normalized internal models.

## Anime

```text
id
provider
provider_id
title
original_title
alternative_titles
description
poster_url
backdrop_url
year
status
type
genres
rating
episode_count
current_episode
age_rating
voiceovers
updated_at
```

## Episode

```text
id
anime_id
season
number
title
release_date
thumbnail
available
player_id
```

## Release

```text
anime
episode
released_at
provider
```

## PlayerInfo

```text
provider
type
embed_url
quality_hint
```

Possible player types:

```text
WEB_EMBED
NATIVE_STREAM
EXTERNAL
```

---

# 7. Backend API

Minimum endpoints:

```text
GET /health
GET /home
GET /search?q=
GET /anime/{id}
GET /anime/{id}/episodes
GET /releases/latest
GET /schedule
GET /player/{episode_id}
```

`GET /home` should return normalized sections such as:

```text
featured
continue_watching
latest
ongoing
popular
movies
donghua
recently_updated
upcoming
```

Where some sections may initially be empty if not yet implemented.

---

# 8. Caching

Do not hit AMD every time the Android user scrolls.

Suggested TTL values:

```text
home: 5–15 minutes
latest releases: 2–5 minutes
anime details: 1–6 hours
genres/filter metadata: 24 hours
schedule: 15–60 minutes
```

Cache must be a separate service.

---

# 9. Parser resilience

All AMD CSS/XPath selectors must be centralized.

Recommended:

```text
providers/amd/selectors.py
```

Never scatter selectors through services or API routes.

Store representative HTML fixtures:

```text
tests/fixtures/
  amd_home.html
  amd_anime.html
  amd_search.html
  amd_releases.html
```

Tests should parse fixtures without network access.

If AMD changes markup, ideally only `providers/amd/` changes.

---

# 10. Android stack

Use:

- Kotlin
- Jetpack Compose
- Material 3
- Navigation Compose
- ViewModel
- Coroutines
- Flow
- Retrofit or Ktor
- Kotlin Serialization
- Coil
- Room
- DataStore
- Hilt or Koin
- Media3 only for permitted direct streams
- WebView for permitted embeds/public player pages

Recommended structure:

```text
android/
  app/

  core/
    model/
    network/
    database/
    designsystem/
    navigation/
    common/
    player/

  feature/
    home/
    browse/
    search/
    details/
    player/
    library/
    history/
    settings/
    schedule/
```

---

# 11. Android data flow

UI must not talk directly to Retrofit/Ktor.

Use:

```text
Compose UI
    ↓
ViewModel
    ↓
UseCase
    ↓
Repository
    ↓
API / Room / DataStore
```

Create:

- AnimeApi
- AnimeRepository
- PlayerRepository
- HistoryRepository
- FavoritesRepository
- SettingsRepository

---

# 12. Design direction

## Primary visual reference

Use:

`ui_reference_liquid_glass.png`

The app should have a premium **Liquid Glass / cinematic anime** identity.

This design system is a core product requirement, not decorative polish to be added at the end.

### Core visual language

Use:

- AMOLED black and near-black backgrounds;
- deep navy;
- electric blue;
- violet;
- restrained magenta highlights;
- translucent glass panels;
- soft blur;
- luminous glass rims;
- layered depth;
- restrained neon glow;
- glossy liquid reflections;
- rounded organic shapes;
- backdrop artwork fading into dark UI;
- clean modern typography;
- generous spacing;
- subtle parallax;
- soft animated gradients;
- smooth motion.

Avoid:

- generic Material-only appearance;
- flat gray cards everywhere;
- excessive neon;
- noisy cyberpunk styling;
- cheap glassmorphism;
- too many borders;
- overly saturated rainbow gradients.

The interface should feel elegant and cinematic rather than loud.

---

# 13. Design system

Create a reusable design system in:

```text
core/designsystem/
```

Suggested pieces:

```text
AnimeTheme
AnimeColors
AnimeTypography
AnimeSpacing
AnimeShapes
AnimeElevation
AnimeMotion
AnimeGlass
```

Reusable UI components:

```text
AnimeCard
AnimePosterCard
AnimeLandscapeCard
HeroBanner
GlassNavigationBar
GlassTabBar
GlassChip
GenreChip
FilterChip
SectionHeader
EpisodeCard
ContinueWatchingCard
RatingBadge
PlayerButton
FavoriteButton
SearchBar
LoadingSkeleton
ErrorState
EmptyState
```

Do not build unique one-off cards for every screen if the same component can be reused.

---

# 14. Liquid Glass implementation

Glass surfaces should be layered rather than merely transparent.

A typical glass surface may combine:

```text
dark translucent fill
+ subtle backdrop blur
+ soft internal highlight
+ low-opacity border
+ outer glow only when active
+ subtle gradient reflection
```

Provide a central abstraction such as:

```text
GlassSurface
```

with configurable:

```text
shape
blur
opacity
border strength
active glow
elevation
```

Do not duplicate glass styling manually across screens.

---

# 15. Motion design language

Motion is a core part of the product.

The app should feel fluid, not like screens instantly replacing each other.

Create a reusable motion system in:

```text
core/designsystem/motion/
```

Suggested abstraction:

```text
AnimeMotion
PageTransition
SharedElementMotion
RippleCollapseTransition
LiquidRevealTransition
```

Motion must be centralized and reusable.

---

# 16. Opening transition — Liquid Wave Reveal

When opening a major screen or tab:

the new screen should appear through a **fluid wave / liquid glass reveal**.

Concept:

1. user taps a card/tab;
2. a luminous glass wave begins near the interaction point;
3. the wave expands across the screen;
4. the next page becomes visible underneath/inside the moving wave;
5. glass distortion settles;
6. content finishes with subtle fade/scale/parallax.

Visual character:

```text
blue → violet glass wave
soft refraction
light edge
very short blur
organic curved mask
```

This must feel fast and premium.

Do not make transitions slow.

Target perceptual duration:

```text
~350–550 ms
```

Use reduced motion fallback when accessibility settings request it.

---

# 17. Closing transition — Orb / Circular Collapse

When closing a page or returning:

the screen should not simply slide away.

Use a **circular collapse / glowing ripple**.

Concept:

1. page subtly scales inward;
2. edges bend toward a focal point;
3. screen collapses into a glowing blue/violet circle;
4. circle contracts;
5. a small ripple dissipates;
6. previous screen is revealed.

Where possible, focal point should relate to:

- original card position;
- back button;
- selected tab;
- center orb in navigation.

Target duration:

```text
~300–450 ms
```

Do not use this animation for every tiny interaction.

Reserve it for:

- major screen close;
- details → home/browse;
- player exit where appropriate;
- modal/fullscreen dismiss.

---

# 18. Shared element motion

When opening anime details from a poster:

prefer shared-element behavior where technically feasible.

Example:

```text
poster thumbnail
→ enlarges
→ becomes part of hero backdrop/details header
```

The title/rating may fade/translate into place separately.

Avoid teleporting content between screens.

---

# 19. Micro-interactions

Use subtle motion for:

- tab selection;
- chips;
- favorites;
- watch button;
- continue watching progress;
- nav bar selection;
- search focus;
- filter sheet opening;
- episode selection.

Examples:

Favorite:

```text
heart compresses
→ liquid highlight fills it
→ tiny glow pulse
```

Tab:

```text
active glass highlight flows underneath label
```

Poster press:

```text
0.98 scale
+ tiny depth change
+ highlight shift
```

Keep micro-interactions short.

---

# 20. Bottom navigation concept

Use a floating liquid-glass bottom navigation bar inspired by the reference image.

Suggested tabs:

```text
Home
Browse
[central orb / action]
Library
Profile / Settings
```

The central orb is a visual identity element.

Possible behavior:

- tap opens Search;
- long press opens quick actions;
- or use it as Discover.

Do not assign final behavior until the navigation IA is validated.

The orb should:

- glow subtly;
- react to touch;
- show liquid movement;
- not constantly pulse aggressively.

---

# 21. Home screen concept

Home is the visual centerpiece.

Recommended structure:

```text
Top bar
Hero banner
Continue Watching
New Episodes
Ongoing
Popular
New Releases
Movies
Donghua
Upcoming
```

## Hero

Large cinematic banner.

Contains:

- backdrop;
- gradient fade;
- title;
- compact genres;
- primary Watch/Continue button;
- add to library;
- optional rating;
- carousel indicators.

Do not overload hero with metadata.

## Continue Watching

Landscape cards.

Display:

```text
thumbnail
anime title
episode
remaining/progress
progress bar
```

## New Episodes

Compact poster or landscape cards.

Emphasize:

- episode number;
- very recent release;
- freshness indicator.

---

# 22. Browse screen

Use:

- glass search field;
- category tabs;
- genre chips;
- filtering;
- poster grid.

Suggested top categories:

```text
Anime
Movies
Ongoing
Genres
Donghua
```

Filtering may include:

```text
genre
year
type
status
rating
voiceover
sort order
```

Filters should open in a polished glass bottom sheet, not a cluttered permanent sidebar.

---

# 23. Anime details screen

The details page should feel cinematic.

Structure:

```text
full-width backdrop
dark gradient fade
title
metadata
genre chips
Watch / Continue
Add to Library

tabs:
Episodes
About
Related
```

Episodes should be displayed as clean rows/cards.

For long shows, provide:

- season selector;
- episode search/jump;
- lazy loading if necessary.

---

# 24. Player screen

Player feature remains isolated.

Suggested package:

```text
feature/player/
```

Components:

```text
PlayerScreen
PlayerViewModel
PlayerRepository
PlayerProvider
WebEmbedPlayer
NativeMediaPlayer
ExternalPlayer
```

If:

```text
PlayerInfo.type == WEB_EMBED
```

use the approved WebView/embed implementation.

Handle:

- fullscreen;
- orientation;
- back navigation;
- lifecycle;
- standard cookies/session when necessary;
- loading;
- player unavailable state.

Do not bypass provider restrictions.

---

# 25. Search behavior

Search should feel immediate.

Use:

- debounce;
- recent searches;
- suggestions if backend supports them;
- clear button;
- loading skeleton;
- empty state;
- error state.

Do not trigger network requests on every keystroke without debounce.

---

# 26. Local persistence

## History

Room fields:

```text
animeId
episodeId
position
duration
updatedAt
completed
```

Consider watched when approximately:

```text
90–95%
```

## Favorites

```text
animeId
addedAt
```

## Settings

Use DataStore.

Possible settings:

- theme;
- preferred quality;
- autoplay;
- auto-next;
- preferred voiceover;
- notifications;
- language;
- reduced motion;
- clear cache;
- clear history.

---

# 27. Error model

Use a centralized error model.

Example:

```text
NetworkError
ProviderUnavailable
ParsingError
NotFound
PlayerUnavailable
RateLimited
UnknownError
```

UI must display understandable messages.

Never expose raw stack traces to the user.

---

# 28. Performance requirements

Be careful with:

- heavy blur;
- large backdrop images;
- excessive recomposition;
- multiple simultaneous animations;
- WebView lifecycle;
- poster grids;
- image cache.

Liquid glass must remain smooth on mid-range Android devices.

If real-time blur is too expensive:

prefer visually similar precomposed/translucent surfaces rather than sacrificing performance.

Create performance fallbacks.

---

# 29. Accessibility

Support:

- reduced motion;
- readable contrast;
- scalable text where practical;
- content descriptions;
- focus behavior;
- large touch targets.

When reduced motion is enabled:

replace large liquid-wave/orb transitions with simple fade/scale transitions.

---


# 29A. Physical Android device is the primary test target

**Do not use an Android emulator as the default test environment.**

The development laptop may have limited resources, so Android testing must primarily use a **real Android phone connected through ADB**.

When Android development begins, use the connected physical device for:

- installing debug APKs;
- launching the app;
- checking navigation;
- testing Compose UI;
- testing animations;
- testing Liquid Glass performance;
- testing scrolling;
- testing WebView/embed playback;
- checking orientation changes;
- checking fullscreen player behavior;
- checking back navigation;
- checking lifecycle behavior;
- checking real-device memory/performance;
- collecting runtime logs and crashes.

Preferred workflow:

```text
./gradlew assembleDebug
        ↓
adb devices
        ↓
adb install -r <debug-apk>
        ↓
launch app on connected phone
        ↓
adb logcat / filtered application logs
        ↓
fix issue
        ↓
rebuild and reinstall
```

When useful, the agent may also use:

```text
adb shell am start ...
adb shell am force-stop ...
adb shell pm clear ...
adb shell dumpsys ...
adb logcat ...
```

Use these only for normal development/testing of this application.

## Device detection rule

Before the first Android-device test:

1. run `adb devices`;
2. verify that exactly the intended physical Android device is available and authorized;
3. record basic non-sensitive device information useful for compatibility testing, such as:
   - Android API level;
   - screen resolution;
   - ABI;
   - device model if exposed normally by ADB;
4. do not treat an emulator as a substitute for the physical device unless explicitly instructed.

If no authorized physical device is connected:

- do not automatically start or create an emulator;
- continue only with build/unit/static checks that do not require a device;
- mark physical-device verification as `BLOCKED: no authorized ADB device`;
- resume real-device tests when the phone becomes available.

## Emulator policy

Do **not**:

- automatically download emulator system images;
- create an AVD;
- boot an Android emulator;
- spend laptop resources on emulator testing;

unless explicitly asked to do so.

A physical phone connected by USB or wireless ADB is the preferred and primary target.

## Mandatory real-device checkpoints

From `STAGE 9 — Android skeleton` onward, every stage that changes runnable Android behavior must include real-device verification when a device is connected.

Examples:

### STAGE 9
Verify:

- app installs;
- app launches;
- navigation shell works;
- no startup crash.

### STAGE 10
Verify on phone:

- Liquid Glass surfaces render correctly;
- text remains readable;
- blur/glow does not cause obvious jank;
- scrolling remains smooth.

### STAGE 11
Verify on phone:

- Liquid Wave Reveal;
- Orb Collapse;
- tab animations;
- cancellation/back behavior;
- reduced-motion fallback;
- frame pacing.

### STAGE 12–14
Verify on phone:

- home;
- browse/search;
- details;
- poster grids;
- real scrolling performance;
- image loading.

### STAGE 15
Verify on phone:

- WebView/embed;
- fullscreen;
- orientation;
- back navigation;
- lifecycle;
- returning from player.

### STAGE 16+
Verify affected features on the real phone after each relevant change.

## Performance-first rule

The reference design uses blur, glow, translucency and motion, but visual fidelity must not destroy performance on the real device.

If an effect causes noticeable jank:

1. profile/inspect the bottleneck;
2. reduce the cost locally;
3. preserve the visual intention with a cheaper approximation when possible;
4. document the compromise.

Prefer a smooth 60 FPS-feeling interface over a more expensive visual effect that stutters.

Do not simplify the entire design system because one component is slow. Optimize that component first.

## Test report format for Android stages

After any Android stage, include:

```text
Physical device:
ADB status:
Android/API:
Build result:
Install result:
Launch result:
Features manually verified:
Runtime errors/logcat findings:
Performance observations:
Known device-specific issues:
```

If the phone is not connected, explicitly say:

```text
Physical device verification: BLOCKED — no authorized ADB device connected.
```

# 30. Testing

Backend:

- parser tests;
- normalization tests;
- provider tests;
- cache tests;
- API tests.

Android:

- repository tests;
- use case tests;
- ViewModel tests;
- critical Compose UI tests.

Motion/design components should also have preview/demo screens during development.

---

# 31. Development stages

## STAGE 0 — Repository and environment analysis

Before coding:

- inspect repository;
- inspect available tools;
- inspect Android SDK;
- inspect ADB availability;
- if a physical Android phone is already connected, verify it with `adb devices`;
- do not start an emulator if no phone is connected;
- inspect Java/Kotlin/Gradle;
- inspect Python;
- inspect existing configuration;
- inspect the reference image;
- create/update `ARCHITECTURE.md`;
- create/update `TODO.md`;
- create initial module map;
- write a short `DESIGN_SYSTEM.md` describing how the reference image will be translated into code.

Do not build the application yet.

Stop after Stage 0.

---

## STAGE 1 — Backend skeleton

Implement:

- FastAPI app;
- config;
- logging;
- errors;
- health endpoint;
- provider interfaces;
- normalized models;
- tests.

No full AMD parser yet.

---

## STAGE 2 — AMD parser proof of concept

Parse one representative anime page.

Extract only:

```text
title
poster
description
genres
year
```

Create fixture.

Create tests.

Do not implement the entire site.

---

## STAGE 3 — Anime details backend

Implement:

```text
AnimeProvider.get_anime()
GET /anime/{id}
```

Add normalization and tests.

---

## STAGE 4 — Search backend

Implement:

```text
search provider
GET /search
filters
```

Tests required.

---

## STAGE 5 — Home backend

Implement:

```text
latest
ongoing
popular
new releases
```

Add:

```text
GET /home
```

Add caching.

---

## STAGE 6 — Episodes backend

Implement:

```text
get_episodes()
GET /anime/{id}/episodes
```

Tests required.

---

## STAGE 7 — Player discovery

Investigate only public/authorized player embedding.

Determine:

- how episode maps to player;
- whether a public iframe/embed exists;
- whether it can be opened safely in Android WebView.

Do not bypass CDN protection.

Create `PlayerProvider`.

Document findings.

---

## STAGE 8 — Player API

Implement:

```text
GET /player/{episode_id}
```

Return normalized `PlayerInfo`.

Example:

```json
{
  "type": "WEB_EMBED",
  "embedUrl": "...",
  "provider": "..."
}
```

---

## STAGE 9 — Android skeleton

Create:

- Compose app;
- Navigation;
- DI;
- Network;
- Room;
- DataStore;
- DesignSystem;
- base motion framework.

No full catalog UI yet.

Before considering this stage complete, when the physical phone is connected:

- verify it with `adb devices`;
- build the debug APK;
- install/reinstall it through ADB;
- launch it on the phone;
- verify startup and base navigation;
- inspect application logs for crashes/errors.

Do not use an emulator as the default fallback.

---

## STAGE 10 — Design system foundation

Before building major screens:

implement reusable visual primitives from `ui_reference_liquid_glass.png`.

Create:

```text
GlassSurface
GlassNavigationBar
GlassTabBar
GlassChip
HeroButton
AnimeCard
PosterCard
LandscapeCard
LoadingSkeleton
```

Create Compose previews.

Create a temporary design showcase screen.

Verify performance.

---

## STAGE 11 — Motion foundation

Implement reusable prototypes for:

```text
LiquidWaveReveal
OrbCollapse
SharedPosterTransition
GlassTabSelection
```

Create a dedicated Motion Demo screen.

Do not yet attach every animation to the entire app.

Test:

- visual quality;
- cancellation;
- back gesture behavior;
- orientation;
- reduced motion;
- performance.

---

## STAGE 12 — Home UI

Connect `/home`.

Implement:

- hero;
- Continue Watching;
- New Episodes;
- Ongoing;
- Popular;
- reusable sections;
- loading;
- errors.

Use the liquid glass visual language.

---

## STAGE 13 — Browse/Search UI

Implement:

- search;
- debounce;
- filter chips;
- filter bottom sheet;
- poster grid;
- empty/error/loading states.

---

## STAGE 14 — Details UI

Implement:

- backdrop;
- poster;
- metadata;
- genres;
- watch button;
- library button;
- episodes;
- tabs.

Add poster → details shared element transition if stable.

---

## STAGE 15 — Player UI

Consume `PlayerInfo`.

Implement:

- Web embed;
- fullscreen;
- orientation;
- loading;
- error state;
- back handling.

Integrate transition conservatively.

---

## STAGE 16 — History

Implement Room history.

Add:

```text
Continue Watching
progress
completed
```

---

## STAGE 17 — Favorites / Library

Implement:

- favorites;
- library screen;
- remove/add actions.

---

## STAGE 18 — Navigation polish

Integrate final:

- floating glass bottom bar;
- central orb;
- page transitions;
- liquid wave reveal;
- circular collapse;
- tab animations.

Do not sacrifice navigation reliability for animation.

---

## STAGE 19 — Notifications

Implement release tracking and notification strategy.

Choose backend/push approach separately.

Do not begin before MVP is stable.

---

## STAGE 20 — Performance and polish

Review:

- animation smoothness;
- memory;
- image loading;
- blur cost;
- Compose recomposition;
- startup time;
- WebView cleanup;
- API caching;
- scrolling.

Add lower-cost visual fallbacks if needed.

---

## STAGE 21 — Android TV

Do not begin until mobile version is stable.

---

# 32. Agent workflow format

Before every stage, output:

```text
STAGE:
Goal:
Files/modules to change:
Files/modules NOT to change:
Risks:
How the result will be verified:
```

After every stage, output:

```text
DONE

Implemented:
Files changed:
Tests/checks:
Problems discovered:
Remaining:
Next recommended stage:
```

Stop after the assigned stage unless explicitly told to continue.

---

# 33. Modular change policy

If instructed:

> improve search

Do not modify player/history/favorites/design system unless truly necessary.

If instructed:

> redo player

Do not rewrite catalog/search/home.

If instructed:

> improve liquid wave animation

Do not rewrite navigation architecture unless the current architecture fundamentally blocks the animation.

Keep features isolated.

---

# 34. Refactoring policy

Before any broad refactor explain:

- why it is necessary;
- what modules it touches;
- expected benefit;
- risks;
- whether a smaller local fix is possible.

Prefer local fixes.

Do not refactor merely because another style seems cleaner.

---

# 35. Existing working code policy

Do not delete working:

- code;
- configs;
- tests;
- providers;
- UI components;

without a concrete reason.

When replacing implementation:

1. build replacement;
2. verify replacement;
3. run tests;
4. only then remove obsolete implementation.

---

# 36. Git discipline

Prefer:

```text
one logical stage = one logical commit
```

Examples:

```text
feat(backend): add provider abstraction
feat(amd): add anime details parser
feat(design): add liquid glass primitives
feat(motion): add liquid wave transition
feat(android): add home screen
fix(player): handle fullscreen webview
refactor(search): isolate filter mapper
```

Do not create giant mixed commits.

---

# 37. Documentation

Maintain:

```text
README.md
ARCHITECTURE.md
DESIGN_SYSTEM.md
API.md
TODO.md
```

Update architecture documentation when architecture changes.

Update design documentation when motion/design rules change.

---

# 38. TODO structure

Maintain:

```text
DONE
IN PROGRESS
NEXT
LATER
BLOCKED
```

Never lose the development roadmap.

---

# 39. MVP definition

MVP is complete when the user can:

1. launch the app;
2. see a polished home screen;
3. browse anime;
4. see latest releases;
5. search;
6. filter;
7. open anime details;
8. choose an episode;
9. open an authorized/public player;
10. return safely;
11. continue watching later;
12. add/remove favorites;
13. use the app without crashes during normal navigation.

The final MVP should already use the intended visual identity rather than a temporary generic Material UI.

---

# 40. Visual acceptance criteria

Before considering the UI polished, verify:

- dark cinematic look;
- glass layers visible but not noisy;
- violet/blue identity consistent;
- poster art remains the visual focus;
- text remains readable;
- bottom navigation feels custom;
- hero section feels premium;
- tabs/chips share one design language;
- animations feel fluid;
- opening wave is noticeable but fast;
- closing orb/ripple does not feel gimmicky;
- reduced-motion fallback works;
- no major jank during scroll or transition.

---

# 41. First instruction to execute

After receiving this brief:

**Do not start building the whole application.**

Execute **STAGE 0 only**.

Specifically:

1. inspect the repository and environment;
2. inspect `ui_reference_liquid_glass.png`;
3. create/update `ARCHITECTURE.md`;
4. create/update `TODO.md`;
5. create `DESIGN_SYSTEM.md`;
6. propose the project/module structure;
7. document how the visual reference maps to Compose components and motion primitives;
8. identify technical risks, especially blur/WebView/motion performance;
9. provide the Stage 0 report;
10. stop.

Do not proceed to Stage 1 until explicitly instructed.
