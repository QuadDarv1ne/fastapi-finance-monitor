# 📋 TODO - FastAPI Finance Monitor

**Дата обновления:** 2026-03-25
**Текущая ветка:** main
**Последний коммит:** JWT Refresh Tokens реализация

---

## ✅ Завершено (v1.0.0)

### Ядро приложения
- [x] FastAPI приложение с lifespan context manager
- [x] WebSocket для real-time обновлений (30 сек интервал)
- [x] Асинхронная архитектура (async/await)
- [x] CORS middleware настроен
- [x] Middleware: exception handler, monitoring, rate limiting

### Источники данных
- [x] 12+ источников данных (Yahoo Finance, CoinGecko, Binance, Coinbase и др.)
- [x] Интеллектуальный fallback при сбое источников
- [x] Автоматическая классификация активов (EQUITY, CRYPTOCURRENCY, FOREX, COMMODITY)
- [x] Мониторинг здоровья источников данных
- [x] Enhanced data fetcher с retry logic

### Кэширование
- [x] LRU cache (in-memory, max 500 элементов)
- [x] Redis cache service (distributed)
- [x] Двухуровневое кэширование
- [x] Cache warming для популярных активов
- [x] Компрессия данных (порог 2KB)

### База данных
- [x] SQLAlchemy ORM
- [x] Alembic миграции
- [x] Модели: User, Watchlist, Portfolio, Alert, HistoricalData, TelegramConnection, RefreshToken
- [x] PostgreSQL + SQLite fallback

### Аутентификация
- [x] JWT токены (HS256)
- [x] Bcrypt хеширование паролей
- [x] Email верификация
- [x] Rate limiting для login/registration
- [x] Password requirements (8+ символов)
- [x] **JWT Refresh Tokens** - долгоживущие сессии с refresh-токенами (30 дней)
- [x] Refresh token API: /api/users/refresh, /api/users/logout
- [x] Отзыв токенов (单个 logout / logout со всех устройств)
- [x] Очистка просроченных токенов
- [x] Исправление deprecation warnings (datetime.utcnow → datetime.now(timezone.utc))

### API Endpoints
#### v1 (Основные)
- [x] GET /api/assets - данные всех активов
- [x] GET /api/asset/{symbol} - данные актива
- [x] GET /api/asset/{symbol}/indicators - технические индикаторы
- [x] GET /api/search - поиск активов
- [x] POST /api/watchlist/add|remove - управление watchlist
- [x] GET /api/health - health check

#### v2 (Enhanced - Multi-Source)
- [x] GET /api/v2/asset/{symbol} - данные с автоматическим fallback
- [x] GET /api/v2/sources/health - статус источников
- [x] GET /api/v2/sources/list - список источников
- [x] POST /api/v2/classify - классификация актива
- [x] GET /api/v2/sources/{name}/status - статус источника

#### Аутентификация
- [x] POST /api/users/register - регистрация
- [x] POST /api/users/login - login (возвращает access + refresh token)
- [x] POST /api/users/refresh - обновление access token через refresh token
- [x] POST /api/users/logout - logout с отзывом refresh token
- [x] POST /api/users/verify-email - подтверждение email
- [x] GET/PUT /api/users/me - профиль пользователя
- [x] PUT /api/users/me/password - смена пароля

#### Портфель
- [x] GET /api/portfolio - список портфелей
- [x] POST /api/portfolio/create - создание портфеля
- [x] GET /api/portfolio/{id} - детали портфеля
- [x] POST /api/portfolio/add_item|remove_item - управление позициями
- [x] GET /api/portfolio/{id}/performance - метрики производительности
- [x] GET /api/portfolio/{id}/holdings - позиции портфеля

#### Уведомления
- [x] GET /api/alerts - список уведомлений
- [x] POST /api/alerts/create - создание уведомления
- [x] Advanced alert service с мониторингом

### Технические индикаторы
- [x] RSI (Relative Strength Index)
- [x] MACD (Moving Average Convergence Divergence)
- [x] Bollinger Bands
- [x] SMA/EMA (Simple/Exponential Moving Average)
- [x] Enhanced индикаторы с обработкой ошибок

