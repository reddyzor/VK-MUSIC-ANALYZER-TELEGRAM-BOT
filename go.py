from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Chat, User, Message
from aiogram.types import FSInputFile
from datetime import datetime, timedelta
from aiogram.types import BotCommand
from playwright.sync_api import sync_playwright
import asyncio
import aiosqlite
import re
import os
import random
import string
import json
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, DayLocator
from matplotlib.ticker import MaxNLocator
import pandas as pd
from io import BytesIO
import logging
import config
from db import init_db, clear_database, fetchallStats
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

scheduler = AsyncIOScheduler()

# Инициализация бота
API_TOKEN = config.API_TOKEN
TEST_MODE = config.TEST_MODE 
album_id = 1  # for testing stats
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Функция для установки команд в меню
async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="analyze", description="Показать все добавленные альбомы"),
        BotCommand(command="help", description="Помощь по боту")
    ]
    await bot.set_my_commands(commands)

# Функция для извлечения основной части ссылки для альбома или плейлиста
def extract_album_id(url):
    pattern = re.compile(r'/music/(album|playlist)/([-_0-9]+)')
    match = pattern.search(url)
    if match:
        return match.group(2)  # Возвращаем только ID (вторую группу)
    return None

def is_valid_album_url(url):
    # Допускаем ссылки на альбомы и плейлисты
    pattern = re.compile(r'https?://(m\.)?vk\.com/music/(album|playlist)/[-\d]+_[\d]+(?:_[a-zA-Z0-9]+)?')
    return re.match(pattern, url)

