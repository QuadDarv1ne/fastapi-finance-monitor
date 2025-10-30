"""Файл запуска для приложения FastAPI Finance Monitor"""

import uvicorn
import os
import sys
import argparse

def run_development():
    """Запуск приложения в режиме разработки с авто-перезагрузкой"""
    print("Запуск приложения в режиме РАЗРАБОТКИ...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
        log_level="debug"
    )

def run_production():
    """Запуск приложения в режиме производства"""
    print("Запуск приложения в режиме ПРОИЗВОДСТВА...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
        log_level="info",
        workers=int(os.environ.get("WORKERS", 4))
    )

def run_staging():
    """Запуск приложения в режиме промежуточного сервера"""
    print("Запуск приложения в режиме ПРОМЕЖУТОЧНОГО СЕРВЕРА...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
        log_level="info",
        workers=2
    )

def run_test():
    """Запуск приложения в тестовом режиме с минимальными ресурсами"""
    print("Запуск приложения в ТЕСТОВОМ режиме...")
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
        log_level="warning",
        workers=1
    )

def run_uvicorn_direct():
    """Запуск приложения напрямую с помощью uvicorn с пользовательскими параметрами"""
    print("Запуск приложения в режиме UVICORN DIRECT...")
    # Получение переменных окружения или использование значений по умолчанию
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    reload = os.environ.get("RELOAD", "false").lower() == "true"
    workers = int(os.environ.get("WORKERS", 1))
    log_level = os.environ.get("LOG_LEVEL", "info")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level
    )

def run_custom(host=None, port=None, reload=None, workers=None, log_level=None):
    """Запуск приложения с пользовательскими параметрами"""
    print("Запуск приложения с ПОЛЬЗОВАТЕЛЬСКОЙ конфигурацией...")
    
    # Использование переданных параметров или значений по умолчанию
    host = host or os.environ.get("HOST", "0.0.0.0")
    port = port or int(os.environ.get("PORT", 8000))
    reload = reload if reload is not None else os.environ.get("RELOAD", "false").lower() == "true"
    workers = workers or int(os.environ.get("WORKERS", 1))
    log_level = log_level or os.environ.get("LOG_LEVEL", "info")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level
    )

def main():
    parser = argparse.ArgumentParser(description="Запуск FastAPI Finance Monitor")
    parser.add_argument(
        "--mode", 
        choices=["dev", "development", "prod", "production", "staging", "test", "uvicorn", "custom"],
        default="dev",
        help="Режим запуска: dev/development, prod/production, staging, test, uvicorn, custom"
    )
    
    # Поддержка флага --uvicorn как ярлыка
    parser.add_argument(
        "--uvicorn",
        action="store_true",
        help="Запуск приложения напрямую с помощью uvicorn (эквивалентно --mode uvicorn)"
    )
    
    # Пользовательские аргументы для режима uvicorn
    parser.add_argument("--host", type=str, help="Хост для привязки")
    parser.add_argument("--port", type=int, help="Порт для привязки")
    parser.add_argument("--reload", action="store_true", help="Включить авто-перезагрузку")
    parser.add_argument("--workers", type=int, help="Количество рабочих процессов")
    parser.add_argument("--log-level", type=str, help="Уровень логирования (debug, info, warning, error)")
    
    args = parser.parse_args()
    
    # Проверка использования флага --uvicorn
    if args.uvicorn:
        run_uvicorn_direct()
        return
    
    mode = args.mode.lower()
    
    if mode in ["dev", "development"]:
        run_development()
    elif mode in ["prod", "production"]:
        run_production()
    elif mode == "staging":
        run_staging()
    elif mode == "test":
        run_test()
    elif mode == "uvicorn":
        # Использование переменных окружения для режима uvicorn
        run_uvicorn_direct()
    elif mode == "custom":
        # Использование аргументов командной строки для пользовательского режима
        run_custom(
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
            log_level=args.log_level
        )
    else:
        print(f"Неизвестный режим: {mode}. Используется режим разработки.")
        run_development()

if __name__ == "__main__":
    main()