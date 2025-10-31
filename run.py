"""Файл запуска для приложения FastAPI Finance Monitor"""

import uvicorn
import os
import argparse
import sys

# Версия приложения (можно вынести в отдельный файл, например, __version__.py)
__version__ = "0.1.0"


def _run_uvicorn(host: str, port: int, reload: bool, workers: int, log_level: str):
    """Внутренняя функция для запуска uvicorn с заданными параметрами."""
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level,
    )


def run_development():
    """Запуск приложения в режиме разработки с авто-перезагрузкой на localhost."""
    os.environ.setdefault("APP_ENV", "development")
    print("Запуск приложения в режиме РАЗРАБОТКИ...")
    _run_uvicorn(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
        workers=1,
        log_level="debug"
    )


def run_production():
    """Запуск приложения в режиме производства (без перезагрузки, с несколькими воркерами)."""
    os.environ.setdefault("APP_ENV", "production")
    print("Запуск приложения в режиме ПРОИЗВОДСТВА...")
    _run_uvicorn(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
        workers=int(os.environ.get("WORKERS", 4)),
        log_level="info"
    )


def run_staging():
    """Запуск приложения в промежуточном (staging) режиме — без перезагрузки, с 2 воркерами."""
    print("Запуск приложения в режиме ПРОМЕЖУТОЧНОГО СЕРВЕРА...")
    _run_uvicorn(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
        workers=2,
        log_level="info"
    )


def run_test():
    """Запуск приложения в тестовом режиме на localhost с минимальными ресурсами."""
    os.environ.setdefault("APP_ENV", "test")
    print("Запуск приложения в ТЕСТОВОМ режиме...")
    _run_uvicorn(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
        workers=1,
        log_level="warning"
    )


def run_custom(host, port, reload, workers, log_level):
    """Запуск приложения с пользовательскими параметрами из CLI или переменных окружения."""
    print("Запуск приложения с ПОЛЬЗОВАТЕЛЬСКОЙ конфигурацией...")
    _run_uvicorn(
        host=host or os.environ.get("HOST", "0.0.0.0"),
        port=port or int(os.environ.get("PORT", 8000)),
        reload=reload if reload is not None else (os.environ.get("RELOAD", "false").lower() == "true"),
        workers=workers or int(os.environ.get("WORKERS", 1)),
        log_level=log_level or os.environ.get("LOG_LEVEL", "info")
    )


def main():
    parser = argparse.ArgumentParser(
        prog="finance-monitor",
        description="Запуск FastAPI-приложения Finance Monitor в различных режимах.",
        epilog="Примеры:\n"
               "  python run.py --mode dev\n"
               "  python run.py --mode prod --port 8080\n"
               "  python run.py --mode custom --host 0.0.0.0 --port 9000 --reload --workers 2",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Показать версию приложения и выйти."
    )

    parser.add_argument(
        "--mode",
        choices=["dev", "development", "prod", "production", "staging", "test", "custom"],
        default="dev",
        help="Режим запуска: "
             "dev/development — с авто-перезагрузкой, "
             "prod/production — для боевого сервера, "
             "staging — промежуточная среда, "
             "test — локальный тестовый запуск, "
             "custom — с параметрами из командной строки."
    )

    # Аргументы для custom-режима (но могут использоваться и в других, если нужно — расширяемо)
    parser.add_argument("--host", type=str, help="Хост для привязки (по умолчанию: 0.0.0.0)")
    parser.add_argument("--port", type=int, help="Порт для привязки (по умолчанию: 8000)")
    parser.add_argument("--reload", action="store_true", help="Включить авто-перезагрузку при изменении кода")
    parser.add_argument("--workers", type=int, help="Количество рабочих процессов (только без --reload)")
    parser.add_argument("--log-level", type=str, choices=["debug", "info", "warning", "error"], 
                        help="Уровень детализации логов")

    args = parser.parse_args()
    mode = args.mode.lower()

    if mode in ("dev", "development"):
        run_development()
    elif mode in ("prod", "production"):
        run_production()
    elif mode == "staging":
        run_staging()
    elif mode == "test":
        run_test()
    elif mode == "custom":
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