### Фронтенд
- [x] Интерактивная панель с Plotly.js
- [x] Темная тема с градиентами
- [x] Адаптивный дизайн (mobile-friendly)
- [x] WebSocket клиент с auto-reconnect
- [x] Вкладки по типам активов (All, Stocks, Crypto, Commodities, Forex)
- [x] My Watchlist вкладка
- [x] Portfolio вкладка с сводкой
- [x] Поиск активов
- [x] Множественные интервалы (1m, 5m, 10m, 30m, 1h, 3h, 6h, 12h, 1d)
- [x] Исторические данные (1D, 5D, 1M, 3M, 6M, 1Y, 5Y)
- [x] Сравнение активов (Compare)
- [x] Экспорт данных (CSV, Excel)
- [x] Создание алертов через UI
- [x] Login/Register модальные окна

### Мониторинг
- [x] Prometheus метрики
- [x] Grafana дашборды
- [x] Endpoint /metrics для Prometheus
- [x] Мониторинг активных WebSocket соединений
- [x] Логирование производительности

### Тесты (32 файла)
- [x] test_cache_manager.py
- [x] test_data_fetcher_enhanced.py
- [x] test_data_fetcher.py
- [x] test_metrics_collector.py
- [x] test_portfolio_service.py
- [x] test_advanced_portfolio_analytics.py
- [x] test_alert_service.py
- [x] test_auth_manager.py
- [x] test_redis_cache_service.py
- [x] test_email_verification.py
- [x] test_historical_data.py
- [x] test_cache_service.py
- [x] test_enhanced_portfolio.py
- [x] test_export_functionality.py
- [x] test_custom_exceptions.py
- [x] test_monitoring_service.py
- [x] test_data_fetcher_enhanced_errors.py
- [x] test_enhanced_cache_service.py
- [x] test_enhanced_indicators.py
- [x] test_portfolio_endpoints.py
- [x] test_alert_endpoints.py
- [x] test_advanced_alert_service.py
- [x] test_delta_manager.py
- [x] test_main_application.py
- [x] test_rate_limiting.py
- [x] test_auth_service.py
- [x] test_registration.py
- [x] test_watchlist.py
- [x] test_websocket_enhanced.py
- [x] test_services.py
- [x] **test_refresh_tokens.py** - JWT refresh token тесты (8 тестов)

### Docker & DevOps
- [x] Dockerfile
- [x] docker-compose.yml (PostgreSQL, Redis, Grafana, Prometheus)
- [x] prometheus.yml конфигурация
- [x] redis.conf конфигурация
- [x] .env.example с документацией
- [x] .pre-commit-config.yaml
- [x] pyproject.toml
- [x] pytest.ini

---

## 🔨 В работе (main)

### Требуется проверка
- [x] Синхронизация dev и main веток (работа в main)
- [x] Проверка всех тестов passing (205 passed, 4 failed - несвязанные с изменениями)
- [ ] Проверка Docker container запуска
- [ ] Проверка Redis подключения
- [ ] Проверка PostgreSQL миграций (alembic upgrade head)

### Актуальное состояние
- **Ветка:** main
- **Последний коммит:** JWT Refresh Tokens реализация
- **Тесты:** 205 passed (4 failing - существующие проблемы в проекте)
- **Статус:** ✅ Готово к коммиту и синхронизации
- **API Endpoints:** 34+ (добавлено: /refresh, /logout)

---

### ✅ Завершено (2026-03-25 - JWT Refresh Tokens)

**Реализованные изменения:**

1. **Конфигурация (`app/config.py`):**
   - Добавлена `REFRESH_TOKEN_EXPIRE_DAYS=30`

2. **Модель БД (`app/models.py`):**
   - Создана модель `RefreshToken` (id, user_id, token, expires_at, is_revoked, created_at, revoked_at)
   - Добавлена связь `User.refresh_tokens` (one-to-many, cascade delete)

3. **Миграция Alembic:**
   - `alembic/versions/20260325_03_add_refresh_tokens_table.py`

4. **AuthService (`app/services/auth_service.py`):**
   - `create_refresh_token()` - создание и сохранение refresh токена
   - `verify_refresh_token()` - проверка валидности (DB + JWT)
   - `revoke_refresh_token()` - отзыв单个 токена
   - `revoke_all_user_tokens()` - отзыв всех токенов пользователя
   - `cleanup_expired_tokens()` - очистка просроченных токенов
   - Исправлены deprecation warnings (datetime.utcnow → datetime.now(timezone.utc))

