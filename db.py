from config import DATABASE
import aiosqlite

async def init_db():
    """Создание таблицы в базе данных"""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                name TEXT,
                nick TEXT,
                genre_year TEXT,
                counts TEXT,
                track_count TEXT,
                date TEXT  -- Добавляем колонку для даты
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aid INTEGER,                -- ID альбома
                counts TEXT,             -- Количество прослушиваний
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Дата обновления
                FOREIGN KEY (aid) REFERENCES albums(id)
            )
        ''')

        await db.commit()

# Функция для очистки базы данных
async def clear_database():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM albums")
        await db.commit()

async def fetchallStats(album_id):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute('''
            SELECT counts, date FROM stats
            WHERE aid = ?
            ORDER BY date
        ''', (album_id,)) as cursor:
            stats = await cursor.fetchall()
            return stats
