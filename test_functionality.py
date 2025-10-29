#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности FastAPI Finance Monitor
"""

import requests
import time
import sys
import os

# Добавление директории app в путь
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_health_check():
    """Тестирование эндпоинта проверки состояния"""
    try:
        response = requests.get('http://localhost:8000/api/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Проверка состояния: {data['message']}")
            return True
        else:
            print(f"✗ Проверка состояния не удалась со статусом {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Проверка состояния не удалась: {e}")
        return False

def test_watchlist():
    """Тестирование эндпоинтов списка наблюдения"""
    try:
        # Получение текущего списка наблюдения
        response = requests.get('http://localhost:8000/api/watchlist', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Получение списка наблюдения: {len(data['watchlist'])} активов")
            
            # Попытка добавить актив
            add_response = requests.post(
                'http://localhost:8000/api/watchlist/add',
                params={'symbol': 'NVDA'},
                timeout=5
            )
            if add_response.status_code == 200:
                print("✓ Актив добавлен в список наблюдения")
                
                # Проверка добавления
                verify_response = requests.get('http://localhost:8000/api/watchlist', timeout=5)
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    if 'NVDA' in verify_data['watchlist']:
                        print("✓ Проверка актива успешна")
                        return True
                    else:
                        print("✗ Актив не найден в списке наблюдения после добавления")
                        return False
                else:
                    print("✗ Не удалось проверить список наблюдения после добавления")
                    return False
            else:
                print("✗ Не удалось добавить актив в список наблюдения")
                return False
        else:
            print(f"✗ Получение списка наблюдения не удалось со статусом {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Тест списка наблюдения не удался: {e}")
        return False

def test_search():
    """Тестирование эндпоинта поиска"""
    try:
        response = requests.get(
            'http://localhost:8000/api/search',
            params={'query': 'Apple'},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Функция поиска: Найдено {len(data['results'])} результатов")
            return True
        else:
            print(f"✗ Поиск не удался со статусом {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Тест поиска не удался: {e}")
        return False

def main():
    """Основная тестовая функция"""
    print("Тестирование функциональности FastAPI Finance Monitor...")
    print("=" * 50)
    
    # Ожидание полного запуска сервера
    time.sleep(2)
    
    tests = [
        test_health_check,
        test_watchlist,
        test_search
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Результаты тестов: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены! Приложение работает корректно.")
        return 0
    else:
        print("❌ Некоторые тесты не пройдены. Пожалуйста, проверьте приложение.")
        return 1

if __name__ == "__main__":
    sys.exit(main())