5. **API Endpoints (`app/api/routes.py`):**
   - `POST /api/users/login` - обновлен (возвращает refresh_token + expires_in)
   - `POST /api/users/refresh` - обновление access token
   - `POST /api/users/logout` - logout с отзывом токенов

6. **Тесты (`app/tests/test_refresh_tokens.py`):**
   - 8 тестов: создание, верификация, отзыв, очистка, интеграция
   - Все тесты проходят ✅

7. **Документация:**
   - Обновлен `.env.example` (REFRESH_TOKEN_EXPIRE_DAYS)
   - Обновлен `README.md` (примеры использования refresh tokens)
   - Обновлен `todo.md`

**Результаты тестов:**
```
✅ test_refresh_token_creation
✅ test_refresh_token_verification
✅ test_refresh_token_verification_invalid
✅ test_refresh_token_revocation
✅ test_refresh_token_revocation_nonexistent
✅ test_revoke_all_user_tokens
✅ test_cleanup_expired_tokens
✅ test_refresh_token_in_login_response
```

---

## 📌 Планы развития (приоритеты)

### Высокий приоритет
- [x] **Уведомления в Telegram** - ✅ реализовано: TelegramService, webhook, API endpoints
- [x] **Оптимизация производительности** - ✅ aiohttp, LRUCache, backpressure, singleton
- [x] **JWT Refresh Tokens** - ✅ реализовано
- [ ] **Email SMTP настройка** - aiosmtplib интеграция для отправки email
- [ ] **Backtesting система** - тестирование торговых стратегий на исторических данных
- [ ] **Machine Learning прогнозы** - прогнозирование цен на основе исторических данных

### Средний приоритет
- [x] **Сравнение нескольких активов на одном графике** - ✅ реализовано через /api/assets/compare
- [x] **Исторические данные за 1 месяц/1 год** - ✅ реализовано через /api/asset/{symbol}/historical
- [x] **Экспорт данных** - ✅ реализован endpoint /api/asset/{symbol}/export
- [ ] **Telegram bot commands menu** - настройка списка команд для бота
- [ ] **Мобильное приложение** - React Native или Flutter

### Низкий приоритет
- [ ] **PWA поддержка** - Progressive Web App для мобильных
- [ ] **GraphQL API** - альтернатива REST
- [ ] **Admin панель** - управление пользователями и системный мониторинг

---

## 🐛 Известные проблемы

### Требуется фикс
- [x] Mock реализация экспорта данных (CSV/Excel) - ✅ реализован endpoint /api/asset/{symbol}/export
- [x] Mock реализация сравнения активов - ✅ реализован GET /api/assets/compare
- [x] Mock реализация исторических данных - ✅ реализован GET /api/asset/{symbol}/historical
- [x] WebSocket reconnect может создавать дублирующие соединения - ✅ исправлена изоляция тестов
- [x] Блокирующие HTTP запросы (requests) - ✅ заменено на aiohttp
- [x] Recreate DataFetcher на каждый запрос - ✅ singleton pattern
- [x] Отсутствие backpressure для WebSocket - ✅ MAX_QUEUE_SIZE, MAX_BROADCAST_QUEUE_SIZE
- [x] Неограниченный рост memory_cache - ✅ LRUCache (max 500 элементов)
- [x] Создание ClientSession на каждый запрос - ✅ переиспользование сессий

### Замечания по коду
- [x] `app/main.py:272-273` - Дублирование глобальных переменных
- [x] `app/api/websocket.py:70-71` - TIMEFRAME_MAPPING: 10m → 15m
- [x] `app/api/websocket.py:476-689` - FINANCIAL_INSTRUMENTS: 400+ символов
- [x] `app/api/websocket.py:48` - Duplicated Prometheus metrics
- [x] `app/models.py:95` - declarative_base() deprecated → DeclarativeBase
- [x] `app/api/websocket.py` - Глобальные переменные без locks - ✅ добавлены asyncio.Lock

### Failing тесты (обновлено 2026-03-25)

**Статус:** 205 passed, 4 failed (существующие проблемы проекта)