# Функция для парсинга данных об альбоме или плейлисте с помощью Playwright
def get_album_info(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        try:
            if 'music/album' in url:
                # Логика для альбомов
                page.wait_for_selector('.AudioPlaylistSnippet__info', timeout=30000)
                page.wait_for_selector('.AudioPlaylistSnippet__title--main', timeout=30000)
                page.wait_for_selector('.AudioPlaylistSnippet__author a[href^="/artist/"]', timeout=30000)

                # Получаем количество прослушиваний и количество песен
                play_count_element = page.query_selector('.AudioPlaylistSnippet__info')
                play_count_text = play_count_element.inner_text() if play_count_element else "0 прослушиваний"

                if 'аудиозаписей' in play_count_text:
                    plays = play_count_text.split('прослушиваний')[0].strip()  # Извлекаем количество прослушиваний
                    track_count = play_count_text.split('прослушиваний')[1].split('аудиозаписей')[0].strip()  # Извлекаем количество песен
                else:
                    plays = play_count_text.strip()
                    track_count = '1'

                # Получаем жанр и год
                genre_year_element = page.query_selector_all('.AudioPlaylistSnippet__info')
                genre_year_text = genre_year_element[1].inner_text() if len(genre_year_element) > 1 else "не указано"

                # Получаем название альбома и исполнителя
                album_name = page.query_selector('.AudioPlaylistSnippet__title--main').inner_text() if page.query_selector('.AudioPlaylistSnippet__title--main') else "Не указано"
                artist_name = page.query_selector('.AudioPlaylistSnippet__author a[href^="/artist/"]').inner_text() if page.query_selector('.AudioPlaylistSnippet__author a[href^="/artist/"]') else "Не указано"

            elif 'music/playlist' in url:
                # Логика для плейлистов
                page.wait_for_selector('.AudioPlaylistSnippet__info', timeout=30000)

                # Извлекаем количество треков (учитывая разделение числа на несколько узлов)
                track_count_element = page.query_selector('.AudioPlaylistSnippet__info')
                track_count_html = track_count_element.inner_html() if track_count_element else ""
                track_count = ''.join([part for part in track_count_html if part.isdigit()]).strip() or "не указано"

                # Извлекаем количество прослушиваний
                play_count_element = page.query_selector_all('.AudioPlaylistSnippet__info')[1]
                play_count_text = play_count_element.inner_text().split('прослушиваний')[0].strip() if play_count_element else "0"

                # Получаем название альбома и исполнителя
                album_name = page.query_selector('.AudioPlaylistSnippet__title--main').inner_text() if page.query_selector('.AudioPlaylistSnippet__title--main') else "Не указано"
                artist_name = page.query_selector('.AudioPlaylistSnippet__author a').inner_text() if page.query_selector('.AudioPlaylistSnippet__author a') else "Не указано"

                genre_year_text = "это плейлист, нет таких данных"

            browser.close()

            return {
                "plays": play_count_text,
                "track_count": track_count,
                "name": album_name,
                "nick": artist_name,
                "genre_year": genre_year_text.strip()
            }
        except TimeoutError:
            browser.close()
            logging.error(f"Ошибка Timeout для URL: {url}")
            raise Exception("Такого альбома или плейлиста не существует")
        except Exception as e:
            browser.close()
            logging.error(f'Ошибка при парсинге {url}: {e}')
            raise Exception(f'Ошибка при парсинге: {str(e)}')

# Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer("👋 Привет!\n\n🔗 Отправь мне ссылку на альбом VK и я начну собирать по нему статистику прослушиваний!")

# Обработчик команды /test
@dp.message(Command("test"))
async def test_command(message: types.Message):
    if TEST_MODE == 1:
        await clear_database()
        await send_test_messages(message.chat.id)

# Команда /analyze
@dp.message(Command("analyze"))
async def analyze_albums(message: types.Message):
    # Извлекаем все альбомы из базы данных
    async with aiosqlite.connect(config.DATABASE) as db:
        async with db.execute('SELECT id, name, nick FROM albums') as cursor:
            albums = await cursor.fetchall()

    # Если в базе данных нет альбомов
    if not albums:
        await message.answer("🧺 В базе данных пока нет добавленных альбомов.")
        return

    # Создаем кнопки для каждого альбома
    buttons = [
        [InlineKeyboardButton(text=f"{album_name} - {album_nick}", callback_data=f"album_{album_id}")]
        for album_id, album_name, album_nick in albums
    ]
    
    # Создаем Inline-клавиатуру
    inline_kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Отправляем пользователю список альбомов
    await message.answer("🔀 Выберите альбом для просмотра информации", reply_markup=inline_kb)

# Обработчик всех сообщений
@dp.message()
async def handle_album_link(message: types.Message):
    album_url = message.text.strip()

    # Отправляем сообщение о начале анализа
    message_wait = await message.answer("⌛ Думаю, подождите немного...")

    # Проверка правильности ссылки
    if not is_valid_album_url(album_url):
        try:
            await message_wait.delete()
        except:
            pass
        await message.answer_photo(photo='https://i.ibb.co/ZdY4JSD/image.png', caption="❌ Вы ввели некорректный формат ссылки на альбом.\n\nℹ️ Ссылка должна быть таких форматов:\nhttps://vk.com/music/album/-2000600197_20600197_805b14b56dae3b32e9\nhttps://vk.com/music/playlist/-147845620_2949\n\n📷 На скриншоте показан пример, как нужно открыть нужный альбом, чтобы получить корректную ссылку. Нажмите на название альбома и Вы перейдёте на его оригинальную страницу.")
        return

    # Извлекаем основную часть ссылки
    album_id = extract_album_id(album_url)
    if not album_id:
        try:
            await message_wait.delete()
        except:
            pass
        await message.answer("❌ Не удалось извлечь данные из ссылки. Проверьте формат.")
        return

    # Проверяем, есть ли альбом с таким ID в базе данных
    async with aiosqlite.connect(config.DATABASE) as db:
        async with db.execute('SELECT * FROM albums WHERE url LIKE ?', (f'%{album_id}%',)) as cursor:
            album_exists = await cursor.fetchone()

    if album_exists:
        try:
            await message_wait.delete()
        except:
            pass

        await message.answer("🤫 Этот альбом уже добавлен в базу данных.\n\nℹ️ Нажмите на /analyze и посмотрите его статистику")
        return

    try:
        # Парсим информацию об альбоме
        try:
            await message_wait.delete()
        except:
            pass
        message_loading = await message.answer("⌛ Загружаю данные, подождите...")

        album_info = await asyncio.to_thread(get_album_info, album_url)

        track_count = album_info.get('track_count', 'не указано')  # Получаем количество песен

        # Получаем текущую дату
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Сохраняем данные в базу
        async with aiosqlite.connect(config.DATABASE) as db:
            await db.execute('INSERT INTO albums (url, name, nick, genre_year, counts, track_count, date) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                             (album_url, album_info["name"], album_info["nick"], album_info["genre_year"], album_info["plays"], track_count, current_date))
            await db.commit()

        try:
            await message_loading.delete()
        except:
            pass

        # Отправляем результат пользователю
        await message.answer(f"☑️ <b>Альбом успешно добавлен в анализатор.</b>\n\n📃 <b>Информация об альбоме</b>\n\n🔢 Количество прослушиваний: <b>{album_info['plays']}</b>\n"
                             f"🎵 Количество песен в альбоме: <b>{track_count}</b>\n📓 Альбом: <b>{album_info['name']}</b>\n"
                             f"😶 Исполнитель: <b>{album_info['nick']}</b>\n🌍 Жанр и год: <b>{album_info['genre_year']}</b>", parse_mode='HTML')
    except Exception as e:
        try:
            await message_loading.delete()
        except:
            pass

        # Проверка, если это ошибка, связанная с отсутствием альбома
        if str(e) == "Такого альбома не существует":
            await message.answer("❌ Такого альбома не существует.")
        else:
            print(f'[handle_album_link]: {e}')
            await message.answer("❌ Произошла ошибка при получении данных, попробуйте снова.\n\n📃 Возможно, этот альбом не существует или был удалён.")

# Обработчик нажатий на альбомы
@dp.callback_query(lambda callback_query: callback_query.data.startswith("album_"))
async def show_album_info(callback_query: types.CallbackQuery):
    album_id = callback_query.data.split("_")[1]

    try:
        await callback_query.message.delete()
    except:
        pass

    # Извлекаем данные альбома из базы
    async with aiosqlite.connect(config.DATABASE) as db:
        async with db.execute('SELECT name, nick, genre_year, counts, track_count, date FROM albums WHERE id = ?', (album_id,)) as cursor:
            album = await cursor.fetchone()

    if album:
        name, nick, genre_year, counts, track_count, date_added  = album

        # Создаем Inline-клавиатуру с кнопками "Статистика" и "Назад"
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data=f"stats_{album_id}"),
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_analyze")
            ]
        ])

        # Отправляем информацию об альбоме
        await callback_query.message.answer(f"\n\n📃 <b>Информация об альбоме:</b>\n\n🖥️ Уникальный ID: <b>{album_id}</b>\n🔢 Количество прослушиваний: <b>{counts}</b>\n"
                                            f"🎵 Количество песен в альбоме: <b>{track_count}</b>\n"
                                            f"📓 Альбом: <b>{name}</b>\n😶 Исполнитель: <b>{nick}</b>\n🌍 Жанр и год: <b>{genre_year}</b>\n📅 Дата добавления: <b>{date_added}</b>",
                                            reply_markup=inline_kb, parse_mode='HTML')
    else:
        await callback_query.message.answer("❌ Информация об альбоме не найдена.")


