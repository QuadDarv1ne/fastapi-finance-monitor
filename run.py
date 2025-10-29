#!/usr/bin/env python3
"""
Скрипт запуска для FastAPI Finance Monitor
"""

import sys
import os
import argparse
import subprocess
import time

def run_direct():
    """Запуск приложения напрямую"""
    print("Запуск FastAPI Finance Monitor...")
    print("Откройте в браузере http://localhost:8000")
    print("Нажмите Ctrl+C для остановки")
    print()
    
    try:
        # Запуск основного приложения
        subprocess.run([sys.executable, "app/main.py"], check=True)
    except KeyboardInterrupt:
        print("\nПриложение остановлено.")
    except Exception as e:
        print(f"Ошибка запуска приложения: {e}")

def run_uvicorn():
    """Запуск приложения с помощью uvicorn"""
    print("Запуск FastAPI Finance Monitor с помощью Uvicorn...")
    print("Откройте в браузере http://localhost:8000")
    print("Нажмите Ctrl+C для остановки")
    print()
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ], check=True)
    except KeyboardInterrupt:
        print("\nПриложение остановлено.")
    except Exception as e:
        print(f"Ошибка запуска приложения: {e}")

def run_docker():
    """Запуск приложения с помощью Docker"""
    print("Запуск FastAPI Finance Monitor с помощью Docker...")
    print("Убедитесь, что Docker установлен и запущен")
    print()
    
    try:
        subprocess.run(["docker-compose", "up"], check=True)
    except FileNotFoundError:
        print("Docker Compose не найден. Пожалуйста, установите Docker Desktop.")
    except KeyboardInterrupt:
        print("\nОстановка Docker контейнеров...")
        subprocess.run(["docker-compose", "down"])
    except Exception as e:
        print(f"Ошибка запуска Docker: {e}")

def test_application():
    """Запуск базовых тестов"""
    print("Запуск базовых тестов...")
    print()
    
    try:
        subprocess.run([sys.executable, "test_functionality.py"], check=True)
    except Exception as e:
        print(f"Ошибка запуска тестов: {e}")

def show_info():
    """Показ информации о приложении"""
    print("FastAPI Finance Monitor")
    print("=" * 30)
    print("Информационная панель для мониторинга финансовых активов в реальном времени")
    print()
    print("Возможности:")
    print("  • Обновления данных в реальном времени через WebSocket")
    print("  • Технические индикаторы (RSI, MACD, Полосы Боллинджера, и др.)")
    print("  • Персонализированные списки наблюдения")
    print("  • Интерактивные графики")
    print("  • Адаптивный интерфейс с темной темой")
    print()
    print("Использование:")
    print("  python run.py                # Показать эту справку")
    print("  python run.py start          # Запуск напрямую")
    print("  python run.py uvicorn        # Запуск с помощью Uvicorn")
    print("  python run.py docker         # Запуск с помощью Docker")
    print("  python run.py test           # Запуск базовых тестов")
    print("  python run.py info           # Показать эту информацию")
    print()

def main():
    """Основная точка входа"""
    parser = argparse.ArgumentParser(description="Запуск FastAPI Finance Monitor")
    parser.add_argument(
        "command", 
        nargs="?", 
        default="info",
        choices=["start", "uvicorn", "docker", "test", "info"],
        help="Команда для запуска"
    )
    
    args = parser.parse_args()
    
    if args.command == "start":
        run_direct()
    elif args.command == "uvicorn":
        run_uvicorn()
    elif args.command == "docker":
        run_docker()
    elif args.command == "test":
        test_application()
    else:
        show_info()

if __name__ == "__main__":
    main()