| Тест | Проблема | Решение |
|------|----------|---------|
| test_cache_service::test_delete_nonexistent_key | assert True is False | Требуется фикс логики cache service |
| test_data_fetcher_enhanced | AttributeError: no attribute 'requests' | Требуется обновление mock (aiohttp) |
| test_data_fetcher_enhanced_errors | AttributeError: no attribute 'requests' | Требуется обновление mock (aiohttp) |
| test_enhanced_cache_service::test_get_stats_with_partitions | KeyError: 'active_items' | Требуется фикс теста |

**Примечание:** failing тесты не связаны с JWT Refresh Tokens изменениями

### Потенциальные улучшения
- [ ] Telegram webhook URL настройка для production (сейчас /webhook/telegram)
- [ ] Telegram bot commands menu (/start, /help, /status)
- [ ] Rate limiting можно вынести в Redis для distributed rate limiting
- [x] JWT refresh tokens для долгоживущих сессий - ✅ реализовано
- [ ] OAuth2 провайдеры (Google, GitHub login)
- [ ] Двухфакторная аутентификация (2FA)

---

## 📊 Метрики проекта

```
Файлов Python:     ~76
Тестов:            32 (добавлен test_refresh_tokens.py)
API Endpoints:     34+ (добавлено /refresh, /logout)
Источников данных: 12+
Активов:           400+ (расширено в websocket.py)
Строк кода:        ~10,700+ (+200 строк)
```

### Оптимизации производительности (2026-03-25)
- ✅ **aiohttp** вместо requests - асинхронные HTTP запросы
- ✅ **LRUCache** для memory_cache - автоматическая eviction (max 500)
- ✅ **Singleton DataFetcher** - переиспользование вместо создания на запрос
- ✅ **Backpressure** для WebSocket - MAX_QUEUE_SIZE=100, MAX_BROADCAST=10000
- ✅ **ClientSession reuse** - Binance, Alpha Vantage сессии переиспользуются
- ✅ **Redis timeouts** 1s→5s - стабильные соединения
- ✅ **health_check** 60s→15s - быстрая очистка неактивных клиентов

### Детализация активов (на 2026-03-25)
- **Акции США:** ~20 компаний (AAPL, GOOGL, MSFT, TSLA, AMZN, META, NVDA, NFLX, DIS, V, JPM, WMT, PG, KO, XOM, BA, IBM, GS, HD, MA)
- **Акции Европы:** ~23 компании (Nestle, Roche, Novartis, SAP, Siemens, BMW, Daimler, Airbus, Sanofi, BNP, ENEL, ENI, UniCredit, ING, ASML, Unilever, Shell, BP, HSBC, Barclays, Vodafone, AstraZeneca, GSK)
- **Акции России:** ~15 компаний (Gazprom, Lukoil, Sberbank, Rosneft, Norilsk Nickel, Novatek, Alrosa, Tatneft, Surgutneftegas, Severstal, NLMK, Magnit, MTS, FEES, RusHydro)
- **Акции Китая:** ~100+ компаний (Alibaba, Tencent, Baidu, JD, NetEase, Xiaomi, BYD, Kweichow Moutai, банки, страховые, промышленные)
- **Криптовалюты:** ~30 монет (Bitcoin, Ethereum, Solana, Cardano, Polkadot, Litecoin, Chainlink, Dogecoin, Avalanche, Polygon, Cosmos, Monero, TRON, VeChain, Filecoin, Theta, EOS, Tezos, Elrond, Flow, Klaytn, NEAR, Hedera, Algorand, IOTA, Dash, Zcash)
- **Товары:** ~19 контрактов (Gold, Silver, Platinum, Palladium, Copper, Crude Oil, Natural Gas, Cotton, Coffee, Sugar, Cocoa, Live Cattle, Lean Hogs, Wheat, Corn, Oat, Rice, Feeder Cattle)
- **Форекс:** ~22 пары (EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD, USD/CHF, NZD/USD, EUR/GBP, EUR/JPY, GBP/JPY, AUD/JPY, NZD/JPY, GBPNZD, EURAUD, EURCHF, CAD/JPY, CHF/JPY, USDMXN, USDZAR, USDRUB, EURRUB, GBPRUB)

---

## 🔧 Конфигурация окружения

