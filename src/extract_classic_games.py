import os
import sys
import json
import logging
import requests
import re
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
import hashlib

# Добавляем src в sys.path для импорта модулей
SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Импортируем config для получения путей и настроек
try:
    import config
except ImportError:
    print("❌ ОШИБКА: Не удалось импортировать config.py")
    print("Убедитесь, что файл config.py существует в папке src/")
    sys.exit(1)

# Используем пути из config.py
DATA_DIR = config.DATA_DIR
LOGS_DIR = config.LOGS_DIR

# Создание директорий, если они не существуют
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Настройка логирования
LOG_FILE = os.path.join(LOGS_DIR, 'extract_games.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_configuration():
    """Загружает конфигурацию из config.py"""
    try:
        # Проверяем наличие обязательных полей
        required_fields = ['TELEGRAM_CONFIG', 'PARSER_CONFIG']
        for field in required_fields:
            if not hasattr(config, field):
                raise AttributeError(f"В config.py отсутствует обязательный параметр: {field}")

        telegram_config = config.TELEGRAM_CONFIG
        if 'token' not in telegram_config or not telegram_config['token']:
            raise ValueError("Токен Telegram не указан в config.py")

        if 'chat_ids' not in telegram_config or not telegram_config['chat_ids']:
            raise ValueError("Chat IDs не указаны в config.py")

        parser_config = config.PARSER_CONFIG

        logger.info("✓ Конфигурация успешно загружена из config.py")

        token = telegram_config['token']
        masked_token = f"{token[:10]}...{token[-5:]}" if len(token) > 15 else "***"
        logger.info(f"  Telegram токен: {masked_token}")
        logger.info(f"  Chat IDs: {telegram_config['chat_ids']}")
        logger.info(f"  Базовый URL: {parser_config['base_url']}")

        return telegram_config, parser_config

    except ImportError:
        logger.error("❌ ФАЙЛ config.py НЕ НАЙДЕН!")
        print_error_and_exit()
    except AttributeError as e:
        logger.error(f"❌ ОШИБКА В СТРУКТУРЕ config.py: {e}")
        print_error_and_exit()
    except ValueError as e:
        logger.error(f"❌ ОШИБКА В ДАННЫХ config.py: {e}")
        print_error_and_exit()
    except Exception as e:
        logger.error(f"❌ НЕОЖИДАННАЯ ОШИБКА ПРИ ЗАГРУЗКЕ КОНФИГУРАЦИИ: {e}")
        print_error_and_exit()


def print_error_and_exit():
    """Выводит сообщение об ошибке и завершает работу"""
    print("\n" + "=" * 60)
    print("❌ ОШИБКА КОНФИГУРАЦИИ!")
    print("=" * 60)
    print("📋 Для решения проблемы выполните следующие шаги:")
    print()
    print("1. Если файла config.py нет:")
    print("   а) Скопируйте шаблон:")
    print("      cp src/config.example.py src/config.py")
    print("   б) Или создайте вручную в папке src/ файл config.py")
    print()
    print("2. Отредактируйте файл config.py:")
    print("   а) Получите токен бота у @BotFather в Telegram")
    print("   б) Замените ВАШ_ТОКЕН_БОТА_ЗДЕСЬ на ваш токен")
    print("   в) Получите Chat ID:")
    print("      python src/get_chat_id.py")
    print("   г) Замените ВАШ_CHAT_ID_ЗДЕСЬ на ваш Chat ID")
    print()
    print("3. Пример содержимого config.py:")
    print("   TELEGRAM_CONFIG = {")
    print("       'token': '1234567890:ABCdefGHIjklMNOpqrSTUvwx',")
    print("       'chat_ids': ['987654321']")
    print("   }")
    print("   PARSER_CONFIG = {")
    print("       'base_url': 'https://klg.quizplease.ru/schedule'")
    print("   }")
    print()
    print("4. Убедитесь, что config.py находится в папке src/")
    print("5. Запустите скрипт снова")
    print("=" * 60)
    sys.exit(1)


# Загружаем конфигурацию
TELEGRAM_CONFIG, PARSER_CONFIG = load_configuration()


@dataclass
class Game:
    """Класс для хранения данных об игре"""
    id: str
    title: str
    game_number: str
    date: str
    time: str
    place: str
    address: str
    price: str
    status: str
    button_text: str
    availability_type: str
    registration_url: str
    extracted_at: str
    is_available: bool = False
    game_hash: str = field(default="")

    def __post_init__(self):
        if not self.game_hash:
            self.game_hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Вычисляет хеш игры для отслеживания изменений"""
        data_string = f"{self.title}{self.game_number}{self.date}{self.time}{self.place}{self.status}{self.availability_type}"
        return hashlib.md5(data_string.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict:
        """Преобразует объект в словарь"""
        return asdict(self)

    def to_telegram_message(self) -> str:
        """
        Формирует сообщение для отправки в Telegram.
        Ссылка отображается полным URL текстом, чтобы сохранялась при копировании.
        """
        if self.availability_type == 'reserve':
            emoji = "⚠️"
            availability_text = "ЗАПИСЬ В РЕЗЕРВ"
        elif self.availability_type == 'active':
            emoji = "✅"
            availability_text = "СВОБОДНЫЕ МЕСТА"
        else:
            emoji = "❓"
            availability_text = "СТАТУС НЕИЗВЕСТЕН"

        price_display = self._clean_price(self.price) if self.price else 'Не указана'
        status_display = self.status if self.status else self.button_text

        message = (
            f"{emoji} *{availability_text}*\n"
            f"🎯 *{self.title} {self.game_number}*\n"
            f"📅 *Дата:* {self.date}\n"
            f"🕒 *Время:* {self.time if self.time else 'Не указано'}\n"
            f"📍 *Место:* {self.place if self.place else 'Не указано'}\n"
            f"🏠 *Адрес:* {self.address if self.address else 'Не указан'}\n"
            f"💰 *Цена:* {price_display}\n"
            f"📊 *Статус:* {status_display}\n"
            f"🕐 *Обновлено:* {self.extracted_at}"
        )

        # ✅ Ссылка отображается полным URL как текст, чтобы сохранялась при копировании
        if self.registration_url and self.registration_url != "#":
            message += f"\n\n👉 Ссылка для регистрации: {self.registration_url}"

        return message

    def _clean_price(self, price: str) -> str:
        """Очищает строку с ценой от лишних символов"""
        if not price:
            return ""
        price = re.sub(r'\s+', ' ', price.strip())
        price = re.sub(r'\s{2,}', ' ', price)
        price = price.replace('\n', ' ').replace('\r', ' ').replace('/', ' / ')
        price = re.sub(r'\s*/\s*', ' / ', price)
        return price


class QuizPleaseApiParser:
    """Парсер API QuizPlease"""

    def __init__(self, base_url: str = None):
        self.api_url = "https://api.quizplease.ru/api/games/schedule/32"
        self.session = requests.Session()
        self._setup_session()

        # Ключевые слова для определения типа игры
        self.game_type_keywords = {
            'classic': ['Квиз, плиз!', 'Квиз, плиз! KLG'],
            'easy': ['[новички]', 'ИЗИ', 'Easy', 'новичк'],
        }

    def _setup_session(self) -> None:
        """Настраивает HTTP сессию"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Referer': 'https://klg.quizplease.ru/',
        })

    def _determine_availability_type(self, status: int, few_places_left: bool) -> Tuple[str, bool]:
        """Определяет тип доступности игры"""
        if status == 0 or status == 1:
            return 'active', True
        else:
            return 'reserve', False

    def _extract_game_number(self, game_number_raw, package_number) -> str:
        """Извлекает номер игры"""
        if game_number_raw:
            return f"#{game_number_raw}"
        if package_number:
            if isinstance(package_number, str):
                return package_number
            return str(package_number)
        return "Без номера"

    def _extract_time_from_datetime(self, datetime_str: str) -> str:
        """Извлекает время из строки даты-времени"""
        if not datetime_str:
            return ""
        try:
            parts = datetime_str.split()
            if len(parts) > 1:
                return parts[1]
            return ""
        except Exception:
            return ""

    def _get_game_type(self, title: str) -> str:
        """
        Определяет тип игры по заголовку.
        Возвращает: 'classic', 'easy' или 'other'
        """
        title_lower = title.lower()

        for game_type, keywords in self.game_type_keywords.items():
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    return game_type

        return 'other'

    def parse_games(self, game_types: List[str] = None) -> List[Game]:
        """
        Парсит игры с фильтрацией по типу.

        Args:
            game_types: Список типов игр для фильтрации.
                        Например: ['classic', 'easy'] - только классические и ИЗИ
                                  ['classic'] - только классические
                                  None или [] - все игры
        """
        try:
            params = {
                'per_page': 50,
                'order': 'date',
                'statuses[]': [0, 1, 2, 3, 5]
            }

            logger.info(f"Запрашиваем данные через API: {self.api_url}")

            response = self.session.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data.get('status') != 'ok':
                logger.error(f"API вернул ошибку: {data}")
                return []

            games_data = data.get('data', {}).get('data', [])
            logger.info(f"Получено {len(games_data)} игр от API")

            games = []
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            for game_info in games_data:
                try:
                    title = game_info.get('title', '')

                    # Определяем тип игры
                    game_type = self._get_game_type(title)

                    # Фильтрация по типам игр
                    if game_types and game_type not in game_types:
                        logger.debug(f"Игра пропущена (тип {game_type} не в {game_types}): {title}")
                        continue

                    # Если тип 'other' и есть фильтрация - пропускаем
                    if game_types and game_type == 'other':
                        logger.debug(f"Игра пропущена (other): {title}")
                        continue

                    status_code = game_info.get('status', 0)
                    few_places = game_info.get('few_places_left', False)
                    availability_type, is_available = self._determine_availability_type(status_code, few_places)

                    game_number = self._extract_game_number(
                        game_info.get('game_number'),
                        game_info.get('package_number')
                    )

                    datetime_full = game_info.get('date', '')
                    date_text = datetime_full.split()[0] if datetime_full else ''
                    time_text = self._extract_time_from_datetime(datetime_full)

                    place_info = game_info.get('place', {})
                    place_title = place_info.get('title', 'Не указано')
                    place_address = place_info.get('address', 'Не указан')

                    price = game_info.get('current_price', '')
                    price_str = f"{price} ₽" if price else 'Не указана'

                    if status_code == 0:
                        status_text = "✅ Места есть"
                    elif status_code == 1:
                        status_text = "⚠️ Осталось мало мест"
                    else:
                        status_text = "📋 Запись в резерв"

                    game_id = game_info.get('id', '')
                    registration_url = f"https://klg.quizplease.ru/game/{game_id}" if game_id else "#"

                    game = Game(
                        id=game_id,
                        title=title,
                        game_number=game_number,
                        date=date_text,
                        time=time_text,
                        place=place_title,
                        address=place_address,
                        price=price_str,
                        status=status_text,
                        button_text="",
                        availability_type=availability_type,
                        registration_url=registration_url,
                        extracted_at=current_time,
                        is_available=is_available
                    )

                    games.append(game)
                    logger.debug(f"Добавлена игра: {title} (тип: {game_type})")

                except Exception as e:
                    logger.error(f"Ошибка при обработке игры: {str(e)}")
                    continue

            logger.info(f"Успешно обработано {len(games)} игр (фильтр: {game_types})")
            return games

        except requests.RequestException as e:
            logger.error(f"Ошибка сети при запросе к API: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге: {str(e)}", exc_info=True)
            return []


