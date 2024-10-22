![image](https://github.com/user-attachments/assets/0116c9ab-792d-4013-ac12-7d1f1992e617)


# VK Album Analyzer

VK Album Analyzer is a bot for analyzing album listening statistics on VKontakte. The bot collects and displays data on album listening statistics every 5th day, builds charts, and sends them to the user. The bot uses the VK API and the Playwright library for scraping listening data.

## Features

- Add albums to track
- Scrape and collect listening statistics every 5th day
- Build and send charts based on listening statistics
- Automatically update data every 5 days

## Installation

### Step 1: Clone the repository

Clone the project repository to your local machine:

```bash
git clone https://github.com/reddyzor/VK-MUSIC-ANALYZER-TELEGRAM-BOT.git
cd vk-album-analyzer
```

### Step 2: Create a virtual environment and install dependencies

Create a Python virtual environment (recommended for project isolation) and activate it:

```bash
python3 -m venv venv
source venv/bin/activate  # For Linux/MacOS

# or

venv\Scripts\activate  # For Windows
```

Install the necessary dependencies:

```bash
pip install -r requirements.txt
```

### Step 3: Install Playwright

For scraping via Playwright, install the required browsers:

```bash
playwright install
```

### Step 4: Configure the settings

Create a configuration file `config.py` in the project root. Example content:

```python
DATABASE = "albums.db"  # Path to the database
VK_API_KEY = "your_vk_api_key"  # Your VK API key
TEST_MODE = 0  # Choose mode: 0 — regular mode, 1 — testing
```

### Step 5: Initialize the database (automatically or manually)

Run the script to initialize the database:

```bash
python init_db.py
```

### Step 6: Start the bot

Run the bot:

```bash
python go.py
```

### Step 7: Additional settings for testing

For testing the bot in test mode, change the `TEST_MODE` variable in `config.py`:

- `TEST_MODE = 1` — Test functions via commands.
- `TEST_MODE = 2` — Test automatic statistics update after 5 seconds.

## Technologies Used

- Python 3.x
- Aiogram — Library for building Telegram bots
- Playwright — Scraping data from web pages
- SQLite — For storing album data
- Matplotlib — For chart plotting
- Pandas — For data processing

---

# VK Album Analyzer (Russian)

VK Album Analyzer — это бот для анализа статистики прослушиваний альбомов во ВКонтакте. Бот собирает и отображает данные о прослушиваниях музыкальных альбомов за каждый 5-й день, строит графики и отправляет их пользователю. Бот использует API ВКонтакте, а также библиотеку Playwright для парсинга данных о прослушиваниях.

## Функциональность

- Добавление альбомов для отслеживания
- Парсинг и сбор статистики прослушиваний за каждый 5-й день
- Построение и отправка графиков по статистике прослушиваний
- Автоматическое обновление данных каждые 5 дней

## Установка

### Шаг 1: Клонирование репозитория

Клонируйте репозиторий проекта на ваш локальный компьютер:

```bash
git clone https://github.com/reddyzor/VK-MUSIC-ANALYZER-TELEGRAM-BOT.git
cd vk-album-analyzer
```

### Шаг 2: Создание виртуального окружения и установка зависимостей

Создайте виртуальное окружение Python (рекомендуется для изоляции проекта) и активируйте его:

```bash
python3 -m venv venv
source venv/bin/activate  # Для Linux/MacOS

# или

venv\Scripts\activate  # Для Windows
```

Установите все необходимые зависимости:

```bash
pip install -r requirements.txt
```

### Шаг 3: Установка Playwright

Для работы парсинга через Playwright необходимо установить браузеры:

```bash
playwright install
```

### Шаг 4: Настройка конфигурации

Создайте файл конфигурации `config.py` в корне проекта. Пример содержимого:

```python
DATABASE = "albums.db"  # Путь к базе данных
VK_API_KEY = "your_vk_api_key"  # Ваш API-ключ ВКонтакте
TEST_MODE = 0  # Выберите режим работы: 0 — обычный режим, 1 — тестирование
```

### Шаг 5: Инициализация базы данных

Запустите скрипт для инициализации базы данных:

```bash
python init_db.py
```

### Шаг 6: Запуск бота

Запустите бота:

```bash
python go.py
```

### Шаг 7: Дополнительные настройки для тестирования

Для тестирования бота в тестовом режиме, можно изменить значение переменной `TEST_MODE` в `config.py`:

- `TEST_MODE = 1` — Тестирование функций через команды.
- `TEST_MODE = 2` — Тестирование автоматического обновления статистики через 5 секунд.

## Используемые технологии

- Python 3.x
- Aiogram — Библиотека для создания Telegram-ботов
- Playwright — Парсинг данных с веб-страниц
- SQLite — Для хранения данных об альбомах
- Matplotlib — Для построения графиков
- Pandas — Для обработки данных
