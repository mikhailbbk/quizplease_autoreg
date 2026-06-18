"""
Модуль для автоматической регистрации на игры QuizPlease
"""
import logging
import requests
import re
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Импортируем config для получения путей
try:
    import config
except ImportError:
    # Если config не найден, используем локальный путь как запасной вариант
    config = None
    print("⚠️ ВНИМАНИЕ: config.py не найден, использую локальные пути")

logger = logging.getLogger(__name__)


@dataclass
class RegistrationData:
    """Данные для регистрации команды"""
    team_name: str
    captain_name: str
    email: str
    phone: str
    players_count: int
    first_time: bool = True
    comment: str = ""
    has_promo: bool = False
    consent_data: bool = True
    consent_marketing: bool = False


class QuizPleaseRegistrator:
    """Класс для автоматической регистрации на игры с поддержкой CSRF-защиты"""

    def __init__(self, base_url: str = "https://api.quizplease.ru", site_url: str = "https://klg.quizplease.ru"):
        """
        Инициализация регистратора

        Args:
            base_url: Базовый URL API
            site_url: URL сайта для получения CSRF-токена
        """
        self.base_url = base_url
        self.site_url = site_url
        self.api_url = f"{base_url}/api/games/records"
        self.calculate_url = f"{base_url}/api/games/records/public/calculate-with-discounts"

        # Создаем сессию для поддержки cookies
        self.session = requests.Session()

        # Настраиваем заголовки как у реального браузера
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 YaBrowser/26.4.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Origin': 'https://klg.quizplease.ru',
            'Referer': 'https://klg.quizplease.ru/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        })

        # Флаг готовности сессии
        self._session_ready = False
        self._csrf_token = None

    def _get_cookies_file_path(self) -> str:
        """
        Определяет путь к файлу cookies.json.
        Сначала пытается использовать путь из config.py,
        если не получается - использует локальный путь.
        """
        # Пробуем получить путь из config
        if config and hasattr(config, 'COOKIES_CONFIG'):
            cookies_path = config.COOKIES_CONFIG.get('file_path')
            if cookies_path and os.path.exists(cookies_path):
                return cookies_path

        # Запасной вариант: локальный путь
        src_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(src_dir, 'cookies.json')

    def load_cookies_from_file(self) -> bool:
        """
        Загружает куки из файла cookies.json.

        Returns:
            bool: True если куки успешно загружены
        """
        try:
            # Получаем путь к файлу cookies.json
            cookies_file = self._get_cookies_file_path()

            if not os.path.exists(cookies_file):
                logger.warning(f"⚠️ Файл с куками не найден: {cookies_file}")
                return False

            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies_dict = json.load(f)

            count = 0
            for name, value in cookies_dict.items():
                if value:
                    # Для домена quizplease.ru
                    self.session.cookies.set(name, str(value), domain='.quizplease.ru')
                    # Также для klg.quizplease.ru
                    self.session.cookies.set(name, str(value), domain='klg.quizplease.ru')
                    count += 1
                    logger.debug(f"🍪 Загружена кука: {name}")

            logger.info(f"✅ Загружено {count} кук из {cookies_file}")

            # Проверяем наличие обязательных кук
            if config and hasattr(config, 'COOKIES_CONFIG'):
                required = config.COOKIES_CONFIG.get('required_cookies', ['_ym_uid', 'city_id'])
            else:
                required = ['_ym_uid', 'city_id']

            missing = [c for c in required if c not in self.session.cookies]
            if missing:
                logger.warning(f"⚠️ Отсутствуют обязательные куки: {missing}")
            else:
                logger.info(f"✅ Все обязательные куки присутствуют")

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка при загрузке кук: {str(e)}")
            return False

    def _prepare_session(self) -> bool:
        """
        Подготавливает сессию: загружает куки и получает CSRF-токен.

        Returns:
            bool: True если сессия успешно подготовлена
        """
        if self._session_ready and self._csrf_token:
            return True

        logger.info("🔄 Подготовка сессии...")

        # Загружаем куки из файла
        if len(self.session.cookies) == 0:
            if not self.load_cookies_from_file():
                logger.warning("⚠️ Не удалось загрузить куки из файла")
                # Продолжаем работу, возможно куки получатся через запросы

        # Проверяем основные куки (используем config если доступен)
        if config and hasattr(config, 'COOKIES_CONFIG'):
            required_cookies = config.COOKIES_CONFIG.get('required_cookies', ['_ym_uid', 'city_id'])
        else:
            required_cookies = ['_ym_uid', 'city_id']

        missing = [c for c in required_cookies if c not in self.session.cookies]
        if missing:
            logger.warning(f"⚠️ Отсутствуют куки: {missing}")

        # 1. Проверяем, есть ли CSRF-токен в куках
        xsrf_token = self.session.cookies.get('XSRF-TOKEN')
        if xsrf_token:
            self._csrf_token = xsrf_token
            self._session_ready = True
            logger.info(f"✅ CSRF-токен получен из кук: {xsrf_token[:15]}...")
            return True

        # 2. Пробуем получить токен через API
        try:
            # Используем city_id из config если доступен
            if config and hasattr(config, 'API_CONFIG'):
                city_id = config.API_CONFIG.get('city_id', 32)
            else:
                city_id = 32

            city_settings_url = f"{self.site_url}/api/city-settings/{city_id}"
            response = self.session.get(
                city_settings_url,
                timeout=15,
                headers={
                    'Accept': '*/*',
                    'Referer': f'{self.site_url}/schedule?statuses[]=0&statuses[]=1&statuses[]=2&statuses[]=3',
                }
            )

            if response.status_code in [200, 304]:
                # Проверяем куки после запроса
                xsrf_token = self.session.cookies.get('XSRF-TOKEN')
                if xsrf_token:
                    self._csrf_token = xsrf_token
                    self._session_ready = True
                    logger.info(f"✅ CSRF-токен получен из кук: {xsrf_token[:15]}...")
                    return True

                # Проверяем заголовки ответа
                if 'X-XSRF-TOKEN' in response.headers:
                    self._csrf_token = response.headers['X-XSRF-TOKEN']
                    self._session_ready = True
                    logger.info(f"✅ CSRF-токен получен из заголовков: {self._csrf_token[:15]}...")
                    return True

                # Проверяем тело ответа
                try:
                    data = response.json()
                    if 'csrf_token' in data:
                        self._csrf_token = data['csrf_token']
                        self._session_ready = True
                        logger.info(f"✅ CSRF-токен получен из тела ответа: {self._csrf_token[:15]}...")
                        return True
                except:
                    pass
        except Exception as e:
            logger.debug(f"Ошибка при запросе к API: {str(e)}")

        # 3. Пробуем через главную страницу
        try:
            response = self.session.get(self.site_url, timeout=15)

            if response.status_code == 200:
                # Проверяем куки после запроса
                xsrf_token = self.session.cookies.get('XSRF-TOKEN')
                if xsrf_token:
                    self._csrf_token = xsrf_token
                    self._session_ready = True
                    logger.info(f"✅ CSRF-токен получен из кук после загрузки страницы: {xsrf_token[:15]}...")
                    return True

                # Ищем CSRF-токен в HTML
                patterns = [
                    r'<meta[^>]*name=["\']csrf-token["\'][^>]*content=["\']([^"\']+)["\']',
                    r'<meta[^>]*name=["\']XSRF-TOKEN["\'][^>]*content=["\']([^"\']+)["\']',
                    r'window\.Laravel\s*=\s*\{[^}]*csrfToken:\s*["\']([^"\']+)["\']',
                    r'"csrfToken"\s*:\s*["\']([^"\']+)["\']',
                ]

                for pattern in patterns:
                    match = re.search(pattern, response.text, re.IGNORECASE)
                    if match:
                        self._csrf_token = match.group(1)
                        self._session_ready = True
                        logger.info(f"✅ CSRF-токен найден в HTML: {self._csrf_token[:15]}...")
                        return True
        except Exception as e:
            logger.debug(f"Ошибка при загрузке главной страницы: {str(e)}")

        # 4. Если есть куки, но нет CSRF-токена, пробуем использовать их
        if len(self.session.cookies) > 0:
            logger.info("ℹ️ Использую существующие куки без CSRF-токена")
            self._session_ready = True
            return True

        logger.error("❌ Не удалось подготовить сессию")
        return False

    def register_to_game(self, game_id: str, registration_data: RegistrationData) -> Dict:
        """Регистрация команды на конкретную игру."""
        # Подготавливаем сессию
        if not self._prepare_session():
            return {
                'success': False,
                'game_id': game_id,
                'message': '❌ Не удалось подготовить сессию для регистрации'
            }

        try:
            logger.info(f"📝 Регистрация на игру {game_id}: {registration_data.team_name}")

            # Получаем ya_client_id из config если доступен
            ya_client_id = "178172800816163693"  # Значение по умолчанию
            if config and hasattr(config, 'API_CONFIG'):
                ya_client_id = config.API_CONFIG.get('ya_client_id', ya_client_id)

            # Формируем payload
            payload = {
                'game_id': game_id,
                'title': registration_data.team_name,
                'captain': registration_data.captain_name,
                'email': registration_data.email,
                'phone': registration_data.phone,
                'people_count': registration_data.players_count,
                'count_paid': registration_data.players_count,
                'comment': registration_data.comment or '',
                'is_first': registration_data.first_time,
                'is_pay_now': False,
                'is_send_email': True,
                'is_personal_data_consent': registration_data.consent_data,
                'is_marketing_consent': registration_data.consent_marketing,
                'promo_ids': [],
                'certificate_ids': [],
                'table_size': None,
                'payment_method': 'cash',
                'utm': {},
                'ya_client_id': ya_client_id
            }

            # Заголовки для запроса
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            }

            if self._csrf_token:
                headers['X-XSRF-TOKEN'] = self._csrf_token
                headers['X-CSRF-TOKEN'] = self._csrf_token

            # Логируем запрос для отладки (без чувствительных данных)
            debug_payload = payload.copy()
            debug_payload['phone'] = '***'
            debug_payload['email'] = '***'
            logger.debug(f"📤 Отправка запроса: {json.dumps(debug_payload, ensure_ascii=False)}")

            # Отправляем запрос на регистрацию
            response = self.session.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            logger.info(f"📡 Статус ответа: {response.status_code}")

            # Парсим ответ
            try:
                response_data = response.json()
                logger.debug(f"📥 Ответ: {json.dumps(response_data, ensure_ascii=False)[:200]}...")
            except ValueError:
                response_data = {'raw_response': response.text[:200]}

            # Анализируем результат
            if response.status_code == 200:
                if (response_data.get('status') == 'ok' or
                        response_data.get('data', {}).get('id') or
                        response_data.get('success', False)):

                    logger.info(f"✅ УСПЕШНАЯ РЕГИСТРАЦИЯ на игру {game_id}!")
                    return {
                        'success': True,
                        'game_id': game_id,
                        'response': response_data,
                        'message': f"✅ Зарегистрированы на игру {game_id}"
                    }
                else:
                    error_msg = response_data.get('message', 'Неизвестная ошибка')
                    logger.error(f"❌ Ошибка сервера при регистрации: {error_msg}")
                    return {
                        'success': False,
                        'game_id': game_id,
                        'error': response_data,
                        'message': f"❌ Ошибка регистрации: {error_msg}"
                    }
            elif response.status_code == 422:
                error_msg = response_data.get('message', 'Ошибка валидации данных')
                errors = response_data.get('errors', {})
                if errors:
                    error_details = []
                    for field, msgs in errors.items():
                        error_details.append(f"{field}: {', '.join(msgs)}")
                    error_msg = f"{error_msg} ({'; '.join(error_details)})"

                logger.error(f"❌ Ошибка валидации (422): {error_msg}")
                return {
                    'success': False,
                    'game_id': game_id,
                    'error': response_data,
                    'message': f"❌ Ошибка валидации: {error_msg}"
                }
            else:
                logger.error(f"❌ HTTP ошибка {response.status_code}: {response.text[:200]}")
                return {
                    'success': False,
                    'game_id': game_id,
                    'error': response_data,
                    'message': f"❌ HTTP ошибка {response.status_code}"
                }

        except requests.exceptions.Timeout:
            logger.error(f"❌ Таймаут при регистрации на игру {game_id}")
            return {
                'success': False,
                'game_id': game_id,
                'error': 'Timeout',
                'message': f"❌ Таймаут при регистрации на игру {game_id}"
            }
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка при регистрации: {str(e)}")
            return {
                'success': False,
                'game_id': game_id,
                'error': str(e),
                'message': f"❌ Неизвестная ошибка: {str(e)}"
            }

    def register_to_multiple_games(self, game_ids: List[str], registration_data: RegistrationData) -> List[Dict]:
        """Регистрация на несколько игр."""
        results = []
        total_games = len(game_ids)

        logger.info(f"🚀 Начинаю регистрацию на {total_games} игр")

        for index, game_id in enumerate(game_ids, 1):
            logger.info(f"📌 Прогресс: {index}/{total_games} - Игра {game_id}")
            result = self.register_to_game(game_id, registration_data)
            results.append(result)

            if index < total_games:
                import time
                time.sleep(1)

        return results

    def get_registration_report(self, results: List[Dict]) -> str:
        """Формирует отчет о регистрации для отправки в Telegram."""
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]

        lines = [
            "📋 *ОТЧЕТ О РЕГИСТРАЦИИ*",
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"✅ Успешно: {len(successful)}",
            f"❌ Ошибок: {len(failed)}",
            ""
        ]

        if successful:
            lines.append("*Успешные регистрации:*")
            for result in successful:
                lines.append(f"  ✅ {result.get('message', 'OK')}")

        if failed:
            lines.append("*Ошибки:*")
            for result in failed:
                lines.append(f"  ❌ {result.get('message', 'Неизвестная ошибка')}")

        return "\n".join(lines)

    def reset_session(self):
        """Сбрасывает сессию."""
        self._session_ready = False
        self._csrf_token = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 YaBrowser/26.4.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Origin': 'https://klg.quizplease.ru',
            'Referer': 'https://klg.quizplease.ru/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        })
        logger.info("🔄 Сессия сброшена")