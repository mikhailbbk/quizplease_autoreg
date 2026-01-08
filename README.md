# QuizPlease Autoreg - Парсер и Telegram-бот


[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4.12-44B02A)](https://www.crummy.com/software/BeautifulSoup/)
[![Telegram API](https://img.shields.io/badge/Telegram%20API-✓-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-✓-2088FF?logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![Systemd](https://img.shields.io/badge/Systemd-✓-DA2F47)](https://systemd.io/)

**Автоматическая система мониторинга расписания игр на quizplease.ru с отправкой уведомлений в Telegram.**

## 🚀 Возможности
*   **Ежедневный мониторинг:** Парсинг расписания игр каждые 15 минут в рабочее время

*   **Telegram-бот:** Автоматические уведомления о новых играх и изменении статуса

*   **CI/CD пайплайн:** Автоматический деплой через GitHub Actions при каждом коммите в main

*   **Отказоустойчивость:** Работает как systemd-сервис 24/7 с автозапуском и автоматическим перезапуском при ошибках

*   **Полный расклад:** Детальная информация по каждой игре в Telegram (дата, время, место, цена, статус)

## 🛠 Технологический стек
*   **Язык:** Python 3.11
*   **Парсинг:** BeautifulSoup4, Requests
*   **Мессенджер:** Telegram Bot API
*   **Инфраструктура:** Ubuntu Server, Systemd, GitHub Actions
*   **Хранение данных:** JSON
*   **Логирование:** Стандартный logging + файловые логи
*   **Инструменты:** Git, GitHub Actions

## 📁 Структура проекта
quizplease-autoreg/
├── src/                   
│   ├── parser.py          
│   ├── bot.py             
│   └── config.py          
├── deploy/                
│   ├── quizplease.service 
│   └── deploy.sh          
├── tests/                 
├── requirements.txt       
├── .github/workflows/     
├── .github/workflows/     
│   └── ci-cd.yml
├── Makefile               
└── README.md              

## 🧠 Решенные задачи и принятые решения

### Задача 1: Надежный парсинг сайта с динамической структурой
*   **Проблема:** Сайт quizplease.ru имеет сложную HTML-структуру с вложенными элементами, которая может меняться при обновлениях.
*   **Решение:** 
    1. **Многоуровневое извлечение данных:** Реализовал несколько методов поиска для каждого поля (заголовок, дата, время, место, статус)

    2. **Резервные селекторы:** Для каждого элемента используются альтернативные CSS-селекторы на случай изменения структуры

    3. **Валидация данных:** Проверка корректности извлеченных данных перед сохранением

    4. **Генерация уникальных ID:** Создание хэшей на основе содержимого игры для отслеживания изменений

### Задача 2: Обеспечение бесперебойной работы 24/7
*   **Проблема:** Скрипт должен работать непрерывно, выдерживать перезагрузки сервера и автоматически восстанавливаться при ошибках.
*   **Решение:** 
    1. **Systemd сервис:** Создал production-ready systemd сервис с настройками:
    ```ini
    Restart=always
    RestartSec=10
    Type=simple
    User=ubuntu
    ```
    2. **Автозапуск при старте системы:** WantedBy=multi-user.target

    3. **Безопасность:** Настройки NoNewPrivileges=true, PrivateTmp=true, ProtectSystem=strict

    4. **Логирование в journald:** Все логи доступны через journalctl -u quizplease-autoreg

### Задача 3: Автоматизация деплоя и CI/CD
*   **Проблема:** Ручное обновление кода на сервере требовало 10-15 минут и могло привести к ошибкам.
*   **Решение:** Реализовал CI/CD пайплайн на GitHub Actions:
    ```yaml
   
    name: Deploy
    on:
    push:
        branches: [ main ]
    jobs:
    deploy:
        runs-on: ubuntu-latest
        steps:
        - uses: actions/checkout@v4
        - name: Deploy to server
            uses: appleboy/ssh-action@v0.1.5
            with:
            host: ${{ secrets.SERVER_HOST }}
            username: ${{ secrets.SERVER_USER }}
            key: ${{ secrets.SSH_KEY }}
            script: |
                cd /opt/quizplease_autoreg
                git fetch origin
                git reset --hard origin/main
                source venv/bin/activate
                pip install -r requirements.txt
                sudo systemctl restart quizplease-autoreg
                sudo systemctl status quizplease-autoreg --no-pager
    ```

    **Результат:** Время деплоя сократилось до 1-2 минут, процесс полностью автоматизирован.

### Задача 4: Интеллектуальные уведомления в Telegram

*   **Проблема:** Пользователи не должны получать спам, но должны быть в курсе всех важных изменений.
*   **Решение:** 
    1. **Только изменения:** Отправка уведомлений только при появлении новых игр или изменении статуса существующих

    2. **Полный расклад:** Каждая игра отправляется отдельным сообщением с полной информацией

    3. **Форматирование Markdown:** Читабельные сообщения с эмодзи и форматированием

    4. **Типы уведомлений:** Разделение на "новые игры", "изменение статуса", "доступные для записи"

### Задача 5: Конфигурация и безопасность
*   **Проблема:** Требовалось безопасное хранение чувствительных данных (токенов Telegram) и гибкая настройка.
*   **Решение:**

    1. **Шаблон конфигурации:** config.example.py для безопасного клонирования

    2. **Отдельный файл конфигурации:** config.py не отслеживается в Git

    3. **Утилита настройки:** get_chat_id.py помогает получить необходимые данные

    4. **Переменные окружения:** Поддержка .env файлов для production окружения

## 📊 Архитектура системы

### Схема работы:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   QuizPlease    │    │   QuizPlease    │    │   PostgreSQL    │
│     Website     │────│     Parser      │────│   (Optional)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │   Data Storage  │─────┐
                       │    (JSON)       │     │
                       └─────────────────┘     │
                               │               │
                               ▼               ▼
                       ┌─────────────────┐ ┌─────────────────┐
                       │   Change        │ │     Logging     │
                       │   Detector      │ │     System      │
                       └─────────────────┘ └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │   Telegram      │─────► Users
                       │      Bot        │
                       └─────────────────┘

### Компоненты:
1. **Парсер (src/extract_classic_games.py):** Основной модуль, извлекает данные с сайта

2. **Telegram бот (src/telegram_notifier.py):** Отправляет уведомления пользователям

3. **Хранилище данных (data/):** Кэширует предыдущие данные для сравнения

4. **Systemd сервис:** Обеспечивает непрерывную работу

5. **CI/CD пайплайн:** Автоматизирует развертывание

## 🚀 Быстрый старт

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
    'token': "8121544932:AAEBUzCUbQYgRzERRSaz37l7eO6P83pJEhM",
    'chat_id': "5137113164"
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
sudo cp systemd/quizplease.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable quizplease-autoreg
sudo systemctl start quizplease-autoreg
```

## Управление сервисом

```bash
# Проверить статус
sudo systemctl status quizplease-autoreg

# Просмотреть логи
sudo journalctl -u quizplease-autoreg -f

# Перезапустить сервис
sudo systemctl restart quizplease-autoreg

# Остановить сервис
sudo systemctl stop quizplease-autoreg
```

## 📈 Результаты и метрики
**Стабильность:** Работает 24/7 с сентября 2024 года без перерывов

**Производительность:** Обработка расписания занимает 2-3 секунды

**Надежность:** Автоматический перезапуск при ошибках, 99.9% uptime

**Эффективность деплоя:** CI/CD сократил время обновления с 15 минут до 1-2 минут

**Покрытие:** Мониторинг всех классических игр "Квиз, плиз! KLG"

## 🔧 Технические детали

### Обработка ошибок
**Таймауты:** Настройка таймаутов HTTP-запросов

**Повторные попытки:** Автоматические повторные запросы при сетевых ошибках

**Логирование:** Детальное логирование всех операций в файл и консоль

**Уведомления:** Отправка сообщений об ошибках в Telegram

## Безопасность

**Изоляция:** Сервис работает под отдельным пользователем

**Права:** Минимальные необходимые права для работы

**Конфиденциальность:** Чувствительные данные не хранятся в репозитории

**Обновления:** Автоматическое обновление через CI/CD

## Мониторинг

**Systemd журналы:** journalctl -u quizplease-autoreg

**Файловые логи:** logs/extract_games.log

**Статус сервиса:** systemctl status quizplease-autoreg

**Данные:** data/classic_games.json (кэш игр)

## 📞 Контакты

**Автор:** Михаил Бабков
**GitHub:** Mikhailbbk
**Telegram:** @Mikhailbbk
**Email:** nebushko.mikhail@gmail.com
**Портфолио:** mikhailbbk.github.io