class GameStorage:
    """Класс для хранения и загрузки данных об играх"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or DATA_DIR
        self.history_file = os.path.join(self.output_dir, 'games_history.json')

    def save_games(self, games: List[Game], filename: str = "classic_games.json") -> str:
        """Сохраняет игры в JSON файл"""
        try:
            output_path = os.path.join(self.output_dir, filename)
            games_data = [game.to_dict() for game in games]
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(games_data, f, ensure_ascii=False, indent=2)
            self._save_to_history(games)
            logger.info(f"Сохранено {len(games)} игр в {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Ошибка при сохранении игр: {str(e)}")
            return ""

    def _save_to_history(self, games: List[Game]) -> None:
        """Сохраняет игры в историю"""
        try:
            history = []
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)

            timestamp = datetime.now().isoformat()
            for game in games:
                game_data = game.to_dict()
                game_data['timestamp'] = timestamp
                game_data['parsed_at'] = game.extracted_at
                history.append(game_data)

            if len(history) > 1000:
                history = history[-1000:]

            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"Не удалось сохранить историю: {str(e)}")

    def load_games(self, filename: str = "classic_games.json") -> List[Game]:
        """Загружает игры из JSON файла"""
        try:
            filepath = os.path.join(self.output_dir, filename)
            if not os.path.exists(filepath):
                logger.info(f"Файл {filepath} не найден, возвращаем пустой список")
                return []

            with open(filepath, 'r', encoding='utf-8') as f:
                games_data = json.load(f)

            games = []
            for game_data in games_data:
                try:
                    game = Game(**game_data)
                    games.append(game)
                except Exception as e:
                    logger.warning(f"Ошибка при создании игры из данных: {str(e)}")
                    continue

            logger.info(f"Загружено {len(games)} игр из {filepath}")
            return games
        except Exception as e:
            logger.error(f"Ошибка при загрузке игр: {str(e)}")
            return []

    def find_new_games(self, current_games: List[Game], previous_games: List[Game]) -> List[Game]:
        """Находит новые игры, которых не было в предыдущем списке"""
        if not previous_games:
            return current_games
        previous_ids = {game.id for game in previous_games}
        new_games = [game for game in current_games if game.id not in previous_ids]
        if new_games:
            logger.info(f"Найдено {len(new_games)} НОВЫХ игр")
        else:
            logger.info("Новых игр не найдено")
        return new_games

    def find_changed_games(self, current_games: List[Game], previous_games: List[Game]) -> List[Game]:
        """Находит игры с измененным статусом"""
        if not previous_games:
            return []
        previous_dict = {game.id: game for game in previous_games}
        changed_games = []
        for current_game in current_games:
            previous_game = previous_dict.get(current_game.id)
            if previous_game and previous_game.availability_type != current_game.availability_type:
                changed_games.append(current_game)
        if changed_games:
            logger.info(f"Найдено {len(changed_games)} игр с ИЗМЕНЕННЫМ статусом")
        else:
            logger.info("Игр с измененным статусом не найдено")
        return changed_games


class QuizPleaseMonitor:
    """Класс для мониторинга игр QuizPlease"""

    def __init__(self, telegram_token: str = None, telegram_chat_ids=None, game_types: List[str] = None):
        self.parser = QuizPleaseApiParser()
        self.storage = GameStorage()
        self.telegram = None
        self.game_types = game_types or ['classic', 'easy']  # По умолчанию классические и ИЗИ

        if telegram_token and telegram_chat_ids:
            try:
                from telegram_notifier import TelegramBot
                self.telegram = TelegramBot(telegram_token, telegram_chat_ids)
                if not self.telegram.is_available:
                    logger.warning("Telegram бот недоступен, уведомления отключены")
                    self.telegram = None
            except ImportError as e:
                logger.warning(f"Модуль telegram_notifier не найден: {e}")
                self.telegram = None
            except Exception as e:
                logger.error(f"Ошибка инициализации Telegram бота: {str(e)}")
                self.telegram = None

    def run(self, send_notifications: bool = True) -> List[Game]:
        """Запускает мониторинг"""
        try:
            logger.info("=" * 60)
            logger.info(f"Запуск мониторинга игр 'Квиз, плиз! KLG' (типы: {self.game_types})")
            logger.info("=" * 60)

            previous_games = self.storage.load_games()
            current_games = self.parser.parse_games(game_types=self.game_types)

            if not current_games:
                logger.warning("Не удалось получить игры через API")
                if self.telegram and send_notifications:
                    self.telegram.send_message("❌ Не удалось получить расписание игр через API.")
                return []

            self.storage.save_games(current_games)
            new_games = self.storage.find_new_games(current_games, previous_games)
            changed_games = self.storage.find_changed_games(current_games, previous_games)

            if self.telegram and send_notifications:
                self._send_change_notifications(new_games, changed_games)

            self._print_statistics(current_games, new_games, changed_games)
            return current_games

        except KeyboardInterrupt:
            logger.info("\nМониторинг прерван пользователем")
            return []
        except Exception as e:
            logger.error(f"Критическая ошибка в мониторинге: {str(e)}", exc_info=True)
            return []

    def _send_change_notifications(self, new_games: List[Game], changed_games: List[Game]) -> None:
        """Отправляет уведомления об изменениях"""
        try:
            if not self.telegram:
                logger.warning("Telegram бот не инициализирован")
                return

            if new_games or changed_games:
                check_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.telegram.send_message(f"🔄 *Проверка расписания*\n🕐 Время: {check_time}")

            if new_games:
                if len(new_games) == 1:
                    self.telegram.send_message(f"🎉 *НОВАЯ ИГРА!*")
                else:
                    self.telegram.send_message(f"🎉 *НОВЫЕ ИГРЫ!* ({len(new_games)})")

                for game in new_games:
                    self.telegram.send_game_notification(game)
                    time.sleep(0.5)

            if changed_games:
                if len(changed_games) == 1:
                    self.telegram.send_message(f"🔄 *ИЗМЕНИЛСЯ СТАТУС ИГРЫ!*")
                else:
                    self.telegram.send_message(f"🔄 *ИЗМЕНИЛСЯ СТАТУС ИГР!* ({len(changed_games)})")

                for game in changed_games:
                    self.telegram.send_game_notification(game)
                    time.sleep(0.5)

            if not new_games and not changed_games:
                logger.info("Нет изменений — уведомления не отправлены")

        except Exception as e:
            logger.error(f"Ошибка при отправке уведомлений: {str(e)}")

    def _print_statistics(self, current_games: List[Game],
                          new_games: List[Game],
                          changed_games: List[Game]) -> None:
        """Выводит статистику мониторинга"""
        active_games = [g for g in current_games if g.availability_type == 'active']
        reserve_games = [g for g in current_games if g.availability_type == 'reserve']

        logger.info("\n" + "=" * 50)
        logger.info("СТАТИСТИКА МОНИТОРИНГА:")
        logger.info("=" * 50)
        logger.info(f"Всего игр: {len(current_games)}")
        logger.info(f"✅ Доступные для записи: {len(active_games)}")
        logger.info(f"⚠️  Запись в резерв: {len(reserve_games)}")
        logger.info(f"🎉 НОВЫЕ игры: {len(new_games)}")
        logger.info(f"🔄 Игры с ИЗМЕНЕННЫМ статусом: {len(changed_games)}")

        print(f"\n🎯 Найдено {len(current_games)} игр 'Квиз, плиз! KLG'")
        print(f"   ✅ Доступных для записи: {len(active_games)}")
        print(f"   ⚠️  Для записи в резерв: {len(reserve_games)}")

        if new_games:
            print(f"   🎉 НОВЫЕ игры: {len(new_games)}")
        if changed_games:
            print(f"   🔄 Изменения статуса: {len(changed_games)}")

        print(f"\n📁 Данные сохранены в: {os.path.join(DATA_DIR, 'classic_games.json')}")
        print(f"📝 Логи сохранены в: {LOG_FILE}")

        logger.info("=" * 50)
        logger.info("Мониторинг завершён успешно!")
        logger.info("=" * 50)


def main():
    """Основная функция"""
    try:
        # Типы игр для мониторинга
        # ['classic'] - только классические
        # ['easy'] - только ИЗИ
        # ['classic', 'easy'] - и классические, и ИЗИ
        # [] или None - все игры
        GAME_TYPES = ['classic', 'easy']  # ← настройка здесь

        monitor = QuizPleaseMonitor(
            telegram_token=TELEGRAM_CONFIG['token'],
            telegram_chat_ids=TELEGRAM_CONFIG['chat_ids'],
            game_types=GAME_TYPES
        )

        games = monitor.run(send_notifications=True)

        if games is not None:
            print(f"\n{'=' * 50}")
            print("✨ Мониторинг завершён успешно!")
            print(f"{'=' * 50}")
            return 0
        else:
            print(f"\n{'=' * 50}")
            print("❌ Мониторинг завершён с ошибками")
            print("Проверьте логи для подробной информации")
            print(f"{'=' * 50}")
            return 1

    except KeyboardInterrupt:
        print(f"\n\n{'=' * 50}")
        print("⏹️  Мониторинг прерван пользователем")
        print(f"{'=' * 50}")
        return 130
    except Exception as e:
        print(f"\n{'=' * 50}")
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print(f"{'=' * 50}")
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)