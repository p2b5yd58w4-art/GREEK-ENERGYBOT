import asyncio
import logging
import os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", "bot.db")
DEFAULT_TZ = os.getenv("TIMEZONE", "Europe/Amsterdam")
if not TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN. Скопируйте .env.example в .env и вставьте токен от @BotFather.")

logging.basicConfig(level=logging.INFO)
bot = Bot(TOKEN)
dp = Dispatcher()

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Учебные материалы — стартовый авторский курс. Он не является официальным экзаменом CEFR.
LESSONS = [
    {"level":"A1","title":"Алфавит и приветствия","goal":"Поздороваться и представиться.",
     "body":"Γεια σου! (Я су) — Привет! одному человеку\\nΓεια σας! (Я сас) — Здравствуйте / приветствие нескольким людям\\nΚαλημέρα (калимера) — Доброе утро\\nΚαλησπέρα (калиспЕра) — Добрый вечер\\nΕυχαριστώ (эфхаристО) — Спасибо\\nΜε λένε… (ме лЭне…) — Меня зовут…",
     "question":"Как по-гречески сказать «Спасибо»?","options":["Παρακαλώ","Ευχαριστώ","Γεια σου"],"answer":1,
     "explain":"Ευχαριστώ означает «спасибо». Παρακαλώ — «пожалуйста / не за что»."},
    {"level":"A1","title":"Как тебя зовут?","goal":"Спросить имя и представиться.",
     "body":"Πώς σε λένε; (пос се лЭне?) — Как тебя зовут?\\nΜε λένε Άννα. — Меня зовут Анна.\\nΧάρηκα! (хАрика) — Приятно познакомиться!\\nДаже если пока не читаешь греческий, произноси слова вслух и повторяй их.",
     "question":"Что означает «Πώς σε λένε;»?","options":["Как дела?","Как тебя зовут?","Откуда ты?"],"answer":1,
     "explain":"Πώς σε λένε; — «Как тебя зовут?»"},
    {"level":"A1","title":"Да, нет и вежливость","goal":"Использовать базовые ответы.",
     "body":"Ναι (нэ) — Да\\nΌχι (Охи) — Нет\\nΠαρακαλώ (паракалО) — Пожалуйста / не за что\\nΣυγγνώμη (сигнОми) — Извините\\nΔεν καταλαβαίνω (дзен каталавЭно) — Я не понимаю.",
     "question":"Как сказать «Нет»?","options":["Ναι","Όχι","Ευχαριστώ"],"answer":1,
     "explain":"Όχι означает «нет»; Ναι — «да»."},
    {"level":"A1","title":"Числа 1–5","goal":"Понимать первые числа.",
     "body":"1 ένα (Эна)\\n2 δύο (дИо)\\n3 τρία (трИа)\\n4 τέσσερα (тЭссера)\\n5 πέντε (пЭнде)\\nПопробуй посчитать предметы вокруг себя по-гречески.",
     "question":"Какое греческое слово означает число 3?","options":["δύο","τρία","πέντε"],"answer":1,
     "explain":"τρία — три."},
    {"level":"A1","title":"Кофе и простые просьбы","goal":"Сделать простый заказ.",
     "body":"Έναν καφέ, παρακαλώ. — Один кофе, пожалуйста.\\nΝερό, παρακαλώ. — Воду, пожалуйста.\\nΠόσο κάνει; — Сколько стоит?\\nΘέλω… — Я хочу…\\nОбрати внимание: формы слов могут меняться в зависимости от рода и грамматики.",
     "question":"Как спросить «Сколько стоит?»?","options":["Πόσο κάνει;","Πώς σε λένε;","Καλημέρα"],"answer":0,
     "explain":"Πόσο κάνει; — «Сколько стоит?»"},
    {"level":"A1","title":"Язык и страна","goal":"Сказать, что ты изучаешь греческий.",
     "body":"Μιλάω ρωσικά. — Я говорю по-русски.\\nΜαθαίνω ελληνικά. — Я учу греческий.\\nΕίμαι από… — Я из…\\nΔεν μιλάω καλά ελληνικά. — Я не очень хорошо говорю по-гречески.\\nΤο ελληνικά — греческий язык; μαθαίνω — учу.",
     "question":"Как сказать «Я учу греческий»?","options":["Μαθαίνω ελληνικά.","Μιλάω ρωσικά.","Δεν καταλαβαίνω."],"answer":0,
     "explain":"Μαθαίνω ελληνικά — «Я учу греческий»."},
    {"level":"A2","title":"Ежедневные действия","goal":"Описывать простые привычки.",
     "body":"Ξυπνάω — я просыпаюсь\\nΠηγαίνω στη δουλειά — я иду на работу\\nΤρώω — я ем\\nΠίνω νερό — я пью воду\\nΚάθε μέρα — каждый день\\nПример: Κάθε μέρα μαθαίνω ελληνικά. — Каждый день я учу греческий.",
     "question":"Что означает «Κάθε μέρα»?","options":["Каждый день","Завтра","Вчера"],"answer":0,
     "explain":"Κάθε μέρα — каждый день."},
    {"level":"B1","title":"Мнение и аргументы","goal":"Выражать мнение.",
     "body":"Νομίζω ότι… — Я думаю, что…\\nΚατά τη γνώμη μου… — По моему мнению…\\nΕπειδή… — потому что…\\nΩστόσο… — однако…\\nПример: Νομίζω ότι η εξάσκηση είναι σημαντική, επειδή βοηθάει στη μάθηση. — Думаю, практика важна, потому что помогает обучению.",
     "question":"Как сказать «По моему мнению»?","options":["Ωστόσο","Κατά τη γνώμη μου","Επειδή"],"answer":1,
     "explain":"Κατά τη γνώμη μου — «по моему мнению»."},
    {"level":"B2","title":"Связная аргументация","goal":"Связывать причины и выводы.",
     "body":"Παρόλο που… — несмотря на то что…\\nΣυνεπώς… — следовательно…\\nΑπό τη μία πλευρά… από την άλλη… — с одной стороны… с другой…\\nΗ τεχνολογία διευκολύνει την επικοινωνία, παρόλο που δημιουργεί νέες προκλήσεις. — Технологии облегчают общение, хотя создают новые вызовы.",
     "question":"Что означает «Συνεπώς»?","options":["Например","Следовательно","Впрочем"],"answer":1,
     "explain":"Συνεπώς — «следовательно»."},
    {"level":"C1","title":"Регистр и нюансы","goal":"Различать формальный и нейтральный стиль.",
     "body":"Σε επίσημο ύφος (в официальном стиле) предпочтительны точные формулировки и ясная структура.\\nΘα ήθελα να επισημάνω ότι… — Я хотел(а) бы отметить, что…\\nΑξίζει να σημειωθεί ότι… — Стоит отметить, что…\\nИзучай оттенки значения и контекст, а не только перевод.",
     "question":"Как начать фразу «Я хотел(а) бы отметить, что…»?","options":["Θα ήθελα να επισημάνω ότι…","Γεια σου!","Ναι"],"answer":0,
     "explain":"Это вежливая формальная конструкция."},
    {"level":"C2","title":"Точная интерпретация","goal":"Работать с нюансами сложных формулировок.",
     "body":"На уровне C2 важны точность, стилистические оттенки, идиомы и понимание сложных текстов.\\nΕν ολίγοις… — вкратце…\\nΥπό την προϋπόθεση ότι… — при условии, что…\\nΔεν πρόκειται απλώς για…, αλλά για… — речь идёт не просто о…, а о…\\nЭто вводный урок: для реального C2 нужны длинные тексты, аудирование и продуктивные задания.",
     "question":"Что означает «Εν ολίγοις»?","options":["Вкратце","С другой стороны","Возможно"],"answer":0,
     "explain":"Εν ολίγοις — «вкратце»."},
]

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, first_name TEXT, level TEXT NOT NULL DEFAULT 'A1',
            timezone TEXT NOT NULL DEFAULT 'Europe/Amsterdam', reminder_hour INTEGER DEFAULT 19,
            created_at TEXT NOT NULL)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS energy (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, brand TEXT,
            volume_ml INTEGER, caffeine_mg REAL, consumed_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS lesson_progress (
            user_id INTEGER NOT NULL, lesson_index INTEGER NOT NULL, completed_at TEXT NOT NULL,
            PRIMARY KEY(user_id, lesson_index))""")
        await db.execute("""CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            lesson_index INTEGER NOT NULL, correct INTEGER NOT NULL, created_at TEXT NOT NULL)""")
        await db.commit()

async def ensure_user(user_id, first_name=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id, first_name, created_at) VALUES(?,?,?)",
                         (user_id, first_name or "", datetime.now().isoformat(timespec="seconds")))
        await db.commit()

def main_menu():
    b = InlineKeyboardBuilder()
    b.button(text="🇬🇷 Учить греческий", callback_data="learn")
    b.button(text="⚡ Записать энергетик", callback_data="energy")
    b.button(text="📊 Статистика", callback_data="stats")
    b.button(text="🎯 Мой прогресс", callback_data="progress")
    b.button(text="⏰ Напоминания", callback_data="reminders")
    b.button(text="ℹ️ Помощь", callback_data="help")
    b.adjust(1, 1, 2, 1, 1)
    return b.as_markup()

@dp.message(CommandStart())
async def start(message: Message):
    await ensure_user(message.from_user.id, message.from_user.first_name)
    await message.answer(
        "Привет! Я Greek & Energy — бот для учёта энергетиков и изучения современного греческого.\n\n"
        "🇬🇷 Курс организован по уровням CEFR A1–C2. Начнём с нуля: алфавит, приветствия и базовые фразы.\n"
        "⚡ Я считаю записанный кофеин, но не могу определить точное содержание без данных с этикетки.\n\n"
        "Выбери действие в меню ниже.", reply_markup=main_menu())

@dp.message(Command("menu"))
async def menu(message: Message):
    await message.answer("Главное меню:", reply_markup=main_menu())

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "Команды:\n/start — запуск\n/menu — главное меню\n/lesson — следующий урок\n/energy — записать энергетик\n/stats — статистика\n\n"
        "Для записи энергетика нажми кнопку меню. Введи данные в формате: бренд, объём в мл, кофеин в мг.\n"
        "Пример: Monster, 500, 160\n\n"
        "Кофеин зависит от бренда и версии напитка: проверяй этикетку. Бот не заменяет медицинскую рекомендацию.",
        reply_markup=main_menu())

@dp.callback_query(F.data == "help")
async def help_cb(c: CallbackQuery):
    await c.message.answer("Команды: /start, /menu, /lesson, /energy, /stats.\\nПример записи: Monster, 500, 160. Проверь кофеин на этикетке.")
    await c.answer()

@dp.callback_query(F.data == "learn")
async def learn_cb(c: CallbackQuery):
    await send_next_lesson(c.message, c.from_user.id)
    await c.answer()

@dp.message(Command("lesson"))
async def lesson_command(message: Message):
    await ensure_user(message.from_user.id, message.from_user.first_name)
    await send_next_lesson(message, message.from_user.id)

async def send_next_lesson(message, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT lesson_index FROM lesson_progress WHERE user_id=?", (user_id,))
        completed = {row[0] for row in await cur.fetchall()}
    idx = next((i for i in range(len(LESSONS)) if i not in completed), None)
    if idx is None:
        await message.answer("Ты прошёл все уроки демо-курса! Это стартовый набор, не полный курс A1–C2. Новые тематические модули можно добавлять в LESSONS.")
        return
    lesson = LESSONS[idx]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Пройти мини-тест", callback_data=f"quiz:{idx}")],
        [InlineKeyboardButton(text="📚 Главное меню", callback_data="menu")]
    ])
    await message.answer(f"🇬🇷 Урок {idx+1}: {lesson['title']}\\nУровень: {lesson['level']}\\nЦель: {lesson['goal']}\\n\\n{lesson['body']}", reply_markup=kb)

@dp.callback_query(F.data.startswith("quiz:"))
async def quiz_start(c: CallbackQuery):
    idx = int(c.data.split(":")[1])
    lesson = LESSONS[idx]
    kb = InlineKeyboardBuilder()
    for i, option in enumerate(lesson["options"]):
        kb.button(text=option, callback_data=f"answer:{idx}:{i}")
    kb.adjust(1)
    await c.message.answer(f"📝 {lesson['question']}", reply_markup=kb.as_markup())
    await c.answer()

@dp.callback_query(F.data.startswith("answer:"))
async def quiz_answer(c: CallbackQuery):
    _, idx_s, answer_s = c.data.split(":")
    idx, answer = int(idx_s), int(answer_s)
    lesson = LESSONS[idx]
    correct = int(answer == lesson["answer"])
    await ensure_user(c.from_user.id, c.from_user.first_name)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO quiz_results(user_id, lesson_index, correct, created_at) VALUES(?,?,?,?)",
                         (c.from_user.id, idx, correct, datetime.now().isoformat(timespec="seconds")))
        if correct:
            await db.execute("INSERT OR IGNORE INTO lesson_progress(user_id, lesson_index, completed_at) VALUES(?,?,?)",
                             (c.from_user.id, idx, datetime.now().isoformat(timespec="seconds")))
        await db.commit()
    if correct:
        msg = f"✅ Верно!\\n{lesson['explain']}\\n\\nУрок засчитан. Нажми «Учить греческий», чтобы продолжить."
    else:
        msg = f"❌ Пока неверно.\\n{lesson['explain']}\\n\\nПопробуй ещё раз через урок."
    await c.message.answer(msg, reply_markup=main_menu())
    await c.answer()

@dp.callback_query(F.data == "menu")
async def menu_cb(c: CallbackQuery):
    await c.message.answer("Главное меню:", reply_markup=main_menu())
    await c.answer()

@dp.callback_query(F.data == "energy")
async def energy_cb(c: CallbackQuery):
    await c.message.answer(
        "Отправь одной строкой: бренд, объём в мл, кофеин в мг.\\n"
        "Пример: Red Bull, 250, 80\\n"
        "Если кофеин неизвестен, укажи 0 и проверь этикетку позже. Для напитка без сахара это поле не меняется.")
    await c.answer()

@dp.message(Command("energy"))
async def energy_command(message: Message):
    await ensure_user(message.from_user.id, message.from_user.first_name)
    await message.answer("Введи: бренд, объём в мл, кофеин в мг. Пример: Monster, 500, 160")

@dp.message(F.text)
async def text_router(message: Message):
    text = message.text.strip()
    if text.startswith("/"):
        return
    parts = [p.strip() for p in text.split(",")]
    if len(parts) == 3 and parts[1].isdigit():
        try:
            caffeine = float(parts[2].replace(",", "."))
            volume = int(parts[1])
            if volume < 1 or volume > 5000 or caffeine < 0 or caffeine > 2000:
                raise ValueError()
            await ensure_user(message.from_user.id, message.from_user.first_name)
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("INSERT INTO energy(user_id, brand, volume_ml, caffeine_mg, consumed_at) VALUES(?,?,?,?,?)",
                                 (message.from_user.id, parts[0][:80], volume, caffeine, datetime.now().isoformat(timespec="seconds")))
                await db.commit()
            await message.answer(
                f"⚡ Записано: {parts[0]} — {volume} мл, кофеин {caffeine:g} мг.\\n"
                "Это значение основано на введённых тобой данных. Если кофеин не указан на этикетке, запись может быть неточной.",
                reply_markup=main_menu())
        except ValueError:
            await message.answer("Не получилось разобрать данные. Пример: Monster, 500, 160")
    else:
        await message.answer("Используй кнопки меню или формат записи энергетика: бренд, объём в мл, кофеин в мг.", reply_markup=main_menu())

@dp.callback_query(F.data == "stats")
async def stats_cb(c: CallbackQuery):
    await show_stats(c.message, c.from_user.id)
    await c.answer()

@dp.message(Command("stats"))
async def stats_command(message: Message):
    await ensure_user(message.from_user.id, message.from_user.first_name)
    await show_stats(message, message.from_user.id)

async def show_stats(message, user_id):
    now = datetime.now()
    day_start = datetime.combine(date.today(), datetime.min.time()).isoformat()
    month_start = datetime(now.year, now.month, 1).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(caffeine_mg),0), COALESCE(SUM(volume_ml),0) FROM energy WHERE user_id=? AND consumed_at>=?",
                               (user_id, day_start))
        today_count, today_caf, today_ml = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(caffeine_mg),0), COALESCE(SUM(volume_ml),0) FROM energy WHERE user_id=? AND consumed_at>=?",
                               (user_id, month_start))
        month_count, month_caf, month_ml = await cur.fetchone()
    await message.answer(
        f"📊 Статистика энергетиков\\n\\nСегодня: {today_count} записей, {today_ml} мл, {today_caf:g} мг кофеина.\\n"
        f"С начала месяца: {month_count} записей, {month_ml} мл, {month_caf:g} мг кофеина.\\n\\n"
        "Важно: учитываются только внесённые записи; статистика не определяет индивидуально безопасную дозу кофеина.",
        reply_markup=main_menu())

@dp.callback_query(F.data == "progress")
async def progress_cb(c: CallbackQuery):
    await ensure_user(c.from_user.id, c.from_user.first_name)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM lesson_progress WHERE user_id=?", (c.from_user.id,))
        done = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(correct),0) FROM quiz_results WHERE user_id=?", (c.from_user.id,))
        total, correct = await cur.fetchone()
    await c.message.answer(
        f"🎯 Твой прогресс\\nУроков пройдено: {done} из {len(LESSONS)} в демо-курсе.\\n"
        f"Ответов в тестах: {total}; правильных: {correct}.\\nТекущий стартовый уровень: A1. Уровень CEFR автоматически не присваивается — для этого нужна более полная оценка навыков.",
        reply_markup=main_menu())
    await c.answer()

@dp.callback_query(F.data == "reminders")
async def reminders_cb(c: CallbackQuery):
    await c.message.answer(
        "⏰ Напоминания: на первом этапе бот не отправляет автоматические уведомления по расписанию. "
        "Можно добавить ежедневные напоминания после размещения бота на постоянно работающем сервере. "
        "Пока используй /lesson и /stats. Напоминания не будут подталкивать к употреблению энергетиков.")
    await c.answer()

async def main():
    await init_db()
    logging.info("Bot is starting")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
