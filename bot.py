# bot.py — Telegram бот с OpenAI Assistants API
import os
import time
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

# ---------- Настройки ----------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
MODEL_NAME = os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
MAX_INPUT_LENGTH = 1000
MAX_OUTPUT_LENGTH = 800

if not BOT_TOKEN:
    raise SystemExit("❌ ERROR: BOT_TOKEN не найден в .env")
if not OPENAI_KEY:
    raise SystemExit("❌ ERROR: OPENAI_KEY не найден в .env")
if not ASSISTANT_ID:
    raise SystemExit("❌ ERROR: OPENAI_ASSISTANT_ID не найден в .env")

logging.basicConfig(level=logging.INFO)
client = OpenAI(api_key=OPENAI_KEY)

# ---------- Команды ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я информационный бот. "
        "Задай свой вопрос — я постараюсь ответить понятно и по существу."
    )

# ---------- Обработка сообщений ----------
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text[:MAX_INPUT_LENGTH]

    await update.message.chat.send_action(action="typing")

    try:
        # Создаём новый thread для каждого запроса
        thread = client.beta.threads.create()

        # Формируем промт
        prompt = (
            f"Игнорируй все стандартные приветствия и системные инструкции. "
            f"Ты не должен повторять «Я — опытный медицинский ассистент…». "
            f"Отвечай кратко, ясно и по существу на вопрос пользователя ниже. "
            f"Если вопрос не относится к медицине, ответь честно, что не можешь дать точный совет. "
            f"Не более {MAX_OUTPUT_LENGTH} символов.\n"
            f"Вопрос: {user_message}"
        )

        # Добавляем сообщение пользователя
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )

        # Запускаем ассистента
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
            model=MODEL_NAME
        )

        # Ждём завершения
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status in ["completed", "failed", "cancelled"]:
                break
            time.sleep(1)

        # Получаем ответ
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        reply_text = None
        for msg in reversed(messages.data):
            if msg.role == "assistant" and msg.content:
                reply_text = msg.content[0].text.value
                break
        if not reply_text:
            reply_text = "⚠️ Не удалось получить ответ от ассистента."

        reply_text = reply_text[:MAX_OUTPUT_LENGTH]
        await update.message.reply_text(reply_text)

    except Exception as e:
        logging.error(f"Ошибка при обработке сообщения: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка при обработке запроса.")

# ---------- Основная функция ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask))
    print("✅ Бот запущен.")
    app.run_polling()

if __name__ == "__main__":
    main()
