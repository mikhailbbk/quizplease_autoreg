#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Планировщик для запуска мониторинга каждые 15 минут (ежедневно)
"""
import os
import sys
import time
import logging
import subprocess
from datetime import datetime
import json

# Добавляем src в путь
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    import config
except ImportError:
    print("❌ Не удалось импортировать config.py")
    print("Убедитесь, что файл config.py существует в папке src/")
    sys.exit(1)

# Используем пути из config
LOG_DIR = config.LOGS_DIR
DATA_DIR = config.DATA_DIR

# Создаем необходимые директории
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Настройка логирования с использованием путей из config
LOG_FILE = os.path.join(LOG_DIR, 'scheduler.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class QuizPleaseScheduler:
    """Планировщик для запуска мониторинга каждые 15 минут"""

    def __init__(self):
        self.config = config.SCHEDULE_CONFIG
        self.script_path = "run_with_registration.py"
        self.last_run_file = os.path.join(LOG_DIR, 'last_run.json')

        # Проверяем наличие скрипта
        if not os.path.exists(self.script_path):
            logger.error(f"❌ Скрипт {self.script_path} не найден!")
            logger.error(f"   Текущая директория: {os.getcwd()}")
            logger.error(f"   Полный путь: {os.path.abspath(self.script_path)}")

        # Настройки
        self.interval_minutes = self.config.get('interval_minutes', 15)
        self.days = self.config.get('days', [0, 1, 2, 3, 4, 5, 6])  # Все дни по умолчанию

        self.day_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']

    def load_last_run(self) -> dict:
        """Загружает информацию о последнем запуске"""
        if os.path.exists(self.last_run_file):
            try:
                with open(self.last_run_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Ошибка загрузки last_run: {e}")
                return {}
        return {}

    def save_last_run(self, data: dict):
        """Сохраняет информацию о последнем запуске"""
        try:
            # Создаем директорию если её нет
            os.makedirs(os.path.dirname(self.last_run_file), exist_ok=True)
            with open(self.last_run_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения last_run: {e}")

    def should_run(self) -> tuple:
        """Проверяет, нужно ли запускать мониторинг"""
        if not self.config.get('enabled', True):
            return False, "Планировщик отключен в настройках"

        # Проверяем день недели
        current_day = datetime.now().weekday()
        if current_day not in self.days:
            days_str = ', '.join([self.day_names[d] for d in self.days])
            return False, f"Сегодня не разрешенный день ({self.day_names[current_day]}). Разрешенные: {days_str}"

        # Проверяем время (если указано)
        time_start = self.config.get('time_start', '00:00')
        time_end = self.config.get('time_end', '23:59')

        now = datetime.now().time()
        try:
            from datetime import time as dt_time
            start = dt_time(*map(int, time_start.split(':')))
            end = dt_time(*map(int, time_end.split(':')))
            if not (start <= now <= end):
                return False, f"Время {now.strftime('%H:%M')} вне окна {time_start}-{time_end}"
        except Exception as e:
            logger.debug(f"Ошибка проверки времени: {e}")

        # Проверяем интервал
        last_run = self.load_last_run()
        if last_run:
            last_time = last_run.get('last_run_time')
            if last_time:
                try:
                    last_dt = datetime.fromisoformat(last_time)
                    elapsed = (datetime.now() - last_dt).total_seconds()
                    interval = self.interval_minutes * 60
                    if elapsed < interval:
                        return False, f"Последний запуск {elapsed:.0f}с назад (интервал {interval}с)"
                except Exception as e:
                    logger.debug(f"Ошибка проверки интервала: {e}")

        return True, "Все условия выполнены"

    def run_monitor(self):
        """Запускает мониторинг"""
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК МОНИТОРИНГА")
        logger.info("=" * 60)
        logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"📋 {self.day_names[datetime.now().weekday()]}")
        logger.info(f"⏱️  Интервал: {self.interval_minutes} минут")
        logger.info(f"📁 Логи: {LOG_FILE}")
        logger.info("=" * 60)

        # Проверяем наличие скрипта перед запуском
        if not os.path.exists(self.script_path):
            logger.error(f"❌ Скрипт {self.script_path} не найден!")
            logger.error(f"   Полный путь: {os.path.abspath(self.script_path)}")
            self.save_last_run({
                'last_run_time': datetime.now().isoformat(),
                'status': 'error',
                'error': f'Скрипт {self.script_path} не найден'
            })
            return

        try:
            # Запускаем скрипт с теми же переменными окружения
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'  # Для немедленного вывода логов

            result = subprocess.run(
                [sys.executable, self.script_path],
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )

            if result.returncode == 0:
                logger.info("✅ Мониторинг выполнен успешно")
                self.save_last_run({
                    'last_run_time': datetime.now().isoformat(),
                    'status': 'success',
                    'returncode': result.returncode
                })
            else:
                logger.error(f"❌ Ошибка (код: {result.returncode})")
                if result.stderr:
                    logger.error(f"Ошибка: {result.stderr[:500]}")
                if result.stdout:
                    logger.info(f"Вывод: {result.stdout[:500]}")
                self.save_last_run({
                    'last_run_time': datetime.now().isoformat(),
                    'status': 'failed',
                    'returncode': result.returncode,
                    'error': result.stderr[:500] if result.stderr else result.stdout[:500] if result.stdout else ''
                })

        except subprocess.TimeoutExpired:
            logger.error("❌ Таймаут (превышено 300 секунд)")
            self.save_last_run({
                'last_run_time': datetime.now().isoformat(),
                'status': 'timeout'
            })
        except FileNotFoundError as e:
            logger.error(f"❌ Ошибка: {e}")
            self.save_last_run({
                'last_run_time': datetime.now().isoformat(),
                'status': 'error',
                'error': f'Файл не найден: {e}'
            })
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            self.save_last_run({
                'last_run_time': datetime.now().isoformat(),
                'status': 'error',
                'error': str(e)
            })

    def run_loop(self):
        """Основной цикл"""
        logger.info("=" * 60)
        logger.info("🔄 ЗАПУСК ПЛАНИРОВЩИКА (ЕЖЕДНЕВНО, 15 МИНУТ)")
        logger.info("=" * 60)
        logger.info(f"📁 Директория проекта: {os.path.dirname(os.path.abspath(__file__))}")
        logger.info(f"📁 Директория логов: {LOG_DIR}")
        logger.info(f"📁 Директория данных: {DATA_DIR}")
        days_str = ', '.join([self.day_names[d] for d in self.days])
        logger.info(f"📅 Дни: {days_str}")
        logger.info(f"⏱️  Интервал: {self.interval_minutes} минут")
        logger.info(f"🕐 Старт: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        run_count = 0
        while True:
            try:
                should_run, reason = self.should_run()

                if should_run:
                    run_count += 1
                    logger.info(f"📊 Запуск #{run_count}")
                    logger.info(f"✅ {reason}")
                    self.run_monitor()
                else:
                    logger.debug(f"⏭️ {reason}")

                # Проверяем каждые 30 секунд
                time.sleep(30)

            except KeyboardInterrupt:
                logger.info("\n⏹️ Остановлено пользователем")
                logger.info(f"📊 Всего выполнено запусков: {run_count}")
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в основном цикле: {e}")
                time.sleep(60)


def main():
    """Основная функция"""
    scheduler = QuizPleaseScheduler()

    # Проверяем аргументы командной строки
    if '--once' in sys.argv:
        logger.info("🔄 Однократный запуск")
        scheduler.run_monitor()
        return
    elif '--help' in sys.argv or '-h' in sys.argv:
        print("Использование: python scheduler.py [опции]")
        print()
        print("Опции:")
        print("  --once    Выполнить однократный запуск мониторинга")
        print("  --help    Показать эту справку")
        print()
        print("Без опций запускается в бесконечном цикле с интервалом 15 минут")
        return

    # Запускаем в бесконечном цикле
    scheduler.run_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Программа остановлена")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)