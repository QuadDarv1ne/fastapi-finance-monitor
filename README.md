# 📊 FastAPI Finance Monitor

Информационная панель для мониторинга финансовых активов в реальном времени

## ✨ Возможности

- 📈 **Графики в реальном времени** - обновление каждые 30 секунд через WebSocket
- 💹 **Множество типов активов** - акции (Apple, Google, Microsoft, Tesla), криптовалюты (Bitcoin, Ethereum, Solana), товары (Золото)
- 📊 **Интерактивные графики** - свечные графики для акций, линейные графики для криптовалют (Plotly.js)
- 🎨 **Современный интерфейс** - темная тема, адаптивный дизайн с плавной анимацией
- ⚡ **Асинхронная архитектура** - FastAPI + async/await для высокой производительности
- 🔌 **WebSocket** - мгновенные обновления без перезагрузки страницы
- 🌟 **Списки наблюдения** - персонализированный трекинг активов
- 📈 **Технические индикаторы** - RSI, MACD, Bollinger Bands и другие
- 🔍 **Поиск активов** - поиск и добавление новых активов для отслеживания

## 🏗️ Архитектура

```bash
fastapi-finance-monitor/
├── app/
│   ├── main.py              # Основное приложение FastAPI
│   ├── models.py            # Модели данных Pydantic
│   ├── config.py            # Конфигурационные настройки
│   ├── api/
│   │   ├── routes.py        # REST API эндпоинты
│   │   └── websocket.py     # WebSocket для данных в реальном времени
│   ├── services/
│   │   ├── data_fetcher.py  # Получение данных с бирж
│   │   ├── indicators.py    # Технические индикаторы
│   │   └── watchlist.py     # Управление списками наблюдения
│   ├── tests/
│   │   └── test_services.py # Модульные тесты
├── requirements.txt         # Зависимости Python
├── Dockerfile               # Docker конфигурация
├── docker-compose.yml       # Docker Compose конфигурация
├── .dockerignore            # Файлы для игнорирования в Docker
└── README.md               # Документация
```

## 🚀 Быстрый старт

### Установка

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/fastapi-finance-monitor.git
cd fastapi-finance-monitor

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### Запуск приложения

```bash
# Прямой запуск:
python app/main.py

# Или с помощью uvicorn:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Или с помощью Docker:
docker-compose up -d
```

Откройте браузер: **http://localhost:8000**

## 🔧 Используемые технологии

### Бэкенд

- **FastAPI** - Современный асинхронный веб-фреймворк
- **WebSocket** - Коммуникация в реальном времени
- **yfinance** - Данные Yahoo Finance (акции, товары)
- **CoinGecko API** - Данные криптовалют
- **Pandas** - Обработка данных
- **NumPy** - Числовые вычисления

### Фронтенд

- **Plotly.js** - Интерактивные графики
- **Vanilla JavaScript** - Клиент WebSocket
- **CSS3** - Современный адаптивный дизайн
- **Font Awesome** - Иконки

## 📊 Отслеживаемые активы

По умолчанию отслеживаются следующие активы:

| Актив | Тип | Источник |
|-------|-----|----------|
| Apple (AAPL) | Акция | Yahoo Finance |
| Google (GOOGL) | Акция | Yahoo Finance |
| Microsoft (MSFT) | Акция | Yahoo Finance |
| Tesla (TSLA) | Акция | Yahoo Finance |
| Gold (GC=F) | Товар | Yahoo Finance |
| Bitcoin | Криптовалюта | CoinGecko |
| Ethereum | Криптовалюта | CoinGecko |
| Solana | Криптовалюта | CoinGecko |

## 🎯 API Эндпоинты

### REST API

- `GET /` - Главная страница информационной панели
- `GET /api/assets` - Получить данные для всех активов в списке наблюдения
- `GET /api/asset/{symbol}` - Получить данные для конкретного актива
- `GET /api/asset/{symbol}/indicators` - Получить технические индикаторы для актива
- `GET /api/search` - Поиск активов
- `POST /api/watchlist/add` - Добавить актив в список наблюдения
- `POST /api/watchlist/remove` - Удалить актив из списка наблюдения
- `GET /api/watchlist` - Получить список наблюдения пользователя
- `GET /api/health` - Проверка состояния

### WebSocket

- `WS /ws` - Обновления данных в реальном времени

Пример подключения:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

## 🔨 Кастомизация

### Добавление новых активов

Добавьте новые активы в список наблюдения по умолчанию в [watchlist.py](app/services/watchlist.py):

```python
default_assets = [
    "AAPL", "GOOGL", "MSFT", "TSLA", "GC=F",
    "bitcoin", "ethereum", "solana"
]
```

### Изменение интервала обновления

Измените интервал обновления в [websocket.py](app/api/websocket.py):

```python
await asyncio.sleep(30)  # 30 секунд -> любое значение
```

### Добавление технических индикаторов

Сервис [indicators.py](app/services/indicators.py) включает RSI, MACD, Bollinger Bands и другие. Вы можете добавить дополнительные индикаторы при необходимости.

## 📈 Примеры использования

### Получение данных через API

```bash
curl http://localhost:8000/api/assets
```

### Подключение к WebSocket (Python)

```python
import asyncio
import websockets
import json

async def listen():
    async with websockets.connect('ws://localhost:8000/ws') as ws:
        while True:
            message = await ws.recv()
            data = json.loads(message)
            print(data)

asyncio.run(listen())
```

## ⚠️ Важные замечания

1. **Ограничения по запросам** - Yahoo Finance и CoinGecko имеют ограничения. Не уменьшайте интервал обновления менее чем до 10 секунд
2. **API ключи** - Текущая версия использует бесплатные API без ключей. Для продакшена используйте платные API с ключами
3. **Данные в реальном времени** - Yahoo Finance предоставляет данные с задержкой ~15 минут для некоторых бирж

## 🚀 Планы развития

- [x] Модульная архитектура проекта
- [x] Технические индикаторы (RSI, MACD, Bollinger Bands, и др.)
- [x] Списки наблюдения и избранное
- [x] Улучшенный интерфейс с темной темой и анимациями
- [ ] Кэширование Redis для улучшения производительности
- [ ] Уведомления по электронной почте/Telegram о ценах
- [ ] Исторические данные (просмотр за 1 месяц, 1 год)
- [ ] Сравнение нескольких активов на одном графике
- [ ] Экспорт данных (CSV, Excel)
- [ ] Аутентификация пользователей
- [ ] Персональные списки наблюдения
- [ ] Мобильное приложение

## 📝 Лицензия

[Этот проект лицензирован под лицензией MIT](LICENCE)

Для получения дополнительной информации ознакомьтесь с файлом `LICENSE`

## 🤝 Участие в разработке

Pull requests приветствуются! Для крупных изменений сначала создайте issue.

## 📧 Контакты

Вопросы и предложения: [создайте issue](https://github.com/yourusername/fastapi-finance-monitor/issues)

---

**Сделано с ❤️ используя FastAPI**

---

💼 **Автор:** Дуплей Максим Игоревич

📲 **Telegram №1:** [@quadd4rv1n7](https://t.me/quadd4rv1n7)

📲 **Telegram №2:** [@dupley_maxim_1999](https://t.me/dupley_maxim_1999)

📅 **Дата:** 29.10.2025

▶️ **Версия 1.0**

```textline
※ Предложения по сотрудничеству можете присылать на почту ※
📧 maksimqwe42@mail.ru
```