# Обработчик кнопки "Назад"
@dp.callback_query(lambda callback_query: callback_query.data == "back_to_analyze")
async def back_to_analyze(callback_query: types.CallbackQuery):
    # Удаляем предыдущее сообщение с информацией об альбоме
    try:
        await callback_query.message.delete()
    except:
        pass

    # Вызываем снова команду /analyze
    await analyze_albums(callback_query.message)

# Функция для преобразования строки с количеством прослушиваний в число
def parse_plays(plays_str):
    # Удаляем ненужные части строки и оставляем только число
    plays_str = plays_str.lower().strip()
    
    # Убираем любые символы, не относящиеся к числам или сокращениям
    plays_str = re.sub(r'[^0-9kKmM]', '', plays_str)

    # Проверяем наличие 'K' или 'M' и преобразуем строку в число
    if 'k' in plays_str:
        return int(float(plays_str.replace('k', '').strip()) * 1000)
    elif 'm' in plays_str:
        return int(float(plays_str.replace('m', '').strip()) * 1000000)
    else:
        # Если это просто число, без 'K' или 'M'
        match = re.match(r'(\d+)', plays_str)
        if match:
            return int(match.group(1))
        return 0

@dp.callback_query(lambda callback_query: callback_query.data.startswith("stats_"))
async def show_stats(callback_query: types.CallbackQuery):
    album_id = callback_query.data.split("_")[1]

    # Извлекаем данные статистики за каждый 5-й день
    stats = await fetchallStats(album_id)

    if not stats or len(stats) < 2:  # Если данных меньше 2-х записей, не строим график
        await callback_query.message.answer("❗ Данных недостаточно для построения статистики. Необходимо минимум две записи за разные дни.")
        return

    # Преобразование дат в формат datetime
    dates = pd.to_datetime([stat[1][:10] for stat in stats])

    # Преобразование количества прослушиваний в числа
    plays = [parse_plays(stat[0]) for stat in stats]

    # Если данных недостаточно (меньше 2 записей), выведем сообщение
    if len(dates) < 2:
        await callback_query.message.answer("❗ Данных недостаточно для построения графика. Попробуйте позже.")
        return

    # Ограничение на количество графиков (по 10 точек на каждом графике, не более 10 графиков)
    max_graphs = 10
    points_per_graph = 10

    # Берём только последние 100 записей (10 графиков по 10 точек)
    if len(plays) > max_graphs * points_per_graph:
        plays = plays[-max_graphs * points_per_graph:]
        dates = dates[-max_graphs * points_per_graph:]

    # Разбиваем данные на группы по 10 записей
    chunks = [plays[i:i + points_per_graph] for i in range(0, len(plays), points_per_graph)]
    date_chunks = [dates[i:i + points_per_graph] for i in range(0, len(dates), points_per_graph)]

    # Список для сохранённых файлов
    saved_files = []

    # Создаём графики по 10 точек и сохраняем их
    for i, (chunk_plays, chunk_dates) in enumerate(zip(chunks, date_chunks)):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(chunk_dates, chunk_plays, marker="o", label="Прослушивания", color="blue")

        # Добавление линий от X до точки
        for j, txt in enumerate(chunk_plays):
            ax.vlines(x=chunk_dates[j], ymin=0, ymax=chunk_plays[j], colors="gray", linestyle="dashed", linewidth=1)
            
            # Добавляем текстовые метки с количеством над каждой точкой
            ax.annotate(f'{txt}', (chunk_dates[j], chunk_plays[j]), textcoords="offset points", xytext=(0, 10), ha='center')

        # Настройка оси X для правильного отображения
        ax.xaxis.set_major_locator(DayLocator(interval=5))  # Интервал 5 дней
        ax.xaxis.set_major_formatter(DateFormatter("%d %b"))  # Форматируем ось X как день и месяц

        # Добавление подписей и оформления
        ax.set_xlabel("Дата")
        ax.set_ylabel("Количество прослушиваний")
        ax.set_title(f"Статистика прослушиваний каждые 5 дней (график {i + 1})")
        ax.legend(loc="upper left")

        # Генерация случайного имени файла для каждого графика
        random_filename = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10)) + '.png'
        filepath = os.path.join(os.getcwd(), random_filename)

        # Сохранение графика в файл
        plt.savefig(filepath)
        plt.close(fig)  # Закрываем фигуру, чтобы завершить процесс сохранения изображения

        # Добавляем файл в список для последующей отправки
        saved_files.append(filepath)

        # Прерываем, если было создано больше 10 файлов
        if len(saved_files) >= max_graphs:
            break

    # Последовательная отправка файлов и удаление после отправки
    for filepath in saved_files:
        try:
            print(f"Отправка файла: {filepath}")
            photo = FSInputFile(filepath)  # Используем FSInputFile для отправки пути к файлу
            await bot.send_photo(chat_id=callback_query.message.chat.id, photo=photo)
        finally:
            # Удаление файла после отправки
            if os.path.exists(filepath):
                os.remove(filepath)

