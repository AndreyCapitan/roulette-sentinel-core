"""
Основной файл Telegram-бота "Умный аналитик рулетки".
"""

import logging
from dotenv import load_dotenv
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Загрузка переменных окружения
load_dotenv(r"C:\roulette-sentinel-core\.env")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояние пользователя
user_sessions = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    logger.info(f"User {user_id} ({user.username}) started the bot.")

    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "initial_bank": 1000.0,
            "current_bank": 1000.0,
            "base_bet": 10.0,
            "streak": 0,
            "z_count_last_50": 0,
            "zero_buffer": 0.0,
            "spins_history": [],
            "is_active": True
        }
    
    session = user_sessions[user_id]
    
    reply_text = (
        f"Привет, {user.mention_html()}!\n"
        f"Текущая стратегия: Адаптивный Щит (v3.1)\n"
        f"Начальный банк: {session['initial_bank']}\n"
        f"Базовая ставка: {session['base_bet']}\n\n"
        f"Команды:\n/stats - статистика\n/stop - завершить сессию"
    )
    await update.message.reply_html(reply_text)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /stats"""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested stats.")

    if user_id not in user_sessions or not user_sessions[user_id]["is_active"]:
        await update.message.reply_text("Нет активной сессии. Используйте /start")
        return

    session = user_sessions[user_id]
    
    stats_text = (
        f"--- Статистика ---\n"
        f"Банк: {session['current_bank']:.2f}\n"
        f"Серия проигрышей: {session['streak']}\n"
        f"Нулей за 50 спинов: {session['z_count_last_50']}\n"
        f"Zero-буфер: {session['zero_buffer']:.2f}\n"
        f"Статус: {'Активна' if session['is_active'] else 'Завершена'}"
    )
    await update.message.reply_text(stats_text)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /stop"""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested to stop.")

    if user_id in user_sessions and user_sessions[user_id]["is_active"]:
        user_sessions[user_id]["is_active"] = False
        await update.message.reply_text("Сессия завершена. Для новой сессии /start")
    else:
        await update.message.reply_text("Нет активной сессии")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик неизвестных команд"""
    await update.message.reply_text("Неизвестная команда. Доступные команды: /start, /stats, /stop")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error("Ошибка:", exc_info=context.error)

def main() -> None:
    """Запуск бота"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Токен не найден! Проверьте .env файл")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация обработчиков
    handlers = [
        CommandHandler("start", start_command),
        CommandHandler("stats", stats_command),
        CommandHandler("stop", stop_command),
        MessageHandler(filters.COMMAND, unknown_command)
    ]
    
    for handler in handlers:
        application.add_handler(handler)
    
    application.add_error_handler(error_handler)
    
    logger.info("Бот запущен")
    application.run_polling()

if __name__ == "__main__":
    main()