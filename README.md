# Marco – Your AI Life Co-Pilot via Telegram 🤖📆

Marco is a smart AI-powered Telegram bot that helps you plan your life, remind you of tasks, and even understand voice messages — all through a natural chat interface.

Built with:
- GPT-4o-mini (OpenAI)
- Whisper (OpenAI voice transcription)
- FastAPI (backend)
- Telegram Bot API
- Deployable to Render.com

## Features

- 🧠 Natural language reminders
- 🗣️ Voice message transcription with OpenAI Whisper
- ✅ Confirmation before scheduling tasks
- ⏰ Telegram reminders
- 🌐 Fully deployable via Render

## Setup Instructions

### 1. Clone the Repo

```bash
git clone https://github.com/RawadZaidan/co-bot.git
cd co-bot
```

### 2. Install Dependencies

Make sure you're using Python 3.9+ and `ffmpeg` is installed on your system.

```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file (or set environment variables manually)

```
OPENAI_API_KEY=your_openai_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id (optional)
```

### 4. Run Locally

```bash
uvicorn marco_bot:app --host 0.0.0.0 --port 10000
```

To test webhook locally, use `ngrok`.

### 5. Deploy to Render

Push the repo and connect it to Render. Set environment variables in the dashboard.

## Telegram Usage

- `/start` – Start Marco
- `/remind [task info]` – Create a reminder
- Send a voice message – Marco will understand it and ask for confirmation

---

MIT License
