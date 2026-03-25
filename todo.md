# 📋 TODO - FastAPI Finance Monitor

**Дата обновления:** 2026-03-25
**Текущая ветка:** main
**Последний коммит:** b2705ca - style: fix line endings and reformat after pre-commit hooks

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
- [x] Модели: User, Watchlist, Portfolio, Alert, HistoricalData
- [x] PostgreSQL + SQLite fallback

### Аутентификация
- [x] JWT токены (HS256)
- [x] Bcrypt хеширование паролей
- [x] Email верификация
- [x] Rate limiting для login/registration
- [x] Password requirements (8+ символов)

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
- [x] POST /api/users/login - login
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

### Тесты (31 файл)
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

## 🔨 В работе (dev → main)

### Требуется проверка
- [x] Синхронизация dev и main веток (dev ветка удалена, работа в main)
- [x] Проверка всех тестов passing (183 passed, 25 failed на 2026-03-25)
- [ ] Проверка Docker container запуска
- [ ] Проверка Redis подключения
- [ ] Проверка PostgreSQL миграций

### Изменения в работе (2026-03-25)
**Измененные файлы:**
- `app/database.py` - удален deprecated `declarative_base()`, импорт Base из `app.models`
- `app/api/routes.py` - добавлены:
  - `_convert_period_to_days()` helper (стр. 48-64)
  - `resend_verification()` endpoint (стр. 362-397)
  - `export_data()` endpoint CSV/XLSX (стр. 954-1041)

### Актуальное состояние
- **Ветка:** main (единственная рабочая)
- **Последний коммит:** b2705ca - style: fix line endings and reformat after pre-commit hooks
- **Несохраненные изменения:** routes.py, database.py (готовы к коммиту)
- **Тесты:** 183 passed, 25 failed (улучшение с 176/32)
- **Статус:** Реализован export endpoint, исправлен deprecated SQLAlchemy API

---

## 📌 Планы развития (приоритеты)

### Высокий приоритет
- [ ] **Уведомления в Telegram/Email** - реализация отправки уведомлений при срабатывании алертов
- [ ] **Email SMTP настройка** - aiosmtplib интеграция для отправки email
- [ ] **Backtesting система** - тестирование торговых стратегий на исторических данных
- [ ] **Machine Learning прогнозы** - прогнозирование цен на основе исторических данных

### Средний приоритет
- [ ] **Сравнение нескольких активов на одном графике** - полноценная реализация (сейчас mock в UI, стр. 1819-1834)
- [ ] **Исторические данные за 1 месяц/1 год** - полноценная загрузка и отображение (mock в UI, стр. 1559-1566)
- [ ] **Экспорт данных** - реальная реализация (mock в UI, стр. 1751-1756)
- [ ] **Мобильное приложение** - React Native или Flutter

### Низкий приоритет
- [ ] **PWA поддержка** - Progressive Web App для мобильных
- [ ] **GraphQL API** - альтернатива REST
- [ ] **Admin панель** - управление пользователями и системный мониторинг

---

## 🐛 Известные проблемы

### Требуется фикс
- [x] Mock реализация экспорта данных (CSV/Excel) - ✅ реализован endpoint /api/asset/{symbol}/export (routes.py:954-1041)
- [ ] Mock реализация сравнения активов - нужна реальная визуализация (UI: `loadComparisonData()`, стр. 1819)
- [ ] Mock реализация исторических данных - нужна загрузка из БД (UI: `fetchHistoricalData()`, стр. 1559)
- [ ] WebSocket reconnect может создавать дублирующие соединения (требуется проверка `data_stream_worker`)

### Замечания по коду
- [x] `app/main.py:272-273` - Дублирование глобальных переменных `background_tasks` и `startup_complete` (объявлены дважды)
- [x] `app/api/websocket.py:70-71` - TIMEFRAME_MAPPING: 10m мапится на 15m (комментарий "Yahoo Finance uses 15m for 10m equivalent")
- [x] `app/api/websocket.py:476-689` - FINANCIAL_INSTRUMENTS: 400+ символов, требует вынесения в отдельный конфиг
- [x] `app/api/websocket.py:48` - Duplicated Prometheus metrics (исправлено через custom CollectorRegistry)
- [x] `app/models.py:95` - MovedIn20Warning: sqlalchemy.orm.declarative_base() deprecated (обновлено на DeclarativeBase)

### Failing тесты (25 failed, 2026-03-25)
| Тест | Проблема |
|------|----------|
| test_portfolio_endpoints (7 failed) | 400/403 errors - auth/валидация |
| test_data_fetcher_enhanced_errors (5 failed) | fallback логика ошибок |
| test_registration (3 failed) | 429 Too Many Requests (rate limiting) |
| test_email_verification (2 failed) | SMTP не настроен |
| test_enhanced_cache_service (2 failed) | partition_stats не реализован |
| test_advanced_portfolio_analytics (1 failed) | VaR расчет |
| test_alert_service (3 failed) | DB session issues |
| test_monitoring_service (1 failed) | response_times metric |

### Потенциальные улучшения
- [ ] Rate limiting можно вынести в Redis для distributed rate limiting
- [ ] JWT refresh tokens для долгоживущих сессий
- [ ] OAuth2 провайдеры (Google, GitHub login)
- [ ] Двухфакторная аутентификация (2FA)

---

## 📊 Метрики проекта

```
Файлов Python:     ~70
Тестов:            31
API Endpoints:     25+
Источников данных: 12+
Активов:           400+ (расширено в websocket.py)
Строк кода:        ~10,000+
```

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

---

## 📝 Заметки по разработке

### Рабочий процесс (обновлено 2026-03-25)
1. Все изменения в main (dev ветка удалена)
2. Запуск тестов: `pytest app/tests/`
3. Проверка pre-commit: `pre-commit run --all-files`
4. Коммит с описанием изменений

### Результаты тестов (2026-03-25, обновлено)
```
Итого: 208 тестов
✅ Passed: 183
❌ Failed: 25
```

**Причины failures:**
1. **Rate limiting** - тесты registration получают 429 вместо 422 (требуют сброса rate limit между тестами)
2. **Auth/permissions** - portfolio endpoints возвращают 403 Forbidden (проблемы с JWT токенами в тестах)
3. **DB session** - alert service тесты failing (session lifecycle issues)
4. **Cache partitioning** - enhanced cache service не реализован полностью (partition_stats)
5. **SMTP не настроен** - email верификация не работает (требуется mock SMTP)
6. **Fallback логика** - data_fetcher error handling требует доработки
7. **VaR расчет** - advanced portfolio analytics edge cases

**Исправлено:**
- ✅ Экспорт данных - реализован endpoint /api/asset/{symbol}/export
- ✅ Historical data helper - `_convert_period_to_days()` добавлен в routes.py
- ✅ SQLAlchemy deprecated API - заменено на DeclarativeBase
- ✅ Duplicate Prometheus metrics - исправлено через CollectorRegistry

### Критические файлы для тестирования
| Файл | Назначение | Приоритет |
|------|------------|-----------|
| `app/main.py` | Основное приложение, lifespan, middleware | 🔴 Высокий |
| `app/api/websocket.py` | WebSocket менеджер, 400+ активов | 🔴 Высокий |
| `app/services/enhanced_data_fetcher.py` | Multi-source данные с fallback | 🔴 Высокий |
| `app/services/redis_cache_service.py` | Redis кэширование | 🟡 Средний |
| `app/services/advanced_alert_service.py` | Система алертов | 🟡 Средний |

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
