"""
Скрипт для экспорта кук из браузера.
"""
import json
import os
import sys

# Добавляем src в путь для импорта config
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    import config

    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    print("⚠️ ВНИМАНИЕ: config.py не найден, использую локальные пути")


def get_cookies_path() -> str:
    """
    Определяет путь к файлу cookies.json.
    Сначала пытается использовать путь из config.py,
    если не получается - использует локальный путь.
    """
    if USE_CONFIG and hasattr(config, 'COOKIES_CONFIG'):
        cookies_path = config.COOKIES_CONFIG.get('file_path')
        if cookies_path:
            return cookies_path

    # Запасной вариант: локальный путь
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.json')


def get_template_path() -> str:
    """Определяет путь к файлу шаблона cookies.json.template"""
    if USE_CONFIG and hasattr(config, 'SRC_DIR'):
        return os.path.join(config.SRC_DIR, 'cookies.json.template')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.json.template')


def export_cookies_manual():
    """
    Помогает вручную экспортировать куки из браузера.
    """
    print("=" * 60)
    print("🍪 ЭКСПОРТ КУК ИЗ БРАУЗЕРА")
    print("=" * 60)
    print()
    print("📋 ИНСТРУКЦИЯ:")
    print()
    print("1. Откройте браузер и перейдите на https://klg.quizplease.ru")
    print("2. Авторизуйтесь на сайте (если требуется)")
    print("3. Откройте Инструменты разработчика (F12) -> Вкладка Application")
    print("4. Слева выберите Cookies -> https://klg.quizplease.ru")
    print("5. Скопируйте значения следующих кук:")
    print()
    print("   Ключевые куки:")
    print("   - _ga")
    print("   - _ym_uid")
    print("   - _ym_d")
    print("   - _ym_isad")
    print("   - city_id")
    print("   - city_name")
    print("   - country_id")
    print("   - country_title")
    print("   - city_map")
    print("   - currency")
    print("   - slug")
    print()
    print("6. Вставьте их в файл cookies.json в формате:")
    print()
    print('   {')
    print('       "_ga": "GA1.1.573193689.1780933125",')
    print('       "_ym_uid": "178172800816163693",')
    print('       "_ym_d": "1781728008",')
    print('       "_ym_isad": "2",')
    print('       "city_id": "32",')
    print('       "city_name": "Калуга",')
    print('       "country_id": "1",')
    print('       "country_title": "Россия",')
    print('       "city_map": "yandex",')
    print('       "currency": "₽",')
    print('       "slug": "klg"')
    print('   }')
    print()
    print(f"📁 Путь к файлу cookies.json: {get_cookies_path()}")
    print()
    print("=" * 60)


def create_cookies_template():
    """
    Создает шаблон файла cookies.json
    """
    template = {
        "_ga": "GA1.1.573193689.1780933125",
        "_ym_uid": "178172800816163693",
        "_ym_d": "1781728008",
        "_ym_isad": "2",
        "city_id": "32",
        "city_name": "Калуга",
        "country_id": "1",
        "country_title": "Россия",
        "city_map": "yandex",
        "currency": "₽",
        "slug": "klg"
    }

    template_path = get_template_path()

    try:
        # Создаем директорию если её нет
        template_dir = os.path.dirname(template_path)
        if template_dir:
            os.makedirs(template_dir, exist_ok=True)

        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        print(f"✅ Шаблон создан: {template_path}")
        print()
        print("📝 Дальнейшие действия:")
        print(f"  1. Скопируйте шаблон в cookies.json:")
        print(f"     cp {template_path} {get_cookies_path()}")
        print("  2. Откройте cookies.json в редакторе")
        print("  3. Замените значения на реальные куки из браузера")
        print("  4. Убедитесь, что обязательные куки (_ym_uid, city_id) присутствуют")
        print()
        print("⚠️ ВАЖНО: cookies.json должен быть на сервере для работы регистрации!")

    except Exception as e:
        print(f"❌ Ошибка при создании шаблона: {e}")
        return False

    return True


def check_cookies_file():
    """Проверяет наличие и корректность файла cookies.json"""
    cookies_path = get_cookies_path()

    print("=" * 60)
    print("🔍 ПРОВЕРКА ФАЙЛА COOKIES.JSON")
    print("=" * 60)
    print()

    if not os.path.exists(cookies_path):
        print(f"❌ Файл cookies.json не найден: {cookies_path}")
        print()
        print("📝 Для создания файла:")
        print("  1. Запустите скрипт с аргументом --create")
        print("     python export_cookies.py --create")
        print("  2. Или создайте вручную из шаблона")
        return False

    print(f"✅ Файл найден: {cookies_path}")

    try:
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies = json.load(f)

        print(f"✅ Файл содержит {len(cookies)} кук")

        # Проверяем обязательные куки
        required = ['_ym_uid', 'city_id']
        missing = [c for c in required if c not in cookies]

        if missing:
            print(f"⚠️ Отсутствуют обязательные куки: {missing}")
            print("   Регистрация может не работать без них!")
            return False
        else:
            print("✅ Все обязательные куки присутствуют")

        # Показываем найденные куки
        print()
        print("📋 Найденные куки:")
        for key in sorted(cookies.keys()):
            value = cookies[key]
            if isinstance(value, str) and len(value) > 30:
                value = value[:30] + "..."
            print(f"  - {key}: {value}")

        return True

    except json.JSONDecodeError as e:
        print(f"❌ Ошибка формата JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке файла: {e}")
        return False


def main():
    """Основная функция"""
    import argparse

    parser = argparse.ArgumentParser(description='Утилита для работы с cookies')
    parser.add_argument('--create', action='store_true',
                        help='Создать шаблон cookies.json.template')
    parser.add_argument('--check', action='store_true',
                        help='Проверить наличие и корректность cookies.json')
    parser.add_argument('--help-full', action='store_true',
                        help='Показать полную инструкцию по экспорту кук')

    args = parser.parse_args()

    if args.help_full or (not args.create and not args.check):
        export_cookies_manual()
        print()
        create_cookies_template()
        print()
        check_cookies_file()
        return

    if args.create:
        create_cookies_template()
        return

    if args.check:
        check_cookies_file()
        return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Программа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()