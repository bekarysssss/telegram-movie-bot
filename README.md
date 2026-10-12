# 🎬 Movie Finder — Telegram-бот: каталог и подбор фильмов

Telegram-бот с собственной базой фильмов (PostgreSQL): поиск по русскому/английскому названию, жанры, годы,
рейтинги, случайный фильм с фильтрами, избранное, просмотренные с личными оценками, подбор по настроению,
похожие фильмы, статистика, веб-админка и импорт данных из TMDB / IMDb.

## Источники данных

| Источник | Что берём | Условия |
|---|---|---|
| **TMDB API** | названия (ru/en), описания, постеры, трейлеры, состав, жанры, страны, рейтинг TMDB, keywords | бесплатно для некоммерческого использования, **обязательна атрибуция** (есть в `/about` и ниже) |
| **IMDb datasets** | рейтинг и число голосов IMDb (`title.ratings.tsv.gz`) | только личное/некоммерческое использование |
| `data/seed_movies.json` | стартовые 79 фильмов, чтобы бот работал сразу без ключей | рейтинги в seed приблизительные — обновите командой `imdb-ratings` |

> **Letterboxd** не используется: API выдаётся только по заявке и сейчас не выдаётся для личных проектов
> и проектов с рекомендациями, а парсинг сайта нарушает условия. Поле `letterboxd_rating` в схеме оставлено
> под будущее. Идея на будущее — импорт личного экспорта Letterboxd (CSV) самим пользователем.

*This product uses the TMDB API but is not endorsed or certified by TMDB.*

## Быстрый старт (Docker)

```bash
cp .env.example .env          # заполните BOT_TOKEN, ADMIN_IDS, TMDB_API_KEY, пароли
docker compose up -d --build  # postgres + redis + миграции + бот + админка

docker compose run --rm bot python -m app.cli seed             # 79 фильмов, без ключей
docker compose run --rm bot python -m app.cli tmdb --pages 25  # +500 самых оценённых (нужен TMDB_API_KEY)
docker compose run --rm bot python -m app.cli imdb-ratings     # актуальные рейтинги IMDb
```

Откройте бота в Telegram и нажмите `/start`.