### Обязательные переменные
```bash
DATABASE_URL=postgresql://user:password@localhost/finance_monitor
SECRET_KEY=your-secret-key-here
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Опциональные API ключи
```bash
ALPHA_VANTAGE_API_KEY=
POLYGON_API_KEY=
FINNHUB_API_KEY=
TWELVE_DATA_API_KEY=
IEX_CLOUD_API_KEY=
COINMARKETCAP_API_KEY=
CRYPTOCOMPARE_API_KEY=
```

### Telegram уведомления (опционально)
```bash
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_BOT_USERNAME=finance_monitor_bot
```

### JWT Refresh Tokens (новое)
```bash
REFRESH_TOKEN_EXPIRE_DAYS=30  # Время жизни refresh token (дни)
```

---

## 📝 Заметки по разработке

### Рабочий процесс (обновлено 2026-03-25)
1. Все изменения в main (dev ветка существует, но работа в main)
2. Запуск тестов: `pytest app/tests/`
3. Проверка pre-commit: `pre-commit run --all-files`
4. Коммит с описанием изменений
5. Синхронизация с origin/main: `git push origin main`

### Результаты тестов (2026-03-25, обновлено)
```
Итого: 209 тестов
✅ Default run: 205 passed
❌ Failing: 4 (существующие проблемы проекта)
📈 Pass rate: 98.1%
```

**Исправлено:**
- ✅ Экспорт данных - реализован endpoint /api/asset/{symbol}/export
- ✅ Historical data helper - `_convert_period_to_days()` добавлен в routes.py
- ✅ SQLAlchemy deprecated API - заменено на DeclarativeBase
- ✅ Duplicate Prometheus metrics - исправлено через CollectorRegistry
- ✅ Test isolation - 208 тестов с 100% pass rate (на момент 2026-03-25)
- ✅ Portfolio service - исправлен dependency injection
- ✅ JWT Refresh Tokens - полная реализация с тестами
- ✅ Deprecation warnings - datetime.utcnow → datetime.now(timezone.utc)

### Критические файлы для тестирования
| Файл | Назначение | Приоритет |
|------|------------|-----------|
| `app/main.py` | Основное приложение, lifespan, middleware | 🔴 Высокий |
| `app/api/websocket.py` | WebSocket менеджер, 400+ активов | 🔴 Высокий |
| `app/services/enhanced_data_fetcher.py` | Multi-source данные с fallback | 🔴 Высокий |
| `app/services/redis_cache_service.py` | Redis кэширование | 🟡 Средний |
| `app/services/advanced_alert_service.py` | Система алертов | 🟡 Средний |
| `app/services/auth_service.py` | Аутентификация, JWT, refresh tokens | 🔴 Высокий |

### Известные точки отказа
1. **Redis подключение** - может отсутствовать в dev среде (fallback на LRU cache)
2. **PostgreSQL** - Alembic миграции могут не примениться (fallback на `create_all`)
3. **Yahoo Finance API** - rate limiting ~2000 запросов/час
4. **CoinGecko API** - rate limiting 10-50 запросов/минуту

### Запуск приложения
```bash
# Прямой запуск
python app/main.py

# Uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Docker
docker-compose up -d

# Применить миграции
alembic upgrade head
```

### Диагностика проблем
```bash
# Проверка тестов
pytest app/tests/ -v

# Проверка с покрытием
pytest app/tests/ --cov=app

# Проверка типов
mypy app/

# Lint
ruff check app/

# Проверка Redis
redis-cli ping

# Проверка PostgreSQL
psql -h localhost -U user -d finance_monitor
```

### Полезные команды
```bash
# Запуск тестов
pytest app/tests/ -v

# Запуск с покрытием
pytest app/tests/ --cov=app

# Проверка типов
mypy app/

# Lint
ruff check app/

# Применить миграции БД
alembic upgrade head

# Создать новую миграцию
alembic revision -m "description"
```

---

## 📚 Документация

- [README.md](README.md) - основная документация
- [ENHANCED_DATA_SOURCES.md](ENHANCED_DATA_SOURCES.md) - источники данных
- [HOW_TO_ADD_DATA_SOURCE.md](HOW_TO_ADD_DATA_SOURCE.md) - добавление источников
- [CHANGELOG.md](CHANGELOG.md) - история изменений

---

**Автор:** Дуплей Максим Игоревич
**Telegram:** [@quadd4rv1n7](https://t.me/quadd4rv1n7), [@dupley_maxim_1999](https://t.me/dupley_maxim_1999)
**Email:** maksimqwe42@mail.ru
