#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки регистрации на игру
"""
import sys
import os
import json
from datetime import datetime

# Добавляем src в путь (абсолютный путь для надежности)
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Импортируем config для получения данных
try:
    import config

    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    print("⚠️ ВНИМАНИЕ: config.py не найден, использую значения по умолчанию")

from auto_register import QuizPleaseRegistrator, RegistrationData


def get_test_game_id(registrator) -> str:
    """
    Получает ID первой доступной игры для теста.
    Если не удается, возвращает фиксированный ID.
    """
    try:
        # Пробуем получить список игр через API
        import requests
        api_url = "https://api.quizplease.ru/api/games/schedule/32"
        params = {
            'per_page': 10,
            'order': 'date',
            'statuses[]': [0, 1]  # Только доступные игры
        }

        response = requests.get(api_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            games = data.get('data', {}).get('data', [])
            if games:
                # Берем первую игру с активным статусом
                for game in games:
                    if game.get('status') in [0, 1]:  # 0 - есть места, 1 - мало мест
                        game_id = game.get('id')
                        if game_id:
                            print(f"🎯 Найдена тестовая игра: {game.get('title')} (ID: {game_id})")
                            return game_id
    except Exception as e:
        print(f"⚠️ Не удалось получить список игр: {e}")

    # Запасной вариант - фиксированный ID (обновите на актуальный)
    fallback_id = '019e8319-1956-7077-af45-9284838d8267'
    print(f"⚠️ Использую фиксированный ID игры: {fallback_id}")
    return fallback_id


def load_test_data():
    """Загружает данные для теста из config.py или использует значения по умолчанию"""
    if USE_CONFIG and hasattr(config, 'REGISTRATION_DATA'):
        reg_data = config.REGISTRATION_DATA
        return {
            'team_name': reg_data.get('team_name', 'Тестовая команда'),
            'captain_name': reg_data.get('captain_name', 'Тестовый капитан'),
            'email': reg_data.get('email', 'test@example.com'),
            'phone': reg_data.get('phone', '+70000000000'),
            'players_count': reg_data.get('players_count', 4),
            'first_time': reg_data.get('first_time', False)
        }

    # Значения по умолчанию
    return {
        'team_name': 'Тестовая команда',
        'captain_name': 'Тестовый капитан',
        'email': 'test@example.com',
        'phone': '+70000000000',
        'players_count': 4,
        'first_time': False
    }


def main():
    """Основная функция теста"""
    print("=" * 60)
    print("🧪 ТЕСТ РЕГИСТРАЦИИ НА ИГРУ")
    print("=" * 60)
    print()

    # Загружаем тестовые данные
    test_data = load_test_data()

    # Создаем уникальное имя команды с временной меткой
    unique_name = f'{test_data["team_name"]} {datetime.now().strftime("%H%M%S")}'
    print(f'📋 Тестовая команда: {unique_name}')
    print()

    # Данные для регистрации
    reg_data = RegistrationData(
        team_name=unique_name,
        captain_name=test_data['captain_name'],
        email=test_data['email'],
        phone=test_data['phone'],
        players_count=test_data['players_count'],
        first_time=test_data['first_time']
    )

    # Создаем регистратор
    print('🔄 Инициализация регистратора...')

    # Используем настройки из config если доступны
    if USE_CONFIG and hasattr(config, 'API_CONFIG'):
        registrator = QuizPleaseRegistrator(
            base_url=config.API_CONFIG.get('base_api_url', 'https://api.quizplease.ru'),
            site_url=config.API_CONFIG.get('site_url', 'https://klg.quizplease.ru')
        )
    else:
        registrator = QuizPleaseRegistrator()

    print('🔄 Подготовка сессии...')

    # Получаем ID игры для теста
    game_id = get_test_game_id(registrator)
    print(f'🎯 ID игры: {game_id}')
    print()

    # Пробуем зарегистрироваться
    print('📝 Отправка запроса на регистрацию...')
    result = registrator.register_to_game(game_id, reg_data)

    print()
    print('=' * 60)
    print('📊 РЕЗУЛЬТАТ ТЕСТА:')
    print('=' * 60)
    print(f'✅ Успех: {result.get("success")}')
    print(f'📝 Сообщение: {result.get("message")}')

    if result.get('success'):
        print('🎉 РЕГИСТРАЦИЯ УСПЕШНА!')
        print()
        print('📋 Детали ответа:')
        print(json.dumps(result.get('response', {}), ensure_ascii=False, indent=2))
    else:
        print('❌ РЕГИСТРАЦИЯ НЕ УДАЛАСЬ')
        if 'error' in result:
            print(f'Ошибка: {result.get("error")}')
        if 'response' in result:
            print(f'Ответ сервера: {result.get("response")}')

    print()
    print('=' * 60)
    print('💡 СОВЕТЫ:')
    print('=' * 60)
    print('1. Убедитесь, что файл src/cookies.json существует и содержит актуальные куки')
    print('2. Проверьте, что игра с указанным ID доступна для регистрации')
    print('3. Проверьте настройки в src/config.py')
    print('4. Убедитесь, что команда не зарегистрирована на эту игру ранее')
    print('=' * 60)

    return 0 if result.get('success') else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Тест прерван пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)