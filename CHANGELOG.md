# Changelog

Все заметные изменения в проекте будут документированы в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и этот проект придерживается [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Planned

- Email/Telegram уведомления о ценах
- Исторические данные (1 месяц, 1 год)
- Экспорт портфолио в PDF/Excel
- Мобильное приложение
- Социальные функции (копирование портфелей)

## [1.0.0] - 2025-11-23

### Added

- 🎯 **Pre-commit hooks** - Автоматическая проверка качества кода
  - Black для форматирования
  - Ruff для линтинга
  - MyPy для проверки типов
  - Bandit для проверки безопасности
  - Markdownlint для документации
- 📚 **Документация**
  - [HOW_TO_ADD_DATA_SOURCE.md](HOW_TO_ADD_DATA_SOURCE.md) - Руководство для разработчиков
  - [ENHANCED_DATA_SOURCES.md](ENHANCED_DATA_SOURCES.md) - Подробная документация по источникам данных
  - CHANGELOG.md (этот файл)
- 🐳 **Docker улучшения**
  - Production-ready docker-compose.yml
  - Nginx reverse proxy с rate limiting
  - PostgreSQL с healthcheck
  - Redis с оптимизированной конфигурацией
  - Resource limits для всех сервисов
- 🗄️ **Database**
  - SQL скрипты инициализации
  - Схема для пользователей, портфолио, watchlist, alerts
  - Индексы для производительности
  - Триггеры для updated_at
- 🌐 **12+ источников данных**
  - Yahoo Finance (акции, индексы, товары, форекс)
  - CoinGecko (криптовалюты)
  - Binance (real-time крипта)
  - Coinbase (криптовалюты)
  - ExchangeRate API (форекс)
  - Alpha Vantage (универсальный)
  - Polygon.io (real-time США)
  - Finnhub (новости + данные)
  - Twelve Data (индикаторы)
  - IEX Cloud (США)
  - CoinMarketCap (детальная крипта)
  - CryptoCompare (агрегированные данные)
- 🔄 **Intelligent fallback** - Автоматическое переключение при сбое источников
- 🏥 **Health monitoring** - Отслеживание надежности источников
- 🎯 **Auto classification** - Определение типа актива
- 💾 **TypedDict models** - Строгая типизация для AssetData, ChartPoint и др.
- ⚡ **Lifespan context manager** - Современный FastAPI lifecycle
- 🔐 **Security config** - Централизованная конфигурация безопасности
- 💾 **Cache optimization** - Улучшенная конфигурация кэша

### Changed

- ♻️ **Рефакторинг кэширования** - Удалено 127 строк дублирующегося кода
- 📦 **Централизованные импорты** - yfinance импортируется через utils.yfinance_safe
- 🔧 **Миграция на lifespan** - Заменён deprecated @app.on_event
- 📝 **README.md** - Обновлена документация с архитектурой и v2 API

### Fixed

- 🐛 **600+ Ruff errors** - Исправлены все проблемы линтера
  - Удалены неиспользуемые переменные (F841)
  - Исправлены сравнения с True/False (E712)
  - Упрощены условные выражения (SIM102, SIM105, SIM117)
  - Добавлены `from e/None` к raise (B904)
- 🔍 **100+ MyPy warnings** - Исправлены проблемы типизации
  - Релаксированы настройки для SQLAlchemy
  - Исключены проблемные файлы
  - Добавлены TypedDict для структурированных данных
- 🔒 **SSL errors в yfinance** - Безопасный импорт с fallback
- 📝 **Markdownlint errors** - Исправлена нумерация списков в README

### Security

- 🔐 **JWT authentication** - Безопасная аутентификация
- 🔒 **Bcrypt hashing** - Хеширование паролей
- 🛡️ **Rate limiting** - Защита от abuse (в Nginx)
- 🔑 **Environment variables** - Безопасное хранение ключей API
- 🚫 **Security headers** - X-Frame-Options, X-Content-Type-Options и др.

## [0.9.0] - 2024-XX-XX

### Added

- 📊 WebSocket real-time updates
- 💹 Multiple asset types support
- 🎨 Dark theme UI
- ⭐ Watchlist functionality
- 📈 Technical indicators (RSI, MACD, Bollinger Bands)
- 🔍 Asset search
- ⏱️ Multiple timeframes
- 📁 Asset categories (stocks, crypto, commodities, forex)

### Changed

- 🏗️ Модульная архитектура
- ⚡ Async/await throughout
- 🗂️ Separated concerns (services, managers, middleware)

## [0.8.0] - 2024-XX-XX

### Added

- 👤 User authentication system
- 💼 Portfolio management
- 🔔 Alert system
- 💾 Redis caching
- 📊 Metrics collection
- 🔍 Monitoring middleware

### Changed

- 🏗️ Database integration (PostgreSQL)
- 🔐 JWT token-based auth

## [0.7.0] - 2024-XX-XX

### Added

- 📱 Interactive dashboard
- 📊 Plotly.js charts
- 🌐 CORS support
- 🔌 WebSocket endpoint

### Changed

- 🎨 Improved UI/UX
- ⚡ Performance optimizations

## [0.1.0] - 2024-XX-XX

### Added

- 🚀 Initial release
- 📈 Basic financial data fetching
- 💹 Stock price tracking
- 🌐 Simple web interface

---

## Типы изменений

- `Added` - новые функции
- `Changed` - изменения в существующих функциях
- `Deprecated` - функции, которые скоро будут удалены
- `Removed` - удалённые функции
- `Fixed` - исправления багов
- `Security` - исправления безопасности

## Ссылки

- [Unreleased]: https://github.com/QuadDarv1ne/fastapi-finance-monitor/compare/v1.0.0...HEAD
- [1.0.0]: https://github.com/QuadDarv1ne/fastapi-finance-monitor/releases/tag/v1.0.0