### Где взять ключи
1. **BOT_TOKEN** — напишите [@BotFather](https://t.me/BotFather): `/newbot` → скопируйте токен.
2. **ADMIN_IDS** — ваш Telegram ID (узнать у [@userinfobot](https://t.me/userinfobot)), несколько — через запятую.
3. **TMDB_API_KEY** — зарегистрируйтесь на themoviedb.org → Settings → API. Подходит и «API Key (v3)», и «API Read Access Token (v4)».

## Импорт и обновление базы

Импорт — это **upsert**: фильм ищется по `tmdb_id`/`imdb_id`, новые добавляются, существующие обновляются
(пустые поля источника данные не затирают). Поэтому seed-фильмы автоматически «обогатятся» постерами и описаниями,
когда TMDB отдаст тот же `imdb_id`.

```bash
python -m app.cli tmdb --pages 25                              # топ по голосам: 25 стр × 20 = 500 фильмов
python -m app.cli tmdb --year-from 1950 --year-to 2025 --pages 3   # срез по годам → масштабирование за 10 000
python -m app.cli tmdb --pages 25 --refresh                    # обновить и уже имеющиеся
python -m app.cli tmdb-id 238 278 424                          # конкретные фильмы по TMDB id
python -m app.cli imdb-ratings [--file title.ratings.tsv.gz]   # рейтинги IMDb (по cron — раз в неделю)
```

TMDB отдаёт максимум 500 страниц на запрос — для базы 100 000+ используйте срезы по годам/жанрам.
Пример cron на VPS: `0 4 * * 1 cd /opt/movie-bot && docker compose run --rm bot python -m app.cli imdb-ratings`.

## Что умеет бот

`🎲 Случайный фильм` (с фильтрами: жанр, десятилетие, рейтинг, длительность, страна — можно комбинировать) ·
`🔎 Найти фильм` (подстрока + триграммы, опечатки прощаются; любой текст вне меню — тоже поиск) ·
`🎭 По жанру` · `📅 По году` (десятилетия или конкретный год) · `⭐ По рейтингу` (+ сортировка рейтинг/популярность/новизна) ·
`🔥 Популярное` (сейчас популярно, лучшие, классика, мировое кино) · `❤️ Избранное` · `✅ Мои просмотренные` (оценка 1–10) ·
`🎯 Подобрать фильм` (настроение → период → длительность, уже просмотренное исключается) · `📊 Моя статистика` ·
карточка фильма с постером, трейлером и «🎲 Похожие фильмы» · везде «🔙 Назад» и пагинация.

Админ-команды в боте (только `ADMIN_IDS`): `/admin_stats`, `/broadcast <текст>`.

## Веб-админка

`http://localhost:8000/admin` (логин/пароль из `.env`): создание, редактирование, удаление фильмов, жанры, пользователи.
JSON-статистика: `GET /api/stats` (HTTP Basic). **Смените пароли в `.env`!** Порт проброшен только на `127.0.0.1`.

## Архитектура

```
app/
├── bot/                 # aiogram 3: handlers/ (по разделам), keyboards, callbacks, formatters, middlewares
│   └── handlers/        # start, browse, search, card, library, randomizer, recommend, stats, nav, admin
├── api/main.py          # FastAPI + SQLAdmin (веб-админка, /api/stats, /health)
├── db/                  # models, repo_movies / repo_users / repo_stats, filters (единый MovieFilter)
├── services/            # importer (upsert), seed, types (MovieData)
├── integrations/        # tmdb.py (клиент + парсер), imdb_datasets.py
├── core/                # config (pydantic-settings), constants, text (нормализация)
└── cli.py               # команды импорта
migrations/              # Alembic (async)
tests/                   # pytest
```

Принципы: handlers не знают про SQL, SQL живёт в `repo_*`; все выборки (списки, рандом, подбор) строятся из одного
`MovieFilter`; импорт приводит любой источник к `MovieData` — новый источник = один новый модуль в `integrations/`.

### Схема БД
`users`, `movies`, `genres`, `movie_genres`, `countries`, `movie_countries`, `people`, `movie_people` (роль: director/writer/actor),
`keywords`, `movie_keywords`, `user_favorites`, `user_watched`.

Отличия от исходного ТЗ (сознательные упрощения):
* режиссёры/актёры/сценаристы — одна таблица `people` + `movie_people(role)` вместо четырёх таблиц;
* личные оценки лежат в `user_watched.rating`, отдельной `user_ratings` нет (оценка возможна только у просмотренного);
* `awards`/`collections` не добавлены — под Oscar/фестивали и подборки (см. «Дальше»).

### Производительность
* поиск: колонка `search_text` (нормализованные ru + оригинальное название, ё→е) + GIN-индекс `pg_trgm`;
* индексы: `year`, `(rating, votes)`, `popularity`, `(genre_id, movie_id)`, `(country_code, movie_id)` и др.;
* пагинация через `LIMIT/OFFSET` с `COUNT` по индексируемым условиям; случайный фильм — без `ORDER BY random()`;
* в списках «по рейтингу» действует порог `MIN_VOTES`, чтобы фильм с 10.0 и тремя голосами не лидировал.

## Деплой на VPS
1. Сервер с Docker (Ubuntu 22.04+): `curl -fsSL https://get.docker.com | sh`.
2. `git clone` проекта, `cp .env.example .env`, заполнить (пароли БД и админки — свои).
3. `docker compose up -d --build`; затем импорт (см. выше).
4. Бот работает через long polling — домен не нужен. Админку наружу — только через reverse proxy с HTTPS, например Caddy:
   ```
   admin.example.com {
       reverse_proxy 127.0.0.1:8000
   }
   ```
5. Бэкап: `docker compose exec postgres pg_dump -U movies movies | gzip > backup.sql.gz`.
6. Обновление: `git pull && docker compose up -d --build` (миграции применятся автоматически сервисом `migrate`).

## Локальная разработка без Docker
```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
# нужен PostgreSQL 14+ с расширением pg_trgm (есть в стандартной поставке) и, по желанию, Redis
# в .env: DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/movies, REDIS_URL= (пусто = FSM в памяти)
alembic upgrade head && python -m app.cli seed && python -m app.bot.main
uvicorn app.api.main:app --reload     # админка
```

## Тесты
```bash
pytest                                                         # логика без БД
TEST_DATABASE_URL=postgresql+asyncpg://u:p@localhost/movies_test pytest   # + интеграционные (поиск, фильтры, похожие, пользователи)
```
⚠️ интеграционные тесты **пересоздают схему** тестовой БД — не указывайте боевую.

## Миграции
Первая (`0001`) создаёт схему из моделей и расширение `pg_trgm`. Дальше: изменили модель →
`alembic revision --autogenerate -m "что изменилось"` → проверили файл → `alembic upgrade head`.

## Дальше (архитектура это позволяет)
Oscar/Cannes/Venice/Berlin (таблицы `awards`, `movie_awards` + пресет в «Популярном») · фильмы режиссёра/актёра (уже есть `people`) ·
подборки (`collections`) · «фильм дня» и уведомления (планировщик) · профили, отзывы, лайки · ML-рекомендации поверх `user_watched` ·
импорт личного экспорта Letterboxd (CSV) · вебхуки вместо polling.
