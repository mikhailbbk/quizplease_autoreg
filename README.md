# QuizPlease Autoreg - Парсер и Telegram-бот


[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4.12-44B02A)](https://www.crummy.com/software/BeautifulSoup/)
[![Telegram API](https://img.shields.io/badge/Telegram%20API-✓-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-✓-2088FF?logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![Systemd](https://img.shields.io/badge/Systemd-✓-DA2F47)](https://systemd.io/)

**Автоматическая система мониторинга расписания игр на quizplease.ru с отправкой уведомлений в Telegram.**

## Возможности
*   **Автоматический мониторинг:** Парсинг расписания игр с автоматической проверкой изменений  
*   **Telegram-бот:** Автоматические уведомления о новых играх и изменении статуса  
*   **CI/CD пайплайн:** Автоматический деплой через GitHub Actions при каждом коммите в main  
*   **Отказоустойчивость:** Может работать как systemd-сервис 24/7  
*   **Полная информация:** Детализированные сообщения с датой, временем, местом, ценой и статусом

## Технологический стек
*   **Язык:** Python 3.11
*   **Парсинг:** BeautifulSoup4, Requests
*   **Мессенджер:** Telegram Bot API
*   **Инфраструктура:** Ubuntu Server, Systemd, GitHub Actions
*   **Хранение данных:** JSON
*   **Логирование:** Стандартный logging + файловые логи
*   **Инструменты:** Git, GitHub Actions

## Структура проекта
```text
quizplease_autoreg/
├── .github/workflows/          # CI/CD пайплайны GitHub Actions
│   ├── deploy.yml              # Автоматический деплой
│   └── fix-git.yml             # Утилита для исправления Git
├── src/                        # Исходный код
│   ├── extract_classic_games.py # Основной парсер
│   ├── telegram_notifier.py    # Telegram бот
│   ├── get_chat_id.py          # Утилита получения Chat ID
│   ├── config.example.py       # Пример конфигурации
│   └── config.py               # Фактическая конфигурация
├── data/                       # Хранение данных
│   ├── classic_games.json      # Текущее расписание игр
│   └── games_history.json      # История изменений
├── logs/                       # Логи работы
├── requirements.txt            # Зависимости Python
└── README.md                   # Документация
```       

## Решенные задачи и принятые решения

### Задача 1: Надежный парсинг сайта с динамической структурой
*   **Проблема:** Сайт quizplease.ru имеет сложную HTML-структуру.
*   **Решение:** 
    1. **Многоуровневое извлечение данных:** Несколько методов поиска для каждого поля  
    2. **Резервные селекторы:** Альтернативные CSS-селекторы на случай изменений  
    3. **Валидация данных:** Проверка корректности перед сохранением  
    4. **Хэширование:** Создание уникальных идентификаторов для отслеживания изменений  

### Задача 2: Обеспечение бесперебойной работы
*   **Проблема:** Система должна работать надежно и восстанавливаться после сбоев.  
*   **Решение:** 
    1. **Systemd сервис:** Production-ready конфигурация с автоперезапуском      
    2. **Логирование:** Комплексное логирование в файлы и systemd journal  
    3. **Обработка ошибок:** Грейсфул деградация при сбоях  

### Задача 3: Автоматизация деплоя
*   **Проблема:** Ручное обновление кода было трудоемким.  
*   **Решение: CI/CD пайплайн на GitHub Actions** с автоматическим деплоем при пуше в main.
  
### Задача 4: Интеллектуальные уведомления

*   **Проблема:** Избегать спама, но информировать о важных изменениях.
*   **Решение:** 
    1. **Только изменения:** Уведомления только при новых играх или изменении статуса  
    2. **Полная информация:** Детализированные сообщения по каждой игре  
    3. **Форматирование:** Читабельные сообщения с эмодзи и Markdown

### Задача 5: Конфигурация и безопасность
*   **Проблема:** Безопасное хранение чувствительных данных.
*   **Решение:**
    1. **Шаблон конфигурации:** config.example.py для безопасного клонирования  
    2. **Отдельный файл** config.py не отслеживается в Git  
    3. **Встроенная утилита:** get_chat_id.py для получения Chat ID  

### Компоненты:
1. **Парсер (src/extract_classic_games.py):** Основной модуль, извлекает данные с сайта
2. **Telegram бот (src/telegram_notifier.py):** Отправляет уведомления пользователям
3. **Хранилище данных (data/):** Кэширует предыдущие данные для сравнения
4. **Systemd сервис:** Обеспечивает непрерывную работу
5. **CI/CD пайплайн:** Автоматизирует развертывание

## Быстрый старт

### Установка
```bash
# Клонируйте репозиторий
git clone https://github.com/Mikhail15011976/quizplease_autoreg.git
cd quizplease_autoreg

# Установите зависимости
pip install -r requirements.txt

# Настройте конфигурацию
cp src/config.example.py src/config.py
# Отредактируйте src/config.py, добавив ваш токен Telegram

# Получение Chat ID
python src/get_chat_id.py
# Следуйте инструкциям в скрипте
```

## Конфигурация
1. **Telegram Bot Token:** Получите у @BotFather  
2. **Chat ID:** Получите через утилиту get_chat_id.py  
3. **Настройки парсера:** Отредактируйте src/config.py

### Пример конфигурации:
```python
# Telegram конфигурация
TELEGRAM_CONFIG = {
    'token': "ВАШ_ТОКЕН_БОТА_ЗДЕСЬ",
    'chat_id': "ВАШ_CHAT_ID_ЗДЕСЬ"
}

# Настройки парсера
PARSER_CONFIG = {
    'base_url': "https://klg.quizplease.ru/schedule",
    'timeout': 30
}
```

## Запуск
```bash
# Локальный запуск (для тестирования)
python src/extract_classic_games.py

# Запуск как systemd сервис (production)
sudo nano /etc/systemd/system/quizplease_autoreg.service
sudo systemctl daemon-reload
sudo systemctl enable quizplease_autoreg
sudo systemctl start quizplease_autoreg
```

## Конфигурация systemd сервиса:
```ini
[Unit]
Description=QuizPlease Autoreg Parser
After=network.target

[Service]
Type=simple
User=mikhail
WorkingDirectory=/opt/quizplease_autoreg
ExecStart=/opt/quizplease-autoreg/venv/bin/python src/extract_classic_games.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Управление сервисом

```bash
# Проверить статус
sudo systemctl status quizplease_autoreg

# Просмотреть логи
sudo journalctl -u quizplease_autoreg -f

# Перезапустить сервис
sudo systemctl restart quizplease_autoreg

# Остановить сервис
sudo systemctl stop quizplease_autoreg
```

## Технические детали

### Обработка ошибок
**Таймауты:** Настройка таймаутов HTTP-запросов  
**Логирование:** Детальное логирование в файл и консоль  
**Уведомления:** Отправка сообщений об ошибках в Telegram  

## Безопасность  
**Изоляция:** Сервис работает под отдельным пользователем  
**Конфиденциальность:** Чувствительные данные не хранятся в репозитории  
**Обновления:** Автоматическое обновление через CI/CD

## Мониторинг

### Systemd журналы:
```bash
journalctl -u quizplease_autoreg
```

### Файловые логи:
```bash
tail -f logs/extract_games.log
```

### Статус сервиса:
```bash
systemctl status quizplease_autoreg
```

### Данные:
* `data/classic_games.json` - текущее расписание  
* `data/games_history.json` - история изменений

## Контакты

**Автор:** Михаил Бабков  
**GitHub:** Mikhailbbk  
**Telegram:** @Mikhailbbk  
**Email:** nebushko.mikhail@gmail.com  
**Портфолио:** mikhailbbk.github.io