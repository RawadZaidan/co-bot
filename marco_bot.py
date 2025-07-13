import os
import json
import datetime
import asyncio
import subprocess
import tempfile

from fastapi import FastAPI, Request
from telegram import Update, File
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dateutil import parser as dateparser
import openai

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")
openai_client = openai

# Telegram bot token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Optional, for direct sending

# Data file to store reminders
DATA_FILE = "reminders.json"

app = FastAPI()
application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

# In-memory store for pending confirmation
user_pending_confirmations = {}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"scheduled_reminders": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_arabic(text):
    return any('\u0600' <= c <= '\u06FF' for c in text)

def localize_reply(parsed, lang="en"):
    dt_str = parsed["datetime"].strftime("%Y-%m-%d %H:%M")
    if lang == "ar":
        return (
            f"📌 المهمة: {parsed['task']}\n"
            f"🕒 الوقت: {dt_str}\n"
            f"🔔 التذكير: قبل {parsed['reminder_minutes']} دقيقة\n"
            "هل أضبط التذكير؟ (نعم / لا)"
        )
    else:
        return (
            f"Here's what I understood:\n"
            f"📌 Task: {parsed['task']}\n"
            f"🕒 When: {dt_str}\n"
            f"🔔 Reminder: {parsed['reminder_minutes']} min before\n"
            "Reply 'yes' to confirm."
        )

async def parse_reminder_text(reminder_text):
    prompt = f"""
You are Marco, a multilingual AI assistant. Understand Arabic, English, and mixed-language reminders.
Extract the following from the user message:
- Task title (in the original language)
- Date/time (in ISO format)
- Reminder lead time (in minutes, optional)

Message: '{reminder_text}'

Respond ONLY in JSON format like:
{{"task": "...", "datetime": "...", "reminder_minutes": ...}}
"""
    response = await openai_client.chat.completions.acreate(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are Marco."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,
        temperature=0,
    )
    try:
        parsed = json.loads(response.choices[0].message.content.strip())
        dt = dateparser.parse(parsed.get("datetime", ""))
        return {
            "task": parsed.get("task", "Untitled Task"),
            "datetime": dt,
            "reminder_minutes": int(parsed.get("reminder_minutes", 10))
        }
    except Exception:
        now = datetime.datetime.now() + datetime.timedelta(hours=1)
        return {"task": reminder_text, "datetime": now, "reminder_minutes": 10}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! I'm Marco, your AI life co-pilot.\n"
        "Send me a reminder like:\n"
        "'Remind me to drink water tomorrow at 3pm'\n"
        "Or send a voice message."
    )

async def handle_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminder_text = " ".join(context.args)
    if not reminder_text:
        await update.message.reply_text("Please specify what you want to be reminded about.")
        return
    parsed = await parse_reminder_text(reminder_text)
    user_pending_confirmations[user_id] = parsed
    lang = "ar" if is_arabic(reminder_text) else "en"
    await update.message.reply_text(localize_reply(parsed, lang))

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.lower()
    if user_id not in user_pending_confirmations:
        return

    if text in ["yes", "نعم"]:
        r = user_pending_confirmations.pop(user_id)
        data = load_data()
        remind_time = r["datetime"] - datetime.timedelta(minutes=r["reminder_minutes"])
        data["scheduled_reminders"].append({
            "task": r["task"],
            "time": r["datetime"].isoformat(),
            "reminder_send_time": remind_time.isoformat(),
            "user_id": user_id
        })
        save_data(data)
        lang = "ar" if is_arabic(update.message.text) else "en"
        msg = "✅ تم ضبط التذكير!" if lang == "ar" else "✅ Reminder set!"
        await update.message.reply_text(msg)
    elif text in ["no", "لا"]:
        user_pending_confirmations.pop(user_id)
        msg = "❌ تم إلغاء التذكير." if is_arabic(update.message.text) else "❌ Okay, reminder canceled."
        await update.message.reply_text(msg)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    file: File = await context.bot.get_file(voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        await file.download_to_drive(custom_path=f.name)
        ogg_path = f.name

    # Convert OGG to MP3 using ffmpeg
    mp3_path = ogg_path.replace(".ogg", ".mp3")
    subprocess.run(["ffmpeg", "-y", "-i", ogg_path, mp3_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Transcribe with OpenAI Whisper
    with open(mp3_path, "rb") as audio_file:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )

    await update.message.reply_text(f"🗣 You said: {transcript}")
    context.args = transcript.split()
    await handle_remind(update, context)

@app.on_event("startup")
async def startup_event():
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

@app.on_event("shutdown")
async def shutdown_event():
    await application.updater.stop()
    await application.stop()
    await application.shutdown()

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("remind", handle_remind))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirmation))
application.add_handler(MessageHandler(filters.VOICE, handle_voice))


@app.post("/webhook")
async def telegram_webhook(request: Request):
    json_update = await request.json()
    update = Update.de_json(json_update, application.bot)
    await application.process_update(update)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("marco_bot:app", host="0.0.0.0", port=int(os.getenv("PORT", 10000)), log_level="info")
