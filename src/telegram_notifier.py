"""
Модуль для отправки уведомлений в Telegram (синхронная версия, поддержка нескольких получателей)
"""
import logging
import requests
from datetime import datetime
from typing import List, Union

logger = logging.getLogger(__name__)


class TelegramBot:
    """Класс для работы с Telegram Bot API (синхронный, поддержка нескольких chat_ids)"""

    def __init__(self, bot_token: str, chat_ids: Union[str, List[str]]):
        self.bot_token = bot_token
        # Преобразуем одиночный chat_id в список
        if isinstance(chat_ids, str):
            self.chat_ids = [chat_ids]
        else:
            self.chat_ids = chat_ids
        self.api_url = f"https://149.154.167.220/bot{bot_token}"
        self.is_available = self._test_connection()

    def _test_connection(self) -> bool:
        """Проверка подключения к боту."""
        try:
            headers = {'Host': 'api.telegram.org'}
            response = requests.get(f"{self.api_url}/getMe", headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    logger.info(f"✅ Бот @{bot_info['result']['username']} успешно подключен")
                    logger.info(f"📨 Будет отправлять уведомления {len(self.chat_ids)} получателям: {self.chat_ids}")
                    return True
            logger.error(f"❌ Ошибка подключения: {response.text}")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к боту: {str(e)}")
            return False

    def send_message(self, text: str, parse_mode: str = 'Markdown') -> bool:
        """Отправка сообщения в Telegram всем получателям"""
        if not self.is_available:
            logger.warning("Бот недоступен, пропускаем отправку сообщения")
            return False

        success_count = 0
        for chat_id in self.chat_ids:
            try:
                headers = {'Host': 'api.telegram.org'}
                payload = {
                    'chat_id': chat_id,
                    'text': text,
                    'parse_mode': parse_mode,
                    'disable_web_page_preview': False
                }
                response = requests.post(f"{self.api_url}/sendMessage", headers=headers, json=payload, timeout=10, verify=False)
                if response.status_code == 200:
                    logger.info(f"✅ Сообщение отправлено в Telegram (chat_id: {chat_id})")
                    success_count += 1
                else:
                    logger.error(f"❌ Ошибка отправки для {chat_id}: {response.text}")
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке сообщения для {chat_id}: {str(e)}")

        return success_count > 0

    def send_game_notification(self, game) -> bool:
        """Отправка уведомления об игре всем получателям"""
        try:
            message = game.to_telegram_message()
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {str(e)}")
            return False

    def send_summary(self, games: List) -> bool:
        """Отправка сводки по играм всем получателям"""
        if not games:
            logger.info("Нет игр для отправки сводки")
            return True

        total_games = len(games)
        active_games = [g for g in games if g.availability_type == 'active']
        reserve_games = [g for g in games if g.availability_type == 'reserve']

        summary_lines = [
            f"📊 *СВОДКА ПО ИГРАМ КВИЗ, ПЛИЗ! KLG*",
            f"🕐 *Обновлено:* {games[0].extracted_at}",
            "",
            f"📋 *Всего игр:* {total_games}",
            f"✅ *Доступно для записи:* {len(active_games)}",
            f"⚠️  *Запись в резерв:* {len(reserve_games)}",
        ]

        if reserve_games:
            summary_lines.extend(["", "*Ближайшие игры:*"])
            for i, game in enumerate(reserve_games[:3], 1):
                info = f"{i}. {game.date} {game.time} - {game.game_number}"
                if game.place and game.place != 'Не указано':
                    info += f" ({game.place})"
                summary_lines.append(info)

        summary_lines.extend([
            "",
            f"[📅 Открыть полное расписание](https://klg.quizplease.ru/schedule)"
        ])

        summary = "\n".join(summary_lines)
        return self.send_message(summary)

    def send_test_message(self) -> bool:
        """Отправка тестового сообщения всем получателям"""
        test_message = (
            "🤖 *Тестовое сообщение от QuizPlease Parser*\n"
            f"🕐 Время отправки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "✅ Бот успешно подключен и готов к работе!\n"
            "📊 Ожидайте уведомлений о новых играх."
        )

        logger.info("Отправка тестового сообщения...")
        return self.send_message(test_message)


# Алиас для совместимости
TelegramNotifier = TelegramBot