# Тестовые данные
test_urls = [
    'https://vk.com/music/playlist/-147845620_2949',
    'https://vk.com/music/playlist/264577489_28',
    'https://vk.com/music/album/-2000600197_20600197_805b14b56dae3b32e9',
    'https://vk.com/music/album/-2000113136_7113136_2a00a34a604257e4fe'
]

# Функция для отправки тестовых сообщений
async def send_test_messages(chat_id):
    test_urls = [
        "https://vk.com/music/playlist/-147845620_2949",
        "https://vk.com/music/playlist/264577489_28",
        "https://vk.com/music/album/-2000600197_20600197_805b14b56dae3b32e9",
        "https://vk.com/music/album/-2000113136_7113136_2a00a34a604257e4fe"
    ]
    
    for url in test_urls:
        print(f"Отправляем ссылку: {url}")
        
        # Создание тестового пользователя
        test_user = User(id=123456, is_bot=False, first_name="Test", username="testuser")
        
        # Создание тестового сообщения с реальным chat_id
        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=chat_id, type="private"),
            from_user=test_user,
            text=url
        )
        
        # Привязываем бота к сообщению
        message = message.as_(bot)
        await handle_album_link(message)
        await asyncio.sleep(2)  # Небольшая пауза между запросами

async def update_album_stats():
    """Функция для автоматического обновления статистики альбомов каждые 5 дней."""
    # Загружаем данные из JSON-файла
    data = load_data()

    async with aiosqlite.connect(config.DATABASE) as db:
        async with db.execute('SELECT id, url FROM albums') as cursor:
            albums = await cursor.fetchall()

        for album_id, album_url in albums:
            try:
                # Преобразуем album_id в строку для использования в JSON
                album_id_str = str(album_id)

                # Проверяем, если ли информация в JSON
                if album_id_str in data:
                    last_update = data[album_id_str].get('last_update', None)
                else:
                    data[album_id_str] = {"url": album_url, "last_update": None}
                    last_update = None

                # Проверяем, прошло ли 5 дней с последнего обновления
                if last_update:
                    last_update_date = pd.to_datetime(last_update)
                    current_date = pd.Timestamp.now()

                    if (current_date - last_update_date).days < 5:
                        logging.info(f"Альбом {album_id} был обновлен менее 5 дней назад.")
                        continue

                # Локальный импорт функции get_album_info, чтобы избежать циклической зависимости
                from go import get_album_info
                album_info = await asyncio.to_thread(get_album_info, album_url)

                # Проверяем данные, которые вернула функция get_album_info
                logging.info(f"Данные альбома {album_id}: {album_info}")

                if 'plays' not in album_info:
                    raise ValueError(f"Не найдено поле 'plays' для альбома {album_id}. Данные: {album_info}")

                current_plays = album_info['plays']  # Сохраняем количество прослушиваний напрямую

                # Вставляем новую запись в таблицу stats
                await db.execute('INSERT INTO stats (aid, counts) VALUES (?, ?)', 
                                 (album_id, current_plays))

                await db.commit()

                # Обновляем дату последнего обновления в JSON
                data[album_id_str]['last_update'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                save_data(data)  # Сохраняем обновленный JSON

            except Exception as e:
                logging.error(f"Ошибка обновления статистики для альбома {album_id}: {e}", exc_info=True)

def load_data():
    """Загружаем данные из JSON-файла. Если файл не существует, создаем новый."""
    if os.path.exists(config.DATA_FILE):
        with open(config.DATA_FILE, 'r') as file:
            return json.load(file)
    else:
        return {}

def save_data(data):
    """Сохраняем данные в JSON-файл."""
    with open(config.DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def update_last_checked(album_id):
    """Обновляем дату последнего обновления для альбома в формате JSON."""
    data = load_data()
    data[album_id]['last_update'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    save_data(data)

# testing stats
# Примерные данные о прослушиваниях
def generate_random_stats(start_date, days):
    stats = []
    current_date = start_date
    for _ in range(days):
        plays = random.randint(1000, 10000)  # Случайное количество прослушиваний от 1K до 10K
        stats.append((album_id, plays, current_date.strftime('%Y-%m-%d %H:%M:%S')))
        current_date += timedelta(days=5)  # Добавляем по 5 дней
    return stats

# Функция для вставки данных в таблицу stats
async def insert_stats(album_id, stats):
    async with aiosqlite.connect(config.DATABASE) as db:
        for stat in stats:
            await db.execute(
                "INSERT INTO stats (aid, counts, date) VALUES (?, ?, ?)", 
                stat
            )
        await db.commit()
    print(f"Статистика для альбома {album_id} успешно добавлена.")

async def on_startup():
    await init_db()  # Инициализация базы данных

    # Инициализация планировщика
    scheduler = AsyncIOScheduler()

    if TEST_MODE == 1:
        logging.warning('Внимание! Запущен тестовый режим #1, Вам доступна команда /test')    

    elif TEST_MODE == 2:
        logging.info("Внимание! Запущен тестовый режим #2. Обновление статистики включится через 5 секунд")
        await asyncio.sleep(5)
        try:
            await update_album_stats()
        except Exception as e:
            logging.error(f"Ошибка в обновлении статистики: {e}")

    elif TEST_MODE == 3:
        album_id = 1  # Убедитесь, что переменная album_id инициализирована
        logging.warning(f'Внимание! Запущен тестовый режим #3, сейчас будет добавлена фейковая статистика на альбом ID: {album_id}.')

        start_date = datetime(2024, 10, 22)
        test_stats = generate_random_stats(start_date, 25)
        
        try:
            await insert_stats(album_id, test_stats)
        except Exception as e:
            logging.error(f"Ошибка при добавлении тестовой статистики: {e}")

    else:
        logging.info("Бот запущен в обычном режиме: обновление статистики каждые пять дней")
        # Запускаем обновление статистики каждые 5 дней
        scheduler.add_job(update_album_stats, 'interval', days=5)

    # Старт планировщика
    scheduler.start()
    
# Регистрируем хук для старта
dp.startup.register(on_startup)

# Запуск бота
if __name__ == "__main__":
    dp.run_polling(bot, skip_updates=True)