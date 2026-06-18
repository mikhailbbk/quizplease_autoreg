"""
Модуль для сбора и отправки статистики по играм
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

# Импортируем config для получения путей
try:
    import config
except ImportError:
    # Если config не найден, используем локальные пути как запасной вариант
    config = None
    print("⚠️ ВНИМАНИЕ: config.py не найден, использую локальные пути")

logger = logging.getLogger(__name__)


@dataclass
class GameStats:
    """Статистика по одной игре"""
    game_id: str
    title: str
    game_number: str
    date: str
    time: str
    game_type: str  # classic, easy
    discovered_at: str  # когда обнаружена
    registered: bool = False
    registered_at: Optional[str] = None
    times_seen: int = 1
    first_seen: Optional[str] = None


@dataclass
class DailyStats:
    """Статистика за день"""
    date: str
    day_of_week: str
    games_found: int
    games_registered: int
    games_details: List[GameStats]
    new_games_today: int
    total_games: int


class StatisticsManager:
    """Менеджер статистики"""

    def __init__(self, stats_file: str = None):
        """
        Инициализация менеджера статистики

        Args:
            stats_file: Путь к файлу статистики. Если не указан, берется из config
        """
        # Определяем путь к файлу статистики
        if stats_file is None:
            if config and hasattr(config, 'STATISTICS_CONFIG'):
                stats_file = config.STATISTICS_CONFIG.get('stats_file')
                if stats_file is None:
                    # Если в конфиге нет, используем путь по умолчанию
                    if config and hasattr(config, 'DATA_DIR'):
                        stats_file = os.path.join(config.DATA_DIR, 'game_stats.json')
                    else:
                        stats_file = 'game_stats.json'
            else:
                stats_file = 'game_stats.json'

        self.stats_file = stats_file
        self.stats: Dict[str, Dict] = {}

        # Создаем директорию для файла статистики, если её нет
        stats_dir = os.path.dirname(self.stats_file)
        if stats_dir:
            os.makedirs(stats_dir, exist_ok=True)

        self.load_stats()

    def _get_registered_games_file(self) -> str:
        """Возвращает путь к файлу с зарегистрированными играми"""
        if config and hasattr(config, 'STATISTICS_CONFIG'):
            registered_file = config.STATISTICS_CONFIG.get('registered_games_file')
            if registered_file:
                return registered_file

        # Запасной вариант
        if config and hasattr(config, 'DATA_DIR'):
            return os.path.join(config.DATA_DIR, 'registered_games.json')
        return 'registered_games.json'

    def load_stats(self):
        """Загружает статистику из файла"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
                logger.info(f"✅ Загружена статистика: {len(self.stats)} записей")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки статистики: {e}")
                self.stats = {}
        else:
            self.stats = {}
            logger.info("ℹ️ Файл статистики не найден, создан новый")

    def save_stats(self):
        """Сохраняет статистику в файл"""
        try:
            # Создаем директорию если её нет
            stats_dir = os.path.dirname(self.stats_file)
            if stats_dir:
                os.makedirs(stats_dir, exist_ok=True)

            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
            logger.info("✅ Статистика сохранена")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения статистики: {e}")

    def add_game(self, game_id: str, title: str, game_number: str,
                 date: str, time: str, game_type: str, registered: bool = False):
        """Добавляет игру в статистику"""
        game_key = game_id

        if game_key not in self.stats:
            self.stats[game_key] = {
                'game_id': game_id,
                'title': title,
                'game_number': game_number,
                'date': date,
                'time': time,
                'game_type': game_type,
                'discovered_at': datetime.now().isoformat(),
                'registered': registered,
                'registered_at': datetime.now().isoformat() if registered else None,
                'first_seen': datetime.now().isoformat(),
                'times_seen': 1
            }
        else:
            self.stats[game_key]['times_seen'] = self.stats[game_key].get('times_seen', 0) + 1
            if registered and not self.stats[game_key].get('registered'):
                self.stats[game_key]['registered'] = True
                self.stats[game_key]['registered_at'] = datetime.now().isoformat()

        self.save_stats()

        # Сохраняем в отдельный файл зарегистрированных игр
        if registered:
            self._save_registered_game(game_id, title, game_number, date, time, game_type)

    def _save_registered_game(self, game_id: str, title: str, game_number: str,
                              date: str, time: str, game_type: str):
        """Сохраняет информацию о зарегистрированной игре в отдельный файл"""
        try:
            registered_file = self._get_registered_games_file()
            registered_dir = os.path.dirname(registered_file)
            if registered_dir:
                os.makedirs(registered_dir, exist_ok=True)

            # Загружаем существующие записи
            if os.path.exists(registered_file):
                with open(registered_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'games': [], 'updated_at': ''}

            # Проверяем, не зарегистрирована ли уже эта игра
            existing_ids = [g.get('game_id') for g in data.get('games', [])]
            if game_id not in existing_ids:
                data['games'].append({
                    'game_id': game_id,
                    'title': title,
                    'game_number': game_number,
                    'date': date,
                    'time': time,
                    'game_type': game_type,
                    'registered_at': datetime.now().isoformat()
                })
                data['updated_at'] = datetime.now().isoformat()

                with open(registered_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ Зарегистрированная игра добавлена в {registered_file}")

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения зарегистрированной игры: {e}")

    def get_today_stats(self) -> DailyStats:
        """Получает статистику за сегодня"""
        today = datetime.now().strftime('%Y-%m-%d')
        day_of_week = self._get_day_of_week(datetime.now().weekday())

        today_games = []
        for game_id, data in self.stats.items():
            game_date = data.get('date', '')
            if game_date == today:
                today_games.append(GameStats(**data))

        # Сортируем по времени обнаружения
        today_games.sort(key=lambda x: x.discovered_at if x.discovered_at else '')

        # Определяем новые игры сегодня
        new_games_today = 0
        for game in today_games:
            if game.discovered_at:
                discovered_time = datetime.fromisoformat(game.discovered_at)
                if discovered_time.date() == datetime.now().date():
                    new_games_today += 1

        return DailyStats(
            date=today,
            day_of_week=day_of_week,
            games_found=len(today_games),
            games_registered=sum(1 for g in today_games if g.registered),
            games_details=today_games,
            new_games_today=new_games_today,
            total_games=len(self.stats)
        )

    def get_weekly_stats(self) -> Dict[str, DailyStats]:
        """Получает статистику за последние 7 дней"""
        weekly_stats = {}
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            day_stats = self._get_stats_for_date(date)
            if day_stats:
                weekly_stats[date] = day_stats
        return weekly_stats

    def _get_stats_for_date(self, date_str: str) -> Optional[DailyStats]:
        """Получает статистику за конкретную дату"""
        games = []
        for game_id, data in self.stats.items():
            if data.get('date') == date_str:
                games.append(GameStats(**data))

        if not games:
            return None

        date_obj = datetime.strptime(date_str, '%Y-%m-%d')

        return DailyStats(
            date=date_str,
            day_of_week=self._get_day_of_week(date_obj.weekday()),
            games_found=len(games),
            games_registered=sum(1 for g in games if g.registered),
            games_details=games,
            new_games_today=0,
            total_games=len(self.stats)
        )

    def _get_day_of_week(self, weekday: int) -> str:
        """Возвращает название дня недели"""
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        return days[weekday]

    def get_summary_message(self) -> str:
        """Формирует сообщение со сводкой статистики"""
        today_stats = self.get_today_stats()
        weekly_stats = self.get_weekly_stats()

        lines = [
            "📊 *СТАТИСТИКА ИГР QUIZPLEASE*",
            "",
            f"📅 *Сегодня:* {today_stats.date} ({today_stats.day_of_week})",
            f"🎯 *Найдено игр:* {today_stats.games_found}",
            f"✅ *Зарегистрировано:* {today_stats.games_registered}",
            f"🆕 *Новых игр:* {today_stats.new_games_today}",
            f"📚 *Всего в базе:* {today_stats.total_games}",
            ""
        ]

        # Добавляем время обнаружения новых игр
        if today_stats.games_details:
            lines.append("*🎮 Игры сегодня:*")
            for game in today_stats.games_details[:5]:  # Показываем первые 5
                discovered = datetime.fromisoformat(game.discovered_at).strftime('%H:%M:%S')
                status = "✅ Зарегистрирована" if game.registered else "⏳ Обнаружена"
                lines.append(f"  • *{game.title} {game.game_number}*")
                lines.append(f"    📅 {game.date} {game.time}")
                lines.append(f"    🏷️ {game.game_type}")
                lines.append(f"    ⏰ {status}: {discovered}")
                lines.append("")

        # Добавляем статистику за неделю
        if weekly_stats:
            lines.append("*📈 Статистика за неделю:*")
            for date, stats in sorted(weekly_stats.items(), reverse=True):
                lines.append(
                    f"  • {date} ({stats.day_of_week}): {stats.games_found} игр, {stats.games_registered} регистраций")

        lines.append("")
        lines.append(f"🕐 *Обновлено:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)

    def get_new_games_report(self, games: List) -> str:
        """Формирует отчет о новых играх"""
        if not games:
            return "🆕 *Новых игр не обнаружено*"

        lines = [
            "🎯 *ОБНАРУЖЕНЫ НОВЫЕ ИГРЫ!*",
            "",
            f"📅 *Дата:* {datetime.now().strftime('%Y-%m-%d')} ({self._get_day_of_week(datetime.now().weekday())})",
            f"🕐 *Время обнаружения:* {datetime.now().strftime('%H:%M:%S')}",
            f"🎮 *Количество новых игр:* {len(games)}",
            ""
        ]

        for game in games:
            # Определяем тип игры
            game_type = 'classic'
            if '[новички]' in game.title or 'ИЗИ' in game.title or 'Easy' in game.title:
                game_type = 'easy'

            lines.append(f"*{game.title} {game.game_number}*")
            lines.append(f"  📅 {game.date} {game.time}")
            lines.append(f"  🏷️ Тип: {game_type}")
            if hasattr(game, 'registration_url') and game.registration_url:
                lines.append(f"  🔗 Ссылка: {game.registration_url}")
            lines.append("")

        lines.append("---")
        lines.append(f"🕐 *Отчет сгенерирован:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(lines)

    def get_registered_games(self) -> List[Dict]:
        """Возвращает список зарегистрированных игр"""
        try:
            registered_file = self._get_registered_games_file()
            if os.path.exists(registered_file):
                with open(registered_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('games', [])
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки зарегистрированных игр: {e}")
            return []

    def clear_old_stats(self, days: int = 30):
        """Удаляет статистику старше указанного количества дней"""
        if days <= 0:
            return

        cutoff_date = datetime.now() - timedelta(days=days)
        games_to_remove = []

        for game_id, data in self.stats.items():
            discovered_at = data.get('discovered_at')
            if discovered_at:
                try:
                    discovered_date = datetime.fromisoformat(discovered_at)
                    if discovered_date < cutoff_date:
                        games_to_remove.append(game_id)
                except:
                    pass

        if games_to_remove:
            for game_id in games_to_remove:
                del self.stats[game_id]
            logger.info(f"🗑️ Удалено {len(games_to_remove)} старых записей статистики")
            self.save_stats()