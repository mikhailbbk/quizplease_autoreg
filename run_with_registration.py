#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Запуск мониторинга с автоматической регистрацией и статистикой
"""
import sys
import os
import locale
import logging
import time
from typing import List, Dict
from datetime import datetime

# Устанавливаем кодировку UTF-8 глобально
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
else:
    import warnings

    warnings.filterwarnings('ignore')

# Устанавливаем локаль
try:
    locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Russian_Russia.65001')
    except:
        pass

# Добавляем src в путь
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Импортируем config для получения путей и настроек
try:
    import config
except ImportError:
    print("❌ ОШИБКА: Не удалось импортировать config.py")
    print("Убедитесь, что файл config.py существует в папке src/")
    sys.exit(1)

# Создаем необходимые директории из config
os.makedirs(config.LOGS_DIR, exist_ok=True)
os.makedirs(config.DATA_DIR, exist_ok=True)

# Импортируем модули
from extract_classic_games import QuizPleaseMonitor, load_configuration
from auto_register import QuizPleaseRegistrator, RegistrationData
from statistics import StatisticsManager

# Настройка логирования с использованием путей из config
LOG_FILE = os.path.join(config.LOGS_DIR, 'registration.log')

logging.basicConfig(
    level=getattr(logging, config.LOGGING_CONFIG.get('level', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Инициализируем менеджер статистики с использованием пути из config
stats_manager = StatisticsManager(
    stats_file=config.STATISTICS_CONFIG.get('stats_file')
)


def load_registration_data() -> RegistrationData:
    """Загружает данные для регистрации из config.py"""
    reg_data = config.REGISTRATION_DATA
    return RegistrationData(
        team_name=reg_data.get('team_name', 'Моя команда'),
        captain_name=reg_data.get('captain_name', 'Капитан'),
        email=reg_data.get('email', 'team@example.com'),
        phone=reg_data.get('phone', '+70000000000'),
        players_count=reg_data.get('players_count', 5),
        first_time=reg_data.get('first_time', True),
        comment=reg_data.get('comment', ''),
        has_promo=reg_data.get('has_promo', False),
        consent_data=reg_data.get('consent_data', True),
        consent_marketing=reg_data.get('consent_marketing', False)
    )


def process_new_games(new_games: List, monitor: QuizPleaseMonitor,
                      registration_data: RegistrationData) -> List[Dict]:
    """
    Обрабатывает новые игры: добавляет в статистику и регистрируется

    Returns:
        List[Dict]: Результаты регистрации
    """
    if not new_games:
        logger.info("🆕 Новых игр нет")
        return []

    logger.info(f"🆕 Обнаружено {len(new_games)} новых игр")

    # Добавляем игры в статистику
    for game in new_games:
        game_type = 'classic'
        if '[новички]' in game.title or 'ИЗИ' in game.title or 'Easy' in game.title:
            game_type = 'easy'

        stats_manager.add_game(
            game_id=game.id,
            title=game.title,
            game_number=game.game_number,
            date=game.date,
            time=game.time,
            game_type=game_type,
            registered=False
        )

    # Отправляем отчет о новых играх в Telegram
    if monitor.telegram and monitor.telegram.is_available:
        report = stats_manager.get_new_games_report(new_games)
        monitor.telegram.send_message(report)
        logger.info("📨 Отчет о новых играх отправлен в Telegram")

    # Регистрируемся на новые игры
    reg_settings = config.REGISTRATION_SETTINGS
    if reg_settings.get('auto_register', True):
        logger.info("🚀 Начинаю регистрацию на новые игры...")

        # Фильтруем только доступные игры
        available_games = [g for g in new_games if g.availability_type == 'active']

        if not available_games:
            logger.info("ℹ️ Нет доступных игр для регистрации")
            return []

        # Проверяем, не зарегистрированы ли уже эти игры
        registered_games = stats_manager.get_registered_games()
        registered_ids = [g.get('game_id') for g in registered_games]

        # Фильтруем только незарегистрированные игры
        games_to_register = []
        for game in available_games:
            if game.id in registered_ids:
                logger.info(f"⏭️ Игра {game.id} уже зарегистрирована, пропускаем")
            else:
                games_to_register.append(game)

        if not games_to_register:
            logger.info("ℹ️ Все доступные игры уже зарегистрированы")
            return []

        # Создаем регистратор
        registrator = QuizPleaseRegistrator(
            base_url=config.API_CONFIG.get('base_api_url', 'https://api.quizplease.ru'),
            site_url=config.API_CONFIG.get('site_url', 'https://klg.quizplease.ru')
        )

        # Получаем ID игр
        game_ids = [game.id for game in games_to_register]

        # Ограничиваем количество регистраций
        max_games = reg_settings.get('max_games_to_register', 20)
        if len(game_ids) > max_games:
            logger.info(f"⚠️ Ограничиваю регистрацию до {max_games} игр (найдено {len(game_ids)})")
            game_ids = game_ids[:max_games]

        results = []
        for game_id in game_ids:
            logger.info(f"📝 Регистрация на игру {game_id}...")
            result = registrator.register_to_game(game_id, registration_data)
            results.append(result)

            # Если регистрация успешна, обновляем статистику
            if result.get('success'):
                game = next((g for g in games_to_register if g.id == game_id), None)
                if game:
                    stats_manager.add_game(
                        game_id=game_id,
                        title=game.title,
                        game_number=game.game_number,
                        date=game.date,
                        time=game.time,
                        game_type='classic',
                        registered=True
                    )
                    logger.info(f"✅ Зарегистрирована игра: {game.title} {game.game_number}")
            else:
                logger.warning(
                    f"⚠️ Не удалось зарегистрироваться на игру {game_id}: {result.get('message', 'Неизвестная ошибка')}")

            # Задержка между регистрациями
            delay = reg_settings.get('delay_between_registrations', 2)
            if len(game_ids) > 1:
                time.sleep(delay)

        return results

    return []


def send_daily_statistics(monitor: QuizPleaseMonitor):
    """Отправляет ежедневную статистику"""
    if not monitor.telegram or not monitor.telegram.is_available:
        logger.warning("Telegram бот недоступен")
        return

    # Проверяем настройки отправки статистики
    if not config.NOTIFICATION_CONFIG.get('send_statistics', True):
        logger.info("ℹ️ Отправка статистики отключена в настройках")
        return

    # Получаем сообщение со статистикой
    message = stats_manager.get_summary_message()

    # Отправляем в Telegram
    try:
        monitor.telegram.send_message(message)
        logger.info("📊 Ежедневная статистика отправлена в Telegram")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки статистики: {e}")


def check_cookies_file():
    """Проверяет наличие файла cookies.json"""
    cookies_path = os.path.join(config.SRC_DIR, 'cookies.json')
    if not os.path.exists(cookies_path):
        logger.warning("⚠️ Файл cookies.json не найден!")
        logger.warning(f"   Ожидаемый путь: {cookies_path}")
        logger.warning("   Регистрация может не работать без этого файла")
        logger.warning("   Скопируйте cookies.json.template и заполните значениями")
        return False
    else:
        logger.info(f"✅ Файл cookies.json найден: {cookies_path}")
        return True


def main():
    """Основная функция запуска"""
    try:
        # Проверяем наличие config.py
        if not os.path.exists(os.path.join(config.SRC_DIR, 'config.py')):
            logger.error("❌ Файл config.py не найден в src/")
            logger.error("   Скопируйте config.example.py в config.py и настройте его")
            return 1

        # Проверяем наличие cookies.json
        check_cookies_file()

        # Загружаем конфигурацию
        telegram_config, parser_config = load_configuration()

        # Загружаем данные для регистрации
        registration_data = load_registration_data()

        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК МОНИТОРИНГА С АВТОРЕГИСТРАЦИЕЙ")
        logger.info("=" * 60)
        logger.info(f"📋 Команда: {registration_data.team_name}")
        logger.info(f"📧 Email: {registration_data.email}")
        logger.info(f"📱 Телефон: {registration_data.phone}")
        logger.info(f"👥 Количество игроков: {registration_data.players_count}")
        logger.info(f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        # Создаем монитор
        monitor = QuizPleaseMonitor(
            telegram_token=telegram_config['token'],
            telegram_chat_ids=telegram_config['chat_ids']
        )

        # Запускаем мониторинг
        logger.info("📡 Запуск мониторинга...")
        games = monitor.run(send_notifications=False)  # Отключаем стандартные уведомления

        if not games:
            logger.warning("❌ Игры не найдены")
            return 0

        logger.info(f"🎯 Найдено {len(games)} игр")

        # Проверяем новые игры
        previous_games = monitor.storage.load_games()
        new_games = monitor.storage.find_new_games(games, previous_games)

        # Обрабатываем новые игры
        if new_games:
            logger.info(f"🆕 Обнаружено {len(new_games)} новых игр")
            results = process_new_games(new_games, monitor, registration_data)

            # Отправляем отчет о регистрации
            if results and monitor.telegram and monitor.telegram.is_available:
                registrator = QuizPleaseRegistrator()
                report = registrator.get_registration_report(results)
                monitor.telegram.send_message(report)
                logger.info("📨 Отчет о регистрации отправлен в Telegram")
        else:
            logger.info("🆕 Новых игр нет")

        # Отправляем ежедневную статистику
        send_daily_statistics(monitor)

        logger.info("=" * 60)
        logger.info("✅ Скрипт завершен успешно!")
        logger.info("=" * 60)
        return 0

    except KeyboardInterrupt:
        print("\n⏹️ Программа прервана пользователем")
        logger.info("Программа прервана пользователем")
        return 130
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {str(e)}", exc_info=True)
        print(f"\n❌ Критическая ошибка: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)